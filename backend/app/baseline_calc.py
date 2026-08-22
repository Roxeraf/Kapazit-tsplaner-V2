"""Baseline-Deviation-Berechnung (Phase 18, siehe CONCEPT.md Abschnitt 12 / Master-MD
Abschnitt 12). Aus routers/baselines.py extrahiert, damit routers/controlling.py (Phase 23,
Baseline Deviations portfolioweit) dieselbe Berechnung ohne Cross-Router-Import nutzen kann -
analog zu capacity_calc.py/gap_calc.py aus Phase 21/22."""

from datetime import date

from sqlalchemy.orm import Session

from . import entity_links, models, schemas

# Datumsfelder, für die Deviations (Tages-Differenz aktueller Wert vs. eingefrorener Wert)
# berechnet werden können.
DATE_FIELDS = {"baseline_start", "baseline_end", "forecast_start", "forecast_end", "baseline_date", "forecast_date"}

# P11 (Planungs-/Kapazitätskonsolidierung): plan_fte zusätzlich zu den Datumsfeldern in die
# Deviation-Liste aufnehmen, damit der Planstand-Vergleich auch die Aufwands-Abweichung zeigen
# kann ("Plan-FTE 0,5 → 0,7, +0,2 FTE"). delta_days bleibt für plan_fte bewusst None
# (_parse_date scheitert erwartungsgemäß an einem Float-String) - baseline_value/current_value
# genügen dem Frontend, um die numerische Differenz selbst darzustellen; kein neues Feld auf
# BaselineDeviationOut nötig.
# P18/B-7 (CONCEPT.md Abschnitt 6b.14): parent_phase_id (PlanPhase) und plan_phase_id
# (Milestone) zusätzlich zu den Datums-/FTE-Feldern als sichtbare Deviation - eine
# strukturelle Änderung (Phase war Top-Level -> jetzt Unterphase, oder umgekehrt) ist für den
# Planstand-Vergleich genauso relevant wie eine Termin-/Aufwandsabweichung. reihenfolge wird
# zwar mit eingefroren (siehe routers/baselines.py._SNAPSHOT_FIELDS), aber bewusst NICHT hier
# aufgenommen - reine Sortierposition ist keine fachlich sichtbare Abweichung.
DEVIATION_FIELDS = DATE_FIELDS | {"plan_fte", "parent_phase_id", "plan_phase_id"}


def _parse_date(value: object) -> date | None:
    # P11: nimmt seit DEVIATION_FIELDS auch den live gelesenen current_value entgegen, der für
    # numerische Felder (z.B. plan_fte) ein float statt str ist - date.fromisoformat() wirft
    # dafür TypeError statt ValueError, deshalb beide abfangen statt nur ValueError.
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def latest_snapshot(db: Session, project_id: int) -> models.BaselineSnapshot | None:
    return (
        db.query(models.BaselineSnapshot)
        .filter(models.BaselineSnapshot.project_id == project_id)
        .order_by(models.BaselineSnapshot.created_at.desc())
        .first()
    )


