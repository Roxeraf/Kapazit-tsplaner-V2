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
from datetime import date, timedelta

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


# ---------------------------------------------------------------------------
# P20.5 - Terminsteuerung (Start Commitment vs. Current Plan vs. Actual, siehe
# P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 28-32). Reine Datumsarithmetik, keine
# DB-/Uhrzeit-Zugriffe hier - der Aufrufer (routers/planning.py) übergibt bereits ermittelte
# ISO-Datumsstrings (inkl. "heute"). Arbeitstage wiederverwendet ausschließlich die bestehende
# capacity_calc.count_weekdays_in_range (Auftrag Abschnitt 28/60: "keine neue Kalenderengine").
# ---------------------------------------------------------------------------


def workday_delta(earlier: str | None, later: str | None) -> int | None:
    """Signierte Arbeitstage zwischen zwei ISO-Daten (P20.5, Abschnitt 28). Positiv, wenn
    `later` NACH `earlier` liegt (Verspätung/Verschiebung nach hinten), negativ wenn `later`
    VOR `earlier` liegt, 0 bei Gleichheit. None, wenn eines der beiden Daten fehlt oder
    ungültig ist - kein erfundener Nullwert bei fehlender Referenz."""
    a = parse_date(earlier)
    b = parse_date(later)
    if a is None or b is None:
        return None
    if b == a:
        return 0
    if b > a:
        return count_weekdays_in_range(a + timedelta(days=1), b)
    return -count_weekdays_in_range(b + timedelta(days=1), a)


def duration_workdays(start: str | None, end: str | None) -> int | None:
    """Arbeitstage zwischen zwei ISO-Daten inkl. beider Endpunkte (P20.5, Abschnitt 32) -
    dieselbe Mon-Fri-Konvention wie plan_hours() oben. None bei fehlendem/ungültigem Zeitraum
    (end < start)."""
    s = parse_date(start)
    e = parse_date(end)
    if s is None or e is None or e < s:
        return None
    return count_weekdays_in_range(s, e)


def schedule_variance(
    commitment_start: str | None,
    commitment_end: str | None,
    current_end: str | None,
    actual_start: str | None,
    actual_end: str | None,
) -> dict:
    """Terminabweichungen in Arbeitstagen (P20.5, Abschnitt 28/31): `start_delay_workdays` =
    actual_start - commitment_start (positiv = später gestartet als bei Phasenbeginn
    geplant). `end_delay_workdays` = actual_end - commitment_end (nur befüllt, sobald die
    Phase tatsächlich abgeschlossen ist - actual_end gesetzt). `plan_shift_workdays` =
    current_end - commitment_end (Abschnitt 31 - wie weit hat sich der AKTUELLE Plan bereits
    vom Start-Commitment entfernt, unabhängig vom tatsächlichen Abschluss). Jeder Wert bleibt
    None, wenn seine Eingaben fehlen (kein Commitment/keine Actuals) statt einer erfundenen 0."""
    return {
        "start_delay_workdays": workday_delta(commitment_start, actual_start),
        "end_delay_workdays": workday_delta(commitment_end, actual_end),
        "plan_shift_workdays": workday_delta(commitment_end, current_end),
    }


def workdays_overdue(commitment_end: str | None, today: str, actual_end: str | None) -> int | None:
    """Arbeitstage, die "heute" bereits über commitment_end liegt, solange die Phase noch
    nicht abgeschlossen ist (P20.5, Abschnitt 30) - KEINE Ampel/Bewertung, reine
    Terminabweichung (Abschnitt 30, letzter Satz: "Das ist KEINE Health-Ampel"). None, wenn
    die Phase bereits abgeschlossen ist (actual_end gesetzt), kein commitment_end existiert,
    oder heute noch nicht über commitment_end hinaus ist."""
    if actual_end is not None or commitment_end is None:
        return None
    delta = workday_delta(commitment_end, today)
    return delta if delta is not None and delta > 0 else None
