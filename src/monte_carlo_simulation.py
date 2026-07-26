"""
Monte-Carlo-Simulation des kompletten WM-2026-Turniers (Gruppenphase bis Final).

Nutzt die trainierten Modelle (Klassifikator + Tore-Regressor) aus
train_models.py, um jedes Spiel zufällig gemäss den Modell-Wahrscheinlichkeiten
auszuwürfeln (nicht deterministisch den Favoriten gewinnen zu lassen).

WICHTIGE, DOKUMENTIERTE VEREINFACHUNGEN (siehe Entwicklungsbericht):

1. Gruppen-Tiebreaker: Punkte -> Tordifferenz -> Tore -> Ranking (Elo).
   Der offizielle Fairplay-Tiebreaker wird NICHT simuliert (Kartendisziplin
   lässt sich mit den vorhandenen Daten nicht sinnvoll vorhersagen).

2. K.o.-Spiele können nicht unentschieden enden: Bei Gleichstand werden die
   Sieg-Wahrscheinlichkeiten von A und B neu skaliert (ohne Draw-Anteil),
   z.B. P(A)=45%, P(B)=30% -> P(A|kein Draw)=60%, P(B|kein Draw)=40%.

3. Die Achtelfinal-Zuordnung der Drittplatzierten folgt EXAKT der offiziellen
   FIFA-Tabelle (Annex C, 495 Kombinationen, aus annex_c.json). Die übrigen
   8 Achtelfinal-Spiele (Gruppensieger vs. Gruppenzweite, Zweiter vs. Zweiter)
   sowie die Weiterleitung Achtelfinale bis Final folgen dem offiziellen
   FIFA-Spielplan, geladen aus fifa_match_schedule.json (Quelle: Wikipedia-
   Zusammenfassung der offiziellen FIFA-Turnierbestimmungen, gegen die
   Tests in test_tournament_logic.py verifiziert).

4. Die Verknüpfung Achtelfinale -> Viertelfinale -> Halbfinale -> Finale folgt
   ebenfalls fifa_match_schedule.json (siehe Punkt 3).

5. Team-Formkurve/Ranking werden EINMALIG vor Turnierbeginn (Stand
   WM2026_START_DATE) berechnet und bleiben über die gesamte Simulation
   konstant - simulierte Turnierspiele fliessen nicht in die Form der
   nächsten Runde ein (sonst müsste man laufend neu trainieren/berechnen).

Aufruf:
    python src/simulate_tournament.py --n 1000
"""
import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import datetime

import joblib
import pandas as pd

from config import DATA_RAW_DIR, DATA_PROCESSED_DIR, PROJECT_ROOT, WM2026_TEAMS
from build_features import (
    load_team_id_cache,
    load_ranking_ratings,
    get_ranking,
    build_team_match_history,
    compute_rolling_features,
    compute_h2h,
    WM2026_START_DATE,
)

MODELS_DIR = PROJECT_ROOT / "models"
GROUPS_CSV = DATA_RAW_DIR / "wm2026_groups.csv"
ANNEX_C_JSON = DATA_RAW_DIR / "annex_c.json"
FIFA_SCHEDULE_JSON = DATA_RAW_DIR / "fifa_match_schedule.json"


def load_fifa_schedule():
    """Laedt die offizielle Achtelfinal-Zuordnung und Turnierbaum-Weiterleitung
    aus fifa_match_schedule.json (analog zu load_annex_c() weiter unten),
    statt sie als Python-Dictionary hart im Code zu haben. Quelle und
    Verifikation gegen die Tests stehen im JSON selbst dokumentiert."""
    data = json.loads(FIFA_SCHEDULE_JSON.read_text(encoding="utf-8"))
    r32_slots = {int(k): tuple(v) for k, v in data["r32_match_slots"].items()}
    third_place_slots = data["third_place_slots"]
    knockout_bracket = {int(k): tuple(v) for k, v in data["knockout_bracket"].items()}
    return r32_slots, third_place_slots, knockout_bracket


