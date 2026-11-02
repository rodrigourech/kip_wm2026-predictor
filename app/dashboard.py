"""
WM 2026 Match Predictor - Streamlit-Dashboard.

Vier Registerkarten:
- Start: Überblick, Lesehilfe und Modellgrenzen
- Spielvorhersage: Wahrscheinlichkeiten und erwartetes Resultat für zwei Teams
- Turniersimulation: Chancen pro Runde, Gruppen, Turnierbaum, Team verfolgen
- Über das Modell: Datenquellen, Kennzahlen und Grenzen

Die Modell- und Simulationslogik liegt unverändert in src/. Dieses Skript
übernimmt nur Darstellung, Zwischenspeicher und Export.

Aufruf:
    streamlit run app/dashboard.py
"""
import base64
import json
import random
import sys
from collections import Counter
from datetime import date
from functools import lru_cache
from html import escape
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import PROJECT_ROOT, WM2026_TEAMS
from build_features import (
    load_team_id_cache,
    load_ranking_ratings,
    get_ranking,
    build_team_match_history,
    compute_rolling_features,
    compute_h2h,
    get_h2h_matches,
    WM2026_START_DATE,
)
import monte_carlo_simulation as sim

MODELS_DIR = PROJECT_ROOT / "models"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TODAY = date.today().isoformat()

# FIFA-Teamname -> (Flaggen-Code gemäss flag-icons, FIFA-Kürzel)
TEAMS_META = {
    "Canada": ("ca", "CAN"), "Mexico": ("mx", "MEX"), "USA": ("us", "USA"),
    "Australia": ("au", "AUS"), "Iraq": ("iq", "IRQ"), "IR Iran": ("ir", "IRN"),
    "Japan": ("jp", "JPN"), "Jordan": ("jo", "JOR"), "Korea Republic": ("kr", "KOR"),
    "Qatar": ("qa", "QAT"), "Saudi Arabia": ("sa", "KSA"), "Uzbekistan": ("uz", "UZB"),
    "Algeria": ("dz", "ALG"), "Cabo Verde": ("cv", "CPV"), "Congo DR": ("cd", "COD"),
    "Côte d'Ivoire": ("ci", "CIV"), "Egypt": ("eg", "EGY"), "Ghana": ("gh", "GHA"),
    "Morocco": ("ma", "MAR"), "Senegal": ("sn", "SEN"), "South Africa": ("za", "RSA"),
    "Tunisia": ("tn", "TUN"), "Curaçao": ("cw", "CUW"), "Haiti": ("ht", "HAI"),
    "Panama": ("pa", "PAN"), "Argentina": ("ar", "ARG"), "Brazil": ("br", "BRA"),
    "Colombia": ("co", "COL"), "Ecuador": ("ec", "ECU"), "Paraguay": ("py", "PAR"),
    "Uruguay": ("uy", "URU"), "New Zealand": ("nz", "NZL"), "Austria": ("at", "AUT"),
    "Belgium": ("be", "BEL"), "Bosnia and Herzegovina": ("ba", "BIH"), "Croatia": ("hr", "CRO"),
    "Czechia": ("cz", "CZE"), "England": ("gb-eng", "ENG"), "France": ("fr", "FRA"),
    "Germany": ("de", "GER"), "Netherlands": ("nl", "NED"), "Norway": ("no", "NOR"),
    "Portugal": ("pt", "POR"), "Scotland": ("gb-sct", "SCO"), "Spain": ("es", "ESP"),
    "Sweden": ("se", "SWE"), "Switzerland": ("ch", "SUI"), "Türkiye": ("tr", "TUR"),
}

# Farben (siehe auch .streamlit/config.toml)
INK, MUTED, LINE = "#172B23", "#6E7B74", "#E2E7E4"
PITCH, TEAM_A, TEAM_B, DRAW, GOLD = "#157347", "#1D3F8F", "#C8102E", "#8C98A4", "#B38A12"


# ---------------------------------------------------------------------------
# Assets: Flaggen und Schriften lokal eingebunden (funktioniert offline)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _flag_data_uri(team_name: str) -> str:
    code = TEAMS_META.get(team_name, (None,))[0]
    path = ASSETS_DIR / "flags" / f"{code}.svg"
    if not code or not path.exists():
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()


def flag(team_name: str, w: int = 22, h: int = 15, radius: int = 2) -> str:
    uri = _flag_data_uri(team_name)
    if not uri:
        return ""
    return (f"<img src='{uri}' alt='' style='width:{w}px;height:{h}px;border-radius:{radius}px;"
            f"object-fit:cover;box-shadow:0 0 0 1px rgba(0,0,0,.08);vertical-align:middle'>")


def code_of(team_name: str) -> str:
    return TEAMS_META.get(team_name, (None, team_name[:3].upper()))[1]


@lru_cache(maxsize=None)
def _font_faces() -> str:
    faces = [("Barlow Condensed", 700, "barlow-condensed-latin-700-normal.woff2"),
             ("Barlow Condensed", 800, "barlow-condensed-latin-800-normal.woff2"),
             ("Barlow", 400, "barlow-latin-400-normal.woff2"),
             ("Barlow", 500, "barlow-latin-500-normal.woff2"),
             ("Barlow", 600, "barlow-latin-600-normal.woff2")]
    css = []
    for family, weight, file in faces:
        path = ASSETS_DIR / "fonts" / file
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            css.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-display:swap;"
                       f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "".join(css)


