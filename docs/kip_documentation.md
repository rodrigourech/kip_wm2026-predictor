# KIP Dokumentation – WM 2026 Match Predictor

## Vorlage

```
### [Datum] – [Kurztitel] - [Modell: Claude Code]
-

**Prompt:**


**Übernommen / angepasst / verworfen:**


**Eigene Entscheidungen:**
-


**Probleme:**
-

-

**Outcome:**
```

---

## Einträge

### 09.07.2026 – Projekt-Setup: Config, Fetch-Skript, Requirements

**Modell:** Claude

**Prompt:**
Claude gebeten, für das Projekt laut Exposé die initialisierenden Dateien zu bauen:

* Konfigurationsmodul
* Skript für den Datenabruf von API-Football (Pro Subscription) für die letzten zwei WM-Zyklen
* `requirements.txt`

**Übernommen / angepasst / verworfen:**
`config.py` und `fetch_data.py` wurden von Claude generiert und übernommen.

`config.py` lädt den API-Key aus der `.env`-Datei und enthält die Liste aller 48 WM-2026-Teams. Die Liste wurde von Claude recherchiert und von mir stichprobenartig geprüft.

`fetch_data.py` ruft pro Team die Team-ID und die letzten Länderspiele ab und speichert sie lokal als JSON.

**Eigene Entscheidungen:**
Die `.env`-Datei mit API-Key und Host wurde selbst erstellt und lokal gehalten. Sie ist nicht Teil des von Claude generierten Codes und wurde bewusst nicht ins Repository committed.

API-Football wurde direkt über `api-football.com` statt über RapidAPI verwendet, da der Zugriff dadurch einfacher ist.

**Probleme:**
Klassisches Windows-Problem: `write_text()` nutzt ohne explizite Angabe die Systemkodierung `cp1252`. Diese kann Sonderzeichen wie `ć`, beispielsweise in Namen wie „Kovačić", nicht darstellen.

Fix: Überall explizit `encoding="utf-8"` angeben.

**Outcome:**
Dateien erstellt, Codeinhalt geprüft.

---

### 10.07.2026 – WM-2026-Toggle für Dashboard-Daten

**Modell:** Claude

**Prompt:**

> Bitte Toggle einfügen für Daten von WM26 (Datum alles nach 19.06.26), damit man entscheiden kann, ob man diese Daten im Dashboard einfliessen lassen möchte.

**Übernommen / angepasst / verworfen:**
Das neue Modul `data_utils.py` mit `load_team_fixtures()` und `filter_fixtures(..., include_wm2026=False)` wurde von Claude vorgeschlagen und übernommen.

Das Cutoff-Datum `19.06.2026` wurde direkt übernommen.

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Rohdaten bleiben unverändert; Filter wird erst bei Nutzung (Feature Engineering / Dashboard-Toggle) angewendet, kein erneuter Datenabruf nötig.

---

### 10.07.2026 – Match-Stats-Skript: Ballbesitz, Schüsse etc.

**Modell:** Claude

**Prompt:**
Ein weiteres Skript erstellen, das die Match-Statistiken exportiert und ebenfalls abspeichert.

**Übernommen / angepasst / verworfen:**
Das neue Skript `fetch_match_stats.py` wurde von Claude vorgeschlagen und übernommen.

Das Skript sammelt zuerst alle eindeutigen Fixture-IDs aus den Dateien der 48 Teams. Dabei werden Duplikate entfernt, da Spiele zwischen zwei WM-Teams ansonsten doppelt gezählt würden.

Anschliessend werden die Statistiken pro Fixture über `/fixtures/statistics` abgerufen und einzeln unter folgendem Pfad gespeichert:

`data/raw/stats/{fixture_id}.json`

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Skript zusätzlich robuster gestaltet (überspringt leere/beschädigte Dateien statt abzustürzen, resumable bei Tageslimit).

---

### 13.07.2026 – Status-Check-Skript für Datenabruf-Fortschritt

**Modell:** Claude

**Prompt:**
Code erstellen, um den aktuellen Stand der Datenabrufe zu prüfen. Danach wurde die Ausgabe übersichtlicher gestaltet und um eine Darstellung pro Team für Spiele und Statistiken ergänzt.

**Übernommen / angepasst / verworfen:**
Das neue Skript `check_status.py` wurde von Claude vorgeschlagen und übernommen.

