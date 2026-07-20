"""
Abruf der Spielstatistiken (Ballbesitz, Schüsse, Ecken etc.) für alle bereits
abgerufenen Fixtures.

Sammelt zuerst alle EINDEUTIGEN Fixture-IDs über alle 48 Teams-Dateien (ein
Spiel zwischen zwei WM-2026-Teams taucht sonst doppelt auf - einmal pro Team -
und würde ohne Deduplizierung zweimal abgerufen). Danach wird pro eindeutiger
Fixture-ID ein Call an /fixtures/statistics gemacht.

Resumable wie fetch_data.py: bereits abgerufene Fixture-Stats werden
übersprungen, bei Tageslimit stoppt das Skript sauber und kann am nächsten
Tag erneut gestartet werden.

Kosten: ca. 1 Request pro eindeutigem Fixture (~mehrere Tausend total) -
kann je nach Datenmenge mehr als einen Tag dauern.

Aufruf:
    python src/fetch_match_stats.py
"""
import json
import sys
import time
from pathlib import Path

import requests

from config import BASE_URL, HEADERS, DATA_RAW_DIR

STATS_DIR = DATA_RAW_DIR / "stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)

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
            print("   Überspringe dieses Fixture, Skript läuft weiter.")
            return {"response": None}  # Signalisiert dem Aufrufer: nichts Verwertbares erhalten

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
    """Liest eine JSON-Datei ein, mit Fallback auf cp1252 falls UTF-8 fehlschlägt.

    Grund: Die ersten paar abgerufenen Teams-Dateien wurden vor einem
    Encoding-Fix mit der Windows-Standardkodierung (cp1252) statt UTF-8
    gespeichert. Damit ältere Dateien trotzdem lesbar bleiben (ohne sie neu
    abrufen zu müssen), wird hier automatisch zurückgefallen.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="cp1252"))


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


def main():
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
            # Netzwerkfehler trotz Retries - überspringen, beim nächsten Lauf erneut versuchen
            failed += 1
            time.sleep(SLEEP_BETWEEN_CALLS)
            continue

        stats_file.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        newly_fetched += 1

        if newly_fetched % 50 == 0:
            print(f"   ... {newly_fetched} neu abgerufen, {already_done} übersprungen (schon vorhanden)")

        time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"\nFertig (oder Tageslimit erreicht). Neu abgerufen: {newly_fetched}, übersprungen: {already_done}")
    if failed:
        print(f"Wegen Netzwerkfehlern übersprungen (werden beim nächsten Lauf erneut versucht): {failed}")
    print("Falls nicht alle Fixtures durch sind: Skript einfach erneut starten.")


if __name__ == "__main__":
    main()
