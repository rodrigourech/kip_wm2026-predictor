# Entwicklungstagebuch – WM 2026 Match Predictor

> Zweck: Laufende, kurze Einträge während der Entwicklung (SW 2–11), damit für den
> Entwicklungsbericht später nichts rekonstruiert werden muss. Kein Roman – Stichworte
> reichen, Hauptsache es ist ehrlich und konkret.
>
> Fülle pro Session (auch kurze!) einen neuen Eintrag aus. Bei wichtigen KI-Interaktionen:
> Prompt kurz notieren oder Screenshot/Export ablegen unter `docs/screenshots/`.

---

## Vorlage pro Eintrag (kopieren & ausfüllen)

```
### [Datum] – [Kurztitel der Session]

**Was gemacht:**
-

**KI-Einsatz (falls relevant):**
- Tool/Modell:
- Prompt (kurz oder Link zum Export):
- Übernommen / angepasst / verworfen:

**Eigene Entscheidungen:**
-

**Probleme / Blocker:**
-

**Strategiewechsel? (falls ja: was & warum)**
-

**Verständnis-Check:** Könntest du das eben Gebaute jemandem ohne KI erklären? (ja/teilweise/nein)
```

---

## Einträge

### 09.07.2026 – Projekt-Setup & GitHub

**Was gemacht:**
- Projektstruktur angelegt (data/, src/, app/, notebooks/, docs/)
- `.env`, `.gitignore`, `requirements.txt` erstellt
- `config.py` (lädt API-Key, definiert alle 48 WM-2026-Teams) und `fetch_data.py`
  (Skript für einmaligen API-Football-Abruf mit Caching/Resume-Logik) erstellt
- GitHub-Repo erstellt und Code gepusht (`rodrigourech/kip_wm2026-predictor`)

**KI-Einsatz (falls relevant):**
- Tool/Modell: Claude
- Prompt (kurz): "das würde ich gerne umsetzen" (Umsetzung des Exposés), danach iterativ
  Debugging-Hilfe bei `pip install` / Windows-Setup
- Übernommen / angepasst / verworfen: Grundgerüst von Claude übernommen, aber jede Datei
  selbst durchgelesen; Team-Liste der 48 WM-Nationen von Claude recherchiert und geprüft

**Eigene Entscheidungen:**
- API-Football (via api-football.com direkt, nicht RapidAPI-Umweg) als Datenquelle gewählt
- Resume-fähiges Fetch-Skript, um Free-Tier-Limit (100 Requests/Tag) zu handhaben

**Probleme / Blocker:**
- `pandas==2.2.2` hatte keine Wheels für Python 3.13 → Build-Fehler (fehlende Visual Studio
  Build Tools). Gelöst durch Versions-Update auf `pandas==2.2.3`
- GitHub-Remote-URL enthielt versehentlich Platzhalter `DEIN-USERNAME` statt echtem
  Repo-Link → korrigiert mit `git remote set-url`

**Strategiewechsel?**
- Ursprünglich RapidAPI geplant (laut Exposé), auf direkten API-Football-Key (api-football.com)
  umgestellt, da einfacher zugänglich – funktional identisch, nur anderer Header
  (`x-apisports-key` statt `X-RapidAPI-Key`)

**Verständnis-Check:** teilweise – Grundstruktur und Config verstanden, Fetch-Logik noch
nicht selbst getestet (API-Call steht noch aus)

---

### [Datum] – [nächster Eintrag hier einfügen]

**Was gemacht:**
-

**KI-Einsatz (falls relevant):**
-

**Eigene Entscheidungen:**
-

**Probleme / Blocker:**
-

**Strategiewechsel?**
-

**Verständnis-Check:**
-
