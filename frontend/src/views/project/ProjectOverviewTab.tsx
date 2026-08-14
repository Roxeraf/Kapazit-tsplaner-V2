import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { describeEntry, formatTimestamp } from "../../components/HistoryPanel";
import {
  PROJECT_STATUS_LABELS,
  type Comment,
  type Decision,
  type GapAnalysis,
  type GapStatus,
  type PlanHistoryEntry,
  type Risk,
  type Task,
} from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

const GAP_STATUS_LABEL: Record<GapStatus, string> = {
  gruen: "im Plan",
  gelb: "Abweichung",
  rot: "kritische Abweichung",
  grau: "keine Ist-Daten",
};

function AmpelBadge({ status }: { status: GapStatus }) {
  return (
    <span className={`gap-badge gap-badge--${status}`}>
      <span className="gap-status-dot" />
      {GAP_STATUS_LABEL[status]}
    </span>
  );
}

export default function ProjectOverviewTab() {
  const { project } = useProjectWorkspace();
  const [gap, setGap] = useState<GapAnalysis | null>(null);
  const [history, setHistory] = useState<PlanHistoryEntry[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    api.getProjectGap(project.id).then(setGap).catch(() => setGap(null));
    api.getProjectHistory(project.id).then(setHistory).catch(() => setHistory([]));
    api.listComments(project.id).then(setComments).catch(() => setComments([]));
    api.listRisks(project.id).then(setRisks).catch(() => setRisks([]));
    api.listDecisions(project.id).then(setDecisions).catch(() => setDecisions([]));
    api.listTasks(project.id).then(setTasks).catch(() => setTasks([]));
  }, [project.id]);

  const generalComments = comments
    .filter((c) => c.monat === null && c.phase_code === null)
    .sort((a, b) => (a.erstellt_am < b.erstellt_am ? 1 : -1));

  const offeneAufgaben = tasks.filter((t) => t.status !== "erledigt");
  const offeneRisiken = risks.filter((r) => r.status !== "geschlossen");
  const offeneEntscheidungen = decisions.filter((d) => d.status === "offen");

  const start = project.monate[0];
  const ende = project.monate[project.monate.length - 1];

  return (
    <div>
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="toolbar" style={{ alignItems: "flex-start" }}>
          <div>
            <h3 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.35rem" }}>{project.name}</h3>
            <p style={{ color: "var(--text-muted)", margin: 0 }}>
              {project.kunde ?? "Kein Kunde hinterlegt"}
              {project.projektleiter && <> · Projektleiter: {project.projektleiter}</>}
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "0.25rem 0 0" }}>
              {start} – {ende} · Status: {PROJECT_STATUS_LABELS[project.status]}
            </p>
          </div>
          {gap && (
            <div style={{ textAlign: "right" }}>
              <AmpelBadge status={gap.status} />
              {gap.gap_pct !== null && (
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "0.4rem 0 0" }}>
                  Auslastung: {gap.soll_gesamt > 0 ? Math.round((gap.projiziert_gesamt / gap.soll_gesamt) * 100) : 0}%
                  {" "}vom Plan (Hochrechnung)
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
        <div className="card">
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Offene Aufgaben</h3>
          {offeneAufgaben.length === 0 && offeneRisiken.length === 0 && offeneEntscheidungen.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine offenen Aufgaben, Risiken oder Entscheidungen.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.85rem" }}>
              {offeneAufgaben.map((t) => (
                <li key={`task-${t.id}`} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                  ☑ {t.titel}
                </li>
              ))}
              {offeneRisiken.map((r) => (
                <li key={`risk-${r.id}`} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                  ⚠ {r.titel}
                </li>
              ))}
              {offeneEntscheidungen.map((d) => (
                <li key={`decision-${d.id}`} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                  ❓ {d.titel}
                </li>
              ))}
            </ul>
          )}
          <p style={{ marginTop: "0.5rem" }}>
            <Link to={`/projekte/${project.id}/kommunikation`} style={{ fontSize: "0.85rem" }}>
              Zur Kommunikation →
            </Link>
          </p>
        </div>

        <div className="card">
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Letzte Notizen</h3>
          {generalComments.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Notizen.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.85rem" }}>
              {generalComments.slice(0, 5).map((c) => (
                <li key={c.id} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                  {c.text}
                  <div style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>{formatTimestamp(c.erstellt_am)}</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Letzte Änderungen</h3>
          {history.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Änderungen protokolliert.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.85rem" }}>
              {history.slice(0, 5).map((entry) => (
                <li key={entry.id} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                  {describeEntry(entry)}
                  <div style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>{formatTimestamp(entry.geaendert_am)}</div>
                </li>
              ))}
            </ul>
          )}
          <p style={{ marginTop: "0.5rem" }}>
            <Link to={`/projekte/${project.id}/historie`} style={{ fontSize: "0.85rem" }}>
              Zur Historie →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