def _structural_plan_phase_deviations(
    db: Session, snapshot: models.BaselineSnapshot
) -> list[schemas.BaselineDeviationOut]:
    """P18.1 Stabilization (CONCEPT.md Abschnitt 16.16, ehem. Audit-Defekt #1, Abschnitt
    16.15): erkennt PlanPhase-Zeilen, die zwischen Snapshot-Zeitpunkt und heute hinzugekommen
    oder entfernt wurden - die reine Feld-für-Feld-Schleife in compute_deviations vergleicht
    nur Entitäten, die zum Snapshot-Zeitpunkt bereits eingefroren wurden, und übersieht daher
    strukturelle Baum-Änderungen. Erweitert die bestehende Baseline-/Deviation-API additiv
    (keine zweite Diff-Engine, kein neuer Endpoint) - eine "added"/"removed" PlanPhase liefert
    genau eine synthetische Deviation-Zeile statt eines Feld-Deltas je eingefrorenem Feld."""
    snapshot_ids = {
        row[0]
        for row in db.query(models.BaselineEntry.entity_id)
        .filter(
            models.BaselineEntry.baseline_id == snapshot.id,
            models.BaselineEntry.entity_type == "plan_phase",
        )
        .distinct()
    }
    current_ids = {
        row[0]
        for row in db.query(models.PlanPhase.id).filter(models.PlanPhase.project_id == snapshot.project_id)
    }

    deviations: list[schemas.BaselineDeviationOut] = []

    for added_id in sorted(current_ids - snapshot_ids):
        phase = db.get(models.PlanPhase, added_id)
        name = phase.phase_type if phase is not None else None
        deviations.append(
            schemas.BaselineDeviationOut(
                entity_type="plan_phase",
                entity_id=added_id,
                label=name,
                field="phase_added",
                baseline_value=None,
                current_value=name,
                delta_days=None,
                type="added",
            )
        )

    for removed_id in sorted(snapshot_ids - current_ids):
        # Die Zeile existiert nicht mehr - der Name muss aus den eigenen, zum Snapshot-Zeitpunkt
        # eingefrorenen Daten rekonstruiert werden (phase_type ist bereits Teil von
        # routers/baselines.py._SNAPSHOT_FIELDS, keine Migration nötig). Kein "#<id>"-Fallback
        # im normalen UI (CONCEPT.md Auftrag Abschnitt 1) - falls die Zeile ausnahmsweise fehlt
        # (z.B. sehr alter Snapshot ohne phase_type-Eintrag), liefert label=None und das
        # Frontend zeigt einen sprechenden Platzhalter statt der rohen ID.
        name_entry = (
            db.query(models.BaselineEntry)
            .filter(
                models.BaselineEntry.baseline_id == snapshot.id,
                models.BaselineEntry.entity_type == "plan_phase",
                models.BaselineEntry.entity_id == removed_id,
                models.BaselineEntry.field == "phase_type",
            )
            .first()
        )
        name = name_entry.value if name_entry is not None else None
        deviations.append(
            schemas.BaselineDeviationOut(
                entity_type="plan_phase",
                entity_id=removed_id,
                label=name,
                field="phase_removed",
                baseline_value=name,
                current_value=None,
                delta_days=None,
                type="removed",
            )
        )

    return deviations


def compute_deviations(db: Session, baseline_id: int) -> list[schemas.BaselineDeviationOut]:
    """Schedule-/Milestone-Abweichungen: vergleicht die eingefrorenen Datumsfelder mit dem
    aktuellen Live-Wert der referenzierten PlanPhase/Milestone (Master-MD Phase 18). Kein
    generischer Multi-Dimensions-GAP - das bleibt Phase 21 (GAP Engine). Seit P18.1
    Stabilization zusätzlich strukturelle PlanPhase-Added/-Removed-Erkennung, siehe
    _structural_plan_phase_deviations."""
    snapshot = db.get(models.BaselineSnapshot, baseline_id)
    structural = _structural_plan_phase_deviations(db, snapshot) if snapshot is not None else []
    removed_plan_phase_ids = {d.entity_id for d in structural if d.type == "removed"}

    entries = (
        db.query(models.BaselineEntry)
        .filter(models.BaselineEntry.baseline_id == baseline_id, models.BaselineEntry.field.in_(DEVIATION_FIELDS))
        .all()
    )
    deviations = []
    for entry in entries:
        # Eine bereits als "removed" markierte PlanPhase liefert keine zusätzlichen
        # Feld-Deltas mehr (z.B. "Start: 2024-01-01 -> -") - die eine strukturelle
        # "− Phase entfernt"-Zeile aus _structural_plan_phase_deviations genügt, sonst würde
        # dieselbe Löschung doppelt und widersprüchlich dargestellt.
        if entry.entity_type == "plan_phase" and entry.entity_id in removed_plan_phase_ids:
            continue
        model = entity_links.model_for(entry.entity_type)
        if model is None:
            continue
        row = db.get(model, entry.entity_id)
        current_raw = getattr(row, entry.field, None) if row is not None else None
        # P11: current_raw ist für numerische Felder (plan_fte) ein float, BaselineDeviationOut
        # erwartet aber str | None wie bei den Datumsfeldern (entry.value ist bereits str) -
        # konsistent stringifizieren statt den rohen Typ durchzureichen.
        current_value = str(current_raw) if current_raw is not None else None
        baseline_date = _parse_date(entry.value)
        current_date = _parse_date(current_value)
        delta_days = (current_date - baseline_date).days if baseline_date and current_date else None
        summary = entity_links.entity_summary(db, entry.entity_type, entry.entity_id)
        deviations.append(
            schemas.BaselineDeviationOut(
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                label=summary["label"] if summary else None,
                field=entry.field,
                baseline_value=entry.value,
                current_value=current_value,
                delta_days=delta_days,
                type="changed",
            )
        )

    deviations.extend(structural)
    return deviations
