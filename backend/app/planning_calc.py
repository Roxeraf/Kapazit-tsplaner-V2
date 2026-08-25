"""PlanPhase-Hierarchie: reine Leaf-/Parent-Berechnungen (P18/B-3, CONCEPT.md Abschnitt
6b.1/6b.3/6b.6, P18_ARCHITECTURE_RECONCILIATION_PASS2.md Abschnitt 35.5 Paket B-3). Kein
neues Statusfeld - Leaf/Parent wird NICHT gespeichert, sondern hier query-seitig berechnet.
Eine Parent-Phase besitzt zu keinem Zeitpunkt eine operative eigene Kapazität (Abschnitt
6b.1a) - Zeitraum/Kapazität werden ausschließlich aus den (rekursiven) Leaf-Nachfahren
abgeleitet, nie aus einem eigenen Feld der Parent-Phase selbst."""

from sqlalchemy import exists
from sqlalchemy.orm import Session

from . import models

# Maximale Hierarchietiefe (BD-10, CLOSED): 3 Ebenen, z.B. Wareingang -> Schnittstellen ->
# WE-Anmeldung. Wird beim Anlegen/Verschieben einer Phase im Router validiert.
MAX_HIERARCHY_DEPTH = 3


def has_children(db: Session, plan_phase_id: int) -> bool:
    return bool(
        db.query(exists().where(models.PlanPhase.parent_phase_id == plan_phase_id)).scalar()
    )


def direct_children(db: Session, plan_phase_id: int) -> list[models.PlanPhase]:
    return (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.parent_phase_id == plan_phase_id)
        .order_by(models.PlanPhase.reihenfolge, models.PlanPhase.id)
        .all()
    )


def depth_of(db: Session, plan_phase_id: int) -> int:
    """1 = Top-Level, 2 = Kind einer Top-Level-Phase, 3 = Enkelkind (maximal erlaubte Tiefe).
    Wandert die parent_phase_id-Kette hoch; bricht bei einem Zyklus defensiv ab (sollte durch
    die Router-Guards nie erreichbar sein, aber diese Funktion darf nie in eine Endlosschleife
    laufen)."""
    depth = 1
    current = db.get(models.PlanPhase, plan_phase_id)
    seen: set[int] = {plan_phase_id}
    while current is not None and current.parent_phase_id is not None:
        if current.parent_phase_id in seen:
            break
        seen.add(current.parent_phase_id)
        current = db.get(models.PlanPhase, current.parent_phase_id)
        depth += 1
    return depth


def all_descendants(db: Session, plan_phase_id: int) -> list[models.PlanPhase]:
    """Alle Nachfahren (Parents UND Leafs), rekursiv - für Zyklenprüfung/Subtree-Delete/
    Impact-Analyse. Reihenfolge nicht garantiert."""
    children = direct_children(db, plan_phase_id)
    result: list[models.PlanPhase] = list(children)
    for child in children:
        result.extend(all_descendants(db, child.id))
    return result


def leaf_descendants(db: Session, plan_phase_id: int) -> list[models.PlanPhase]:
    """Alle Leaf-Nachfahren (rekursiv). Eine Phase ohne Kinder ist ihr eigener einziger
    Leaf-Nachfahre."""
    children = direct_children(db, plan_phase_id)
    if not children:
        phase = db.get(models.PlanPhase, plan_phase_id)
        return [phase] if phase is not None else []
    leaves: list[models.PlanPhase] = []
    for child in children:
        leaves.extend(leaf_descendants(db, child.id))
    return leaves


def subtree_max_depth(db: Session, plan_phase_id: int) -> int:
    """Größte absolute Tiefe (depth_of) innerhalb des aktuellen Teilbaums dieser Phase
    (inklusive sich selbst). Für die Depth-Validierung beim Reparenting nötig: eine Phase mit
    eigenen Kindern (z.B. eine Parent-Phase auf Ebene 2 mit einem Leaf-Kind auf Ebene 3) darf
    nicht einfach anhand ihrer EIGENEN neuen Tiefe geprüft werden - ihre Nachfahren würden bei
    einem zu tiefen Ziel sonst unbemerkt über MAX_HIERARCHY_DEPTH hinausrutschen."""
    ids = [plan_phase_id] + [d.id for d in all_descendants(db, plan_phase_id)]
    return max(depth_of(db, i) for i in ids)