Das Skript zeigt pro Team eine Tabelle mit:

* Anzahl Spiele
* Bereits abgerufenen Match-Statistiken
* Fortschritt in Prozent

Zusätzlich wird am Ende eine Gesamtzusammenfassung ausgegeben. Fehlende oder leere Dateien werden explizit ausgewiesen.

**Eigene Entscheidungen:**
–

**Probleme:**
Dabei wurde festgestellt, dass `fixtures_Mexico.json` leer war und eine Dateigrösse von 0 Bytes hatte. Dabei handelte es sich um ein Überbleibsel eines früheren abgebrochenen Laufs.

Die Datei wurde dank des Status-Checks gezielt nachgeladen.

**Outcome:**
47 von 48 Teams, 4'611 eindeutige Fixtures, Match-Statistik-Fortschritt in Prozent ausgegeben.

---

### 13.07.2026 – Stats-Abdeckungsanalyse und MVP-Scope-Erweiterung

**Modell:** Claude

**Prompt:**
Wunsch geäussert, Spielstatistiken wie Ballbesitz und Eckbälle in das MVP aufzunehmen, da diese Daten dank des Pro-Abonnements nun verfügbar sind.

Anschliessend wurde darum gebeten, im Status-Check zu ergänzen, welche Statistiktypen konsistent über alle Daten vorhanden sind, um die Feature-Auswahl besser zu fundieren.

**Übernommen / angepasst / verworfen:**
Das neue Skript `analyze_stats_coverage.py` wurde von Claude vorgeschlagen und übernommen.

Das Skript prüft pro Statistiktyp, in wie vielen Spielen beide Teams einen echten Wert besitzen. Untersucht werden unter anderem:

* Ballbesitz
* Schüsse
* Eckbälle
* Fouls
* Karten

Die Ausgabe erfolgt als nach Abdeckungsgrad sortierte Tabelle.

**Eigene Entscheidungen:**
Bewusste Scope-Erweiterung gegenüber dem ursprünglichen Exposé.

Ballbesitz und Eckbälle waren dort nicht als Features geplant. Ursprünglich vorgesehen waren lediglich:

* Formkurve
* Head-to-Head
* Ranking-Differenz
* Tordurchschnitt

Es wurde entschieden, Eckbälle als zusätzliches Feature aufzunehmen. Die finale Feature-Auswahl soll jedoch datenbasiert anhand des Abdeckungsgrads erfolgen und nicht nach Bauchgefühl.

**Probleme:**
–

**Outcome:**
Feature-Auswahl erfolgt datenbasiert anhand des Abdeckungsgrads statt nach Bauchgefühl.

---

### 14.07.2026 – Feature Engineering: Formkurve, H2H, Ranking-Differenz, Match-Stats

**Modell:** Claude

**Prompt:**
Wunsch geäussert, das Feature Engineering als sauberes Skript (nicht als Notebook) umzusetzen. Vorgabe gemacht, dass Features pro Spiel ausschliesslich aus Daten vor dem jeweiligen Spieldatum berechnet werden dürfen (kein Data Leakage). Formkurve-Fenster auf die letzten 5 Spiele festgelegt.

**Übernommen / angepasst / verworfen:**
Das neue Skript `build_features.py` wurde von Claude vorgeschlagen und übernommen.

Das Skript baut pro Team eine chronologische Spielhistorie auf, identifiziert alle Spiele zwischen zwei WM-2026-Teams und berechnet pro Spiel:

* Formkurve (Punkte aus den letzten 5 Spielen)
* Tordurchschnitt (geschossen/kassiert)
* Head-to-Head-Bilanz
* Ranking-Differenz, berechnet aus Elo-Ratings (inkl. Namens-Mapping zwischen unserer Team-Liste und der Rating-CSV, z. B. "USA" vs. "United States")
* Ballbesitz-, Schuss- und Eckball-Schnitt (wo Daten vorhanden)

Das Ergebnis wird als `data/processed/match_features.csv` gespeichert.

**Eigene Entscheidungen:**
Formkurve-Fenster bewusst auf 5 Spiele festgelegt (nicht 10 oder 15), um einen Kompromiss zwischen Aktualität und genügend Stichprobengrösse zu haben.

**Probleme:**
–

