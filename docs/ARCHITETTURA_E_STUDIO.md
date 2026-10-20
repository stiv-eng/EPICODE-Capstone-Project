# Guida all'architettura e alla migrazione (v0.3)

## Provenienza delle tecniche

Il codice si basa sui file del repository originale `stiv-eng/Formula-1-Data-Analysis`:

- `Source_Code/F1_Data_Analysis.py`: serie dei lap time, tyre stint, fit lineare con NumPy, analisi Speed/RPM/Throttle e mappa XY. Ora: `pages/01_Lap_and_Stint_Analysis.py`, `pages/03_Track_Map.py`, `motorsport_ui/analytics.py`.
- `Codes/Page_2.py`: confronto di due giri, scelta fastest/giro N, grafici canali, delta tempo. Ora: `pages/02_Telemetry_Comparison.py` e `motorsport_ui/analytics.py`.
- `Codes/Page_3.py`: regressore SVR (OneHotEncoder, StandardScaler, ColumnTransformer, train_test_split, metriche). Ora: `pages/04_Legacy_SVR.py` e `motorsport_ui/svr.py`.
- `Utils/DarkF1_Plotting_Theme.py`: stile originale Matplotlib. Ora: front-end Plotly/Streamlit, per cui la gestione del tema è diversa.

**Due import mancanti nell'originale:** `utils_func` e `Page_4` non sono nel tree del repository letto. Non sono necessari alla nuova app.

## Flusso architetturale

```text
streamlit_app.py
    |
    +-- pages/01_* --- common.py --> FastF1 --> analytics.py --> Plotly
    +-- pages/02_* --- common.py --> FastF1 --> analytics.py --> Plotly
    +-- pages/03_* --- common.py --> FastF1 -------------> Plotly
    +-- pages/04_* --- common.py --> FastF1 --> svr.py --> scikit-learn --> Plotly
    +-- pages/05_* --- data.py --> FastF1 --> features.py --> model.py --> Keras
    +-- pages/04_Model_Evaluation.py --> model.py --> metrica MAE su Q
```

### Dataset ML

`load_practice()` carica FP1/FP2/FP3 per lo stesso weekend e individua per pilota il miglior giro FP3, escluso dal training. `build_dataset()` costruisce snapshot a distanze prefissate dal giro FP3. `fit_model()` divide i dati per **giro intero**, poi fa il `fit` dello scaler e dell'encoder solo sul train e addestra il MLP con Huber loss. `replay_predictions()` applica il modello ai prefissi osservati del giro Q. `evaluate_qualifying()` usa il tempo Q reale solo per calcolare gli errori a posteriori.

**Differenza importante:** il vecchio modello SVR vede medie statistiche di tutto il giro ed è perciò retrospettivo; la nuova rete progressiva è progettata per utilizzare solo il prefisso disponibile nel replay.

### Limiti metodologici

- Le predizioni usano il miglior giro FP3 noto a fine sessione: ciò è coerente con la valutazione successiva sulle qualifiche, ma non permette di prevedere FP1 in modo realtime.
- FP e Q variano per carburante, gomme, pista ed evoluzione delle condizioni. Una rete piccola può non generalizzare e peggiorare la baseline.
- Non c'è ancora una verifica end-to-end in browser con i dati FastF1 di un GP concreto.
- I weekend sprint senza FP3 tradizionale non sono supportati dal modello di riferimento.
- La nuova `Telemetry Comparison` attualmente confronta due giri della stessa sessione; il modulo originale supportava anche due GP/anni diversi e tale estensione rimane pianificata.

## Procedura di verifica

1. `py -3.11 -m venv .venv` e attivazione `.venv`.
2. `pip install -r requirements.txt`.
3. `python -m pytest -q tests` per test sintetici.
4. `streamlit run streamlit_app.py` per interfaccia.
5. Selezionare un GP con FP1/FP2/FP3 e una qualifica disponibili (ad esempio un weekend non sprint).
6. Confrontare analisi tempi e telemetria con il codice originale a parità di evento/driver/giro.
7. Allenare Keras, riprodurre una qualifica e valutare MAE baseline vs modello senza assumere che il modello debba vincere.

Una guida **PDF con lettura riga per riga** è consegnata insieme al pacchetto ZIP nella conversazione.
