from sqlalchemy import (
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Project(Base):
    """Entspricht dem Projektblatt-Kopf im Excel-Tool."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kunde: Mapped[str | None] = mapped_column(String(200), nullable=True)
    start_monat: Mapped[str] = mapped_column(String(7))  # "MM.YYYY"
    anzahl_monate: Mapped[int] = mapped_column(default=14)
    # Mapping zu Jira (Component oder Label des Jira-Projekts), siehe CONCEPT.md Abschnitt 4.
    # Auf Projekt- statt Teilprojekt-Ebene, da Teilprojekte nur die Feinplanung innerhalb
    # eines Projekts sind und kein eigenes Jira-Gegenstück haben.
    jira_component: Mapped[str | None] = mapped_column(String(200), nullable=True)

    subprojects: Mapped[list["Subproject"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Subproject.reihenfolge"
    )


class Subproject(Base):
    """Entspricht einem der 3 Teilprojekte je Projektblatt."""

    __tablename__ = "subprojects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(200))
    reihenfolge: Mapped[int] = mapped_column(default=0)

    project: Mapped["Project"] = relationship(back_populates="subprojects")
    gantt_phases: Mapped[list["GanttPhase"]] = relationship(
        back_populates="subproject", cascade="all, delete-orphan"
    )
    fte_plan: Mapped[list["FtePlan"]] = relationship(
        back_populates="subproject", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="subproject", cascade="all, delete-orphan"
    )


class GanttPhase(Base):
    """Entspricht einer belegten Gantt-Zelle. Mehrere Phasen pro Monat = mehrere Zeilen."""

    __tablename__ = "gantt_phases"
    __table_args__ = (UniqueConstraint("subproject_id", "monat", "phase_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subproject_id: Mapped[int] = mapped_column(ForeignKey("subprojects.id"))
    monat: Mapped[str] = mapped_column(String(10))  # z.B. "Apr 26"
    phase_code: Mapped[str] = mapped_column(String(1))  # p/k/t/g/?

    subproject: Mapped["Subproject"] = relationship(back_populates="gantt_phases")


class FtePlan(Base):
    """Entspricht den FTE-Zeilen (Soll) je Teilprojekt/Monat."""

    __tablename__ = "fte_plan"
    __table_args__ = (UniqueConstraint("subproject_id", "monat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subproject_id: Mapped[int] = mapped_column(ForeignKey("subprojects.id"))
    monat: Mapped[str] = mapped_column(String(10))
    wert_soll: Mapped[float] = mapped_column(Float, default=0)

    subproject: Mapped["Subproject"] = relationship(back_populates="fte_plan")


# ---------------------------------------------------------------------------
# Team-Kapazität (Phase 4) und Jira-Ist-Integration (Phase 2), siehe CONCEPT.md
# Abschnitt 9. GapSnapshot (Phase 3, Hochrechnung) bleibt vorbereitet, aber noch
# ohne Endpunkte.
# ---------------------------------------------------------------------------


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    members: Mapped[list["TeamMember"]] = relationship(back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    jira_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wochenstunden: Mapped[float] = mapped_column(Float, default=40)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    team: Mapped["Team | None"] = relationship(back_populates="members")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="team_member")


class Assignment(Base):
    """Verknüpft MA <-> Teilprojekt mit Anteil (%)."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_member_id: Mapped[int] = mapped_column(ForeignKey("team_members.id"))
    subproject_id: Mapped[int] = mapped_column(ForeignKey("subprojects.id"))
    anteil: Mapped[float] = mapped_column(Float, default=100)

    team_member: Mapped["TeamMember"] = relationship(back_populates="assignments")
    subproject: Mapped["Subproject"] = relationship(back_populates="assignments")


class JiraWorklogCache(Base):
    """Ist-Daten aus Jira (Worklog-Sync, Phase 2)."""

    __tablename__ = "jira_worklogs_cache"
    __table_args__ = (
        UniqueConstraint("jira_account_id", "jira_issue_key", "datum", name="uq_worklog_eintrag"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    jira_account_id: Mapped[str] = mapped_column(String(100))
    jira_issue_key: Mapped[str] = mapped_column(String(50))
    datum: Mapped[str] = mapped_column(String(10))  # ISO "YYYY-MM-DD"
    stunden: Mapped[float] = mapped_column(Float)
    # projects.id als String — welchem Projekt der Worklog zugeordnet wurde.
    projekt_mapping: Mapped[str | None] = mapped_column(String(200), nullable=True)


class JiraProjectCatalog(Base):
    """Verwaltung, welche Jira-Projekte im Kapazitätsplaner geplant werden (siehe /jira/projects).

    Rein lokale Zusatzinfo zu einem Jira-Projekt (Key kommt aus Jira) — legt fest, ob es in der
    Auswahl als "wird geplant" markiert ist und welchen Planungsstatus es hat.
    """

    __tablename__ = "jira_project_catalog"

    jira_project_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    relevant: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(20), default="aktiv")  # aktiv/on_hold/beendet


class GapSnapshot(Base):
    """Berechnete Soll-Ist-Gap-Werte inkl. Hochrechnung (Phase 3), historisiert."""

    __tablename__ = "gap_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    monat: Mapped[str] = mapped_column(String(10))
    soll: Mapped[float] = mapped_column(Float)
    ist: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    hochrechnung: Mapped[float | None] = mapped_column(Float, nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(30))
