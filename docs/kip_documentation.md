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

---

### 15.07.2026 – Recherche: Offizielle Achtelfinal-Zuordnungsregeln (Annex C + Basisstruktur)

**Modell:** Claude

**Prompt:**
Für die Monte-Carlo-Turniersimulation gefragt, wie die Achtelfinal-Zuordnung der Drittplatzierten funktioniert. Nach anfänglicher Vereinfachungs-Idee (zufällige Zuordnung) PDF-Seiten von "Annex C" (495 Kombinationen für die 8 besten Drittplatzierten) sowie strukturierte JSON-Versionen von Annex B (Fairplay-Reglement) und Annex C bereitgestellt.

**Übernommen / angepasst / verworfen:**
Annex-C-JSON (495 Zeilen, je mit `qualified_groups`-Schlüssel und Zuordnung der 8 Sieger-Slots zu Drittplatzierten-Gruppen) direkt übernommen – exakte offizielle Regel statt Vereinfachung. Für die übrigen 8 Achtelfinal-Spiele (Gruppensieger C/F/H/J vs. Gruppenzweite, Zweiter-vs-Zweiter) selbständig über Wikipedia-Gruppenseiten und tatsächlich gespielte Partien recherchiert und verifiziert (Sieger C ↔ Zweiter F, Sieger H ↔ Zweiter J als "Swap"-Paare; Zweiter A↔B, D↔G, E↔I, K↔L).

**Eigene Entscheidungen:**
Offizielles FIFA-Regularien-PDF blockierte automatisierten Zugriff (robots.txt) – bewusst auf Sekundärquellen (Wikipedia-Gruppenseiten, CBS/Yahoo-Artikel mit echten Spielresultaten) als Kreuzvalidierung ausgewichen, statt die Suche abzubrechen oder ungeprüft zu raten.

**Probleme:**
Erste zwei PDF-Uploads von Annex C enthielten nur Optionen 1–279 von 495 (unvollständig) – erst der dritte Upload (bzw. die JSON-Version) deckte alle 495 Kombinationen ab.

**Outcome:**
Vollständige, verifizierte Basis für die Achtelfinal-Struktur: 8 Spiele exakt nach Annex C, 8 Spiele nach recherchierter Grundstruktur. Einzige verbleibende, dokumentierte Vereinfachung: die Verknüpfung Achtelfinale→Viertelfinale→Halbfinale→Finale folgt einer plausiblen Standard-Reihenfolge, da das offizielle Bracket-PDF nicht abrufbar war.

---

### 15.07.2026 – Monte-Carlo-Turniersimulation gebaut (simulate_tournament.py)

**Modell:** Claude

**Prompt:**
Aufbau der vollständigen Turniersimulation (Gruppenphase bis Final) angefordert, inkl. Klärung, wie Unentschieden in K.o.-Spielen zu behandeln sind.

**Übernommen / angepasst / verworfen:**
Neues Skript `simulate_tournament.py` von Claude vorgeschlagen und übernommen:

* Gruppenphase: Round-Robin-Simulation mit echten FIFA-Tiebreakern (Punkte → Tordifferenz → Tore → Ranking)
* Drittplatzierten-Ranking über alle 12 Gruppen, Nachschlagen der exakten Achtelfinal-Zuordnung via Annex-C-JSON
* K.o.-Runden (Achtelfinale bis Finale) über Wahrscheinlichkeiten neu skaliert ohne Unentschieden-Anteil (P(A)/(P(A)+P(B))) – meine eigene Idee, sauberer als eine Neusimulation bei Unentschieden oder ein reiner Münzwurf
* Team-Formkurve/Ranking werden einmalig vor Turnierbeginn berechnet und über die gesamte Simulation konstant gehalten (Performance, dokumentierte Vereinfachung)

