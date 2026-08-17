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
    # Projektleitung (freies Textfeld, wie `kunde`). Bleibt bestehen (Abwärtskompatibilität) -
    # projektleiter_person_id ist die additive, nullable Bridge auf das Personen-Verzeichnis
    # (Phase 14, siehe CONCEPT.md Abschnitt 12), per Best-Effort-Mapping befüllt.
    projektleiter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    projektleiter_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)

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
    # Additive Felder (Phase 14, siehe CONCEPT.md Abschnitt 12) - lokal verwaltete Teams haben
    # kein external_id, source bleibt "LOCAL" bis eine Enterprise-Plattform synct.
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="LOCAL")
    active: Mapped[bool] = mapped_column(default=True)

    members: Mapped[list["TeamMember"]] = relationship(back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    jira_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wochenstunden: Mapped[float] = mapped_column(Float, default=40)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    # Nullable Bridge auf das Personen-Verzeichnis (Phase 14) - TeamMember bleibt bestehen,
    # solange Assignment/Jira-Sync noch darauf referenzieren (siehe CONCEPT.md Abschnitt 12.3
    # Frage 4), per Best-Effort-Mapping befüllt.
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)

    team: Mapped["Team | None"] = relationship(back_populates="members")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="team_member")


# ---------------------------------------------------------------------------
# Personen, Organisation & Permissions (Phase 14 der Kapazitätsplaner-v2-Zielarchitektur,
# siehe CONCEPT.md Abschnitt 12). Person ist bewusst schlank (kein Auth/Login) und getrennt
# von TeamMember (Kapazitätsressource) - siehe Entwicklungsprinzip 8 der Master-MD.
# ---------------------------------------------------------------------------


