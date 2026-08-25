import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import type {
  CandidatePerson,
  PhaseMetricsOut,
  PlanPhaseAssignmentSummary,
  PlanPhasePersonActuals,
  ProjectActualsCoverage,
} from "../../../types";

function fmtFte(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(2)} FTE`;
}

// P18/B-6, P20.1 (Auftrag Abschnitt 7-10/20): Direct Assignment ist der VOLLSTÄNDIGE normale
// Ressourcenplanungsflow einer Leaf-PlanPhase - zeigt die verfügbare Kapazität der gewählten
// Person über den GESAMTEN Phasenzeitraum (compute_person_capacity_for_range), nicht nur
// einen Monats-Bucket. Kein Rollen-Picker, keine ResourceDemand-Begriffe - der Projektleiter
// muss diese technischen Konzepte nicht kennen (Auftrag Abschnitt 44).
function AssignPersonForm({
  planPhaseId,
  forecastStart,
  forecastEnd,
  onAssigned,
  onCancel,
}: {
  planPhaseId: number;
  forecastStart: string | null;
  forecastEnd: string | null;
  onAssigned: (summary: PlanPhaseAssignmentSummary) => void;
  onCancel: () => void;
}) {
  const [candidates, setCandidates] = useState<CandidatePerson[]>([]);
  const [personId, setPersonId] = useState<number | null>(null);
  const [fte, setFte] = useState(0.2);
  const [availableFte, setAvailableFte] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPlanPhaseAssignmentCandidates(planPhaseId).then(setCandidates).catch(() => setCandidates([]));
  }, [planPhaseId]);

  useEffect(() => {
    setAvailableFte(null);
    if (personId == null || !forecastStart || !forecastEnd) return;
    api
      .getPersonCapacityRange(personId, forecastStart, forecastEnd)
      .then((c) => setAvailableFte(c.available_fte))
      .catch(() => setAvailableFte(null));
  }, [personId, forecastStart, forecastEnd]);

  const handleAssign = async () => {
    if (personId == null) return;
    setSaving(true);
    setError(null);
    try {
      const summary = await api.assignPersonToPlanPhase(planPhaseId, { person_id: personId, fte });
      onAssigned(summary);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const restDanach = availableFte != null ? availableFte - fte : null;

  return (
    <div style={{ marginTop: "0.5rem", padding: "0.6rem", background: "#f7f9fc", borderRadius: "0.4rem" }}>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.78rem" }}>{error}</p>}
      <div className="field-row" style={{ marginTop: 0 }}>
        <label style={{ flex: 1 }}>
          Person
          <PersonPicker value={personId} onChange={setPersonId} />
        </label>
        <label>
          FTE
          <input type="number" min={0.05} max={2} step={0.05} value={fte} onChange={(e) => setFte(Number(e.target.value))} style={{ width: "4.5rem" }} />
        </label>
      </div>
      {personId != null && (
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.35rem 0 0" }}>
          {availableFte == null
            ? "Verfügbare Kapazität über den Phasenzeitraum unbekannt (kein Zeitraum oder keine Kapazitätsdaten)."
            : `Verfügbar im Phasenzeitraum: ${availableFte.toFixed(2)} FTE · Rest danach: ${restDanach!.toFixed(2)} FTE`}
        </p>
      )}
      {candidates.length > 0 && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
          Vorschläge: {candidates.slice(0, 5).map((c) => `${c.display_name} (${c.available_fte.toFixed(2)})`).join(", ")}
        </p>
      )}
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
        <button type="button" className="btn" disabled={personId == null || saving} onClick={handleAssign}>
          {saving ? "Speichert …" : "Zuweisen"}
        </button>
        <button type="button" className="btn secondary" onClick={onCancel}>
          Abbrechen
        </button>
      </div>
    </div>
  );
}

// P20.1 (Kapazitäts-UX radikal vereinfacht, Auftrag Abschnitt 7-10/20): der komplette normale
// Ressourcenplanungsflow einer Leaf-PlanPhase. plan_fte hat hier seine EINDEUTIGE primäre
// Bearbeitungsstelle (Abschnitt 20) - keine zweite Editierstelle im Übersicht-Tab mehr.
// Bewusst ENTFERNT gegenüber der Vorgängerversion: Rollen-Picker/"Rollen aufschlüsseln"/
// "Ohne Rolle"/ResourceDemand-Begriffe - ResourceRole/ResourceDemand bleiben als Legacy/
// Compat-Datenmodell bestehen (siehe CONCEPT.md), aber ein Projektleiter muss sie in diesem
// normalen Flow nicht mehr kennen.
export default function PlanPhaseCapacityTab({
  projectId,
  planPhaseId,
  planFte,
  forecastStart,
  forecastEnd,
  metrics,
  assignmentSummary,
  onChanged,
  onUpdatePlanFte,
}: {
  projectId: number;
  planPhaseId: number;
  planFte: number | null;
  forecastStart: string | null;
  forecastEnd: string | null;
  metrics: PhaseMetricsOut;
  // P19.2 (Round-Trip-Reduktion, Gap 3): bereits in PlanPhaseDetail gebündelt (dieselbe
  // Auswertung wie GET .../assignment-summary) - wird bevorzugt statt eines eigenen Fetches
  // beim Öffnen des Tabs verwendet. Optional gehalten, falls ein künftiger Aufrufer diese Prop
  // (noch) nicht mitgibt - dann fällt die Komponente auf den eigenständigen Endpoint zurück.
  assignmentSummary?: PlanPhaseAssignmentSummary;
  onChanged: () => void;
  // P20.1 (Auftrag Abschnitt 20): einzige Bearbeitungsstelle für plan_fte.
  onUpdatePlanFte: (value: number | null) => void;
}) {
  const [summary, setSummary] = useState<PlanPhaseAssignmentSummary | null>(assignmentSummary ?? null);
  // P20.5 (Kapazität-Tab-Karte "Steuerung", siehe
  // P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 26): Projekt-Coverage ist eine
  // eigene, projektweite Kennzahl (P20.3) - hier nur zusätzlich eingeblendet, damit der
  // Projektleiter beim Blick auf eine einzelne Phase sofort sieht, wie vollständig das
  // Mapping im ganzen Projekt gerade ist. Kein Health-Wert.
  const [coverage, setCoverage] = useState<ProjectActualsCoverage | null>(null);
  useEffect(() => {
    api.getProjectActualsCoverage(projectId).then(setCoverage).catch(() => setCoverage(null));
  }, [projectId]);
  // P20.6 (Personen-Drilldown + Planned-vs-Actual, siehe
  // P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/18/24/25): erst bei Bedarf
  // geladen ("Details ▾" aufklappen), kein zusätzlicher Call beim bloßen Öffnen des Tabs.
  const [showPersonDetails, setShowPersonDetails] = useState(false);
  const [personActuals, setPersonActuals] = useState<PlanPhasePersonActuals | null>(null);
  useEffect(() => {
    if (!showPersonDetails) return;
    api.getPlanPhasePersonActuals(planPhaseId).then(setPersonActuals).catch(() => setPersonActuals(null));
  }, [showPersonDetails, planPhaseId]);
  const [showAssignForm, setShowAssignForm] = useState(false);

  // P19.2: die gebündelte Zusammenfassung aus PlanPhaseDetail bevorzugen (kein Extra-Call) -
  // nur ohne sie wird der eigenständige Endpoint separat abgerufen.
  useEffect(() => {
    if (assignmentSummary) {
      setSummary(assignmentSummary);
    } else {
      api.getPlanPhaseAssignmentSummary(planPhaseId).then(setSummary).catch(() => setSummary(null));
    }
  }, [planPhaseId, assignmentSummary]);

  const handleAssigned = (newSummary: PlanPhaseAssignmentSummary) => {
    setShowAssignForm(false);
    setSummary(newSummary);
    onChanged();
  };

  const handleUnassign = async (personId: number) => {
    const newSummary = await api.unassignPersonFromPlanPhase(planPhaseId, personId);
    setSummary(newSummary);
    onChanged();
  };

  const assignmentOpenFte = summary?.open_fte ?? null;
  const overassigned = assignmentOpenFte != null && assignmentOpenFte < 0;

  return (
    <div>
      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kapazität</h4>
        <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
          <label>
            Geplanter Ressourcenbedarf (FTE)
            <input
              key={`${planPhaseId}-fte-${planFte}`}
              type="number"
              min={0}
              step={0.05}
              defaultValue={planFte ?? ""}
              placeholder="—"
              style={{ maxWidth: "8rem" }}
              onBlur={(e) => {
                const raw = e.target.value.trim();
                onUpdatePlanFte(raw === "" ? null : Number(raw));
              }}
            />
          </label>
          <div>
            <strong>Planstunden:</strong> {metrics.plan_hours == null ? "—" : `${metrics.plan_hours} h`}
          </div>
        </div>
      </div>

      {/* P20.4 (Auftrag Abschnitt 24): die generischen Phasen-Rohmetriken (Ist-Aufwand/
          Aufwandsverbrauch/Zeit verstrichen/Restlicher Planaufwand/Überverbrauch) sind seit
          P20.4 ausschließlich Teil der "Steuerung"-Karte im Übersicht-Tab ("WO STEHEN WIR",
          siehe PlanPhaseWorkspace.tsx) - hier im Kapazität-Tab bewusst NICHT dupliziert, um
          die Trennung "Übersicht = WAS/WANN/WO STEHEN WIR" vs. "Kapazität = WIE VIEL/WER"
          nicht zu verwässern. Was hier bleibt, ist kapazitätsspezifisch: der Personen-
          Drilldown (Planned-vs-Actual Personen) und die projektweite Mapping-Coverage als
          Vertrauensindikator für die Ressourcenplanung - beides steht nirgends sonst. Bewusst
          KEINE Ampel/Bewertung (Auftrag Abschnitt 21). */}
      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Ist-Aufwand nach Person</h4>
        <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
          <div className="toolbar" style={{ justifyContent: "flex-start", gap: "0.5rem" }}>
            <span>
              <strong>Ist-Aufwand:</strong>{" "}
              {metrics.ist_hours == null ? "Noch nicht eindeutig zugeordnet" : `${metrics.ist_hours} h`}
            </span>
            {metrics.ist_hours != null && (
              <button
                type="button"
                onClick={() => setShowPersonDetails((v) => !v)}
                style={{ border: "none", background: "none", cursor: "pointer", padding: 0, fontSize: "0.78rem", color: "var(--blau)" }}
              >
                {showPersonDetails ? "Details ▴" : "Details ▾"}
              </button>
            )}
          </div>
          {coverage && coverage.project_ist_total > 0 && (
            <div style={{ paddingTop: "0.3rem", borderTop: "1px solid var(--border)", color: "var(--text-muted)" }}>
              <strong>Ist-Zuordnung (Projekt):</strong>{" "}
              {coverage.coverage_pct == null ? "—" : `${coverage.coverage_pct}%`}
              {coverage.unmapped_total > 0 && ` (${coverage.unmapped_total} h nicht zugeordnet)`}
            </div>
          )}
        </div>

        {/* P20.6 (Personen-Drilldown + Planned-vs-Actual, siehe
            P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/18/24/25): keine
            automatische Änderung der Ressourcenplanung, reine Anzeige. */}
        {showPersonDetails && (
          <div style={{ marginTop: "0.6rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border)", fontSize: "0.82rem" }}>
            {personActuals == null ? (
              <p style={{ color: "var(--text-muted)" }}>Lädt …</p>
            ) : (
              <>
                {personActuals.persons.length === 0 ? (
                  <p style={{ color: "var(--text-muted)" }}>Keine Ist-Stunden mit bekanntem Autor.</p>
                ) : (
                  personActuals.persons.map((p) => (
                    <div key={p.jira_account_id} className="toolbar" style={{ padding: "0.1rem 0" }}>
                      <span>{p.display_name}</span>
                      <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        {!p.planned && (
                          <span style={{ color: "var(--orange, #a65b00)", fontSize: "0.75rem" }}>nicht eingeplant</span>
                        )}
                        <strong>{p.hours} h</strong>
                      </span>
                    </div>
                  ))
                )}
                {personActuals.planned_without_actual.length > 0 && (
                  <p style={{ color: "var(--text-muted)", margin: "0.4rem 0 0" }}>
                    Eingeplant, bisher kein Ist:{" "}
                    {personActuals.planned_without_actual.map((p) => p.person_name).join(", ")}
                  </p>
                )}
                {personActuals.unplanned_actual_hours != null && personActuals.unplanned_actual_hours > 0 && (
                  <p style={{ color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
                    Davon durch nicht eingeplante Ressourcen: {personActuals.unplanned_actual_hours} h
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <div className="toolbar">
          <h4 style={{ color: "var(--navy)", margin: 0 }}>Personenbesetzung</h4>
          {!showAssignForm && (
            <button type="button" className="btn secondary" style={{ fontSize: "0.78rem" }} onClick={() => setShowAssignForm(true)}>
              + Mitarbeiter zuweisen
            </button>
          )}
        </div>

        {summary == null ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lädt …</p>
        ) : summary.assignments.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.4rem" }}>Noch niemand zugeordnet.</p>
        ) : (
          <div style={{ marginTop: "0.4rem" }}>
            {summary.assignments.map((a) => (
              <div key={a.person_id} className="toolbar" style={{ fontSize: "0.85rem", padding: "0.15rem 0" }}>
                <span>
                  {a.person_name} — {a.fte.toFixed(2)} FTE
                </span>
                <button
                  type="button"
                  onClick={() => handleUnassign(a.person_id)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {showAssignForm && (
          <AssignPersonForm
            planPhaseId={planPhaseId}
            forecastStart={forecastStart}
            forecastEnd={forecastEnd}
            onAssigned={handleAssigned}
            onCancel={() => setShowAssignForm(false)}
          />
        )}

        {summary != null && (
          <div
            style={{
              marginTop: "0.6rem",
              paddingTop: "0.5rem",
              borderTop: "1px solid var(--border)",
              display: "flex",
              gap: "1rem",
              flexWrap: "wrap",
              fontSize: "0.85rem",
            }}
          >
            <span>
              <strong>Bedarf:</strong> {fmtFte(summary.plan_fte)}
            </span>
            <span>
              <strong>Besetzt:</strong> {summary.assigned_fte.toFixed(2)}
            </span>
            <span style={{ color: overassigned ? "var(--rot)" : undefined }}>
              <strong>{overassigned ? "Überbesetzt:" : "Offen:"}</strong>{" "}
              {assignmentOpenFte == null ? "—" : Math.abs(assignmentOpenFte).toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
