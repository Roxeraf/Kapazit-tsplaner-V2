"""Available-Capacity-Berechnung (Phase 20, Grundformel Master-MD Abschnitt 20:
Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity). Aus
routers/real_capacity.py extrahiert, damit routers/gap_engine.py (Phase 21, Capacity Gap/
Utilization Gap) dieselbe Berechnung ohne Cross-Router-Import nutzen kann - analog zu
entity_links.py als gemeinsamem Modul für mehrere Router."""

import calendar as calendar_module
from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import models, schemas
from .constants import VOLLZEIT_WOCHENSTUNDEN, parse_period


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


def compute_capacity_gap(db: Session, period: str, resource_role_id: int | None = None) -> schemas.CapacityGapOut:
    """Demand/Capacity Gap = Available Capacity - Resource Demand (Master-MD Abschnitt 22).
    Portfolioweit über alle kapazitätsrelevanten Personen, da es keine Person<->ResourceRole-
    Zuordnung im Datenmodell gibt (siehe CONCEPT.md Abschnitt 12.3) - resource_role_id
    filtert nur die Bedarfsseite, nicht die Kapazitätsseite. Aus routers/gap_engine.py (Phase
    21) extrahiert, damit routers/controlling.py (Phase 23) dieselbe Berechnung für die
    Capacity Heatmap über mehrere Perioden hinweg wiederverwenden kann."""
    demand_query = db.query(models.ResourceDemand).filter(models.ResourceDemand.period == period)
    if resource_role_id is not None:
        demand_query = demand_query.filter(models.ResourceDemand.resource_role_id == resource_role_id)
    demand_fte = round(sum(d.fte for d in demand_query.all()), 2)

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
