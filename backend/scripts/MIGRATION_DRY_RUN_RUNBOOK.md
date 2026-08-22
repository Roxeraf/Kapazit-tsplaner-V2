# Migration Realistic Dry-Run Runbook (P18.1 Stabilization)

Siehe CONCEPT.md Abschnitt 16.16 / Abschnitt 6b.12. Dieses Runbook beschreibt den sicheren
Ablauf für einen realitätsnahen Dry-Run von `migrate_to_planphase_hierarchy.py` gegen eine
**Kopie** der Produktivdaten — **kein Schritt hiervon schreibt in die echte Produktion.**

Bisheriger Stand (Abschnitt 16.15): der Dry-Run lief ausschließlich gegen eine synthetische
SQLite-Testfixture (`test_migrate_to_planphase_hierarchy.py`). Diese deckt die Migrationslogik
strukturell ab, aber nicht die Datenrealität (Volumen, echte Rollenverteilung, echte
Sonderfälle in Alt-Daten).

**In dieser aktuellen Arbeitsumgebung existiert keine Kopie/kein Zugriff auf die
Produktivdatenbank** (kein Docker-Daemon, keine Postgres-Instanz, keine Zugangsdaten). Schritte
1–2 unten sind daher ein **externer, außerhalb dieser Umgebung auszuführender Schritt** — hier
wird bewusst nichts simuliert oder erfunden (Auftrag Abschnitt 6: "Wenn im aktuellen Umfeld
keine Produktivdatenkopie verfügbar ist: keine Daten erfinden").

## Ablauf

### Schritt 1 — Produktivdaten-Snapshot beziehen (EXTERN, außerhalb dieser Umgebung)

Auf dem Produktivserver (bzw. durch die Person mit Postgres-Zugriff):

```bash
pg_dump --format=custom --file=kapazitaetsplaner_prod_$(date +%Y%m%d).dump \
  "$DATABASE_URL"   # die echte Produktions-Connection-String, NICHT hier ausführen
```

Der Dump muss auf ein Medium außerhalb der Produktionsinfrastruktur übertragen werden (z.B.
verschlüsselter Transfer auf eine isolierte Migrations-/Staging-Maschine). Dieser Schritt
erfordert Zugriff, den diese Arbeitsumgebung nicht hat — er ist der explizit dokumentierte
externe Vorbedingung für alles Weitere.

### Schritt 2 — Lokal/isoliert restaurieren (EXTERN/Staging, nicht produktiv)

Auf einer isolierten Staging-Maschine (niemals auf dem Produktivserver selbst):

```bash
createdb kapazitaetsplaner_migration_staging
pg_restore --dbname=kapazitaetsplaner_migration_staging kapazitaetsplaner_prod_YYYYMMDD.dump
```

Alternativ (kleinere Installationen): Export nach SQLite über ein separates ETL-Skript, sofern
das Datenvolumen das zulässt — nicht Teil dieses Runbooks, da produktiv Postgres ist
(`docker-compose.yml`).

**Bis hierhin ist nichts davon in dieser Arbeitsumgebung ausführbar oder verifizierbar.**

### Schritt 3 — Migration `--dry-run` gegen die Staging-Kopie

Ab hier ist der Ablauf identisch zu dem, was `migrate_to_planphase_hierarchy.py` bereits heute
unterstützt und was in diesem Repo automatisiert getestet ist:

```bash
cd backend
python scripts/migrate_to_planphase_hierarchy.py \
  --database-url "postgresql+psycopg2://<user>:<pass>@<staging-host>:5432/kapazitaetsplaner_migration_staging" \
  --report-file /pfad/zu/dry_run_report_$(date +%Y%m%d).json
```

Kein `--apply` — reiner Dry-Run (Sicherheitsdefault des Skripts, siehe Skript-Docstring).
Committet nichts, macht am Ende explizit `db.rollback()`.

### Schritt 4 — Report speichern

`--report-file` (P18.1 Stabilization, in diesem Durchgang ergänzt) schreibt den vollständigen
Report zusätzlich als JSON. Aufbewahren als Vergleichsbasis für Schritt 6–10 und als Nachweis
für das Freigabe-Gate.

### Schritt 5 — Apply auf der Kopie (NICHT auf Produktion!)

Erst NACH Prüfung des Dry-Run-Reports (Exit-Code 0, `"has_discrepancies": false`):

```bash
python scripts/migrate_to_planphase_hierarchy.py \
  --database-url "postgresql+psycopg2://<user>:<pass>@<staging-host>:5432/kapazitaetsplaner_migration_staging" \
  --apply \
  --report-file /pfad/zu/apply_report_$(date +%Y%m%d).json
```

**Ausdrücklich nur gegen die Staging-Kopie**, niemals gegen den Produktiv-Connection-String.

### Schritt 6 — Post-Migration Integrity Checks

Automatisiert im Report bereits enthalten (kein manueller SQL-Vergleich nötig):

- `hierarchy_depth_violations` (Tiefe > 3 UND Zyklen, `_compute_hierarchy_depth_violations`)
- je Projekt: `orphan_resource_demands_after == 0`
- je Projekt: `fte_sum_before == fte_sum_after` (Grobplanung-FTE-Summe)
- je Projekt: `milestones_before == milestones_after`
- je Projekt (P18.1 Stabilization, neu ergänzt): `assignments_count_before ==
  assignments_count_after` und `assignments_fte_sum_before == assignments_fte_sum_after`

`report.has_discrepancies == false` (Exit-Code 0) fasst alle diese Checks zusammen.

### Schritt 7 — Capacity Parity

Zusätzlich zum reinen FTE-Summen-Check (Schritt 6): `compute_project_monthly_capacity` (siehe
`app/capacity_calc.py`) VOR und NACH dem Apply auf denselben Perioden aufrufen und vergleichen
— die migrierten Monats-Leaf-Phasen müssen exakt dieselbe monatliche Stunden-Verteilung liefern
wie vorher `compute_project_monthly_capacity` (das seit B-5 bereits ausschließlich aus
PlanPhase.plan_fte liest, vor der Migration also 0 für migrierte Grobplanungs-Projekte lieferte
— das "Vorher" für den Capacity-Parity-Vergleich ist daher die alte, ResourceDemand-basierte
Soll-Rechnung, nicht `compute_project_monthly_capacity` selbst). Ein kleines Vergleichsskript
dafür ist nicht Teil dieses Durchgangs (kein Zugriff auf reale Daten, um es zu verifizieren) —
sollte vor dem eigentlichen B-8-Cutover ergänzt werden, sobald Schritt 1/2 real durchgeführt
wurden.

### Schritt 8 — Tree Validation

`hierarchy_depth_violations` (Schritt 6) deckt Tiefe/Zyklen ab. Zusätzlich stichprobenartig
(Schritt 9 unten) den Baum eines migrierten Subproject-Projekts im Frontend (PlanPhase-Liste/
Gantt) visuell prüfen.

### Schritt 9 — Assignment Validation

Siehe Schritt 6 (`assignments_count_before/after`, `assignments_fte_sum_before/after`, in
diesem Durchgang ergänzt). Zusätzlich stichprobenartig: ein Assignment vor/nach der Migration
im Frontend (PlanPhaseWorkspace → Kapazität-Tab) öffnen und die zugeordnete Person/FTE
vergleichen.

### Schritt 10 — Milestone Validation

Siehe Schritt 6 (`milestones_before/after`). Zusätzlich stichprobenartig: ein Milestone, das
vor der Migration an einem Subproject hing, nach der Migration im Frontend öffnen und
verifizieren, dass es weiterhin an der (jetzt migrierten) PlanPhase hängt und im Gantt an der
richtigen Position erscheint.

## Stichproben (Auftrag Abschnitt 7)

Nach Schritt 5 mindestens folgende Projekttypen manuell im Frontend gegen die Staging-Kopie
öffnen und auf Vollständigkeit/Erreichbarkeit prüfen:

- [ ] Projekt mit Subprojects
- [ ] Projekt mit Grob-Demands (Alt-Grobplanung, `plan_phase_id IS NULL` vor der Migration)
- [ ] Projekt mit Assignments
- [ ] Projekt mit Milestones
- [ ] Projekt mit mehreren Monaten Grobplanung
- [ ] Projekt OHNE Grob-Demands (reines PlanPhase-Projekt, sollte von der Migration unberührt
      bleiben — kein Report-Eintrag für dieses Projekt)

## Status dieses Durchgangs

**Schritt 1/2 sind ein externer, in dieser Arbeitsumgebung nicht ausführbarer Vorbedingungs-
Schritt** (kein Docker-/Postgres-Zugriff, keine Produktions-Zugangsdaten). Schritte 3–10 sind
werkzeugseitig vorbereitet (Migrationsskript inkl. `--report-file` und
Assignment-Vorher/Nachher-Check, in diesem Durchgang ergänzt) und automatisiert gegen die
synthetische Fixture verifiziert (`test_migrate_to_planphase_hierarchy.py`, weiterhin grün),
aber **noch nicht gegen eine echte Produktivkopie ausgeführt worden**. Das bleibt der offene,
extern zu beschaffende Schritt vor dem eigentlichen B-8-Cutover.
