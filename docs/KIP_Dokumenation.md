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

**Outcome + eigen Verständnis:** 
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
Klassisches Windows-Problem: `write_text()` nutzt ohne explizite Angabe die Systemkodierung `cp1252`. Diese kann Sonderzeichen wie `ć`, beispielsweise in Namen wie „Kovačić“, nicht darstellen.

Fix: Überall explizit `encoding="utf-8"` angeben.

**Outcome + eigenes Verständnis:**
Die gewünschten Dateien wurden erstellt. Der Codeinhalt wurde von mir geprüft und ist schlüssig.

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

**Outcome + eigenes Verständnis:**
Die Rohdaten bleiben in `data/raw/` unverändert und vollständig. Der Filter wird erst bei der Nutzung angewendet, beispielsweise beim Feature Engineering oder später über einen Dashboard-Toggle, und nicht bereits beim Datenabruf.

Dadurch ist kein erneuter Datenabruf notwendig, wenn WM-2026-Spiele später einbezogen oder ausgeschlossen werden sollen.

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

**Outcome + eigenes Verständnis:**
Ich verstehe, weshalb die Deduplizierung anhand der Fixture-IDs notwendig ist. Ohne diese würden für dasselbe Spiel doppelte Requests durchgeführt.

Das Skript wurde zusätzlich robuster gestaltet:

* Leere oder beschädigte Dateien werden mit einer Warnung übersprungen, statt dass das Skript abstürzt.
* Das Skript ist wie das Fetch-Skript resumable, falls das tägliche API-Limit erreicht wird.

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

**Outcome + eigenes Verständnis:**
Das Skript ermöglicht jederzeit einen schnellen Überblick über den Fortschritt der Datenpipeline, ohne dass einzelne Dateien manuell durchsucht werden müssen.

Aktueller Stand:

* 47 von 48 Teams
* 4'611 eindeutige Fixtures
* Match-Statistik-Fortschritt in Prozent

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

**Outcome + eigenes Verständnis:**
Ich verstehe, weshalb eine Statistik nur dann als vorhanden gelten darf, wenn beide Teams einen Wert besitzen. Andernfalls lässt sich beispielsweise keine Differenz zwischen den Teams berechnen.

Gerade bei kleineren Nationen und Freundschaftsspielen sind Datenlücken zu erwarten. Die Feature-Auswahl sollte deshalb datenbasiert erfolgen, anstatt unverändert aus dem Exposé übernommen zu werden.

---

### 14.07.2026 – Feature Engineering: Formkurve, H2H, Elo-Differenz, Match-Stats

**Modell:** Claude

**Prompt:**
Wunsch geäussert, das Feature Engineering als sauberes Skript (nicht als Notebook) umzusetzen. Vorgabe gemacht, dass Features pro Spiel ausschliesslich aus Daten vor dem jeweiligen Spieldatum berechnet werden dürfen (kein Data Leakage). Formkurve-Fenster auf die letzten 5 Spiele festgelegt.

**Übernommen / angepasst / verworfen:**
Das neue Skript `build_features.py` wurde von Claude vorgeschlagen und übernommen.

Das Skript baut pro Team eine chronologische Spielhistorie auf, identifiziert alle Spiele zwischen zwei WM-2026-Teams und berechnet pro Spiel:

* Formkurve (Punkte aus den letzten 5 Spielen)
* Tordurchschnitt (geschossen/kassiert)
* Head-to-Head-Bilanz
* Elo-Rating-Differenz (inkl. Namens-Mapping zwischen unserer Team-Liste und der Elo-CSV, z. B. "USA" vs. "United States")
* Ballbesitz-, Schuss- und Eckball-Schnitt (wo Daten vorhanden)

Das Ergebnis wird als `data/processed/match_features.csv` gespeichert.

**Eigene Entscheidungen:**
Formkurve-Fenster bewusst auf 5 Spiele festgelegt (nicht 10 oder 15), um einen Kompromiss zwischen Aktualität und genügend Stichprobengrösse zu haben.

**Probleme:**
–

**Outcome + eigenes Verständnis:**
Ich verstehe, weshalb Features nur aus Daten vor dem jeweiligen Spieldatum berechnet werden dürfen, da sonst das Modell mit Zukunftswissen trainiert würde, das bei echten Vorhersagen nicht existiert (Data Leakage).

Die Logik wurde von Claude an einem kleinen Beispiel-Datensatz (Canada vs. Mexico) durchgerechnet und manuell verifiziert, bevor das Skript auf die echten Daten angewendet wurde.


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

**Outcome + eigenes Verständnis:**
Verstehe, dass Encoding-Fixes an mehreren Stellen im Code konsistent nachgezogen werden müssen, wenn dieselbe Datei (`fixtures_*.json`) von mehreren Skripten (`fetch_match_stats.py`, `data_utils.py`) gelesen wird – ein Fix an einer Stelle reicht nicht automatisch für alle.

---
