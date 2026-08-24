import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import type {
  AdminResourceRole,
  CandidatePerson,
  PhaseMetricsOut,
  PlanPhaseAssignmentSummary,
  PlanPhasePersonActuals,
  ProjectActualsCoverage,
  ResourceDemand,
} from "../../../types";

const MONAT_NAMEN = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];

// Periode ("Apr 26") aus forecast_start ableiten - ResourceDemand ist im Backend immer
// periodengebunden (constants.parse_period), auch wenn die optionale Rollen-Aufschlüsselung
// pro Phase nur eine einzelne Rolle-FTE-Zeile zeigen will. Für Phasen ohne Termin: laufender
// Monat.
function defaultPeriod(forecastStart: string | null): string {
  const d = forecastStart ? new Date(forecastStart + "T00:00:00") : new Date();
  if (Number.isNaN(d.getTime())) return `${MONAT_NAMEN[new Date().getMonth()]} ${String(new Date().getFullYear()).slice(2)}`;
  return `${MONAT_NAMEN[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`;
}

function fmtFte(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(2)} FTE`;
}

// P18/B-6 (CONCEPT.md Abschnitt 5): Direct Assignment UX - primärer Weg, eine Person
// zuzuordnen, OHNE vorher eine Rolle wählen zu müssen. Zeigt die verfügbare Kapazität der
// gewählten Person über den GESAMTEN Phasenzeitraum (Abschnitt 6b.11,
// compute_person_capacity_for_range), nicht nur einen Monats-Bucket.
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
            : `Verfügbar: ${availableFte.toFixed(2)} FTE · Rest danach: ${restDanach!.toFixed(2)} FTE`}
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

// P19.2 (Kapazität-Tab N+1-Fix): die Zuordnungen kommen jetzt bereits gebündelt über
// demand.assignments aus PlanPhaseDetail (siehe ResourceDemandOut.assignments) - kein eigener
// listResourceAssignments-Call mehr beim Aufklappen einer Rolle nötig. Nur die Kandidatenliste
// bleibt ein gezielter Call (dynamisch, hängt von aktueller Kapazität ab, wird nur beim
// Aufklappen dieser einen Rolle abgerufen - kein N+1, da stets nur eine Rolle gleichzeitig
// aufgeklappt ist).
function DemandAssignments({ demand, onChanged }: { demand: ResourceDemand; onChanged: () => void }) {
  const [candidates, setCandidates] = useState<CandidatePerson[]>([]);
  const [personId, setPersonId] = useState<number | null>(null);
  const [fte, setFte] = useState(0.2);
  const [error, setError] = useState<string | null>(null);

  const refreshCandidates = () => {
    api.getResourceDemandCandidates(demand.id).then(setCandidates).catch(() => setCandidates([]));
  };

  useEffect(refreshCandidates, [demand.id]);

  const handleAssign = async () => {
    if (personId == null) return;
    try {
      await api.createResourceAssignment(demand.id, { person_id: personId, fte });
      setPersonId(null);
      refreshCandidates();
      onChanged();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleRemove = async (assignmentId: number) => {
    await api.deleteResourceAssignment(assignmentId);
    refreshCandidates();
    onChanged();
  };

  const assignments = demand.assignments;

  return (
    <div style={{ marginTop: "0.4rem", paddingLeft: "0.5rem", borderLeft: "2px solid var(--border)" }}>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.78rem" }}>{error}</p>}
      {assignments.length === 0 ? (
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.2rem 0" }}>Noch niemand zugeordnet.</p>
      ) : (
        assignments.map((a) => (
          <div key={a.id} className="toolbar" style={{ fontSize: "0.82rem", padding: "0.1rem 0" }}>
            <span>
              {a.person_name} — {a.fte.toFixed(2)} FTE
            </span>
            <button type="button" onClick={() => handleRemove(a.id)} style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}>
              ×
            </button>
          </div>
        ))
      )}
      <div className="field-row" style={{ marginTop: "0.35rem" }}>
        <label style={{ flex: 1 }}>
          Person zuordnen
          <PersonPicker value={personId} onChange={setPersonId} />
        </label>
        <label>
          FTE
          <input type="number" min={0.1} max={2} step={0.1} value={fte} onChange={(e) => setFte(Number(e.target.value))} style={{ width: "4.5rem" }} />
        </label>
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={personId == null} onClick={handleAssign}>
          Zuordnen
        </button>
      </div>
      {candidates.length > 0 && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
          Verfügbar: {candidates.map((c) => `${c.display_name} (${c.available_fte.toFixed(2)})`).join(", ")}
        </p>
      )}
    </div>
  );
}

// P11/P18-B6 (PlanPhase Workspace, Tab "Kapazität"): Plan-FTE + Planstunden als Kopfzeile,
// darunter PRIMÄR die direkte Personenbesetzung ohne Rollen-Zwang (Abschnitt 5/6b.4/6b.10) -
// "Bedarf/Besetzt/Offen". Die Rollen-Aufschlüsselung (ResourceDemand) bleibt als expliziter,
// eingeklappter Zusatzabschnitt "Rollen aufschlüsseln" bestehen (optional, Abschnitt 6b.4) -
// niemals Voraussetzung für eine normale Personenzuweisung.
export default function PlanPhaseCapacityTab({
  projectId,
  planPhaseId,
  planFte,
  forecastStart,
  forecastEnd,
  demands,
  metrics,
  assignmentSummary,
  onChanged,
}: {
  projectId: number;
  planPhaseId: number;
  planFte: number | null;
  forecastStart: string | null;
  forecastEnd: string | null;
  demands: ResourceDemand[];
  metrics: PhaseMetricsOut;
  // P19.2 (Round-Trip-Reduktion, Gap 3): bereits in PlanPhaseDetail gebündelt (dieselbe
  // Auswertung wie GET .../assignment-summary) - wird bevorzugt statt eines eigenen Fetches
  // beim Öffnen des Tabs verwendet. Optional gehalten, falls ein künftiger Aufrufer diese Prop
  // (noch) nicht mitgibt - dann fällt die Komponente auf den eigenständigen Endpoint zurück.
  assignmentSummary?: PlanPhaseAssignmentSummary;
  onChanged: () => void;
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
  const [showRoleBreakdown, setShowRoleBreakdown] = useState(demands.length > 0);
  const [roles, setRoles] = useState<AdminResourceRole[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [addRoleId, setAddRoleId] = useState("");
  const [addFte, setAddFte] = useState(0.2);
  const [error, setError] = useState<string | null>(null);

  // P19.2: die gebündelte Zusammenfassung aus PlanPhaseDetail bevorzugen (kein Extra-Call) -
  // nur ohne sie wird der eigenständige Endpoint separat abgerufen.
  useEffect(() => {
    if (assignmentSummary) {
      setSummary(assignmentSummary);
    } else {
      api.getPlanPhaseAssignmentSummary(planPhaseId).then(setSummary).catch(() => setSummary(null));
    }
  }, [planPhaseId, assignmentSummary]);

  useEffect(() => {
    api.listResourceRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

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

  const handleAddDemand = async () => {
    if (!addRoleId) return;
    try {
      await api.createResourceDemand(projectId, {
        plan_phase_id: planPhaseId,
        resource_role_id: Number(addRoleId),
        period: defaultPeriod(forecastStart),
        fte: addFte,
      });
      setAddRoleId("");
      setAddFte(0.2);
      onChanged();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleDeleteDemand = async (demandId: number) => {
    await api.deleteResourceDemand(demandId);
    if (expandedId === demandId) setExpandedId(null);
    onChanged();
  };

  // P14.2 (Reconciliation sichtbar): plan_fte bleibt führend (CONCEPT.md Abschnitt 3/6) - wenn
  // die optionale Rollen-Aufschlüsselung mehr FTE summiert als geplant, wird das nicht
  // automatisch korrigiert, sondern klar erklärt statt eine verwirrende negative Zahl zu zeigen.
  const breakdownOpenFte = metrics.reconciliation.open_fte;
  const breakdownOverAllocated = breakdownOpenFte != null && breakdownOpenFte < 0;

  const assignmentOpenFte = summary?.open_fte ?? null;
  const overassigned = assignmentOpenFte != null && assignmentOpenFte < 0;

  return (
    <div>
      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kapazität</h4>
        <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
          <div>
            <strong>Geplanter Ressourcenbedarf:</strong> {fmtFte(planFte)}
          </div>
          <div>
            <strong>Planstunden:</strong> {metrics.plan_hours == null ? "—" : `${metrics.plan_hours} h`}
          </div>
        </div>
      </div>

      {/* P20.5 (Steuerung, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 26):
          Rohmetriken aus PhaseMetricsOut (P20.4) - bewusst KEINE Ampel/Bewertung (BD-3 bleibt
          separat offen). "Ist-Zuordnung" ist die Projekt-Coverage (P20.3), nicht phasen-
          scoped - deshalb explizit als "Projekt" gekennzeichnet, um keine falsche Genauigkeit
          vorzutäuschen. */}
      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Steuerung</h4>
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
          <div>
            <strong>Aufwandsverbrauch:</strong>{" "}
            {metrics.effort_consumption_pct == null ? "—" : `${metrics.effort_consumption_pct}%`}
          </div>
          <div>
            <strong>Zeitfortschritt:</strong>{" "}
            {metrics.time_progress_pct == null ? "—" : `${metrics.time_progress_pct}%`}
          </div>
          {metrics.remaining_plan_hours != null && (
            <div>
              <strong>Verbleibender Planaufwand:</strong> {metrics.remaining_plan_hours} h
            </div>
          )}
          {metrics.overrun_hours != null && metrics.overrun_hours > 0 && (
            <div style={{ color: "var(--rot)" }}>
              <strong>Überverbrauch:</strong> {metrics.overrun_hours} h
            </div>
          )}
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

      {/* P19.2 (visuelle Hierarchie Direct-Assignment vs. optionale Rollenaufschlüsselung,
          Abschnitt 7/8): Primärpfad durch Akzent-Rahmen optisch als "die Ebene, die zuerst
          zählt" hervorgehoben - rein Layout/Typografie, keine Funktionsänderung. */}
      <div className="card" style={{ marginBottom: "0.75rem", borderLeft: "3px solid var(--blau)" }}>
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

      {/* P19.2: bewusst zurückhaltendere Rahmung (gestrichelter Rand, gedämpfter Hintergrund,
          kleinere Schrift) als der Primärpfad oben - signalisiert "optionale Zusatzebene", ohne
          etwas an der Funktion zu ändern (weiterhin derselbe DemandAssignments-Flow). */}
      <div className="card" style={{ marginTop: "1rem", background: "#f7f9fc", border: "1px dashed var(--border)" }}>
        <button
          type="button"
          onClick={() => setShowRoleBreakdown((v) => !v)}
          style={{ border: "none", background: "none", cursor: "pointer", padding: 0, fontSize: "0.85rem", fontWeight: 600, color: "var(--text-muted)" }}
        >
          {showRoleBreakdown ? "▾" : "▸"} Rollen aufschlüsseln (optional)
        </button>
        <p style={{ fontSize: "0.76rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
          Nie Voraussetzung für eine direkte Personenzuweisung - nur zur optionalen
          Rollen-/Skill-Aufschlüsselung des Bedarfs.
        </p>

        {showRoleBreakdown && (
          <div style={{ marginTop: "0.5rem" }}>
            {demands.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Rollen-Aufschlüsselung.</p>
            ) : (
              demands.map((d) => (
                <div key={d.id} style={{ marginBottom: "0.5rem", paddingBottom: "0.4rem", borderBottom: "1px solid var(--border)" }}>
                  <div className="toolbar">
                    <button
                      type="button"
                      onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                      style={{ border: "none", background: "none", cursor: "pointer", textAlign: "left", padding: 0, fontSize: "0.88rem", fontWeight: 600, color: "var(--navy)" }}
                    >
                      {expandedId === d.id ? "▾" : "▸"} {d.resource_role_name}
                    </button>
                    <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", fontSize: "0.85rem" }}>
                      <span>Bedarf {d.fte.toFixed(2)} FTE</span>
                      <span style={{ color: d.allocation_gap > 0 ? "var(--rot)" : "var(--gruen)" }}>
                        Besetzt {d.assigned_fte.toFixed(2)}
                        {d.allocation_gap > 0 && ` · noch unbesetzt ${d.allocation_gap.toFixed(2)}`}
                      </span>
                      <button type="button" onClick={() => handleDeleteDemand(d.id)} style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}>
                        ×
                      </button>
                    </div>
                  </div>
                  {expandedId === d.id && <DemandAssignments demand={d} onChanged={onChanged} />}
                </div>
              ))
            )}

            <div style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>
                  <strong>Aufgeschlüsselt:</strong> {fmtFte(metrics.reconciliation.breakdown_fte)}
                </span>
                {!breakdownOverAllocated && (
                  <span>
                    <strong>Noch nicht aufgeschlüsselt:</strong> {fmtFte(breakdownOpenFte)}
                  </span>
                )}
              </div>
              {breakdownOverAllocated && (
                <p style={{ color: "var(--rot)", margin: "0.3rem 0 0", fontSize: "0.82rem" }}>
                  Aufgeschlüsselter Bedarf liegt {Math.abs(breakdownOpenFte!).toFixed(2)} FTE über dem geplanten
                  Ressourcenbedarf. Geplanter Ressourcenbedarf bleibt führend.
                </p>
              )}
            </div>

            {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}
            <div className="field-row" style={{ marginTop: "0.6rem" }}>
              <label>
                Rolle hinzufügen
                <select value={addRoleId} onChange={(e) => setAddRoleId(e.target.value)}>
                  <option value="">— wählen —</option>
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                FTE
                <input type="number" min={0.1} step={0.1} value={addFte} onChange={(e) => setAddFte(Number(e.target.value))} style={{ width: "4.5rem" }} />
              </label>
              <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={!addRoleId} onClick={handleAddDemand}>
                + Hinzufügen
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
