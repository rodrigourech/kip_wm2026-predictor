"""
WM 2026 Match Predictor - Streamlit-Dashboard.

Zwei Teams auswaehlen -> Sieg-Wahrscheinlichkeit (Klassifikator) + erwartetes
Ergebnis (Tore-Regressor) + Feature-Importance-Chart. WM-2026-Toggle steuert,
ob bereits gespielte WM-2026-Partien in die Formkurve/H2H-Berechnung
einfliessen.

Aufruf:
    streamlit run app/dashboard.py
"""
import json
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
import altair as alt
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
TODAY = date.today().isoformat()

# FIFA-Teamname -> ISO-3166-1-Alpha-2-Code (bzw. flagcdn-Sondercode für England/Schottland)
# für die Flaggen-Anzeige via flagcdn.com
TEAM_FLAG_CODES = {
    "Canada": "ca", "Mexico": "mx", "USA": "us", "Australia": "au", "Iraq": "iq",
    "IR Iran": "ir", "Japan": "jp", "Jordan": "jo", "Korea Republic": "kr", "Qatar": "qa",
    "Saudi Arabia": "sa", "Uzbekistan": "uz", "Algeria": "dz", "Cabo Verde": "cv",
    "Congo DR": "cd", "Côte d'Ivoire": "ci", "Egypt": "eg", "Ghana": "gh", "Morocco": "ma",
    "Senegal": "sn", "South Africa": "za", "Tunisia": "tn", "Curaçao": "cw", "Haiti": "ht",
    "Panama": "pa", "Argentina": "ar", "Brazil": "br", "Colombia": "co", "Ecuador": "ec",
    "Paraguay": "py", "Uruguay": "uy", "New Zealand": "nz", "Austria": "at", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Croatia": "hr", "Czechia": "cz", "England": "gb-eng",
    "France": "fr", "Germany": "de", "Netherlands": "nl", "Norway": "no", "Portugal": "pt",
    "Scotland": "gb-sct", "Spain": "es", "Sweden": "se", "Switzerland": "ch", "Türkiye": "tr",
}


def flag_url(team_name: str, width: int = 320) -> str:
    code = TEAM_FLAG_CODES.get(team_name)
    return f"https://flagcdn.com/w{width}/{code}.png" if code else ""


def render_h2h(team_a: str, team_b: str, row: dict, h2h_matches: list):
    h2h_games = row.get("h2h_games", 0)
    st.markdown("**Head-to-Head**" + (f" (letzte {h2h_games} direkte Duelle)" if h2h_games else ""))
    if h2h_games:
        h2h_df = pd.DataFrame({
            "Ergebnis": [wrap_label(team_a), "Unentschieden", wrap_label(team_b)],
            "Anzahl": [row.get("h2h_a_wins", 0), row.get("h2h_a_draws", 0), row.get("h2h_a_losses", 0)],
        })
        h2h_chart = alt.Chart(h2h_df).mark_bar(color="#4C72B0").encode(
            x=alt.X("Ergebnis:N", sort=None, axis=alt.Axis(labelAngle=0, labelLimit=200, title=None)),
            y=alt.Y("Anzahl:Q", title="Anzahl Siege", axis=alt.Axis(tickMinStep=1)),
        )
        st.altair_chart(h2h_chart, use_container_width=True)

        with st.expander(f"Alle {h2h_games} direkten Duelle im Detail anzeigen"):
            for m in h2h_matches:
                result_icon = "\U0001f7e2" if m["points"] == 3 else ("\U0001f7e0" if m["points"] == 1 else "\U0001f534")
                st.markdown(f"{result_icon} **{m['date']}**: {team_a} {m['goals_for']} : {m['goals_against']} {team_b}")
    else:
        st.caption("Keine bisherigen direkten Duelle in den Daten gefunden.")


def wrap_label(text: str, max_len: int = 10) -> str:
    """Bricht lange Achsenbeschriftungen auf 2 Zeilen um (an Wortgrenze, falls
    vorhanden, sonst in der Mitte des Wortes)."""
    if len(text) <= max_len:
        return text
    if " " not in text:
        mid = len(text) // 2
        return text[:mid] + "\n" + text[mid:]
    words = text.split(" ")
    mid = len(text) // 2
    best_split, best_diff = 1, float("inf")
    running = 0
    for i, w in enumerate(words[:-1]):
        running += len(w) + 1
        diff = abs(running - mid)
        if diff < best_diff:
            best_diff, best_split = diff, i + 1
    return " ".join(words[:best_split]) + "\n" + " ".join(words[best_split:])


