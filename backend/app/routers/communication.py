"""Entscheidungen/Risiken/Meetingprotokolle (Kommunikation-Tab, siehe CONCEPT.md Abschnitt
6a) - CRUD folgt in Phase 4. GET /tags lebt in routers/documents.py, da es eng an
entity_links.py gekoppelt ist, das auch die Dokument-Verknüpfungen verwaltet."""

from fastapi import APIRouter

router = APIRouter(tags=["communication"])
