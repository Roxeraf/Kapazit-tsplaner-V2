from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import entity_links, models, schemas
from ..database import get_db

router = APIRouter(tags=["knowledge"])


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
