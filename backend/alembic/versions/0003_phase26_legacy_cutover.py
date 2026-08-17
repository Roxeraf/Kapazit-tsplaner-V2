"""phase26.9: Legacy Cutover - Gantt/FTE-Grid und TeamMember/Assignment entfernen, MIT Datenkonvertierung.

Revision ID: 0003_phase26_legacy_cutover
Revises: 0002_align_project_nullable
Create Date: 2026-08-18 00:05:00.000000

Nutzerentscheidung Welle 2 (siehe CONCEPT.md Abschnitt 11 Punkt 26 und Abschnitt 12.1
Migrations-Policy Nr. 3): PlanPhase/Milestone werden die führende Planungswahrheit, das
Gantt/FTE-Grid und TeamMember/Assignment fallen. Anders als der historische erste
Cutover-Versuch (ehemalige Migration 0013, seit dem Squash Geschichte) löscht diese
Migration die Legacy-Tabellen NUR NACH strukturierter Datenkonvertierung:

1. Gantt-Zellen (gantt_phases/project_gantt_phases) -> PlanPhase/Milestone:
   - Aufeinanderfolgende Monate mit gleichem Phasencode (= eine Laufzeit) werden zu EINER
     PlanPhase mit forecast_start/forecast_end (Monatsgrenzen), phase_type =
     PHASE_LABELS[code] ("p" -> "Pflichtenheft" usw.), status="geplant".
   - Der Phasencode "?" (Meilenstein) wird je Vorkommen zu einem Milestone mit
     forecast_date (Monatsende des Vorkommens), status="geplant".
   - Teilprojekt-Zugehörigkeit bleibt erhalten: PlanPhase.subproject_id /
     Milestone.subproject_id.
2. FTE-Soll (fte_plan/project_fte_plan) -> ResourceDemand:
   - ResourceDemand kennt keine Teilprojekt-Ebene -> je Projekt/Monat ein Demand mit der
     Fachlogik aus gap_analysis._soll_je_monat: Hat das Projekt Teilprojekte, zählt die
     Summe der Teilprojekt-FTEs des Monats, sonst der Projektwert.
   - Rolle = Default-Rolle "Allgemein" (wird angelegt, falls noch keine existiert),
     commitment_level = "TENTATIVE" (Modell-Default), period = Monat.
3. TeamMember -> Person/ResourceProfile (Best-Effort wie ehemalige Migration 0003):
   - Matching über jira_account_id (primär) bzw. display_name (case-insensitive/getrimmt);
     ohne Treffer neue Person (source=LOCAL, active=true). Jira-ID wird nachgezogen, falls
     noch nicht gesetzt. Team-Zugehörigkeit -> ResourceProfile.team_id.
4. Assignment -> ResourceDemand/ResourceAssignment:
   - Assignment kennt keine Periode -> je Projekt-Monat ein Demand (Rolle "Allgemein",
     fte = assignment.fte) plus ResourceAssignment der Person mit gleichem FTE.

Danach werden gelöscht: assignments, team_members, gantt_phases, fte_plan,
project_gantt_phases, project_fte_plan sowie projects.projektleiter (Freitext, seit
Phase 26.1 durch projektleiter_person_id abgelöst).

Downgrade stellt die Tabellen NUR strukturell wieder her (keine Datenwiederherstellung) -
analog zur Migrations-Policy (CONCEPT.md Abschnitt 12.1): Destruktive Migrationen sind nur
mit Vorab-Datenkonvertierung erlaubt, ein Downgrade gibt die Daten nicht zurück.
"""

from typing import Sequence, Union
import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect, text