**Outcome:**
Logik an Beispiel-Datensatz (Canada vs. Mexico) durchgerechnet und manuell verifiziert, bevor auf echte Daten angewendet.

---

### 14.07.2026 – Encoding-Bug in data_utils.py behoben

**Modell:** Claude

**Prompt:**
Fehlermeldung beim Ausführen von `build_features.py` gemeldet (`UnicodeDecodeError` beim Einlesen von `fixtures_*.json` über `data_utils.py`).

**Übernommen / angepasst / verworfen:**
Festgestellt, dass die lokale Version von `data_utils.py` den bereits an anderer Stelle (fetch_match_stats.py) eingebauten Encoding-Fallback (UTF-8 mit cp1252-Fallback) noch nicht enthielt. Aktuelle, bereits korrigierte Version von Claude erneut zum Ersetzen erhalten und übernommen.

**Eigene Entscheidungen:**
–

**Probleme:**
Gleicher Encoding-Bug wie zuvor bei `fetch_match_stats.py` (ältere, vor dem Fix gespeicherte `fixtures_*.json`-Dateien enthalten Sonderzeichen in cp1252 statt UTF-8) – diesmal in `data_utils.py`, da dort der Fix versehentlich nicht mit übernommen wurde, als nur einzelne Dateien ersetzt wurden.

**Outcome:**
Encoding-Fallback in `data_utils.py` nachgezogen.

---

### 14.07.2026 – Diagnose-Skripte zu einem Notebook zusammengeführt

**Modell:** Claude

**Prompt:**
Wunsch geäussert, die drei Diagnose-Skripte (`check_status.py`, `analyze_stats_coverage.py`, `quick_check_features.py`) in einem Notebook zusammenzufassen, um die Einzel-Skripte danach löschen zu können.

**Übernommen / angepasst / verworfen:**
Neues Notebook `notebooks/data_diagnostics.ipynb` von Claude erstellt und übernommen. Enthält eine gemeinsame Setup-Zelle (Imports, Pfad-Konfiguration zu `src/`) sowie drei separate Abschnitte mit Markdown-Überschriften:

1. Status-Check (Fixtures/Match-Stats-Fortschritt pro Team)
2. Stats-Abdeckung (welche Statistik-Typen zuverlässig genug sind)
3. Feature-Sanity-Check (Klassenverteilung, fehlende Werte in `match_features.csv`)

**Eigene Entscheidungen:**
Bewusste Entscheidung, reine Diagnose-/Kontroll-Skripte (die nicht Teil der eigentlichen Datenpipeline sind) in ein Notebook auszulagern, während die Kern-Pipeline (`fetch_data.py`, `fetch_match_stats.py`, `build_features.py`) als Skripte bestehen bleibt – sauberere Trennung zwischen reproduzierbarer Pipeline und explorativer Kontrolle.

**Probleme:**
–

**Outcome:**
Notebook vor Auslieferung auf gültiges JSON-Format geprüft; Logik identisch zu den drei Skripten, nur zusammengeführt.

---

### 14.07.2026 – Random-Forest-Modell trainieren

**Modell:** Claude

**Prompt:**
Skript erstellen lassen, das auf Basis von `match_features.csv` einen Random-Forest-Klassifikator trainiert (Sieg Team A / Unentschieden / Sieg Team B), inkl. Evaluation und Speicherung fürs spätere Dashboard.

**Übernommen / angepasst / verworfen:**
Skript `train_model.py` von Claude vorgeschlagen und übernommen. Enthält:

* **Zeitlichen statt zufälligen Train/Test-Split**: Test = chronologisch letzte 20% der Spiele, statt zufällige Stichprobe – begründet damit, dass ein zufälliger Split die Performance zu optimistisch einschätzen würde (Modell könnte sonst aus zeitlich nahen, ähnlichen Spielen in Training und Test "schummeln").
* **Median-Imputation für fehlende Werte** (Ballbesitz/Schüsse/Ecken, ca. 19% der Zeilen), wobei der Median explizit nur aus dem Trainingsset berechnet wird (nicht aus dem Testset), um erneutes Data Leakage zu vermeiden.
* Random Forest mit `n_estimators=200`, `max_depth=10`.
* Ausgabe von Accuracy, Classification Report, Confusion Matrix und Feature Importance (Top 10).
* Speicherung von Modell, Imputer und Feature-Liste unter `models/` für die spätere Nutzung im Streamlit-Dashboard.

