# KIP-Entwicklungsdokumentation – WM 2026 Predictor

**Autor:** Rodrigo Urech  
**Modul:** KIP – KI-gestütztes Programmieren  
**Primär verwendete Werkzeuge:** Claude, Claude Code in VS Code

---


### Schema der Einträge

Jeder relevante Entwicklungsschritt wird nach demselben Muster dokumentiert:

1. **Ausgangslage und Ziel**
2. **KI-Einsatz**
3. **Prüfung der KI-Ausgabe**
4. **Entscheidung und Umsetzung**
5. **Ergebnis und Reflexion**



---

# Phase 1 – Projektaufbau und Datenbeschaffung

## 09.07.2026 – Projektstruktur und erste Datenpipeline

### Ausgangslage und Ziel

Gemäss Exposé sollte zunächst eine reproduzierbare Grundlage für den Datenabruf entstehen. Benötigt wurden:

- eine zentrale Konfiguration,
- ein Abrufskript für historische Länderspiele,
- eine sichere Verwaltung des API-Schlüssels,
- und eine dokumentierte Python-Umgebung.

### KI-Einsatz

Claude erhielt den Auftrag, ausgehend vom Exposé eine erste Projektstruktur mit `config.py`, `fetch_data.py` und `requirements.txt` zu erstellen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- ob der API-Key nicht direkt im Code gespeichert wird,
- ob die Teamliste alle vorgesehenen WM-2026-Teams enthält,
- ob pro Team eine lokale JSON-Datei entsteht,
- und ob fehlgeschlagene Requests nachvollziehbar behandelt werden.

Die von Claude erstellte Teamliste wurde stichprobenartig kontrolliert.

### Entscheidung und Umsetzung

- `config.py`: übernommen
- `fetch_data.py`: übernommen und anschliessend weiterentwickelt
- `requirements.txt`: übernommen
- direkte Speicherung des API-Keys im Code: nicht verwendet


Ich erstellte die `.env`-Datei selbst und nahm sie über `.gitignore` vom Repository aus. Zudem verwendete ich API-Football direkt über `api-football.com` statt über RapidAPI.

### Problem

Unter Windows verwendete `write_text()` ohne explizite Angabe teilweise `cp1252`. Dadurch konnten Namen mit Sonderzeichen wie `Kovačić` nicht zuverlässig gespeichert werden.

### Ergebnis und Reflexion

Die Dateien wurden erfolgreich erzeugt. Schreibvorgänge wurden explizit auf UTF-8 umgestellt.


Der erste KI-Vorschlag war funktional, berücksichtigte aber die lokale Encoding-Umgebung nicht ausreichend. Daraus entstand früh die Erkenntnis, dass plattformabhängige Details auch bei plausibel wirkendem Code selbst geprüft werden müssen.

---

## 10.07.2026 – Zeitliche Trennung der WM-2026-Daten

### Ausgangslage und Ziel

Während der Entwicklung sollte wählbar sein, ob bereits ausgetragene Spiele der WM 2026 in die Formberechnung einfliessen. Gleichzeitig sollten die Rohdaten unverändert bleiben.

### KI-Einsatz

Claude wurde gebeten, einen Toggle einzubauen, der Spiele ab dem 19.06.2026 optional ausschliesst.

### Prüfung der KI-Ausgabe

Ich prüfte, ob:

- die Rohdaten unverändert bleiben,
- der Filter erst beim Laden oder beim Feature Engineering greift,
- und der gleiche Datenbestand sowohl für eine historische als auch für eine aktualisierte Vorhersage verwendet werden kann.

### Entscheidung und Umsetzung

Die vorgeschlagenen Funktionen `load_team_fixtures()` und `filter_fixtures()` wurden übernommen. Später wurden sie im Rahmen der Skript-Konsolidierung direkt in `build_features.py` integriert.


Der Filter wurde bewusst nicht in den Datenabruf eingebaut. Damit bleibt die Rohdatenbasis vollständig und die Entscheidung wird erst bei der Analyse getroffen.

### Ergebnis und Reflexion

WM-2026-Spiele lassen sich ein- oder ausschliessen, ohne Daten erneut abzurufen.


Die Trennung zwischen Rohdaten und analytischer Filterung verbessert Nachvollziehbarkeit und Reproduzierbarkeit. Die KI unterstützte die technische Umsetzung; die Entscheidung über den Ort des Filters war eine Architekturentscheidung.

---

## 10.07.2026 – Erweiterung um Match-Statistiken

### Ausgangslage und Ziel

Das Exposé sah zunächst hauptsächlich Resultate, Form, direkte Duelle und Rankingdaten vor. Durch das Pro-Abonnement waren zusätzlich Statistiken wie Ballbesitz, Schüsse und Eckbälle verfügbar.

### KI-Einsatz

Claude wurde beauftragt, ein Skript zu erstellen, das für alle eindeutigen Fixture-IDs Match-Statistiken über den Endpoint `/fixtures/statistics` abruft.

### Prüfung der KI-Ausgabe

Ich kontrollierte insbesondere:

