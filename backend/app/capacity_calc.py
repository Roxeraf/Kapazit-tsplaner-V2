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
