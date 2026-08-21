# P18 DESIGN & IMPLEMENTATION PLAN

**Grob-/Feinplanung, Capacity Reconciliation & Rebuild-Safe CONCEPT.md**

Status: **Design/Spezifikation abgeschlossen. Keine Implementierung in diesem Durchgang.**
Die fachlich verbindliche Spezifikation lebt in [`CONCEPT.md`](CONCEPT.md) Abschnitt 6
(korrigiert) und Abschnitt 6a (neu) — dieses Dokument ist die Prozess-/Planungssicht darauf
(Audit-Nachweis, Paketierung, Abhängigkeiten, Testfälle, Empfehlung). Bei Widerspruch
zwischen diesem Dokument und CONCEPT.md gilt CONCEPT.md.

---

## 1. Executive Summary

P1–P17 haben `PlanPhase`/`ResourceDemand`/`ResourceAssignment` als tagegenaue Planungs- und
Kapazitätswahrheit etabliert, aber nie erklärt, warum ein Projektleiter zusätzlich eine
projektweite Monats-`ResourceDemand` (`plan_phase_id = NULL`) pflegt und wie sie sich zur
Phasenplanung verhält. P18 liefert diese fachliche Erklärung ("Grobplanung" vs.
"Feinplanung", zwei Konkretisierungsgrade derselben Planung) und eine geprüfte, minimal-
invasive Reconciliation-Formel — **ohne** neues Datenmodell, neue Planning Engine oder neue
Available-Capacity-Berechnung.

Der Audit deckte zusätzlich zwei **bereits heute bestehende** Lücken auf, die unabhängig
von P18 real sind:

1. Alle Portfolio-/Cockpit-Aggregationen (`capacity-heatmap`, `allocation-gaps`, `roles`,
   `gap-engine/capacity`, Cockpit-Kapazität) summieren `ResourceDemand` **ohne**
   `plan_phase_id`-Filter — Grob- und Feinplanung werden dort schon heute addiert, wenn
   beide für dieselbe Rolle/Periode existieren (CONCEPT.md Abschnitt 6.3).
2. `ResourceDemandGrid.tsx` (Grobplanungs-UI) filtert seine geladenen `ResourceDemand`-Zeilen
   ebenfalls nicht nach `plan_phase_id`, wodurch eine Zellen-Kollision mit einer
   Phasen-Demand gleicher Rolle/Periode möglich ist (CONCEPT.md Abschnitt 6.3).

Beide Punkte werden als Teil der P18-Implementierungspakete behoben, sind aber **keine
Neuerfindung** — reine Korrektur an bestehendem, ungetestetem Verhalten.

**Ergebnis dieses Durchgangs:** Drei neue Business Decisions (BD-7/8/9, siehe Abschnitt 23)
sind offen. Die fachliche Analyse ist für alle drei eindeutig (Empfehlungen liegen vor),
aber die Umsetzung ändert heute sichtbare Portfolio-Zahlen — das rechtfertigt eine explizite
Freigabe vor Codeänderung. Endergebnis (Abschnitt 28): **BUSINESS DECISION REQUIRED.**

---

## 2. Codebase Validation

Vollständige Prüfung von CONCEPT.md gegen Code, Status je Zeile: CONFIRMED (Doku = Code),
PARTIAL (teilweise zutreffend/unvollständig dokumentiert), CONFLICT (Doku und Code
widersprechen sich oder ein reales Risiko war undokumentiert), MISSING (Code-Verhalten war
in CONCEPT.md gar nicht beschrieben).