- ob Spiele zwischen zwei WM-Teams doppelt vorkommen,
- ob Fixture-IDs vor dem Abruf dedupliziert werden,
- ob bereits vorhandene Statistikdateien übersprungen werden,
- und ob ein abgebrochener Lauf fortgesetzt werden kann.

### Entscheidung und Umsetzung

Das Skript `fetch_match_stats.py` wurde übernommen. Die Speicherung pro Fixture unter `data/raw/stats/{fixture_id}.json` wurde beibehalten.


Die Daten wurden pro Fixture statt pro Team gespeichert. Dadurch ist jedes Spiel genau einer Statistikdatei zugeordnet.

### Ergebnis und Reflexion

Der Abruf wurde resumierbar umgesetzt und übersprang leere oder beschädigte Dateien kontrolliert.


Die KI lieferte schnell eine funktionierende Erweiterung. Der fachlich relevante Kontrollpunkt war jedoch die Granularität: Ohne Deduplizierung wären Spiele zweier WM-Teams doppelt verarbeitet worden.

---

# Phase 2 – Datenkontrolle und Feature-Auswahl

## 13.07.2026 – Statuskontrolle der Datenpipeline

### Ausgangslage und Ziel

Bei mehreren Tausend Spielen und API-Limits war der Fortschritt des Datenabrufs nicht ausreichend sichtbar. Es wurde eine Kontrolle pro Team benötigt.

### KI-Einsatz

Claude wurde beauftragt, einen Status-Check mit Anzahl Spielen, vorhandenen Statistikdateien und Fortschritt in Prozent zu erstellen.

### Prüfung der KI-Ausgabe

Ich verglich die Anzahl eindeutiger Fixture-IDs mit den lokal vorhandenen Dateien und prüfte leere Dateien separat.

### Entscheidung und Umsetzung

`check_status.py` wurde übernommen und später in das Diagnose-Notebook integriert.

### Problem

Die Datei `fixtures_Mexico.json` war 0 Byte gross. Sie stammte aus einem abgebrochenen Lauf und wäre ohne Statusprüfung unbemerkt geblieben.

### Ergebnis und Reflexion

Der fehlende Datensatz wurde gezielt neu geladen. Der Status-Check zeigte 4’611 eindeutige Fixtures und den Abruffortschritt pro Team.


Eine Pipeline kann ohne Fehlermeldung unvollständige Resultate erzeugen. Die Kontrolle von Dateiexistenz allein reicht deshalb nicht; auch Dateigrösse und Inhalt müssen plausibilisiert werden.

---

## 13.07.2026 – Datenbasierte Auswahl zusätzlicher Features

### Ausgangslage und Ziel

Nicht jede über API-Football verfügbare Statistik ist für genügend Spiele vorhanden. Die Feature-Auswahl sollte daher nicht allein nach inhaltlicher Attraktivität erfolgen.

### KI-Einsatz

Claude wurde gebeten, die Abdeckung verschiedener Statistiktypen zu analysieren.

### Prüfung der KI-Ausgabe

Ich prüfte, ob nur Spiele gezählt werden, bei denen für beide Teams ein verwertbarer Wert vorliegt. Die Ausgabe wurde nach Abdeckungsgrad sortiert.

### Entscheidung und Umsetzung

Das Skript `analyze_stats_coverage.py` wurde übernommen und später in das Diagnose-Notebook überführt.


Die Erweiterung des MVP wurde nur für ausreichend abgedeckte Werte weiterverfolgt. Ballbesitz, Schüsse und Eckbälle wurden berücksichtigt; schwächer abgedeckte Statistiken nicht.

### Ergebnis und Reflexion

Die Feature-Auswahl wurde auf Basis der tatsächlichen Datenqualität getroffen.


Die KI half bei der technischen Analyse. Die Auswahl der Features blieb jedoch eine fachliche Entscheidung. Ein zusätzliches Feature ist nicht automatisch nützlich, nur weil es technisch verfügbar ist.

---

## 14.07.2026 – Diagnosefunktionen in einem Notebook gebündelt

### Ausgangslage und Ziel

Mit `check_status.py`, `analyze_stats_coverage.py` und `quick_check_features.py` entstanden mehrere kleine Kontrollskripte. Diese waren keine Bestandteile der produktiven Pipeline.

### KI-Einsatz

Claude wurde beauftragt, die Diagnosefunktionen in einem Notebook zusammenzuführen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- die JSON-Struktur des Notebooks,
- die Importpfade zu `src/`,
- und ob die Resultate mit den bisherigen Einzelskripten übereinstimmen.

### Entscheidung und Umsetzung

Das Notebook wurde übernommen. Die drei Einzelskripte wurden anschliessend entfernt.


Produktive Schritte blieben als Python-Skripte bestehen; explorative Kontrollen wurden in ein Notebook ausgelagert.

### Ergebnis und Reflexion

Es entstand eine klarere Trennung zwischen:

- reproduzierbarer Pipeline,
- explorativer Analyse,
- Modellvalidierung,
- und Demonstration einzelner Vorhersagen.


Die Zusammenführung reduzierte Komplexität, ohne fachliche Logik zu verändern. KI wurde hier gezielt für Refactoring verwendet, nicht für eine neue fachliche Entscheidung.

---

# Phase 3 – Feature Engineering