# Offizielle Matchnummern der ersten K.-o.-Runde. "1X" = Sieger Gruppe X,
# "2X" = Zweiter Gruppe X. Bei den Gruppensiegern gegen Drittplatzierte wird
# der Gegner über Annex C bestimmt. Geladen aus fifa_match_schedule.json.
#
# Feste Weiterleitung gemäss offiziellem FIFA-Spielplan.
# Zielspiel -> Quellspiele, deren Sieger gegeneinander antreten.
# Ebenfalls geladen aus fifa_match_schedule.json.
R32_MATCH_SLOTS, THIRD_PLACE_SLOTS, KNOCKOUT_BRACKET = load_fifa_schedule()


def build_knockout_round_matches(winner_by_match, target_match_numbers):
    """Erstellt die nächste K.-o.-Runde aus den Siegern der offiziellen Quellspiele."""
    return {
        target: (
            winner_by_match[KNOCKOUT_BRACKET[target][0]],
            winner_by_match[KNOCKOUT_BRACKET[target][1]],
        )
        for target in target_match_numbers
    }


# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------

def load_groups() -> dict:
    groups = defaultdict(list)
    with open(GROUPS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            groups[row["group"]].append(row["team"])
    return dict(groups)


def load_annex_c() -> dict:
    data = json.loads(ANNEX_C_JSON.read_text(encoding="utf-8"))
    return {row["qualified_groups"]: row for row in data["rows"]}


def load_models():
    clf_model = joblib.load(MODELS_DIR / "random_forest_model.pkl")
    clf_imputer = joblib.load(MODELS_DIR / "imputer.pkl")
    clf_feature_cols = json.loads((MODELS_DIR / "feature_columns.json").read_text(encoding="utf-8"))
    goals_model = joblib.load(MODELS_DIR / "goals_regressor_model.pkl")
    goals_imputer = joblib.load(MODELS_DIR / "goals_imputer.pkl")
    goals_feature_cols = json.loads((MODELS_DIR / "goals_feature_columns.json").read_text(encoding="utf-8"))
    return clf_model, clf_imputer, clf_feature_cols, goals_model, goals_imputer, goals_feature_cols


def precompute_team_features(team_id_cache: dict, id_to_fifa_name: dict, ranking_by_year: dict) -> tuple:
    """Formkurve/Ranking EINMALIG als 'Stand kurz vor Turnierbeginn' berechnen."""
    histories = {}
    static_feat = {}
    year = int(WM2026_START_DATE[:4])
    for name in WM2026_TEAMS:
        if name not in team_id_cache:
            continue
        own_id = team_id_cache[name]
        hist = build_team_match_history(name, own_id, id_to_fifa_name, include_wm2026=False)
        histories[name] = hist
        static_feat[name] = {
            "feat": compute_rolling_features(hist, WM2026_START_DATE),
            "ranking": get_ranking(ranking_by_year, name, year),
        }
    return histories, static_feat


# ---------------------------------------------------------------------------
# Match-Vorhersage (gecached pro Team-Paarung, s.o. Vereinfachung 5)
# ---------------------------------------------------------------------------

def build_row(team_a: str, team_b: str, histories: dict, static_feat: dict):
    feat_a = static_feat.get(team_a, {}).get("feat")
    feat_b = static_feat.get(team_b, {}).get("feat")
    if feat_a is None or feat_b is None:
        return None

    h2h = compute_h2h(histories[team_a], team_b, WM2026_START_DATE)
    ranking_a = static_feat[team_a]["ranking"]
    ranking_b = static_feat[team_b]["ranking"]

    row = {"a_is_home": False}
    row.update({f"a_{k}": v for k, v in feat_a.items()})
    row.update({f"b_{k}": v for k, v in feat_b.items()})
    row.update(h2h)
    row["ranking_a"] = ranking_a
    row["ranking_b"] = ranking_b
    row["ranking_diff"] = (ranking_a - ranking_b) if (ranking_a is not None and ranking_b is not None) else None
    return row


def get_match_prediction(team_a: str, team_b: str, cache: dict, models: tuple, histories: dict, static_feat: dict):
    key = (team_a, team_b)
    if key in cache:
        return cache[key]

    clf_model, clf_imputer, clf_feature_cols, goals_model, goals_imputer, goals_feature_cols = models
    row = build_row(team_a, team_b, histories, static_feat)

    if row is None:
        result = {"proba": {"A": 1 / 3, "Draw": 1 / 3, "B": 1 / 3}, "goals_a": 1.2, "goals_b": 1.2}
        cache[key] = result
        return result

    X_clf = pd.DataFrame([row])[clf_feature_cols]
    proba = clf_model.predict_proba(clf_imputer.transform(X_clf))[0]
    proba_dict = dict(zip(clf_model.classes_, proba))

    X_goals = pd.DataFrame([row])[goals_feature_cols]
    goals_pred = goals_model.predict(goals_imputer.transform(X_goals))[0]

    result = {"proba": proba_dict, "goals_a": goals_pred[0], "goals_b": goals_pred[1]}
    cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Einzelspiel-Simulation
# ---------------------------------------------------------------------------

def simulate_group_match(team_a, team_b, cache, models, histories, static_feat, rng):
    """Gruppenspiel: Unentschieden möglich, Torzahlen konsistent zum Ausgang."""
    pred = get_match_prediction(team_a, team_b, cache, models, histories, static_feat)
    proba = pred["proba"]
    p_a, p_draw = proba.get("A", 0), proba.get("Draw", 0)

    r = rng.random()
    outcome = "A" if r < p_a else ("Draw" if r < p_a + p_draw else "B")

    goals_a = max(0, round(pred["goals_a"]))
    goals_b = max(0, round(pred["goals_b"]))
    if outcome == "A" and goals_a <= goals_b:
        goals_a = goals_b + 1
    elif outcome == "B" and goals_b <= goals_a:
        goals_b = goals_a + 1
    elif outcome == "Draw" and goals_a != goals_b:
        goals_a = goals_b = round((goals_a + goals_b) / 2)

    return goals_a, goals_b


def simulate_knockout_match(team_a, team_b, cache, models, histories, static_feat, rng) -> str:
    """K.o.-Spiel: kein Unentschieden möglich - Wahrscheinlichkeiten ohne
    Draw-Anteil neu skaliert (s.o. Vereinfachung 2). Gibt nur den Sieger zurück."""
    winner, _, _ = simulate_knockout_match_with_score(team_a, team_b, cache, models, histories, static_feat, rng)
    return winner


def simulate_knockout_match_with_score(team_a, team_b, cache, models, histories, static_feat, rng):
    """Wie simulate_knockout_match, gibt zusätzlich einen plausiblen Spielstand
    zurück (aus dem Tore-Regressor, konsistent zum gewürfelten Sieger
    zurechtgerückt). Für die Spielverlauf-Anzeige - der Spielstand ist
    illustrativ, echte K.o.-Spiele könnten in Verlängerung/Elfmeterschiessen
    gehen, was hier nicht separat modelliert wird."""
    pred = get_match_prediction(team_a, team_b, cache, models, histories, static_feat)
    proba = pred["proba"]
    p_a, p_b = proba.get("A", 0), proba.get("B", 0)
    denom = p_a + p_b
    p_a_rescaled = p_a / denom if denom > 0 else 0.5
    winner_is_a = rng.random() < p_a_rescaled

    goals_a = max(0, round(pred["goals_a"]))
    goals_b = max(0, round(pred["goals_b"]))
    if winner_is_a and goals_a <= goals_b:
        goals_a = goals_b + 1
    elif not winner_is_a and goals_b <= goals_a:
        goals_b = goals_a + 1

    winner = team_a if winner_is_a else team_b
    return winner, goals_a, goals_b


# ---------------------------------------------------------------------------
# Gruppentabelle mit Tiebreakern
# ---------------------------------------------------------------------------

def compute_group_standings(group_teams: list, results: dict, static_feat: dict):
    stats = {t: {"pts": 0, "gf": 0, "ga": 0} for t in group_teams}
    for (a, b), (ga, gb) in results.items():
        stats[a]["gf"] += ga
        stats[a]["ga"] += gb
        stats[b]["gf"] += gb
        stats[b]["ga"] += ga
        if ga > gb:
            stats[a]["pts"] += 3
        elif ga < gb:
            stats[b]["pts"] += 3
        else:
            stats[a]["pts"] += 1
            stats[b]["pts"] += 1

    def sort_key(t):
        s = stats[t]
        gd = s["gf"] - s["ga"]
        ranking = static_feat.get(t, {}).get("ranking") or 0
        return (-s["pts"], -gd, -s["gf"], -ranking)

    ranked = sorted(group_teams, key=sort_key)
    return ranked, stats


# ---------------------------------------------------------------------------
# Kompletter Turnier-Durchlauf
# ---------------------------------------------------------------------------

def simulate_tournament(groups, annex_c_by_combo, cache, models, histories, static_feat, rng):
    # 1. Gruppenphase (Round Robin)
    group_standings = {}
    group_stats = {}
    group_match_details = {}  # group -> [(team_a, team_b, goals_a, goals_b), ...]
    for group, teams in groups.items():
        results = {}
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                a, b = teams[i], teams[j]
                results[(a, b)] = simulate_group_match(a, b, cache, models, histories, static_feat, rng)
        ranked, stats = compute_group_standings(teams, results, static_feat)
        group_standings[group] = ranked
        group_stats[group] = stats
        group_match_details[group] = [(a, b, ga, gb) for (a, b), (ga, gb) in results.items()]

    winners = {g: group_standings[g][0] for g in groups}
    runners_up = {g: group_standings[g][1] for g in groups}
    thirds = {g: group_standings[g][2] for g in groups}

    # 2. Drittplatzierten-Ranking über alle 12 Gruppen
    def third_sort_key(g):
        s = group_stats[g][thirds[g]]
        gd = s["gf"] - s["ga"]
        ranking = static_feat.get(thirds[g], {}).get("ranking") or 0
        return (-s["pts"], -gd, -s["gf"], -ranking)

    ranked_third_groups = sorted(groups.keys(), key=third_sort_key)
    qualified_third_groups = sorted(ranked_third_groups[:8])
    combo_key = "".join(qualified_third_groups)

    annex_row = annex_c_by_combo.get(combo_key)
    if annex_row is None:
        raise ValueError(f"Keine Annex-C-Kombination gefunden für: {combo_key}")

    # 3. Round of 32 anhand der offiziellen Matchnummern zusammenbauen
    def resolve_group_slot(slot):
        kind, group = slot[0], slot[1]
        if kind == "1":
            return winners[group]
        if kind == "2":
            return runners_up[group]
        raise ValueError(f"Unbekannter Gruppenslot: {slot}")

    r32_matches = {}
    for match_number, (slot_a, slot_b) in R32_MATCH_SLOTS.items():
        team_a = resolve_group_slot(slot_a)
        if slot_b == "3?":
            third_slot = annex_row[slot_a]
            team_b = thirds[third_slot[1]]
        else:
            team_b = resolve_group_slot(slot_b)
        r32_matches[match_number] = (team_a, team_b)

    # 4. K.-o.-Runden gemäss fester FIFA-Weiterleitung simulieren
    def play_matches(matches_by_number):
        winner_by_match = {}
        details = []
        for match_number in sorted(matches_by_number):
            a, b = matches_by_number[match_number]
            winner, ga, gb = simulate_knockout_match_with_score(
                a, b, cache, models, histories, static_feat, rng
            )
            winner_by_match[match_number] = winner
            details.append((a, b, ga, gb, winner))
        return winner_by_match, details

    r32_winners, r32_details = play_matches(r32_matches)

    r16_matches = build_knockout_round_matches(r32_winners, range(89, 97))
    r16_winners, r16_details = play_matches(r16_matches)

    quarterfinal_matches = build_knockout_round_matches(r16_winners, range(97, 101))
    quarterfinal_winners, r8_details = play_matches(quarterfinal_matches)

    semifinal_matches = build_knockout_round_matches(quarterfinal_winners, range(101, 103))
    semifinal_winners, r4_details = play_matches(semifinal_matches)

    final_matches = build_knockout_round_matches(semifinal_winners, [104])
    final_winners, final_details = play_matches(final_matches)
    champion = final_winners[104]

    r16_teams = [r32_winners[n] for n in range(73, 89)]
    r8_teams = [r16_winners[n] for n in range(89, 97)]
    r4_teams = [quarterfinal_winners[n] for n in range(97, 101)]
    r2_teams = [semifinal_winners[n] for n in range(101, 103)]

    return {
        "champion": champion,
        "finalists": r2_teams,
        "semifinalists": r4_teams,
        "quarterfinalists": r8_teams,
        "round_of_16": r16_teams,
        "group_standings": group_standings,
        "group_match_details": group_match_details,
        "knockout_details": {
            "round_of_32": r32_details,
            "round_of_16": r16_details,
            "quarterfinal": r8_details,
            "semifinal": r4_details,
            "final": final_details,
        },
    }


# ---------------------------------------------------------------------------
# Hauptprogramm: N Simulationen, Ergebnisse aggregieren
# ---------------------------------------------------------------------------

def main(n_simulations: int = 1000):
    print("Lade Modelle und Referenzdaten...")
    team_id_cache = load_team_id_cache()
    id_to_fifa_name = {v: k for k, v in team_id_cache.items()}
    ranking_by_year = load_ranking_ratings()
    models = load_models()
    histories, static_feat = precompute_team_features(team_id_cache, id_to_fifa_name, ranking_by_year)
    groups = load_groups()
    annex_c_by_combo = load_annex_c()
    cache = {}
    rng = random.Random(42)

    print(f"Starte {n_simulations} Turnier-Simulationen...\n")

    counters = {
        "champion": Counter(),
        "final": Counter(),
        "semifinal": Counter(),
        "quarterfinal": Counter(),
        "round_of_16": Counter(),
    }

    for i in range(n_simulations):
        result = simulate_tournament(groups, annex_c_by_combo, cache, models, histories, static_feat, rng)
        counters["champion"][result["champion"]] += 1
        for t in result["finalists"]:
            counters["final"][t] += 1
        for t in result["semifinalists"]:
            counters["semifinal"][t] += 1
        for t in result["quarterfinalists"]:
            counters["quarterfinal"][t] += 1
        for t in result["round_of_16"]:
            counters["round_of_16"][t] += 1

        if (i + 1) % max(1, n_simulations // 10) == 0:
            print(f"  {i + 1}/{n_simulations} Simulationen...")

    print("\n" + "=" * 60)
    print(f"ERGEBNISSE NACH {n_simulations} SIMULATIONEN")
    print("=" * 60)

    for label, key in [
        ("WELTMEISTER", "champion"),
        ("FINALE ERREICHT", "final"),
        ("HALBFINALE ERREICHT", "semifinal"),
        ("VIERTELFINALE ERREICHT", "quarterfinal"),
        ("ACHTELFINALE ERREICHT", "round_of_16"),
    ]:
        print(f"\nTop 10 - {label}:")
        for team, count in counters[key].most_common(10):
            print(f"  {team:<25} {100 * count / n_simulations:5.1f}%")

    # Ergebnisse als JSON speichern, damit das Dashboard sie laden kann
    output = {
        "n_simulations": n_simulations,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": {
            key: dict(counter.most_common())
            for key, counter in counters.items()
        },
    }
    output_path = DATA_PROCESSED_DIR / "tournament_simulation.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nErgebnisse gespeichert: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1000, help="Anzahl Simulationen")
    args = parser.parse_args()
    main(n_simulations=args.n)