**Eigene Entscheidungen:**
`NON_FEATURE_COLS` bewusst definiert, um Identifikatoren (fixture_id, date, team_a/b) und die zum Vorhersagezeitpunkt nicht bekannten Ist-Werte (goals_a, goals_b) explizit vom Feature-Set auszuschliessen.

**Probleme:**
–

**Outcome:**
Modell trainiert und gespeichert (`models/*.pkl`, `feature_columns.json`).

---

### 14.07.2026 – Modell trainiert, Draw-Problem als bekannte Grenze dokumentiert

**Modell:** Claude

**Prompt:**
`train_model.py` ausgeführt und Ergebnisse (Accuracy 50.2%, schwache Erkennung von Unentschieden) besprochen.

**Übernommen / angepasst / verworfen:**
Ergebnis so übernommen wie trainiert, keine Anpassung vorgenommen. Bewusst entschieden, das Draw-Problem als dokumentierte Modellgrenze stehen zu lassen statt sofort zu optimieren (z.B. via `class_weight`), um zügig zum Dashboard überzugehen.

**Eigene Entscheidungen:**
Entscheidung, die Erkennungsschwäche bei Unentschieden nicht als Fehler zu behandeln, sondern als bekannte, in der Fussball-Analytik übliche Grenze zu akzeptieren und im Bericht transparent zu machen.

**Probleme:**
Modell erkennt Unentschieden kaum (Recall 0.10) – von 69 echten Unentschieden im Testset wurden nur 7 korrekt erkannt, die meisten wurden als Sieg vorhergesagt.

**Outcome:**
Accuracy 50.2% (Zufall = 33%); Ranking-Differenz als stärkstes Einzel-Feature bestätigt.

---

### 15.07.2026 – Umbenennung Elo → Ranking (Code, Daten, Dokumentation)

**Modell:** Claude Code

**Prompt:**
Eigenständig (ohne Claude-Chat) mit Claude Code durchgeführt: sämtliche `elo_`-Bezeichnungen im Projekt auf `ranking_` umbenennen, sowohl im Code als auch in der Prosa, mit gezielten Ausnahmen.

**Übernommen / angepasst / verworfen:**
Folgende Umbenennungen selbständig vorgenommen:

* `src/build_features.py`: `ELO_CSV`→`RANKING_CSV`, `ELO_NAME_MAP`→`RANKING_NAME_MAP`, `load_elo_ratings()`→`load_ranking_ratings()`, `get_elo()`→`get_ranking()`, Variablen `elo_*`→`ranking_*`, Output-Spalten `elo_a/elo_b/elo_diff`→`ranking_a/ranking_b/ranking_diff`
* `models/feature_columns.json`: Spaltennamen entsprechend angepasst
* `data/processed/match_features.csv`: Header-Zeile umbenannt (Werte unverändert)
* `docs/progress.md`: Statustabelle, Feature-Liste, "Stärkstes Feature"-Zeile umgestellt
* `notebooks/wm2026_predictor_nb.ipynb`: alle Code- und Markdown-Zellen entsprechend angepasst

**Eigene Entscheidungen:**
Bewusst NICHT geändert:

* Dateiname `data/raw/elo_ratings_wc2026.csv` bleibt unverändert (einzige Ausnahme)
* Wörtliche Zitate/faktische Aussagen über den echten Elo-Algorithmus (Kaggle-Datensatztitel "...Historical Elo Ratings", die Aussage zur wissenschaftlichen Evidenz "Elo prädiktiver als FIFA-Ranking") bleiben bei "Elo", da eine Umbenennung dort inhaltlich falsch wäre

**Probleme:**
–

**Outcome:**
Refactoring eigenständig mit Claude Code durchgeführt, ohne Rückfrage im Chat.

---


### 15.07.2026 – Konsolidierung der Einzel-Skripte

**Modell:** Claude

**Prompt:**
Rückmeldung gegeben, dass mittlerweile zu viele einzelne Skripte im Projekt vorhanden sind, und gefragt, ob sich das zusammenführen lässt.

**Übernommen / angepasst / verworfen:**
Drei Zusammenführungen von Claude vorgeschlagen und übernommen:

