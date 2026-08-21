"""Rohmetriken für PlanPhase (P2, zentrale Calc-Layer für die Planungs- und
Kapazitätskonsolidierung). Liefert ausschließlich Rohmetriken - Zeitfortschritt,
Planstunden, Headline-vs-Aufschlüsselung-Reconciliation und Aufwandsverbrauch - ohne
Bewertung oder Ampel-Logik (folgt erst nach BD-3). Wiederverwendung bestehender Berechnungen
aus gap_calc.py/capacity_calc.py/constants.py nach dem in Phase 21 etablierten
Shared-Module-Muster (Router und Calc-Module importieren nur von gemeinsamen Modulen, nicht
voneinander). effort_consumption ist zurückgestellt bis das Tempo→PlanPhase-Mapping vorliegt
(BD-1)."""

from .capacity_calc import count_weekdays_in_range
from .constants import VOLLZEIT_WOCHENSTUNDEN
from .gap_calc import expected_progress_pct, parse_date


def time_progress(forecast_start: str | None, forecast_end: str | None) -> float | None:
    """Zeitfortschritt der Phase in Prozent (0-100) basierend auf forecast_start/forecast_end.
    Dünner Wrapper um gap_calc.expected_progress_pct - parst die ISO-Datumstrings und reicht
    sie durch, ohne die Berechnung zu duplizieren."""
    start = parse_date(forecast_start)
    end = parse_date(forecast_end)
    return expected_progress_pct(start, end)


def plan_hours(plan_fte: float | None, forecast_start: str | None, forecast_end: str | None) -> float | None:
    """Planstunden einer Phase = plan_fte × Werktage × (VOLLZEIT_WOCHENSTUNDEN / 5).
    Person-unabhängig (kein Feiertagsabzug, siehe BD-4). Werktage = Mon-Fri via
    capacity_calc.count_weekdays_in_range. Liefert None bei fehlendem plan_fte oder
    ungültigem Zeitraum (end < start); 0.0 bei plan_fte == 0."""
    if plan_fte is None:
        return None
    start = parse_date(forecast_start)
    end = parse_date(forecast_end)
    if start is None or end is None or end < start:
        return None
    weekdays = count_weekdays_in_range(start, end)
    hours_per_day = VOLLZEIT_WOCHENSTUNDEN / 5
    return round(plan_fte * weekdays * hours_per_day, 2)


def reconcile(plan_fte: float | None, breakdown_sum: float) -> dict:
    """Reconciliation Headline-FTE (PlanPhase.plan_fte) vs. Aufschlüsselungs-Summe
    (Summe ResourceDemand.fte dieser Phase). open_fte = plan_fte - breakdown_sum; positiv
    bedeutet offene/unzugeordnete Kapazität, negativ bedeutet Überdeckung/Drift. Beide
    Zustände sind gültig - dieses Modul bewertet nicht. Bei plan_fte is None kann open_fte
    nicht bestimmt werden (None)."""
    if plan_fte is None:
        return {"headline_fte": None, "breakdown_fte": breakdown_sum, "open_fte": None}
    return {
        "headline_fte": plan_fte,
        "breakdown_fte": breakdown_sum,
        "open_fte": round(plan_fte - breakdown_sum, 4),
    }


def assignment_summary(plan_fte: float | None, assigned_fte: float) -> dict:
    """Bedarf/Besetzt/Offen einer Leaf-PlanPhase (P18/B-4, CONCEPT.md Abschnitt 6b.10):
    plan_fte bleibt IMMER der Bedarf - eine direkte Personenzuordnung verändert ihn nie
    (Kernprinzip, Abschnitt 3). assigned_fte ist die Summe aller ResourceAssignment.fte über
    ALLE ResourceDemands dieser Phase (unabhängig von Rolle - sowohl über die interne
    Systemrolle "Ohne Rolle" als auch über eine optionale Rollen-Aufschlüsselung direkt
    zugeordnete Personen zählen zur Besetzung). open_fte = plan_fte - assigned_fte; negativ
    bedeutet Überbesetzung (bewusst nicht auf 0 gekappt, damit der Aufrufer den Unterschied
    zwischen "genau besetzt" und "überbesetzt" erkennen kann). Bei plan_fte is None (Phase
    noch ohne Kapazitätsbestätigung, z.B. gerade erst Parent gewesen) ist open_fte
    unbestimmt (None) - dieselbe Konvention wie reconcile() oben."""
    if plan_fte is None:
        return {"plan_fte": None, "assigned_fte": round(assigned_fte, 4), "open_fte": None}
    return {
        "plan_fte": plan_fte,
        "assigned_fte": round(assigned_fte, 4),
        "open_fte": round(plan_fte - assigned_fte, 4),
    }


def effort_consumption(ist_hours: float | None, plan_hours: float | None) -> float | None:
    """Aufwandsverbrauch = ist_hours / plan_hours × 100 (Prozent). ZURÜCKGESTELLT bis das
    Tempo→PlanPhase-Mapping vorliegt (BD-1) - aktuell gibt es keine Ist-Stunden-Quelle auf
    PlanPhase-Ebene. Liefert daher immer None; die Formel ist dokumentiert, damit ein
    folgendes Paket sie implementieren kann."""
    return None
