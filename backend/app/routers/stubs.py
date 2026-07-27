"""Endpunkte für spätere Phasenplan-Schritte (CONCEPT.md, Abschnitt 9: Phasen 2-4).

Liefern bewusst nur leere/Platzhalter-Antworten, damit Frontend-Views schon
gegen eine stabile Route entwickeln können, ohne dass Jira-Sync, Gap-Berechnung
oder Team-Pflege bereits produktiv sein müssen.
"""

from fastapi import APIRouter

router = APIRouter(tags=["future-phases"])


@router.get("/team")
def list_teams():
    return {"status": "not_implemented", "phase": "4 – Team-Kapazität", "teams": []}


@router.get("/gap")
def gap_analysis():
    return {"status": "not_implemented", "phase": "3 – Gap-Analyse + Hochrechnung", "gaps": []}


@router.get("/forecast")
def forecast():
    return {
        "status": "not_implemented",
        "phase": "3 – Gap-Analyse + Hochrechnung",
        "hinweis": "Trendfortschreibung (Variante 1) ist als Default vorgesehen, siehe CONCEPT.md Abschnitt 5.",
    }
