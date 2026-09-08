# Tab „Entwicklung“ — Frontend-Vorschlag

**Status:** Entwurf zur Abstimmung, noch nicht implementiert  
**Sicht:** nur UI / Informationsarchitektur  
**Nicht Teil dieses Vorschlags:** Backend, Datenmodell, Jira-Sync, Euro-Budget, Entwicklungs-FTE-Planung

Ziel dieses Dokuments: einen konkreten Bildschirm vorschlagen, den Projektleiterinnen und Projektleiter öffnen, um zu sehen, **was die Entwicklung (bzw. alle Nicht-Berater) bereits auf das Projekt gebucht hat.** Der Text ist so geschrieben, dass er intern weitergegeben werden kann.

---

## 1. Wozu der Tab da ist

Heute sieht man Entwicklungsaufwand nur als kleine Grauzelle in der Phasen-Steuerung:

> Weitere Jira-Aufwände: X h außerhalb Kapazitätsscope

Das geht für eine einzelne Phase. Projektweit fehlt die Fläche.

**Leitfrage des Tabs:**

> Was wurde außerhalb des Beraterteams auf diesem Projekt gebucht — und welchen Phasen ist das zugeordnet?

**Was der Tab bewusst nicht ist:**

- kein zweiter Kapazitätsplaner für Developer
- kein „Projektfortschritt in Prozent“
- kein Vergleich gegen den Berater-`plan_fte` (das wäre ein falscher Nenner)
- kein Sync-/Integrationsbildschirm (das bleibt der Tab Jira)

Erstes Release: **reine Ist-Anzeige.** Sobald es später ein eigenes Entwicklungssoll gibt (Stundenhülle oder Jira-Schätzung), kann derselbe Tab um Plan vs. Ist ergänzt werden. Dafür muss die erste Version Platz lassen, aber keinen Fortschrittsbalken vortäuschen.

---

## 2. Einordnung in die Tab-Leiste

Heutige Reihenfolge:

Übersicht · Planung · Kommunikation · Dokumente · Historie · Jira · Einstellungen

**Vorschlag:**

```
Übersicht | Planung | Entwicklung | Kommunikation | Dokumente | Historie | Jira | Einstellungen
```

| Tab | Rolle |
|---|---|
| Übersicht | Lagebild (Health, Blocker, Aufgaben) |
| Planung | Absicht des Beraterteams (Phasen, Kapazität, Personen) |
| **Entwicklung** | **Ist-Buchungen außerhalb des Beraterteams** |
| Kommunikation | Diskussionen, Entscheidungen, Aufgaben |
| Dokumente | Ablage |
| Historie | Audit Trail |
| Jira | Anbindung, Sync, technische Zuordnung |
| Einstellungen | Stammdaten |

Route intern: `/projekte/:id/entwicklung`  
GUI-Name: **Entwicklung**  
Technische Identifier (`ProjectDevelopmentTab.tsx` o. ä.) müssen nicht den GUI-Namen spiegeln.

Klick auf eine Phase in diesem Tab öffnet die Planung mit bereits geöffnetem Phasen-Drawer (`?openPhase=` — das Pattern gibt es schon).

---

## 3. Bildschirmaufbau

Drei Karten untereinander, gleiche Sprache wie der Rest des Workspace (weiße Cards, Navy-Überschriften, Planner-Tabelle, kein neues Design-System).

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Zurück                                                       │
│  Projektname                                                     │
│  Kunde                                      [Als PPTX exportieren]│
│                                                                 │
│  Übersicht  Planung  Entwicklung  Kommunikation  Dokumente …    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Karte 1: Gebuchter Aufwand ──────────────────────────────┐  │
│  │  186 h gebucht                                             │  │
│  │  4 Autorinnen/Autoren · letzte Buchung 02.09.2026          │  │
│  │                                                            │  │
│  │  Das sind Jira-/Tempo-Buchungen von Personen, die nicht    │  │
│  │  zum kapazitätsplanbaren Beraterteam gehören.              │  │
│  │  Das ist kein Fertigstellungsgrad.                         │  │
│  │                                                            │  │
│  │  12 h noch keiner Phase zugeordnet  →  in Jira prüfen      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ Karte 2: Nach Phase ─────────────────────────────────────┐  │
│  │  Phase              Gebucht    Autoren   Letzte Buchung    │  │
│  │  Konfiguration      72 h       2         28.08.2026   →    │  │
│  │  Umsetzung          96 h       3         02.09.2026   →    │  │
│  │  Go-Live            6 h        1         15.08.2026   →    │  │
│  │  Nicht zugeordnet   12 h       1         01.09.2026        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ Karte 3: Nach Monat ─────────────────────────────────────┐  │
│  │            Jun 26   Jul 26   Aug 26   Sep 26               │  │
│  │  Gebucht   12 h     48 h     86 h     40 h                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Keine vierte Karte im ersten Schnitt. Keine Ampel. Kein Balken „X % fertig“.

