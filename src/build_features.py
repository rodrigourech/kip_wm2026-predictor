"""
Feature Engineering: baut aus den Rohdaten (Fixtures, Match-Stats, Ranking)
eine Trainings-Tabelle für die Random-Forest-Modelle.

WICHTIG (Data Leakage vermeiden): Für jedes historische Spiel zwischen zwei
WM-2026-Teams werden Formkurve/Stats/Ranking NUR aus Daten berechnet, die vor
dem jeweiligen Spieldatum verfügbar waren - nie aus der Zukunft dieses Spiels.

Enthält auch die Lade-/Filter-Utilities für Fixtures (ehem. data_utils.py) -
zusammengeführt, da sie ausschliesslich hier verwendet wurden.

Input:
  - data/raw/fixtures_*.json (Spiele pro Team)
  - data/raw/stats/*.json (Ballbesitz, Schüsse, Ecken pro Spiel)
  - data/raw/elo_ratings_wc2026.csv (Elo-Rating als Ranking-Ersatz)

Output:
  - data/processed/match_features.csv (eine Zeile pro Spiel zwischen zwei
    WM-2026-Teams, mit allen berechneten Features + Zielvariable)

Aufruf:
    python src/build_features.py
"""
import csv
import json
from pathlib import Path

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR, WM2026_TEAMS

STATS_DIR = DATA_RAW_DIR / "stats"
RANKING_CSV = DATA_RAW_DIR / "elo_ratings_wc2026.csv"
TEAM_ID_CACHE_FILE = DATA_RAW_DIR / "team_ids.json"

DECAY_FACTOR = 0.87  # Gewichtsfaktor pro Spiel zurück, entspricht Halbwertszeit ~5 Spiele
# (0.87^5 ≈ 0.50 - ein Spiel vor 5 Spielen zählt noch halb so stark wie das letzte)

# Die WM 2026 läuft ab diesem Datum - per Default schliessen wir diese Spiele
# aus den Trainingsdaten aus, da sie das eigentliche Vorhersageziel sind und
# nicht als "historische Formkurve" ins Modell einfliessen sollen.
WM2026_START_DATE = "2026-06-19"

# Unser FIFA-Teamname -> Name in der Ranking-CSV (weicht bei manchen Teams ab)
RANKING_NAME_MAP = {
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Côte d'Ivoire": "Ivory Coast",
    "USA": "United States",
    "Türkiye": "Turkey",
}

# API-Football Statistik-Typ -> unser Feature-Name
STATS_TYPES = {
    "Ball Possession": "possession",
    "Total Shots": "shots_total",
    "Shots on Goal": "shots_on_goal",
    "Corner Kicks": "corners",
}


# ---------------------------------------------------------------------------
# Laden & Filtern der Fixtures (ehem. data_utils.py)
# ---------------------------------------------------------------------------

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

    Falls include_wm2026=False (Default), werden Spiele ab cutoff_date entfernt.
    Falls True, bleiben alle Spiele erhalten (z.B. für einen Dashboard-Toggle,
    der WM-2026-Resultate testweise einbeziehen will).
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


# ---------------------------------------------------------------------------
# Team-IDs & Ranking (Elo)
# ---------------------------------------------------------------------------

def load_team_id_cache() -> dict:
    return json.loads(TEAM_ID_CACHE_FILE.read_text(encoding="utf-8"))


def load_ranking_ratings() -> dict:
    """Liest die Ranking-CSV (Elo-Ratings) ein: {year: {country_name: rating}}"""
    ranking_by_year = {}
    with open(RANKING_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["year"])
            country = row["country"]
            try:
                rating = float(row["rating"])
            except (ValueError, TypeError):
                continue
            ranking_by_year.setdefault(year, {})[country] = rating
    return ranking_by_year


def get_ranking(ranking_by_year: dict, fifa_name: str, year: int):
    """Holt das Ranking (Elo-Rating) für ein Team im gegebenen Jahr, sonst das
    letzte verfügbare Jahr davor (falls für dieses exakte Jahr nichts vorliegt)."""
    ranking_name = RANKING_NAME_MAP.get(fifa_name, fifa_name)
    for y in range(year, 1900, -1):
        if y in ranking_by_year and ranking_name in ranking_by_year[y]:
            return ranking_by_year[y][ranking_name]
    return None


# ---------------------------------------------------------------------------
# Match-Stats & Spielhistorie
# ---------------------------------------------------------------------------

