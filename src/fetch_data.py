"""
Einmaliger Abruf aller Rohdaten von API-Football für die 48 WM-2026-Teams,
in zwei Phasen:

  Phase 1 - Fixtures: Länderspiele pro Team (Saisons 2018-2026, ~2 WM-Zyklen).
  Phase 2 - Match-Stats: Ballbesitz/Schüsse/Ecken etc. pro Fixture (dedupliziert
            über eindeutige Fixture-IDs, da ein Spiel zwischen zwei WM-Teams
            sonst doppelt abgerufen würde).

Beide Phasen sind unabhängig voneinander resumable (bereits abgerufene
Dateien werden übersprungen) und stoppen sauber bei Tageslimit oder
Netzwerkfehlern, statt abzustürzen.

Kosten-Kalkulation Phase 1: 48 Teams x 9 Saisons = 432 Requests (~5.8% des
Tageslimits von 7500). Phase 2: ca. 1 Request pro eindeutigem Fixture
(mehrere Tausend total) - kann je nach Datenmenge mehr als einen Tag dauern.

Aufruf:
    python src/fetch_data.py
"""
import json
import sys
import time
from pathlib import Path

import requests

from config import BASE_URL, HEADERS, DATA_RAW_DIR, WM2026_TEAMS

TEAM_ID_CACHE_FILE = DATA_RAW_DIR / "team_ids.json"
STATS_DIR = DATA_RAW_DIR / "stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)

SEASONS_TO_FETCH = list(range(2018, 2027))  # 2018-2026 (9 Jahre, ~2 WM-Zyklen)
SLEEP_BETWEEN_CALLS = 0.5  # Sekunden; Pro-Plan erlaubt 300 Requests/Minute

session = requests.Session()
session.headers.update(HEADERS)


def _get(endpoint: str, params: dict, retries: int = 2, network_retries: int = 3) -> dict:
    """Führt einen GET-Request aus, mit Retry bei 429 UND bei Netzwerkfehlern
    (z.B. ConnectionResetError - passiert gelegentlich bei vielen Requests
    hintereinander und ist kein API-Problem, sondern ein kurzer Netzwerk-Hänger)."""
    url = f"{BASE_URL}/{endpoint}"

    try:
        resp = session.get(url, params=params, timeout=20)
    except requests.exceptions.RequestException as e:
        if network_retries > 0:
            print(f"   Netzwerkfehler ({type(e).__name__}) - warte 5 Sekunden und versuche erneut ...")
            time.sleep(5)
            return _get(endpoint, params, retries=retries, network_retries=network_retries - 1)
        else:
            print(f"   Netzwerkfehler wiederholt gescheitert: {e}")
            print("   Überspringe, Skript läuft weiter.")
            return {"response": None}

    if resp.status_code == 429:
        if retries > 0:
            print("   429 Too Many Requests - warte 15 Sekunden und versuche erneut ...")
            time.sleep(15)
            return _get(endpoint, params, retries=retries - 1, network_retries=network_retries)
        else:
            print("   429 Too Many Requests - erneut gescheitert. Skript stoppt hier sauber.")
            sys.exit(0)

    resp.raise_for_status()
    data = resp.json()

    remaining = resp.headers.get("x-ratelimit-requests-remaining")
    if remaining is not None and int(remaining) % 200 == 0:
        print(f"   -> verbleibende Requests heute: {remaining}")
        if int(remaining) <= 0:
            print("Tageslimit erreicht. Skript stoppt hier, morgen einfach erneut starten.")
            sys.exit(0)

    if data.get("errors"):
        print(f"   WARNUNG API-Fehler: {data['errors']}")

    return data


