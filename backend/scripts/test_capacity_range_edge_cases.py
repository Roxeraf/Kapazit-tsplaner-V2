"""P18.1 Stabilization (CONCEPT.md Abschnitt 16.16, ehem. Audit-Defekt #6, Abschnitt 16.15):
gezielte Testabdeckung für capacity_calc.compute_person_capacity_for_range, die bisher nur den
Grundfall und die Werktage-Gewichtung über eine Monatsgrenze abdeckte (siehe
test_direct_assignment_and_capacity_range.py Schritt 1). Ruft die Funktion direkt (kein
Router-Umweg nötig, reine Berechnungslogik) gegen eine Wegwerf-SQLite-DB auf. Kein pytest im
Repo (siehe check_migrations.py als etabliertes Muster).

Prüft, ohne die fachliche Formel zu ändern (nur Testabdeckung, siehe Auftrag Abschnitt 3):

1. WorkingTime (expliziter Zeitreihen-Eintrag) wird korrekt verwendet.
2. ResourceProfile-Fallback (keine WorkingTime-Zeile) liefert dasselbe Ergebnis.
3. Holiday reduziert die verfügbare Kapazität um den Werktage-Anteil des Feiertags.
4. Absence reduziert die verfügbare Kapazität um den überlappten Werktage-Anteil.
5. InternalAllocation reduziert die verfügbare Kapazität um den vollen FTE-Wert des Monats.
6. Fehlendes ResourceProfile UND fehlende WorkingTime liefert None (keine Kapazitätsdaten).
7. Bestehende ResourceAssignments verändern die berechnete Kapazität NICHT (Demand ≠
   Assignment - Available Capacity ist unabhängig von bereits erfolgten Zuordnungen).
8. Überbuchte Person (Absence + InternalAllocation zusammen > nominal): available_fte wird
   negativ, nicht bei 0 gekappt.
9. Teilmonat (Range beginnt/endet mitten im Monat) gewichtet korrekt.
10. Mehrere Monate (3 Kalendermonate) akkumulieren korrekt.
11. Zero-Workday Edge Case (Range liegt ausschließlich auf einem Wochenende) liefert None.

Aufruf: python backend/scripts/test_capacity_range_edge_cases.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_capacity_range_edge_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from app.main import app  # noqa: E402,F401 - Import triggert db_bootstrap.run_migrations()
from app.database import SessionLocal, engine  # noqa: E402
from app import capacity_calc, models  # noqa: E402


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _close(msg: str = "") -> None:
    if msg:
        print(msg)


def main() -> None:
    print("1/11  WorkingTime wird korrekt verwendet ...")
    db = SessionLocal()
    p_wt = models.Person(display_name="WorkingTime-Person")
    db.add(p_wt)
    db.flush()
    db.add(models.WorkingTime(person_id=p_wt.id, valid_from="2020-01-01", weekly_hours=20))
    db.commit()
    p_wt_id = p_wt.id
    db.close()

    cap = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_wt_id, date(2026, 10, 1), date(2026, 10, 31))
    if cap is None:
        _fail("WorkingTime", "erwartet Ergebnis, bekam None")
    expected_nominal = round(20 / 40, 4)
    if abs(cap.nominal_fte - expected_nominal) > 0.0001 or cap.available_fte != cap.nominal_fte:
        _fail("WorkingTime", f"unerwartet: {cap}")

    print("2/11  ResourceProfile-Fallback ohne WorkingTime liefert dasselbe Muster ...")
    db = SessionLocal()
    p_profile = models.Person(display_name="Profile-Fallback-Person")
    db.add(p_profile)
    db.flush()
    db.add(models.ResourceProfile(person_id=p_profile.id, weekly_hours=20, capacity_relevant=True))
    db.commit()
    p_profile_id = p_profile.id
    db.close()

    cap = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_profile_id, date(2026, 10, 1), date(2026, 10, 31))
    if cap is None or abs(cap.nominal_fte - expected_nominal) > 0.0001:
        _fail("ResourceProfile-Fallback", f"unerwartet: {cap}")

    print("3/11  Holiday reduziert verfügbare Kapazität ...")
    db = SessionLocal()
    calendar = models.CapacityCalendar(name="DE-Test")
    db.add(calendar)
    db.flush()
    # 2026-10-03 (Sa) ist kein Werktag - bewusst ein Werktags-Feiertag wählen (2026-10-01, Do).
    db.add(models.Holiday(capacity_calendar_id=calendar.id, date="2026-10-01", name="Test-Feiertag"))
    p_holiday = models.Person(display_name="Holiday-Person")
    db.add(p_holiday)
    db.flush()
    db.add(
        models.WorkingTime(
            person_id=p_holiday.id, capacity_calendar_id=calendar.id, valid_from="2020-01-01", weekly_hours=40
        )
    )
    db.commit()
    p_holiday_id = p_holiday.id
    db.close()

    cap_with_holiday = capacity_calc.compute_person_capacity_for_range(
        SessionLocal(), p_holiday_id, date(2026, 10, 1), date(2026, 10, 31)
    )
    if cap_with_holiday is None or cap_with_holiday.holiday_fte <= 0:
        _fail("Holiday", f"erwartet holiday_fte > 0, bekam: {cap_with_holiday}")
    if cap_with_holiday.available_fte >= cap_with_holiday.nominal_fte:
        _fail("Holiday", f"available_fte hätte durch Feiertag reduziert werden müssen: {cap_with_holiday}")

    print("4/11  Absence reduziert verfügbare Kapazität (Teilüberlappung) ...")
    db = SessionLocal()
    p_absence = models.Person(display_name="Absence-Person")
    db.add(p_absence)
    db.flush()
    db.add(models.WorkingTime(person_id=p_absence.id, valid_from="2020-01-01", weekly_hours=40))
    # 5 Werktage Urlaub mitten im Monat.
    db.add(models.Absence(person_id=p_absence.id, start_date="2026-10-12", end_date="2026-10-16"))
    db.commit()
    p_absence_id = p_absence.id
    db.close()

    cap_absence = capacity_calc.compute_person_capacity_for_range(
        SessionLocal(), p_absence_id, date(2026, 10, 1), date(2026, 10, 31)
    )
    if cap_absence is None or cap_absence.absence_fte <= 0:
        _fail("Absence", f"erwartet absence_fte > 0, bekam: {cap_absence}")

    print("5/11  InternalAllocation reduziert verfügbare Kapazität ...")
    db = SessionLocal()
    p_internal = models.Person(display_name="Internal-Person")
    db.add(p_internal)
    db.flush()
    db.add(models.WorkingTime(person_id=p_internal.id, valid_from="2020-01-01", weekly_hours=40))
    db.add(models.InternalAllocation(person_id=p_internal.id, period="Okt 26", fte=0.3))
    db.commit()
    p_internal_id = p_internal.id
    db.close()

    cap_internal = capacity_calc.compute_person_capacity_for_range(
        SessionLocal(), p_internal_id, date(2026, 10, 1), date(2026, 10, 31)
    )
    if cap_internal is None or abs(cap_internal.internal_fte - 0.3) > 0.0001:
        _fail("InternalAllocation", f"erwartet internal_fte=0.3, bekam: {cap_internal}")
    if abs(cap_internal.available_fte - (cap_internal.nominal_fte - 0.3)) > 0.0001:
        _fail("InternalAllocation", f"available_fte nicht korrekt reduziert: {cap_internal}")

    print("6/11  Fehlendes ResourceProfile UND fehlende WorkingTime liefert None ...")
    db = SessionLocal()
    p_empty = models.Person(display_name="Ohne-Kapazitätsdaten")
    db.add(p_empty)
    db.commit()
    p_empty_id = p_empty.id
    db.close()

    cap_empty = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_empty_id, date(2026, 10, 1), date(2026, 10, 31))
    if cap_empty is not None:
        _fail("Fehlende Kapazitätsdaten", f"erwartet None, bekam: {cap_empty}")

    print("7/11  Bestehende ResourceAssignments verändern die Kapazität nicht ...")
    db = SessionLocal()
    project = models.Project(name="Capacity-Edge-Projekt", start_monat="10.2026", anzahl_monate=3, reihenfolge=0)
    db.add(project)
    db.flush()
    role = models.ResourceRole(name="Edge-Testrolle")
    db.add(role)
    db.flush()
    demand = models.ResourceDemand(
        project_id=project.id,
        plan_phase_id=None,
        resource_role_id=role.id,
        period="Okt 26",
        fte=0.5,
        commitment_level="TENTATIVE",
        erstellt_am="2026-01-01T00:00:00+00:00",
        aktualisiert_am="2026-01-01T00:00:00+00:00",
    )
    db.add(demand)
    db.flush()
    db.add(
        models.ResourceAssignment(
            resource_demand_id=demand.id,
            person_id=p_wt_id,
            fte=0.9,
            erstellt_am="2026-01-01T00:00:00+00:00",
            aktualisiert_am="2026-01-01T00:00:00+00:00",
        )
    )
    db.commit()
    db.close()

    cap_after_assignment = capacity_calc.compute_person_capacity_for_range(
        SessionLocal(), p_wt_id, date(2026, 10, 1), date(2026, 10, 31)
    )
    if cap_after_assignment is None or abs(cap_after_assignment.available_fte - cap.available_fte) > 0.0001:
        _fail(
            "Assignment-Unabhängigkeit",
            f"Available Capacity hätte trotz Assignment unverändert bleiben müssen: vorher={cap}, nachher={cap_after_assignment}",
        )

    print("8/11  Überbuchte Person: available_fte wird negativ (kein Clamping bei 0) ...")
    db = SessionLocal()
    p_over = models.Person(display_name="Überbuchte-Person")
    db.add(p_over)
    db.flush()
    db.add(models.WorkingTime(person_id=p_over.id, valid_from="2020-01-01", weekly_hours=10))  # nominal_fte = 0.25
    db.add(models.Absence(person_id=p_over.id, start_date="2026-10-01", end_date="2026-10-15"))
    db.add(models.InternalAllocation(person_id=p_over.id, period="Okt 26", fte=0.5))
    db.commit()
    p_over_id = p_over.id
    db.close()

    cap_over = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_over_id, date(2026, 10, 1), date(2026, 10, 31))
    if cap_over is None or cap_over.available_fte >= 0:
        _fail("Überbuchte Person", f"erwartet available_fte < 0, bekam: {cap_over}")

    print("9/11  Teilmonat (Range mitten im Monat) gewichtet korrekt ...")
    cap_partial = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_wt_id, date(2026, 10, 10), date(2026, 10, 20))
    if cap_partial is None:
        _fail("Teilmonat", "erwartet Ergebnis, bekam None")
    full_month_weekdays = capacity_calc._weekdays_in_month(2026, 10)
    partial_weekdays = capacity_calc.count_weekdays_in_range(date(2026, 10, 10), date(2026, 10, 20))
    expected_partial_nominal = round(expected_nominal * partial_weekdays / full_month_weekdays, 4)
    if abs(cap_partial.nominal_fte - expected_partial_nominal) > 0.0001:
        _fail("Teilmonat", f"erwartet nominal_fte={expected_partial_nominal}, bekam {cap_partial.nominal_fte}")
    if cap_partial.working_days != partial_weekdays:
        _fail("Teilmonat", f"working_days unerwartet: {cap_partial.working_days}")

    print("10/11  Mehrere Monate (3 Kalendermonate) akkumulieren korrekt ...")
    cap_multi = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_wt_id, date(2026, 10, 1), date(2026, 12, 31))
    if cap_multi is None:
        _fail("Mehrere Monate", "erwartet Ergebnis, bekam None")
    expected_multi_working_days = capacity_calc.count_weekdays_in_range(date(2026, 10, 1), date(2026, 12, 31))
    if cap_multi.working_days != expected_multi_working_days:
        _fail("Mehrere Monate", f"working_days unerwartet: {cap_multi.working_days}")
    if cap_multi.nominal_fte <= cap_partial.nominal_fte:
        _fail("Mehrere Monate", f"nominal_fte über 3 Monate sollte größer sein als über 11 Tage: {cap_multi}")

    print("11/11  Zero-Workday Edge Case (reines Wochenende) liefert None ...")
    # 2026-10-03/04 sind Samstag/Sonntag.
    cap_weekend = capacity_calc.compute_person_capacity_for_range(SessionLocal(), p_wt_id, date(2026, 10, 3), date(2026, 10, 4))
    if cap_weekend is not None:
        _fail("Zero-Workday", f"erwartet None für ein reines Wochenende, bekam: {cap_weekend}")

    print("OK — compute_person_capacity_for_range korrekt getestet für WorkingTime/"
          "ResourceProfile-Fallback/Holiday/Absence/InternalAllocation/fehlende Kapazitätsdaten/"
          "Assignment-Unabhängigkeit/Überbuchung (negativ statt gekappt)/Teilmonat/"
          "Mehrmonats-Akkumulation/Zero-Workday - keine Änderung der fachlichen Formel nötig.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