class Person(Base):
    """Fachliche Person, unabhängig davon ob sie kapazitätsplanbar ist (siehe
    ResourceProfile) oder Zuordnungen/Verantwortlichkeiten trägt (ProjectMembership,
    Project.projektleiter_person_id, ...). Kein Auth/Login-Konzept."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Fremdschlüssel/ID aus einer künftigen Enterprise-Plattform - lokal angelegte Personen
    # haben keine.
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Used by Jira/Tempo worklog synchronization. TeamMember keeps the same value only as a
    # compatibility bridge for the restored legacy planning UI.
    jira_account_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="LOCAL")  # LOCAL | ENTERPRISE_PLATFORM
    active: Mapped[bool] = mapped_column(default=True)


class ResourceProfile(Base):
    """Macht eine Person kapazitätsplanbar (nicht jede Person muss es sein, z.B. externe
    Ansprechpartner) - eine Person hat höchstens ein ResourceProfile."""

    __tablename__ = "resource_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), unique=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    weekly_hours: Mapped[float] = mapped_column(Float, default=40)
    capacity_relevant: Mapped[bool] = mapped_column(default=True)
    active: Mapped[bool] = mapped_column(default=True)


class ProjectRole(Base):
    """Projektbezogene Rolle (z.B. Projektleiter, Consultant) - getrennt von globalen
    App-Rollen (AppRole), siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 30."""

    __tablename__ = "project_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class ProjectMembership(Base):
    """Verknüpft Person <-> Projekt mit einer Projektrolle."""

    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    project_role_id: Mapped[int] = mapped_column(ForeignKey("project_roles.id"))

    person: Mapped["Person"] = relationship()
    project_role: Mapped["ProjectRole"] = relationship()


class Permission(Base):
    """Fachliche App-Berechtigung (z.B. PROJECT_EDIT) - siehe Master-MD Abschnitt 31. Wird
    per Migration mit dem dort aufgeführten Grundvokabular geseedet; eine künftige
    Enterprise-Plattform kann ihre eigenen Rollen später auf diese Capabilities mappen."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AppRole(Base):
    """Globale App-Rolle, bündelt Permissions über RolePermission. Kein Auth-System im Repo
    (siehe CONCEPT.md Abschnitt 7) - AppRole ist reine Vorbereitung für Phase 25/Enterprise-
    Integration, noch nicht an konkrete Personen vergeben."""

    __tablename__ = "app_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("app_roles.id"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"))


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
    # Nullable Self-FK für Diskussions-Threads (Phase 16, siehe CONCEPT.md Abschnitt 12) -
    # None = eigenständige Notiz/Wurzel eines Threads, gesetzt = Antwort auf comments.id.
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)


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
    """Systemweit wiederverwendbares Tag (nicht projektgebunden). AI-Metadata-Felder (Phase
    15, siehe Master-MD Abschnitt 43 / CONCEPT.md Abschnitt 12) beschreiben ein Tag
    semantisch für den späteren Knowledge Layer/KI-Agenten (Phase 26) - rein additiv,
    bestehende Tags bleiben ohne diese Angaben gültig."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("tag_categories.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    ai_relevant: Mapped[bool] = mapped_column(default=False)
    ai_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Kommagetrennt gespeichert (kein Array-Typ in SQLite) - als list[str] exponiert, siehe
    # schemas.TagOut.synonyms.
    synonyms: Mapped[str | None] = mapped_column(String(500), nullable=True)


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
    # Trennt WAS entschieden wurde (beschreibung) von WARUM (Decision Context, Phase 16,
    # Master-MD Abschnitt 35: decision_text vs. reason). Additiv/nullable.
    begruendung: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen/entschieden/verworfen
    # Phase 26.1: FK auf Person statt Freitext - Personenverzeichnis existiert seit Phase 14.
    entschieden_von_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
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
    # Phase 26.1: FK auf Person statt Freitext - Personenverzeichnis existiert seit Phase 14.
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
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
    # Phase 26.1: FK auf Person statt Freitext - Personenverzeichnis existiert seit Phase 14.
    zustaendig_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    faellig_am: Mapped[str | None] = mapped_column(String(10), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class Blocker(Base):
    """Etwas verhindert oder verzögert aktuell den Projektfortschritt (Phase 16, Master-MD
    Abschnitt 37/38). Zielarchitektur-native Entität - englische Feldnamen wie Person/
    ResourceProfile (Phase 14), im Unterschied zu den aus dem Excel-Tool abgeleiteten
    Kommunikation-Tab-Modellen (Decision/Risk/Task/MeetingMinutes/Comment), siehe CONCEPT.md
    Abschnitt 12. caused_by_party und waiting_for_party werden bewusst getrennt geführt: wer
    hat den Blocker verursacht vs. bei wem liegt aktuell der Ball."""

    __tablename__ = "blockers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen/in_bearbeitung/geloest
    severity: Mapped[str] = mapped_column(String(10), default="mittel")  # niedrig/mittel/hoch/kritisch
    active_since: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO "YYYY-MM-DD"
    caused_by_party: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    waiting_for_party: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    owner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    impact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class PlanPhase(Base):
    """Fachliche Source of Truth für Projektplanung (Phase 17, Master-MD Abschnitt 8/9).
    Zielarchitektur-native Entität - englische Feldnamen wie Person/Blocker. Additiv und
    bewusst NICHT automatisch aus GanttPhase/ProjectGanttPhase synchronisiert: das
    bestehende Gantt-Grid bleibt bis auf Weiteres unverändert die Bedienoberfläche (siehe
    CONCEPT.md Abschnitt 12.3 Frage 5) - kein Big-Bang-Wechsel, keine zweite unabhängige
    Planungswahrheit wird hier vorausgesetzt, PlanPhase startet leer und wird schrittweise
    befüllt. Plan/Baseline/Forecast/Actual werden sauber getrennt (Baseline/Forecast/Actual
    hier bereits vorbereitet, BaselineSnapshot/-Entry folgen in Phase 18)."""

    __tablename__ = "plan_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    subproject_id: Mapped[int | None] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    # Freitext (nicht der 1-Zeichen-Phasencode aus GanttPhase) - z.B. "Pflichtenheft",
    # "Konfiguration", "Migrationstest". Bewusst offen statt Enum, siehe Master-MD Abschnitt 7.
    phase_type: Mapped[str] = mapped_column(String(100))
    baseline_start: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO "YYYY-MM-DD"
    baseline_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    forecast_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    forecast_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    actual_start: Mapped[str | None] = mapped_column(String(10), nullable=True)
    actual_end: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="geplant")  # geplant/laufend/abgeschlossen/verzoegert
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    owner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class Milestone(Base):
    """Echtes Steuerungsobjekt (Phase 17, Master-MD Abschnitt 10) - Zielarchitektur-native
    Entität, englische Feldnamen. Additiv, siehe PlanPhase-Docstring: kein Sync mit dem
    bestehenden Gantt-Meilensteincode ('?')."""

    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    subproject_id: Mapped[int | None] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    baseline_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO "YYYY-MM-DD"
    forecast_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    actual_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="geplant")  # geplant/gefaehrdet/erreicht/verpasst
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    owner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class BaselineSnapshot(Base):
    """Eingefrorener, benannter Planstand eines Projekts zu einem Zeitpunkt (Phase 18,
    Master-MD Abschnitt 12). Zielarchitektur-native Entität, englische Feldnamen wie
    PlanPhase/Milestone. Erst sinnvoll seit Phase 17 (PlanPhase/Milestone liefern die
    Baseline-/Forecast-Felder, die hier eingefroren werden)."""

    __tablename__ = "baseline_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[str] = mapped_column(String(40))
    created_by_person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)


class BaselineEntry(Base):
    """Ein eingefrorener Feldwert innerhalb eines BaselineSnapshot (generisch über
    entity_type/entity_id/field, analog zu TagLink/DocumentLink/EntityRelation). entity_id
    ist bewusst KEIN Fremdschlüssel: ein Snapshot muss gültig bleiben, auch wenn die
    referenzierte PlanPhase/Milestone später gelöscht wird - historischer Stand, analog zu
    PlanHistory."""

    __tablename__ = "baseline_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_id: Mapped[int] = mapped_column(ForeignKey("baseline_snapshots.id"))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int] = mapped_column()
    field: Mapped[str] = mapped_column(String(50))
    value: Mapped[str | None] = mapped_column(String(500), nullable=True)


# ---------------------------------------------------------------------------
# Capacity Planning Core (Phase 19 der Kapazitätsplaner-v2-Zielarchitektur, siehe CONCEPT.md
# Abschnitt 12). Grundsatz "Demand ≠ Assignment": ResourceDemand/ResourceAssignment sind
# komplett neu und unabhängig vom bestehenden Assignment-Modell (TeamMember<->Project, siehe
# routers/team.py) - keine Migration, keine Bridge, beide Systeme laufen parallel.
# ---------------------------------------------------------------------------


class ResourceRole(Base):
    """Rollenbasierter Ressourcenbedarf (z.B. Projektleitung, Consulting, Integration,
    Development, Support), siehe Master-MD Abschnitt 15. Getrennt von Skill (Abschnitt 16) -
    Rolle und Skill sind unterschiedliche Dimensionen."""

    __tablename__ = "resource_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class PersonSkill(Base):
    __tablename__ = "person_skills"
    __table_args__ = (UniqueConstraint("person_id", "skill_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    # Freitext (wie Blocker.severity) - Master-MD gibt keine feste Werteliste vor, z.B.
    # "grundkenntnisse"/"fortgeschritten"/"experte".
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)


class ResourceDemand(Base):
    """Ressourcenbedarf, zunächst unabhängig von konkreten Personen geplant (Master-MD
    Abschnitt 17) - erst ResourceAssignment ordnet ihn Personen zu."""

    __tablename__ = "resource_demands"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    plan_phase_id: Mapped[int | None] = mapped_column(ForeignKey("plan_phases.id"), nullable=True)
    resource_role_id: Mapped[int] = mapped_column(ForeignKey("resource_roles.id"))
    # Gleiches "Apr 26"-Format wie GanttPhase.monat/FtePlan.monat (siehe
    # constants.berechne_monate) - "Capacity Bucket = MONTH" laut Master-MD Abschnitt 17.
    period: Mapped[str] = mapped_column(String(10))
    fte: Mapped[float] = mapped_column(Float, default=0)
    # FIX/TENTATIVE/SCENARIO, fester Wertebereich laut Master-MD Abschnitt 19.
    commitment_level: Mapped[str] = mapped_column(String(20), default="TENTATIVE")
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


class ResourceAssignment(Base):
    """Ordnet einen ResourceDemand konkreten Personen zu (Master-MD Abschnitt 18) - getrennt
    vom bestehenden Assignment-Modell (TeamMember<->Project), siehe Klassendoku oben."""

    __tablename__ = "resource_assignments"
    __table_args__ = (UniqueConstraint("resource_demand_id", "person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_demand_id: Mapped[int] = mapped_column(ForeignKey("resource_demands.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    fte: Mapped[float] = mapped_column(Float, default=0)
    erstellt_am: Mapped[str] = mapped_column(String(40))
    aktualisiert_am: Mapped[str] = mapped_column(String(40))


# ---------------------------------------------------------------------------
# Real Capacity (Phase 20 der Kapazitätsplaner-v2-Zielarchitektur, siehe CONCEPT.md
# Abschnitt 12 / Master-MD Abschnitt 20). Grundformel:
#   Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity
# Personenbezogen, unabhängig von einem einzelnen Projekt - kein delete_project-Cascade nötig.
# ---------------------------------------------------------------------------


class CapacityCalendar(Base):
    """Benannter Feiertagskalender (z.B. 'Deutschland', 'Bayern'), dem WorkingTime-Zeiträume
    zugeordnet werden können."""

    __tablename__ = "capacity_calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("capacity_calendar_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    capacity_calendar_id: Mapped[int] = mapped_column(ForeignKey("capacity_calendars.id"))
    date: Mapped[str] = mapped_column(String(10))  # ISO "YYYY-MM-DD"
    name: Mapped[str] = mapped_column(String(200))


class WorkingTime(Base):
    """Nominale Wochenstunden einer Person für einen Gültigkeitszeitraum (Historisierung von
    Teilzeit-/Vollzeit-Änderungen), inkl. anzuwendendem Feiertagskalender. Ergänzt
    ResourceProfile.weekly_hours (Phase 14, dort der aktuelle Einzelwert) um eine echte
    Zeitreihe - beide Felder werden bewusst nicht synchronisiert (additiv, siehe CONCEPT.md
    Abschnitt 12.3 Frage 5 zum generellen Nicht-Sync-Prinzip)."""

    __tablename__ = "working_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    capacity_calendar_id: Mapped[int | None] = mapped_column(ForeignKey("capacity_calendars.id"), nullable=True)
    valid_from: Mapped[str] = mapped_column(String(10))  # ISO "YYYY-MM-DD"
    valid_to: Mapped[str | None] = mapped_column(String(10), nullable=True)  # None = weiterhin gültig
    weekly_hours: Mapped[float] = mapped_column(Float, default=40)


class Absence(Base):
    __tablename__ = "absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    # Freitext (wie Blocker.severity) - z.B. "urlaub"/"krankheit"/"sonstiges".
    absence_type: Mapped[str] = mapped_column(String(30), default="urlaub")
    start_date: Mapped[str] = mapped_column(String(10))  # ISO "YYYY-MM-DD"
    end_date: Mapped[str] = mapped_column(String(10))


class InternalAllocation(Base):
    """Kapazität, die pauschal für interne Tätigkeiten (nicht Projektarbeit) reserviert ist,
    je Monat (gleiches 'Apr 26'-Format wie ResourceDemand.period)."""

    __tablename__ = "internal_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    period: Mapped[str] = mapped_column(String(10))
    fte: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)


class HealthThreshold(Base):
    """Konfigurierbare Schwellwerte für die Project-Health-Berechnung (Phase 22, Master-MD
    Abschnitt 22/50: 'Schwellwerte sollen konfigurierbar sein'). Je Dimension ein 'badness'-
    Wert (nicht-negative Kennzahl, je größer desto schlechter - siehe health_calc.py), ab dem
    gelb bzw. rot ausgelöst wird. Effort Health bleibt bewusst außen vor: sie verwendet
    unverändert GAP_SCHWELLE_GELB/ROT aus gap_analysis.py (bestehende, produktiv genutzte
    Logik wird nicht dupliziert/parallel konfigurierbar gemacht)."""

    __tablename__ = "health_thresholds"

    id: Mapped[int] = mapped_column(primary_key=True)
    metric: Mapped[str] = mapped_column(String(30), unique=True)
    yellow: Mapped[float] = mapped_column(Float)
    red: Mapped[float] = mapped_column(Float)
