"""Available-Capacity-Berechnung (Phase 20, Grundformel Master-MD Abschnitt 20:
Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity). Aus
routers/real_capacity.py extrahiert, damit routers/gap_engine.py (Phase 21, Capacity Gap/
Utilization Gap) dieselbe Berechnung ohne Cross-Router-Import nutzen kann - analog zu
entity_links.py als gemeinsamem Modul für mehrere Router."""

import calendar as calendar_module
from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import models, schemas
from .constants import MONAT_NAMEN, VOLLZEIT_WOCHENSTUNDEN, parse_period


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    _, days_in_month = calendar_module.monthrange(year, month)
    return date(year, month, 1), date(year, month, days_in_month)


def _weekdays_in_month(year: int, month: int) -> int:
    month_start, month_end = _month_bounds(year, month)
    return count_weekdays_in_range(month_start, month_end)


def count_weekdays_in_range(range_start: date, range_end: date) -> int:
    if range_end < range_start:
        return 0
    count = 0
    current = range_start
    while current <= range_end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _current_working_time(db: Session, person_id: int, month_start: date, month_end: date) -> models.WorkingTime | None:
    rows = db.query(models.WorkingTime).filter(models.WorkingTime.person_id == person_id).all()
    for wt in rows:
        valid_from = date.fromisoformat(wt.valid_from)
        valid_to = date.fromisoformat(wt.valid_to) if wt.valid_to else None
        if valid_from <= month_end and (valid_to is None or valid_to >= month_start):
            return wt
    return None


def compute_person_capacity(db: Session, person_id: int, period: str) -> schemas.PersonCapacityOut | None:
    """Verfügbare Kapazität einer Person in einer Periode. Liefert None, wenn weder
    WorkingTime noch ResourceProfile für die Person hinterlegt ist (Aufrufer entscheidet, ob
    das ein 404 ist oder in einer Aggregation einfach übersprungen wird)."""
    year, month = parse_period(period)
    month_start, month_end = _month_bounds(year, month)
    gross_weekdays = _weekdays_in_month(year, month)

    working_time = _current_working_time(db, person_id, month_start, month_end)
    if working_time is not None:
        weekly_hours = working_time.weekly_hours
        calendar_id = working_time.capacity_calendar_id
    else:
        profile = db.query(models.ResourceProfile).filter(models.ResourceProfile.person_id == person_id).first()
        if profile is None:
            return None
        weekly_hours = profile.weekly_hours
        calendar_id = None

    nominal_fte = round(weekly_hours / VOLLZEIT_WOCHENSTUNDEN, 4)

    holiday_days = 0
    if calendar_id is not None:
        for holiday in db.query(models.Holiday).filter(models.Holiday.capacity_calendar_id == calendar_id).all():
            holiday_date = date.fromisoformat(holiday.date)
            if month_start <= holiday_date <= month_end and holiday_date.weekday() < 5:
                holiday_days += 1

    absence_days = 0
    for absence in db.query(models.Absence).filter(models.Absence.person_id == person_id).all():
        overlap_start = max(date.fromisoformat(absence.start_date), month_start)
        overlap_end = min(date.fromisoformat(absence.end_date), month_end)
        absence_days += count_weekdays_in_range(overlap_start, overlap_end)

    internal_fte = round(
        sum(
            a.fte
            for a in db.query(models.InternalAllocation)
            .filter(models.InternalAllocation.person_id == person_id, models.InternalAllocation.period == period)
            .all()
        ),
        4,
    )

    holiday_fte = round(nominal_fte * holiday_days / gross_weekdays, 4) if gross_weekdays else 0.0
    absence_fte = round(nominal_fte * absence_days / gross_weekdays, 4) if gross_weekdays else 0.0
    available_fte = round(nominal_fte - holiday_fte - absence_fte - internal_fte, 4)

    return schemas.PersonCapacityOut(
        person_id=person_id,
        period=period,
        nominal_fte=nominal_fte,
        holiday_fte=holiday_fte,
        absence_fte=absence_fte,
        internal_fte=internal_fte,
        available_fte=available_fte,
        working_days=gross_weekdays,
        holiday_days=holiday_days,
        absence_days=absence_days,
    )


def _period_for(year: int, month: int) -> str:
    return f"{MONAT_NAMEN[month - 1]} {year % 100:02d}"


