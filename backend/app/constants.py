"""Phasencodes und FTE-Heatmap-Schwellen 1:1 aus dem Excel-Tool (siehe CONCEPT.md, Abschnitt 3)."""

import datetime

# Referenz-Wochenstunden für "1.0 FTE" - TeamMember.wochenstunden/ResourceProfile.weekly_hours/
# WorkingTime.weekly_hours default ist 40. Kapazität einer Person wird durchgängig als
# wochenstunden / VOLLZEIT_WOCHENSTUNDEN ausgedrückt (siehe routers/team.py, routers/
# real_capacity.py).
VOLLZEIT_WOCHENSTUNDEN = 40

PHASE_LABELS = {
    "p": "Pflichtenheft",
    "k": "Konfiguration",
    "t": "Test",
    "s": "Schulung",
    "g": "GoLive",
    "?": "Meilenstein",
}

PHASE_CODES = list(PHASE_LABELS.keys())

# Für die Ist-FTE-Umrechnung (Jira-Integration, siehe CONCEPT.md Abschnitt 4):
# Stunden -> FTE über einen pauschalen Wert für Arbeitswochen pro Monat (52 / 12).
ARBEITSWOCHEN_PRO_MONAT = 52 / 12

MONAT_NAMEN = [
    "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def fte_heatmap_bucket(wert: float | None) -> str:
    if not wert or wert <= 0:
        return "zero"
    if wert > 2:
        return "high"
    if wert >= 1.5:
        return "mid2"
    if wert >= 1:
        return "mid1"
    return "low"


def berechne_monate(start_monat: str, anzahl_monate: int) -> list[str]:
    """start_monat im Format 'MM.YYYY' (wie im Excel-Konfigurationsblatt)."""
    monat_str, jahr_str = start_monat.split(".")
    monat_idx = int(monat_str) - 1
    jahr = int(jahr_str)

    monate = []
    for i in range(anzahl_monate):
        m = (monat_idx + i) % 12
        j = jahr + (monat_idx + i) // 12
        monate.append(f"{MONAT_NAMEN[m]} {j % 100:02d}")
    return monate


def parse_period(period: str) -> tuple[int, int]:
    """Kehrt berechne_monate() um: 'Apr 26' -> (2026, 4) (Jahr, Monat). Für die
    Available-Capacity-Berechnung (Phase 20) benötigt, um Kalendergrenzen eines
    Perioden-Buckets (ResourceDemand.period/InternalAllocation.period) zu bestimmen.
    Nimmt wie berechne_monate() ein Jahrhundert von 2000 an."""
    name, jahr_str = period.split()
    monat = MONAT_NAMEN.index(name) + 1
    jahr = 2000 + int(jahr_str)
    return jahr, monat


def current_period() -> str:
    """Heutiges Perioden-Bucket im 'Apr 26'-Format (siehe berechne_monate). Für die
    Capacity Health (Phase 22) benötigt, um den aktuellen ResourceDemand-Zeitraum eines
    Projekts zu bestimmen."""
    today = datetime.date.today()
    return f"{MONAT_NAMEN[today.month - 1]} {today.year % 100:02d}"