| Thema | CONCEPT (vor P18) | Code | Bewertung | Konsequenz |
|---|---|---|---|---|
| Grobplanung als Begriff | nicht benannt, nur "Portfolio-/Monatsachse" | `ResourceDemand.plan_phase_id IS NULL` | MISSING | Abschnitt 6a.1/6a.3 neu dokumentiert (rein begrifflich, kein Codewechsel) |
| Phase Plan-FTE (`plan_fte`) | Source of Truth für Phasenaufwand (Abschnitt 3/5.2) | `PlanPhase.plan_fte`, `phase_metrics_calc.plan_hours` | CONFIRMED | keine Änderung nötig |
| `ResourceDemand`-Semantik | Rollen-Aufschlüsselung, `period` "Apr 26" | `period: Mapped[str]` nicht nullable, auch bei `plan_phase_id` gesetzt | PARTIAL | CONCEPT.md dokumentierte nicht, dass `period` bei Phasen-Demands nur ein einmalig gesetzter Default ist (Abschnitt 6.1 ergänzt) |
| `ResourceAssignment` auf Grob-Demand (Level 3) | nicht erwähnt | keine Einschränkung im Code; `ResourceDemandGrid.tsx` bietet UI dafür bereits | MISSING | Abschnitt 6a.5 dokumentiert dies erstmals — **kein BD nötig**, bereits funktionsfähig |
| Monatsperioden (`constants.parse_period`/`berechne_monate`) | dokumentiert für Available Capacity | `parse_period` erwartet exakt "Apr 26"-Format, keine Datumsbereiche | CONFIRMED | Grenze für Abschnitt 6a.8 (Available Capacity über Phasenzeitraum) explizit gemacht |
| Planstunden (`plan_hours`) | Formel dokumentiert (Abschnitt 5.2) | `phase_metrics_calc.plan_hours`, nutzt `count_weekdays_in_range` | CONFIRMED | Basis für Monatsverteilungsalgorithmus (Abschnitt 6a.6), keine Duplizierung |
| Available Capacity | Formel dokumentiert (Abschnitt 6, jetzt 6.2) | `capacity_calc.compute_person_capacity`, nur Monats-`period` | PARTIAL | CONCEPT.md nannte die Monats-Beschränkung bisher nicht explizit — jetzt in Abschnitt 6.2 ergänzt |
| Portfolio Aggregation (`controlling.py`, `gap_engine.py`, `health.py`) | "keine Doppelzählung" als Grundsatz (Abschnitt 3), aber Aggregation selbst nicht im Detail beschrieben | `ResourceDemand.period == period` **ohne** `plan_phase_id`-Filter in `compute_capacity_gap`, `get_allocation_gaps`, `get_role_analysis`, `_cockpit_capacity` | **CONFLICT** | Wichtigster Fund des Audits — Abschnitt 6.3 (neu) dokumentiert dies als bestehende Lücke; P18.3 behebt sie (abhängig von BD-7/9) |
| GAP Aggregation | Abschnitt 9 (Allocation/Capacity/Utilization Gap) | dieselbe zugrunde liegende `ResourceDemand`-Summe wie Portfolio Aggregation | CONFLICT (identische Ursache) | wird mit demselben Fix (P18.3) behoben |
| Baseline (`BaselineSnapshot`) | friert `PlanPhase`/`Milestone`-Felder ein (Abschnitt 5.3) | `_SNAPSHOT_FIELDS` enthält nur `plan_phase`/`milestone`, kein `resource_demand` | CONFIRMED (als Lücke) | Abschnitt 6a.9/BD-8 — offene Entscheidung, ob/wie Grobplanung eingefroren wird |
| Teilprojekte | `PlanPhase.subproject_id` nullable (Abschnitt 5.4) | `ResourceDemand` hat **kein** `subproject_id`-Feld | CONFIRMED | bestätigt die Arbeitshypothese aus der Auftragsvorgabe: Grobplanung bleibt projektweit (Abschnitt 6a.11) |
| `WorkingTime`/`ResourceProfile` | primär/Fallback dokumentiert (Abschnitt 6) | `_current_working_time` sucht Zeitraum-Überlappung, Fallback auf `ResourceProfile.weekly_hours` | CONFIRMED | keine Änderung nötig |
| `Absence` | fließt in Available Capacity ein | `absence_fte` über `count_weekdays_in_range`-Overlap | CONFIRMED | keine Änderung nötig |
| `Holiday` | fließt in Available Capacity ein | `holiday_fte`, nur wenn `capacity_calendar_id` gesetzt (über `WorkingTime`) | CONFIRMED | keine Änderung nötig; bewusst getrennt von der Nicht-Feiertagsabzug-Konvention bei `plan_hours` (BD-4) — zwei Konventionen koexistieren bereits heute |
| `InternalAllocation` | fließt in Available Capacity ein | `internal_fte`, direkt in FTE gepflegt, kein Werktage-Umweg | CONFIRMED | keine Änderung nötig |

**Zusätzlicher Fund (Frontend, nicht in ursprünglicher Prüfliste, aber P18-relevant):**
`ResourceDemandGrid.tsx::demandFor()` filtert nicht nach `plan_phase_id` — CONFLICT,
dokumentiert in CONCEPT.md Abschnitt 6.3, behoben in P18.4.

---

## 3. Fachliches Zielbild

Siehe CONCEPT.md Abschnitt 6a.1 (vollständig). Kernaussage: Grobplanung und Feinplanung sind
**Konkretisierungsgrade**, keine additiven Bedarfe. Ein Projekt plant nicht zweimal
Kapazität — es beschreibt denselben erwarteten Aufwand mit zunehmender Präzision, von
"~1,5 FTE im Oktober" bis zu tagegenauen Phasen mit Rollen- und Personenbesetzung.

## 4. Grobplanung

Siehe CONCEPT.md Abschnitt 6a.2 (keine neue Tabelle), 6a.3 (Definition), 6a.5
(Reifegrade Level 1–3). Kein neues Datenmodell — `ResourceDemand` mit
`plan_phase_id = NULL` erfüllt bereits alle drei Reifegrade (Gesamt-FTE, Rollen, Personen).

## 5. Feinplanung

Unverändert Abschnitt 5 (Projektplanung, tagegenaue `PlanPhase`) + Abschnitt 6.1
(Phasenachse `ResourceDemand`). P18 ändert an der Feinplanung selbst nichts — sie liefert
nur zusätzlich Input für die Reconciliation (Abschnitt 6a.6).

## 6. Grob-/Fein-Reconciliation

Formeln, Definitionen und vollständig durchgerechnetes Beispiel: CONCEPT.md Abschnitt 6a.3,
6a.6. Kurzfassung:

```
Konsumption(Monat) = max(Grobplanstunden(Monat), Feinplanstunden(Monat))
Noch grob(Monat)    = max(Grobplanstunden(Monat) − Feinplanstunden(Monat), 0)
Konkretisierungsgrad = Feinplanstunden(Monat) / Grobplanstunden(Monat) × 100   (nur wenn Grob > 0)
```

Keine Addition, keine 50/50-Verteilung, keine Doppelzählung — alle drei sind explizite
Nicht-Ziele, die von der Formel eingehalten werden (algebraischer Nachweis: Option A/B sind
identisch, CONCEPT.md Abschnitt 6a.10).

## 7. FTE-/Stunden-Semantik

