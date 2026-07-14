"""
Utility-Funktionen zum Laden und Filtern der abgerufenen Fixtures-Daten.

Wird sowohl vom Feature Engineering als auch später vom Streamlit-Dashboard
verwendet (dort z.B. als Toggle "WM-2026-Spiele einbeziehen?").
"""
import json
from pathlib import Path

from config import DATA_RAW_DIR

# Die WM 2026 läuft ab diesem Datum - per Default schliessen wir diese Spiele
# aus den Trainingsdaten aus, da sie das eigentliche Vorhersageziel sind und
# nicht als "historische Formkurve" ins Modell einfliessen sollen.
WM2026_START_DATE = "2026-06-19"


def load_team_fixtures(fifa_team_name: str) -> list:
    """Lädt die gespeicherten Rohdaten (alle abgerufenen Saisons) für ein Team."""
    fixtures_file = DATA_RAW_DIR / f"fixtures_{fifa_team_name.replace(' ', '_')}.json"
    if not fixtures_file.exists():
        return []
    try:
        return json.loads(fixtures_file.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        # Ältere Dateien (vor Encoding-Fix) wurden mit cp1252 statt UTF-8 gespeichert
        return json.loads(fixtures_file.read_text(encoding="cp1252"))


def filter_fixtures(fixtures: list, include_wm2026: bool = False, cutoff_date: str = WM2026_START_DATE) -> list:
    """Filtert eine Liste von Fixtures nach dem WM-2026-Cutoff-Datum.

    Args:
        fixtures: Liste von Fixture-Objekten (wie von der API zurückgegeben)
        include_wm2026: Falls False (Default), werden Spiele ab `cutoff_date`
            entfernt. Falls True, bleiben alle Spiele erhalten (z.B. für einen
            Dashboard-Toggle, der WM-2026-Resultate testweise einbeziehen will).
        cutoff_date: Datum im Format "YYYY-MM-DD", ab dem gefiltert wird.

    Returns:
        Gefilterte Liste von Fixtures.
    """
    if include_wm2026:
        return fixtures

    filtered = []
    for fx in fixtures:
        match_date = fx.get("fixture", {}).get("date", "")
        # match_date hat Format "2026-06-19T18:00:00+00:00" - String-Vergleich reicht hier
        if match_date and match_date[:10] < cutoff_date:
            filtered.append(fx)
    return filtered


def load_filtered_team_fixtures(fifa_team_name: str, include_wm2026: bool = False) -> list:
    """Komfort-Funktion: lädt und filtert in einem Schritt."""
    fixtures = load_team_fixtures(fifa_team_name)
    return filter_fixtures(fixtures, include_wm2026=include_wm2026)


if __name__ == "__main__":
    # Kleiner Selbsttest: zeigt für Canada, wie viele Spiele mit/ohne Filter übrig bleiben
    all_fixtures = load_team_fixtures("Canada")
    without_wm = filter_fixtures(all_fixtures, include_wm2026=False)
    with_wm = filter_fixtures(all_fixtures, include_wm2026=True)
    print(f"Canada: {len(all_fixtures)} Spiele total")
    print(f"  ohne WM-2026: {len(without_wm)} Spiele")
    print(f"  mit WM-2026:  {len(with_wm)} Spiele")