**Eigene Entscheidungen:**
Vorschlag, bei Unentschieden einfach so lange zu simulieren, bis kein Unentschieden mehr kommt, verworfen zugunsten der mathematisch saubereren Neuskalierung – nutzt weiterhin die relative Stärkeeinschätzung des Modells statt eines reinen Zufalls-Münzwurfs.

**Probleme:**
–

**Outcome:**
Struktur-Tests bestanden (12 Gruppen, 495 Annex-C-Kombinationen, korrekte Tiebreaker-Sortierung anhand eines Beispiels). Zusätzlich 21 komplette Turnier-Durchläufe mit Dummy-Modellen für alle 48 Teams getestet (unterschiedliche zufällige Drittplatzierten-Kombinationen) – durchgehend fehlerfrei, keine Duplikate im Achtelfinale, kein fehlender Annex-C-Eintrag.


---

### 18.07.2026 – Monte-Carlo-Simulation ins Dashboard integriert

**Modell:** Claude

**Prompt:**
Gewünscht, die Turniersimulation ins Dashboard einzubauen mit einem Umschalter oben ("Team-Vorhersage" / "Turnier-Simulation").

**Übernommen / angepasst / verworfen:**
Festgestellt, dass die Dashboard-Integration bereits grösstenteils vorhanden war (offenbar eigenständig zwischenzeitlich weiterentwickelt), aber einen Import-Bug enthielt (`import simulate_tournament as sim` statt des tatsächlichen Dateinamens `monte_carlo_simulation.py`) – korrigiert. Zusätzlich `monte_carlo_simulation.py` um Speicherung der Ergebnisse als JSON (`data/processed/tournament_simulation.json`) ergänzt.

**Eigene Entscheidungen:**
–

**Probleme:**
Import-Namenskonflikt zwischen Dateiname und Modul-Import-Statement – hätte bei Ausführung zu `ModuleNotFoundError` geführt.

**Outcome:**
Dashboard-Integration mit Dummy-Modellen für alle 48 Teams getestet (identische Funktionsaufruf-Kette wie im echten Dashboard-Code) – lief fehlerfrei durch.

---

### 18.07.2026 – Team-Verlauf-Feature: einzelnes Team durch Turnier verfolgen

**Modell:** Claude

**Prompt:**
Gewünscht, ein Team eingeben zu können und den kompletten Spielverlauf (inkl. Resultate) für die WM zu sehen, sowie die Anzahl Simulationen (1–1000) wählbar zu machen.

**Übernommen / angepasst / verworfen:**
`simulate_tournament()` in `monte_carlo_simulation.py` erweitert: liefert jetzt zusätzlich `group_match_details` (alle Gruppenspiele mit Resultat) und `knockout_details` (jedes K.o.-Spiel mit Resultat + Sieger) zurück. Neue Dashboard-Ansicht "Team im Detail verfolgen": bei 1 Simulation kompletter Spielverlauf (Gruppenspiele, Tabellenplatz, K.o.-Runden bis Ausscheiden/Titel), bei mehreren Simulationen aggregierte Prozentzahlen pro Phase plus ein Beispiel-Verlauf aus der letzten Simulation.

**Eigene Entscheidungen:**
Bei mehreren Simulationen bewusst zusätzlich einen "Beispiel-Turnierverlauf" ergänzt (nicht nur Prozentzahlen), um die abstrakten Zahlen greifbarer zu machen.

**Probleme:**
–

**Outcome:**
Logik mit Dummy-Modellen getestet (30 Simulationen für Canada): Prozentzahlen sinken plausibel von Runde zu Runde (90% → 57% → 33% → 10% → 7% → 0%). Beispiel-Verlauf zeigt korrekt Gruppenspiele → K.o.-Runden → Ausscheiden.

---

### 18.07.2026 – Echtes WM-2026-Resultat zur Vorhersage anzeigen

**Modell:** Claude

**Prompt:**
Gewünscht, dass bei der Team-Vorhersage zusätzlich angezeigt wird, falls die gewählten zwei Teams während der laufenden WM 2026 tatsächlich gegeneinander gespielt haben, inkl. echtem Resultat.

