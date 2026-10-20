
import fastf1
import pandas as pd
import requests
from pathlib import Path

# Questo file è stato creao per diagniosticare lo stato doi salute
# di FastF1, per via dei problemi riscontrati nel recuperare i dati. 


# 1. Mostra le versioni e abilita i log dettagliati.
print("FastF1:", fastf1.__version__)
print("Pandas:", pd.__version__)
fastf1.set_log_level("DEBUG")

# 2. Crea una cache persistente nella cartella del progetto.
cache_dir = Path(".fastf1_cache")
cache_dir.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(cache_dir))

# 3. Seleziona una sessione storica.
session = fastf1.get_session(2024, "Monza", "R")
print("Sessione:", session.event["EventName"])
print("Percorso API:", session.api_path)

# 4. Prova a richiedere direttamente un file F1.
url = (
    "https://livetiming.formula1.com"
    + session.api_path
    + "SessionInfo.jsonStream"
)

try:
    response = requests.get(url, timeout=20)
    print("HTTP Status:", response.status_code)
    print("Dimensione risposta:", len(response.content))
except requests.RequestException as exc:
    print("Problema di rete:", repr(exc))

# 5. Prova a caricare soltanto i dati dei giri.
session.load(
    laps=True,
    telemetry=False,
    weather=False,
    messages=False
)

try:
    print("Giri caricati:", len(session.laps))
    print(session.laps[
        ["Driver", "LapNumber", "LapTime"]
    ].head())
except fastf1.exceptions.DataNotLoadedError:
    print("ERRORE: i dati dei giri non sono stati caricati.")