def parse_match_stats(fixture_id, team_api_id) -> dict:
    """Liest die Match-Stats-Datei eines Fixtures und gibt die Werte für EIN
    Team (anhand seiner API-Football-ID) zurück."""
    stats_file = STATS_DIR / f"{fixture_id}.json"
    if not stats_file.exists():
        return {}
    try:
        response = json.loads(stats_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not response:
        return {}

    result = {}
    for team_block in response:
        if team_block.get("team", {}).get("id") != team_api_id:
            continue
        for stat in team_block.get("statistics", []):
            stat_type = stat.get("type")
            if stat_type not in STATS_TYPES:
                continue
            value = stat.get("value")
            if isinstance(value, str) and value.endswith("%"):
                value = value.replace("%", "")
            if value is not None:
                try:
                    result[STATS_TYPES[stat_type]] = float(value)
                except (ValueError, TypeError):
                    pass
    return result


def build_team_match_history(fifa_name: str, own_id: int, id_to_fifa_name: dict, include_wm2026: bool = False) -> list:
    """Baut die chronologische Spielhistorie eines Teams aus TEAM-Sicht auf
    (nicht Heim/Auswärts-Rohdaten), inkl. Ergebnis, Gegner und Stats.

    include_wm2026: Falls True, werden auch bereits gespielte WM-2026-Partien
    einbezogen (relevant für den Dashboard-Toggle bei aktuellen Vorhersagen)."""
    fixtures = load_filtered_team_fixtures(fifa_name, include_wm2026=include_wm2026)

    history = []
    for fx in fixtures:
        fixture_info = fx.get("fixture", {})
        teams_info = fx.get("teams", {})
        goals_info = fx.get("goals", {})

        home = teams_info.get("home", {})
        away = teams_info.get("away", {})

        date_str = fixture_info.get("date", "")
        if not date_str:
            continue

        is_home = home.get("id") == own_id
        opp_side = away if is_home else home

        own_goals = goals_info.get("home") if is_home else goals_info.get("away")
        opp_goals = goals_info.get("away") if is_home else goals_info.get("home")
        if own_goals is None or opp_goals is None:
            continue  # kein Ergebnis vorhanden (z.B. abgesagtes Spiel)

        if own_goals > opp_goals:
            points = 3
        elif own_goals == opp_goals:
            points = 1
        else:
            points = 0

        stats = parse_match_stats(fixture_info.get("id"), own_id)
        opponent_fifa_name = id_to_fifa_name.get(opp_side.get("id"))

        history.append({
            "fixture_id": fixture_info.get("id"),
            "date": date_str[:10],
            "is_home": is_home,
            "opponent_fifa_name": opponent_fifa_name,  # None, falls kein WM-2026-Team
            "opponent_name": opp_side.get("name", "Unbekannt"),  # roher API-Name, immer vorhanden
            "goals_for": own_goals,
            "goals_against": opp_goals,
            "points": points,
            **stats,
        })

    history.sort(key=lambda r: r["date"])
    return history


def compute_rolling_features(history: list, before_date: str, decay: float = DECAY_FACTOR):
    """Formkurve/Tordurchschnitt/Stats-Schnitt als exponentiell gewichteter
    Durchschnitt (EWMA) über die GESAMTE verfügbare Historie vor before_date -
    kein fester Fenster-Cutoff mehr, sondern neuere Spiele zählen graduell mehr
    als ältere. Methodisch konsistent mit dem Prinzip von Elo-Ratings.

    Gibt None zurück, falls keine Historie vorhanden ist.
    """
    past_games = [g for g in history if g["date"] < before_date]
    if not past_games:
        return None

    # Neuestes Spiel zuerst, damit Gewicht[0] = neuestes Spiel (höchstes Gewicht)
    past_games_desc = list(reversed(past_games))
    weights = [decay ** i for i in range(len(past_games_desc))]

    def weighted_avg(pairs):
        """pairs: Liste von (wert, gewicht) - überspringt Spiele ohne diesen Wert."""
        num = sum(v * w for v, w in pairs)
        denom = sum(w for _, w in pairs)
        return num / denom if denom > 0 else None

    form_points = weighted_avg(list(zip((g["points"] for g in past_games_desc), weights)))
    goals_for_avg = weighted_avg(list(zip((g["goals_for"] for g in past_games_desc), weights)))
    goals_against_avg = weighted_avg(list(zip((g["goals_against"] for g in past_games_desc), weights)))

    features = {
        "form_points": round(form_points, 2) if form_points is not None else None,
        "form_games_count": len(past_games_desc),  # Total verfügbare Spiele (nicht mehr "Fenstergrösse")
        "goals_for_avg": round(goals_for_avg, 2) if goals_for_avg is not None else None,
        "goals_against_avg": round(goals_against_avg, 2) if goals_against_avg is not None else None,
    }

    for stat_key in STATS_TYPES.values():
        pairs = [(g[stat_key], w) for g, w in zip(past_games_desc, weights) if stat_key in g]
        val = weighted_avg(pairs) if pairs else None
        features[f"{stat_key}_avg"] = round(val, 2) if val is not None else None

    return features


def get_h2h_matches(history_a: list, fifa_name_b: str, before_date: str) -> list:
    """Gibt die einzelnen H2H-Spiele (chronologisch, neuestes zuerst) zurück,
    inkl. Datum und Resultat aus Sicht von Team A - für Detail-Anzeigen."""
    matches = [g for g in history_a if g["opponent_fifa_name"] == fifa_name_b and g["date"] < before_date]
    return sorted(matches, key=lambda g: g["date"], reverse=True)


def compute_h2h(history_a: list, fifa_name_b: str, before_date: str) -> dict:
    """Head-to-Head-Bilanz von Team A gegen Team B, aus Sicht von Team A."""
    h2h_games = [g for g in history_a if g["opponent_fifa_name"] == fifa_name_b and g["date"] < before_date]
    return {
        "h2h_games": len(h2h_games),
        "h2h_a_wins": sum(1 for g in h2h_games if g["points"] == 3),
        "h2h_a_draws": sum(1 for g in h2h_games if g["points"] == 1),
        "h2h_a_losses": sum(1 for g in h2h_games if g["points"] == 0),
    }


def main():
    team_id_cache = load_team_id_cache()
    id_to_fifa_name = {v: k for k, v in team_id_cache.items()}
    ranking_by_year = load_ranking_ratings()

    print("Baue Spielhistorien pro Team...")
    histories = {}
    for fifa_name in WM2026_TEAMS:
        if fifa_name not in team_id_cache:
            print(f"  WARNUNG: keine Team-ID für {fifa_name} - übersprungen.")
            continue
        own_id = team_id_cache[fifa_name]
        histories[fifa_name] = build_team_match_history(fifa_name, own_id, id_to_fifa_name)

    print(f"  {len(histories)} Teams mit Historie geladen.\n")
    print("Suche Spiele zwischen zwei WM-2026-Teams und berechne Features...")

    rows = []
    seen_fixture_ids = set()

    for fifa_name, history in histories.items():
        for game in history:
            fixture_id = game["fixture_id"]
            opponent = game["opponent_fifa_name"]

            if opponent is None or opponent not in histories:
                continue  # Gegner ist kein WM-2026-Team
            if fixture_id in seen_fixture_ids:
                continue  # Spiel schon aus der anderen Perspektive erfasst
            seen_fixture_ids.add(fixture_id)

            match_date = game["date"]

            feat_a = compute_rolling_features(history, match_date)
            feat_b = compute_rolling_features(histories[opponent], match_date)
            if feat_a is None or feat_b is None:
                continue  # zu wenig Historie vor diesem Spiel

            h2h = compute_h2h(history, opponent, match_date)
            year = int(match_date[:4])
            ranking_a = get_ranking(ranking_by_year, fifa_name, year)
            ranking_b = get_ranking(ranking_by_year, opponent, year)

            row = {
                "fixture_id": fixture_id,
                "date": match_date,
                "team_a": fifa_name,
                "team_b": opponent,
                "a_is_home": game["is_home"],
                "goals_a": game["goals_for"],
                "goals_b": game["goals_against"],
                "result": "A" if game["points"] == 3 else ("Draw" if game["points"] == 1 else "B"),
            }
            row.update({f"a_{k}": v for k, v in feat_a.items()})
            row.update({f"b_{k}": v for k, v in feat_b.items()})
            row.update(h2h)
            row["ranking_a"] = ranking_a
            row["ranking_b"] = ranking_b
            row["ranking_diff"] = (ranking_a - ranking_b) if (ranking_a is not None and ranking_b is not None) else None

            rows.append(row)

    print(f"\n{len(rows)} Spiele zwischen WM-2026-Teams mit ausreichend Historie gefunden.")

    if not rows:
        print("Keine Zeilen zum Speichern - Abbruch.")
        return

    output_file = DATA_PROCESSED_DIR / "match_features.csv"
    fieldnames = list(rows[0].keys())
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Gespeichert: {output_file}")


if __name__ == "__main__":
    main()