def get_last_n_results(history, before_date: str, n: int = 5):
    """Gibt die letzten n Spiele (komplette Spieldaten, nicht nur Punkte) vor
    before_date zurück, chronologisch (älteste zuerst)."""
    return [g for g in history if g["date"] < before_date][-n:]


def form_tiles(games: list) -> str:
    """Baut kleine farbige Kacheln (grün=Sieg, orange=Unentschieden, rot=Niederlage)
    mit Hover-Tooltip (Gegner, Resultat, Datum)."""
    color_map = {3: "#2ECC71", 1: "#F39C12", 0: "#E74C3C"}
    letter_map = {3: "S", 1: "U", 0: "N"}
    tiles = []
    for g in games:
        p = g["points"]
        opponent = g.get("opponent_name") or g.get("opponent_fifa_name") or "Unbekannt"
        tooltip = f"{g['date']}: {g['goals_for']}:{g['goals_against']} vs. {opponent}"
        tiles.append(
            f"<span title='{tooltip}' style='display:inline-block; width:24px; height:24px; "
            f"line-height:24px; background:{color_map[p]}; color:white; text-align:center; "
            f"border-radius:4px; margin:0 2px; font-size:0.8rem; font-weight:700; cursor:default;'>"
            f"{letter_map[p]}</span>"
        )
    return "".join(tiles)

st.set_page_config(page_title="WM 2026 Match Predictor", page_icon="\u26bd", layout="centered")


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


@st.cache_data
def get_team_history(fifa_name: str, include_wm2026: bool):
    team_id_cache, id_to_fifa_name, _ = load_reference_data()
    own_id = team_id_cache[fifa_name]
    return build_team_match_history(fifa_name, own_id, id_to_fifa_name, include_wm2026=include_wm2026)


def find_actual_wm2026_results(team_a: str, team_b: str):
    """Prüft, ob Team A und Team B während der WM 2026 (nach WM2026_START_DATE)
    tatsächlich gegeneinander gespielt haben, und gibt die echten Resultate
    zurück (kann leer sein, oder theoretisch >1 Eintrag bei zwei Duellen,
    z.B. Gruppenphase + spätere K.o.-Runde)."""
    hist_a_full = get_team_history(team_a, include_wm2026=True)
    matches = [
        g for g in hist_a_full
        if g["opponent_fifa_name"] == team_b and g["date"] >= WM2026_START_DATE
    ]
    return sorted(matches, key=lambda g: g["date"])


def build_matchup_row(team_a: str, team_b: str, include_wm2026: bool, as_of_date: str = TODAY):
    _, _, ranking_by_year = load_reference_data()

    hist_a = get_team_history(team_a, include_wm2026)
    hist_b = get_team_history(team_b, include_wm2026)

    feat_a = compute_rolling_features(hist_a, as_of_date)
    feat_b = compute_rolling_features(hist_b, as_of_date)
    if feat_a is None or feat_b is None:
        return None

    h2h = compute_h2h(hist_a, team_b, as_of_date)
    year = int(as_of_date[:4])
    ranking_a = get_ranking(ranking_by_year, team_a, year)
    ranking_b = get_ranking(ranking_by_year, team_b, year)

    row = {"a_is_home": True}
    row.update({f"a_{k}": v for k, v in feat_a.items()})
    row.update({f"b_{k}": v for k, v in feat_b.items()})
    row.update(h2h)
    row["ranking_a"] = ranking_a
    row["ranking_b"] = ranking_b
    row["ranking_diff"] = (ranking_a - ranking_b) if (ranking_a is not None and ranking_b is not None) else None
    return row


def predict(team_a: str, team_b: str, include_wm2026: bool):
    (clf_model, clf_imputer, clf_feature_cols,
     goals_model, goals_imputer, goals_feature_cols) = load_models()

    row = build_matchup_row(team_a, team_b, include_wm2026)
    if row is None:
        return None

    hist_a = get_team_history(team_a, include_wm2026)
    hist_b = get_team_history(team_b, include_wm2026)
    form_a = get_last_n_results(hist_a, TODAY)
    form_b = get_last_n_results(hist_b, TODAY)

    X_clf = pd.DataFrame([row])[clf_feature_cols]
    proba = clf_model.predict_proba(clf_imputer.transform(X_clf))[0]
    proba_dict = dict(zip(clf_model.classes_, proba))

    X_goals = pd.DataFrame([row])[goals_feature_cols]
    goals_pred = goals_model.predict(goals_imputer.transform(X_goals))[0]

    h2h_matches = get_h2h_matches(hist_a, team_b, TODAY)

    return {
        "proba": proba_dict,
        "goals_a": goals_pred[0],
        "goals_b": goals_pred[1],
        "clf_model": clf_model,
        "clf_feature_cols": clf_feature_cols,
        "row": row,
        "form_a": form_a,
        "form_b": form_b,
        "h2h_matches": h2h_matches,
    }


