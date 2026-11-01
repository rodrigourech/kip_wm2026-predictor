# WM 2026 Match Predictor

Vorhersage von Spielen zwischen den 48 Teams der FIFA WM 2026 und Monte-Carlo-Simulation des gesamten Turniers, mit Streamlit-Dashboard.

Projekt der Mini-Challenge im Modul KIP (KI-gestütztes Programmieren), BSc Data Science, FHNW. Autor Rodrigo Urech.

## Was das Projekt macht

- Ruft historische Länderspiele und Match-Statistiken aller 48 WM-Teams über API-Football ab (Saisons 2018 bis 2026)
- Ergänzt die Daten um historische Elo-Ratings als Ranking (statt FIFA-Ranking)
- Berechnet pro Spiel Form-, Tor- und Statistikwerte ausschliesslich aus früheren Spielen (kein Data Leakage)
- Sagt mit einem Random-Forest-Klassifikator Sieg, Unentschieden oder Niederlage voraus und schätzt mit einem Random-Forest-Regressor die erwarteten Tore
- Simuliert das komplette Turnier von der Gruppenphase bis zum Final, inklusive der offiziellen Zuordnung der acht besten Gruppendritten (Annex C, 495 Kombinationen)
- Zeigt Vorhersagen, Teamvergleiche und Simulationsergebnisse in einem Streamlit-Dashboard

## Projektstruktur

```
wm2026-predictor/
├── app/
│   └── dashboard.py              Streamlit-Dashboard
├── data/
│   ├── raw/                      Rohdaten (Fixtures je Team, Match-Stats, Elo, Annex C, Spielplan, Gruppen)
│   └── processed/                Feature-Tabelle und Simulationsergebnisse
├── docs/
│   ├── kip_documentation.md      KI-Dokumentation (Entwicklungstagebuch)
│   └── FWC2026_Annex_C.pdf       Auszug FIFA-Reglement, Annex C
├── models/                       Trainierte Modelle, Imputer, Feature-Listen, Modellvergleich
├── notebooks/
│   └── wm2026_predictor.ipynb    Datenkontrolle, Evaluation, Modellvergleich
├── src/
│   ├── config.py                 Konfiguration, Teamliste, Pfade
│   ├── fetch_data.py             Datenabruf über API-Football
│   ├── build_features.py         Feature Engineering
│   ├── train_models.py           Training von Klassifikator und Tore-Regressor
│   ├── compare_models.py         Vergleich Random Forest, Logistic Regression, Gradient Boosting
│   └── monte_carlo_simulation.py Turniersimulation
├── tests/                        12 pytest-Tests in vier Dateien
├── .env.example                  Vorlage für die Umgebungsvariablen
└── requirements.txt
```

## Setup

Voraussetzung ist Python 3.13.

```powershell
git clone https://github.com/rodrigourech/kip_wm2026-predictor.git
cd kip_wm2026-predictor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Unter macOS oder Linux lauten die beiden abweichenden Befehle `source .venv/bin/activate` und `cp .env.example .env`.

## API-Key

`src/config.py` erwartet die Variable `API_FOOTBALL_KEY` in der Datei `.env`. Die `.env` ist über die `.gitignore` vom Repository ausgeschlossen.

- Für Dashboard, Training, Simulation und Tests genügt der Platzhalter aus `.env.example`. Alle Rohdaten liegen bereits im Repository.
- Nur für einen neuen Datenabruf mit `fetch_data.py` ist ein gültiger Key von [api-football.com](https://www.api-football.com) nötig.

## Ablauf der Pipeline

Alle Befehle werden im Projektordner ausgeführt.

```powershell
python src/fetch_data.py               # optional, nur mit gültigem Key
python src/fetch_data.py --refresh     # optional, ergänzt nur neue Spiele der Saison 2026
python src/build_features.py           # erzeugt data/processed/match_features.csv
python src/train_models.py             # trainiert Klassifikator und Tore-Regressor
python src/compare_models.py           # vergleicht drei Klassifikationsmodelle
python src/monte_carlo_simulation.py --n 1000   # simuliert das Turnier 1000-mal
```

Die trainierten Modelle liegen bereits in `models/`. Für das Dashboard muss die Pipeline nicht neu ausgeführt werden.

## Dashboard starten

```powershell
streamlit run app/dashboard.py
```

## Tests

```powershell
pytest -v
```

Geprüft werden unter anderem die zeitliche Korrektheit der Features, der Ausschluss von Data Leakage, die Vollständigkeit der 495 Annex-C-Kombinationen, die Weiterleitung im K.-o.-Turnierbaum, gültige Modellwahrscheinlichkeiten und die Reproduzierbarkeit der Simulation bei gleichem Seed.

## Modellleistung

Chronologischer Split, Training 912 Spiele bis 10.10.2024, Test 229 Spiele ab 11.10.2024.

| Modell | Kennzahl | Modell | Baseline |
| --- | --- | --- | --- |
| Klassifikator (Random Forest) | Accuracy | 0.498 | 0.354 |
| Tore-Regressor Team A | MAE | 0.861 | 0.901 |
| Tore-Regressor Team B | MAE | 1.011 | 1.082 |

Die Logistic Regression erreicht im Vergleich 0.520 Accuracy. Der Unterschied ist bei 229 Testspielen nicht belastbar, deshalb bleibt der bereits integrierte Random Forest das Hauptmodell. Details im Notebook.

## Bekannte Grenzen

- Unentschieden werden kaum erkannt (Recall 0.17), bei allen drei getesteten Modellen
- Verlängerung und Elfmeterschiessen werden nicht modelliert. In der K.-o.-Phase wird der Unentschieden-Anteil entfernt und die beiden Siegwahrscheinlichkeiten werden auf 100 Prozent hochgerechnet
- Der Fairplay-Tiebreaker der Gruppenphase wird nicht simuliert
- Form und Ranking werden einmal vor Turnierbeginn berechnet und bleiben während einer Simulation konstant
- Vorhersagen sind Wahrscheinlichkeiten und keine sicheren Resultate

## Datenquellen

- API-Football (API-Sports), Version 3, [api-football.com](https://www.api-football.com)
- Historische Elo-Ratings von [eloratings.net](https://www.eloratings.net), über den Kaggle-Datensatz "2026 FIFA World Cup Historical Elo Ratings"
- FIFA-Reglement zur WM 2026, Annex C, Auszug in `docs/FWC2026_Annex_C.pdf`

## KI-Einsatz

Das Projekt wurde mit KI-Unterstützung entwickelt, hauptsächlich mit Claude und Claude Code, punktuell mit ChatGPT. Der Einsatz, die Prüfung der KI-Ausgaben und die getroffenen Entscheidungen sind in `docs/kip_documentation.md` dokumentiert.