## 14.07.2026 – Chronologisches Feature Engineering ohne Data Leakage

### Ausgangslage und Ziel

Für jedes historische Spiel sollten Features berechnet werden, die zum damaligen Spielzeitpunkt tatsächlich bekannt gewesen wären.

### KI-Einsatz

Claude erhielt die Vorgabe, ein eigenständiges Skript `build_features.py` zu erstellen. Eine zentrale Anforderung war, dass ausschliesslich frühere Spiele in die Berechnung einfliessen dürfen.

### Prüfung der KI-Ausgabe

Ich kontrollierte:

- die chronologische Sortierung der Spiele,
- die Trennung zwischen Team A und Team B,
- den Ausschluss des aktuellen Spiels aus der Historie,
- das Mapping unterschiedlicher Teamnamen,
- und die berechneten Werte anhand eines Beispiels Canada gegen Mexico.

### Entscheidung und Umsetzung

Folgende Features wurden übernommen:

- Formpunkte,
- geschossene und kassierte Tore,
- direkte Duelle,
- Rankingwerte und Rankingdifferenz,
- Ballbesitz,
- Schüsse,
- Eckbälle.

Identifikatoren und tatsächliche Endresultate wurden ausdrücklich nicht als Modellfeatures verwendet.


Zunächst wurde ein Fenster von fünf Spielen gewählt, um Aktualität und Stichprobengrösse zu verbinden. Diese Entscheidung wurde später aufgrund der Datenlücken revidiert.

### Ergebnis und Reflexion

Die Feature-Tabelle wurde unter `data/processed/match_features.csv` gespeichert.


Die wichtigste Qualitätsanforderung war nicht die Anzahl Features, sondern die zeitliche Korrektheit. Ein Data Leakage hätte zu scheinbar guten, aber unbrauchbaren Modellergebnissen geführt.

---

## 14.07.2026 – Wiederkehrenden Encoding-Fehler systematisch behoben

### Ausgangslage und Ziel

Beim Laden älterer Fixture-Dateien trat erneut ein `UnicodeDecodeError` auf.

### KI-Einsatz

Die Fehlermeldung wurde Claude zur Analyse gegeben.

### Prüfung der KI-Ausgabe

Ich verglich die betroffenen Lesewege und stellte fest, dass der bereits an anderer Stelle ergänzte Fallback in `data_utils.py` fehlte.

### Entscheidung und Umsetzung

Der UTF-8-Leseversuch mit `cp1252`-Fallback wurde übernommen und an allen betroffenen Stellen vereinheitlicht.


Der Fehler wurde nicht nur lokal an einer Datei korrigiert, sondern als wiederkehrendes Problem der gesamten Datenpipeline behandelt.

### Ergebnis und Reflexion

Alte und neue Dateien konnten konsistent eingelesen werden.


Das blosse Kopieren einer Fehlermeldung an die KI löst ein Problem häufig nur lokal. Erst der Vergleich ähnlicher Codepfade zeigte, dass die Ursache systematisch behoben werden musste.

---

## 15.07.2026 – Umstellung von festem Fenster auf EWMA

### Ausgangslage und Ziel

Ein festes Fenster von fünf Spielen erwies sich für Statistiken mit Datenlücken als instabil. Bei einzelnen Teams standen innerhalb des Fensters zu wenige verwertbare Werte zur Verfügung.

### KI-Einsatz

Claude wurde gebeten, Alternativen zu einem festen Fenster zu erläutern und die Berechnung auf einen exponentiell gewichteten Durchschnitt umzustellen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- ob neuere Spiele stärker gewichtet werden,
- ob ältere Spiele weiterhin einen abnehmenden Einfluss behalten,
- ob nur Spiele vor dem Stichtag berücksichtigt werden,
- und ob die Berechnung bei fehlenden Werten stabil bleibt.

### Entscheidung und Umsetzung

Die EWMA-Umsetzung wurde übernommen. Das ursprüngliche Fünf-Spiele-Fenster wurde verworfen.


Die gesamte verfügbare Historie wird verwendet, aber mit abnehmendem Gewicht. Dies reduziert harte Sprünge und nutzt mehr vorhandene Informationen.

### Ergebnis und Reflexion

Die Form- und Statistikfeatures wurden neu erzeugt; beide Modelle mussten danach neu trainiert werden.


Die ursprüngliche Entscheidung war einfach, aber nicht ausreichend robust. Die spätere Umstellung zeigte, dass Feature Engineering stärker von Datenqualität als von einer intuitiven Fenstergrösse abhängt.

---

## 15.07.2026 – Begriffe im Projekt konsolidiert

### Ausgangslage und Ziel

Im Code wurden Elo-spezifische Variablennamen verwendet, obwohl die Oberfläche allgemein von einem Ranking sprach.

### KI-Einsatz

Das Refactoring wurde mit Claude Code direkt im Projekt durchgeführt.

### Prüfung der KI-Ausgabe

Ich prüfte alle Fundstellen in Code, CSV-Headern, Modellmetadaten, Notebook und Dokumentation.

### Entscheidung und Umsetzung

Technische Variablennamen wurden von `elo_*` zu `ranking_*` geändert. Sachlich korrekte Quellenbezeichnungen wie „Historical Elo Ratings“ und der Rohdateiname blieben unverändert.