st.title("\u26bd WM 2026 Match Predictor")
st.caption("Sieg-Wahrscheinlichkeit und erwartetes Ergebnis auf Basis historischer Laenderspieldaten "
           "(2015\u20132026), Formkurve, Head-to-Head-Bilanz und Ranking (bis vor der WM 2026).")

mode = st.radio(
    "Ansicht",
    ["Team-Vorhersage", "Turnier-Simulation"],
    horizontal=True,
    label_visibility="collapsed",
)
st.divider()

if mode == "Team-Vorhersage":
    team_names = sorted(WM2026_TEAMS.keys())

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", team_names, index=team_names.index("Canada") if "Canada" in team_names else 0)
    with col2:
        default_b_index = team_names.index("Mexico") if "Mexico" in team_names else 1
        team_b = st.selectbox("Team B", team_names, index=default_b_index)

    # Grosse Flaggen-Anzeige zur Team-Auswahl
    flag_col1, flag_col_vs, flag_col2 = st.columns([5, 1, 5])
    with flag_col1:
        st.image(flag_url(team_a), use_column_width=True)
        st.markdown(f"<h3 style='text-align: center;'>{team_a}</h3>", unsafe_allow_html=True)
    with flag_col_vs:
        st.markdown("<h2 style='text-align: center; margin-top: 60px;'>vs</h2>", unsafe_allow_html=True)
    with flag_col2:
        st.image(flag_url(team_b), use_column_width=True)
        st.markdown(f"<h3 style='text-align: center;'>{team_b}</h3>", unsafe_allow_html=True)

    include_wm2026 = st.checkbox(
        "WM-2026-Spiele einbeziehen (nach 19.06.2026)",
        value=False,
        help="Standardmaessig werden bereits gespielte WM-2026-Partien nicht in die Formkurve "
             "einbezogen, um Trainings- und Vorhersagedaten sauber zu trennen. Aktivieren, um "
             "sie testweise einzubeziehen.",
    )

    if team_a == team_b:
        st.warning("Bitte zwei unterschiedliche Teams auswaehlen.")
        st.stop()

    if st.button("Vorhersage berechnen", type="primary"):
        with st.spinner("Berechne Formkurve, Head-to-Head und Ranking..."):
            result = predict(team_a, team_b, include_wm2026)

        if result is None:
            st.error(f"Zu wenig Spielhistorie fuer {team_a} oder {team_b} vorhanden - keine Vorhersage moeglich.")
            st.stop()

        st.divider()

        st.subheader("Vorhersage")

        goals_a_rounded = max(0, round(result["goals_a"]))
        goals_b_rounded = max(0, round(result["goals_b"]))

        if goals_a_rounded > goals_b_rounded:
            color_a, color_b = "#2ECC71", "#E74C3C"  # Team A gewinnt: grün / rot
        elif goals_b_rounded > goals_a_rounded:
            color_a, color_b = "#E74C3C", "#2ECC71"  # Team B gewinnt: rot / grün
        else:
            color_a, color_b = "#F39C12", "#F39C12"  # Unentschieden: beide orange

        st.markdown(
            f"<h1 style='text-align: center; font-size: 3rem;'>"
            f"<span style='color:{color_a};'>{team_a} {goals_a_rounded}</span>"
            f" : "
            f"<span style='color:{color_b};'>{goals_b_rounded} {team_b}</span>"
            f"</h1>",
            unsafe_allow_html=True,
        )
        st.caption(f"Nicht gerundete Vorhersage: {result['goals_a']:.2f} : {result['goals_b']:.2f}")

        actual_matches = find_actual_wm2026_results(team_a, team_b)
        if actual_matches:
            for m in actual_matches:
                st.info(
                    f"\u2705 **Tatsächliches Ergebnis (WM 2026, {m['date']}):** "
                    f"{team_a} {m['goals_for']} : {m['goals_against']} {team_b}"
                )

        row = result["row"]

        st.markdown("##### Sieg-Wahrscheinlichkeit")
        proba = result["proba"]
        label_map = {"A": team_a, "Draw": "Unentschieden", "B": team_b}

        proba_df = pd.DataFrame({
            "Ergebnis": [wrap_label(label_map[k]) for k in ["A", "Draw", "B"]],
            "Wahrscheinlichkeit": [proba.get("A", 0) * 100, proba.get("Draw", 0) * 100, proba.get("B", 0) * 100],
            "Farbe": [color_a, "#F39C12", color_b],
        })

        cols = st.columns(3)
        for c, outcome in zip(cols, ["A", "Draw", "B"]):
            c.metric(label_map[outcome], f"{proba.get(outcome, 0) * 100:.1f}%")

        chart = alt.Chart(proba_df).mark_bar().encode(
            x=alt.X("Ergebnis:N", sort=None, axis=alt.Axis(labelAngle=0, labelLimit=200, title=None)),
            y=alt.Y("Wahrscheinlichkeit:Q", title="Wahrscheinlichkeit (%)"),
            color=alt.Color("Farbe:N", scale=None, legend=None),
        )
        st.altair_chart(chart, use_container_width=True)

        st.markdown("##### Team-Vergleich")

        header_c1, header_c2, header_c3 = st.columns([2, 3, 2])
        header_c1.markdown(f"<div style='text-align:right; font-weight:700;'>{team_a}</div>", unsafe_allow_html=True)
        header_c2.markdown("", unsafe_allow_html=True)
        header_c3.markdown(f"<div style='text-align:left; font-weight:700;'>{team_b}</div>", unsafe_allow_html=True)

        def fmt(v, decimals=1, suffix=""):
            return "\u2013" if v is None else f"{v:.{decimals}f}{suffix}"

        ranking_label = (
            "<a href='https://www.eloratings.net' target='_blank' "
            "title='Elo-Rating: Bewertungssystem für Teamstärke (urspr. aus dem Schach). "
            "Wird nach jedem Spiel basierend auf Ergebnis und Gegnerstärke angepasst.' "
            "style='color:#999; text-decoration:underline;'>Elo Ranking</a>"
        )
        stat_rows = [
            (ranking_label, row.get("ranking_a"), row.get("ranking_b"), 0, ""),
            ("\u00d8 Tore/Spiel", row.get("a_goals_for_avg"), row.get("b_goals_for_avg"), 2, ""),
            ("\u00d8 Gegentore/Spiel", row.get("a_goals_against_avg"), row.get("b_goals_against_avg"), 2, ""),
            ("\u00d8 Ballbesitz", row.get("a_possession_avg"), row.get("b_possession_avg"), 1, "%"),
            ("\u00d8 Sch\u00fcsse/Spiel", row.get("a_shots_total_avg"), row.get("b_shots_total_avg"), 1, ""),
            ("\u00d8 Sch\u00fcsse aufs Tor", row.get("a_shots_on_goal_avg"), row.get("b_shots_on_goal_avg"), 1, ""),
            ("\u00d8 Ecken/Spiel", row.get("a_corners_avg"), row.get("b_corners_avg"), 1, ""),
        ]

        # Form als farbige Kacheln (grün=Sieg, orange=Unentschieden, rot=Niederlage)
        fc1, fc2, fc3 = st.columns([2, 3, 2])
        fc1.markdown(f"<div style='text-align:right;'>{form_tiles(result['form_a'])}</div>", unsafe_allow_html=True)
        fc2.markdown("<div style='text-align:center; color:#999; font-size:0.85rem; padding-top:4px;'>Form (letzte 5 Spiele)</div>", unsafe_allow_html=True)
        fc3.markdown(f"<div style='text-align:left;'>{form_tiles(result['form_b'])}</div>", unsafe_allow_html=True)

        for label, val_a, val_b, decimals, suffix in stat_rows:
            c1, c2, c3 = st.columns([2, 3, 2])
            style_a = "font-weight:700; color:#2ECC71;" if (val_a is not None and val_b is not None and val_a > val_b) else ""
            style_b = "font-weight:700; color:#2ECC71;" if (val_a is not None and val_b is not None and val_b > val_a) else ""
            c1.markdown(f"<div style='text-align:right; font-size:1.1rem; {style_a}'>{fmt(val_a, decimals, suffix)}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align:center; color:#999; font-size:0.85rem; padding-top:4px;'>{label}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:left; font-size:1.1rem; {style_b}'>{fmt(val_b, decimals, suffix)}</div>", unsafe_allow_html=True)

        render_h2h(team_a, team_b, row, result["h2h_matches"])

        st.markdown(
            "<div style='background-color:rgba(28,131,225,0.1); border-radius:8px; "
            "padding:10px 14px; font-size:0.8rem; line-height:1.5; margin-top:24px;'>"
            "<b>Hinweis</b><br>"
            "\u00d8 bedeutet gewichteter Durchschnitt über die gesamte Spielhistorie<br>"
            "neuere Spiele zählen mehr, ältere klingen graduell ab (keine feste Anzahl Spiele)."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Zwei Teams auswaehlen und auf **Vorhersage berechnen** klicken.")

elif mode == "Turnier-Simulation":
    st.subheader("Monte-Carlo-Turniersimulation")
    st.caption(
        "Simuliert das komplette Turnier (Gruppenphase bis Finale) mehrfach - bei jedem "
        "Durchlauf werden die Spiele zufällig gemäss den Modell-Wahrscheinlichkeiten "
        "ausgewürfelt, nicht deterministisch der Favorit gewinnen lassen. Achtelfinal-"
        "Zuordnung der Drittplatzierten folgt der offiziellen FIFA-Regel (Annex C)."
    )

    sim_view = st.radio(
        "Simulationsansicht",
        ["Top-Teams gesamt", "Team im Detail verfolgen"],
        horizontal=True,
    )
    st.divider()

    if sim_view == "Top-Teams gesamt":
        n_sim = st.slider("Anzahl Simulationen", min_value=10, max_value=1000, value=100, step=10)

        @st.cache_data(show_spinner=False)
        def run_tournament_simulations(n_simulations: int):
            team_id_cache, id_to_fifa_name, ranking_by_year = load_reference_data()
            models = load_models()
            histories, static_feat = sim.precompute_team_features(team_id_cache, id_to_fifa_name, ranking_by_year)
            groups = sim.load_groups()
            annex_c_by_combo = sim.load_annex_c()
            match_cache = {}
            rng = random.Random(42)

            counters = {
                "champion": Counter(), "final": Counter(), "semifinal": Counter(),
                "quarterfinal": Counter(), "round_of_16": Counter(), "group_advanced": Counter(),
            }
            # Pro Team, wie oft es in seiner Gruppe auf Platz 1/2/3/4 gelandet ist
            group_rank_counts = {t: Counter() for t in WM2026_TEAMS}

            for _ in range(n_simulations):
                result = sim.simulate_tournament(groups, annex_c_by_combo, match_cache, models, histories, static_feat, rng)
                counters["champion"][result["champion"]] += 1
                for t in result["finalists"]:
                    counters["final"][t] += 1
                for t in result["semifinalists"]:
                    counters["semifinal"][t] += 1
                for t in result["quarterfinalists"]:
                    counters["quarterfinal"][t] += 1
                for t in result["round_of_16"]:
                    counters["round_of_16"][t] += 1

                advanced = set()
                for m in result["knockout_details"]["round_of_32"]:
                    advanced.add(m[0])
                    advanced.add(m[1])
                for t in advanced:
                    counters["group_advanced"][t] += 1

                for g, standings in result["group_standings"].items():
                    for pos, t in enumerate(standings, start=1):
                        group_rank_counts[t][pos] += 1

            return counters, group_rank_counts, static_feat, groups

        if st.button("Simulation starten", type="primary"):
            with st.spinner(f"Simuliere {n_sim} Turniere... (kann je nach Anzahl einen Moment dauern)"):
                counters, group_rank_counts, static_feat, groups_data = run_tournament_simulations(n_sim)
                st.session_state["sim_counters"] = counters
                st.session_state["sim_group_ranks"] = group_rank_counts
                st.session_state["sim_static_feat"] = static_feat
                st.session_state["sim_groups"] = groups_data
                st.session_state["sim_n"] = n_sim

        if "sim_counters" in st.session_state:
            counters = st.session_state["sim_counters"]
            group_rank_counts = st.session_state["sim_group_ranks"]
            static_feat = st.session_state["sim_static_feat"]
            groups_data = st.session_state["sim_groups"]
            n_done = st.session_state["sim_n"]

            # -----------------------------------------------------------------
            # 1. Gesamtübersicht: Top 15, alle Phasen nebeneinander
            # -----------------------------------------------------------------
            st.markdown("##### \U0001f3c6 Gesamtübersicht")

            all_teams = list(WM2026_TEAMS.keys())
            overview_rows = []
            for t in all_teams:
                overview_rows.append({
                    "Flagge": flag_url(t),
                    "Team": t,
                    "Gruppenphase überstanden": 100 * counters["group_advanced"].get(t, 0) / n_done,
                    "Achtelfinale": 100 * counters["round_of_16"].get(t, 0) / n_done,
                    "Viertelfinale": 100 * counters["quarterfinal"].get(t, 0) / n_done,
                    "Halbfinale": 100 * counters["semifinal"].get(t, 0) / n_done,
                    "Finale": 100 * counters["final"].get(t, 0) / n_done,
                    "Weltmeister": 100 * counters["champion"].get(t, 0) / n_done,
                })
            overview_df = pd.DataFrame(overview_rows).sort_values("Weltmeister", ascending=False).head(10)

            st.dataframe(
                overview_df,
                hide_index=True,
                use_container_width=True,
                height=386,  # exakt 10 Zeilen + Header, kein vertikales Scrollen
                column_config={
                    "Flagge": st.column_config.ImageColumn("", width="small"),
                    "Team": st.column_config.TextColumn("Team", width="small"),
                    "Gruppenphase überstanden": st.column_config.ProgressColumn("Gruppe", format="%.0f%%", min_value=0, max_value=100, width="small"),
                    "Achtelfinale": st.column_config.ProgressColumn("AF", format="%.0f%%", min_value=0, max_value=100, width="small"),
                    "Viertelfinale": st.column_config.ProgressColumn("VF", format="%.0f%%", min_value=0, max_value=100, width="small"),
                    "Halbfinale": st.column_config.ProgressColumn("HF", format="%.0f%%", min_value=0, max_value=100, width="small"),
                    "Finale": st.column_config.ProgressColumn("Finale", format="%.0f%%", min_value=0, max_value=100, width="small"),
                    "Weltmeister": st.column_config.ProgressColumn("WM", format="%.0f%%", min_value=0, max_value=100, width="small"),
                },
            )
            st.caption(f"Top 10 nach Weltmeister-Wahrscheinlichkeit, basierend auf {n_done} simulierten Turnieren.")

            # -----------------------------------------------------------------
            # 2. Überraschungen: Simulation vs. Elo-Ranking-Erwartung
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("##### \U0001f52e Überraschungen: Simulation vs. Elo-Ranking")
            st.caption(
                "Vergleicht, wie weit ein Team in der Simulation kommt, mit dem, was sein Elo-Ranking "
                "erwarten liesse. Positiver Wert = performt besser als das Ranking vermuten lässt."
            )

            sim_score = {
                t: (
                    counters["group_advanced"].get(t, 0)
                    + counters["round_of_16"].get(t, 0)
                    + counters["quarterfinal"].get(t, 0)
                    + counters["semifinal"].get(t, 0)
                    + counters["final"].get(t, 0)
                    + counters["champion"].get(t, 0)
                )
                for t in all_teams
            }
            elo_ranked = sorted(all_teams, key=lambda t: -(static_feat.get(t, {}).get("ranking") or 0))
            sim_ranked = sorted(all_teams, key=lambda t: -sim_score[t])
            elo_rank = {t: i + 1 for i, t in enumerate(elo_ranked)}
            sim_rank = {t: i + 1 for i, t in enumerate(sim_ranked)}

            surprise_rows = [
                {"Flagge": flag_url(t), "Team": t, "Elo-Rang": elo_rank[t], "Sim-Rang": sim_rank[t],
                 "Differenz": elo_rank[t] - sim_rank[t]}
                for t in all_teams
            ]
            surprise_df = pd.DataFrame(surprise_rows)

            col_over, col_under = st.columns(2)
            with col_over:
                st.markdown("**Übertrifft Erwartungen**")
                st.dataframe(
                    surprise_df.sort_values("Differenz", ascending=False).head(5)[["Flagge", "Team", "Elo-Rang", "Sim-Rang", "Differenz"]],
                    hide_index=True, use_container_width=True,
                    column_config={"Flagge": st.column_config.ImageColumn("", width="small")},
                )
            with col_under:
                st.markdown("**Bleibt hinter Erwartungen zurück**")
                st.dataframe(
                    surprise_df.sort_values("Differenz", ascending=True).head(5)[["Flagge", "Team", "Elo-Rang", "Sim-Rang", "Differenz"]],
                    hide_index=True, use_container_width=True,
                    column_config={"Flagge": st.column_config.ImageColumn("", width="small")},
                )

            # -----------------------------------------------------------------
            # 3. Gruppen-Ansicht
            # -----------------------------------------------------------------
            st.divider()
            st.markdown("##### \U0001f465 Gruppen-Ansicht")

            group_letter = st.selectbox("Gruppe wählen", sorted(groups_data.keys()))
            group_teams = groups_data[group_letter]

            group_rows = []
            for t in group_teams:
                ranks = group_rank_counts[t]
                group_rows.append({
                    "Flagge": flag_url(t),
                    "Team": t,
                    "Platz 1": 100 * ranks.get(1, 0) / n_done,
                    "Platz 2": 100 * ranks.get(2, 0) / n_done,
                    "Platz 3": 100 * ranks.get(3, 0) / n_done,
                    "Platz 4": 100 * ranks.get(4, 0) / n_done,
                })
            group_df = pd.DataFrame(group_rows).sort_values("Platz 1", ascending=False)

            st.dataframe(
                group_df, hide_index=True, use_container_width=True,
                column_config={
                    "Flagge": st.column_config.ImageColumn("", width="small"),
                    "Platz 1": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Platz 2": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Platz 3": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Platz 4": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                },
            )
            st.caption(f"Wahrscheinlichkeit pro Endplatzierung innerhalb der Gruppe {group_letter}.")
        else:
            st.info("Anzahl Simulationen wählen und auf **Simulation starten** klicken.")

    else:  # "Team im Detail verfolgen"
        team_names = sorted(WM2026_TEAMS.keys())
        tracked_team = st.selectbox("Team auswählen", team_names)
        n_sim_team = st.number_input("Anzahl Simulationen", min_value=1, max_value=1000, value=1, step=1)

        @st.cache_data(show_spinner=False)
        def run_tournament_simulations_detailed(n_simulations: int, _seed: int = 42):
            team_id_cache, id_to_fifa_name, ranking_by_year = load_reference_data()
            models = load_models()
            histories, static_feat = sim.precompute_team_features(team_id_cache, id_to_fifa_name, ranking_by_year)
            groups = sim.load_groups()
            annex_c_by_combo = sim.load_annex_c()
            match_cache = {}
            rng = random.Random(_seed)
            results = [
                sim.simulate_tournament(groups, annex_c_by_combo, match_cache, models, histories, static_feat, rng)
                for _ in range(n_simulations)
            ]
            return results, groups

        def match_line(team_x, team_y, gx, gy, winner):
            """Formatierte Zeile: Team links - Score zentriert - Team rechts (Grid),
            kleine Flaggen, grün markierter Sieger."""
            def side(name, is_winner, align):
                color = "#2ECC71" if is_winner else "#E9E9E9"
                weight = "700" if is_winner else "400"
                justify = "flex-end" if align == "right" else "flex-start"
                flag_html = f"<img src='{flag_url(name, width=40)}' style='height:18px; border-radius:2px;'>"
                name_html = f"<span style='color:{color}; font-weight:{weight};'>{name}</span>"
                items = [flag_html, name_html] if align == "left" else [name_html, flag_html]
                return (
                    f"<div style='display:flex; align-items:center; justify-content:{justify}; gap:6px;'>"
                    f"{''.join(items)}</div>"
                )

            is_x = winner == team_x
            is_y = winner == team_y
            score_color_x = "#2ECC71" if is_x else "#E9E9E9"
            score_color_y = "#2ECC71" if is_y else "#E9E9E9"

            html = (
                f"<div style='display:grid; grid-template-columns:1fr auto 1fr; align-items:center; "
                f"padding:8px 12px; margin:4px 0; background:rgba(255,255,255,0.04); border-radius:6px;'>"
                f"{side(team_x, is_x, 'left')}"
                f"<div style='padding:0 14px; font-weight:700; font-size:1.05rem; white-space:nowrap;'>"
                f"<span style='color:{score_color_x};'>{gx}</span>"
                f"<span style='color:#777;'> : </span>"
                f"<span style='color:{score_color_y};'>{gy}</span>"
                f"</div>"
                f"{side(team_y, is_y, 'right')}"
                f"</div>"
            )
            st.markdown(html, unsafe_allow_html=True)

        def section_header(text, color):
            st.markdown(
                f"<div style='background:{color}; padding:6px 12px; border-radius:6px; "
                f"font-weight:700; margin:14px 0 8px 0;'>{text}</div>",
                unsafe_allow_html=True,
            )

        def render_team_journey(result: dict, groups_data: dict, team: str):
            team_group = next(g for g, teams in groups_data.items() if team in teams)

            section_header(f"\U0001f4cb GRUPPENPHASE \u2013 Gruppe {team_group}", "rgba(76,114,176,0.25)")

            standings = result["group_standings"][team_group]
            table_html = " &nbsp;→&nbsp; ".join(
                f"<img src='{flag_url(t, width=40)}' style='height:16px; vertical-align:middle; "
                f"margin-right:4px; border-radius:2px;'>{t}"
                for t in standings
            )
            st.markdown(
                f"<div style='padding:10px 14px; margin-bottom:10px; background:rgba(76,114,176,0.10); "
                f"border-left:3px solid #4C72B0; border-radius:6px;'>"
                f"<span style='color:#999; font-size:0.8rem;'>Tabelle:</span><br>{table_html}</div>",
                unsafe_allow_html=True,
            )

            for a, b, ga, gb in result["group_match_details"][team_group]:
                if team in (a, b):
                    winner = a if ga > gb else (b if gb > ga else None)
                    match_line(a, b, ga, gb, winner)

            rank = standings.index(team)
            if rank >= 2:
                st.warning(f"{team} scheidet in der Gruppenphase aus (Platz {rank + 1}).")
                return

            st.success(f"\u2705 {team} übersteht die Gruppenphase (Platz {rank + 1}).")

            section_header("\u26bd K.O.-PHASE", "rgba(243,156,18,0.25)")

            for round_key, label in [
                ("round_of_32", "Achtelfinale"),
                ("round_of_16", "Viertelfinale"),
                ("quarterfinal", "Halbfinale"),
                ("semifinal", "Finale"),
            ]:
                matches = result["knockout_details"][round_key]
                match = next((m for m in matches if team in (m[0], m[1])), None)
                if match is None:
                    return
                a, b, ga, gb, winner = match
                st.markdown(f"**{label}**")
                match_line(a, b, ga, gb, winner)
                if winner != team:
                    st.error(f"{team} scheidet im {label} aus.")
                    return

            a, b, ga, gb, winner = result["knockout_details"]["final"][0]
            st.markdown("**Finale**")
            match_line(a, b, ga, gb, winner)
            if winner == team:
                st.balloons()
                st.success(f"\U0001f3c6 {team} wird Weltmeister!")
            else:
                st.error(f"{team} verliert das Finale.")

        if st.button("Simulation starten", type="primary", key="team_sim_button"):
            with st.spinner(f"Simuliere {n_sim_team} Turnier(e) für {tracked_team}..."):
                results, groups_data = run_tournament_simulations_detailed(n_sim_team)
                st.session_state["team_sim_results"] = results
                st.session_state["team_sim_groups"] = groups_data
                st.session_state["team_sim_n"] = n_sim_team
                st.session_state["team_sim_team"] = tracked_team

        if st.session_state.get("team_sim_team") == tracked_team and "team_sim_results" in st.session_state:
            results = st.session_state["team_sim_results"]
            groups_data = st.session_state["team_sim_groups"]
            n_done = st.session_state["team_sim_n"]

            if n_done == 1:
                render_team_journey(results[0], groups_data, tracked_team)
            else:
                stage_labels = [
                    ("Gruppenphase", "r32"),
                    ("Achtelfinale", "round_of_16"),
                    ("Viertelfinale", "quarterfinal"),
                    ("Halbfinale", "semifinal"),
                    ("Finale", "final"),
                    ("Weltmeister", "champion"),
                ]
                counts = dict.fromkeys([k for _, k in stage_labels], 0)
                for r in results:
                    if any(tracked_team in (m[0], m[1]) for m in r["knockout_details"]["round_of_32"]):
                        counts["r32"] += 1
                    if tracked_team in r["round_of_16"]:
                        counts["round_of_16"] += 1
                    if tracked_team in r["quarterfinalists"]:
                        counts["quarterfinal"] += 1
                    if tracked_team in r["semifinalists"]:
                        counts["semifinal"] += 1
                    if tracked_team in r["finalists"]:
                        counts["final"] += 1
                    if r["champion"] == tracked_team:
                        counts["champion"] += 1

                df = pd.DataFrame(
                    [(label, 100 * counts[key] / n_done) for label, key in stage_labels],
                    columns=["Phase", "Wahrscheinlichkeit"],
                )

                base = alt.Chart(df).encode(
                    x=alt.X("Phase:N", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
                    y=alt.Y("Wahrscheinlichkeit:Q", title="Wahrscheinlichkeit (%)", scale=alt.Scale(domain=[0, 100])),
                )
                line = base.mark_line(color="#4C72B0", strokeWidth=3, point=alt.OverlayMarkDef(size=80, filled=True, color="#4C72B0"))
                labels = base.mark_text(dy=-14, color="white", fontWeight="bold", fontSize=13).encode(
                    text=alt.Text("Wahrscheinlichkeit:Q", format=".0f")
                )
                chart = (line + labels).properties(title="Wahrscheinlichkeit je Turnierphase")
                st.altair_chart(chart, use_container_width=True)
                st.caption(f"Basierend auf {n_done} simulierten Turnieren für {tracked_team}.")

                st.divider()
                st.markdown("##### Beispiel-Turnierverlauf (letzte Simulation)")
                render_team_journey(results[-1], groups_data, tracked_team)
        else:
            st.info("Team und Anzahl Simulationen wählen, dann auf **Simulation starten** klicken.")
