"""Rohmetriken für PlanPhase (P2, zentrale Calc-Layer für die Planungs- und
Kapazitätskonsolidierung). Liefert ausschließlich Rohmetriken - Zeitfortschritt,
Planstunden, Headline-vs-Aufschlüsselung-Reconciliation und Aufwandsverbrauch - ohne
Bewertung oder Ampel-Logik (folgt erst nach BD-3). Wiederverwendung bestehender Berechnungen
aus gap_calc.py/capacity_calc.py/constants.py nach dem in Phase 21 etablierten
Shared-Module-Muster (Router und Calc-Module importieren nur von gemeinsamen Modulen, nicht
voneinander). Reine Formeln ohne DB-Zugriff - die Ist-Stunden-Ermittlung (Worklog-Resolver
+ Aggregation) lebt in worklog_resolver.py/worklog_actuals.py (P20.2/P20.4), diese Funktionen
hier nehmen ist_hours nur als bereits berechneten Wert entgegen (P20.4, BD-1 CLOSED, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 16)."""

import calendar
from datetime import date

from .capacity_calc import count_weekdays_in_range
from .constants import MONAT_NAMEN, VOLLZEIT_WOCHENSTUNDEN
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


def monthly_distribution(
    plan_fte: float | None, forecast_start: str | None, forecast_end: str | None
) -> dict[str, float]:
    """Werktage-anteilige Monatsverteilung der Planstunden einer Phase (P18/B-5, CONCEPT.md
    Abschnitt 6a.6/6b.6) - Periode im "Apr 26"-Format -> Stunden. KEIN 50/50-Split, KEIN
    Feiertagsabzug (identische Werktage-Konvention wie plan_hours() oben, BD-4). Leeres dict
    bei fehlendem plan_fte oder ungültigem Zeitraum (end < start) - konsistent mit
    plan_hours(), das in diesem Fall None liefert. Reine Aufteilung von plan_hours() auf die
    berührten Kalendermonate, keine zweite Stundenformel."""
    total_hours = plan_hours(plan_fte, forecast_start, forecast_end)
    if total_hours is None:
        return {}
    start = parse_date(forecast_start)
    end = parse_date(forecast_end)
    weekdays_total = count_weekdays_in_range(start, end)
    if weekdays_total == 0:
        return {}

    result: dict[str, float] = {}
    current_month_start = date(start.year, start.month, 1)
    while current_month_start <= end:
        year, month = current_month_start.year, current_month_start.month
        _, days_in_month = calendar.monthrange(year, month)
        month_end = date(year, month, days_in_month)
        overlap_start = max(start, current_month_start)
        overlap_end = min(end, month_end)
        weekdays_m = count_weekdays_in_range(overlap_start, overlap_end)
        if weekdays_m > 0:
            period = f"{MONAT_NAMEN[month - 1]} {year % 100:02d}"
            result[period] = round(total_hours * weekdays_m / weekdays_total, 2)
        current_month_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return result


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
    """Aufwandsverbrauch = ist_hours / plan_hours × 100 (Prozent, P20.4). None, wenn
    ist_hours oder plan_hours fehlt (keine Mapping-Konfiguration bzw. kein gültiger
    Zeitraum/plan_fte, Abschnitt 18/21 des Auftrags - "noch nicht zugeordnet" statt einer
    irreführenden 0%) oder wenn plan_hours 0 ist (Division durch Null vermieden)."""
    if ist_hours is None or plan_hours is None or plan_hours == 0:
        return None
    return round(ist_hours / plan_hours * 100, 2)


def remaining_plan_hours(ist_hours: float | None, plan_hours: float | None) -> float | None:
    """Verbleibender Planaufwand = max(plan_hours - ist_hours, 0) (P20.4, Abschnitt 23 des
    Auftrags). None, wenn ist_hours oder plan_hours fehlt."""
    if ist_hours is None or plan_hours is None:
        return None
    return round(max(plan_hours - ist_hours, 0), 2)


def overrun_hours(ist_hours: float | None, plan_hours: float | None) -> float | None:
    """Überverbrauch = ist_hours - plan_hours, nur wenn Ist > Plan (P20.4, Abschnitt 23 des
    Auftrags) - sonst 0.0 (kein negativer "Überverbrauch" bei Unterverbrauch, das zeigt
    remaining_plan_hours). None, wenn ist_hours oder plan_hours fehlt. Reine Subtraktion,
    keine Burn-Rate-/Forecast-Logik (Abschnitt 22)."""
    if ist_hours is None or plan_hours is None:
        return None
    return round(max(ist_hours - plan_hours, 0), 2)