def _read_json_robust(path: Path):
    """Liest eine JSON-Datei ein, mit Fallback auf cp1252 falls UTF-8 fehlschlägt
    (ältere Dateien wurden vor einem Encoding-Fix mit Windows-Kodierung gespeichert)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="cp1252"))


# ---------------------------------------------------------------------------
# Phase 1: Fixtures pro Team
# ---------------------------------------------------------------------------

def load_team_id_cache() -> dict:
    if TEAM_ID_CACHE_FILE.exists():
        return json.loads(TEAM_ID_CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_team_id_cache(cache: dict) -> None:
    TEAM_ID_CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def get_team_id(search_names: list[str]) -> int | None:
    """Sucht die API-Football Team-ID für ein Nationalteam.

    Probiert zuerst den "name"-Parameter mit allen Namensvarianten durch,
    danach zusätzlich den "country"-Parameter (matcht manchmal zuverlässiger
    bei Ländern, deren Team-Name bei API-Football abweicht, z.B. Cabo Verde,
    Bosnia and Herzegovina).
    """
    for param_key in ("name", "country"):
        for name in search_names:
            data = _get("teams", {param_key: name})
            results = data.get("response", [])
            for entry in results:
                team = entry.get("team", {})
                if team.get("national") is True:
                    return team.get("id")
            if results:
                return results[0]["team"]["id"]
            time.sleep(SLEEP_BETWEEN_CALLS)
    return None


def fetch_fixtures_for_team(team_id: int) -> list:
    """Holt Länderspiele eines Teams über möglichst viele Saisons und führt
    sie dedupliziert und nach Datum sortiert zusammen."""
    fixtures_by_id = {}

    for season in SEASONS_TO_FETCH:
        data = _get("fixtures", {"team": team_id, "season": season})
        season_fixtures = data.get("response", [])
        for fx in season_fixtures:
            fx_id = fx.get("fixture", {}).get("id")
            if fx_id is not None:
                fixtures_by_id[fx_id] = fx
        if season_fixtures:
            print(f"   Saison {season}: {len(season_fixtures)} Spiele gefunden")
        time.sleep(SLEEP_BETWEEN_CALLS)

    all_fixtures = list(fixtures_by_id.values())
    all_fixtures.sort(key=lambda fx: fx.get("fixture", {}).get("date", ""), reverse=True)
    return all_fixtures


def fetch_all_fixtures():
    print("=" * 60)
    print("PHASE 1: FIXTURES PRO TEAM")
    print("=" * 60)

    team_id_cache = load_team_id_cache()

    for fifa_name, api_names in WM2026_TEAMS.items():
        fixtures_file = DATA_RAW_DIR / f"fixtures_{fifa_name.replace(' ', '_')}.json"

        if fixtures_file.exists():
            print(f"[skip] {fifa_name} bereits vorhanden.")
            continue

        print(f"[fetch] {fifa_name} ...")

        if fifa_name in team_id_cache:
            team_id = team_id_cache[fifa_name]
        else:
            team_id = get_team_id(api_names)
            time.sleep(SLEEP_BETWEEN_CALLS)
            if team_id is None:
                print(f"   FEHLER: Keine Team-ID gefunden für '{fifa_name}' (probiert: {api_names}). Übersprungen.")
                continue
            team_id_cache[fifa_name] = team_id
            save_team_id_cache(team_id_cache)

        fixtures = fetch_fixtures_for_team(team_id)
        fixtures_file.write_text(json.dumps(fixtures, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"   TOTAL {len(fixtures)} Spiele gespeichert -> {fixtures_file.name}")

    print("\nPhase 1 fertig (oder Tageslimit erreicht - dann einfach erneut starten).")


# ---------------------------------------------------------------------------
# Phase 2: Match-Stats pro Fixture
# ---------------------------------------------------------------------------

def collect_unique_fixture_ids() -> set[int]:
    """Sammelt alle eindeutigen Fixture-IDs über alle Teams-JSON-Dateien.

    Überspringt leere oder beschädigte Dateien mit einer Warnung, statt
    abzustürzen (z.B. falls ein früherer Lauf mittendrin unterbrochen wurde).
    """
    fixture_ids = set()
    for team_file in DATA_RAW_DIR.glob("fixtures_*.json"):
        if team_file.stat().st_size == 0:
            print(f"   WARNUNG: {team_file.name} ist leer (0 Bytes) - übersprungen.")
            continue
        try:
            fixtures = _read_json_robust(team_file)
        except json.JSONDecodeError:
            print(f"   WARNUNG: {team_file.name} enthält kein gültiges JSON - übersprungen.")
            continue
        for fx in fixtures:
            fx_id = fx.get("fixture", {}).get("id")
            if fx_id is not None:
                fixture_ids.add(fx_id)
    return fixture_ids


def fetch_stats_for_fixture(fixture_id: int):
    """Holt die Statistiken (Ballbesitz, Schüsse, Ecken etc.) für ein Spiel.

    Gibt None zurück, falls auch nach den Netzwerk-Retries kein Ergebnis kam
    (dann wird die Datei NICHT geschrieben, damit ein späterer Lauf es erneut
    versucht statt es fälschlicherweise als "erledigt" zu markieren)."""
    data = _get("fixtures/statistics", {"fixture": fixture_id})
    if data.get("response") is None:
        return None
    return data.get("response", [])


def fetch_all_match_stats():
    print("\n" + "=" * 60)
    print("PHASE 2: MATCH-STATS PRO FIXTURE")
    print("=" * 60)

    fixture_ids = collect_unique_fixture_ids()
    print(f"{len(fixture_ids)} eindeutige Fixtures gefunden (über alle 48 Teams).\n")

    already_done = 0
    newly_fetched = 0
    failed = 0

    for fixture_id in sorted(fixture_ids):
        stats_file = STATS_DIR / f"{fixture_id}.json"

        if stats_file.exists():
            already_done += 1
            continue

        stats = fetch_stats_for_fixture(fixture_id)

        if stats is None:
            failed += 1
            time.sleep(SLEEP_BETWEEN_CALLS)
            continue

        stats_file.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        newly_fetched += 1

        if newly_fetched % 50 == 0:
            print(f"   ... {newly_fetched} neu abgerufen, {already_done} übersprungen (schon vorhanden)")

        time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\nPhase 2 fertig (oder Tageslimit erreicht). Neu abgerufen: {newly_fetched}, übersprungen: {already_done}")
    if failed:
        print(f"Wegen Netzwerkfehlern übersprungen (werden beim nächsten Lauf erneut versucht): {failed}")


def refresh_current_season(season: int = 2026):
    """Aktualisiert NUR die aktuelle Saison für alle Teams - holt neu gespielte
    Spiele (z.B. laufende WM-2026-Partien) nach und fügt sie in die bestehenden
    Dateien ein (dedupliziert über Fixture-ID), OHNE die vorhandene Historie zu
    löschen. Im Gegensatz zu fetch_all_fixtures() wird hier nicht übersprungen,
    nur weil die Datei schon existiert - genau das ist ja der Zweck."""
    print("=" * 60)
    print(f"REFRESH: Saison {season} für alle Teams aktualisieren")
    print("=" * 60)

    team_id_cache = load_team_id_cache()

    for fifa_name in WM2026_TEAMS:
        if fifa_name not in team_id_cache:
            print(f"[skip] {fifa_name}: keine Team-ID im Cache - erst fetch_all_fixtures() laufen lassen.")
            continue

        team_id = team_id_cache[fifa_name]
        data = _get("fixtures", {"team": team_id, "season": season})
        new_fixtures = data.get("response", [])
        time.sleep(SLEEP_BETWEEN_CALLS)

        fixtures_file = DATA_RAW_DIR / f"fixtures_{fifa_name.replace(' ', '_')}.json"
        if fixtures_file.exists() and fixtures_file.stat().st_size > 0:
            try:
                existing = _read_json_robust(fixtures_file)
            except json.JSONDecodeError:
                existing = []
        else:
            existing = []

        by_id = {fx.get("fixture", {}).get("id"): fx for fx in existing}
        added = 0
        for fx in new_fixtures:
            fx_id = fx.get("fixture", {}).get("id")
            if fx_id is not None and fx_id not in by_id:
                by_id[fx_id] = fx
                added += 1

        merged = list(by_id.values())
        merged.sort(key=lambda fx: fx.get("fixture", {}).get("date", ""), reverse=True)
        fixtures_file.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

        marker = "NEU" if added else "keine Änderung"
        print(f"[{marker}] {fifa_name}: {added} neue Spiele hinzugefügt (total jetzt {len(merged)})")

    print("\nRefresh der Fixtures fertig. Jetzt noch Match-Stats für neue Spiele nachholen:")
    fetch_all_match_stats()


def main():
    fetch_all_fixtures()
    fetch_all_match_stats()
    print("\nAlles fertig (oder Tageslimit erreicht - Skript einfach erneut starten für den Rest).")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh_current_season()
    else:
        main()
