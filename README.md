# Motorsport Performance Analysis — Streamlit Extension v0.2.0

**Cosa contiene:** un nuovo frontend Streamlit multipagina, una pipeline di previsione
Keras su FP1+FP2+FP3 del singolo weekend, replay Q e valutazione separata Q.
Il frontend analitico replica a livello funzionale le aree della sinossi, ma è stato confrontato con il codice effettivamente letto da **stiv-eng/Formula-1-Data-Analysis**.
La pagina SVR conserva l’approccio di `Codes/Page_3.py`, adattandolo a Streamlit.

**Integrazione sicura:** lo sviluppo si colloca nella repository CAPOSTONE, senza modificare la sorgente.
Si avvia con un nuovo entrypoint `streamlit_app.py`, indipendente dal vecchio.

## File e responsabilità

| File | Ruolo |
|---|---|
| `streamlit_app.py` | Homepage Streamlit, menù multipagina automatico |
| `pages/01_Lap_and_Stint_Analysis.py` | Lap times, distribuzioni, classifiche, stint, regressione lineare |
| `pages/02_Telemetry_Comparison.py` | Speed, throttle, brake, RPM, gear, delta tempo cumulato |
| `pages/03_Track_Map.py` | Mappa del circuito e velocità visualizzate in Plotly |
| `pages/04_Model_Evaluation.py` | Audit: confronto baseline/rete sui giri Q non visti |
| `pages/05_Dynamic_Lap_Time_Prediction.py` | Training FP e replay progressivo di Q |
| `motorsport_ui/common.py` | Selezione GP/sessione, cache, caricamento FastF1 |
| `motorsport_ui/analytics.py` | Elaborazione dati, stint, regressioni, delta telemetria |
| `motorsport_prediction/data.py` | FP/Q loader, filtri, normalizzazione tempo e distanza |
| `motorsport_prediction/features.py` | Snapshot causali, baseline FP3, etichette FP |
| `motorsport_prediction/model.py` | Preprocessing train-only, Keras, gruppo per giro, score Q, salvataggio |
| `tests/` | Test offline su dati sintetici |

## Avvio autonomo (Windows 11 + VS Code)