Nicht jede Fundstelle wurde blind ersetzt. Fachlich echte Elo-Bezüge blieben bestehen.

### Ergebnis und Reflexion

Code und Benutzeroberfläche verwenden konsistentere Begriffe, ohne die Datenquelle falsch umzubenennen.


Automatisiertes Refactoring ist effizient, birgt aber das Risiko inhaltlich falscher Ersetzungen. Deshalb mussten technische Bezeichner und fachliche Aussagen getrennt behandelt werden.

---

# Phase 4 – Modellierung und Evaluation

## 14.07.2026 – Random-Forest-Klassifikator als erstes Kernmodell

### Ausgangslage und Ziel

Das erste Modell sollte drei Klassen vorhersagen:

- Sieg Team A,
- Unentschieden,
- Sieg Team B.

### KI-Einsatz

Claude wurde beauftragt, ein Trainingsskript mit Evaluation und Speicherung der Pipeline zu erstellen.

### Prüfung der KI-Ausgabe

Ich prüfte besonders:

- den chronologischen Train-Test-Split,
- die Median-Imputation ausschliesslich auf Basis des Trainingssets,
- den Ausschluss nicht verfügbarer Ist-Werte,
- die gespeicherte Feature-Liste,
- und die Confusion Matrix.

### Entscheidung und Umsetzung

Übernommen wurden:

- chronologischer Split, letzte 20 % als Testdaten,
- Median-Imputation,
- Random Forest mit 200 Bäumen und begrenzter Tiefe,
- Speicherung von Modell, Imputer und Feature-Liste.

Ein zufälliger Split wurde bewusst nicht verwendet.


Die Zielwerte `goals_a` und `goals_b` sowie Identifikatoren wurden explizit aus dem Feature-Set ausgeschlossen.

### Ergebnis und Reflexion

Das erste Modell erreichte auf dem Testset ungefähr 50 % Accuracy und lag damit über einer einfachen Mehrheitsklassen-Baseline.


Die Gesamt-Accuracy allein war nicht ausreichend. Die klassenweise Auswertung zeigte, dass das Modell Unentschieden nur sehr schwach erkennt.

---

## 14.07.2026 – Schwache Draw-Erkennung als offene Modellgrenze

### Ausgangslage und Ziel

Der Recall für Unentschieden lag deutlich unter dem Recall der beiden Siegklassen.

### KI-Einsatz

Die Resultate wurden mit Claude analysiert und mögliche Ursachen sowie Optimierungen diskutiert.

### Prüfung der KI-Ausgabe

Ich verglich Support und Recall der drei Klassen. Die Draw-Klasse war nur leicht kleiner als die beiden anderen Klassen. Eine reine Klassenimbalance erklärt den tiefen Recall daher nicht vollständig.

### Entscheidung und Umsetzung

Die Schwäche wurde transparent dokumentiert. Eine sofortige umfangreiche Optimierung wurde zunächst zurückgestellt, um den vollständigen MVP fertigzustellen.


Die Draw-Problematik wurde nicht als behobener Punkt dargestellt, sondern als offene Modellgrenze.

### Ergebnis und Reflexion

Das Modell blieb vorerst Bestandteil der Pipeline.


Rückblickend war es zu passiv, die Schwäche nur als „typisches Fussballproblem“ zu akzeptieren. Für eine methodisch stärkere Lösung sollten mindestens einfache Massnahmen wie Klassengewichte, alternative Modelle oder Schwellenwertanalysen systematisch geprüft werden.

---

## 15.07.2026 – Tore-Regressor als Scope-Erweiterung

### Ausgangslage und Ziel

Neben der Ergebnisklasse sollte das Dashboard auch eine erwartete Toranzahl anzeigen.

### KI-Einsatz

Claude wurde beauftragt, einen Multi-Output-Regressor für `goals_a` und `goals_b` zu ergänzen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- identischen zeitlichen Split wie beim Klassifikator,
- identische Imputationslogik,
- separate Speicherung von Modell und Metadaten,
- sowie negative Vorhersagen.

### Entscheidung und Umsetzung

Ein `RandomForestRegressor` wurde übernommen. Eine Poisson-Regression wurde diskutiert, aber zunächst nicht umgesetzt.


Der Regressor ergänzt den Klassifikator und ersetzt ihn nicht. Rohwerte bleiben für die Evaluation ungerundet; Rundung erfolgt nur in der Benutzeroberfläche.

### Ergebnis und Reflexion

Für beide Teams wurden MAE und RMSE berechnet und das Modell gespeichert.


Random Forest wurde aus Konsistenzgründen gewählt. Methodisch wäre für Zähldaten ein Vergleich mit einer Poisson-basierten Lösung sinnvoller gewesen. Diese Einschränkung wird im Bericht offengelegt.

---

## 15.07.2026 – Baselines für die Regressionsmodelle ergänzt

### Ausgangslage und Ziel

Eine Fehlermetrik allein zeigt nicht, ob ein Modell besser als eine triviale Vorhersage ist.

### KI-Einsatz

