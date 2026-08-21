import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import PersonPicker from "../../components/PersonPicker";
import { useUnsavedChanges } from "../../unsavedChanges";
import { PROJECT_STATUS_LABELS, type JiraComponent, type JiraProject, type ProjectStatus } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";
import ProjectTeamSection from "./components/ProjectTeamSection";

// P11 (Planungs-/Kapazitätskonsolidierung): Projektstammdaten (Name/Kunde/Startmonat/Anzahl
// Monate) sind aus dem Planning-Tab hierher umgezogen - reine Stammdaten, kein
// Planungs-Arbeitsschritt (siehe CONCEPT.md). Der batch-/grund-basierte Speichern-Workflow
// (PlanHistory-Audit-Trail) zieht mit um, bleibt aber bewusst auf genau diese vier Felder
// beschränkt - PlanPhase/Milestone/Kapazität speichern weiterhin sofort im Planning-Tab.
export default function ProjectSettingsTab() {
  const { project, reload } = useProjectWorkspace();
  const [error, setError] = useState<string | null>(null);
  const { isDirty, setIsDirty } = useUnsavedChanges();

  const [stammdaten, setStammdaten] = useState({
    name: project.name,
    kunde: project.kunde,
    start_monat: project.start_monat,
    anzahl_monate: project.anzahl_monate,
  });
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saveReason, setSaveReason] = useState("");

  useEffect(() => {
    setStammdaten({ name: project.name, kunde: project.kunde, start_monat: project.start_monat, anzahl_monate: project.anzahl_monate });
    setIsDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, project.name, project.kunde, project.start_monat, project.anzahl_monate]);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  const handleStammdatenChange = (field: "name" | "kunde" | "start_monat" | "anzahl_monate", raw: string) => {
    setStammdaten((prev) => {
      if (field === "anzahl_monate") {
        const value = Number(raw);
        if (!Number.isFinite(value) || value < 1) return prev;
        return { ...prev, anzahl_monate: value };
      }
      if (field === "kunde") return { ...prev, kunde: raw.trim() || null };
      if (field === "start_monat") {
        if (!/^\d{2}\.\d{4}$/.test(raw)) return prev;
        return { ...prev, start_monat: raw };
      }
      if (!raw.trim()) return prev;
      return { ...prev, name: raw.trim() };
    });
    setIsDirty(true);
  };

  const handleSaveStammdaten = async () => {
    setSaving(true);
    setError(null);
    try {
      let kommentarId: number | null = null;
      if (saveReason.trim()) {
        const comment = await api.createComment(project.id, { text: saveReason.trim() });
        kommentarId = comment.id;
      }
      const batchId = crypto.randomUUID();
      const changes: Partial<{ name: string; kunde: string | null; start_monat: string; anzahl_monate: number }> = {};
      if (stammdaten.name !== project.name) changes.name = stammdaten.name;
      if (stammdaten.kunde !== project.kunde) changes.kunde = stammdaten.kunde;
      if (stammdaten.start_monat !== project.start_monat) changes.start_monat = stammdaten.start_monat;
      if (stammdaten.anzahl_monate !== project.anzahl_monate) changes.anzahl_monate = stammdaten.anzahl_monate;
      if (Object.keys(changes).length > 0) {
        await api.updateProject(project.id, { ...changes, kommentar_id: kommentarId, batch_id: batchId });
      }
      setSaveReason("");
      setSavedAt(new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }));
      setIsDirty(false);
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [relevantJiraProjects, setRelevantJiraProjects] = useState<JiraProject[]>([]);
  const [pickerJiraProjectKey, setPickerJiraProjectKey] = useState("");
  const [pickerComponents, setPickerComponents] = useState<JiraComponent[]>([]);
  const [pickerLabels, setPickerLabels] = useState<string[]>([]);

  useEffect(() => {
    api
      .jiraStatus()
      .then((status) => {
        setJiraConfigured(status.configured);
        if (!status.configured) return;
        return api.jiraListProjects().then((all) => setRelevantJiraProjects(all.filter((p) => p.relevant)));
      })
      .catch(() => setJiraConfigured(false));
  }, []);

  const handlePickerJiraProjectChange = async (key: string) => {
    setPickerJiraProjectKey(key);
    setPickerComponents([]);
    setPickerLabels([]);
    if (!key) return;
    try {
      const [components, labels] = await Promise.all([api.jiraListComponents(key), api.jiraListLabels(key)]);
      setPickerComponents(components);
      setPickerLabels(labels);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    if (project.jira_project_key && jiraConfigured && pickerJiraProjectKey !== project.jira_project_key) {
      handlePickerJiraProjectChange(project.jira_project_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.jira_project_key, jiraConfigured]);

  const handleStatusChange = async (status: ProjectStatus) => {
    await api.updateProject(project.id, { status });
    reload();
  };

  const handleProjektleiterChange = async (personId: number | null) => {
    await api.updateProject(project.id, { projektleiter_person_id: personId });
    reload();
  };

  const handleJiraComponentChange = async (raw: string) => {
    await api.updateProject(project.id, { jira_component: raw.trim() || null });
    reload();
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="toolbar" style={{ marginBottom: "0.75rem" }}>
          <h3 style={{ color: "var(--navy)", margin: 0 }}>Projektstammdaten</h3>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            {!isDirty && savedAt && <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Gespeichert um {savedAt}</span>}
            <input
              value={saveReason}
              onChange={(e) => setSaveReason(e.target.value)}
              placeholder="Grund für diese Änderung (optional)"
              style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", width: "14rem" }}
            />
            <button type="button" className="btn" disabled={!isDirty || saving} onClick={handleSaveStammdaten}>
              {saving ? "Speichert …" : "Speichern"}
            </button>
          </div>
        </div>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Projektname
            <input key={project.name} defaultValue={stammdaten.name} onBlur={(e) => handleStammdatenChange("name", e.target.value)} />
          </label>
          <label>
            Kunde
            <input
              key={project.kunde ?? ""}
              defaultValue={stammdaten.kunde ?? ""}
              onBlur={(e) => handleStammdatenChange("kunde", e.target.value)}
            />
          </label>
          <label>
            Startmonat (MM.YYYY)
            <input
              key={project.start_monat}
              defaultValue={stammdaten.start_monat}
              pattern="\d{2}\.\d{4}"
              onBlur={(e) => handleStammdatenChange("start_monat", e.target.value)}
            />
          </label>
          <label>
            Anzahl Monate
            <input
              key={project.anzahl_monate}
              type="number"
              min={1}
              max={24}
              defaultValue={stammdaten.anzahl_monate}
              onBlur={(e) => handleStammdatenChange("anzahl_monate", e.target.value)}
            />
          </label>
        </div>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.5rem 0 0" }}>
          Start/Anzahl Monate bestimmen den Planungszeitraum (u.a. für Gantt/PPTX-Export).
        </p>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projektparameter</h3>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Status
            <select value={project.status} onChange={(e) => handleStatusChange(e.target.value as ProjectStatus)}>
              {Object.entries(PROJECT_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Projektleiter
            <PersonPicker value={project.projektleiter_person_id} onChange={handleProjektleiterChange} />
          </label>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <ProjectTeamSection projectId={project.id} />
      </div>

      <div className="card">
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Jira-Verknüpfung</h3>
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Jira-Komponente/Label (für Ist-FTE des gesamten Projekts)
          <input
            key={project.jira_component ?? ""}
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px" }}
            defaultValue={project.jira_component ?? ""}
            placeholder="z. B. ETE"
            onBlur={(e) => handleJiraComponentChange(e.target.value)}
          />
        </label>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.35rem 0 0" }}>
          {project.jira_component ? (
            <>
              Aktuell gespeichert: <strong>{project.jira_component}</strong>
            </>
          ) : (
            "Noch nichts gespeichert — ohne Wert bleibt die Ist-FTE-Berechnung für dieses Projekt leer."
          )}
        </p>
        {jiraConfigured && !project.jira_project_key && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            <label>
              Oder aus Jira-Projekt wählen
              <select value={pickerJiraProjectKey} onChange={(e) => handlePickerJiraProjectChange(e.target.value)}>
                <option value="">
                  {relevantJiraProjects.length === 0
                    ? "— keine Jira-Projekte als 'wird geplant' markiert —"
                    : "— Jira-Projekt wählen —"}
                </option>
                {relevantJiraProjects.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.name} ({p.key})
                  </option>
                ))}
              </select>
            </label>
            {pickerJiraProjectKey && (
              <label>
                Komponente/Label
                <select
                  value={project.jira_component ?? ""}
                  onChange={(e) => {
                    if (e.target.value) handleJiraComponentChange(e.target.value);
                  }}
                >
                  <option value="">— wählen —</option>
                  {pickerComponents.length > 0 && (
                    <optgroup label="Components">
                      {pickerComponents.map((c) => (
                        <option key={`c-${c.id}`} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerLabels.length > 0 && (
                    <optgroup label="Labels">
                      {pickerLabels.map((l) => (
                        <option key={`l-${l}`} value={l}>
                          {l}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerComponents.length === 0 && pickerLabels.length === 0 && (
                    <option value="" disabled>
                      Keine Components oder Labels in diesem Jira-Projekt gefunden
                    </option>
                  )}
                </select>
              </label>
            )}
          </div>
        )}
        {project.jira_project_key && (
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.5rem 0 0" }}>
            Verknüpft mit Jira-Projekt: {project.jira_project_key}
          </p>
        )}
        <p style={{ fontSize: "0.8rem", margin: "0.75rem 0 0" }}>
          Sync-Status und offene Issues siehe <Link to={`/projekte/${project.id}/jira`}>Jira-Tab</Link>.
        </p>
      </div>
    </div>
  );
}