Aprire il terminale **dentro la cartella estratta**, in Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-extension.txt
streamlit run streamlit_app.py
```

La homepage e tutte le pagine appaiono nel menu a sinistra. Se i download FastF1
falliscono, controllare connettività, accesso dati e supporto della sessione.
La cache locale `.fastf1_cache/` riutilizza i download nelle richieste successive.

### Integrazione con il repo già esistente

1. Creare una branch Git di sicurezza (es.: `feat/streamlit-capstone`).
2. Copiare **solo** `motorsport_ui/`, `motorsport_prediction/`, `pages/`,
   `streamlit_app.py`, `requirements-extension.txt` (ed eventualmente i test)
   nella root della repo. Se ci sono file omonimi, **confrontarli prima**.
3. Lasciare invariati i vecchi `Page_*.py`, `utils_func.py`, `DarkF1_Plotting_Theme.py`
   e l'eventuale vecchio entrypoint Python. Non sono stati letti e non vanno rimossi.
4. Lanciare `streamlit run streamlit_app.py` per testare il frontend alternativo.
5. Se la repo usa già un entrypoint Streamlit + `pages/`, copiare solo i nuovi
   moduli e nuove pagine e continuare ad avviare quello esistente (senza doppio router).
6. Se invece usa **`st.navigation`** il filesystem `pages/` viene ignorato: registrare
   esplicitamente le pagine `st.Page('pages/…')` all'interno del suo `st.navigation`.
7. Solo dopo aver verificato a parità di sessione risultati e grafici fra
   vecchia e nuova UI, migrare/eliminare le vecchie pagine.

Non è stato fatto **nessun commit o push** nel repository dell'utente.

## Metodo ML, rigorosamente entro il weekend

- Training: soltanto le sessioni FP1, FP2, FP3 dello stesso evento e stagione.
- Dataset unico dei piloti; driver e compound come variabili categoriche.
- Reference: miglior giro valido FP3 per pilota; escluso dal training/holdout.
- Per ogni checkpoint di distanza noto **dalla reference FP3**:
  `baseline = elapsed_Q + (FP3_final - FP3_elapsed_at_distance)`.
- Feature causali: tempo, velocità, media fino all'istante, media 3 s,
  throttle, brake, RPM, marcia, gomma, differenza rispetto alla reference.
- Target FP: errore residuo `tempo_finale_FP - baseline`; modello MLP Keras
  con due layer nascosti (64, 32), Huber loss ed EarlyStopping.
- Train/validation split `GroupShuffleSplit` per `lap_uid`; scaler/encoder
  fittati **solo sul train**. Metriche FP sia per snapshot sia macro per giro.
- La qualifica viene caricata solo per replay e audit (mai come dato di fit).
  Il tempo effettivo Q è visualizzato **solo al completamento** o nelle pagine
  di valutazione *a posteriori*; non viene utilizzato nelle feature input.
- L'errore MAE sulla Q viene riportato come media **per giro** e per fase
  (0-25%, 25-50%, 50-75%, 75-100%), confrontando baseline e modello.

**Limitazioni:**

- Non supporta weekend senza FP3 tradizionale (es. weekend sprint).
- Il modello è una proof-of-concept; con pochi giri il DL può peggiorare la baseline.
- È un replay di una sessione storica, non un live timing ufficiale.
- Telemetria FastF1 di broadcast: campionamento/posizione stimati, non dati
  di acquisizione ad alta frequenza da vettura reale.
- La validazione è *within-weekend* e dipende dal riferimento FP3 già noto a fine FP3.
  Non equivale a validazione walk-forward fra weekend, non prevista dalla sinossi.
- Il fit lineare di stint è descrittivo, non isola il degrado pneumatici
  da peso carburante, traffico, safety car e cambi delle condizioni meteo.
- Il delta telemetrico B-A usa l'interpolazione sulle distanze stimate.
- I modelli e preprocessing salvati (`artifacts/`) vanno caricati solo da
  file locali fidati: `joblib` può eseguire codice arbitrario in deserializzazione.

## Test offline

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q tests
```

La suite non richiede di scaricare dati; usa telemetria sintetica e un mini train Keras.
Il test end-to-end su veri weekend FastF1 e l'interfaccia Streamlit in browser
**non sono stati eseguiti** nell'ambiente di sviluppo di questo pacchetto.

## Checklist di accettazione sul proprio PC

- [ ] Aprire una gara storica con il nuovo Lap & Stint Analysis.
- [ ] Confrontare due giri Q sulla pagina Telemetry Comparison.
- [ ] Visualizzare la mappa XY e la colormap velocità di un giro.
- [ ] Caricare FP1/FP2/FP3 dello stesso GP e addestrare la rete Keras.
- [ ] Riprodurre un giro Q al 25, 50, 75, 95% e poi al traguardo.
- [ ] Verificare che Model Evaluation mostri tempi e MAE (anche se rete peggiora).
- [ ] Confrontare risultati con i moduli originali, senza regressioni.


## Repo esaminate (15 ottobre 2026)

- Sorgente: https://github.com/stiv-eng/Formula-1-Data-Analysis
- Destinazione: https://github.com/stiv-eng/EPICODE-Capstone-Project
- L’originale include `Source_Code/F1_Data_Analysis.py`, `Codes/Page_2.py`, `Codes/Page_3.py` e un tema Matplotlib.
- L’originale importa `utils_func` e `Page_4`, che non risultano versionati: il porting evita tale dipendenza.
- `Page_2.py` consente in origine confronto tra sessioni/stagioni differenti; la nuova pagina di confronto v0.3 supporta due giri della stessa sessione, mentre il confronto cross-session è un’estensione futura.
- SVR è retrospettivo perché `AvgSpeed` e `BrakeTime` richiedono il giro intero; non deve essere confuso con il replay Keras.