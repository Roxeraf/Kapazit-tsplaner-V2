"""Real Capacity (Phase 20, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 20).
Grundformel: Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity.
Personenbezogen, unabhängig von einem einzelnen Projekt. Folgt demselben CRUD-Muster wie
routers/capacity.py (Phase 19)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import capacity_calc, models, schemas
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


@router.put("/capacity-calendars/{calendar_id}", response_model=schemas.CapacityCalendarOut)
def update_capacity_calendar(
    calendar_id: int, payload: schemas.CapacityCalendarUpdate, db: Session = Depends(get_db)
):
    calendar = _get_calendar_or_404(db, calendar_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(calendar, field, value)
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
# Available Capacity (Grundformel, Master-MD Abschnitt 20) - Berechnung in ../capacity_calc.py,
# gemeinsam genutzt mit routers/gap_engine.py (Phase 21, Capacity Gap/Utilization Gap).
# ---------------------------------------------------------------------------


@router.get("/people/{person_id}/capacity", response_model=schemas.PersonCapacityOut)
def get_person_capacity(person_id: int, period: str, db: Session = Depends(get_db)):
    """Verfügbare Kapazität einer Person in einer Periode (Grundformel Master-MD Abschnitt
    20). Nominale Wochenstunden kommen aus dem für die Periode gültigen WorkingTime-Eintrag,
    ersatzweise aus ResourceProfile.weekly_hours (Phase 14), falls kein WorkingTime gepflegt
    ist. Holiday/Absence werden über den Werktage-Anteil der Periode proportional in FTE
    umgerechnet, InternalAllocation wird direkt in FTE abgezogen."""
    _get_person_or_404(db, person_id)
    result = capacity_calc.compute_person_capacity(db, person_id, period)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Keine Kapazitätsdaten (WorkingTime oder ResourceProfile) für diese Person hinterlegt"
        )
    return result
