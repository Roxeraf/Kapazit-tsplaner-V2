"""Phasencodes und FTE-Heatmap-Schwellen 1:1 aus dem Excel-Tool (siehe CONCEPT.md, Abschnitt 3)."""

PHASE_LABELS = {
    "p": "Pflichtenheft",
    "k": "Konfiguration",
    "t": "Test",
    "g": "GoLive",
    "?": "Meilenstein",
}

PHASE_CODES = list(PHASE_LABELS.keys())

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