Mit Claude Code wurde ein Vergleich gegen den Mittelwert der Trainingsdaten ergänzt.

### Prüfung der KI-Ausgabe

Ich kontrollierte, dass:

- die Baseline nur aus Trainingsdaten berechnet wird,
- Modell und Baseline auf denselben Testdaten bewertet werden,
- und negative Torprognosen separat gezählt werden.

### Entscheidung und Umsetzung

Der Baseline-Vergleich wurde übernommen.

### Ergebnis und Reflexion

Das Modell lag bei beiden Zielvariablen unter der Baseline-MAE. Die Verbesserung war jedoch besonders bei Team A nur klein.


„Besser als Baseline“ bedeutet nicht automatisch „gutes Modell“. Die relative Verbesserung muss zusätzlich eingeordnet werden.

---

## 20.07.2026 – Vergleich mehrerer Klassifikationsmodelle

### Ausgangslage und Ziel

Im Exposé war ein Vergleich von Random Forest, logistischer Regression und Gradient Boosting vorgesehen. Dieser Vergleich wurde erst gegen Ende des Projekts durchgeführt.

### KI-Einsatz

Claude erstellte `compare_models.py` mit identischem chronologischem Split und identischer Imputation für alle Modelle. Für die logistische Regression wurde zusätzlich standardisiert.

### Prüfung der KI-Ausgabe

Ich prüfte:

- gleiche Trainings- und Testdaten,
- gleiche Featurebasis,
- Accuracy, Macro-F1 und Draw-Recall,
- Confusion Matrices,
- und die gespeicherte JSON-Zusammenfassung.

Ein Versionsproblem beim veralteten Parameter `multi_class="multinomial"` wurde erkannt und durch Entfernen des Parameters behoben.

### Entscheidung und Umsetzung

Der Vergleich wurde übernommen und als letzter methodischer Abschnitt in das Notebook integriert.

### Ergebnis auf den finalen Daten

| Modell | Accuracy | Macro-F1 | Draw-Recall |
|---|---:|---:|---:|
| Logistic Regression | 0.520 | 0.478 | 0.17 |
| Random Forest | 0.498 | 0.456 | 0.17 |
| Gradient Boosting | 0.472 | 0.423 | 0.14 |

### Entscheidung und Umsetzung

Der Vergleich wurde nicht als Beweis für einen grossen Leistungsunterschied interpretiert. Die logistische Regression schnitt jedoch in Accuracy und Macro-F1 am besten ab und ist deshalb für die finale Modellwahl ernsthaft zu bevorzugen.

### Ergebnis und Reflexion

Der Modellvergleich hätte vor dem Bau des Dashboards stattfinden sollen. So hätte die Architektur von Beginn an auf dem stärksten oder zumindest einfachsten Modell aufgebaut werden können. Die Resultate zeigen zudem, dass komplexere Modelle nicht automatisch bessere Prognosen liefern.

---

# Phase 5 – Projektstruktur und Dashboard

## 15.07.2026 – Kernskripte konsolidiert

### Ausgangslage und Ziel

Im Verlauf des Projekts waren sieben Einzelskripte entstanden. Die Struktur wurde zunehmend schwer überschaubar.

### KI-Einsatz

Claude wurde gebeten, sinnvolle Zusammenlegungen vorzuschlagen.

### Prüfung der KI-Ausgabe

Ich prüfte, ob:

- sich das Verhalten der Pipeline verändert,
- bestehende Daten erneut erzeugt werden müssen,
- Imports weiterhin funktionieren,
- und die Skripte mit Mock-Daten ausführbar sind.

### Entscheidung und Umsetzung

Zusammengeführt wurden:

- `fetch_data.py` und `fetch_match_stats.py`,
- `data_utils.py` und `build_features.py`,
- `train_model.py` und `train_goals_model.py`.

`config.py` blieb als eigenständige Datei bestehen.

### Ergebnis und Reflexion

Die Anzahl Kernskripte sank von sieben auf vier:

- `config.py`
- `fetch_data.py`
- `build_features.py`
- `train_models.py`


Die Konsolidierung verbesserte Übersichtlichkeit. Eine zu frühe Zusammenlegung hätte die Fehlersuche jedoch erschwert; deshalb war der Zeitpunkt nach funktionierenden Einzelkomponenten sinnvoll.

---

## 15.07.2026 – Streamlit-Dashboard als Benutzerschnittstelle

### Ausgangslage und Ziel

Die Modelle sollten über eine einfache Oberfläche nutzbar sein.

### KI-Einsatz

Claude wurde beauftragt, ein Streamlit-Dashboard mit Teamauswahl, Klassenwahrscheinlichkeiten, erwartetem Resultat und WM-2026-Toggle zu erstellen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- ob dieselben Feature-Funktionen wie im Training verwendet werden,
- ob Modelle und Daten korrekt geladen werden,
- ob die Vorhersage für beide Teamreihenfolgen plausibel reagiert,
- und ob Rundung nur in der Darstellung erfolgt.

### Entscheidung und Umsetzung

Das Grundgerüst wurde übernommen. Ein inkompatibler Streamlit-Parameter wurde an die lokal installierte Version angepasst.