**Übernommen / angepasst / verworfen:**
Neue Funktion `find_actual_wm2026_results()` in `dashboard.py`: lädt die volle Spielhistorie (inkl. WM-2026-Spiele) und filtert nach Duellen ab dem Cutoff-Datum (`WM2026_START_DATE`). Bei Treffer erscheint eine Info-Box mit Datum und echtem Resultat direkt unter der Vorhersage.

**Eigene Entscheidungen:**
Funktioniert unabhängig vom WM-2026-Toggle (der nur die Formkurve-Berechnung steuert) – die Prüfung auf ein tatsächlich gespieltes Duell läuft immer im Hintergrund mit.

**Probleme:**
–

**Outcome:**
Mit einem simulierten WM-2026-Spiel (Canada vs. Mexico, 2:2) getestet – Funktion erkennt das Spiel korrekt und liefert das exakte Resultat zurück.

---

### 18.07.2026 – Ästhetische Überarbeitung der Team-Verlauf-Ansicht

**Modell:** Claude

**Prompt:**
Gewünscht, die Team-Verlauf-Ansicht optisch zu verbessern: klare Abgrenzung Gruppenphase/K.o.-Phase, kleine Flaggen einblenden, Sieger grün markieren.

**Übernommen / angepasst / verworfen:**
`render_team_journey()` komplett überarbeitet: farbig hinterlegte Abschnitts-Header ("📋 GRUPPENPHASE", "⚽ K.O.-PHASE"), kleine Flaggen-Icons bei jedem Team (Tabelle und Spielzeilen), Sieger grün/fett hervorgehoben, jede Spielzeile als eigene leicht abgesetzte Box statt Fliesstext.

**Eigene Entscheidungen:**
Bei Unentschieden in der Gruppenphase bewusst keine Seite grün markiert (nur bei echtem Sieger).

**Probleme:**
–

**Outcome:**
Syntax geprüft, konsistent mit bereits bestehendem Flaggen-/Farb-Schema aus der Team-Vorhersage-Ansicht.¨


---


### 18.07.2026 – Formatierung der Team-Verlauf-Ansicht verfeinert

**Modell:** Claude

**Prompt:**
Mehrere Feinschliff-Wünsche zur Team-Verlauf-Ansicht (Screenshot-basiert):
- Gruppenphase-Pfad (Tabellen-Kette) stärker abgrenzen
- Spielzeilen "Team vs. Team - Punktestand" besser formatieren
- Bei der aggregierten Mehrfach-Simulationsansicht: Tabelle unter dem Chart entfernen, nur Plot mit Titel und klaren Kurzbeschriftungen (Gruppenphase/Achtelfinale/Viertelfinale/Halbfinale/Finale), eventuell Linienplot mit Wahrscheinlichkeits-Beschriftung pro Datenpunkt statt Balkendiagramm

**Übernommen / angepasst / verworfen:**
- `match_line()` auf CSS-Grid-Layout umgestellt (`grid-template-columns: 1fr auto 1fr`): Team links rechtsbündig, Score fett zentriert in der Mitte, Team rechts linksbündig – unabhängig von Namenslänge exakt ausgerichtet
- Gruppentabellen-Kette in eigenen Kasten gepackt (blauer linker Rahmen, dezenter Hintergrund, Label "Tabelle:")
- Beide Abschnitts-Header (Gruppenphase/K.o.-Phase) auf einheitliche Farbe vereinheitlicht
- Aggregierte Mehrfach-Simulationsansicht: `st.dataframe`-Tabelle entfernt, Balkendiagramm durch Altair-Linienchart mit Datenpunkten und direkt darüber platzierten Prozent-Beschriftungen ersetzt, Titel "Wahrscheinlichkeit je Turnierphase", kürzere Phasen-Labels

