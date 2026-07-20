"""
Einmaliger Abruf historischer Länderspieldaten für alle 48 WM-2026-Teams.

Mit dem Pro-Plan (7'500 Requests/Tag, 300 Requests/Minute) rufen wir die
Saisons 2018-2026 ab (2 WM-Zyklen: 2018-2022 und 2022-2026) - ein bewusster
Kompromiss aus genug Stichprobengrösse (auch für kleinere Fussballnationen)
und Aktualität der Teamstärke, statt naiv "so viele Jahre wie möglich".

Kosten-Kalkulation: 48 Teams x 9 Saisons = 432 Requests (~5.8% des
Tageslimits von 7500) - passt locker in einen einzigen Durchgang.

Aufruf:
    python src/fetch_data.py
"""
import json
import time
import sys
from pathlib import Path

import requests

from config import BASE_URL, HEADERS, DATA_RAW_DIR, WM2026_TEAMS

TEAM_ID_CACHE_FILE = DATA_RAW_DIR / "team_ids.json"
SEASONS_TO_FETCH = list(range(2018, 2027))  # 2018-2026 (9 Jahre, ~2 WM-Zyklen) - guter Kompromiss aus Stichprobengrösse und Aktualität
SLEEP_BETWEEN_CALLS = 0.5  # Sekunden; Pro-Plan erlaubt 300 Requests/Minute

session = requests.Session()
session.headers.update(HEADERS)


def _get(endpoint: str, params: dict, retries: int = 2) -> dict:
    """Führt einen GET-Request aus und gibt das geparste JSON zurück.

    Bei 429 (Rate Limit) wartet die Funktion kurz und versucht es erneut,
    statt das Skript abstürzen zu lassen.
    """
    url = f"{BASE_URL}/{endpoint}"
    resp = session.get(url, params=params, timeout=20)

    if resp.status_code == 429:
        if retries > 0:
            print("   429 Too Many Requests - warte 15 Sekunden und versuche erneut ...")
            time.sleep(15)
            return _get(endpoint, params, retries=retries - 1)
        else:
            print("   429 Too Many Requests - erneut gescheitert. Skript stoppt hier sauber.")
            sys.exit(0)

    resp.raise_for_status()
    data = resp.json()

    remaining = resp.headers.get("x-ratelimit-requests-remaining")
    if remaining is not None and int(remaining) % 100 == 0:
        print(f"   -> verbleibende Requests heute: {remaining}")
        if int(remaining) <= 0:
            print("Tageslimit erreicht. Skript stoppt hier, morgen einfach erneut starten.")
            sys.exit(0)

    if data.get("errors"):
        print(f"   WARNUNG API-Fehler: {data['errors']}")

    return data


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
    fixtures_by_id = {}  # dedupe über fixture-id, falls ein Spiel doppelt auftaucht

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

    def _match_date(fixture):
        return fixture.get("fixture", {}).get("date", "")

    all_fixtures.sort(key=_match_date, reverse=True)
    return all_fixtures


def main():
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

    print("\nFertig (oder Tageslimit erreicht - dann einfach morgen erneut starten).")


if __name__ == "__main__":
    main()
