import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ActivityFeed from "./ActivityFeed";
import BlockerList from "./BlockerList";
import DecisionList from "./DecisionList";
import NotesSection from "../../../components/NotesSection";
import PersonPicker from "../../../components/PersonPicker";
import PlanPhaseCapacityTab from "./PlanPhaseCapacityTab";
import TagInput from "../../../components/TagInput";
import TaskList from "./TaskList";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { categorize, CATEGORY_ICONS } from "../../../documentIcons";
import {
  PLAN_PHASE_STATUS_LABELS,
  PLAN_PHASE_STATUS_OPTIONS,
  PLAN_PHASE_TYPE_SUGGESTIONS,
  type EntityType,
  type PlanPhaseDetail,
  type PlanPhaseStatus,
  type SubprojectDetail,
} from "../../../types";

// P11 (Planungs-/Kapazitätskonsolidierung): PlanPhase Workspace - rechtsseitiger Drawer, jetzt
// die primäre Bearbeitungsoberfläche einer Phase (löst den bisherigen Doppel-UX-Zustand ab, in
// dem PlanPhaseList.tsx parallel ein vollständiges Inline-Formular zeigte). Vier Tabs:
// Übersicht (editierbar, Sofort-Speichern wie der Rest der Planung - kein Batch-/Grund-
// Workflow), Kapazität (Rollen-/Personenaufschlüsselung), Aktivität (bestehende generische
// Kommentar-/Task-/Blocker-/Decision-/ActivityFeed-Infrastruktur, unverändert wiederverwendet),
// Dateien (bestehendes Document/DocumentLink-System). forecast_start/forecast_end erscheinen
// hier nur als "Start"/"Ende" (= "aktueller Plan") - baseline_*/progress erscheinen im
// Normalflow gar nicht mehr (Planstand siehe BaselineList, Progress deprecatet seit P6);
// actual_start/actual_end sind sekundär und nur über eine explizite Korrektur-Aktion editierbar.
const PHASE_ACTIVITY_TYPES: EntityType[] = ["comment", "decision", "task", "blocker"];

type Tab = "uebersicht" | "kapazitaet" | "aktivitaet" | "dateien";