def inject_styles():
    st.markdown(f"""<style>
{_font_faces()}
html, body, [class*="css"], .stMarkdown, .stText, button, input, label {{ font-family:'Barlow',sans-serif; }}
header[data-testid="stHeader"], #MainMenu, footer {{ display:none; }}
.block-container {{ max-width:1240px; padding-top:0; padding-bottom:3rem; }}
.cond {{ font-family:'Barlow Condensed',sans-serif; }}
.stripe {{ position:fixed; top:0; left:0; right:0; height:4px; z-index:1000; background:linear-gradient(90deg,#D52B1E 0 33.3%,#006847 33.3% 66.6%,#0A3161 66.6%); }}
.brand {{ display:flex; align-items:baseline; gap:14px; padding:28px 0 4px; flex-wrap:wrap; }}
.brand .w {{ font-family:'Barlow Condensed'; font-weight:800; font-size:32px; color:{INK}; }}
.brand .s {{ color:{MUTED}; font-size:14px; }}
div[data-baseweb="tab-list"] {{ gap:30px; border-bottom:1px solid {LINE}; }}
button[data-baseweb="tab"] {{ padding:10px 0 12px; background:transparent; }}
button[data-baseweb="tab"] p {{ font-size:15.5px; font-weight:500; color:{MUTED}; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color:{INK}; font-weight:600; }}
div[data-baseweb="tab-highlight"] {{ background:{PITCH}; height:3px; }}
div[data-baseweb="tab-border"] {{ display:none; }}
h1.title {{ font-family:'Barlow Condensed'; font-weight:700; font-size:42px; line-height:1.08; color:{INK}; margin:18px 0 8px; max-width:860px; padding:0; }}
.lead {{ color:{MUTED}; font-size:17px; max-width:740px; margin-bottom:22px; }}
h2.sub {{ font-family:'Barlow Condensed'; font-weight:700; font-size:24px; color:{INK}; margin:0 0 8px; padding:0; }}
.panel {{ background:#fff; border:1px solid {LINE}; border-radius:10px; padding:22px 24px; }}
.muted {{ color:{MUTED}; }}
.note {{ border-left:3px solid {GOLD}; padding:4px 0 4px 14px; color:#5B4A12; font-size:14.5px; }}
.kpis {{ display:flex; gap:56px; flex-wrap:wrap; margin:8px 0 30px; }}
.kpis .v {{ font-family:'Barlow Condensed'; font-size:54px; font-weight:800; line-height:1; color:{INK}; }}
table.t {{ width:100%; border-collapse:collapse; font-size:14.5px; border:none; }}
table.t tr, table.t th, table.t td {{ border-left:none; border-right:none; border-top:none; background:transparent; }}
table.t th {{ text-align:left; color:{MUTED}; font-weight:500; font-size:13px; padding:8px 6px; border-bottom:1px solid {LINE}; }}
table.t td {{ padding:9px 6px; border-bottom:1px solid #EEF2EF; color:{INK}; }}
div[role="radiogroup"] {{ background:#EAEFEC; border-radius:8px; padding:3px; gap:2px; display:inline-flex; flex-wrap:wrap; }}
div[role="radiogroup"] label {{ padding:5px 14px; border-radius:6px; margin:0; }}
div[role="radiogroup"] label > div:first-child {{ display:none; }}
div[role="radiogroup"] label:has(input:checked) {{ background:#fff; box-shadow:0 1px 2px rgba(23,43,35,.12); }}
div[role="radiogroup"] label:has(input:checked) p {{ font-weight:600; color:{INK}; }}
div[role="radiogroup"] label p {{ color:{MUTED}; font-size:14px; }}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Daten und Modelle laden (zwischengespeichert)
# ---------------------------------------------------------------------------

@st.cache_resource
def load_models():
    clf_model = joblib.load(MODELS_DIR / "random_forest_model.pkl")
    clf_imputer = joblib.load(MODELS_DIR / "imputer.pkl")
    clf_feature_cols = json.loads((MODELS_DIR / "feature_columns.json").read_text(encoding="utf-8"))
    goals_model = joblib.load(MODELS_DIR / "goals_regressor_model.pkl")
    goals_imputer = joblib.load(MODELS_DIR / "goals_imputer.pkl")
    goals_feature_cols = json.loads((MODELS_DIR / "goals_feature_columns.json").read_text(encoding="utf-8"))
    return clf_model, clf_imputer, clf_feature_cols, goals_model, goals_imputer, goals_feature_cols


@st.cache_resource
def load_reference_data():
    team_id_cache = load_team_id_cache()
    id_to_fifa_name = {v: k for k, v in team_id_cache.items()}
    ranking_by_year = load_ranking_ratings()
    return team_id_cache, id_to_fifa_name, ranking_by_year


@st.cache_resource
def load_simulation_inputs():
    """Einmalige Vorberechnung für alle Simulationen (Teamform, Gruppen, Annex C)."""
    team_id_cache, id_to_fifa_name, ranking_by_year = load_reference_data()
    histories, static_feat = sim.precompute_team_features(team_id_cache, id_to_fifa_name, ranking_by_year)
    return histories, static_feat, sim.load_groups(), sim.load_annex_c()


@st.cache_data
def data_summary():
    """Kennzahlen für Kopfzeile und Startseite, direkt aus den Rohdaten berechnet."""
    team_id_cache, id_to_fifa_name, _ = load_reference_data()
    fixture_ids, dates = set(), []
    for team in WM2026_TEAMS:
        for g in build_team_match_history(team, team_id_cache[team], id_to_fifa_name):
            fixture_ids.add(g["fixture_id"])
            dates.append(g["date"])
    comparison = json.loads((MODELS_DIR / "model_comparison.json").read_text(encoding="utf-8"))
    rf_accuracy = next((m["accuracy"] for m in comparison if m["model"].startswith("Random Forest")), None)
    return {"matches": len(fixture_ids), "first_year": min(dates)[:4],
            "last_date": date.fromisoformat(max(dates)).strftime("%d.%m.%Y"),
            "annex_c_variants": len(sim.load_annex_c()), "rf_accuracy": rf_accuracy}


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", "'")


@st.cache_data
def get_team_history(fifa_name: str, include_wm2026: bool):
    team_id_cache, id_to_fifa_name, _ = load_reference_data()
    return build_team_match_history(fifa_name, team_id_cache[fifa_name], id_to_fifa_name,
                                    include_wm2026=include_wm2026)


@st.cache_data(show_spinner=False)
def simulate_many(n_simulations: int, seed: int = 42):
    """Simuliert n Turniere und gibt die vollständigen Resultate zurück."""
    histories, static_feat, groups, annex_c = load_simulation_inputs()
    models = load_models()
    rng = random.Random(seed)
    match_cache = {}
    results = [sim.simulate_tournament(groups, annex_c, match_cache, models, histories, static_feat, rng)
               for _ in range(n_simulations)]
    return results, groups


# ---------------------------------------------------------------------------
# Vorhersage für ein einzelnes Spiel
# ---------------------------------------------------------------------------

def build_matchup_row(team_a: str, team_b: str, include_wm2026: bool, as_of_date: str = TODAY):
    _, _, ranking_by_year = load_reference_data()
    hist_a = get_team_history(team_a, include_wm2026)
    hist_b = get_team_history(team_b, include_wm2026)
    feat_a = compute_rolling_features(hist_a, as_of_date)
    feat_b = compute_rolling_features(hist_b, as_of_date)
    if feat_a is None or feat_b is None:
        return None
    year = int(as_of_date[:4])
    ranking_a = get_ranking(ranking_by_year, team_a, year)
    ranking_b = get_ranking(ranking_by_year, team_b, year)
    row = {"a_is_home": True}
    row.update({f"a_{k}": v for k, v in feat_a.items()})
    row.update({f"b_{k}": v for k, v in feat_b.items()})
    row.update(compute_h2h(hist_a, team_b, as_of_date))
    row["ranking_a"] = ranking_a
    row["ranking_b"] = ranking_b
    row["ranking_diff"] = (ranking_a - ranking_b) if (ranking_a is not None and ranking_b is not None) else None
    return row


def predict(team_a: str, team_b: str, include_wm2026: bool):
    clf_model, clf_imputer, clf_cols, goals_model, goals_imputer, goals_cols = load_models()
    row = build_matchup_row(team_a, team_b, include_wm2026)
    if row is None:
        return None
    hist_a = get_team_history(team_a, include_wm2026)
    hist_b = get_team_history(team_b, include_wm2026)
    proba = clf_model.predict_proba(clf_imputer.transform(pd.DataFrame([row])[clf_cols]))[0]
    goals = goals_model.predict(goals_imputer.transform(pd.DataFrame([row])[goals_cols]))[0]
    return {
        "proba": dict(zip(clf_model.classes_, proba)),
        "goals_a": goals[0],
        "goals_b": goals[1],
        "row": row,
        "form_a": [g for g in hist_a if g["date"] < TODAY][-5:],
        "form_b": [g for g in hist_b if g["date"] < TODAY][-5:],
        "h2h_matches": get_h2h_matches(hist_a, team_b, TODAY),
    }


def actual_wm2026_results(team_a: str, team_b: str):
    hist = get_team_history(team_a, include_wm2026=True)
    return sorted((g for g in hist if g["opponent_fifa_name"] == team_b and g["date"] >= WM2026_START_DATE),
                  key=lambda g: g["date"])


# ---------------------------------------------------------------------------
# Kleine HTML-Bausteine
# ---------------------------------------------------------------------------

def html(markup: str):
    st.markdown(markup, unsafe_allow_html=True)


def form_tiles(games: list) -> str:
    colors = {3: PITCH, 1: "#C9A227", 0: TEAM_B}
    letters = {3: "S", 1: "U", 0: "N"}
    tiles = []
    for g in games:
        opponent = g.get("opponent_name") or g.get("opponent_fifa_name") or "unbekannt"
        tip = escape(f"{g['date']}: {g['goals_for']}:{g['goals_against']} gegen {opponent}")
        tiles.append(f"<span title='{tip}' style='display:inline-block;width:20px;height:20px;border-radius:4px;"
                     f"margin-left:3px;background:{colors[g['points']]};color:#fff;font-size:11px;font-weight:700;"
                     f"text-align:center;line-height:20px'>{letters[g['points']]}</span>")
    return "".join(tiles)


def probability_block(team_a: str, team_b: str, proba: dict) -> str:
    vals = {"A": proba.get("A", 0) * 100, "Draw": proba.get("Draw", 0) * 100, "B": proba.get("B", 0) * 100}
    top = max(vals, key=vals.get)
    colors = {"A": TEAM_A, "Draw": DRAW, "B": TEAM_B}
    labels = {"A": f"{flag(team_a)} Sieg {escape(team_a)}", "Draw": "Unentschieden",
              "B": f"{flag(team_b)} Sieg {escape(team_b)}"}
    cells = []
    for k in ("A", "Draw", "B"):
        is_top = k == top
        cells.append(
            f"<div style='flex:{max(vals[k], 12):.1f};min-width:140px'>"
            f"<div style='font-size:14px;{'font-weight:600;color:' + INK if is_top else 'color:' + MUTED}'>{labels[k]}</div>"
            f"<div class='cond' style='height:64px;display:flex;align-items:flex-end;font-weight:{800 if is_top else 600};"
            f"font-size:{62 if is_top else 40}px;line-height:1;margin:6px 0 10px;color:{colors[k] if is_top else '#9AA5AE'}'>{vals[k]:.0f}"
            f"<span style='font-size:{26 if is_top else 20}px;margin-left:4px'>%</span></div>"
            f"<div style='height:{10 if is_top else 6}px;border-radius:5px;background:{colors[k] if is_top else '#DDE3E0'}'></div>"
            f"</div>")
    return f"<div style='display:flex;gap:8px;align-items:flex-start'>{''.join(cells)}</div>"


def comparison_table(team_a: str, team_b: str, result: dict) -> str:
    row = result["row"]

    def fmt(v, decimals=1, suffix=""):
        return "–" if v is None else f"{v:,.{decimals}f}{suffix}".replace(",", "'")

    def better(va, vb, higher_is_better=True):
        if va is None or vb is None or va == vb:
            return None
        return "A" if (va > vb) == higher_is_better else "B"

    h2h_n = row.get("h2h_games", 0) or 0
    lines = [
        ("Form, letzte 5 Spiele", form_tiles(result["form_a"]), form_tiles(result["form_b"]), None),
        ("Elo-Stärke", fmt(row.get("ranking_a"), 0), fmt(row.get("ranking_b"), 0),
         better(row.get("ranking_a"), row.get("ranking_b"))),
        ("Ø Tore pro Spiel", fmt(row.get("a_goals_for_avg"), 2), fmt(row.get("b_goals_for_avg"), 2),
         better(row.get("a_goals_for_avg"), row.get("b_goals_for_avg"))),
        ("Ø Gegentore pro Spiel", fmt(row.get("a_goals_against_avg"), 2), fmt(row.get("b_goals_against_avg"), 2),
         better(row.get("a_goals_against_avg"), row.get("b_goals_against_avg"), higher_is_better=False)),
        ("Ø Ballbesitz", fmt(row.get("a_possession_avg"), 1, " %"), fmt(row.get("b_possession_avg"), 1, " %"),
         better(row.get("a_possession_avg"), row.get("b_possession_avg"))),
        ("Ø Schüsse pro Spiel", fmt(row.get("a_shots_total_avg")), fmt(row.get("b_shots_total_avg")),
         better(row.get("a_shots_total_avg"), row.get("b_shots_total_avg"))),
        ("Ø Schüsse aufs Tor", fmt(row.get("a_shots_on_goal_avg")), fmt(row.get("b_shots_on_goal_avg")),
         better(row.get("a_shots_on_goal_avg"), row.get("b_shots_on_goal_avg"))),
        ("Ø Ecken pro Spiel", fmt(row.get("a_corners_avg")), fmt(row.get("b_corners_avg")),
         better(row.get("a_corners_avg"), row.get("b_corners_avg"))),
    ]
    if h2h_n:
        wins_a, wins_b = row.get("h2h_a_wins", 0), row.get("h2h_a_losses", 0)
        lines.append((f"Direkte Duelle, {h2h_n} Spiele", f"{wins_a} {'Sieg' if wins_a == 1 else 'Siege'}",
                      f"{wins_b} {'Sieg' if wins_b == 1 else 'Siege'}",
                      better(row.get("h2h_a_wins", 0), row.get("h2h_a_losses", 0))))
    win_style = f"font-weight:700;color:{PITCH}"
    body = "".join(
        f"<tr><td style='text-align:right;width:30%;{win_style if w == 'A' else ''}'>{a}</td>"
        f"<td style='text-align:center;color:{MUTED}'>{label}</td>"
        f"<td style='width:30%;{win_style if w == 'B' else ''}'>{b}</td></tr>"
        for label, a, b, w in lines)
    return (f"<table class='t'><tr><th style='text-align:right'>{escape(team_a)}</th><th></th>"
            f"<th>{escape(team_b)}</th></tr>{body}</table>")


def bar_cell(value: float, highlight: bool = False) -> str:
    color = GOLD if highlight else PITCH
    return (f"<td><div style='display:flex;align-items:center;gap:8px'>"
            f"<div style='width:80px;height:6px;background:#E6EBE8;border-radius:3px'>"
            f"<div style='width:{value:.0f}%;height:6px;background:{color};border-radius:3px'></div></div>"
            f"<span style='{'font-weight:700' if highlight else ''}'>{value:.0f} %</span></div></td>")


# ---------------------------------------------------------------------------
# Auswertung der Simulationen
# ---------------------------------------------------------------------------

STAGES = [  # (Spaltenname, Schlüssel)
    ("Gruppe überstanden", "group_advanced"),
    ("Achtelfinal", "round_of_16"),
    ("Viertelfinal", "quarterfinal"),
    ("Halbfinal", "semifinal"),
    ("Final", "final"),
    ("Weltmeister", "champion"),
]


def stage_counts(results: list) -> dict:
    counts = {key: Counter() for _, key in STAGES}
    for r in results:
        for m in r["knockout_details"]["round_of_32"]:
            counts["group_advanced"][m[0]] += 1
            counts["group_advanced"][m[1]] += 1
        counts["round_of_16"].update(r["round_of_16"])
        counts["quarterfinal"].update(r["quarterfinalists"])
        counts["semifinal"].update(r["semifinalists"])
        counts["final"].update(r["finalists"])
        counts["champion"][r["champion"]] += 1
    return counts


def stage_table(results: list) -> pd.DataFrame:
    counts = stage_counts(results)
    n = len(results)
    rows = [{"Team": t, **{label: 100 * counts[key].get(t, 0) / n for label, key in STAGES}} for t in WM2026_TEAMS]
    return pd.DataFrame(rows).sort_values(["Weltmeister", "Final", "Halbfinal"], ascending=False)


def group_table(results: list, group_teams: list) -> pd.DataFrame:
    ranks = {t: Counter() for t in group_teams}
    for r in results:
        for g, standings in r["group_standings"].items():
            for pos, t in enumerate(standings, start=1):
                if t in ranks:
                    ranks[t][pos] += 1
    n = len(results)
    rows = [{"Team": t, **{f"Platz {p}": 100 * ranks[t].get(p, 0) / n for p in range(1, 5)}} for t in group_teams]
    return pd.DataFrame(rows).sort_values("Platz 1", ascending=False)


# Rundenbezeichnungen der K.-o.-Phase (WM 2026 mit 48 Teams)
KO_ROUNDS = [
    ("round_of_32", "Sechzehntelfinal"),
    ("round_of_16", "Achtelfinal"),
    ("quarterfinal", "Viertelfinal"),
    ("semifinal", "Halbfinal"),
    ("final", "Final"),
]


def match_line(a: str, b: str, ga: int, gb: int, winner) -> str:
    def side(team, align):
        won = team == winner
        style = f"font-weight:700;color:{INK}" if won else f"color:{MUTED}"
        parts = [flag(team, 20, 14), f"<span style='{style}'>{escape(team)}</span>"]
        if align == "right":
            parts.reverse()
        justify = "flex-end" if align == "right" else "flex-start"
        return f"<div style='display:flex;align-items:center;gap:8px;justify-content:{justify}'>{''.join(parts)}</div>"
    return (f"<div style='display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px;"
            f"padding:8px 12px;margin:4px 0;background:#fff;border:1px solid {LINE};border-radius:6px'>"
            f"{side(a, 'left')}<div class='cond' style='font-size:20px;font-weight:700;color:{INK}'>{ga} : {gb}</div>"
            f"{side(b, 'right')}</div>")


def team_journey(result: dict, groups: dict, team: str) -> list:
    """Gibt den Weg eines Teams durch ein simuliertes Turnier als HTML-Blöcke zurück."""
    blocks = []
    group = next(g for g, teams in groups.items() if team in teams)
    standings = result["group_standings"][group]
    rank = standings.index(team) + 1
    table = " &nbsp; ".join(f"<span style='white-space:nowrap'>{i}. {flag(t, 18, 12)} {escape(t)}</span>"
                            for i, t in enumerate(standings, start=1))
    blocks.append(f"<h2 class='sub'>Gruppe {group}</h2><p class='muted' style='margin-bottom:6px'>{table}</p>")
    for a, b, ga, gb in result["group_match_details"][group]:
        if team in (a, b):
            winner = a if ga > gb else (b if gb > ga else None)
            blocks.append(match_line(a, b, ga, gb, winner))
    advanced = any(team in (m[0], m[1]) for m in result["knockout_details"]["round_of_32"])
    if not advanced:
        blocks.append(f"<p class='note' style='margin-top:10px'>{escape(team)} scheidet als Gruppen-{rank}. aus.</p>")
        return blocks
    for key, label in KO_ROUNDS:
        match = next((m for m in result["knockout_details"][key] if team in (m[0], m[1])), None)
        if match is None:
            break
        a, b, ga, gb, winner = match
        blocks.append(f"<h2 class='sub' style='margin-top:16px'>{label}</h2>")
        blocks.append(match_line(a, b, ga, gb, winner))
        if winner != team:
            blocks.append(f"<p class='note' style='margin-top:10px'>{escape(team)} scheidet im {label} aus.</p>")
            return blocks
    blocks.append(f"<p class='cond' style='font-size:26px;font-weight:800;color:{GOLD};margin-top:12px'>"
                  f"{escape(team)} wird Weltmeister</p>")
    return blocks


def bracket_html(result: dict) -> str:
    """Zeichnet den K.-o.-Baum eines simulierten Turniers.

    Die Anordnung folgt der offiziellen Weiterleitung aus fifa_match_schedule.json
    (sim.KNOCKOUT_BRACKET): Match 104 (Final) <- 101 und 102, usw.
    """
    numbers = {"round_of_32": range(73, 89), "round_of_16": range(89, 97), "quarterfinal": range(97, 101),
               "semifinal": range(101, 103), "final": [104]}
    by_number = {}
    for key, nums in numbers.items():
        for n, m in zip(sorted(nums), result["knockout_details"][key]):
            by_number[n] = m
    champion = result["champion"]

    def leaves(match_no, depth):
        """Matchnummern pro Runde in Baumreihenfolge, von oben nach unten."""
        if depth == 0:
            return [[match_no]]
        left, right = sim.KNOCKOUT_BRACKET[match_no]
        sub_l, sub_r = leaves(left, depth - 1), leaves(right, depth - 1)
        return [sub_l[i] + sub_r[i] for i in range(depth)] + [[match_no]]

    left_half = leaves(sim.KNOCKOUT_BRACKET[104][0], 3)   # [R32(8), R16(4), VF(2), HF(1)]
    right_half = leaves(sim.KNOCKOUT_BRACKET[104][1], 3)

    bw, bh, pitch_y, col_x, top, left_pad = 100, 48, 64, 113, 56, 8
    y_centers = [[top + i * pitch_y + bh / 2 for i in range(8)]]
    for _ in range(3):
        prev = y_centers[-1]
        y_centers.append([(prev[2 * i] + prev[2 * i + 1]) / 2 for i in range(len(prev) // 2)])

    def x_of(col):
        return left_pad + col * col_x

    boxes, lines = [], []

    def team_row(team, goals, won):
        style = f"font-weight:700;color:{INK}" if won else "color:#A3ADB5"
        return (f"<div style='display:flex;align-items:center;gap:6px;height:21px;padding:0 7px;font-size:13px;{style}'>"
                f"{flag(team, 18, 12)}<span style='flex:1'>{code_of(team)}</span>"
                f"<span class='cond' style='font-size:15px'>{goals}</span></div>")

    def box(x, y, match_no):
        a, b, ga, gb, winner = by_number[match_no]
        gold = winner == champion
        border = f"1.5px solid {GOLD}" if gold else f"1px solid {LINE}"
        boxes.append(f"<div title='Match {match_no}' style='position:absolute;left:{x}px;top:{y - bh / 2}px;width:{bw}px;"
                     f"height:{bh}px;background:#fff;border:{border};border-radius:6px;display:flex;flex-direction:column;"
                     f"justify-content:center'>{team_row(a, ga, winner == a)}{team_row(b, gb, winner == b)}</div>")
        return gold

    def connect(x1, y1, x2, y2, gold):
        xm = (x1 + x2) / 2
        lines.append(f"<path d='M{x1},{y1} H{xm} V{y2} H{x2}' fill='none' stroke='{GOLD if gold else '#CDD5D1'}' "
                     f"stroke-width='{2 if gold else 1.2}'/>")

    for half, cols, direction in ((left_half, [0, 1, 2, 3], 1), (right_half, [8, 7, 6, 5], -1)):
        for r, match_numbers in enumerate(half):
            for i, n in enumerate(match_numbers):
                x, y = x_of(cols[r]), y_centers[r][i]
                gold = box(x, y, n)
                if r < 3:
                    nx, ny = x_of(cols[r + 1]), y_centers[r + 1][i // 2]
                    if direction == 1:
                        connect(x + bw, y, nx, ny, gold)
                    else:
                        connect(x, y, nx + bw, ny, gold)

    fx, fy = x_of(4) + (col_x - bw) / 2 - 4, y_centers[3][0]
    box(fx, fy, 104)
    for x1, x2, semi in ((x_of(3) + bw, fx, left_half[3][0]), (fx + bw, x_of(5), right_half[3][0])):
        gold = by_number[semi][4] == champion
        lines.append(f"<path d='M{x1},{fy} H{x2}' stroke='{GOLD if gold else '#CDD5D1'}' stroke-width='{2 if gold else 1.2}'/>")

    crown = (f"<div style='position:absolute;left:{fx - 30}px;top:{fy - 140}px;width:{bw + 60}px;text-align:center'>"
             f"<div class='muted' style='font-size:13px'>Weltmeister</div><div style='margin:8px 0 4px'>"
             f"{flag(champion, 52, 35, 4)}</div><div class='cond' style='font-size:28px;font-weight:800;color:{GOLD}'>"
             f"{escape(champion)}</div></div>")
    heads = ["Sechzehntelfinal", "Achtelfinal", "Viertelfinal", "Halbfinal", "Final",
             "Halbfinal", "Viertelfinal", "Achtelfinal", "Sechzehntelfinal"]
    head_html = "".join(
        f"<div style='position:absolute;left:{x_of(c)}px;top:14px;width:{bw}px;text-align:center;font-size:13px;"
        f"font-weight:{600 if c == 4 else 500};color:{INK if c == 4 else MUTED}'>{h}</div>"
        for c, h in enumerate(heads))
    width, height = x_of(8) + bw + left_pad, top + 8 * pitch_y + 8
    svg = f"<svg width='{width}' height='{height}' style='position:absolute;left:0;top:0'>{''.join(lines)}</svg>"
    return (f"<div class='panel' style='padding:10px 14px;overflow-x:auto'>"
            f"<div style='position:relative;width:{width}px;height:{height}px;margin:0 auto'>"
            f"{svg}{head_html}{''.join(boxes)}{crown}</div></div>")


# ---------------------------------------------------------------------------
# Seite aufbauen
# ---------------------------------------------------------------------------

st.set_page_config(page_title="WM 2026 Predictor", layout="wide")
inject_styles()
summary = data_summary()
cutoff = date.fromisoformat(WM2026_START_DATE).strftime("%d.%m.%Y")
html("<div class='stripe'></div><div class='brand'><span class='w'>WM 2026 Predictor</span>"
     f"<span class='s'>Prognosen aus {thousands(summary['matches'])} Länderspielen, Mini-Challenge KIP an der "
     "FHNW</span></div>")

tab_start, tab_match, tab_sim, tab_model = st.tabs(["Start", "Spielvorhersage", "Turniersimulation", "Über das Modell"])

# --- Start -------------------------------------------------------------------
with tab_start:
    html("<h1 class='title'>Wer wird Weltmeister 2026? Ein Modell schätzt jedes Spiel und das ganze Turnier.</h1>"
         f"<p class='lead'>Grundlage sind Länderspiele aller 48 Teams seit {summary['first_year']}, ihre Elo-Stärke und die offiziellen "
         "Turnierregeln. Die Werte sind Wahrscheinlichkeiten, keine Gewissheiten.</p>"
         f"<div class='kpis'><div><div class='v'>{len(WM2026_TEAMS)}</div><div class='muted'>Teams</div></div>"
         f"<div><div class='v'>{thousands(summary['matches'])}</div><div class='muted'>Länderspiele als Datenbasis</div></div>"
         f"<div><div class='v'>{summary['annex_c_variants']}</div><div class='muted'>Varianten für die Gruppendritten</div></div>"
         f"<div><div class='v'>{100 * summary['rf_accuracy']:.0f} %</div><div class='muted'>Trefferquote auf "
         "Testspielen</div></div></div>")
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        html("<h2 class='sub'>Ein Spiel vorhersagen</h2><p class='muted'>In der Registerkarte Spielvorhersage zwei "
             "Teams wählen und sehen, wie wahrscheinlich Sieg, Unentschieden und Niederlage sind.</p>")
    with c2:
        html("<h2 class='sub'>Das Turnier durchspielen</h2><p class='muted'>In der Registerkarte Turniersimulation bis "
             "zu 1000 Turniere simulieren und die Chancen jedes Teams pro Runde ablesen.</p>")
    with c3:
        html("<h2 class='sub'>So lesen Sie die Werte</h2><p class='muted'>60 % bedeutet, dass dieses Ergebnis in etwa "
             "6 von 10 vergleichbaren Spielen eintritt. Ø steht für einen Durchschnitt, in dem neuere Spiele stärker "
             "zählen.</p><p class='note' style='margin-top:12px'>Unentschieden erkennt das Modell selten. Verlängerung "
             "und Penaltyschiessen sind nicht abgebildet.</p>")

# --- Spielvorhersage ---------------------------------------------------------
with tab_match:
    team_names = sorted(WM2026_TEAMS.keys())
    s1, s2, s3 = st.columns([3, 3, 3])
    team_a = s1.selectbox("Team A", team_names, index=team_names.index("Canada"))
    team_b = s2.selectbox("Team B", team_names, index=team_names.index("Mexico"))
    with s3:
        html("<div style='height:30px'></div>")
        include_wm2026 = st.checkbox(
            "Bereits gespielte WM-Spiele einbeziehen",
            value=False,
            help=f"Standardmässig fliessen nur Spiele vor dem {cutoff} in Form und direkte Duelle ein. "
                 "So bleiben Trainings- und Vorhersagedaten sauber getrennt.",
        )

    if team_a == team_b:
        html("<p class='note'>Bitte zwei unterschiedliche Teams wählen.</p>")
    else:
        result = predict(team_a, team_b, include_wm2026)
        if result is None:
            html(f"<p class='note'>Für {escape(team_a)} oder {escape(team_b)} gibt es zu wenige Spiele für eine "
                 "Vorhersage.</p>")
        else:
            ga_r, gb_r = max(0, round(result["goals_a"])), max(0, round(result["goals_b"]))
            left, right = st.columns([1.15, 1], gap="medium")
            with left:
                html(f"""<div class='panel'>
<div style='display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:22px;flex-wrap:wrap'>
<div style='display:flex;align-items:center;gap:14px'>{flag(team_a, 64, 43, 4)}<span class='cond' style='font-size:30px;font-weight:700;color:{INK}'>{escape(team_a)}</span></div>
<div style='text-align:center'><div class='cond' style='font-size:58px;font-weight:800;line-height:1;color:{INK}'>{ga_r} : {gb_r}</div>
<div class='muted' style='font-size:13px'>erwartete Tore {result['goals_a']:.2f} zu {result['goals_b']:.2f}</div></div>
<div style='display:flex;align-items:center;gap:14px'><span class='cond' style='font-size:30px;font-weight:700;color:{INK}'>{escape(team_b)}</span>{flag(team_b, 64, 43, 4)}</div></div>
{probability_block(team_a, team_b, result['proba'])}
<p class='muted' style='font-size:13.5px;margin-top:16px'>Das Modell trifft auf Testspielen etwa jedes zweite Ergebnis. Unentschieden werden oft unterschätzt.</p></div>""")
                for m in actual_wm2026_results(team_a, team_b):
                    html(f"<p class='note' style='margin-top:14px'>Tatsächliches Resultat an der WM 2026 am {m['date']}: "
                         f"{escape(team_a)} {m['goals_for']} : {m['goals_against']} {escape(team_b)}</p>")
            with right:
                html(f"<div class='panel'><h2 class='sub'>Im Vergleich</h2>{comparison_table(team_a, team_b, result)}"
                     "<p class='muted' style='font-size:13px;margin-top:10px'>Grün ist jeweils der bessere Wert. "
                     "Ø ist ein gewichteter Durchschnitt, neuere Spiele zählen stärker.</p></div>")
                if result["h2h_matches"]:
                    with st.expander(f"Alle {len(result['h2h_matches'])} direkten Duelle anzeigen"):
                        for m in result["h2h_matches"]:
                            html(f"<div style='font-size:14px'>{m['date']} &nbsp; {escape(team_a)} "
                                 f"<b>{m['goals_for']} : {m['goals_against']}</b> {escape(team_b)}</div>")

# --- Turniersimulation -------------------------------------------------------
with tab_sim:
    n_sim = st.session_state.get("sim_n")
    results_all = st.session_state.get("sim_results")
    if results_all:
        table = stage_table(results_all)
        leader = table.iloc[0]
        html(f"<h1 class='title' style='font-size:38px'>{escape(leader['Team'])} gewinnt den Titel in "
             f"{leader['Weltmeister']:.0f} % der Turniere</h1><p class='lead'>Ergebnis aus {n_sim} simulierten "
             "Turnieren. Jedes Spiel wird gemäss den Modellwahrscheinlichkeiten ausgelost.</p>")
    else:
        html("<h1 class='title' style='font-size:38px'>Das ganze Turnier simulieren</h1><p class='lead'>Jedes Spiel "
             "wird gemäss den Modellwahrscheinlichkeiten ausgelost. Aus vielen Durchläufen entstehen die Chancen pro "
             "Runde.</p>")

    c_view, c_n, c_go = st.columns([5, 2, 1.3])
    with c_view:
        view = st.radio("Ansicht", ["Chancen pro Runde", "Gruppen", "Turnierbaum", "Team verfolgen"],
                        horizontal=True, label_visibility="collapsed")
    n_choice = c_n.select_slider("Anzahl Turniere", options=[50, 100, 250, 500, 1000], value=500)
    with c_go:
        html("<div style='height:28px'></div>")
        run_clicked = st.button("Simulieren", type="primary", use_container_width=True)
    if run_clicked:
        with st.spinner(f"{n_choice} Turniere werden simuliert ..."):
            st.session_state["sim_results"], st.session_state["sim_groups"] = simulate_many(n_choice)
            st.session_state["sim_n"] = n_choice
        st.rerun()

    if view == "Turnierbaum":
        seed = st.session_state.get("bracket_seed", 42)
        single, groups_single = simulate_many(1, seed)
        b1, b2 = st.columns([5, 1.3])
        b1.markdown(f"<p class='muted'>Beispielturnier Nr. {seed - 41}. Gleiche Nummer ergibt "
                    "denselben Turnierbaum. Der goldene Weg führt zum Weltmeister. Die Spielstände sind illustrativ, "
                    "der Sieger wird über die Modellwahrscheinlichkeiten bestimmt.</p>", unsafe_allow_html=True)
        if b2.button("Anderes Turnier ziehen", use_container_width=True):
            st.session_state["bracket_seed"] = seed + 1
            st.rerun()
        html(bracket_html(single[0]))

    elif view == "Team verfolgen":
        team_names = sorted(WM2026_TEAMS.keys())
        tracked = st.columns([1, 2])[0].selectbox("Team", team_names, index=team_names.index("Switzerland"))
        seed = st.session_state.get("bracket_seed", 42)
        single, groups_single = simulate_many(1, seed)
        if st.button("Anderes Turnier ziehen", key="journey_reroll"):
            st.session_state["bracket_seed"] = seed + 1
            st.rerun()
        t1, t2 = st.columns([1, 1.2], gap="large")
        with t1:
            html(f"<h2 class='sub'>Verlauf im Beispielturnier Nr. {seed - 41}</h2>")
            html("".join(team_journey(single[0], groups_single, tracked)))
        with t2:
            if results_all:
                counts = stage_counts(results_all)
                rows = "".join(
                    f"<tr><td>{label}</td>{bar_cell(100 * counts[key].get(tracked, 0) / n_sim, key == 'champion')}</tr>"
                    for label, key in STAGES)
                html(f"<div class='panel'><h2 class='sub'>Chancen von {escape(tracked)} in {n_sim} Turnieren</h2>"
                     f"<table class='t'>{rows}</table></div>")
            else:
                html("<p class='muted'>Für die Chancen pro Runde zuerst oben auf Simulieren klicken.</p>")

    elif not results_all:
        html("<p class='muted'>Anzahl Turniere wählen und auf Simulieren klicken.</p>")

    elif view == "Chancen pro Runde":
        top = table.head(10)
        head = "".join(f"<th>{label}</th>" for label, _ in STAGES)
        body = "".join(
            f"<tr><td><span style='display:inline-flex;align-items:center;gap:10px;font-weight:600'>{flag(r['Team'])}"
            f"{escape(r['Team'])}</span></td>" + "".join(bar_cell(r[label], label == "Weltmeister") for label, _ in STAGES)
            + "</tr>" for _, r in top.iterrows())
        html(f"<div class='panel'><table class='t'><tr><th>Team</th>{head}</tr>{body}</table>"
             f"<p class='muted' style='font-size:13px;margin-top:10px'>Top 10 nach Titelchance. Die Datei unten enthält "
             "alle 48 Teams.</p></div>")
        st.download_button("Als CSV speichern", table.round(1).to_csv(index=False).encode("utf-8"),
                           file_name=f"wm2026_simulation_{n_sim}.csv", mime="text/csv")

    elif view == "Gruppen":
        groups_data = st.session_state["sim_groups"]
        letter = st.columns([1, 4])[0].selectbox("Gruppe", sorted(groups_data.keys()))
        gt = group_table(results_all, groups_data[letter])
        body = "".join(
            f"<tr><td><span style='display:inline-flex;align-items:center;gap:10px;font-weight:600'>{flag(r['Team'])}"
            f"{escape(r['Team'])}</span></td>" + "".join(bar_cell(r[f"Platz {p}"]) for p in range(1, 5)) + "</tr>"
            for _, r in gt.iterrows())
        html(f"<div class='panel'><table class='t'><tr><th>Team</th><th>Platz 1</th><th>Platz 2</th><th>Platz 3</th>"
             f"<th>Platz 4</th></tr>{body}</table><p class='muted' style='font-size:13px;margin-top:10px'>"
             f"Wahrscheinlichkeit jeder Endplatzierung in Gruppe {letter}.</p></div>")
        st.download_button("Als CSV speichern", gt.round(1).to_csv(index=False).encode("utf-8"),
                           file_name=f"wm2026_gruppe_{letter}_{n_sim}.csv", mime="text/csv")

# --- Über das Modell ---------------------------------------------------------
with tab_model:
    rf_acc = summary["rf_accuracy"]
    html("<h1 class='title' style='font-size:38px'>Woher die Zahlen kommen</h1><p class='lead'>Die Kennzahlen stammen "
         "aus dem Notebook im Repository und beziehen sich auf 229 Testspiele ab Oktober 2024.</p>")
    m1, m2 = st.columns(2, gap="large")
    with m1:
        html(f"<h2 class='sub'>Daten</h2><p>{thousands(summary['matches'])} Länderspiele mit Spielstatistiken von "
             f"API-Football, {summary['first_year']} bis {summary['last_date']}. Teamstärke als Elo-Wert von eloratings.net. "
             f"Turnierregeln aus dem FIFA-Reglement, Annex C mit {summary['annex_c_variants']} Varianten für die "
             "Gruppendritten.</p>"
             "<h2 class='sub' style='margin-top:24px'>Modelle</h2><p>Ein Random Forest schätzt Sieg, Unentschieden "
             "und Niederlage, ein zweiter die erwarteten Tore. Trainiert wurde auf älteren Spielen, getestet auf den "
             "jüngsten 20 Prozent.</p>")
    with m2:
        acc = f"{100 * rf_acc:.1f} %" if rf_acc is not None else "–"
        html(f"<h2 class='sub'>Wie gut es funktioniert</h2><table class='t'><tr><th>Was</th><th>Modell</th>"
             f"<th>Einfache Vergleichsregel</th></tr><tr><td>Richtiger Ausgang</td><td><b>{acc}</b></td><td>35.4 %</td></tr>"
             "<tr><td>Abweichung Tore Team A</td><td><b>0.86</b></td><td>0.90</td></tr>"
             "<tr><td>Abweichung Tore Team B</td><td><b>1.01</b></td><td>1.08</td></tr></table>"
             "<p class='muted' style='font-size:13px;margin-top:8px'>Die Vergleichsregel sagt immer den häufigsten "
             "Ausgang beziehungsweise die durchschnittliche Toranzahl voraus.</p>"
             "<h2 class='sub' style='margin-top:24px'>Was es nicht kann</h2><p class='note'>Unentschieden werden nur in "
             "17 % der Fälle erkannt. Verlängerung, Penaltyschiessen und Fairplay-Wertung fehlen. Form und Stärke bleiben "
             "während eines simulierten Turniers gleich.</p>")
