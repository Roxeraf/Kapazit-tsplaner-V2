from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import ai_readiness, entity_links, models, schemas
from ..database import get_db

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/readiness", response_model=schemas.AiReadinessReport)
def get_ai_readiness(db: Session = Depends(get_db)):
    """Phase-26-Audit: maschinenlesbare, read-only Bewertung der Voraussetzungen für einen
    späteren KI-Agenten. `productive_agent_enabled` bleibt bis zur Zugriffskontrolle false."""
    return ai_readiness.build_report(db)


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _relation_out(relation: models.EntityRelation) -> schemas.EntityRelationOut:
    return schemas.EntityRelationOut(
        id=relation.id,
        source_entity_type=relation.source_entity_type,
        source_entity_id=relation.source_entity_id,
        target_entity_type=relation.target_entity_type,
        target_entity_id=relation.target_entity_id,
        relation_type=relation.relation_type,
        created_at=relation.created_at,
        created_by_person_id=relation.created_by_person_id,
    )


@router.post("/entity-relations", response_model=schemas.EntityRelationOut, status_code=201)
def create_entity_relation(payload: schemas.EntityRelationCreate, db: Session = Depends(get_db)):
    """Legt eine gerichtete, typisierte Beziehung zwischen zwei Entitäten an (z.B. Decision
    `resulted_in` Task) - Knowledge-Layer-Baustein, siehe CONCEPT.md Abschnitt 12."""
    relation = entity_links.create_relation(
        db,
        payload.source_entity_type,
        payload.source_entity_id,
        payload.target_entity_type,
        payload.target_entity_id,
        payload.relation_type,
        payload.created_by_person_id,
    )
    db.commit()
    return _relation_out(relation)