def derive_parent_bounds(db: Session, plan_phase_id: int) -> tuple[str | None, str | None]:
    """MIN(forecast_start)/MAX(forecast_end) über alle Leaf-Nachfahren (Abschnitt 6b.3).
    (None, None), wenn kein Leaf-Nachfahre einen Zeitraum gesetzt hat."""
    leaves = leaf_descendants(db, plan_phase_id)
    starts = [leaf.forecast_start for leaf in leaves if leaf.forecast_start]
    ends = [leaf.forecast_end for leaf in leaves if leaf.forecast_end]
    return (min(starts) if starts else None, max(ends) if ends else None)


def derive_parent_capacity(db: Session, plan_phase_id: int) -> float | None:
    """SUM(plan_fte) über alle Leaf-Nachfahren (Abschnitt 6b.3/6b.6). None (nicht 0.0), wenn
    kein Leaf-Nachfahre einen plan_fte-Wert gesetzt hat - unterscheidet "noch keine Kapazität
    geplant" von "Kapazität ist 0"."""
    leaves = leaf_descendants(db, plan_phase_id)
    values = [leaf.plan_fte for leaf in leaves if leaf.plan_fte is not None]
    return round(sum(values), 4) if values else None


def derive_parent_commitment_bounds(db: Session, plan_phase_id: int) -> tuple[str | None, str | None]:
    """P20.5 (Abschnitt 35/36): MIN(commitment_start)/MAX(commitment_end) über alle Leaf-
    Nachfahren - kein eigenes, separat gepflegtes Parent-Commitment (Abschnitt 36: "kein
    zweites manuell gepflegtes Parent-System"), rein aus den Leaf-Commitments abgeleitet,
    analog zu derive_parent_bounds() für den aktuellen Plan. (None, None), wenn kein
    Leaf-Nachfahre bereits ein Commitment hat (Phase/Teilbaum noch nicht begonnen)."""
    leaves = leaf_descendants(db, plan_phase_id)
    starts = [leaf.commitment_start for leaf in leaves if leaf.commitment_start]
    ends = [leaf.commitment_end for leaf in leaves if leaf.commitment_end]
    return (min(starts) if starts else None, max(ends) if ends else None)


def derive_parent_actual_start(db: Session, plan_phase_id: int) -> str | None:
    """P20.5 (Abschnitt 35): frühester actual_start aller Leaf-Nachfahren. None, wenn noch
    kein Leaf-Nachfahre tatsächlich begonnen hat."""
    leaves = leaf_descendants(db, plan_phase_id)
    starts = [leaf.actual_start for leaf in leaves if leaf.actual_start]
    return min(starts) if starts else None


def derive_parent_actual_end(db: Session, plan_phase_id: int) -> str | None:
    """P20.5 (Abschnitt 35): spätester tatsächlicher Abschluss aller Leaf-Nachfahren, ABER
    NUR wenn ALLE relevanten (= mit gesetztem jira_label, also operativ konfigurierten)
    Leaf-Nachfahren bereits abgeschlossen sind (actual_end gesetzt) - eine Parent-Phase gilt
    nie als "fertig", solange auch nur eine ihrer Unterphasen noch offen ist. Leaf-Nachfahren
    ohne jira_label (noch nicht konfiguriert) blockieren den Parent-Abschluss nicht, tragen
    aber auch kein eigenes actual_end bei - "relevant" folgt hier bewusst derselben
    jira_label-Konvention wie leaf_ist_hours()/leaf_capacity_ist_hours()."""
    leaves = leaf_descendants(db, plan_phase_id)
    relevant = [leaf for leaf in leaves if leaf.jira_label is not None]
    if not relevant or any(leaf.actual_end is None for leaf in relevant):
        return None
    return max(leaf.actual_end for leaf in relevant)