**Eigene Entscheidungen:**
Titel bewusst nicht "Sieg-Wahrscheinlichkeit" genannt (wie ursprünglich vorgeschlagen), sondern "Wahrscheinlichkeit je Turnierphase" – da es inhaltlich nicht um eine einzelne Sieg-Chance geht, sondern um das Erreichen verschiedener Turnierrunden.

**Probleme:**
–

**Outcome:**
Syntax geprüft; visuelle Konsistenz mit dem bereits etablierten Flaggen-/Farb-Schema aus der Team-Vorhersage-Ansicht hergestellt.

---

### 18.07.2026 – "Top-Teams gesamt" grundlegend überarbeitet (3 neue Abschnitte)

**Modell:** Claude

**Prompt:**
Rückmeldung, dass die bisherige "Top-Teams gesamt"-Ansicht (Balkendiagramm, eine Phase nach der anderen per Dropdown) nicht überzeugt. Nach Ideen für eine sinnvollere Darstellung gefragt.

**Übernommen / angepasst / verworfen:**
Drei vorgeschlagene Ideen alle übernommen und umgesetzt:

1. **Gesamtübersicht**: Tabelle mit Top 15 (sortiert nach Weltmeister-%), Flaggen-Spalte, alle 5 Phasen nebeneinander mit eingebauten Fortschrittsbalken (`st.column_config.ProgressColumn`) statt Balkendiagramm-Umschalten
2. **Überraschungen**: Vergleich simulierte Performance vs. Elo-Ranking-Erwartung – Top 5 Über- und Top 5 Unterperformer (Differenz aus Elo-Rang und Simulations-Rang)
3. **Gruppen-Ansicht**: Gruppe wählbar, zeigt pro Team die Wahrscheinlichkeit für Platz 1–4 innerhalb der Gruppe

`run_tournament_simulations()` dafür erweitert: neuer Zähler `group_advanced` (Teams, die die Gruppenphase überstehen) sowie `group_rank_counts` (Platzierungs-Historie pro Team innerhalb der eigenen Gruppe).

**Eigene Entscheidungen:**
Für die "Überraschungen"-Metrik einen einfachen Summen-Score (Anzahl Vorkommen über alle Phasen hinweg) als Simulations-Rang-Grundlage gewählt, statt nur einer einzelnen Phase – differenziert auch schwächere Teams besser als z.B. reine Weltmeister-Wahrscheinlichkeit (die für viele Teams bei 0 läge).

**Probleme:**
–

**Outcome:**
Neue Zähler-Logik mit Dummy-Modellen getestet: `group_advanced` plausibel begrenzt, Elo-Rang/Sim-Rang vollständig für alle 48 Teams, Gruppenplatzierungs-Summe pro Team korrekt gleich der Anzahl Simulationen.


---


### 18.07.2026 – Gesamtübersicht-Tabelle kompakter, Simulationsbereich reduziert

**Modell:** Claude

**Prompt:**
Rückmeldung, dass die Gesamtübersicht-Tabelle sowohl vertikal als auch horizontal gescrollt werden musste. Gewünscht: nur Top 10 statt 15 anzeigen, sowie den Simulations-Slider (wegen Ladezeit) auf 10–1000 in 10er-Schritten eingrenzen statt 100–5000 in 100er-Schritten.

**Übernommen / angepasst / verworfen:**
Tabelle auf Top 10 reduziert, feste Höhe (`height=386`, exakt 10 Zeilen + Header) gesetzt, um vertikales Scrollen zu vermeiden. Alle Spalten auf `width="small"` gesetzt und Spalten-Labels gekürzt (z.B. "AF"/"VF"/"HF"/"WM" statt ausgeschriebener Phasennamen), um horizontales Scrollen zu vermeiden. Slider-Range von `100–5000 (Schritt 100)` auf `10–1000 (Schritt 10)` geändert, Default-Wert auf 100 gesenkt.

**Eigene Entscheidungen:**
–

**Probleme:**
–