---

## 4. Karte 1 — Gebuchter Aufwand (Kopf)

Große Zahl, kleine Meta-Zeile, ein ehrlicher Hinweis, optional ein Zuordnungs-Hinweis.

| Element | Inhalt | Warum |
|---|---|---|
| Primärwert | `186 h gebucht` | Die eine Zahl, die man sucht |
| Meta | `4 Autorinnen/Autoren · letzte Buchung TT.MM.JJJJ` | Einordnung ohne Drilldown |
| Hinweis (muted) | Buchungen außerhalb des Beraterteams. **Kein Fertigstellungsgrad.** | Verhindert die Lesart „Projekt ist zu X % fertig“ |
| Zuordnungszeile | nur wenn unmapped/ambiguous > 0: `12 h noch keiner Phase zugeordnet` + Link **Jira** | Coverage ist Vertrauenshinweis, keine Bewertung |
| Stand | `Stand: 08.09.2026 11:40 (vor 12 Minuten)` | Dieselbe Freshness-Zeile wie im Jira-Tab, read-only, **kein** Sync-Button |

**Nicht in dieser Karte:**

- Berater-Ist, Planstunden, `plan_fte`
- Zeit-verstrichen-Balken
- „Aufwand verbraucht“ in Prozent
- Health-Farbe

Platzhalter für später (nicht zeichnen, nur nicht verbauen): rechts neben der großen Zahl könnte später `von 250 h geplant` stehen, **sobald** es ein eigenes Entwicklungssoll gibt. Im ersten Schnitt diese Zeile weglassen, nicht grauen Dummy zeigen.

---

## 5. Karte 2 — Nach Phase

Das ist die Arbeitskarte. Eine Zeile je Leaf-Phase, die mindestens eine solche Buchung hat, plus eine Zeile **Nicht zugeordnet**.

Spalten:

| Spalte | Beispiel | Verhalten |
|---|---|---|
| Phase | Konfiguration | Name, bei Parent eingerückte Kinder (wie Planung-Liste, kompakt) |
| Gebucht | 72 h | Stunden, 0–1 Nachkommastelle |
| Autoren | 2 | Anzahl, nicht Namen in der Tabelle |
| Letzte Buchung | 28.08.2026 | Datum der letzten Worklog-Zeile |
| Aktion | → | öffnet Planung, Drawer dieser Phase |

Zeilen ohne Buchung **nicht** listen (sonst eine leere Kopie des Phasenbaums). Phasen ohne Jira-Label erscheinen nicht — außer in „Nicht zugeordnet“.

Klick auf die Zeile (nicht nur auf →) reicht. Hover wie ein Link, kein neuer Button-Stil.

**Aufklappen einer Zeile (optional, zweiter Schliff):**  
Autoren mit Stunden darunter, z. B. `j.schmidt@…  40 h` / `Unbekannter Jira-Account  32 h`. Nicht im ersten sichtbaren Zustand, sonst wird die Karte zum Personen-Dump. Pattern wie „Details ▾“ im Kapazität-Tab.

Parent-Phasen: Summe der Kinder, nicht zusätzlich zählen. Gleiche Semantik wie überall sonst.

---

## 6. Karte 3 — Nach Monat

Dieselbe Planner-Tabelle wie der Jira-Tab, aber **nur** die Entwicklungs-/Outside-Scope-Stunden, in **Stunden**, nicht in FTE.

FTE würde hier eine Wochenstunden-Annahme für unbekannte Developer erzwingen (heute 40 h Default für unzugeordnete Accounts). Stunden sind die ehrliche Einheit.

Nur Monate mit Wert > 0, oder durchgehend die Projektmonate mit `0` / `—`. **Vorschlag:** Projektmonate durchgehend, leere Zellen als `—`, damit Lücken sichtbar sind.

Kein Hochrechnungsbalken, kein Soll-Strich, kein Forecast. Das wäre wieder Fortschritt ohne Plan.

---

## 7. Zustände (wichtig für den ersten Eindruck)

| Zustand | Was der Tab zeigt |
|---|---|
| Jira nicht verbunden / keine Komponente | Kurze Karte: „Entwicklung-Ist kommt aus Jira-Worklogs. Verknüpfung unter Einstellungen.“ Link dorthin. Keine leere Tabelle. |
| Verbunden, aber noch keine Worklogs | „Noch keine Buchungen außerhalb des Beraterteams.“ |
| Nur Beraterteam hat gebucht | Dieselbe Leerzeile. Nicht `0 h` als Erfolg verkaufen. |
| Buchungen vorhanden, Mapping unvollständig | Kopfzahl trotzdem zeigen (Ist ist Ist). Zusätzlich die Zuordnungszeile, nicht die ganze Seite grau. |
| Alles zugeordnet | Keine Coverage-Zeile. Stille Vollständigkeit. |
| Sync-Fehler | Freshness-Zeile rot wie im Jira-Tab: bisherige Werte bleiben stehen. Kein zweiter Sync-Button. |

