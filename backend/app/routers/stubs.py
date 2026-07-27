"""Endpunkte für noch ausstehende Phasenplan-Schritte (CONCEPT.md, Abschnitt 9: Phase 3).

Team-Kapazität (Phase 4, ../team.py) und Jira-Ist-Integration (Phase 2, ../jira.py)
sind bereits umgesetzt. Liefert bewusst nur leere/Platzhalter-Antworten für die
noch offene Gap-Analyse/Hochrechnung, damit Frontend-Views schon gegen eine
stabile Route entwickeln können.
"""

from fastapi import APIRouter

router = APIRouter(tags=["future-phases"])


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
