# Release v0.5.0 - 2026-10-20

- Added observed-time session metrics for irregular timestamps, repeated clocks,
  missing time and acquisition gaps; sample and temporal statistics stay distinct.
- Added configurable pedal usage/overlap, complete/partial braking events,
  onset-speed statistics and source-scale steering activity.
- Added Session Overview, Driver Inputs, Vehicle Dynamics, Tyre Analysis,
  generalized Telemetry Comparison and Position Analysis pages with CSV exports.
- Added shared cached dataset selection and a Data Explorer upload/mapping registry,
  including file-replacement invalidation and bounded chart rendering.
- Added saved session windows, compatible-unit checks, guarded validated-lap
  comparison and explicit rejection of unsupported cumulative lap deltas.
- Researched public datasets; downloaded and pinned a CC-BY-4.0 GT7 collection.
  Validated eight complete lap targets from real packet timers; rejected inconsistent
  groups and preserved raw files. No full supervised training was introduced.
- Added capability and ML/DL eligibility assessment, retrospective candidate lap
  features, reproducible source manifests, measured audit and readiness documentation.
- Expanded unit, UI, real-file integration and browser smoke coverage.
- Preserved v0.4 Git baseline, F5 setup, original datasets and historical SVR/Keras code.

# Release v0.4.0 - 2026-10-20

- Restored local Git history from the verified remote v0.3 branch without replacing
  workspace files; recorded the supplied workspace baseline on feat/sim-telemetry-v04.
- Added source-independent Parquet/CSV readers, explicit unit/column mappings,
  quality reporting, full-session metrics and conservative complete-lap validation.
- Added Data Explorer: cached local/uploaded telemetry, manual mappings, quality
  summaries, signal charts with bounded extrema downsampling and position traces.
- Renamed the homepage Motorsport Telemetry Analyzer; historical FastF1 pages are
  opt-in. Core local analysis does not import FastF1, Keras or PyTorch.
- Reused Python 3.11 .venv, split core/legacy requirements and configured VS Code F5.
- Audited the actual 116,987-row attachment; preserved original and copy hashes.
  Constant lap channels and integrated coordinates prevent certified lap segmentation.
- Added offline unit, UI and real-file integration tests plus reproducible audit and
  HTTP/browser smoke scripts. Added architecture and release documentation.
- Preserved historical analytics, SVR, feature engineering and Keras model sources.

# Release v0.2.0 — 2026-10-15

## Nuove funzioni
- Frontend Streamlit multipagina senza modifiche ai file legacy.
- Lap/stint dashboard con ranking e distribuzione dei lap times.
- Cronologia stint/compound e regressione lineare esplorativa sui giri gomma.
- Confronto due giri telemetrici (Speed, Throttle, Brake, RPM, nGear).
- Grafico del delta tempo cumulato B-A sullo stesso asse distanza.
- Mappa XY con colorazione speed e hover interattivo.
- Selettore condiviso di stagione, GP e sessione e cache locale FastF1.
- Valutazione quantitativa del modello Q su dati mai usati in training.
- Report MAE macro per giro / fase e export CSV Q.
- Metriche macro FP su validazione raggruppata per giro.
- Normalizzazione dello zero dei tempi telemetrici al primo campione.
- Suite di test sintetici ampliata a 10 test.

## Non modificato / non verificato
- Il codice legacy del repository GitHub non è stato letto o modificato.
- Replay e modello principale restano quelli del prototipo v0.1 con migliorie sopra.
- Non eseguito l'avvio completo FastF1 + Streamlit con un weekend reale.

## 0.3.0 — integrazione repository originali
- Letti i file originali su GitHub tramite plugin con permessi di scrittura.
- Porting SVR da Codes/Page_3.py, con pipeline scikit-learn e nuova pagina Streamlit.
- Protezione del repository originale: codice scritto solo su branch nel Capstone.
- Test smoke aggiuntivo e manuale per lo studio del codice.