@router.get("/entity-relations", response_model=list[schemas.EntityRelationOut])
def list_entity_relations(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    """Alle Relationen einer Entität, unabhängig davon ob sie Quelle oder Ziel ist."""
    relations = entity_links.relations_for(db, entity_type, entity_id)
    return [_relation_out(r) for r in relations]


@router.delete("/entity-relations/{relation_id}", status_code=204)
def delete_entity_relation(relation_id: int, db: Session = Depends(get_db)):
    relation = db.get(models.EntityRelation, relation_id)
    if relation is None:
        raise HTTPException(status_code=404, detail="Relation nicht gefunden")
    db.delete(relation)
    db.commit()


# ---------------------------------------------------------------------------
# Knowledge Query Layer (Phase 15, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 46) -
# zentrale strukturierte Zugriffsschicht über alle taggable Entitäten. Noch kein Vector-RAG/
# KI-Agent - soll später sowohl UI-Funktionen (z.B. Tag-Dossiers, Phase 24) als auch einen
# KI-Agenten (Phase 26+) versorgen. `/knowledge/tags` wird bewusst nicht dupliziert - dafür
# existiert bereits `GET /tags` (Phase 13).
# ---------------------------------------------------------------------------


@router.get("/knowledge/entities", response_model=list[schemas.KnowledgeEntityOut])
def list_knowledge_entities(entity_type: schemas.EntityType, project_id: int | None = None, db: Session = Depends(get_db)):
    return entity_links.list_entity_summaries(db, entity_type, project_id)


@router.get("/knowledge/search", response_model=list[schemas.KnowledgeSearchResult])
def search_knowledge(q: str, project_id: int | None = None, db: Session = Depends(get_db)):
    """Volltextsuche über Titel/Text aller taggable Entitäten sowie über Tag-Namen (liefert
    dann die verknüpften Entitäten) - noch keine semantische/Vector-Suche."""
    if not q.strip():
        return []
    return entity_links.search_entities(db, q.strip(), project_id)


@router.get("/knowledge/context", response_model=schemas.KnowledgeContextOut)
def get_knowledge_context(entity_type: schemas.EntityType, entity_id: int, db: Session = Depends(get_db)):
    """"Wissenskarte" einer einzelnen Entität: Tags, Dokumente, explizite Relationen und
    (Phase 24) tag-basierte Related Entities an einem Ort."""
    summary = entity_links.entity_summary(db, entity_type, entity_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Entität nicht gefunden")
    return schemas.KnowledgeContextOut(
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=summary["project_id"],
        label=summary["label"],
        tags=entity_links.tags_for(db, entity_type, entity_id),
        documents=entity_links.documents_for(db, entity_type, entity_id),
        relations=[_relation_out(r) for r in entity_links.relations_for(db, entity_type, entity_id)],
        related=[
            schemas.RelatedEntityOut(**entity)
            for entity in entity_links.related_entities(db, entity_type, entity_id)
        ],
    )


@router.get("/knowledge/relations", response_model=list[schemas.EntityRelationOut])
def query_knowledge_relations(
    relation_type: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Breitere Filterung als `GET /entity-relations` (das genau eine Entität voraussetzt):
    beliebige Kombination aus relation_type/entity_type+entity_id/project_id."""
    if (entity_type is None) != (entity_id is None):
        raise HTTPException(status_code=422, detail="entity_type und entity_id müssen zusammen gesetzt werden")

    query = db.query(models.EntityRelation)
    if relation_type is not None:
        query = query.filter(models.EntityRelation.relation_type == relation_type)
    if entity_type is not None and entity_id is not None:
        query = query.filter(
            or_(
                (models.EntityRelation.source_entity_type == entity_type)
                & (models.EntityRelation.source_entity_id == entity_id),
                (models.EntityRelation.target_entity_type == entity_type)
                & (models.EntityRelation.target_entity_id == entity_id),
            )
        )
    relations = query.order_by(models.EntityRelation.created_at).all()

    if project_id is not None:
        def _touches_project(relation: models.EntityRelation) -> bool:
            for etype, eid in (
                (relation.source_entity_type, relation.source_entity_id),
                (relation.target_entity_type, relation.target_entity_id),
            ):
                summary = entity_links.entity_summary(db, etype, eid)
                if summary is not None and summary["project_id"] == project_id:
                    return True
            return False

        relations = [r for r in relations if _touches_project(r)]

    return [_relation_out(r) for r in relations]


@router.get("/knowledge/project/{project_id}", response_model=schemas.KnowledgeProjectContextOut)
def get_project_knowledge_context(project_id: int, db: Session = Depends(get_db)):
    """Wissenskontext-Aggregation eines Projekts: wie viele Entitäten je Typ, welche Tags
    im Projekt tatsächlich verwendet werden, welche Relationen Projekt-Entitäten betreffen."""
    _get_project_or_404(db, project_id)

    counts: dict[str, int] = {}
    tag_names: set[str] = set()
    relation_ids: dict[int, models.EntityRelation] = {}

    for entity_type in entity_links.ENTITY_TYPES:
        summaries = entity_links.list_entity_summaries(db, entity_type, project_id)
        counts[entity_type] = len(summaries)
        for summary in summaries:
            tag_names.update(summary["tags"])
            for relation in entity_links.relations_for(db, entity_type, summary["entity_id"]):
                relation_ids[relation.id] = relation

    return schemas.KnowledgeProjectContextOut(
        project_id=project_id,
        counts=counts,
        tags=sorted(tag_names),
        relations=[_relation_out(r) for r in relation_ids.values()],
    )


# ---------------------------------------------------------------------------
# Tag-Dossiers (Phase 24, Master-MD Abschnitt 44) - ein einzelner Tag oder eine Kombination
# wie "#Kunde + #GoLive" wird zu einem dynamischen Projektdossier. Bewusst unter
# `/knowledge/tags/dossier` statt `/tags/{id}/dossier`, weil kombinierte Tags (mode="and"/
# "or", mehrere Namen) keiner einzelnen Tag-ID zugeordnet werden können.
# ---------------------------------------------------------------------------


@router.get("/knowledge/tags/dossier", response_model=schemas.TagDossierOut)
def get_tag_dossier(
    tags: str,
    mode: Literal["and", "or"] = "and",
    project_id: int | None = None,
    activity_limit: int = 20,
    db: Session = Depends(get_db),
):
    """Dynamisches Tag-Dossier: Anzahl je Entitätstyp, die Entitäten selbst und die jüngste
    Aktivität dazu - für einen einzelnen Tag (`tags=Schnittstelle`) oder eine Kombination
    (`tags=Kunde,GoLive&mode=and`). `tags` matcht auch Synonyme (siehe
    `entity_links.resolve_tag`), z.B. `tags=Livegang` findet denselben Tag wie "GoLive"."""
    tag_names = [name.strip() for name in tags.split(",") if name.strip()]
    if not tag_names:
        raise HTTPException(status_code=422, detail="tags darf nicht leer sein")

    entities = entity_links.entities_by_tags(db, tag_names, mode, project_id)

    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity["entity_type"]] = counts.get(entity["entity_type"], 0) + 1

    activity: list[schemas.ActivityItemOut] = []
    for entity in entities:
        timestamp = entity_links.timestamp_for(db, entity["entity_type"], entity["entity_id"])
        if timestamp is None:
            continue
        activity.append(
            schemas.ActivityItemOut(
                entity_type=entity["entity_type"],
                entity_id=entity["entity_id"],
                label=entity["label"],
                timestamp=timestamp,
                tags=entity["tags"],
            )
        )
    activity.sort(key=lambda item: item.timestamp, reverse=True)

    return schemas.TagDossierOut(
        tags=tag_names,
        mode=mode,
        project_id=project_id,
        counts=counts,
        entities=[schemas.KnowledgeEntityOut(**entity) for entity in entities],
        activity=activity[:activity_limit],
    )
