"""Erklärbarer KI-Readiness-Audit für Phase 26.

Das Modul bewertet ausschließlich vorhandene strukturierte Daten und Architekturmerkmale.
Es implementiert weder einen Agenten noch RAG/Embeddings und verändert keine Daten.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import entity_links, models, schemas


def _coverage(complete: int, total: int) -> float:
    return round(complete / total * 100, 1) if total else 100.0


def _check(
    key: str,
    label: str,
    status: str,
    evidence: str,
    recommendation: str | None = None,
    metrics: list[schemas.ReadinessMetric] | None = None,
) -> schemas.ReadinessCheck:
    return schemas.ReadinessCheck(
        key=key,
        label=label,
        status=status,
        evidence=evidence,
        recommendation=recommendation,
        metrics=metrics or [],
    )


def build_report(db: Session) -> schemas.AiReadinessReport:
    entity_types = list(entity_links.ENTITY_TYPES)
    relations = db.query(models.EntityRelation).all()
    tags = db.query(models.Tag).filter(models.Tag.active.is_(True)).all()
    semantically_described = sum(bool(t.ai_description or t.synonyms) for t in tags)
    plan_phases = db.query(models.PlanPhase).all()
    milestones = db.query(models.Milestone).all()
    planning_entities = [*plan_phases, *milestones]
    timeline_complete = sum(
        bool(
            (getattr(item, "baseline_start", None) or getattr(item, "baseline_date", None))
            and (getattr(item, "forecast_start", None) or getattr(item, "forecast_date", None))
        )
        for item in planning_entities
    )
    blockers = db.query(models.Blocker).filter(models.Blocker.status != "geloest").all()
    owned_blockers = sum(bool(b.owner_person_id or b.owner_team_id) for b in blockers)
    explained_blockers = sum(bool(b.waiting_for_party and b.next_action and b.impact) for b in blockers)
    thresholds = db.query(models.HealthThreshold).count()
    permissions = {row.name for row in db.query(models.Permission).all()}

    checks = [
        _check(
            "structured_entities",
            "Relevante Entitäten strukturiert erreichbar",
            "READY",
            f"Der Knowledge Layer exponiert {len(entity_types)} standardisierte Entitätstypen.",
            metrics=[schemas.ReadinessMetric(key="entity_types", value=len(entity_types), unit="Typen")],
        ),
        _check(
            "machine_readable_relations",
            "Beziehungen maschinenlesbar",
            "READY",
            "EntityRelation verwendet gerichtete, typisierte Quelle/Ziel-Beziehungen.",
            metrics=[schemas.ReadinessMetric(key="relations", value=len(relations), unit="Relationen")],
        ),
        _check(
            "semantic_tags",
            "Tags semantisch beschrieben",
            "READY" if _coverage(semantically_described, len(tags)) >= 80 else "PARTIAL",
            f"{semantically_described} von {len(tags)} aktiven Tags besitzen AI-Beschreibung oder Synonyme.",
            None if _coverage(semantically_described, len(tags)) >= 80 else "Semantische Metadaten der fachlich relevanten Tags vervollständigen.",
            [schemas.ReadinessMetric(key="semantic_tag_coverage", value=_coverage(semantically_described, len(tags)), unit="Prozent")],
        ),
        _check(
            "planning_dimensions",
            "Plan/Baseline/Forecast/Actual eindeutig",
            "READY" if _coverage(timeline_complete, len(planning_entities)) >= 80 else "PARTIAL",
            "PlanPhase und Milestone besitzen getrennte Baseline-, Forecast- und Actual-Felder.",
            None if _coverage(timeline_complete, len(planning_entities)) >= 80 else "Baseline und Forecast in bestehenden Planungsobjekten vervollständigen.",
            [schemas.ReadinessMetric(key="timeline_coverage", value=_coverage(timeline_complete, len(planning_entities)), unit="Prozent")],
        ),
        _check("explainable_gaps", "GAPs berechenbar und erklärbar", "READY", "GAP Engine und Controlling liefern Capacity-, Allocation-, Effort-, Schedule-, Progress- und Utilization-Gaps mit Drill-down-IDs."),
        _check(
            "blocker_ownership",
            "Blocker und Ownership nachvollziehbar",
            "READY" if _coverage(owned_blockers, len(blockers)) >= 80 and _coverage(explained_blockers, len(blockers)) >= 80 else "PARTIAL",
            f"{owned_blockers} von {len(blockers)} offenen Blockern haben einen Owner; {explained_blockers} besitzen Waiting-for, nächste Aktion und Impact.",
            "Owner, nächste Aktion und Impact für offene Blocker verpflichtend pflegen." if blockers and (owned_blockers < len(blockers) or explained_blockers < len(blockers)) else None,
            [schemas.ReadinessMetric(key="ownership_coverage", value=_coverage(owned_blockers, len(blockers)), unit="Prozent"), schemas.ReadinessMetric(key="explanation_coverage", value=_coverage(explained_blockers, len(blockers)), unit="Prozent")],
        ),
        _check("capacity_drilldown", "Capacity Gaps drill-down-fähig", "READY", "ResourceDemand und ResourceAssignment bleiben getrennt; Portfolio-Aggregate referenzieren Projekt, Rolle und Demand-ID."),
        _check("explainable_health", "Project Health erklärbar", "READY", f"Health-Dimensionen liefern Wert und Erklärung; {thresholds} Schwellwerte sind explizit konfiguriert.", metrics=[schemas.ReadinessMetric(key="configured_thresholds", value=thresholds, unit="Schwellwerte")]),
        _check("knowledge_context", "Knowledge Layer liefert Fachkontext", "READY", "Projekt- und Entitätskontext bündeln Tags, Dokumente, explizite Relationen und Related Entities."),
        _check(
            "agent_authorization",
            "Berechtigungen für Agent-Zugriffe vorbereitet",
            "BLOCKED",
            f"{len(permissions)} fachliche Capabilities sind modelliert, aber AppRole ist keiner Identität zugeordnet und Requests werden nicht autorisiert.",
            "Vor einem produktiven Agenten Identity/SSO, Rollen-Zuordnung, read-only Agent-Capabilities, Projekt-Scope und Auditierung implementieren.",
            [schemas.ReadinessMetric(key="permissions", value=len(permissions), unit="Capabilities")],
        ),
    ]
    blocking = [check.recommendation for check in checks if check.status == "BLOCKED" and check.recommendation]
    overall = "BLOCKED" if blocking else ("PARTIAL" if any(c.status == "PARTIAL" for c in checks) else "READY")
    return schemas.AiReadinessReport(
        overall_status=overall,
        generated_at=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        blockers=blocking,
    )
