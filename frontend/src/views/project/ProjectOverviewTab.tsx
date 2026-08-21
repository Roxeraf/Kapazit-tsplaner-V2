import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import TagChip from "../../components/TagChip";
import { describeEntry, formatTimestamp } from "../../components/HistoryPanel";
import {
  HEALTH_DIMENSION_LABELS,
  HEALTH_STATUS_COLOR,
  PROJECT_STATUS_LABELS,
  type Comment,
  type HealthDimension,
  type PlanHistoryEntry,
  type ProjectControlCockpit,
} from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

function HealthBadge({ label, dimension }: { label: string; dimension: HealthDimension }) {
  return (
    <div title={dimension.explanation} style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.8rem" }}>
      <span
        aria-hidden="true"
        style={{
          display: "inline-block",
          width: 9,
          height: 9,
          borderRadius: "50%",
          background: HEALTH_STATUS_COLOR[dimension.status],
        }}
      />
      {label}
    </div>
  );
}

const PARTY_LABELS: Record<"customer" | "internal" | "third_party" | "unknown", string> = {
  customer: "Kunde",
  internal: "Intern",
  third_party: "Drittpartei",
  unknown: "Unbekannt",
};

export default function ProjectOverviewTab() {
  const { project } = useProjectWorkspace();
  const [cockpit, setCockpit] = useState<ProjectControlCockpit | null>(null);
  const [history, setHistory] = useState<PlanHistoryEntry[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCockpit(project.id).then(setCockpit).catch((e) => setError(String(e)));
    api.getProjectHistory(project.id).then(setHistory).catch(() => setHistory([]));
    api.listComments(project.id).then(setComments).catch(() => setComments([]));
  }, [project.id]);

  const generalComments = comments
    .filter((c) => c.monat === null && c.phase_code === null)
    .sort((a, b) => (a.erstellt_am < b.erstellt_am ? 1 : -1));

  const start = project.monate[0];
  const ende = project.monate[project.monate.length - 1];

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="toolbar" style={{ alignItems: "flex-start" }}>
          <div>
            <h3 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.35rem" }}>{project.name}</h3>
            <p style={{ color: "var(--text-muted)", margin: 0 }}>
              {project.kunde ?? "Kein Kunde hinterlegt"}
              {cockpit?.projektleiter && <> · Projektleiter: {cockpit.projektleiter}</>}
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: "0.25rem 0 0" }}>
              {start} – {ende} · Status: {PROJECT_STATUS_LABELS[project.status]}
            </p>
          </div>
          {cockpit && (
            <div style={{ textAlign: "right" }}>
              <span className={`gap-badge gap-badge--${cockpit.health.overall.status}`}>
                <span className="gap-status-dot" />
                {cockpit.health.overall.explanation}
              </span>
            </div>
          )}
        </div>
      </div>

      {cockpit && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Project Control</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "0.4rem", marginBottom: "0.75rem" }}>
            {(Object.keys(HEALTH_DIMENSION_LABELS) as (keyof typeof HEALTH_DIMENSION_LABELS)[]).map((key) => (
              <HealthBadge key={key} label={HEALTH_DIMENSION_LABELS[key]} dimension={cockpit.health[key]} />
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", fontSize: "0.88rem" }}>
            <div>
              <strong>Termine</strong>
              <p style={{ margin: "0.2rem 0" }}>
                Aktuelle Phase: {cockpit.current_phase ?? "—"}
                <br />
                Voraussichtliches Projektende: {cockpit.forecast_end ?? "—"}
                {cockpit.health.schedule.status !== "gruen" && cockpit.health.schedule.status !== "grau" && (
                  <>
                    <br />
                    <Link to={`/projekte/${project.id}/planung`} style={{ fontSize: "0.8rem", color: "var(--rot)" }}>
                      Ursache in der Planung ansehen →
                    </Link>
                  </>
                )}
              </p>
            </div>
            <div>
              <strong>Kapazität ({cockpit.capacity.period})</strong>
              <p style={{ margin: "0.2rem 0" }}>
                Bedarf {cockpit.capacity.demand_fte.toFixed(2)} FTE · Zugeordnet {cockpit.capacity.assigned_fte.toFixed(2)} FTE
                <br />
                <span style={{ color: cockpit.capacity.allocation_gap_fte < 0 ? "var(--rot)" : undefined }}>
                  Gap {cockpit.capacity.allocation_gap_fte > 0 ? "+" : ""}
                  {cockpit.capacity.allocation_gap_fte.toFixed(2)} FTE
                </span>
                {cockpit.capacity.allocation_gap_fte < 0 && (
                  <>
                    <br />
                    <Link to={`/projekte/${project.id}/planung`} style={{ fontSize: "0.8rem", color: "var(--rot)" }}>
                      Geeignete Ressourcen suchen →
                    </Link>
                  </>
                )}
              </p>
            </div>
            <div>
              <strong>Blocker ({cockpit.blockers.open_total} offen)</strong>
              <p style={{ margin: "0.2rem 0" }}>
                {(["customer", "internal", "third_party", "unknown"] as const)
                  .filter((party) => cockpit.blockers[party] > 0)
                  .map((party) => `${PARTY_LABELS[party]} ${cockpit.blockers[party]}`)
                  .join(" · ") || "Keine offenen Blocker"}
                {cockpit.blockers.open_total > 0 && (
                  <>
                    <br />
                    <Link to={`/projekte/${project.id}/kommunikation`} style={{ fontSize: "0.8rem" }}>
                      Blocker ansehen →
                    </Link>
                  </>
                )}
              </p>
            </div>
            <div>
              <strong>Aufgaben</strong>
              <p style={{ margin: "0.2rem 0" }}>
                {cockpit.tasks.open_total} offen
                {cockpit.tasks.overdue > 0 && <span style={{ color: "var(--rot)" }}> · {cockpit.tasks.overdue} überfällig</span>}
              </p>
            </div>
          </div>

          {cockpit.tags.length > 0 && (
            <div style={{ marginTop: "0.75rem" }}>
              <strong style={{ fontSize: "0.88rem" }}>Aktuelle Themen</strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.3rem" }}>
                {cockpit.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {cockpit && cockpit.milestones.length > 0 && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Milestones</h3>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.85rem" }}>
            {cockpit.milestones.map((m) => (
              <li key={m.id} style={{ padding: "0.25rem 0", borderBottom: "1px solid var(--border)" }}>
                🚩 {m.name} — {m.forecast_date ?? m.baseline_date ?? "kein Termin"} ({m.status})
              </li>
            ))}
          </ul>
          <p style={{ marginTop: "0.5rem" }}>
            <Link to={`/projekte/${project.id}/planung`} style={{ fontSize: "0.85rem" }}>
              Zur Planung →
            </Link>
          </p>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
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
          <p style={{ marginTop: "0.5rem" }}>
            <Link to={`/projekte/${project.id}/kommunikation`} style={{ fontSize: "0.85rem" }}>
              Zur Kommunikation →
            </Link>
          </p>
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