Die Feature-Importance-Grafik wurde später durch einen direkten Teamvergleich ersetzt, weil dieser für Nutzer ohne ML-Hintergrund verständlicher ist.

### Ergebnis und Reflexion

Das Dashboard konnte Teamvergleiche und Vorhersagen anzeigen.


Visuelle Funktionalität ist kein Nachweis für korrekte Modelllogik. Deshalb blieb das Notebook die primäre technische Kontrollumgebung.

---

## 15.–18.07.2026 – Iterative Verbesserung der Dashboard-Darstellung

### Ausgangslage und Ziel

Das erste Dashboard war funktional, aber teilweise zu technisch und visuell unübersichtlich.

### KI-Einsatz

Claude erhielt schrittweise konkrete Änderungsaufträge, unter anderem zu:

- Flaggen,
- Darstellung des erwarteten Resultats,
- Formkacheln,
- Head-to-Head-Ansicht,
- Teamvergleich,
- Tooltips,
- realen WM-Resultaten,
- und kompakteren Tabellen.

### Prüfung der KI-Ausgabe

Nach jeder Änderung wurde das Dashboard im Browser geprüft. Bei Zwischenständen wurden unter anderem folgende Fehler entdeckt:

- überschriebene Hilfsfunktion `flag_url()`,
- doppelte Head-to-Head-Anzeige,
- nicht passender Modulimport,
- unübersichtliche Tabellenbreite.

### Entscheidung und Umsetzung

Die meisten visuellen Vorschläge wurden übernommen. Nicht passende Darstellungen wurden in mehreren Iterationen verändert oder entfernt.


Die Darstellung wurde auf den Informationsbedarf eines Nutzers ausgerichtet. Technisch abstrakte Informationen wurden nur beibehalten, wenn sie für die Interpretation der Vorhersage hilfreich waren.

### Ergebnis und Reflexion

Das Dashboard erhielt:

- direkte Teamvergleiche,
- Form- und Head-to-Head-Details,
- reale Resultate bereits ausgetragener WM-Spiele,
- kompaktere Übersichten,
- und eine Team-Detailansicht für Simulationen.


KI eignet sich sehr gut für schnelle UI-Iterationen. Gleichzeitig stieg bei diesen Schritten mein Detailverständnis weniger stark als bei Datenpipeline und Feature Engineering. Für Ownership ist deshalb entscheidend, zumindest Datenfluss, Funktionsgrenzen und Fehlerfälle nachvollziehen zu können.

---

## 15.07.2026 – Inkrementelles Aktualisieren der laufenden Saison

### Ausgangslage und Ziel

Das ursprüngliche Abrufskript übersprang vorhandene Teamdateien vollständig. Neue WM-Spiele wären bei einem erneuten Lauf daher nicht ergänzt worden.

### KI-Einsatz

Claude wurde gebeten, das Verhalten zu analysieren und eine Refresh-Funktion vorzuschlagen.

### Prüfung der KI-Ausgabe

Ich testete separat:

- Duplikaterkennung über Fixture-ID,
- Ergänzung neuer Spiele,
- Erhalt der bisherigen Historie,
- und anschliessenden Abruf fehlender Match-Statistiken.

### Entscheidung und Umsetzung

`refresh_current_season()` und das CLI-Flag `--refresh` wurden übernommen.

### Ergebnis und Reflexion

Aktuelle Spiele können inkrementell ergänzt werden, ohne den gesamten historischen Bestand neu zu laden.


Die bestehende Pipeline war zwar resumierbar, aber nicht aktualisierbar. Erst die Betrachtung eines späteren Betriebsfalls machte diese Designschwäche sichtbar.

---

# Phase 6 – Turniersimulation

## 15.07.2026 – Offizielle Turnierregeln recherchiert und strukturiert

### Ausgangslage und Ziel

Die Simulation des WM-Formats mit 48 Teams erforderte eine korrekte Zuordnung der acht besten Gruppendritten im Achtelfinal. Diese Logik war im Exposé unterschätzt worden.

### KI-Einsatz

Claude wurde zunächst zur Regelstruktur befragt. Anschliessend wurden die offiziellen Annex-C-Tabellen aus PDF in JSON übertragen.

### Prüfung der KI-Ausgabe

Ich prüfte:

- ob alle 495 Kombinationen vorhanden sind,
- ob jeder Schlüssel eindeutig ist,
- ob acht Drittplatzierte korrekt zugeordnet werden,
- und ob die übrigen Achtelfinalpaarungen mit weiteren Quellen übereinstimmen.

### Entscheidung und Umsetzung

Eine vereinfachte zufällige Zuordnung wurde verworfen. Die Annex-C-Tabelle wurde als strukturierte Regelbasis übernommen.

### Problem

Erste PDF-Exporte enthielten nur einen Teil der 495 Kombinationen. Erst eine vollständige Version konnte verwendet werden.

### Entscheidung und Umsetzung

Bei nicht direkt zugänglichen offiziellen Detailinformationen wurden Sekundärquellen zur Kreuzvalidierung genutzt, statt Lücken durch Annahmen zu füllen.

### Ergebnis und Reflexion

Die vollständige Annex-C-Zuordnung wurde unter `data/raw/annex_c.json` eingebunden.