* `fetch_data.py` + `fetch_match_stats.py` → **`fetch_data.py`** (Phase 1: Fixtures, Phase 2: Match-Stats, in einem `main()`-Durchlauf)
* `data_utils.py` (nur von `build_features.py` genutzt) → Funktionen direkt in **`build_features.py`** integriert, `data_utils.py` entfernt
* `train_model.py` + `train_goals_model.py` → **`train_models.py`** (gemeinsame Datenlade-/Split-/Imputations-Logik, trainiert Klassifikator und Regressor nacheinander)

`config.py` bewusst unverändert gelassen (reine Konstanten/Pfade, macht als eigene Datei weiterhin Sinn).

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Von 7 auf 4 Skripte reduziert (`config.py`, `fetch_data.py`, `build_features.py`, `train_models.py`). Alle drei zusammengeführten Skripte vor Auslieferung gegen Mock-Daten getestet (Syntax + Ausführung), keine inhaltliche Änderung an der bisherigen Logik – bereits abgerufene/berechnete Daten (Fixtures, Match-Stats, `match_features.csv`, trainierte Modelle) mussten daher nicht neu erzeugt werden.


### 15.07.2026 – Tore-Regressor als Ergänzung zum Klassifikator

**Modell:** Claude

**Prompt:**
Nachfrage gestellt, ob das Modell auch Spielstände (Tore pro Team) vorhersagen kann, nicht nur Sieg/Unentschieden/Niederlage. Auf Rückfrage entschieden, ein zusätzliches Regressionsmodell dafür zu bauen.

**Übernommen / angepasst / verworfen:**
Neues Skript `train_goals_model.py` (später in `train_models.py` zusammengeführt) von Claude vorgeschlagen und übernommen: `RandomForestRegressor` mit nativem Multi-Output (`goals_a` + `goals_b` in einem Modell), gleicher chronologischer Split und gleiche Median-Imputation wie beim Klassifikator, damit die Ergebnisse vergleichbar bleiben.

**Eigene Entscheidungen:**
Bewusste Scope-Erweiterung gegenüber dem Exposé – dort war nur "wahrscheinlicher Sieger + Siegwahrscheinlichkeit" geplant, nicht die konkrete Toranzahl. Regressor ergänzt den Klassifikator, ersetzt ihn nicht (beide Outputs sollen später im Dashboard nebeneinander erscheinen).

Methodische Entscheidung: Random Forest Regressor statt der in der Fussball-Analytik "klassischen" Poisson-Regression (die statistisch für Zähldaten wie Tore eigentlich passender wäre) – begründet mit Konsistenz zum Rest des Projekts (Random Forest ist bereits das Kernmodell) und der Fähigkeit, nichtlineare Interaktionseffekte zwischen Features abzubilden, statt ein zweites Modell-Framework einzuführen.

**Probleme:**
–

**Outcome:**
Modell trainiert und gespeichert (`goals_regressor_model.pkl`, `goals_imputer.pkl`, `goals_feature_columns.json`). Aus den vorhergesagten Toren zusätzlich ein abgeleitetes Ergebnis (A/Draw/B) berechnet, nur als Cross-Check gegen den Klassifikator, nicht als Ersatz für die Dashboard-Siegwahrscheinlichkeit.

---

### 15.07.2026 – Baseline-Vergleich im Regression Report

**Modell:** Claude Code

**Prompt:**
Eigenständig (ohne Claude-Chat) mit Claude Code durchgeführt: Regression Report um einen Baseline-Vergleich (naive Vorhersage = Mittelwert aus Trainingsdaten) sowie einen Check auf negative Torprognosen ergänzt.

**Übernommen / angepasst / verworfen:**
Baseline berechnet als konstante Vorhersage (Mittelwert von `goals_a`/`goals_b` aus dem Trainingsset), MAE/RMSE davon neben die Modell-Werte gestellt. Zusätzlich Anzahl negativer Torprognosen im Testset ausgegeben (Random Forest könnte theoretisch <0 vorhersagen, auch wenn das fachlich unmöglich ist).

**Eigene Entscheidungen:**
Baseline-Vergleich bewusst beibehalten (Diskussion mit Claude, ob nötig): zeigt, dass das Modell tatsächlich etwas gelernt hat und nicht nur ähnlich gut ist wie "einfach den Durchschnitt vorhersagen" – Standardpraxis in der ML-Validierung, relevant fürs Bewertungskriterium Qualitätssicherung.

