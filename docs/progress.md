# Progress – WM 2026 Match Predictor

> Kompakte Zusammenfassung des aktuellen Projektstands. Wird laufend ergänzt.
> Für den detaillierten KI-Einsatz siehe `docs/KIP_Dokumenation.md`.

**Letztes Update:** 14.07.2026

---

## Status auf einen Blick

| Baustein | Status |
|---|---|
| Datenpipeline (Fixtures) | ✅ Fertig – 48/48 Teams |
| Datenpipeline (Match-Stats) | ✅ Fertig – 4'683/4'683 Fixtures |
| Ranking-Ratings (Elo-basiert) | ✅ Integriert |
| Feature Engineering | ✅ Fertig – `match_features.csv` |
| ML-Modell (Random Forest) | ✅ Trainiert & evaluiert |
| Diagnose/EDA-Notebook | ✅ Fertig – `wm2026_predictor_nb.ipynb` |
| Streamlit-Dashboard | ⬜ Noch offen |
| Stretchgoals | ⬜ Noch offen |

---

## 1. Setup & Repository

- Exposé erstellt und via Mail eingereicht (SW6)
- Git-Repo: `github.com/rodrigourech/kip_wm2026-predictor`
- Projektstruktur: `src/`, `data/raw/`, `data/processed/`, `models/`, `notebooks/`, `docs/`
- `.env` (API-Key) und `.gitignore` korrekt eingerichtet – keine Secrets im Repo

## 2. Datenpipeline

**Datenquelle:** API-Football (Pro-Plan, $19/Monat, 7'500 Requests/Tag), direkt über api-football.com

- **`fetch_data.py`**: Länderspiele für alle 48 WM-2026-Teams, Saisons 2018–2026 (2 WM-Zyklen)
  → 5'965 Spiele total, **4'683 eindeutige Fixtures**
- **`fetch_match_stats.py`**: Match-Statistiken (Ballbesitz, Schüsse, Ecken etc.) pro Fixture
  → 100% Abdeckung (4'683/4'683), dedupliziert über Fixture-IDs
- **Stats-Abdeckungsanalyse**: nur Statistik-Typen mit >90% Abdeckung als Feature verwendet
  (Ball Possession, Total Shots, Shots on Goal, Corner Kicks) – Red Cards/expected_goals verworfen (<30% Abdeckung)
- **Ranking-Feature**: Kaggle-Datensatz "2026 FIFA World Cup – Historical Elo Ratings" (1901–2026,
  alle 48 Teams) als Ersatz fürs offizielle FIFA-Ranking (Begründung: zeitliche Konsistenz +
  wissenschaftliche Evidenz, dass Elo prädiktiver ist als FIFA-Ranking – wird im Bericht dokumentiert)

**Gelöste Probleme unterwegs:**
- Windows-Encoding-Bug (`cp1252` statt UTF-8) bei Sonderzeichen in Teamnamen
- Free-Tier-Limits (Rate-Limit, gesperrter `last`-Parameter, nur Saisons 2022–2024) → Pro-Plan-Upgrade
- 5 Teams mit abweichenden Namen bei API-Football (z.B. "DR Congo" statt "Congo DR") → Mehrfach-Namensvarianten
- Fabrizierte FIFA-Ranking-Daten (Claude-Fehler, erkannt & korrigiert) → Umstieg auf verifizierte Elo-CSV

## 3. Feature Engineering (`build_features.py`)

Für jedes historische Spiel zwischen zwei WM-2026-Teams, **ausschliesslich aus Daten vor dem
Spieldatum** (kein Data Leakage):

- Formkurve (Punkte letzte 5 Spiele), Tordurchschnitt (Ø letzte 5 Spiele)
- Match-Stats-Schnitt (Ballbesitz, Schüsse, Ecken, letzte 5 Spiele)
- Head-to-Head-Bilanz
- Ranking-Rating-Differenz (Elo-basiert)

→ **1'141 Spiele** zwischen WM-2026-Teams mit ausreichend Historie in `data/processed/match_features.csv`

**WM-2026-Toggle** (`data_utils.py`): Spiele nach dem 19.06.2026 (Turnierbeginn) können optional
aus- oder eingeschlossen werden – Rohdaten bleiben davon unberührt.

## 4. Modell (`train_model.py`)

- Random Forest (`n_estimators=200`, `max_depth=10`)
- **Chronologischer Split** (nicht zufällig!) – letzte 20% der Spiele als Testset
- Fehlende Werte (~19%, v.a. Match-Stats) per Median-Imputation (nur aus Trainingsset)

**Ergebnis:**
- Accuracy: **50.2%** (Zufall bei 3 Klassen = 33%)
- Bekannte Schwäche: Unentschieden werden kaum erkannt (Recall 0.10) – dokumentiert als
  strukturelle, in der Fussball-Analytik übliche Modellgrenze, nicht als Bug
- Stärkstes Feature: `ranking_diff`

## 5. Notebooks

**`notebooks/wm2026_predictor_nb.ipynb`** – zentrales Analyse-Notebook (11 Abschnitte):
Datenpipeline-Status, Feature-Sanity-Check, Klassenverteilung, Feature-Verteilungen,
Korrelationen, fehlende Werte, Modell-Evaluation, Feature Importance, Live-Vorhersage-Test
(`predict_matchup("Team A", "Team B")` als Vorschau auf die Dashboard-Logik)

## 6. Dokumentation

- `docs/KIP_Dokumenation.md`: laufendes Prompt-für-Prompt-Log (Prompt / Übernommen-angepasst-verworfen
  / Eigene Entscheidungen / Probleme / Outcome)
- `docs/entwicklungsbericht_template.md`: Skelett für den finalen Bericht (wird gegen Ende befüllt)

---

## Nächste Schritte

1. **Streamlit-Dashboard**: Team-Auswahl, Vorhersage + Wahrscheinlichkeit, Feature-Importance-Chart,
   WM-2026-Toggle einbauen
2. Stretchgoals priorisieren (Modellvergleich, Momentum-Score, WM-Trauma-Index, Monte-Carlo-Simulation)
3. Gegen Ende: KI-Dokumentation zum finalen Entwicklungsbericht verdichten