Dies war ein besonders wichtiger Kontrollfall: KI konnte aus unvollständigem Material eine formal plausible, aber sachlich unvollständige Datei erzeugen. Vollständigkeit musste deshalb explizit über Anzahl, Eindeutigkeit und Stichproben geprüft werden.

---

## 15.07.2026 – Monte-Carlo-Simulation umgesetzt

### Ausgangslage und Ziel

Das gesamte Turnier sollte von der Gruppenphase bis zum Final mehrfach simuliert werden.

### KI-Einsatz

Claude wurde beauftragt, die Simulation auf Basis der trainierten Modelle und der offiziellen Turnierstruktur umzusetzen.

### Prüfung der KI-Ausgabe

Geprüft wurden:

- 12 Gruppen mit je sechs Spielen,
- Gruppentabelle und Tiebreaker,
- Auswahl der acht besten Drittplatzierten,
- Annex-C-Lookup,
- eindeutige Achtelfinalteilnehmer,
- und ein Sieger in jeder K.-o.-Partie.

Die Struktur wurde mit Dummy-Modellen und mehreren vollständigen Turnierläufen getestet.

### Entscheidung und Umsetzung

Die Grundstruktur wurde übernommen.

Ein Vorschlag, bei einem K.-o.-Unentschieden so lange neu zu simulieren, bis ein Sieger entsteht, wurde verworfen.


Für K.-o.-Spiele wurde der Draw-Anteil entfernt und die beiden Siegwahrscheinlichkeiten auf 100 % normiert:

\[
P(A \mid \text{kein Draw}) = \frac{P(A)}{P(A)+P(B)}
\]

Diese Vereinfachung nutzt die relative Einschätzung des Modells, bildet aber Verlängerung und Elfmeterschiessen nicht separat ab.

### Ergebnis und Reflexion

Die Simulation lief in Testdurchläufen ohne fehlende Annex-C-Einträge oder doppelte Achtelfinalteilnehmer.


Die mathematische Normierung ist nachvollziehbar, aber weiterhin eine Modellannahme. Eine spätere Version könnte Verlängerung und Elfmeterschiessen explizit modellieren.

---

## 18.07.2026 – Simulation in das Dashboard integriert

### Ausgangslage und Ziel

Die Turniersimulation sollte über das Dashboard bedienbar sein.

### KI-Einsatz

Claude unterstützte bei Integration, Speicherung der Resultate und Visualisierung.

### Prüfung der KI-Ausgabe

Ein fehlerhafter Modulimport wurde erkannt und korrigiert. Die komplette Funktionskette wurde mit Dummy-Modellen für alle 48 Teams ausgeführt.

### Entscheidung und Umsetzung

Die Integration und JSON-Speicherung wurden übernommen.

### Ergebnis und Reflexion

Im Dashboard konnten Einzelsimulationen und aggregierte Mehrfachsimulationen angezeigt werden.


Der Importfehler zeigt, dass auch bereits „fertig“ wirkende KI-Änderungen mindestens einmal über den tatsächlichen Anwendungspfad ausgeführt werden müssen.

---

## 18.07.2026 – Teamverlauf und Gesamtübersichten ergänzt

### Ausgangslage und Ziel

Aggregierte Wahrscheinlichkeiten allein waren schwer greifbar. Zusätzlich sollte der konkrete Weg eines Teams durch ein simuliertes Turnier sichtbar sein.

### KI-Einsatz

Claude erweiterte die Simulation um Spiel- und Rundeninformationen und entwickelte darauf aufbauend mehrere Dashboard-Ansichten.

### Prüfung der KI-Ausgabe

Ich kontrollierte:

- abnehmende Erreichenswahrscheinlichkeiten über die Turnierphasen,
- vollständige Gruppenspiele,
- korrektes Ausscheiden,
- und Summen der Gruppenplatzierungen über alle Simulationen.

### Entscheidung und Umsetzung

Übernommen wurden:

- Teamverlauf einer Einzelsimulation,
- aggregierte Phasenwahrscheinlichkeiten,
- Top-10-Gesamtübersicht,
- Über- und Unterperformer relativ zum Ranking,
- Gruppenplatzierungswahrscheinlichkeiten.


Bei mehreren Simulationen wird zusätzlich ein einzelner Beispielverlauf gezeigt, damit die aggregierten Prozentwerte interpretierbar bleiben.

### Ergebnis und Reflexion

Die Turniersimulation wurde zu einem wesentlichen Bestandteil des Endprodukts und übertraf den ursprünglich geplanten Scope.


Die Erweiterung erhöhte den Produktwert, aber auch das Risiko versteckter Logikfehler. Entsprechend sind regelbasierte Tests für diese Komponente besonders wichtig.

---


# Phase 7 – Definition automatisierter Tests

## 23.07.2026 – Testkonzept für die zentralen fachlichen Risiken

### Ausgangslage und Ziel

Die bisherigen Kontrollen erfolgten grösstenteils manuell oder im Diagnose-Notebook. Für die finale Qualitätssicherung sollten deshalb gezielt automatisierte Tests ergänzt werden. Dabei war nicht eine möglichst hohe Anzahl Tests das Ziel, sondern die Absicherung der wichtigsten fachlichen Risiken des WM-2026-Predictors.