function fmtNum(v: number | null | undefined, suffix = ""): string {
  return v == null ? "—" : `${v}${suffix}`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function PlanPhaseWorkspace({
  planPhaseId,
  projectId,
  subprojects,
  onClose,
  onChanged,
}: {
  planPhaseId: number | null;
  projectId: number;
  subprojects: SubprojectDetail[];
  onClose: () => void;
  onChanged?: () => void;
}) {
  const [detail, setDetail] = useState<PlanPhaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("uebersicht");
  const [correctingActual, setCorrectingActual] = useState(false);
  const [uploading, setUploading] = useState(false);
  // ActivityFeed lädt selbst nach, bekommt Mutationen von NotesSection/TaskList/DecisionList/
  // BlockerList (Geschwisterkomponenten im selben Tab) aber nicht automatisch mit - dieser
  // Zähler wird bei jedem reload() hochgezählt und an ActivityFeed durchgereicht (P16.1).
  const [activityVersion, setActivityVersion] = useState(0);
  const people = usePeopleMap();

  const load = () => {
    if (planPhaseId == null) return;
    setError(null);
    api.getPlanPhaseDetail(planPhaseId).then(setDetail).catch((e) => setError(String(e)));
  };

  // Beim Phasenwechsel: Detail zurücksetzen (vermeidet Stale-Data-Flash), Tab/Korrektur-Modus
  // zurücksetzen und neu laden. Nach Mutationen (reload) wird load() direkt aufgerufen.
  useEffect(() => {
    setDetail(null);
    setTab("uebersicht");
    setCorrectingActual(false);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planPhaseId]);

  const reload = () => {
    load();
    setActivityVersion((v) => v + 1);
    onChanged?.();
  };

  if (planPhaseId == null) return null;

  const update = async (changes: Record<string, unknown>) => {
    try {
      await api.updatePlanPhase(planPhaseId, changes);
      reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleAddNote = async (input: { text: string; tags: string[]; files: File[] }) => {
    const comment = await api.createComment(projectId, {
      text: input.text,
      tags: input.tags,
      plan_phase_id: planPhaseId,
    });
    for (const file of input.files) {
      await api.uploadDocument(projectId, file, { entityType: "comment", entityId: comment.id });
    }
    reload();
  };

  const handleDeleteNote = async (commentId: number) => {
    await api.deleteComment(commentId);
    reload();
  };

  const handleUploadFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(fileList)) {
        await api.uploadDocument(projectId, file, { entityType: "plan_phase", entityId: planPhaseId });
      }
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: number) => {
    await api.deleteDocument(documentId);
    reload();
  };

  // Statuswert der aktuellen Phase in den Options-Dropdown mit aufnehmen, falls es sich um
  // einen historischen Wert handelt (z.B. "verzoegert") - Daten bleiben sichtbar/wählbar
  // erhalten, ohne dass er als neuer Zielwert beworben wird (siehe types.ts).
  const statusOptions = detail && !PLAN_PHASE_STATUS_OPTIONS.includes(detail.status)
    ? [detail.status, ...PLAN_PHASE_STATUS_OPTIONS]
    : PLAN_PHASE_STATUS_OPTIONS;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "min(34rem, 100vw)",
        background: "#fff",
        borderLeft: "1px solid var(--border)",
        boxShadow: "-4px 0 16px rgba(0,0,0,0.12)",
        zIndex: 900,
        overflowY: "auto",
        padding: "1rem",
      }}
    >
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>{detail?.phase_type ?? "Phase"}</h3>
        <button type="button" className="btn secondary" onClick={onClose}>
          Schließen
        </button>
      </div>

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
        {([
          ["uebersicht", "Übersicht"],
          ["kapazitaet", "Kapazität"],
          ["aktivitaet", "Aktivität"],
          ["dateien", "Dateien"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button key={key} type="button" className={tab === key ? "btn" : "btn secondary"} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {!detail ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade Phase …</p>
      ) : tab === "uebersicht" ? (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
              <label>
                Name
                <input
                  key={`${detail.id}-name-${detail.phase_type}`}
                  defaultValue={detail.phase_type}
                  list="plan-phase-type-suggestions"
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    if (value && value !== detail.phase_type) update({ phase_type: value });
                  }}
                />
              </label>
              <datalist id="plan-phase-type-suggestions">
                {PLAN_PHASE_TYPE_SUGGESTIONS.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>

              <label>
                Zeitraum (Start – Ende)
                <div style={{ display: "flex", gap: "0.4rem" }}>
                  <input
                    key={`${detail.id}-fs-${detail.forecast_start}`}
                    type="date"
                    defaultValue={detail.forecast_start ?? ""}
                    onBlur={(e) => update({ forecast_start: e.target.value || null })}
                  />
                  <input
                    key={`${detail.id}-fe-${detail.forecast_end}`}
                    type="date"
                    defaultValue={detail.forecast_end ?? ""}
                    onBlur={(e) => update({ forecast_end: e.target.value || null })}
                  />
                </div>
              </label>

              <div className="field-row" style={{ marginTop: 0 }}>
                <label>
                  Status
                  <select value={detail.status} onChange={(e) => update({ status: e.target.value as PlanPhaseStatus })}>
                    {statusOptions.map((value) => (
                      <option key={value} value={value}>
                        {PLAN_PHASE_STATUS_LABELS[value]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Plan-Aufwand (FTE)
                  <input
                    key={`${detail.id}-fte-${detail.plan_fte}`}
                    type="number"
                    min={0}
                    step={0.05}
                    defaultValue={detail.plan_fte ?? ""}
                    placeholder="—"
                    onBlur={(e) => {
                      const raw = e.target.value.trim();
                      update({ plan_fte: raw === "" ? null : Number(raw) });
                    }}
                  />
                </label>
              </div>

              <div className="field-row" style={{ marginTop: 0 }}>
                <label>
                  Teilprojekt
                  <select
                    value={detail.subproject_id ?? ""}
                    onChange={(e) => update({ subproject_id: e.target.value === "" ? null : Number(e.target.value) })}
                  >
                    <option value="">Projektweit</option>
                    {subprojects.map((sp) => (
                      <option key={sp.id} value={sp.id}>
                        {sp.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Owner
                  <PersonPicker value={detail.owner_person_id} onChange={(personId) => update({ owner_person_id: personId })} />
                </label>
              </div>
              {detail.owner_person_id != null && (
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "-0.2rem 0 0" }}>
                  {people.get(detail.owner_person_id) ?? "…"}
                </p>
              )}

              <label>
                Tags
                <TagInput value={detail.tags} onChange={(tags) => update({ tags })} />
              </label>
            </div>
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kennzahlen</h4>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
              <div>
                <strong>Planstunden:</strong> {fmtNum(detail.metrics.plan_hours, " h")}
              </div>
              <div>
                <strong>Zeitfortschritt:</strong> {fmtNum(detail.metrics.time_progress_pct, "%")}
                <span style={{ color: "var(--text-muted)", marginLeft: "0.4rem", fontSize: "0.78rem" }}>
                  (Anteil des geplanten Zeitraums, der vergangen ist - kein Health-/Fortschrittswert)
                </span>
              </div>
              <div>
                <strong>Ist-Aufwand:</strong> Noch nicht eindeutig der Planphase zugeordnet
              </div>
              <div>
                <strong>Aufwandsverbrauch:</strong> {"—"}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="toolbar">
              <h4 style={{ color: "var(--navy)", margin: 0 }}>Tatsächlicher Verlauf</h4>
              <button type="button" className="btn secondary" style={{ fontSize: "0.75rem" }} onClick={() => setCorrectingActual((v) => !v)}>
                {correctingActual ? "Fertig" : "Ist-Daten korrigieren"}
              </button>
            </div>
            {!correctingActual ? (
              <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem", marginTop: "0.4rem" }}>
                <div>
                  <strong>Gestartet:</strong> {fmtDate(detail.actual_start)}
                </div>
                <div>
                  <strong>Abgeschlossen:</strong> {fmtDate(detail.actual_end)}
                </div>
              </div>
            ) : (
              <div className="field-row" style={{ marginTop: "0.4rem" }}>
                <label>
                  Gestartet
                  <input
                    key={`${detail.id}-as-${detail.actual_start}`}
                    type="date"
                    defaultValue={detail.actual_start ?? ""}
                    onBlur={(e) => update({ actual_start: e.target.value || null })}
                  />
                </label>
                <label>
                  Abgeschlossen
                  <input
                    key={`${detail.id}-ae-${detail.actual_end}`}
                    type="date"
                    defaultValue={detail.actual_end ?? ""}
                    onBlur={(e) => update({ actual_end: e.target.value || null })}
                  />
                </label>
              </div>
            )}
          </div>
        </>
      ) : tab === "kapazitaet" ? (
        <PlanPhaseCapacityTab
          projectId={projectId}
          planPhaseId={detail.id}
          planFte={detail.plan_fte}
          forecastStart={detail.forecast_start}
          demands={detail.resource_demands}
          metrics={detail.metrics}
          onChanged={reload}
        />
      ) : tab === "aktivitaet" ? (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aktivität</h4>
            <ActivityFeed
              projectId={projectId}
              planPhaseId={planPhaseId}
              filterTypes={PHASE_ACTIVITY_TYPES}
              onOpenSection={() => setTab("aktivitaet")}
              onChanged={reload}
              refreshToken={activityVersion}
            />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kommentare</h4>
            <NotesSection notes={detail.comments} onAdd={handleAddNote} onDelete={handleDeleteNote} />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aufgaben</h4>
            <TaskList projectId={projectId} tasks={detail.tasks} onChanged={reload} planPhaseId={planPhaseId} />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Entscheidungen</h4>
            <DecisionList projectId={projectId} decisions={detail.decisions} onChanged={reload} planPhaseId={planPhaseId} />
          </div>

          <div className="card">
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Blocker</h4>
            <BlockerList projectId={projectId} blockers={detail.blockers} onChanged={reload} planPhaseId={planPhaseId} />
          </div>
        </>
      ) : (
        <div className="card">
          <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Dateien</h4>
          {detail.documents.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Dateien.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 0.75rem" }}>
              {detail.documents.map((doc) => (
                <li key={doc.id} className="toolbar" style={{ fontSize: "0.85rem", padding: "0.25rem 0" }}>
                  <a href={api.downloadDocumentUrl(doc.id)} target="_blank" rel="noreferrer">
                    {CATEGORY_ICONS[categorize(doc.mimetype, doc.dateiname)]} {doc.dateiname}
                  </a>
                  <button
                    type="button"
                    onClick={() => handleDeleteDocument(doc.id)}
                    style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <input
            type="file"
            multiple
            disabled={uploading}
            onChange={(e) => {
              handleUploadFiles(e.target.files);
              e.target.value = "";
            }}
            style={{ fontSize: "0.85rem" }}
          />
          {uploading && <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Lädt hoch …</p>}
        </div>
      )}
    </div>
  );
}