Der Tab darf nie eine `0 %`-Fortschrittsanzeige zeigen, wenn kein Soll existiert.

---

## 8. Was wir weglassen (erster Schnitt)

Damit der Vorschlag nicht zur Mini-Jira-Oberfläche wird:

- kein Sync-Button (bleibt Jira)
- keine Label-Konfiguration (bleibt Phasen-Übersicht → „Ist-Zuordnung konfigurieren“)
- keine Ticketliste (Issue-Keys, Status, Estimates sind heute nicht die Heimat dieses Tools)
- keine Personen einplanen, keine Rollen, keine Available Capacity
- keine Euro, keine Tagessätze
- kein Vergleich mit Berater-Planstunden
- keine Ampel (BD-3 bleibt offen, und hier gäbe es sowieso keinen Schwellwert)
- keine Änderung an Übersicht/Kommunikation/Dokumente in diesem Schritt

Einziger Querverweis: eine Zeile auf der **Übersicht** ist später sinnvoll, analog zur Kapazitätskachel:

> Entwicklung: 186 h gebucht → Tab Entwicklung

Das ist kein Bestandteil des ersten Tab-Schnitts, nur erwähnt damit Übersicht und Tab sich nicht widersprechen.

---

## 9. Sprache in der UI

| Nicht schreiben | Stattdessen |
|---|---|
| Fortschritt, Fertigstellungsgrad, Budget verbraucht | gebucht, Gebuchter Aufwand |
| Developer-FTE, Kapazität Entwicklung | Stunden |
| außerhalb Kapazitätsscope | im Hinweistext einmal erklären; in der Überschrift **Entwicklung** |
| forecast, outside_scope, plan_fte, jira_label | nie in der normalen UI |
| Ist-FTE | Stunden (Karte 3) |

Wenn die Kollegen festlegen, dass wirklich **nur Entwicklung** gemeint ist und nicht „alle Nicht-Berater“, muss der Hinweistext das sagen. Bis dahin ehrlich bleiben:

> Buchungen von Personen, die nicht zum kapazitätsplanbaren Beraterteam gehören (z. B. Entwicklung, Externe).

---

## 10. Dummy-Daten für den ersten Frontend-Stand

Solange das Backend fehlt, kann der Tab mit **festen Beispieldaten** gebaut und angeschaut werden. Kein Live-Server nötig für die Layout-Abstimmung.

Beispiel (fiktiv, ein Projekt „plx.crew Portal“):

```
Kopf:     186 h · 4 Autoren · letzte Buchung 02.09.2026
Unmapped: 12 h

Phasen:
  Konfiguration   72 h   2   28.08.2026
  Umsetzung       96 h   3   02.09.2026
  Go-Live          6 h   1   15.08.2026
  Nicht zugeordnet 12 h  1   01.09.2026

Monate:
  Jun 26  12 h
  Jul 26  48 h
  Aug 26  86 h
  Sep 26  40 h
```

Zusätzlich die Leerzustände aus Abschnitt 7 per lokalem Schalter oder Story-Variante klickbar machen, damit man nicht nur den Happy Path sieht.

---

## 11. Fragen an die Kollegen

Bitte vor dem Bau entscheiden. Sonst entsteht genau der Fortschrittsbalken, den wir nicht wollen.

1. **Wer zählt als „Entwicklung“?**  
   Alle Nicht-Berater-Buchungen (heute schon als Outside-Scope da) — oder nur bestimmte Autoren/Teams?

2. **Soll es später ein Entwicklungssoll geben?**  
   Z. B. „geplante Entwicklungsstunden“ je Phase, gepflegt im Planer. Dann erst Plan vs. Ist. Im ersten Tab **nicht** andeuten.

3. **Sollen Autorennamen in der Haupttabelle stehen** oder nur nach „Details ▾“?

4. **Ist die Tab-Bezeichnung „Entwicklung“ ok**, auch wenn technisch zunächst „Nicht-Beraterteam“ gemeint ist?

5. **Braucht die Übersicht schon im ersten Schnitt die eine Verweiszeile**, oder reicht der neue Tab allein?

---

## 12. Was danach kommt (nicht jetzt)

- Backend nur als lesende Aggregation vorhandener Worklogs, keine neue Planungstabelle
- Optional: Autor-Drilldown
- Optional: Übersicht-Kachel
- Erst nach Entscheidung zu Frage 2: Soll-Zahl und echter Vergleich Plan vs. Ist

Keine dieser Punkte sind Voraussetzung, um den Bildschirm in Abschnitt 3 zu bauen.