Siehe CONCEPT.md Abschnitt 6a.4. `plan_fte` (und jede `ResourceDemand.fte`) ist ein
**durchschnittlicher Ressourceneinsatz über den Zeitraum**, keine Tages-Reservierung. Die
technische Semantik bleibt unverändert; ein UI-Label-Vorschlag ("Geplanter
Ressourcenbedarf" statt "Plan-Aufwand", mit Stunden-Erklärzeile) ist optional und kein
Blocker für das Backend-Paket.

## 8. Monthly Distribution Algorithm

Siehe CONCEPT.md Abschnitt 6a.6 — vollständige Formel, Reuse-Nachweis
(`capacity_calc.count_weekdays_in_range`, `capacity_calc._month_bounds`,
`phase_metrics_calc.plan_hours`-Formel) und durchgerechnetes Zahlenbeispiel (Red Bull WMS
Rollout, Okt/Nov/Dez 2026, exakte Werktagszahlen per Python nachgerechnet — keine
Rundungsannahmen).

**Rundungspolitik (Ergänzung, hier statt CONCEPT.md, da rein technisches
Implementierungsdetail):** `phase_hours(M)` wird analog zu `plan_hours` auf 2 Nachkommastellen
gerundet. Da die Summe der Monatsanteile durch Rundung minimal von `plan_hours_total`
abweichen kann (Cent-Rundung, max. ±0,01h je Phase bei ≤3 berührten Monaten), wird **nicht**
nachträglich auf `plan_hours_total` normalisiert — dieselbe Toleranz gilt bereits heute für
`open_fte` (Abschnitt 3, `round(..., 4)`), keine neue Rundungsstrategie nötig.

## 9. Capacity Consumption Source of Truth

Vollständige Matrix inkl. Bewertung der Optionen A–D: CONCEPT.md Abschnitt 6a.10. Empfehlung:
**Option A/B kombiniert** (intern `max()`, UI-seitig als "konkret + noch grob" dargestellt).
Option C (expliziter Planungsmodus) verworfen — unvereinbar mit Phasen, die Monatsgrenzen
überschreiten (ein Monat kann nicht eindeutig "GROB" oder "FEIN" sein, wenn er teilweise
durch eine Phase abgedeckt ist).

## 10. ResourceDemand / Assignment Semantik

CONCEPT.md Abschnitt 6a.2/6a.5 beantwortet die Auftragsfrage aus Abschnitt 17/18 der
Aufgabenstellung explizit: `ResourceDemand` mit `plan_phase_id = NULL` ist bereits heute
**sowohl** reiner Gesamt-FTE-Bedarf (eine Zeile) **als auch** Rollenbedarf pro Monat
(mehrere Zeilen, unterschiedliche `resource_role_id`) — je nachdem, wie viele Zeilen der
Projektleiter anlegt. Kein neues `gross_plan_fte`-Feld nötig. `ResourceAssignment` auf einer
Grob-Demand ist technisch bereits uneingeschränkt möglich und im Frontend
(`ResourceDemandGrid.tsx`) bereits bedienbar — **kein BD, keine neue Funktion nötig,** nur
Dokumentation (jetzt Abschnitt 6a.5) fehlte bisher.

## 11. Available Capacity Integration

CONCEPT.md Abschnitt 6.2 (Grenze: nur Monats-`period`) und Abschnitt 6a.8 (P18-Vorschlag:
Datumsbereich-Variante). Detailformel für die vorgeschlagene Erweiterung
(`compute_person_capacity_for_range`, Name vorläufig):

```
def compute_person_capacity_for_range(db, person_id, range_start, range_end) -> PersonCapacityOut | None:
    total_weekdays = count_weekdays_in_range(range_start, range_end)       # bestehend
    if total_weekdays == 0:
        return None
    accumulated = {nominal: 0, holiday: 0, absence: 0, internal: 0, working_days: 0, ...}
    for month M overlapping [range_start, range_end]:                      # wie 6a.6
        overlap_start, overlap_end = Schnittmenge(M, [range_start, range_end])
        weekdays_M = count_weekdays_in_range(overlap_start, overlap_end)   # bestehend
        month_capacity = compute_person_capacity(db, person_id, period_of(M))  # bestehend, unverändert
        if month_capacity is None:
            continue  # Person hat für diesen Monat kein Profil -> nicht einbeziehbar
        weight = weekdays_M / weekdays_in_month(M)                          # Anteil des Monats im Zeitraum
        accumulated.nominal  += month_capacity.nominal_fte  * weight
        accumulated.holiday  += month_capacity.holiday_fte  * weight
        accumulated.absence  += month_capacity.absence_fte  * weight
        accumulated.internal += month_capacity.internal_fte * weight
    available = accumulated.nominal - accumulated.holiday - accumulated.absence - accumulated.internal
    return PersonCapacityOut(..., available_fte=round(available, 4))
```

Reuse-Nachweis: **keine** neue Holiday-/Absence-/InternalAllocation-Query — jeder Monat ruft
exakt `compute_person_capacity` unverändert auf und gewichtet nur das Ergebnis. Das ist die
in der Aufgabenstellung (Abschnitt 20) geforderte "minimal-invasive Erweiterung" statt einer
neuen Engine. Rundungsproblem bei Teilmonaten: die Gewichtung ist linear über Werktage,
identisch zur Monatsverteilung in Abschnitt 8 — keine zweite Konvention.

## 12. Teilprojekte

CONCEPT.md Abschnitt 6a.11. Grobplanung bleibt projektweit (kein `subproject_id`-Feld auf
`ResourceDemand`, bestätigt durch Modellprüfung). Keine neue Dimension eingeführt — konsistent
mit Abschnitt 40 der Aufgabenstellung ("keine Architektur um ihrer selbst willen").

## 13. Planstände

CONCEPT.md Abschnitt 6a.9. Offene Frage BD-8 (Granularität: je Demand-Zeile vs. aggregierte
Monatssumme). Technisch bereits heute ohne Schemaänderung möglich (`BaselineEntry` ist
generisch genug), daher keine Migration in den betroffenen Paketen vorgesehen, unabhängig
vom Ausgang von BD-8.

## 14. GAP / Controlling Auswirkungen

Der wichtigste Effekt: **sobald** die unter Abschnitt 2 (CONFLICT-Zeile "Portfolio
Aggregation") dokumentierte Lücke behoben wird, ändern sich die von
`GET /controlling/capacity-heatmap`, `/controlling/allocation-gaps`, `/controlling/roles`,
`GET /gap-engine/capacity` und `GET /projects/{id}/cockpit` gelieferten Zahlen für jedes
Projekt, das heute sowohl Grob- als auch Feinplanung für dieselbe Rolle/Periode gepflegt hat
(bisher: Summe; künftig: `max()`, typischerweise niedriger). Das ist **gewollt** (behebt
Doppelzählung), aber ein sichtbarer Zahlensprung im Portfolio-Dashboard am Umstellungstag —
Grund für BD-9 (Rollout additiv vs. direkt).

## 15. UX Design

CONCEPT.md Abschnitt 6a.14 (Planungsstand-Kapazität-Block) und 6a.15 (User Flows 1–10).
Keine neue Seite — Erweiterung von `ProjectPlanningTab.tsx` unterhalb der bestehenden
`ResourceDemandGrid`. `PlanPhaseCapacityTab.tsx` bleibt unverändert (Reconciliation ist eine
Projekt-/Monatssicht, keine Phasensicht).

## 16. Data Model Changes

**Keine** Schema-Änderung für P18.1–P18.4 (Kernpaket). Kein neues Feld, keine neue Tabelle,
keine Migration. Falls BD-8 (Planstand-Grobplanung) mit "ja, granular" beantwortet wird,
genügt eine zusätzliche `_SNAPSHOT_FIELDS["resource_demand"] = ["fte"]`-Ergänzung im
bestehenden generischen Mechanismus (`backend/app/routers/baselines.py`) — ebenfalls **ohne**
Migration, da `BaselineEntry.entity_type`/`field` bereits als String-Spalten beliebige neue
Werte aufnehmen.

## 17. Calculation Layer Changes

Neue Funktionen (additiv, keine bestehende Funktion wird verändert oder dupliziert):

- `phase_metrics_calc.monthly_distribution(plan_fte, forecast_start, forecast_end) ->
  dict[str, float]` — Monatsverteilung einer Phase (Abschnitt 8), nutzt
  `capacity_calc.count_weekdays_in_range`.
- `capacity_calc.compute_grob_hours(db, project_id, period) -> float` — Summe
  `ResourceDemand.fte` mit `plan_phase_id IS NULL` für Projekt/Periode, umgerechnet in
  Stunden über `count_weekdays_in_range`/`VOLLZEIT_WOCHENSTUNDEN`.
- `capacity_calc.compute_fein_hours(db, project_id, period) -> float` — Summe
  `monthly_distribution(...)`-Anteile aller `PlanPhase`s des Projekts für diese Periode.
- `capacity_calc.compute_reconciliation(db, project_id, periods: list[str]) ->
  list[ReconciliationEntry]` — kombiniert die beiden obigen zu `grob_hours`, `fein_hours`,
  `noch_grob_hours`, `konsumption_hours`, `konkretisierungsgrad_pct` je Periode (CONCEPT.md
  Abschnitt 6a.13 Response-Form).
- `capacity_calc.compute_person_capacity_for_range(db, person_id, range_start, range_end) ->
  PersonCapacityOut | None` — Abschnitt 11.

**Geänderte Funktionen (Bugfix, kein neues Verhalten, nur Filterkorrektur):**
`compute_capacity_gap`, `controlling.get_allocation_gaps`, `controlling.get_role_analysis`,
`health._cockpit_capacity` erhalten je einen `ResourceDemand.plan_phase_id.is_(None)`-Filter
für ihren bisherigen "Grob"-Anteil, plus Addition von `compute_fein_hours`/`max()` für den
Gesamtwert (abhängig vom Ausgang von BD-7/9).

## 18. API Changes

**Neu, additiv:** `GET /projects/{id}/capacity/reconciliation?periods=` (CONCEPT.md
Abschnitt 6a.13, Response-Beispiel dort). Kein Schreibpfad — reine Aggregation bestehender
Daten.

**Bestehend, Verhalten geändert (nur falls BD-9 "direkt umstellen" ergibt):**
`GET /controlling/capacity-heatmap`, `/controlling/allocation-gaps`, `/controlling/roles`,
`GET /gap-engine/capacity`, `GET /projects/{id}/cockpit` — Rückgabewerte ändern sich für
Projekte mit paralleler Grob-/Feinplanung (Abschnitt 14). Bei BD-9-Ausgang "additiv
zuerst" bleiben diese Endpoints in P18 unverändert, der Fix folgt in einem separaten,
späteren Paket nach Beobachtungsphase.

**Keine neue API-Landschaft** — alle Änderungen bleiben in `capacity.py`/`controlling.py`/
`gap_engine.py`/`health.py`, konsistent mit dem bestehenden Router-Schnitt.

## 19. Frontend Changes

- `ProjectPlanningTab.tsx`: neuer Kartenblock "Planungsstand Kapazität" zwischen
  `ResourceDemandGrid` und `BaselineList`, rendert `GET
  /projects/{id}/capacity/reconciliation` (CONCEPT.md Abschnitt 6a.14).
- `ResourceDemandGrid.tsx`: `listResourceDemands`-Aufruf/`demandFor()` auf
  `plan_phase_id === null` filtern (Bugfix, Abschnitt 2/14).
- `PlanPhaseCapacityTab.tsx`: unverändert.
- `types.ts`/`client.ts`: neuer Typ `CapacityReconciliationEntry`, neue Client-Funktion
  `getCapacityReconciliation(projectId, periods)`.
- Kein neues Formular, keine neue Route, keine neue Navigationsebene.

## 20. Edge Cases

Vollständige Tabelle: CONCEPT.md Abschnitt 6a.12. Deckt ab: keine Grobplanung, nur
Grobplanung, Fein > Grob, Fein < Grob, Phase über Monatsgrenze, Projektstart/-ende
mitten im Monat, vollständig fein geplantes Projekt (Grobplanung bleibt erhalten),
Person ohne Profil, Urlaub/Krankheit, Feiertag, interne Allokation, überbuchte Person.

## 21. Test Strategy

Rebuild-safe Testfälle mit konkreten Zahlen (Fortsetzung des Beispiels aus CONCEPT.md
Abschnitt 6a.6, Projekt "Red Bull WMS Rollout", Kalenderjahr 2026):

| # | Szenario | Eingabe | Erwartete Ausgabe |
|---|---|---|---|
| T1 | Monatsverteilung einer phasenübergreifenden Phase | Konfiguration 19.10.–13.11., plan_fte 0,80 | Okt: 64,0 h (10 Werktage), Nov: 64,0 h (10 Werktage), Summe 128,0 h = `plan_hours_total` |
| T2 | Monatsverteilung einer Ein-Monats-Phase | Pflichtenheft 01.10.–17.10., plan_fte 0,50 | Okt: 48,0 h, kein anderer Monat betroffen |
| T3 | Reconciliation, teilweise konkretisiert | Grob Okt 1,50 FTE (264,0 h); Fein Okt 112,0 h | `noch_grob = 152,0 h`, `konsumption = 264,0 h`, `konkretisierungsgrad ≈ 42,4 %` |
| T4 | Reconciliation, vollständig konkretisiert | Grob Dez 1,00 FTE (184,0 h); Fein Dez 184,0 h (angenommen) | `noch_grob = 0,0 h`, `konsumption = 184,0 h`, `konkretisierungsgrad = 100 %` |
| T5 | Edge Case Fein > Grob | Grob Nov 336,0 h; Fein Nov 400,0 h (angenommen) | `noch_grob = 0,0 h` (nicht negativ), `konsumption = 400,0 h`, Abweichung `+64,0 h` separat ausgewiesen |
| T6 | Edge Case keine Grobplanung | Grob Dez = 0 (keine Zeilen) | `konkretisierungsgrad = null` (nicht 0 %), `konsumption = Feinplanstunden` |
| T7 | Edge Case nur Grobplanung | Fein = 0 für alle Monate | `konkretisierungsgrad = 0 %` für jeden Monat mit Grob > 0, `konsumption = Grobplanstunden` |
| T8 | Portfolio-Fix Regressionstest | Projekt mit Grob-Demand UND Phasen-Demand derselben Rolle/Periode | `GET /controlling/allocation-gaps` zeigt Grob- und Fein-Anteil getrennt/korrekt `max()`-aggregiert, nicht mehr die heutige Summe |
| T9 | `ResourceDemandGrid`-Kollision (Regressionstest des Frontend-Fundes) | Grob-Demand UND Phasen-Demand, gleiche Rolle/Periode | Grob-Grid zeigt/editiert ausschließlich die Grob-Demand, Phasen-Demand bleibt unangetastet |
| T10 | Available Capacity über Phasenzeitraum | Person mit `WorkingTime` 40h, Phase 20.10.–20.11. | `compute_person_capacity_for_range` liefert werktage-gewichtete Kombination aus Okt- und Nov-Monatswerten, keine neue Holiday/Absence-Query |

Testebenen: Unit (neue Calc-Funktionen isoliert gegen die obigen Zahlen), Integration
(`TestClient` gegen die geänderten/neuen Endpoints, analog zum bestehenden Muster aus
P11/P17), `check_migrations.py` (nur relevant, falls BD-8 zu einer `_SNAPSHOT_FIELDS`-
Erweiterung führt — keine Schema-Änderung selbst). Kein Playwright-Lauf in diesem
Design-Durchgang (keine UI implementiert); vorgesehen für das jeweilige Umsetzungspaket.

## 22. CONCEPT.md Changes

Exakte Änderungen dieses Durchgangs:

- **Kopfzeile:** Version v0.18 → v0.19, Stand-Hinweis auf P18-Design-Status.
- **"Wie dieses Dokument zu lesen ist":** Ausnahme-Hinweis für Abschnitt 6a ergänzt;
  Cross-Reference-Fehler korrigiert ("Abschnitt 15" → "Abschnitt 14" für Open BDs, war ein
  vorbestehender Doku-Bug, beim Audit gefunden).
- **Abschnitt 3 (Kernprinzipien):** zwei neue Bullet Points (Grob-/Feinplanung als
  Konkretisierungsgrade, `plan_fte` bleibt Quelle für Feinplanstunden).
- **Abschnitt 6 (Kapazitätsplanung):** umstrukturiert in 6.1 (Zwei Achsen, ergänzt um
  Level-3-Personen-Fund), 6.2 (Available Capacity, ergänzt um Monats-Grenze), 6.3 (neu:
  bekannte Aggregationslücke), 6.4 (neu: Planstände und Kapazität).
- **Abschnitt 6a (komplett neu):** 15 Unterabschnitte, siehe Abschnitte 3–15 dieses
  Dokuments für die Zuordnung.
- **Abschnitt 13 (Source-of-Truth-Matrix):** zwei neue Zeilen (Grobplanung; Grob-/
  Feinplanstunden/Konsumption/Konkretisierungsgrad).
- **Abschnitt 14 (Open Business Decisions):** BD-7, BD-8, BD-9 ergänzt, plus expliziter
  "nicht als BD aufgenommen"-Absatz (Begründungstransparenz).
- **Abschnitt 15 (Deferred Features):** P18-Reconciliation als deferred (wartet auf
  BD-7/8/9) ergänzt.
- **Abschnitt 16 (Umsetzungsstand):** neuer Abschnitt 16.4 (P18, Design-Zusammenfassung).

Keine Kürzung, keine Entfernung bestehender Abschnitte — reine additive Erweiterung plus
zwei kleine Korrekturen (Cross-Reference-Nummerierung, Ergänzung der bisher undokumentierten
Monats-/Aggregations-Grenzen als Ist-Zustand).

## 23. New Business Decisions

| ID | Frage | Empfehlung | Warum trotzdem offen |
|---|---|---|---|
| BD-7 | Capacity-Consumption-Formel für Portfolio-/Cockpit-/GAP-Sichten: `max(Grobplanstunden, Feinplanstunden)` je Projekt/Monat? | Ja, `max()` (CONCEPT.md Abschnitt 6a.10) | Ändert heute sichtbare Portfolio-Zahlen (behebt die in Abschnitt 6.3 dokumentierte Doppelzählung) — Verhaltensänderung an produktiven Kennzahlen braucht Freigabe, auch wenn fachlich eindeutig |
| BD-8 | Soll `BaselineSnapshot` künftig Grobplanung einfrieren, und wenn ja: granular (je `ResourceDemand`-Zeile) oder aggregiert (Monatssumme)? | Aggregiert (Monatssumme) als einfacherer Einstieg, granular als Ausbaustufe | Reine Scope-/Prioritäts-Entscheidung, keine technische Blockade — Business muss den Aufwand-Nutzen einordnen |
| BD-9 | Rollout von BD-7: bestehende Portfolio-Endpoints direkt umstellen oder zunächst additiv (neuer Reconciliation-Endpoint) daneben anbieten? | Additiv zuerst (P18.1–P18.2), Umstellung bestehender Endpoints als eigenes, späteres Paket nach Beobachtungsphase | Risikoabwägung (sichtbarer Zahlensprung im Portfolio-Dashboard) ist eine Produktentscheidung, keine technische |

## 24. Implementation Packages

Reihenfolge = Abhängigkeitsreihenfolge (siehe Abschnitt 25 für den Graphen). Jedes Paket ist
unabhängig freigebbar/testbar.

### P18.1 — Calculation Layer: Monatsverteilung & Reconciliation-Aggregation

- **Ziel:** Neue, reine Berechnungsfunktionen ohne API-Exposition, vollständig testbar.
- **Scope:** `phase_metrics_calc.monthly_distribution`, `capacity_calc.compute_grob_hours`,
  `capacity_calc.compute_fein_hours`, `capacity_calc.compute_reconciliation`.
- **Out of Scope:** API-Endpoint, Frontend, Änderung bestehender Aggregations-Endpoints.
- **Files:** `backend/app/phase_metrics_calc.py`, `backend/app/capacity_calc.py`.
- **DB:** keine.
- **Backend:** vier neue Funktionen, s. o.
- **API:** keine.
- **Frontend:** keine.
- **Tests:** T1–T7 (Abschnitt 21) als Unit-Tests.
- **Dependencies:** keine (nutzt nur bestehende Primitiven).
- **Risks:** Rundungsverhalten bei sehr kurzen Phasen (<1 Werktag) — Divide-by-zero-Schutz
  wie bei `plan_hours` bereits vorhanden, muss für `monthly_distribution` repliziert werden.
- **Acceptance Criteria:** Alle T1–T7 grün, `check_migrations.py` unverändert clean
  (keine Schema-Berührung).
- **Definition of Done:** Code Review, Unit-Tests grün, keine Änderung an bestehenden Calc-
  Funktionen.

### P18.2 — API: Neuer Reconciliation-Endpoint (additiv)

- **Ziel:** `GET /projects/{id}/capacity/reconciliation` bereitstellen.
- **Scope:** Neuer Endpoint in `capacity.py`, neues Response-Schema.
- **Out of Scope:** Änderung bestehender Endpoints (das ist P18.3, abhängig von BD-9).
- **Files:** `backend/app/routers/capacity.py`, `backend/app/schemas.py`.
- **DB:** keine.
- **Backend:** Router-Funktion ruft `capacity_calc.compute_reconciliation`.
- **API:** neuer additiver Endpoint, keine Breaking Changes.
- **Frontend:** keine (folgt in P18.5).
- **Tests:** `TestClient`-Integrationstest gegen T3–T7.
- **Dependencies:** P18.1.
- **Risks:** gering — rein additiv.
- **Acceptance Criteria:** Endpoint liefert exakt die in CONCEPT.md Abschnitt 6a.13
  dokumentierte Response-Form für das Red-Bull-WMS-Beispiel.
- **Definition of Done:** OpenAPI-Schema aktualisiert, Integrationstest grün.

### P18.3 — Bugfix: Aggregationslücke in Portfolio-/Cockpit-Endpoints (BD-7/BD-9-abhängig)

- **Ziel:** `plan_phase_id`-Filter in bestehenden Aggregationen ergänzen, `max()`-Formel
  integrieren.
- **Scope:** `compute_capacity_gap`, `controlling.get_allocation_gaps`,
  `controlling.get_role_analysis`, `health._cockpit_capacity`.
- **Out of Scope:** UI-Änderungen (Frontend konsumiert nur die korrigierten Zahlen).
- **Files:** `backend/app/capacity_calc.py`, `backend/app/routers/controlling.py`,
  `backend/app/routers/health.py`.
- **DB:** keine.
- **Backend:** Filter + `max()`-Kombination, s. Abschnitt 17.
- **API:** Response-**Werte** ändern sich (nicht die Struktur) für betroffene Projekte.
- **Frontend:** keine Codeänderung nötig, nur andere Zahlen.
- **Tests:** T8 (Regressionstest), plus bestehende Controlling-/Cockpit-Tests erneut
  laufen lassen (Nichtregression für Projekte ohne parallele Grob-/Feinplanung — dort
  darf sich nichts ändern).
- **Dependencies:** P18.1. **Blockiert bis BD-7 UND BD-9 entschieden sind** ("additiv
  zuerst" gemäß BD-9-Empfehlung heißt: dieses Paket wird erst nach einer
  Beobachtungsphase von P18.1/P18.2 angegangen, nicht im selben Umsetzungsschritt).
- **Risks:** sichtbare Zahlenänderung im Portfolio-Dashboard am Tag der Umstellung —
  Kommunikationsbedarf an Nutzer:innen, kein technisches Risiko.
- **Acceptance Criteria:** T8 grün; für alle Projekte ohne parallele Grob-/Feinplanung
  bleiben die zurückgegebenen Werte exakt identisch zu vorher (Snapshot-Vergleich vor/nach).
- **Definition of Done:** Code Review inkl. expliziter Vorher/Nachher-Zahlenprobe für
  mindestens ein reales Projekt mit paralleler Planung.

### P18.4 — Bugfix: `ResourceDemandGrid`-Filterlücke

- **Ziel:** Grobplanungs-Grid zeigt/editiert ausschließlich `plan_phase_id = NULL`-Zeilen.
- **Scope:** `ResourceDemandGrid.tsx`.
- **Out of Scope:** neue UI-Elemente.
- **Files:** `frontend/src/views/project/components/ResourceDemandGrid.tsx`.
- **DB/Backend/API:** keine.
- **Frontend:** Filter in `listResourceDemands`-Auswertung/`demandFor()`.
- **Tests:** T9 (manueller/Playwright-Regressionstest).
- **Dependencies:** keine (unabhängig von P18.1–3, kann sofort umgesetzt werden — reiner
  Bugfix ohne Business-Decision-Abhängigkeit).
- **Risks:** minimal.
- **Acceptance Criteria:** T9 grün.
- **Definition of Done:** Playwright-Check gegen ein Projekt mit paralleler Planung.

### P18.5 — Frontend: "Planungsstand Kapazität"-Block

- **Ziel:** UX-Zielbild aus CONCEPT.md Abschnitt 6a.14 umsetzen.
- **Scope:** Neue Komponente, Einbindung in `ProjectPlanningTab.tsx`.
- **Out of Scope:** Änderungen an `PlanPhaseCapacityTab.tsx`.
- **Files:** neue Datei `frontend/src/views/project/components/CapacityReconciliationCard.tsx`,
  Änderung `ProjectPlanningTab.tsx`, `types.ts`, `client.ts`.
- **DB/Backend:** keine (konsumiert P18.2).
- **API:** keine Änderung, nur Client-seitiger Aufruf.
- **Frontend:** neue Karte, Label "Planung konkretisiert X %" (keine Ampel, kein
  "Fortschritt"-Wort, Abschnitt 6a.7).
- **Tests:** Playwright-Lauf: Karte zeigt korrekte Werte für das Red-Bull-WMS-Beispiel.
- **Dependencies:** P18.2.
- **Risks:** gering.
- **Acceptance Criteria:** UI zeigt exakt die in Abschnitt 6a.14 skizzierte Struktur.
- **Definition of Done:** `npm run build`/`npm run lint` clean, Playwright-Check grün.

### P18.6 — Available Capacity über Phasenzeitraum

- **Ziel:** `compute_person_capacity_for_range` (Abschnitt 11) + Integration in
  `GET /resource-demands/{id}/candidates` für Phasen-Demands.
- **Scope:** neue Calc-Funktion + Anpassung der Kandidaten-Query für phasengebundene
  Demands (Grob-Demands nutzen weiterhin die bestehende Monatsfunktion unverändert,
  Abschnitt 6a.8).
- **Out of Scope:** UI-Änderung außer der bereits vorhandenen Kandidatenliste, die nur
  präzisere Werte erhält.
- **Files:** `backend/app/capacity_calc.py`, `backend/app/routers/capacity.py`.
- **DB:** keine.
- **Tests:** T10.
- **Dependencies:** keine (unabhängig von P18.1–5, kann parallel laufen).
- **Risks:** Verhaltensänderung für phasengebundene Kandidatenlisten (heute: Monats-Only-
  Prüfung; künftig: Zeitraum-Prüfung) — kann bei sehr kurzen Phasen zu anderen
  Verfügbarkeits-Werten führen. Kein BD nötig (reine Präzisierung einer bereits als
  "Available Capacity" beworbenen, aber technisch unvollständigen Prüfung), aber im PR
  explizit benennen.
- **Acceptance Criteria:** T10 grün.
- **Definition of Done:** Code Review, Integrationstest gegen eine phasenübergreifende
  Phase.

### P18.7 — Optional: Planstand-Erweiterung um Grobplanung (nur falls BD-8 = "ja")

- **Ziel:** `_SNAPSHOT_FIELDS["resource_demand"] = ["fte"]` (oder aggregierte Variante,
  abhängig vom BD-8-Ausgang).
- **Scope:** `backend/app/routers/baselines.py`, `baseline_calc.py` (Deviation-Anzeige).
- **Out of Scope:** neue Baseline-UI jenseits der bestehenden `BaselineList.tsx`-Erweiterung
  um die neuen Felder.
- **Files:** `backend/app/routers/baselines.py`, `backend/app/baseline_calc.py`,
  `frontend/src/views/project/components/BaselineList.tsx`.
- **DB:** keine (generischer Mechanismus).
- **Dependencies:** BD-8-Entscheidung; unabhängig von P18.1–6.
- **Risks:** bei "granular" potenziell viele `BaselineEntry`-Zeilen je Snapshot (ein Snapshot
  pro Grob-Demand-Zeile) — Performance bei sehr vielen Rollen/Monaten prüfen, kein
  strukturelles Risiko.
- **Acceptance Criteria/DoD:** abhängig vom finalen BD-8-Scope, hier bewusst nicht
  vorweggenommen.

---

## 25. Dependency Graph

```
P18.1 (Calc: Monatsverteilung/Reconciliation)
  │
  ├──> P18.2 (API: neuer additiver Reconciliation-Endpoint)
  │      │
  │      └──> P18.5 (Frontend: Planungsstand-Kapazität-Block)
  │
  └──> P18.3 (Bugfix bestehende Aggregation) ── blockiert bis BD-7 + BD-9 entschieden

P18.4 (Bugfix ResourceDemandGrid-Filter) ── unabhängig, sofort umsetzbar

P18.6 (Available Capacity über Zeitraum) ── unabhängig, sofort umsetzbar

P18.7 (Planstand-Erweiterung) ── unabhängig, blockiert bis BD-8 entschieden
```

Kritischer Pfad für den sichtbaren Nutzen (UI-Block): P18.1 → P18.2 → P18.5. P18.3/P18.7
sind bewusst vom kritischen Pfad entkoppelt (BD-abhängig), P18.4/P18.6 sind reine Bugfixes
ohne Abhängigkeit zu einer BD und können sofort nach Freigabe dieses Designs starten.

## 26. Parallel Agent Plan

Bei paralleler Umsetzung (mehrere Agents/Entwickler:innen gleichzeitig):

- **Agent/Strang A:** P18.1 → P18.2 → P18.5 (Backend-Calc → API → Frontend, sequenziell,
  da jeweils voneinander abhängig — nicht weiter parallelisierbar innerhalb des Strangs).
- **Agent/Strang B:** P18.4 (Frontend-Bugfix `ResourceDemandGrid`) — komplett unabhängig,
  kann jederzeit parallel zu Strang A laufen.
- **Agent/Strang C:** P18.6 (Available Capacity über Zeitraum) — komplett unabhängig,
  reiner Backend-Calc-Strang, kann parallel zu A/B laufen.
- **Nicht parallelisierbar vor Freigabe:** P18.3 und P18.7 dürfen **nicht** gestartet
  werden, bevor BD-7/BD-9 bzw. BD-8 vorliegen — kein Agent sollte darauf angesetzt werden,
  solange diese offen sind.
- **Koordinationspunkt:** P18.2 und P18.4 berühren beide `ResourceDemand`-nahen Code, aber
  unterschiedliche Dateien (`capacity.py`-Router-Endpoint neu hinzufügen vs.
  `ResourceDemandGrid.tsx`-Filter) — kein Merge-Konflikt-Risiko, aber beide sollten gegen
  denselben Stand von P18.1 branchen, um Testdaten-Annahmen konsistent zu halten.

## 27. Rebuild Safety Assessment

Prüf-Frage: Könnte ein kompetentes Engineering-Team allein aus CONCEPT.md (ohne dieses
Dokument, ohne Repository, ohne Chatverlauf) rekonstruieren, was Grobplanung/Feinplanung
sind, wie sie zusammenhängen und welche Formeln gelten?

| Anforderung (Auftragsvorgabe Abschnitt 33) | Erfüllt in CONCEPT.md? |
|---|---|
| Was die App tut | Ja — Abschnitt 1/2 unverändert, ergänzt um Abschnitt 6a.1 |
| Wie Projektplanung funktioniert | Ja — Abschnitt 5 unverändert |
| Wie Kapazität geplant wird (inkl. Grob-/Fein) | Ja — Abschnitt 6/6a vollständig neu/korrigiert |
| Welche Modelle benötigt werden | Ja — Abschnitt 4 (unverändert, da P18 kein neues Modell einführt) + Abschnitt 6a.2 (explizit: kein neues Modell) |
| Welche Berechnungen gelten (mit Formeln/Beispielen) | Ja — Abschnitt 6a.4/6a.6 inkl. vollständig durchgerechnetem Zahlenbeispiel |
| Wie die UI funktionieren soll | Ja — Abschnitt 6a.14 (Entwurf, klar als "nicht implementiert" markiert) |
| Welche Integrationen existieren | unverändert (Abschnitt 7), P18 führt keine neue Integration ein |
| Welche Regeln/Edge Cases gelten | Ja — Abschnitt 6a.12 (12 Edge Cases tabellarisch) |
| Welche Entscheidungen noch offen sind | Ja — Abschnitt 14, BD-7/8/9 mit Begründung, warum sie offen sind statt entschieden |

**Bewertung: Rebuild-safe.** Ein neues Team könnte aus CONCEPT.md allein sowohl das
bestehende System (Abschnitt 1–14 inkl. korrigiertem Abschnitt 6) als auch das P18-Zielbild
(Abschnitt 6a) vollständig nachbauen, inklusive der offenen Fragen, die vor einer
Umsetzung zu klären sind. Einzige bewusste Lücke: die konkrete Rundungs-/
Implementierungspolitik (dieses Dokument, Abschnitt 8) ist als reines
Umsetzungsdetail hier statt in CONCEPT.md dokumentiert — das ist konsistent mit der
bestehenden Konvention, dass CONCEPT.md fachliche, nicht jede code-technische Entscheidung
trägt (z. B. steht auch die exakte Rundung von `open_fte` nur im Code-Kommentar, nicht in
CONCEPT.md). Sollte diese Grenze künftig strenger gezogen werden wollen, ist das ein
eigener, kleiner Doku-Nachtrag, kein Blocker für P18.

## 28. Final Recommendation

Die fachliche Analyse ist für alle drei neuen Business Decisions eindeutig (klare
Empfehlungen liegen vor, Abschnitt 23) und die technische Umsetzung ist vollständig
spezifiziert, minimal-invasiv und ohne neue Architektur (Abschnitte 16–19). Zwei Pakete
(P18.4, P18.6) sind bereits jetzt freigebbar, da sie reine Bugfixes ohne BD-Abhängigkeit
sind.

Die verbleibenden Kernpakete (P18.3, P18.7) verändern jedoch **heute sichtbare
Portfolio-/Cockpit-Zahlen** (Abschnitt 14) bzw. **Planstand-Umfang** — beides Entscheidungen,
die laut Auftragsvorgabe ausdrücklich einer Business Decision vorbehalten bleiben sollen,
nicht einer impliziten technischen Entscheidung während der Implementierung.

**BUSINESS DECISION REQUIRED**

Konkret benötigt, bevor P18.3/P18.7 gestartet werden dürfen: Freigabe zu BD-7 (Formel), BD-8
(Planstand-Scope) und BD-9 (Rollout-Reihenfolge). P18.1, P18.2, P18.4, P18.5, P18.6 können
unabhängig davon sofort freigegeben und begonnen werden, sobald dieses Design abgenommen ist.
