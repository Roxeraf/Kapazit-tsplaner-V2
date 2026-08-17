"""Real Capacity (Phase 20, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 20).
Grundformel: Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity.
Personenbezogen, unabhängig von einem einzelnen Projekt. Folgt demselben CRUD-Muster wie
routers/capacity.py (Phase 19)."""

import calendar as calendar_module
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..constants import VOLLZEIT_WOCHENSTUNDEN, parse_period
from ..database import get_db

router = APIRouter(tags=["real-capacity"])


def _get_person_or_404(db: Session, person_id: int) -> models.Person:
    person = db.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")
    return person


def _get_calendar_or_404(db: Session, calendar_id: int) -> models.CapacityCalendar:
    calendar = db.get(models.CapacityCalendar, calendar_id)
    if calendar is None:
        raise HTTPException(status_code=404, detail="Kapazitätskalender nicht gefunden")
    return calendar


# ---------------------------------------------------------------------------
# CapacityCalendar & Holiday
# ---------------------------------------------------------------------------


@router.get("/capacity-calendars", response_model=list[schemas.CapacityCalendarOut])
def list_capacity_calendars(db: Session = Depends(get_db)):
    return db.query(models.CapacityCalendar).order_by(models.CapacityCalendar.name).all()


@router.post("/capacity-calendars", response_model=schemas.CapacityCalendarOut, status_code=201)
def create_capacity_calendar(payload: schemas.CapacityCalendarCreate, db: Session = Depends(get_db)):
    existing = db.query(models.CapacityCalendar).filter(models.CapacityCalendar.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Kapazitätskalender mit diesem Namen existiert bereits")
    calendar = models.CapacityCalendar(**payload.model_dump())
    db.add(calendar)
    db.commit()
    db.refresh(calendar)
    return calendar


@router.delete("/capacity-calendars/{calendar_id}", status_code=204)
def delete_capacity_calendar(calendar_id: int, db: Session = Depends(get_db)):
    _get_calendar_or_404(db, calendar_id)
    db.query(models.Holiday).filter(models.Holiday.capacity_calendar_id == calendar_id).delete()
    # WorkingTime-Zeiträume verlieren nur die Kalenderzuordnung, bleiben aber bestehen.
    db.query(models.WorkingTime).filter(models.WorkingTime.capacity_calendar_id == calendar_id).update(
        {"capacity_calendar_id": None}
    )
    db.query(models.CapacityCalendar).filter(models.CapacityCalendar.id == calendar_id).delete()
    db.commit()


@router.get("/capacity-calendars/{calendar_id}/holidays", response_model=list[schemas.HolidayOut])
def list_holidays(calendar_id: int, db: Session = Depends(get_db)):
    _get_calendar_or_404(db, calendar_id)
    return (
        db.query(models.Holiday)
        .filter(models.Holiday.capacity_calendar_id == calendar_id)
        .order_by(models.Holiday.date)
        .all()
    )


@router.post("/capacity-calendars/{calendar_id}/holidays", response_model=schemas.HolidayOut, status_code=201)
def create_holiday(calendar_id: int, payload: schemas.HolidayCreate, db: Session = Depends(get_db)):
    _get_calendar_or_404(db, calendar_id)
    existing = (
        db.query(models.Holiday)
        .filter(models.Holiday.capacity_calendar_id == calendar_id, models.Holiday.date == payload.date)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Feiertag an diesem Datum existiert in diesem Kalender bereits")
    holiday = models.Holiday(capacity_calendar_id=calendar_id, date=payload.date, name=payload.name)
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    holiday = db.get(models.Holiday, holiday_id)
    if holiday is None:
        raise HTTPException(status_code=404, detail="Feiertag nicht gefunden")
    db.delete(holiday)
    db.commit()


# ---------------------------------------------------------------------------
# WorkingTime
# ---------------------------------------------------------------------------


def _get_working_time_or_404(db: Session, working_time_id: int) -> models.WorkingTime:
    wt = db.get(models.WorkingTime, working_time_id)
    if wt is None:
        raise HTTPException(status_code=404, detail="Arbeitszeit-Zeitraum nicht gefunden")
    return wt


@router.get("/people/{person_id}/working-times", response_model=list[schemas.WorkingTimeOut])
def list_working_times(person_id: int, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    return (
        db.query(models.WorkingTime)
        .filter(models.WorkingTime.person_id == person_id)
        .order_by(models.WorkingTime.valid_from)
        .all()
    )


@router.post("/people/{person_id}/working-times", response_model=schemas.WorkingTimeOut, status_code=201)
def create_working_time(person_id: int, payload: schemas.WorkingTimeCreate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    if payload.capacity_calendar_id is not None:
        _get_calendar_or_404(db, payload.capacity_calendar_id)
    working_time = models.WorkingTime(person_id=person_id, **payload.model_dump())
    db.add(working_time)
    db.commit()
    db.refresh(working_time)
    return working_time


@router.put("/working-times/{working_time_id}", response_model=schemas.WorkingTimeOut)
def update_working_time(working_time_id: int, payload: schemas.WorkingTimeUpdate, db: Session = Depends(get_db)):
    working_time = _get_working_time_or_404(db, working_time_id)
    changes = payload.model_dump(exclude_unset=True)
    if "capacity_calendar_id" in changes and changes["capacity_calendar_id"] is not None:
        _get_calendar_or_404(db, changes["capacity_calendar_id"])
    for field, value in changes.items():
        setattr(working_time, field, value)
    db.commit()
    db.refresh(working_time)
    return working_time


@router.delete("/working-times/{working_time_id}", status_code=204)
def delete_working_time(working_time_id: int, db: Session = Depends(get_db)):
    _get_working_time_or_404(db, working_time_id)
    db.query(models.WorkingTime).filter(models.WorkingTime.id == working_time_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Absence
# ---------------------------------------------------------------------------


def _get_absence_or_404(db: Session, absence_id: int) -> models.Absence:
    absence = db.get(models.Absence, absence_id)
    if absence is None:
        raise HTTPException(status_code=404, detail="Abwesenheit nicht gefunden")
    return absence


@router.get("/people/{person_id}/absences", response_model=list[schemas.AbsenceOut])
def list_absences(person_id: int, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    return (
        db.query(models.Absence).filter(models.Absence.person_id == person_id).order_by(models.Absence.start_date).all()
    )


@router.post("/people/{person_id}/absences", response_model=schemas.AbsenceOut, status_code=201)
def create_absence(person_id: int, payload: schemas.AbsenceCreate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    absence = models.Absence(person_id=person_id, **payload.model_dump())
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


@router.put("/absences/{absence_id}", response_model=schemas.AbsenceOut)
def update_absence(absence_id: int, payload: schemas.AbsenceUpdate, db: Session = Depends(get_db)):
    absence = _get_absence_or_404(db, absence_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(absence, field, value)
    db.commit()
    db.refresh(absence)
    return absence


@router.delete("/absences/{absence_id}", status_code=204)
def delete_absence(absence_id: int, db: Session = Depends(get_db)):
    _get_absence_or_404(db, absence_id)
    db.query(models.Absence).filter(models.Absence.id == absence_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# InternalAllocation
# ---------------------------------------------------------------------------


def _get_internal_allocation_or_404(db: Session, allocation_id: int) -> models.InternalAllocation:
    allocation = db.get(models.InternalAllocation, allocation_id)
    if allocation is None:
        raise HTTPException(status_code=404, detail="Interne Allokation nicht gefunden")
    return allocation


@router.get("/people/{person_id}/internal-allocations", response_model=list[schemas.InternalAllocationOut])
def list_internal_allocations(person_id: int, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    return (
        db.query(models.InternalAllocation)
        .filter(models.InternalAllocation.person_id == person_id)
        .order_by(models.InternalAllocation.period)
        .all()
    )


@router.post("/people/{person_id}/internal-allocations", response_model=schemas.InternalAllocationOut, status_code=201)
def create_internal_allocation(person_id: int, payload: schemas.InternalAllocationCreate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    allocation = models.InternalAllocation(person_id=person_id, **payload.model_dump())
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.put("/internal-allocations/{allocation_id}", response_model=schemas.InternalAllocationOut)
def update_internal_allocation(allocation_id: int, payload: schemas.InternalAllocationUpdate, db: Session = Depends(get_db)):
    allocation = _get_internal_allocation_or_404(db, allocation_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(allocation, field, value)
    db.commit()
    db.refresh(allocation)
    return allocation


@router.delete("/internal-allocations/{allocation_id}", status_code=204)
def delete_internal_allocation(allocation_id: int, db: Session = Depends(get_db)):
    _get_internal_allocation_or_404(db, allocation_id)
    db.query(models.InternalAllocation).filter(models.InternalAllocation.id == allocation_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Available Capacity (Grundformel, Master-MD Abschnitt 20)
# ---------------------------------------------------------------------------


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    _, days_in_month = calendar_module.monthrange(year, month)
    return date(year, month, 1), date(year, month, days_in_month)


def _weekdays_in_month(year: int, month: int) -> int:
    month_start, month_end = _month_bounds(year, month)
    return _count_weekdays_in_range(month_start, month_end)


def _count_weekdays_in_range(range_start: date, range_end: date) -> int:
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


@router.get("/people/{person_id}/capacity", response_model=schemas.PersonCapacityOut)
def get_person_capacity(person_id: int, period: str, db: Session = Depends(get_db)):
    """Verfügbare Kapazität einer Person in einer Periode (Grundformel Master-MD Abschnitt
    20). Nominale Wochenstunden kommen aus dem für die Periode gültigen WorkingTime-Eintrag,
    ersatzweise aus ResourceProfile.weekly_hours (Phase 14), falls kein WorkingTime gepflegt
    ist. Holiday/Absence werden über den Werktage-Anteil der Periode proportional in FTE
    umgerechnet, InternalAllocation wird direkt in FTE abgezogen."""
    _get_person_or_404(db, person_id)
    year, month = parse_period(period)
    month_start, month_end = _month_bounds(year, month)
    gross_weekdays = _weekdays_in_month(year, month)

    working_time = _current_working_time(db, person_id, month_start, month_end)
    if working_time is not None:
        weekly_hours = working_time.weekly_hours
        calendar_id = working_time.capacity_calendar_id
    else:
        profile = (
            db.query(models.ResourceProfile).filter(models.ResourceProfile.person_id == person_id).first()
        )
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail="Keine Kapazitätsdaten (WorkingTime oder ResourceProfile) für diese Person hinterlegt",
            )
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
        absence_days += _count_weekdays_in_range(overlap_start, overlap_end)

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
