import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import NotesSection from "../../components/NotesSection";
import type { Blocker, Comment, Decision, EntityType, MeetingMinutes, Risk, Task } from "../../types";
import ActivityFeed from "./components/ActivityFeed";
import BlockerList from "./components/BlockerList";
import CurrentTopicsWidget from "./components/CurrentTopicsWidget";
import DecisionList from "./components/DecisionList";
import MeetingMinutesList from "./components/MeetingMinutesList";
import RiskList from "./components/RiskList";
import TaskList from "./components/TaskList";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

type Section = "aktivitaet" | "diskussionen" | "entscheidungen" | "risiken" | "meetingprotokolle" | "aufgaben" | "blocker";

// Bildet ActivityItem.entity_type auf die passende Sub-Ansicht ab (Phase 26.4).
const ENTITY_TYPE_TO_SECTION: Partial<Record<EntityType, Section>> = {
  comment: "diskussionen",
  decision: "entscheidungen",
  risk: "risiken",
  meeting_minutes: "meetingprotokolle",
  task: "aufgaben",
  blocker: "blocker",
};

const ACTIVITY_ENTITY_TYPES: EntityType[] = ["comment", "decision", "risk", "meeting_minutes", "task", "blocker"];

export default function ProjectCommunicationTab() {
  const { project } = useProjectWorkspace();
  const [section, setSection] = useState<Section>("aktivitaet");
  const [comments, setComments] = useState<Comment[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [meetings, setMeetings] = useState<MeetingMinutes[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const [search, setSearch] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // ActivityFeed lädt selbst nach, bekommt Mutationen aus den Geschwister-Listen (Tasks/
  // Decisions/Risks/Meetings/Blockers/Comments) sonst nicht automatisch mit (P16.1, siehe
  // PlanPhaseWorkspace für dasselbe Muster im Phasenkontext).
  const [activityVersion, setActivityVersion] = useState(0);
  const bumpActivity = () => setActivityVersion((v) => v + 1);

  const refreshComments = () => api.listComments(project.id).then(setComments).catch((e) => setError(String(e)));
  const refreshDecisions = () => api.listDecisions(project.id).then(setDecisions).catch((e) => setError(String(e)));
  const refreshRisks = () => api.listRisks(project.id).then(setRisks).catch((e) => setError(String(e)));
  const refreshMeetings = () => api.listMeetingMinutes(project.id).then(setMeetings).catch((e) => setError(String(e)));
  const refreshTasks = () => api.listTasks(project.id).then(setTasks).catch((e) => setError(String(e)));
  const refreshBlockers = () => api.listBlockers(project.id).then(setBlockers).catch((e) => setError(String(e)));

  useEffect(() => {
    refreshComments();
    refreshDecisions();
    refreshRisks();
    refreshMeetings();
    refreshTasks();
    refreshBlockers();
  }, [project.id]);

  const handleAddNote = async (
    subprojectId: number | null,
    input: { text: string; tags: string[]; files: File[] },
  ) => {
    const comment = await api.createComment(project.id, {
      subproject_id: subprojectId,
      text: input.text,
      tags: input.tags,
    });
    for (const file of input.files) {
      await api.uploadDocument(project.id, file, { entityType: "comment", entityId: comment.id });
    }
    refreshComments();
    bumpActivity();
  };

  const handleDeleteComment = async (commentId: number) => {
    await api.deleteComment(commentId);
    refreshComments();
    bumpActivity();
  };

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    for (const c of comments) c.tags.forEach((t) => tags.add(t));
    for (const d of decisions) d.tags.forEach((t) => tags.add(t));
    for (const r of risks) r.tags.forEach((t) => tags.add(t));
    for (const m of meetings) m.tags.forEach((t) => tags.add(t));
    for (const t of tasks) t.tags.forEach((tag) => tags.add(tag));
    for (const b of blockers) b.tags.forEach((tag) => tags.add(tag));
    return Array.from(tags).sort();
  }, [comments, decisions, risks, meetings, tasks, blockers]);

  const matches = (text: string) => !search.trim() || text.toLowerCase().includes(search.trim().toLowerCase());
  const hasTag = (tags: string[]) => !tagFilter || tags.includes(tagFilter);

  const filteredComments = comments.filter((c) => matches(c.text) && hasTag(c.tags));
  const filteredDecisions = decisions.filter((d) => matches(d.titel + " " + (d.beschreibung ?? "")) && hasTag(d.tags));
  const filteredRisks = risks.filter((r) => matches(r.titel + " " + (r.beschreibung ?? "")) && hasTag(r.tags));
  const filteredMeetings = meetings.filter((m) => matches(m.titel + " " + m.text) && hasTag(m.tags));
  const filteredTasks = tasks.filter((t) => matches(t.titel + " " + (t.beschreibung ?? "")) && hasTag(t.tags));
  const filteredBlockers = blockers.filter((b) => matches(b.title + " " + (b.description ?? "")) && hasTag(b.tags));

  const SECTIONS: { key: Section; label: string; count: number }[] = [
    { key: "aktivitaet", label: "Aktivität", count: comments.length + decisions.length + risks.length + meetings.length + tasks.length + blockers.length },
    { key: "diskussionen", label: "Diskussionen", count: filteredComments.length },
    { key: "aufgaben", label: "Aufgaben", count: filteredTasks.length },
    { key: "entscheidungen", label: "Entscheidungen", count: filteredDecisions.length },
    { key: "risiken", label: "Risiken", count: filteredRisks.length },
    { key: "meetingprotokolle", label: "Meetings", count: filteredMeetings.length },
    { key: "blocker", label: "Blocker", count: filteredBlockers.length },
  ];

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      <CurrentTopicsWidget projectId={project.id} />

      <div className="toolbar" style={{ marginBottom: "0.75rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              type="button"
              className={s.key === section ? "btn" : "btn secondary"}
              onClick={() => setSection(s.key)}
            >
              {s.label} ({s.count})
            </button>
          ))}
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Suche …"
          style={{ padding: "0.4rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", minWidth: "12rem" }}
        />
      </div>

      {allTags.length > 0 && (
        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          {tagFilter && (
            <button type="button" className="btn secondary" onClick={() => setTagFilter(null)}>
              Filter zurücksetzen (#{tagFilter})
            </button>
          )}
          {allTags
            .filter((t) => t !== tagFilter)
            .map((t) => (
              <button key={t} type="button" className="btn secondary" onClick={() => setTagFilter(t)}>
                #{t}
              </button>
            ))}
        </div>
      )}

      {section === "aktivitaet" && (
        <ActivityFeed
          projectId={project.id}
          filterTypes={ACTIVITY_ENTITY_TYPES}
          onOpenSection={(type) => {
            const target = ENTITY_TYPE_TO_SECTION[type];
            if (target) setSection(target);
          }}
          onChanged={() => {
            refreshComments();
            refreshDecisions();
            refreshRisks();
            refreshTasks();
            refreshBlockers();
            bumpActivity();
          }}
          refreshToken={activityVersion}
        />
      )}

      {section === "diskussionen" && (
        <div>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projekt</h3>
            <NotesSection
              notes={filteredComments.filter((c) => c.subproject_id === null && c.monat === null && c.phase_code === null)}
              onAdd={(input) => handleAddNote(null, input)}
              onDelete={handleDeleteComment}
            />
          </div>
          {project.subprojects.map((sp) => (
            <div key={sp.id} className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{sp.name}</h3>
              <NotesSection
                notes={filteredComments.filter((c) => c.subproject_id === sp.id && c.monat === null && c.phase_code === null)}
                onAdd={(input) => handleAddNote(sp.id, input)}
                onDelete={handleDeleteComment}
              />
            </div>
          ))}
        </div>
      )}

      {section === "aufgaben" && (
        <TaskList projectId={project.id} tasks={filteredTasks} onChanged={() => { refreshTasks(); bumpActivity(); }} />
      )}
      {section === "entscheidungen" && (
        <DecisionList projectId={project.id} decisions={filteredDecisions} onChanged={() => { refreshDecisions(); bumpActivity(); }} />
      )}
      {section === "risiken" && (
        <RiskList projectId={project.id} risks={filteredRisks} onChanged={() => { refreshRisks(); bumpActivity(); }} />
      )}
      {section === "meetingprotokolle" && (
        <MeetingMinutesList projectId={project.id} meetings={filteredMeetings} onChanged={() => { refreshMeetings(); bumpActivity(); }} />
      )}
      {section === "blocker" && (
        <BlockerList projectId={project.id} blockers={filteredBlockers} onChanged={() => { refreshBlockers(); bumpActivity(); }} />
      )}
    </div>
  );
}
