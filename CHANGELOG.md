# Release v0.7.1 - 2026-10-24

- Recover all 116 Barcelona laps excluded only for uncertain identity/date metadata,
  plus one verified 0.5 ms source-rounding case: 205 usable laps, 100% core coverage.
- Replace the 12-group gate with seed-42 recording-block holdout: 103/66/36 laps.
  Keep uncertain metadata, verified targets, causal prefixes and exact deduplication.
- Actually train unchanged Ridge, Random Forest and SVR; validation selects SVR
  (MAE 9.868 s). Evaluate selected SVR once on frozen test (15.393 s versus median
  17.901 s), with checkpoint/lap/recording/pace diagnostics and a learning curve.
- Retain inclusive experiment A; no training lap meets the preregistered optional
  timing-quality filter. Preserve legitimate slow laps and report their large errors.
- Integrate compatible signed Barcelona artifacts, frozen evaluation reuse and
  causal target-hidden replay. Preserve v0.6.3 hover and historical Monza/GT7 results.
- Add recovery/protocol/UI tests, actual Chrome workflows and measured reports.
  See [release](docs/RELEASE_V071_REPORT.md) and [ML health](docs/ML_EVALUATION_V071.md).

# Preserved v0.7 checkpoint - 2026-10-24

- Acquire and hash 70 human Barcelona LD/LDX pairs plus 11 catalogue CSVs (574.6 MB).
- Verify 204 complete targets; admit 88 under the original strict metadata policy.
  Preserve the failed 11/12-group gate honestly, with no Barcelona fitting or scores.
- Preserve this implementation on `feat/sim-telemetry-v07`, commit `23796be`.
  v0.7.1 explicitly supersedes its restrictive inclusion policy.

# Release v0.6.3 - 2026-10-24

- Restore a relative-time SVG cursor across every telemetry panel; preserve
  external readouts through hover, zoom, pan, resize and channel/source changes.
- Fix A/B row ordering with source/lap/window/slot identities, stable colors and
  persistent unavailable rows; no hover-driven Python reruns or interpolation.
- Share the hover renderer across Explorer, G-G/correlations, Position, Cockpit
  context, ML/replay and optional legacy charts. Clockless Signals explicitly use
  source sample indices without a time cursor. Preserve causal target visibility.
- Group related figures, serve a content-hashed offline runtime with explicit
  browser caching, resolve Streamlit palette tokens and support below-chart
  readouts at narrow widths. Keep existing numerical pipelines and SVG budgets.
- Retain 172 baseline tests and add 21; rerun all 36 prior Chrome checks plus 47
  new workflow and 4 fixture interaction checks. Frozen 390 ACGym + 60 GT7
  predictions remain within 1e-9 s. See [release](docs/RELEASE_V063_REPORT.md),
  [validation](docs/HOVER_UX_TEST_V063.md) and [architecture/audit](docs/ARCHITECTURE_V063.md).

# Release v0.6.2 - 2026-10-24

- Prioritized installed GT7/ACGym examples and hid only the audited original demo
  attachment from the catalog; preserved its file, explicit upload, generic Parquet
  ingestion, pyarrow and all canonical/source/model contracts.
- Added consistent Overview/Comparison sidebar icons and shared actual finite-channel
  filtering, dynamic tyre/dynamics families and safe stale-choice reconciliation.
- Corrected G-G equal pixel-per-unit scaling with matched ranges, constrained domains
  and a bounded plotting container; verified actual square data areas after resizing.
- Added a small top-down pixel-sized vector car on source-coordinate trajectories,
  verified heading conventions where declared, guarded atan2 fallback, neutral markers
  for undefined directions and cached trajectory preparation across slider changes.
- Moved Comparison readouts into a reserved offline side panel, preserving measured
  values, units, source/lap/window identities, shared legend and consistent colors.
- Added a separate ML health audit with verified frozen metrics, group/tail/checkpoint
  residual analysis, three unchanged development-only diagnostic fits and safe outputs.
- Kept production ML, splits, models, artifacts, target separation and prediction
  results unchanged; no tuning, Keras experiment, dataset acquisition or v0.7 code.
- Added geometry/availability/state/upload/audit tests, Chrome hover/marker/scale checks,
  measured diagnostic evidence and release/architecture/scientific assessment reports.

# Release v0.6.1 - 2026-10-24

- Consolidated six detailed analytical sections inside Data Explorer; retained Home,
  Session Overview, Comparison, ML, Progressive Prediction and optional legacy tools.
- Added shared cached source/lap/time selection with verified timing labels and
  dataset/revision/mapping invalidation; GT7 no longer has a separate explorer layout.
- Exposed ACGym recordings and declared tyre/load/suspension channels through a
  UI-only adapter, preserving the audited ML corpus and all model implementations.
- Simplified Overview to measured-time coverage and time-weighted Mean; removed
  pedal usage, distributions and the visible verified-lap/features section.
- Added a responsive recorded Cockpit, nearest actual packet selection, pedal bars,
  available tyre temperatures and optional context traces.
- Added bounded connected trajectories with gap/lap/discontinuity guards, numeric
  source-channel coloring, discrete gear legends and full-range continuous scales.
- Made verified laps the primary comparison mode; source-relative time alignment,
  concise session labels, deterministic colors and one shared legend across subplots.
- Replaced detailed analytical WebGL traces with bounded SVG and lazy section
  mounting. Scrolling passed in Chrome; the original intermittent v0.6 symptom was
  not reproduced, so the rendering issue remains qualified in the release report.
- Added state/visualization/UI tests, a three-source Chrome smoke workflow, an archived
  v0.6 rendering investigation and frozen v0.6 sklearn prediction regression checks.
- Preserved raw datasets, Git history, historical modules and VS Code launch settings.

# Release v0.6.0 - 2026-10-20

- Added a pinned 241.903 MB human MoTeC dataset subset with a bounded numeric
  reader, verified source hashes, source-clock/target validation and quarantine.
- Integrated 55 eligible Monza/Dallara laps from 11 physical recording sessions
  and eight participant codes; excluded ambiguous series and inconsistent dates.
- Added causal elapsed-time feature snapshots, separate retrospective summaries,
  past-only allowed training-lap baselines and physical-session/lap split contracts.
- Added training-only sklearn Ridge/Random Forest/SVR pipelines, fixed validation
  selection, frozen test metrics, per-checkpoint/lap/session errors and importance.
- Added independent inference, future-sample/label leakage tests and locally signed
  model/preprocessing artifacts; unknown model files cannot be uploaded/loaded.
- Added Machine Learning and Progressive Prediction pages with explicit training,
  persistent bundles, eligibility explanations and optional retrospective target reveal.
- Kept GT7 explicitly experimental and the original attachment ineligible for ML.
- Preserved v0.5 datasets, historical SVR/Keras modules and VS Code F5 configuration.
- Added measured dataset/evaluation evidence, offline/UI/browser regression coverage
  and a technical guide for presenting the pipeline.

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