**Probleme:**
–

**Outcome:**
Regression Report zeigt jetzt Modell- und Baseline-MAE/RMSE nebeneinander sowie die Anzahl negativer Vorhersagen; Rundung auf ganze Tore bewusst nicht hier, sondern erst später in der Dashboard-Anzeige vorgesehen (Rohwerte bleiben für die Fehlermetrik unverändert).


---

### 15.07.2026 – Streamlit-Dashboard: Grundgerüst

**Modell:** Claude

**Prompt:**
Aufbau des Streamlit-Dashboards angefordert: zwei Teams auswählen, Sieg-Wahrscheinlichkeit (Klassifikator) und erwartetes Ergebnis (Tore-Regressor) anzeigen, WM-2026-Toggle einbauen.

**Übernommen / angepasst / verworfen:**
`app/dashboard.py` von Claude erstellt und übernommen. Nutzt dieselben Funktionen aus `build_features.py` wie Notebook (`build_team_match_history`, `compute_rolling_features`, `compute_h2h`, `get_ranking`), keine Logik-Duplikation. Modelle und Referenzdaten via `@st.cache_resource`/`@st.cache_data` gecached.

**Eigene Entscheidungen:**
Torzahlen für die Anzeige gerundet, Rohwert zusätzlich klein daneben angezeigt (Rundung bewusst nur in der UI, nicht in der Modell-Evaluation).

**Probleme:**
`use_container_width` bei `st.image()` nicht kompatibel mit der lokal installierten Streamlit-Version – durch `use_column_width` ersetzt.

**Outcome:**
Funktionierendes Grundgerüst mit Team-Auswahl, Vorhersage, Sieg-Wahrscheinlichkeit und Feature-Importance-Chart.

---

### 15.07.2026 – Umstellung Formkurve/Stats auf EWMA (statt festem Fenster)

**Modell:** Claude

**Prompt:**
Hinterfragt, ob ein festes Fenster von 5 (bzw. 10) Spielen für Formkurve und Match-Stats-Durchschnitte statistisch fundiert genug ist, angesichts der Datenlücken bei Match-Stats (~39% fehlend) und der Frage, ob mehr historische Daten einen fundierteren Ansatz ermöglichen würden.

**Übernommen / angepasst / verworfen:**
`compute_rolling_features()` in `build_features.py` umgebaut: exponentiell gewichteter Durchschnitt (EWMA) über die **komplette verfügbare Historie** statt festem Fenster-Cutoff. Decay-Faktor 0.87 (Halbwertszeit ≈ 5 Spiele), methodisch konsistent mit dem Funktionsprinzip von Elo-Ratings.

**Eigene Entscheidungen:**
Bewusst gegen die einfachere "Option 2" (zwei getrennte feste Fenster für Form vs. Stats) entschieden, zugunsten der methodisch saubereren EWMA-Lösung – mehr Aufwand (Feature-Tabelle und beide Modelle mussten neu erzeugt werden), aber fundierter begründbar.

**Probleme:**
`form_points` ist durch die Umstellung jetzt ein gewichteter Durchschnitt (Skala 0–3) statt einer Summe (Skala 0–15) – Semantikänderung, an keiner weiteren Stelle im Code Anpassung nötig (Dashboard/Notebook rufen die Funktion mit denselben Positionsargumenten auf).

**Outcome:**
`match_features.csv` und beide Modelle (`train_models.py`) neu generiert. Dashboard/Notebook ohne Codeänderung weiterhin kompatibel, da der neue Parameter einen Default-Wert hat.

---

### 15.07.2026 – Dashboard UI-Verfeinerung (iterativ)

**Modell:** Claude

**Prompt:**
Mehrere aufeinanderfolgende Anpassungswünsche zur Dashboard-Optik und -Struktur geäussert, u.a.:
- Flaggen der Teams gross anzeigen
- Feature-Importance-Chart durch direkten Team-Vergleich ("Tale of the Tape") ersetzen
- Vorhersage-Score grösser, Gewinner grün/Verlierer rot einfärben
- Sieg-Wahrscheinlichkeit als Unterkapitel von "Vorhersage"
- Form als farbige Kacheln (Sieg/Unentschieden/Niederlage) statt nur Punktzahl
- "Ranking" zu "Elo Ranking" präzisiert, als Hyperlink mit Hover-Erklärung
- Head-to-Head als Balkendiagramm statt Liste, einfarbig, nur einmal (im Team-Vergleich) statt doppelt
- Hinweis-Box zur Ø-Erklärung formatiert (Titel fett, definierter Abstand)