revision: str = "0003_phase26_legacy_cutover"
down_revision: Union[str, Sequence[str], None] = "0002_align_project_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# PHASE_CODES <-> Labels (Duplikat von backend/app/constants.py - eine Migration darf keine
# App-Module importieren, die ihrerseits die engine binden).
_PHASE_LABELS = {
    "p": "Pflichtenheft",
    "k": "Konfiguration",
    "t": "Test",
    "s": "Schulung",
    "g": "GoLive",
    "?": "Meilenstein",
}
_MONAT_NAMEN = [
    "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _berechne_monate(start_monat: str, anzahl_monate: int) -> list[str]:
    """start_monat 'MM.YYYY' -> ['Apr 25', 'Mai 25', ...] (Duplikat constants.berechne_monate)."""
    monat_str, jahr_str = start_monat.split(".")
    monat_idx = int(monat_str) - 1
    jahr = int(jahr_str)
    monate = []
    for i in range(anzahl_monate):
        m = (monat_idx + i) % 12
        j = jahr + (monat_idx + i) // 12
        monate.append(f"{_MONAT_NAMEN[m]} {j % 100:02d}")
    return monate


def _parse_period(period: str) -> tuple[int, int]:
    """'Apr 26' -> (Jahr, Monat)."""
    name, jahr_str = period.split()
    return 2000 + int(jahr_str), _MONAT_NAMEN.index(name) + 1


def _monat_start(period: str) -> str:
    jahr, monat = _parse_period(period)
    return f"{jahr}-{monat:02d}-01"


def _monat_end(period: str) -> str:
    jahr, monat = _parse_period(period)
    if monat == 12:
        return f"{jahr}-12-31"
    return (datetime.date(jahr, monat + 1, 1) - datetime.timedelta(days=1)).isoformat()


def _project_monate(bind, project_id: int) -> list[str]:
    row = bind.execute(
        text("SELECT start_monat, anzahl_monate FROM projects WHERE id = :pid"),
        {"pid": project_id},
    ).fetchone()
    if row is None:
        return []
    return _berechne_monate(row[0], row[1])


def _table_exists(bind, name: str) -> bool:
    """Tabellen-Existenz im Zielschema - die Migration muss auch auf DBs laufen, deren
    Legacy-Tabellen bereits fehlen (z.B. nach abgebrochenen Vorgängern), ohne zu brechen.
    Nutzt die öffentliche inspect-API, die sowohl Engine als auch Connection akzeptiert."""
    return sa_inspect(bind).has_table(name)


def _gantt_rows(bind) -> list[tuple[int, int | None, str, str]]:
    """Alle Gantt-Zellen als (project_id, subproject_id|None, monat, phase_code),
    aus project_gantt_phases (Projekt-Ebene) und gantt_phases (Teilprojekt-Ebene)."""
    rows = []
    if _table_exists(bind, "gantt_phases"):
        for project_id, sp_id, monat, phase_code in bind.execute(
            text(
                "SELECT s.project_id, g.subproject_id, g.monat, g.phase_code"
                " FROM gantt_phases g JOIN subprojects s ON s.id = g.subproject_id"
            )
        ).fetchall():
            rows.append((project_id, sp_id, monat, phase_code))
    if _table_exists(bind, "project_gantt_phases"):
        for project_id, monat, phase_code in bind.execute(
            text("SELECT project_id, monat, phase_code FROM project_gantt_phases")
        ).fetchall():
            rows.append((project_id, None, monat, phase_code))
    return rows


def _gantt_to_planphase(bind, project_id: int, sp_id: int | None, phase_type: str,
                        fstart: str, fend: str) -> None:
    bind.execute(
        text(
            "INSERT INTO plan_phases (project_id, subproject_id, phase_type, baseline_start,"
            " baseline_end, forecast_start, forecast_end, actual_start, actual_end, status,"
            " progress, owner_person_id, owner_team_id, erstellt_am, aktualisiert_am)"
            " VALUES (:pid, :spid, :ptype, NULL, NULL, :fstart, :fend, NULL, NULL, 'geplant',"
            " NULL, NULL, NULL, :now, :now)"
        ),
        {
            "pid": project_id,
            "spid": sp_id,
            "ptype": phase_type,
            "fstart": fstart,
            "fend": fend,
            "now": _now(),
        },
    )


def _gantt_to_milestone(bind, project_id: int, sp_id: int | None, monat: str) -> None:
    bind.execute(
        text(
            "INSERT INTO milestones (project_id, subproject_id, name, baseline_date, forecast_date,"
            " actual_date, status, owner_person_id, owner_team_id, erstellt_am, aktualisiert_am)"
            " VALUES (:pid, :spid, :name, NULL, :fdate, NULL, 'geplant', NULL, NULL, :now, :now)"
        ),
        {
            "pid": project_id,
            "spid": sp_id,
            "name": f"Meilenstein {_monat_end(monat)}",
            "fdate": _monat_end(monat),
            "now": _now(),
        },
    )


def _convert_gantt(bind) -> None:
    """Gantt-Zellen -> PlanPhase/Milestone (siehe Modul-Docstring, Abschnitt 1)."""
    cells = _gantt_rows(bind)
    if not cells:
        return

    # Zellen sind je (Monatsindex, project, subproject) sortierbar; Monatsindizes kommen
    # aus der Projekt-Monatsliste, damit "aufeinanderfolgend" fachlich stimmt.
    projekt_monate: dict[int, list[str]] = {}

    def _monatsindex(project_id: int, monat: str) -> int | None:
        monate = projekt_monate.get(project_id)
        if monate is None:
            monate = _project_monate(bind, project_id)
            projekt_monate[project_id] = monate
        return monate.index(monat) if monat in monate else None

    for project_id, sp_id, monat, phase_code in cells:
        if phase_code == "?":
            _gantt_to_milestone(bind, project_id, sp_id, monat)
            continue
        idx = _monatsindex(project_id, monat)
        if idx is None:
            # Monat außerhalb des Planungszeitraums - als Einzelphase übernehmen statt
            # zu verwerfen (gleiche Semantik wie der Monat selbst, keine Datumsgrenze).
            _gantt_to_planphase(
                bind,
                project_id,
                sp_id,
                _PHASE_LABELS.get(phase_code, f"Phase {phase_code}"),
                _monat_start(monat),
                _monat_end(monat),
            )

    # Aufeinanderfolgende Monatsindizes je (project, subproject, phase_code) verdichten.
    runs: dict[tuple[int, int | None, str], list[int]] = {}
    for project_id, sp_id, monat, phase_code in cells:
        if phase_code == "?":
            continue
        idx = _monatsindex(project_id, monat)
        if idx is None:
            continue
        runs.setdefault((project_id, sp_id, phase_code), []).append(idx)

    for (project_id, sp_id, phase_code), indices in runs.items():
        indices = sorted(set(indices))
        gruppen: list[list[int]] = []
        for idx in indices:
            if gruppen and idx == gruppen[-1][-1] + 1:
                gruppen[-1].append(idx)
            else:
                gruppen.append([idx])
        for gruppe in gruppen:
            monate = projekt_monate[project_id]
            _gantt_to_planphase(
                bind,
                project_id,
                sp_id,
                _PHASE_LABELS.get(phase_code, f"Phase {phase_code}"),
                _monat_start(monate[gruppe[0]]),
                _monat_end(monate[gruppe[-1]]),
            )


def _default_role_id(bind) -> int:
    """ID der Default-ResourceRole ('Allgemein'); legt sie bei Bedarf an. Reine
    Legacy-Überführungshilfe - die eigentliche Rollenpflege läuft über routers/capacity.py,
    diese Migration erzeugt keine zweite Wahrheit."""
    row = bind.execute(text("SELECT id FROM resource_roles WHERE name = 'Allgemein'")).fetchone()
    if row:
        return row[0]
    bind.execute(
        text(
            "INSERT INTO resource_roles (name, description, active) VALUES"
            " ('Allgemein', 'Default-Rolle für Legacy-überführte Bedarfe (Migration 0003)', :active)"
        ),
        {"active": True},
    )
    row = bind.execute(text("SELECT id FROM resource_roles WHERE name = 'Allgemein'")).fetchone()
    if row is None:
        raise RuntimeError("Default-Ressourcenrolle 'Allgemein' konnte nicht angelegt werden")
    return row[0]


def _find_person(bind, jira_account_id: str | None, display_name: str) -> int | None:
    if jira_account_id:
        row = bind.execute(
            text("SELECT id FROM persons WHERE jira_account_id = :j"),
            {"j": jira_account_id},
        ).fetchone()
        if row:
            return row[0]
    row = bind.execute(
        text("SELECT id FROM persons WHERE LOWER(TRIM(display_name)) = LOWER(TRIM(:n))"),
        {"n": display_name},
    ).fetchone()
    return row[0] if row else None


def _ensure_person(bind, jira_account_id: str | None, display_name: str) -> int:
    """Person auflösen (Best-Effort: jira_account_id, dann Name) oder als LOCAL anlegen."""
    person_id = _find_person(bind, jira_account_id, display_name)
    if person_id is not None:
        if jira_account_id:
            bind.execute(
                text("UPDATE persons SET jira_account_id = :j WHERE id = :id AND jira_account_id IS NULL"),
                {"j": jira_account_id, "id": person_id},
            )
        return person_id
    bind.execute(
        text(
            "INSERT INTO persons (external_id, display_name, email, jira_account_id, source, active)"
            " VALUES (NULL, :n, NULL, :j, 'LOCAL', :active)"
        ),
        {"n": display_name, "j": jira_account_id, "active": True},
    )
    row = bind.execute(
        text("SELECT id FROM persons WHERE display_name = :n ORDER BY id DESC LIMIT 1"),
        {"n": display_name},
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Person '{display_name}' konnte nicht angelegt werden")
    return row[0]


def _convert_fte_to_demands(bind) -> None:
    """FTE-Soll (fte_plan/project_fte_plan) -> ResourceDemand (siehe Modul-Docstring, 2)."""
    if not _table_exists(bind, "fte_plan") and not _table_exists(bind, "project_fte_plan"):
        return
    role_id = None
    subproject_count = dict(bind.execute(text("SELECT project_id, COUNT(*) FROM subprojects GROUP BY project_id")).fetchall())
    project_ids = [r[0] for r in bind.execute(text("SELECT id FROM projects"))]
    for project_id in project_ids:
        monate = _project_monate(bind, project_id)
        if not monate:
            continue
        if subproject_count.get(project_id, 0) > 0:
            quelle = bind.execute(
                text(
                    "SELECT f.monat, SUM(f.wert_soll) FROM fte_plan f"
                    " JOIN subprojects s ON s.id = f.subproject_id"
                    " WHERE s.project_id = :pid GROUP BY f.monat"
                ),
                {"pid": project_id},
            ).fetchall()
        else:
            quelle = bind.execute(
                text(
                    "SELECT monat, SUM(wert_soll) FROM project_fte_plan"
                    " WHERE project_id = :pid GROUP BY monat"
                ),
                {"pid": project_id},
            ).fetchall()
        for monat, wert in quelle:
            if wert is None or wert == 0:
                continue
            if role_id is None:
                role_id = _default_role_id(bind)
            bind.execute(
                text(
                    "INSERT INTO resource_demands (project_id, plan_phase_id, resource_role_id, period,"
                    " fte, commitment_level, erstellt_am, aktualisiert_am)"
                    " VALUES (:pid, NULL, :rid, :monat, :ft, 'TENTATIVE', :now, :now)"
                ),
                {"pid": project_id, "rid": role_id, "monat": monat, "ft": float(wert), "now": _now()},
            )


def _convert_team_members(bind) -> None:
    """TeamMember -> Person/ResourceProfile (siehe Modul-Docstring, 3)."""
    if not _table_exists(bind, "team_members"):
        return
    rows = bind.execute(
        text("SELECT id, name, jira_account_id, wochenstunden, team_id FROM team_members ORDER BY id")
    ).fetchall()
    for member_id, name, jira_account_id, wochenstunden, team_id in rows:
        person_id = _ensure_person(bind, jira_account_id, name)
        exists = bind.execute(
            text("SELECT id FROM resource_profiles WHERE person_id = :pid"), {"pid": person_id}
        ).fetchone()
        if not exists:
            bind.execute(
                text(
                    "INSERT INTO resource_profiles (person_id, team_id, weekly_hours, capacity_relevant,"
                    " active) VALUES (:pid, :tid, :wh, :cr, :act)"
                ),
                {"pid": person_id, "tid": team_id, "wh": wochenstunden or 40, "cr": True, "act": True},
            )


def _convert_assignments(bind) -> None:
    """Assignment -> ResourceDemand/ResourceAssignment (siehe Modul-Docstring, 4)."""
    if not _table_exists(bind, "assignments"):
        return
    rows = bind.execute(
        text(
            "SELECT a.id, a.project_id, a.fte, tm.person_id, tm.name, tm.jira_account_id"
            " FROM assignments a LEFT JOIN team_members tm ON tm.id = a.team_member_id"
        )
    ).fetchall()
    if not rows:
        return
    role_id = _default_role_id(bind)
    for assignment_id, project_id, fte, person_id, name, jira_account_id in rows:
        person_id = person_id if person_id is not None else _ensure_person(bind, jira_account_id, name)
        for monat in _project_monate(bind, project_id):
            bind.execute(
                text(
                    "INSERT INTO resource_demands (project_id, plan_phase_id, resource_role_id, period,"
                    " fte, commitment_level, erstellt_am, aktualisiert_am)"
                    " VALUES (:pid, NULL, :rid, :monat, :ft, 'TENTATIVE', :now, :now)"
                ),
                {"pid": project_id, "rid": role_id, "monat": monat, "ft": float(fte), "now": _now()},
            )
            demand_id = (
                bind.execute(text("SELECT LAST_INSERT_ROWID()")).scalar()
                if bind.dialect.name == "sqlite"
                else bind.execute(
                    text("SELECT id FROM resource_demands ORDER BY id DESC LIMIT 1")
                ).fetchone()[0]
            )
            bind.execute(
                text(
                    "INSERT INTO resource_assignments (resource_demand_id, person_id, fte, erstellt_am,"
                    " aktualisiert_am) VALUES (:did, :pid, :f, :now, :now)"
                ),
                {"did": demand_id, "pid": person_id, "f": float(fte), "now": _now()},
            )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1) Gantt -> PlanPhase/Milestone (projekt- UND teilprojekt-Ebene)
    _convert_gantt(bind)
    # 2) FTE-Soll -> ResourceDemand (projektweite Monatssumme)
    _convert_fte_to_demands(bind)
    # 3) TeamMember -> Person/ResourceProfile
    _convert_team_members(bind)
    # 4) Assignment -> ResourceDemand/ResourceAssignment
    _convert_assignments(bind)

    # 5) Legacy-Tabellen entfernen (NACH der Konvertierung), Abhängigkeitsreihenfolge:
    #    assignments referenziert team_members/projects, daher zuerst. Existenzprüfung:
    #    auf DBs ohne diese Tabellen (Randfall, siehe _table_exists) sind die Drops No-Ops.
    for tabelle in ("assignments", "team_members", "gantt_phases", "fte_plan",
                    "project_gantt_phases", "project_fte_plan"):
        if _table_exists(bind, tabelle):
            op.drop_table(tabelle)

    with op.batch_alter_table("projects", schema=None) as batch_op:
        if "projektleiter" in {col["name"] for col in sa_inspect(bind).get_columns("projects")}:
            batch_op.drop_column("projektleiter")


def downgrade() -> None:
    """Downgrade schema. Rein strukturell - keine Datenwiederherstellung (siehe Docstring)."""
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("projektleiter", sa.String(length=200), nullable=True))

    op.create_table(
        "project_fte_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("wert_soll", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "monat"),
    )
    op.create_table(
        "project_gantt_phases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("phase_code", sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "monat", "phase_code"),
    )
    op.create_table(
        "fte_plan",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subproject_id", sa.Integer(), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("wert_soll", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["subproject_id"], ["subprojects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subproject_id", "monat"),
    )
    op.create_table(
        "gantt_phases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subproject_id", sa.Integer(), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("phase_code", sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(["subproject_id"], ["subprojects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subproject_id", "monat", "phase_code"),
    )
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("jira_account_id", sa.String(length=100), nullable=True),
        sa.Column("wochenstunden", sa.Float(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_member_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("fte", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["team_member_id"], ["team_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )