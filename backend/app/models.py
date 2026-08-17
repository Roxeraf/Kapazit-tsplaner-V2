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
    # Sortierposition der Kachel auf dem Portfolio-Dashboard (frei per Drag & Drop änderbar).
    reihenfolge: Mapped[int] = mapped_column(default=0)
    # Lifecycle-Status: aktiv/on_hold/abgeschlossen/archiviert (siehe schemas.ProjectStatus).
    status: Mapped[str] = mapped_column(String(20), default="aktiv")
    # Mapping zu Jira (Component oder Label des Jira-Projekts), siehe CONCEPT.md Abschnitt 4.
    # Auf Projekt- statt Teilprojekt-Ebene, da Teilprojekte nur die Feinplanung innerhalb
    # eines Projekts sind und kein eigenes Jira-Gegenstück haben.
    jira_component: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Jira-Projekt-Key, falls dieses Kapa-Projekt aus dem Jira-Projekt-Katalog (Abschnitt 10 in
    # CONCEPT.md) automatisch angelegt wurde — verhindert Doppelanlage beim erneuten Aktivieren.
    jira_project_key: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    # Projektleitung (freies Textfeld, wie `kunde` — kein FK, da es (noch) keinen
    # User-/Personen-Verzeichnis-Baustein im Repo gibt, siehe CONCEPT.md Abschnitt 10).
    projektleiter: Mapped[str | None] = mapped_column(String(200), nullable=True)

    subprojects: Mapped[list["Subproject"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Subproject.reihenfolge"
    )
    gantt_phases: Mapped[list["ProjectGanttPhase"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    fte_plan: Mapped[list["ProjectFtePlan"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectGanttPhase(Base):
    """Gantt-Phasen direkt am Projekt (Grundplanung; Teilprojekte sind optionale Feinplanung)."""

    __tablename__ = "project_gantt_phases"
    __table_args__ = (UniqueConstraint("project_id", "monat", "phase_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    monat: Mapped[str] = mapped_column(String(10))
    phase_code: Mapped[str] = mapped_column(String(1))

    project: Mapped["Project"] = relationship(back_populates="gantt_phases")


class ProjectFtePlan(Base):
    """FTE-Soll direkt am Projekt (Grundplanung; Teilprojekte sind optionale Feinplanung)."""

    __tablename__ = "project_fte_plan"
    __table_args__ = (UniqueConstraint("project_id", "monat"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    monat: Mapped[str] = mapped_column(String(10))
    wert_soll: Mapped[float] = mapped_column(Float, default=0)

    project: Mapped["Project"] = relationship(back_populates="fte_plan")


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
    """Verknüpft MA <-> Projekt mit einem FTE-Wert (nicht Prozent — direkt in derselben Einheit
    wie FTE-Soll/-Ist, siehe CONCEPT.md). Auf Projekt- statt Teilprojekt-Ebene, konsistent zur
    übrigen Projekt/Teilprojekt-Logik (Teilprojekte sind reine Feinplanung ohne eigene MA-Zuordnung)."""

    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_member_id: Mapped[int] = mapped_column(ForeignKey("team_members.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    fte: Mapped[float] = mapped_column(Float, default=0)

    team_member: Mapped["TeamMember"] = relationship(back_populates="assignments")
    project: Mapped["Project"] = relationship(back_populates="assignments")


class UnassignedJiraAuthor(Base):
    """Autoren aus Jira/Tempo-Worklogs ohne bekanntes Teammitglied (siehe jira_sync.sync_project).

    Wird bei jedem Sync ergänzt, damit auf der Team-Kapazität-Seite direkt sichtbar ist, wer
    schon gebucht hat, aber noch nicht als Teammitglied angelegt ist — inkl. per Jira aufgelöstem
    Klarnamen (Tempo-Worklogs liefern selbst nur die Account-ID, siehe tempo_client.py).
    """

    __tablename__ = "unassigned_jira_authors"

    jira_account_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))


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


class Comment(Base):
    """Kommentar an einer Projekt-/Teilprojekt-Phase(+Monat) oder allgemeine Notiz.

    subproject_id gesetzt = Kommentar gehört zu einem Teilprojekt statt zum Projekt selbst.
    monat/phase_code gesetzt = an eine konkrete Gantt-Zelle gebunden; sonst allgemeine Notiz.
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    subproject_id: Mapped[int | None] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    monat: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phase_code: Mapped[str | None] = mapped_column(String(1), nullable=True)
    text: Mapped[str] = mapped_column(String(2000))
    # 40 statt 30 Zeichen: datetime.isoformat() mit Mikrosekunden + UTC-Offset kann bis zu
    # 32 Zeichen lang werden (z.B. "2026-07-28T10:05:52.407714+00:00").
    erstellt_am: Mapped[str] = mapped_column(String(40))


class PlanHistory(Base):
    """Automatisches Änderungsprotokoll: Alt-/Neu-Wert je tatsächlich geänderter Zelle/Feld.

    Wird beim Speichern in den betroffenen PUT-Endpunkten (siehe routers/projects.py,
    _log_change) geschrieben, sobald sich ein Wert wirklich ändert. Der Alt-Wert des
    ältesten Eintrags je (project_id/subproject_id, bereich, monat, feld) gilt als
    Ursprungsplanung.
    """

    __tablename__ = "plan_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    subproject_id: Mapped[int | None] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    bereich: Mapped[str] = mapped_column(String(20))  # "phase" | "fte" | "stammdaten"
    monat: Mapped[str | None] = mapped_column(String(10), nullable=True)
    feld: Mapped[str] = mapped_column(String(50))  # z.B. Phasencode "p" oder "start_monat"
    alter_wert: Mapped[str | None] = mapped_column(String(500), nullable=True)
    neuer_wert: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 40 statt 30 Zeichen: datetime.isoformat() mit Mikrosekunden + UTC-Offset kann bis zu
    # 32 Zeichen lang werden (z.B. "2026-07-28T10:05:52.407714+00:00").
    geaendert_am: Mapped[str] = mapped_column(String(40))
    kommentar_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    # Gruppiert alle PlanHistory-Einträge eines Speichern-Klicks zu einer "Revision" für die
    # Historie-Ansicht (siehe HistoryTimeline.tsx) — bewusst getrennt von kommentar_id, da
    # kommentar_id die fachliche Begründung ist (optional) und batch_id rein technisch die
    # Gruppierung, damit auch Saves ohne Begründungstext gruppierbar bleiben. Wird clientseitig
    # pro Speichern-Klick per crypto.randomUUID() erzeugt (siehe ProjectPlanningTab.handleSave).
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Zentrale Dokumentenablage, Tags & generische Verknüpfungen (siehe CONCEPT.md
# Abschnitt 6a). Jede Datei, die irgendwo im Projekt hochgeladen wird, existiert
# physisch und als Document-Datensatz genau einmal — andere Bereiche (Notizen,
# Entscheidungen, Risiken, Meetingprotokolle) referenzieren sie nur über DocumentLink.
# ---------------------------------------------------------------------------


class Document(Base):
    """Zentrale Dokumentenablage eines Projekts. Wird unabhängig vom Entstehungsort (direkt
    im Dokumente-Tab oder als Anhang an eine Notiz/Entscheidung/Risiko/Meetingprotokoll)
    über denselben Upload-Endpoint angelegt — siehe routers/documents.py."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    dateiname: Mapped[str] = mapped_column(String(300))
    speicherpfad: Mapped[str] = mapped_column(String(500))  # relativ zu DOCUMENTS_DIR
    mimetype: Mapped[str | None] = mapped_column(String(120), nullable=True)
    groesse_bytes: Mapped[int] = mapped_column()
    hochgeladen_von: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hochgeladen_am: Mapped[str] = mapped_column(String(40))


class DocumentLink(Base):
    """Generische Verknüpfung Document <-> beliebige Entität (comment/decision/risk/
    meeting_minutes, später erweiterbar um z.B. task/milestone/revision/jira_issue) —
    entity_type/entity_id statt separater FK-Spalten je Entität, analog zu TagLink. Ein
    Dokument kann von mehreren Entitäten referenziert werden, ohne dass die Datei oder der
    Document-Datensatz dupliziert wird."""

    __tablename__ = "document_links"
    __table_args__ = (UniqueConstraint("document_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column()
    erstellt_am: Mapped[str] = mapped_column(String(40))


class TagCategory(Base):
    """Fachliche Gruppierung von Tags (z.B. THEMA/PROJEKTPHASE/STAKEHOLDER/STEUERUNG, siehe
    Kapazitätsplaner-v2-Zielarchitektur, CONCEPT.md Abschnitt 12). Rein additiv: bestehende
    Tags bleiben ohne Kategorie gültig (Tag.category_id ist nullable)."""

    __tablename__ = "tag_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Tag(Base):
    """Systemweit wiederverwendbares Tag (nicht projektgebunden)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("tag_categories.id"), nullable=True)


class TagLink(Base):
    """Verknüpfung Tag <-> beliebige Entität. Teilt sich das entity_type-Vokabular mit
    DocumentLink, zusätzlich "document" (Dokumente sind selbst taggbar, aber nie Ziel
    eines DocumentLink)."""

    __tablename__ = "tag_links"
    __table_args__ = (UniqueConstraint("tag_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column()


class EntityRelation(Base):
    """Explizite semantische Beziehung zwischen zwei beliebigen Entitäten (z.B. Decision
    `resulted_in` Task, Blocker `blocks` Milestone) - ergänzt die reinen Tag-Verknüpfungen
    um gerichtete, typisierte Relationen. Siehe Kapazitätsplaner-v2-Zielarchitektur,
    CONCEPT.md Abschnitt 12 (Knowledge Layer, Master-MD Abschnitt 45)."""

    __tablename__ = "entity_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", "relation_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_entity_type: Mapped[str] = mapped_column(String(30))
    source_entity_id: Mapped[int] = mapped_column()
    target_entity_type: Mapped[str] = mapped_column(String(30))
    target_entity_id: Mapped[int] = mapped_column()
    relation_type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(40))
    # Freitext/FK-Platzhalter - kein Person-Modell in diesem Durchgang (siehe CONCEPT.md
    # Abschnitt 12, Phase 14 der Zielarchitektur).
    created_by_person_id: Mapped[int | None] = mapped_column(nullable=True)


class Decision(Base):
    """Entscheidung im Projekt (Kommunikation-Tab)."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen/entschieden/verworfen
    entschieden_von: Mapped[str | None] = mapped_column(String(200), nullable=True)
    entschieden_am: Mapped[str | None] = mapped_column(String(10), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))


class Risk(Base):
    """Risiko-Register-Eintrag (Kommunikation-Tab)."""

    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    wahrscheinlichkeit: Mapped[str] = mapped_column(String(10), default="mittel")  # niedrig/mittel/hoch
    auswirkung: Mapped[str] = mapped_column(String(10), default="mittel")  # niedrig/mittel/hoch
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen/in_bearbeitung/geschlossen
    owner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    faellig_am: Mapped[str | None] = mapped_column(String(10), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class MeetingMinutes(Base):
    """Meetingprotokoll (Kommunikation-Tab)."""

    __tablename__ = "meeting_minutes"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    titel: Mapped[str] = mapped_column(String(200))
    datum: Mapped[str] = mapped_column(String(10))
    teilnehmer: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Freitext, kommasepariert
    text: Mapped[str] = mapped_column(String(5000))
    erstellt_am: Mapped[str] = mapped_column(String(40))


class Task(Base):
    """Aufgabe im Projekt (Kommunikation-Tab). Löst den MVP-Alias 'offene Aufgaben =
    offene Risiken + offene Entscheidungen' auf dem Übersicht-Tab ab, siehe CONCEPT.md
    Abschnitt 10."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    titel: Mapped[str] = mapped_column(String(200))
    beschreibung: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen/in_bearbeitung/erledigt
    # Freitext (wie Risk.owner) - kein FK auf TeamMember, da es kein Personen-/User-
    # Verzeichnis für Zuweisungen im Repo gibt (siehe CONCEPT.md Abschnitt 10).
    zustaendig: Mapped[str | None] = mapped_column(String(200), nullable=True)
    faellig_am: Mapped[str | None] = mapped_column(String(10), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))