**Outcome:**
Tabelle sollte jetzt ohne Scrollen in beide Richtungen sichtbar sein; falls je nach Bildschirmbreite immer noch horizontales Scrollen nötig ist, wäre der nächste Schritt, zusätzlich einzelne Phasen-Spalten (z.B. Halbfinale) wegzulassen.

---

### 20.07.2026 – Modellvergleich: Random Forest vs. Logistic Regression vs. Gradient Boosting

**Modell:** Claude

**Prompt:**
Umsetzung des Stretchgoals "Modellvergleich" aus dem Exposé angefordert.

**Übernommen / angepasst / verworfen:**
Neues Skript `compare_models.py` von Claude vorgeschlagen und übernommen: trainiert Random Forest (bestehendes Modell), Logistic Regression und Gradient Boosting auf identischen Trainingsdaten (gleicher chronologischer Split, gleiche Median-Imputation, zusätzlich Standardisierung der Features für die Logistic Regression). Gibt pro Modell Accuracy, F1 (macro), Classification Report und Confusion Matrix aus, plus eine sortierte Zusammenfassungstabelle am Ende. Ergebnisse werden zusätzlich als `models/model_comparison.json` gespeichert.

**Eigene Entscheidungen:**
Alle drei Modelle bewusst auf denselben (skalierten) Eingabedaten trainiert, obwohl Random Forest/Gradient Boosting skaleninvariant sind und die Standardisierung nicht bräuchten – so bleibt der Vergleich sauber nachvollziehbar (identische Datenbasis für alle drei), statt pro Modell unterschiedliche Preprocessing-Pipelines zu verwenden.

**Probleme:**
`LogisticRegression(multi_class="multinomial")` führte zu `TypeError` – der Parameter wurde in neueren scikit-learn-Versionen entfernt, da multinomiale Regression bei mehreren Klassen inzwischen automatisch verwendet wird. Behoben durch Entfernen des Parameters.

**Outcome:**
Mit Mock-Daten (300 Zeilen) getestet, lief nach dem Fix fehlerfrei durch. Auf den Mock-Daten schnitt Random Forest am besten ab (Accuracy 0.533), gefolgt von Gradient Boosting (0.483) und Logistic Regression (0.433) – Ergebnis auf den echten Daten steht noch aus.

---

### 20.07.2026 – Notebook-Reorganisation: Modellvergleich als abschliessender Abschnitt

**Modell:** Claude

**Prompt:**
Ursprünglichen Vorschlag (Modellvergleich direkt nach Model Evaluation, vor Live-Vorhersage) verworfen zugunsten einer anderen Reihenfolge: Live-Vorhersage bleibt an ihrem angestammten Platz (Abschnitt 6), Modellvergleich wird als abschliessender Abschnitt 7 angehängt, mit der Rahmung "zu guter Letzt wurde geprüft, ob ein anderes Modell signifikant besser wäre – Ergebnis: nein".

**Übernommen / angepasst / verworfen:**
Notebook-Struktur entsprechend umgebaut: Abschnitte 1–6 unverändert aus der bestehenden Datei übernommen, neuer Abschnitt 7 (Modellvergleich, Unterabschnitte 7.1–7.3) ans Ende gehängt.

**Eigene Entscheidungen:**
–

**Probleme:**
Beim ersten Umbau-Versuch (Zellen per Slicing neu anordnen) wurde versehentlich eine bereits verfälschte Zwischenversion der Datei als Ausgangspunkt verwendet, was zu einer fehlerhaften, teils duplizierten Zellstruktur führte. Bemerkt, verworfen, und stattdessen sauber direkt von der ursprünglichen Upload-Datei neu aufgebaut.

**Outcome:**
JSON-Struktur geprüft (25 Zellen, korrekte Reihenfolge 1–7 mit korrekter Nummerierung). Alle drei neuen Code-Zellen des Modellvergleichs-Abschnitts erneut end-to-end getestet – liefen fehlerfrei durch.