def compute_person_capacity_for_range(
    db: Session, person_id: int, range_start: date, range_end: date
) -> schemas.PersonCapacityRangeOut | None:
    """Bereichsbasierte Erweiterung von compute_person_capacity (P18/B-4, CONCEPT.md
    Abschnitt 6b.5/6b.11) - für die Available-Capacity-Prüfung über einen ganzen
    PlanPhase-Zeitraum (nicht nur einen einzelnen Monats-`period`-Bucket). Minimal-invasiv:
    KEINE neue Holiday-/Absence-/InternalAllocation-Query - jeder überlappte Kalendermonat
    ruft compute_person_capacity() unverändert auf und gewichtet dessen Ergebnis nur mit dem
    Werktage-Anteil des Bereichs an diesem Monat (identische Konvention wie
    phase_metrics_calc/monatliche Verteilung: werktage-anteilig, kein Feiertagsabzug, BD-4).
    Liefert None, wenn range_end < range_start oder kein überlappter Monat ein Profil für die
    Person liefert (kein WorkingTime/ResourceProfile in diesem gesamten Zeitraum)."""
    total_weekdays = count_weekdays_in_range(range_start, range_end)
    if total_weekdays == 0:
        return None

    acc_nominal = acc_holiday = acc_absence = acc_internal = 0.0
    any_month_found = False

    current_month_start = date(range_start.year, range_start.month, 1)
    while current_month_start <= range_end:
        year, month = current_month_start.year, current_month_start.month
        month_start, month_end = _month_bounds(year, month)
        overlap_start = max(month_start, range_start)
        overlap_end = min(month_end, range_end)
        weekdays_overlap = count_weekdays_in_range(overlap_start, overlap_end)
        weekdays_in_month = _weekdays_in_month(year, month)

        month_capacity = compute_person_capacity(db, person_id, _period_for(year, month))
        if month_capacity is not None and weekdays_in_month:
            weight = weekdays_overlap / weekdays_in_month
            acc_nominal += month_capacity.nominal_fte * weight
            acc_holiday += month_capacity.holiday_fte * weight
            acc_absence += month_capacity.absence_fte * weight
            acc_internal += month_capacity.internal_fte * weight
            any_month_found = True

        current_month_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    if not any_month_found:
        return None

    available = acc_nominal - acc_holiday - acc_absence - acc_internal
    return schemas.PersonCapacityRangeOut(
        person_id=person_id,
        range_start=range_start.isoformat(),
        range_end=range_end.isoformat(),
        nominal_fte=round(acc_nominal, 4),
        holiday_fte=round(acc_holiday, 4),
        absence_fte=round(acc_absence, 4),
        internal_fte=round(acc_internal, 4),
        available_fte=round(available, 4),
        working_days=total_weekdays,
    )


def compute_project_monthly_capacity(
    db: Session, project_id: int, periods: list[str] | None = None
) -> dict[str, float]:
    """Projektkapazität(Monat), AUSSCHLIESSLICH aus PlanPhase.plan_fte abgeleitet (P18/B-5,
    CONCEPT.md Abschnitt 6b.6) - EINE Berechnungsquelle statt der früheren
    ResourceDemand-Summe. Summe von monthly_distribution() über ALLE PlanPhases des Projekts,
    in Stunden. Kein explizites Leaf-Filtering nötig: eine Parent-Phase trägt nach dem B-3-
    Lifecycle (Abschnitt 6b.1a) immer plan_fte=None und liefert damit automatisch {} bei
    monthly_distribution() - sie trägt niemals selbst zur Summe bei, nur ihre Leaf-Nachfahren.
    periods=None liefert alle Monate, die von mindestens einer Phase berührt werden;
    andernfalls wird exakt für die übergebenen Perioden aufgefüllt (0.0 falls keine Phase
    diesen Monat berührt).

    Lokaler (Funktions-Body-)Import von phase_metrics_calc: vermeidet einen Circular Import,
    da phase_metrics_calc.py bereits von capacity_calc.py importiert (count_weekdays_in_range)
    - beide Module sind zum Aufrufzeitpunkt dieser Funktion längst vollständig geladen."""
    from . import phase_metrics_calc

    phases = db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all()
    totals: dict[str, float] = {}
    for phase in phases:
        distribution = phase_metrics_calc.monthly_distribution(
            phase.plan_fte, phase.forecast_start, phase.forecast_end
        )
        for period, hours in distribution.items():
            totals[period] = totals.get(period, 0.0) + hours
    totals = {period: round(hours, 2) for period, hours in totals.items()}
    if periods is None:
        return totals
    return {period: totals.get(period, 0.0) for period in periods}


def hours_to_fte_equivalent(hours: float, period: str) -> float:
    """Stunden -> FTE-Äquivalent für einen Monats-Bucket (Abschnitt 6a.6: "Stunden /
    (Werktage_Monat × 8)"), z.B. für die UI-Rückrechnung einer Projektkapazität-Zeile oder um
    eine PlanPhase-abgeleitete Kapazität mit dem bestehenden FTE-basierten
    CapacityGapOut/CockpitCapacity-Schema kompatibel zu halten (keine Schema-Änderung, nur
    Berechnung dahinter, B-5)."""
    year, month = parse_period(period)
    weekdays = _weekdays_in_month(year, month)
    if weekdays == 0:
        return 0.0
    hours_per_day = VOLLZEIT_WOCHENSTUNDEN / 5
    return round(hours / (weekdays * hours_per_day), 4)