### KI-Einsatz

Ich definierte Claude einen klar abgegrenzten Testauftrag mit ungefähr zwölf fachlichen Tests und einer festen Dateistruktur:

```text
tests/
├── test_feature_engineering.py
├── test_tournament_logic.py
├── test_model_predictions.py
└── test_reproducibility.py
```

Die Tests sollten sich auf folgende Bereiche konzentrieren:

1. korrekte Berechnung der Ranking-Differenz,
2. historische Features ohne Einbezug des aktuellen oder zukünftiger Spiele,
3. Schutz vor Target Leakage durch Ausschluss von `result`, `goals_a` und `goals_b`,
4. Vollständigkeit der vom Modell erwarteten Feature-Spalten,
5. korrekte Gruppenstruktur mit 12 Gruppen und 48 eindeutigen Teams,
6. genau sechs eindeutige Gruppenspiele bei vier Teams,
7. genau 495 eindeutige Annex-C-Kombinationen,
8. gültige und vollständige Annex-C-Zuordnungen,
9. korrekte Siegerweiterleitung im offiziellen K.-o.-Turnierbaum,
10. vollständiger Turnierlauf mit genau einem Weltmeister,
11. gültige Modellwahrscheinlichkeiten unter Berücksichtigung von `model.classes_`,
12. reproduzierbare Simulationen bei identischem Zufallsseed.

Zusätzlich erhielt Claude die Anweisung, nach der Ausführung von `pytest -v` bestandene, fehlgeschlagene und übersprungene Tests sowie Laufzeit und Fehlerursachen zusammenzufassen.


### Entscheidung und Umsetzung

Ich beschränkte den Testumfang bewusst auf die zentralen Risiken:

- zeitliche Korrektheit und Leakage im Feature Engineering,
- Vollständigkeit und Eindeutigkeit der offiziellen Turnierregeln,
- korrekte Weiterleitung von Teams,
- Gültigkeit der Modellwahrscheinlichkeiten,
- und Reproduzierbarkeit der Simulation.

UI-Details und triviale Hilfsfunktionen wurden nicht priorisiert. Die Tests wurden auf vier thematisch getrennte Dateien verteilt, damit Fehler leichter einem Bereich zugeordnet werden können.

### Ergebnis und Reflexion

Mit diesem Auftrag wurde erstmals vor der Implementierung klar festgelegt, welche fachlichen Eigenschaften als korrekt gelten müssen. Dies verbessert die Qualität gegenüber rein visuellen oder manuellen Kontrollen, weil zentrale Invarianten wiederholbar geprüft werden können.

Besonders wichtig war die Vorgabe, bei einem Fehlschlag zunächst nur Ursache und kleinste sinnvolle Korrektur zu bestimmen. Dadurch wird verhindert, dass Claude produktiven Code automatisch verändert, nur damit ein Test besteht. Die Tests dienen damit nicht nur der Fehlererkennung, sondern auch als zusätzliche Kontrolle über KI-generierte Änderungen.

---

# 9. Kritische KI-Erfahrungen

## 9.1 Erfundene FIFA-Rankingdaten

### Ausgangslage

Claude sollte eine CSV mit aktuellen FIFA-Rankings der WM-Teams beschaffen.

### Problem

Der Webabruf schlug fehl. Trotzdem lieferte die KI eine formal plausible Datei mit Werten, die nicht verifiziert werden konnten und teilweise erfunden waren.

### Reaktion

Die Datei wurde vollständig verworfen. Stattdessen wurde ein nachprüfbarer Kaggle-Datensatz mit historischen Elo-Ratings verwendet.

### Erkenntnis

Plausibilität ist kein Qualitätsnachweis. Externe Daten dürfen nur übernommen werden, wenn Quelle, Vollständigkeit und Werte überprüfbar sind.

---

## 9.2 Lokale Fehlerkorrektur statt systematischer Lösung

### Ausgangslage

Der gleiche Encoding-Fehler trat in mehreren Dateien und Funktionen auf.

### Problem

Eine erste Korrektur löste nur den gerade sichtbaren Fehlerpfad.

### Reaktion

Alle Lese- und Schreibstellen wurden verglichen und auf eine einheitliche Encoding-Strategie umgestellt.

### Erkenntnis

KI reagiert oft auf die unmittelbar gemeldete Fehlermeldung. Die Verantwortung, nach ähnlichen Fehlerstellen im Gesamtsystem zu suchen, bleibt bei mir.

---

## 9.3 Funktionierender Output trotz begrenztem Verständnis

### Ausgangslage

Teile des Dashboards und der Turniersimulation funktionierten früh.

### Problem

Fehlerfreie Ausführung erzeugte zunächst den Eindruck, dass keine tiefere Prüfung erforderlich sei.

### Reaktion

Die Funktionskette wurde mit Dummy-Daten, Strukturprüfungen und konkreten Invarianten kontrolliert.

### Erkenntnis

„Läuft ohne Fehler“ bedeutet nur, dass kein sichtbarer Laufzeitfehler auftritt. Es beweist weder fachliche Korrektheit noch vollständige Regelumsetzung.

---