**Übernommen / angepasst / verworfen:**
Alle Punkte von Claude umgesetzt, mit Zwischenständen nach jedem Schritt zur Kontrolle. Mehrere Korrekturschleifen bei Detailwünschen (Farbgebung, Abstände, Reihenfolge von Head-to-Head relativ zu "Vorhersage" und "Team-Vergleich").

**Eigene Entscheidungen:**
Team-Vergleich (konkrete Statistik-Werte nebeneinander) bewusst der abstrakteren Feature-Importance-Darstellung vorgezogen, da für einen Dashboard-Nutzer ohne ML-Hintergrund deutlich verständlicher.

**Probleme:**
Bei einer Zwischenversion wurde `flag_url()` versehentlich beim Einfügen einer neuen Funktion überschrieben – bemerkt und korrigiert. Head-to-Head-Anzeige kurzzeitig doppelt im Dashboard (einmal direkt nach der Vorhersage, einmal im Team-Vergleich) – auf eine einzige Stelle reduziert.

**Outcome:**
Dashboard zeigt jetzt: grosse Team-Flaggen, farblich codierte Vorhersage, Head-to-Head als Chart, direkter Stat-für-Stat-Vergleich beider Teams mit hervorgehobenem jeweils besserem Wert, sowie eine klar formatierte Erklärung der EWMA-Methodik.

---

### 15.07.2026 – Refresh-Funktion für aktuelle Saison

**Modell:** Claude

**Prompt:**
Nachgefragt, ob ein erneuter Lauf von `fetch_data.py` automatisch die neuesten (laufenden) WM-2026-Spiele nachholen würde.

**Übernommen / angepasst / verworfen:**
Festgestellt, dass das bisherige Skript pro Team überspringt, sobald die Datei existiert – ein erneuter Lauf hätte also nichts Neues geholt. Neue Funktion `refresh_current_season()` von Claude vorgeschlagen und übernommen: ruft gezielt nur die aktuelle Saison (2026) ab und merged neue Spiele (dedupliziert über Fixture-ID) in die bestehende Datei, ohne die vorhandene Historie zu löschen. Aufruf über neues CLI-Flag `--refresh`.

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Merge-Logik isoliert getestet (Duplikat-Erkennung, neues Spiel wird hinzugefügt, alte Historie bleibt erhalten). Nach `refresh_current_season()` wird automatisch `fetch_all_match_stats()` mit aufgerufen, damit auch die Statistiken zu neu gefundenen Spielen nachgeladen werden.

---

### 15.07.2026 – Hover-Tooltips für Form-Kacheln und H2H-Detailliste

**Modell:** Claude

**Prompt:**
Gewünscht, dass beim Hovern über die Form-Kacheln (letzte 5 Spiele) Resultat und Gegner angezeigt werden, sowie dass bei Head-to-Head zusätzlich sichtbar wird, wie die einzelnen Duelle effektiv ausgegangen sind (nicht nur die aggregierte Bilanz).

**Übernommen / angepasst / verworfen:**
`build_team_match_history()` in `build_features.py` um das Feld `opponent_name` (roher API-Gegnername, auch für Nicht-WM-2026-Teams) ergänzt. Neue Funktion `get_h2h_matches()` liefert die einzelnen H2H-Spiele statt nur der aggregierten Zahlen. Im Dashboard: `get_last_n_results()` gibt jetzt volle Spieldaten statt nur Punkte zurück, `form_tiles()` baut daraus ein `title`-Attribut (HTML-Tooltip) mit Datum, Resultat und Gegner. `render_h2h()` zeigt zusätzlich einen ausklappbaren Bereich mit allen Einzelduellen (Datum, Resultat, Ampel-Symbol).

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Änderungen gegen Mock-Daten getestet (opponent_name korrekt befüllt, H2H-Einzelspiele korrekt gefunden, Form-Liste mit vollständigen Details). Keine Änderung an `match_features.csv` oder den trainierten Modellen nötig, da das neue Feld nur für die Dashboard-Anzeige verwendet wird, nicht als Modell-Feature.