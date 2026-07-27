"""
Einmal-Import bestehender Excel-Planungsdaten (.xlsm) in den Kapazitätsplaner.
Siehe CONCEPT.md, Abschnitt 8.

Liest jedes Projektblatt (alles außer Konfiguration/Legende/Gesamtuebersicht)
nach der Struktur, die das VBA-Tool erzeugt (legacy/VBA.txt, Funktion
`Exportiere_Als_JSON_Und_PPTX`):

  Zeile 1, Spalte A         Projektname
  Zeile 2, Spalte B..       Monatsspalten
  Teilprojekt 1: Header Zeile 4, Phasenzeilen 5-9  (p,k,t,g,?)
  Teilprojekt 2: Header Zeile 10, Phasenzeilen 11-15
  Teilprojekt 3: Header Zeile 16, Phasenzeilen 17-21
  FTE (Soll):    Zeile 24 (TP1), 25 (TP2), 26 (TP3) — Zeile 27 (Summe) wird ignoriert,
                 die Summe berechnet der neue Web-App aus TP1-3 on the fly.

Das Konfigurationsblatt liefert Startmonat/Anzahl Monate (Row 17/18, Spalte C).

Nutzung:
    python migration/import_excel.py <pfad-zur-datei.xlsm> [--api http://localhost:8000]

Voraussetzung: `pip install openpyxl requests` (nicht Teil von backend/requirements.txt,
da nur für den einmaligen Migrationslauf benötigt).
"""

import argparse
import sys

import requests
from openpyxl import load_workbook

PHASE_ROW_CODES = ["p", "k", "t", "g", "?"]
TP_START_ROWS = [5, 11, 17]  # erste Phasenzeile je Teilprojekt
TP_FTE_ROWS = [24, 25, 26]
MONAT_HEADER_ROW = 2
FIRST_MONAT_COL = 2  # Spalte B

SKIP_SHEETS = {"Konfiguration", "Legende", "Gesamtuebersicht"}


def read_config(wb) -> tuple[str, int]:
    ws = wb["Konfiguration"]
    start_monat = str(ws.cell(row=17, column=3).value).strip()
    anzahl_monate = int(ws.cell(row=18, column=3).value)
    return start_monat, anzahl_monate


def read_project_sheet(ws, anzahl_monate: int) -> dict:
    name = str(ws.cell(row=1, column=1).value or ws.title).strip()

    monate = [
        ws.cell(row=MONAT_HEADER_ROW, column=FIRST_MONAT_COL + i).value
        for i in range(anzahl_monate)
    ]

    subprojects = []
    for tp_idx, start_row in enumerate(TP_START_ROWS):
        header_row = start_row - 1
        tp_name = str(ws.cell(row=header_row, column=1).value or f"Teilprojekt {tp_idx + 1}").strip()

        phasen: dict[str, list[str]] = {}
        for ph_idx, code in enumerate(PHASE_ROW_CODES):
            row = start_row + ph_idx
            for i, monat in enumerate(monate):
                if not monat:
                    continue
                cell_val = ws.cell(row=row, column=FIRST_MONAT_COL + i).value
                if cell_val and str(cell_val).strip() == code:
                    phasen.setdefault(monat, []).append(code)

        fte: dict[str, float] = {}
        fte_row = TP_FTE_ROWS[tp_idx]
        for i, monat in enumerate(monate):
            if not monat:
                continue
            val = ws.cell(row=fte_row, column=FIRST_MONAT_COL + i).value
            if val:
                fte[monat] = float(val)

        # Leere Teilprojekte (keine Phasen, kein FTE, kein Name) überspringen.
        if tp_name.startswith("Teilprojekt ") and not phasen and not fte:
            continue

        subprojects.append({"name": tp_name, "reihenfolge": tp_idx, "phasen": phasen, "fte": fte})

    return {"name": name, "subprojects": subprojects}


def push_to_api(api_base: str, start_monat: str, anzahl_monate: int, project: dict) -> None:
    resp = requests.post(
        f"{api_base}/projects",
        json={
            "name": project["name"],
            "start_monat": start_monat,
            "anzahl_monate": anzahl_monate,
        },
        timeout=30,
    )
    resp.raise_for_status()
    project_id = resp.json()["id"]

    for sp in project["subprojects"]:
        resp = requests.post(
            f"{api_base}/projects/{project_id}/subprojects",
            json={"name": sp["name"], "reihenfolge": sp["reihenfolge"]},
            timeout=30,
        )
        resp.raise_for_status()
        subproject_id = resp.json()["id"]

        for monat, codes in sp["phasen"].items():
            requests.put(
                f"{api_base}/projects/subprojects/{subproject_id}/phasen",
                json={"monat": monat, "codes": codes},
                timeout=30,
            ).raise_for_status()

        for monat, wert in sp["fte"].items():
            requests.put(
                f"{api_base}/projects/subprojects/{subproject_id}/fte",
                json={"monat": monat, "wert_soll": wert},
                timeout=30,
            ).raise_for_status()

    print(f"  -> importiert als Projekt #{project_id}: {project['name']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsm_path", help="Pfad zur bestehenden .xlsm-Datei")
    parser.add_argument("--api", default="http://localhost:8000", help="Basis-URL der Backend-API")
    parser.add_argument("--dry-run", action="store_true", help="Nur einlesen und ausgeben, nicht in die API schreiben")
    args = parser.parse_args()

    wb = load_workbook(args.xlsm_path, data_only=True)
    start_monat, anzahl_monate = read_config(wb)
    print(f"Startmonat: {start_monat}, Anzahl Monate: {anzahl_monate}")

    project_sheets = [ws for ws in wb.worksheets if ws.title not in SKIP_SHEETS]
    print(f"Gefundene Projektblätter: {len(project_sheets)}")

    for ws in project_sheets:
        project = read_project_sheet(ws, anzahl_monate)
        if args.dry_run:
            print(project)
        else:
            push_to_api(args.api, start_monat, anzahl_monate, project)

    if args.dry_run:
        print("Dry-run — es wurde nichts in die API geschrieben.")


if __name__ == "__main__":
    sys.exit(main())
