"""Zyklischer Background-Sync für Jira/Tempo (P20.5, siehe
P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 13/14/16). Kein neues Scheduler-Framework
(Celery/APScheduler/...) - das Repo hat keine bestehende Job-Engine (verifiziert, siehe
requirements.txt), daher ein simpler In-Process-`asyncio`-Loop, der beim FastAPI-Startup-Event
angestoßen wird (Auftrag Abschnitt 13: "KEINE neue Infrastruktur erfinden, wenn bereits ein
geeigneter Mechanismus vorhanden ist" - hier ist keiner vorhanden, ein zusätzlicher Prozess/
Broker wäre für einen einzelnen periodischen DB-Sync-Job unverhältnismäßig).

Fehlerisolation (Abschnitt 16): jira_sync.sync_project_and_refresh() fängt Fehler bereits pro
Projekt ab (JiraSyncStatus) - ein zusätzliches try/except hier fängt zusätzlich alles ab, was
außerhalb eines einzelnen Projekt-Syncs schiefgehen könnte (z.B. eine DB-Verbindung, die beim
Session-Aufbau selbst fehlschlägt), damit der Scheduler-Loop niemals wegen eines einzelnen
fehlgeschlagenen Zyklus dauerhaft stirbt (keine Endlosschleife durch schnelles Retry: der
nächste Versuch wartet den vollen Intervall ab, kein Retry-Sturm).
"""

import asyncio
import logging
import os

from . import jira_client, jira_sync, models
from .database import SessionLocal

logger = logging.getLogger(__name__)

# Bevorzugtes Sync-Intervall laut Auftrag (Abschnitt 13): alle 15 Minuten. Über Env
# konfigurierbar (Tests/Betrieb), damit kein Codeänderung für ein anderes Intervall nötig ist.
DEFAULT_INTERVAL_SECONDS = 15 * 60


def _interval_seconds() -> int:
    raw = os.environ.get("JIRA_AUTOSYNC_INTERVAL_SECONDS")
    if raw is None:
        return DEFAULT_INTERVAL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_INTERVAL_SECONDS
    return value if value > 0 else DEFAULT_INTERVAL_SECONDS


def autosync_enabled() -> bool:
    """Abschaltbar über Env (Default an) - z.B. für Testläufe, die keinen Hintergrund-Task
    parallel zur eigenen DB-Session wollen. Ohne konfigurierte Jira-Verbindung ist der
    Scheduler ohnehin ein No-Op (kein Projekt hat dann etwas zu synchronisieren), läuft aber
    trotzdem harmlos leer, falls Jira zur Laufzeit nachträglich konfiguriert wird."""
    return os.environ.get("JIRA_AUTOSYNC_ENABLED", "true").lower() not in ("false", "0", "")


def run_sync_cycle() -> None:
    """Ein einzelner Sync-Durchlauf über alle Jira-konfigurierten Projekte (Abschnitt 14) -
    eigene, kurzlebige DB-Session (nicht die Request-Session), damit ein hängender Sync keine
    Request-Verbindung blockiert. Wird sowohl vom periodischen Loop als auch potenziell aus
    Tests direkt aufgerufen."""
    if not jira_client.is_configured():
        return
    db = SessionLocal()
    try:
        projects = db.query(models.Project).filter(models.Project.jira_component.isnot(None)).all()
        for project in projects:
            try:
                jira_sync.sync_project_and_refresh(db, project)
            except Exception:  # noqa: BLE001 - siehe Modul-Docstring: ein Projekt darf den Zyklus nicht stoppen
                logger.exception("Automatischer Jira-Sync für Projekt %s fehlgeschlagen", project.id)
    finally:
        db.close()


async def _loop() -> None:
    interval = _interval_seconds()
    while True:
        try:
            await asyncio.to_thread(run_sync_cycle)
        except Exception:  # noqa: BLE001 - der Loop selbst darf nie sterben (Abschnitt 16)
            logger.exception("Automatischer Jira-Sync-Zyklus fehlgeschlagen")
        await asyncio.sleep(interval)


_task: asyncio.Task | None = None


def start() -> None:
    """Beim FastAPI-Startup-Event aufgerufen (app/main.py). No-Op, wenn Autosync deaktiviert
    ist oder bereits ein Loop läuft (idempotent bei mehrfachem Aufruf, z.B. Test-Fixtures)."""
    global _task
    if not autosync_enabled():
        logger.info("Jira-Auto-Sync deaktiviert (JIRA_AUTOSYNC_ENABLED=false)")
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.get_event_loop().create_task(_loop())


def stop() -> None:
    """Beim FastAPI-Shutdown-Event aufgerufen - beendet den Loop sauber statt ihn beim
    Prozessende hart abzuwürgen."""
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