def compute_portfolio_planphase_demand_fte(db: Session, period: str) -> float:
    """Portfolioweite Projektkapazität(Monat), ausschließlich aus PlanPhase.plan_fte
    abgeleitet (P18/B-5, Abschnitt 6b.6) - Summe über alle Projekte, als FTE-Äquivalent.
    Ersetzt die frühere ResourceDemand.fte-Summe als rollen-unabhängige Bedarfsseite von
    compute_capacity_gap(); eine rollen-gefilterte Abfrage (resource_role_id gesetzt) bleibt
    unverändert auf der optionalen Rollen-Aufschlüsselung (ResourceDemand), da Rolle keine
    Dimension der PlanPhase-Kapazität ist (Abschnitt 6b.4)."""
    total_hours = 0.0
    for (project_id,) in db.query(models.Project.id).all():
        distribution = compute_project_monthly_capacity(db, project_id, periods=[period])
        total_hours += distribution.get(period, 0.0)
    return hours_to_fte_equivalent(total_hours, period)


def compute_capacity_gap(db: Session, period: str, resource_role_id: int | None = None) -> schemas.CapacityGapOut:
    """Demand/Capacity Gap = Available Capacity - Resource Demand (Master-MD Abschnitt 22).
    Portfolioweit über alle kapazitätsrelevanten Personen, da es keine Person<->ResourceRole-
    Zuordnung im Datenmodell gibt (siehe CONCEPT.md Abschnitt 12.3) - resource_role_id
    filtert nur die Bedarfsseite, nicht die Kapazitätsseite. Aus routers/gap_engine.py (Phase
    21) extrahiert, damit routers/controlling.py (Phase 23) dieselbe Berechnung für die
    Capacity Heatmap über mehrere Perioden hinweg wiederverwenden kann.

    P18/B-5 (CONCEPT.md Abschnitt 6b.6): ohne Rollenfilter kommt die Bedarfsseite jetzt
    ausschließlich aus PlanPhase.plan_fte (compute_portfolio_planphase_demand_fte) statt aus
    einer ResourceDemand-Summe - es gibt keine Rollen-Dimension auf Projektkapazitätsebene
    mehr (Abschnitt 6b.4). Ein gesetzter resource_role_id-Filter bleibt bewusst auf der
    optionalen Rollen-Aufschlüsselung (ResourceDemand) - das ist die einzige Stelle, an der
    Rolleninformation überhaupt existiert, und wird durch B-5 nicht ersetzt, nur nicht mehr
    als Quelle der rollen-unabhängigen Gesamtkapazität verwendet."""
    if resource_role_id is not None:
        demand_fte = round(
            sum(
                d.fte
                for d in db.query(models.ResourceDemand)
                .filter(
                    models.ResourceDemand.period == period,
                    models.ResourceDemand.resource_role_id == resource_role_id,
                )
                .all()
            ),
            2,
        )
    else:
        demand_fte = round(compute_portfolio_planphase_demand_fte(db, period), 2)

    persons = (
        db.query(models.Person)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(models.Person.active.is_(True), models.ResourceProfile.capacity_relevant.is_(True))
        .all()
    )
    available_fte = 0.0
    considered = 0
    for person in persons:
        result = compute_person_capacity(db, person.id, period)
        if result is not None:
            available_fte += result.available_fte
            considered += 1

    return schemas.CapacityGapOut(
        period=period,
        resource_role_id=resource_role_id,
        demand_fte=demand_fte,
        available_fte=round(available_fte, 2),
        capacity_gap_fte=round(available_fte - demand_fte, 2),
        persons_considered=considered,
    )


def compute_portfolio_utilization(db: Session, period: str) -> list[schemas.PortfolioUtilizationEntry]:
    """Auslastungsgrad je Person: über ResourceAssignment zugeordnetes FTE einer Periode im
    Verhältnis zur individuellen Nominal-Kapazität (siehe compute_person_capacity). Ersetzt
    routers/team.py::compute_utilization (Phase 26.9 Legacy Cutover) - TeamMember/Assignment
    fallen weg, dieselbe kapazitätsrelevante Personenmenge wie compute_capacity_gap."""
    persons_with_profile = (
        db.query(models.Person, models.ResourceProfile)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(models.Person.active.is_(True), models.ResourceProfile.capacity_relevant.is_(True))
        .order_by(models.Person.display_name)
        .all()
    )
    teams_by_id = {t.id: t for t in db.query(models.Team).all()}

    result = []
    for person, profile in persons_with_profile:
        capacity = compute_person_capacity(db, person.id, period)
        kapazitaet_fte = capacity.nominal_fte if capacity is not None else 0.0
        zugeordnet_fte = round(
            sum(
                a.fte
                for a in db.query(models.ResourceAssignment)
                .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
                .filter(models.ResourceAssignment.person_id == person.id, models.ResourceDemand.period == period)
                .all()
            ),
            2,
        )
        auslastung_pct = round(zugeordnet_fte / kapazitaet_fte * 100, 1) if kapazitaet_fte > 0 else None
        team = teams_by_id.get(profile.team_id) if profile.team_id else None
        result.append(
            schemas.PortfolioUtilizationEntry(
                person_id=person.id,
                person_name=person.display_name,
                team_id=profile.team_id,
                team_name=team.name if team else None,
                jira_account_id=person.jira_account_id,
                weekly_hours=profile.weekly_hours,
                kapazitaet_fte=kapazitaet_fte,
                zugeordnet_fte=zugeordnet_fte,
                auslastung_pct=auslastung_pct,
            )
        )
    return result
