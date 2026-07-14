"""
Zentrale Konfiguration: lädt API-Key & Host aus der .env Datei.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env liegt im Projekt-Root, eine Ebene über src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
BASE_URL = f"https://{API_HOST}"

if not API_KEY:
    raise RuntimeError(
        "Kein API_FOOTBALL_KEY gefunden. Bitte in der .env Datei im Projekt-Root setzen."
    )

HEADERS = {
    "x-apisports-key": API_KEY,
}

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Alle 48 WM-2026-Teams (offizielle FIFA-Bezeichnung -> Liste möglicher API-Football-Suchnamen).
# Bei manchen Ländern weicht der API-Football-Name leicht von der FIFA-Bezeichnung ab, oder
# es ist unklar, welche Schreibweise API-Football intern nutzt - deshalb mehrere Kandidaten
# pro Team, die der Reihe nach probiert werden (siehe get_team_id in fetch_data.py).
WM2026_TEAMS = {
    # Co-Gastgeber
    "Canada": ["Canada"],
    "Mexico": ["Mexico"],
    "USA": ["USA"],
    # AFC
    "Australia": ["Australia"],
    "Iraq": ["Iraq"],
    "IR Iran": ["Iran"],
    "Japan": ["Japan"],
    "Jordan": ["Jordan"],
    "Korea Republic": ["South Korea"],
    "Qatar": ["Qatar"],
    "Saudi Arabia": ["Saudi Arabia"],
    "Uzbekistan": ["Uzbekistan"],
    # CAF
    "Algeria": ["Algeria"],
    "Cabo Verde": ["Cape Verde Islands", "Cape Verde", "Cabo Verde", "Cabo-Verde"],
    "Congo DR": ["Congo DR", "DR Congo", "Democratic Republic of the Congo", "DRC"],
    "Côte d'Ivoire": ["Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"],
    "Egypt": ["Egypt"],
    "Ghana": ["Ghana"],
    "Morocco": ["Morocco"],
    "Senegal": ["Senegal"],
    "South Africa": ["South Africa"],
    "Tunisia": ["Tunisia"],
    # Concacaf
    "Curaçao": ["Curacao", "Curaçao"],
    "Haiti": ["Haiti"],
    "Panama": ["Panama"],
    # CONMEBOL
    "Argentina": ["Argentina"],
    "Brazil": ["Brazil"],
    "Colombia": ["Colombia"],
    "Ecuador": ["Ecuador"],
    "Paraguay": ["Paraguay"],
    "Uruguay": ["Uruguay"],
    # OFC
    "New Zealand": ["New Zealand"],
    # UEFA
    "Austria": ["Austria"],
    "Belgium": ["Belgium"],
    "Bosnia and Herzegovina": ["Bosnia & Herzegovina", "Bosnia Herzegovina", "Bosnia and Herzegovina", "Bosnia-Herzegovina", "Bosnia", "BIH"],
    "Croatia": ["Croatia"],
    "Czechia": ["Czech Republic", "Czechia"],
    "England": ["England"],
    "France": ["France"],
    "Germany": ["Germany"],
    "Netherlands": ["Netherlands"],
    "Norway": ["Norway"],
    "Portugal": ["Portugal"],
    "Scotland": ["Scotland"],
    "Spain": ["Spain"],
    "Sweden": ["Sweden"],
    "Switzerland": ["Switzerland"],
    "Türkiye": ["Turkey", "Türkiye", "Turkiye"],
}

assert len(WM2026_TEAMS) == 48, f"Erwartet 48 Teams, gefunden: {len(WM2026_TEAMS)}"
