# Motorsport Telemetry Analyzer - v0.7.2

Lap-based telemetry exploration, recorded vehicle/Cockpit replay and audited causal ML.
Barcelona GP / Dallara F317 is the primary ML demonstration: **205 usable complete
laps**, including all 116 formerly excluded for uncertain metadata. The selected
SVR has validation MAE **9.868 s** and frozen test MAE **15.393 s** (median baseline
17.901 s). Slow-lap errors remain large; this is an educational retrospective
recording holdout, not a claim of unseen-session or live-racing generalization.
Python 3.11, Streamlit, Plotly, Pandas, NumPy and scikit-learn; no running simulator
or FastF1 connection is needed for local analysis.

## v0.7.2 diagnosis and feature experiments

The operational reference remains **SVR v0.7.1**. All 205 valid laps and its frozen
results stay intact. New experiments use only the original training+validation
pool: **169 laps / 40 recording blocks**, five group folds, with the 36 already
observed historical test laps excluded before feature construction.

| Development variant | Features | OOF MAE |
|---|---:|---:|
| F0, original reference configuration | 13 | 13.361 s |
| F1, trailing-window summaries | 20 | 13.381 s |
| F2, observed events/distance proxy | 18 | 13.424 s |
| F3, combined compact history | 25 | 13.400 s |
| F0W, separate pace-loss weighting | 13 | 13.317 s |

No variant meets the fixed adoption rule. Weighting's 0.044 s pooled improvement
comes with worse recording-macro and middle-pace errors. Preserve the current SVR
as an educational reference; a limited sequence-model comparison is a future
research option, with no demonstrated neural superiority and no DL added here.

On **Machine Learning**, expand **Diagnosi ML v0.7.2** and enable **Mostra confronto
delle feature sui fold di sviluppo** for tables, calibration, checkpoint/pace
errors and predefined development examples. These are experimental development
results, not a new final test. The existing training button and Progressive
Prediction continue to use the compatible v0.7.1 reference with hidden targets.

Explicit offline commands:

These use the installed signed v0.7.1 reference. On a fresh local setup, first
use its existing explicit training button to restore that reference from TRAIN
while reusing frozen evaluation, then run the development commands.

```powershell
python -m scripts.run_barcelona_v072 --audit-only
python -m scripts.run_barcelona_v072
python -m scripts.report_barcelona_v072
python -m scripts.verify_baselines_v072
```

The runner verifies/reuses frozen development evaluation. Missing research models
can be rebuilt on development data without rescoring held-out folds/test. Research
artifacts live separately in ignored `artifacts/barcelona_v072/models/`. Report
figures use the already-installed optional Matplotlib; normal application/training
does not require it. No new telemetry is downloaded and no live capture is added.

See [release](docs/RELEASE_V072_REPORT.md), [pace diagnosis](docs/PACE_DISTRIBUTION_AUDIT_V072.md),
[feature experiments](docs/ML_FEATURE_EXPERIMENTS_V072.md), [model assessment and sequence feasibility](docs/ML_MODEL_ASSESSMENT_V072.md),
[architecture](docs/ARCHITECTURE_V072.md) and [next recommendation](docs/NEXT_RELEASE_RECOMMENDATION.md).

## Start in VS Code

1. Open this project folder.
2. In **Run and Debug**, select **Motorsport Telemetry Analyzer**.
3. Press **F5**. Open **Data Explorer** from the sidebar.
4. Select **GT7** (the preferred installed demo) or an **ACGym** recording.
   CSV/Parquet uploads remain available when examples are absent.

The existing `.venv` and F5 configuration are preserved. VS Code uses the selected
project interpreter; `.vscode/settings.json` points to `.venv/Scripts/python.exe`.
If a different interpreter was explicitly selected earlier, select this `.venv`
once using **Python: Select Interpreter**. Ordinary startup needs no terminal command.

## Pages

| Page | What it does |
|---|---|
| Home | Offline entrypoint and links to the principal workflows |
| Session Overview | Essential session metrics; Channel / Time Measured [s] / Mean; explanations only for unavailable capabilities |
| Data Explorer | One dataset and shared verified-lap/time selection across Signals, Driver Inputs, Vehicle Dynamics, Tyre Analysis, Cockpit and Position / Track Map |
| Telemetry Comparison | Verified laps by default when both sources support them; source-relative lap time, compatible units, one shared legend and stable selection colors; saved-window fallback |
| Machine Learning | Inclusive Barcelona audit, explicit Ridge/Random Forest/SVR training, distinct validation and selected-model test results, baseline comparisons, importance and exports |
| Progressive Prediction | Retrospective checkpoint replay, observed telemetry, prediction history and optional final-target reveal; baseline, experimental and evaluated modes |

Legacy Formula 1 pages remain opt-in through the sidebar checkbox. Historical
SVR and Keras source modules are preserved. New canonical ML is separate; sequence
models remain optional future research.

## Explore recorded telemetry

Use **Dataset analizzato** in the sidebar once, then switch **Sezione analitica**.
GT7 is preferred for validated laps and a map, followed by ACGym and other local
files. The old 116,987-row `telemetry.parquet` attachment is preserved on disk but
hidden from the built-in catalog by its audited hash. A future different Parquet
file with the same filename is still discoverable. Uploading the original explicitly
remains supported; its exact known mapping is recognized. Parquet ingestion and
`pyarrow` are unchanged. There are no automatic downloads.
GT7 and ACGym offer measured labels such as `Lap 2 — 1:48.650`. Select one or
several verified laps; Signals overlays each using its own elapsed lap time.
The explicitly uploaded original attachment has no complete validated laps and
offers a recording-time window instead. Dataset, revision or mapping changes reset incompatible selections.
Uploaded compatible CSV/Parquet files use the same six sections and capability checks.

Driver Inputs retains configurable pedal usage and braking events; Dynamics and
Tyres retain their existing analytics and exports. Channel/family menus include only
finite real numerical measurements in the active selection; all-missing, infinite,
textual and complex signals are filtered, while legitimate constants remain usable.
Stale channel choices reset safely without changing selected laps or windows.
The G-G data area has matched axis ranges, `scaleanchor`/`scaleratio=1` and constrained
domains; actual equal pixel scales were checked in Chrome at several widths.
Unknown GT7 acceleration units remain source units rather than calibrated g.
Cockpit selects a real recorded
packet with an instant slider and shows only available measurements, including tyre
temperatures with declared units. This is recorded replay. Position draws connected,
colored source-coordinate segments, breaks at unsupported gaps/fragments/lap changes,
and allows any finite real numeric channel as color. Continuous colors use 32 bands
over the full measured range; gear uses discrete colors; missing color values are grey.
The display is bounded to 6,000 position vertices, with full-resolution calculations.
A small top-down vector car marks the selected real packet and stays the same pixel
size under zoom. Current datasets use an explicitly labelled local `atan2` trajectory
estimate with the same gap/lap/discontinuity guards as the line. A verified measured
heading requires declared angle units, axes, zero direction, rotation and handedness;
unlabelled angles/quaternions are never assumed to be heading. Undefined directions,
including stationary coordinates, use a neutral marker. Trajectory preparation is
cached across marker slider changes and never enters ML features.

ACGym selection is per recording rather than a concatenation of independent clocks.
Its UI adds declared tyre temperatures, pressures, loads and suspension travel without
altering the ML adapter. The inspected export has no compatible world X/Y; race rank
and normalized progress are not converted into coordinates. Original integrated
positions and GT7 reported world positions retain their accuracy warnings.

Detailed charts use bounded SVG traces and mount one analytical section at a time.
Chrome scrolling and section/dataset switching passed. The original intermittent
disappearance was **not reproduced** on the archived v0.6 page; a universal GPU/browser
fix is not claimed. See the [UI validation report](docs/UI_TEST_REPORT_V061.md).

## Shared hover interaction

All chart renderers use the same external numerical readout. Temporal plots show
an amber cursor at the same time across their panels; Dynamics and replay group
related figures into one component. Comparison rows follow selection A then B,
with stable source/lap/window identities and colors. Readouts and cursor persist
when the pointer leaves. Left/right arrows on a focused temporal chart inspect
observed samples without a Python rerun.

Readouts identify the nearest **real displayed sample**, its recorded time and
source sample where available. The tolerance is 0.51 times the original median
positive recording step; missing/null/decimated samples outside this tolerance
show `N/D`. There is no interpolation across gaps. XY, G-G, distributions, maps
and categorical charts use coordinate/statistic readouts and no temporal cursor.
On narrower component widths the panel moves below the plot. The installed
Plotly runtime is served offline as a cacheable local asset, once per component,
rather than embedded in each figure payload. See the architecture/chart audit
and real Chrome limitations in the v0.6.3 reports.

## Train and replay

Open **Machine Learning** for Barcelona / Dallara F317. The installed corpus has
70 recordings, 62 with independently checkable timing, **205 usable laps / 1,025
causal snapshots**. Participant/date uncertainty is flagged without rejecting
valid telemetry. Seed-42 recording-block holdout: **103 train / 66 validation /
36 test laps**, in 30/10/11 recording blocks. Unknown capture links remain a
documented limitation; these are not certified independent physical sessions.

Press **Addestra e valuta i tre modelli** to train on a fresh local installation
or reuse the frozen experiment. The fixed 13 causal features, checkpoints and
training-only preprocessing are preserved. Only validation chooses the model;
only selected SVR is evaluated on test. Compatible locally signed models load
automatically on page visits, with no fitting or download. Repeated training
actions verify/reuse saved evaluation rather than reopening the final test.
Dedicated artifacts live in ignored `artifacts/barcelona_v071/models/`.

Navigate to **Progressive Prediction**, choose a lap and advance 10/20/30/45/60 s.
Only observed telemetry and predictions enter the charts/readouts. The actual
target/error requires explicit retrospective reveal. The median baseline is fixed
from TRAIN targets; previous-lap comparisons require supported earlier history.
Validation and test labels never update baseline history.

All acquired data is used offline. If Barcelona is absent, the UI explains the
separate acquisition commands and never downloads automatically:

```powershell
python -m scripts.download_barcelona inspect
python -m scripts.download_barcelona sample
python -m scripts.download_barcelona all
python -m scripts.run_barcelona_v071
```

Acquisition is pinned to the public human Barcelona catalogue, with a 750 MB
transfer cap and 1.5 GB free-space reserve; installed originals total 574,612,274
bytes. No need to download again on this checkout. `--audit-only` reprocesses
without fitting. `python -m scripts.report_barcelona_v071` regenerates reports and
PNG/SVG figures from frozen CSVs without prediction or final-test access.
Static figure regeneration uses Matplotlib, already installed in this environment;
the application and training path do not import it.

See [release](docs/RELEASE_V071_REPORT.md), [dataset recovery](docs/BARCELONA_DATASET_AUDIT_V071.md),
[measured ML health](docs/ML_EVALUATION_V071.md), [comparison](docs/ML_COMPARISON_V071.md)
and [next recommendation](docs/NEXT_RELEASE_RECOMMENDATION.md).

### Historical Monza and GT7 reproduction

Run `python -m scripts.archive_app` to open the historical corpus interface.
Its source data, numerical models, snapshots and artifact namespace are separate
from Barcelona. The following v0.6 measurements remain historical evidence:

Open **Machine Learning**, select **ACGym human Monza / Dallara**, inspect eligibility
and features, then press **Addestra e valuta i tre modelli**. Training is explicit;
page visits never train or download data. The local subset supplies **55 verified
laps / 11 physical sessions / eight participant codes**, 275 causal snapshots and
100% valid key-channel coverage. Split: 29 train / 11 validation / 15 test laps,
keeping complete physical sessions together. The selected SVR's test MAE is
**6.743 s**, versus **9.443 s** for a frozen historical median; this small single-domain
result does not establish generalization. See [evaluation details](docs/ML_EVALUATION_V06.md).

Navigate through the sidebar to **Progressive Prediction** to preserve the trained
bundle. Select a lap/model and advance the 10/20/30/45/60 s slider. Only observed
inputs and predictions are shown; the verified result/error requires the explicit
retrospective checkbox. A browser/server restart clears the in-memory bundle.
**Salva bundle locale verificabile** persists models and preprocessing under ignored
`artifacts/models/`; only locally signed artifacts can be loaded through the Python API.

GT7 remains an **experimental single-session case study — insufficient evidence
for generalization**. Its eight laps require an explicit experimental opt-in;
robust training stays disabled. The original attachment has no valid lap targets
and therefore displays an eligibility explanation instead of training controls.

## Data and analytical definitions

The original attachment contains **116,987 rows / 86 channels**, no validated lap
boundaries, repeated simulator timestamps and a 2.36 s gap. Recorded span is
**1,827.078 s**; observed support after excluding the gap is **1,824.718 s**.
Time means and pedal usage use positive finite forward intervals, with left-hold
values. Repeated time values get zero dwell; gaps are excluded and no terminal
sample duration is invented. Overview displays only time-weighted means and
channel-specific temporal coverage. Sample statistics remain in the analytics APIs.
Braking events do not split at zero-duration
clock repeats; unsupported gaps and unknown samples do split them.

The additional GT7 source is downloaded locally and hash-verified: **95,796 rows /
114 source columns**, one driver/session/car/track, **eight** consistency-checked
complete laps. Other source groups are rejected for timer repeats/resets, out-lap
status or missing finish evidence. Session time is host capture time; accepted lap
targets use the independent simulator lap timer/next-lap packet, not host duration.
Both v0.5 raw datasets remain unchanged and excluded from Git.

The v0.6 [ACGym expansion](docs/DATASET_EXPANSION_V06.md) adds 48 pinned source
files totaling **241,902,674 bytes**, below the authorized 300 MB payload budget.
Safe numeric MoTeC decoding avoids pickle and downloaded code. One date-inconsistent
recording and 51 identity-ambiguous A-series laps are excluded from robust training.
Exports declare 50/100 Hz grids; native acquisition timing is not certified.
Source: [AssettoCorsaGym research team / dasGringuen](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym),
publisher-declared CC BY 4.0. Originals stay local; normalization and filtering are
documented derivations. The [manifest](docs/ACGYM_MANIFEST_V06.json) records every hash.

GT7 attribution: Ricardo Queiroz (2026),
[GT7 Telemetry: Porsche 962 C at Trial Mountain](https://huggingface.co/datasets/rpqueiroz/gt7-trial-mountain-962c),
publisher-declared [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) for the
author's contribution. Our normalization, validation and summaries are separate
derivations. No game assets or raw source telemetry are committed.

Unknown physical units remain labelled source units. Source-coordinate trajectories
are not verified circuit geometry. Normalized driven distance supports retrospective
signal-shape comparison in the analytics API; the UI uses relative elapsed lap time.
**Cumulative lap delta remains unavailable for the supplied datasets** because no
verified common spatial reference exists. Arbitrary session
windows never become laps. The original/GT7 sources remain below the robust ML
gate. Only the independently identified ACGym subset passes it for elapsed-time
ML; certified causal common-distance progress and deep-learning adequacy remain
unestablished. Whole-lap summaries are descriptive, never predictive inputs.

## Load and compare another session

Choose **Carica file** in Data Explorer to upload CSV/Parquet. Use
**Mappatura colonne e unita** to declare names/units and press **Applica mappatura**.
That mapped session becomes available to Data Explorer sections and comparison
selectors for the current Streamlit session. Local files in `data/raw/` or
`data/demo/` are also discovered. There are no startup downloads.

In **Telemetry Comparison**, choose sessions A/B and readable verified lap labels.
Compatible recordings of the same verified track can be compared. Each selected lap
keeps one color across channel subplots and appears once in the shared legend.
When verified laps are unavailable, select positive-duration session windows and
optionally save up to 20 windows with **Salva finestra A/B**. Windows are explicitly
labelled as windows. No unsupported cumulative delta is introduced. CSV exports remain
available for metrics and events; retrospective lap features remain available through
the Python API, with no dedicated feature table in Overview.

Comparison hover values now appear in a reserved side panel outside the signals.
The last inspected values, units, measured relative times and lap/window identities
remain readable after moving the pointer; colors and the single shared legend are
preserved. The small offline HTML component uses the already installed Plotly runtime
with no CDN or new frontend dependency. It reserves horizontal space and repeats
the bundled runtime in its iframe; dense/narrow layouts have less plot width.

## ML health assessment

The [v0.6.2 assessment](docs/ML_HEALTH_ASSESSMENT_V062.md) verifies source targets,
splits, preprocessing and frozen baseline calculations without changing models.
SVR's exact test MAE remains **6.743072 s**; **61.62%** of its absolute test error
is concentrated in the AB recording. Early predictions cluster near the training
center and slower laps are underestimated. Data coverage and feature compression
both warrant investigation; their relative effects are not established by one split.
The recommendation is to preserve current models, collect more independent sessions
with a new untouched holdout, and preregister small development-only feature tests.
Deep Learning is not implemented or presumed better.

Reproduce the separate safe audit with `python -m scripts.assess_ml_v062`.
It writes only new v0.6.2 evidence, uses three fixed development-only model fits,
and checks original frozen files/model-store hashes. It does not save trained artifacts
or overwrite v0.6 metrics. The standalone diagnostic figure is
`artifacts/v062/ml_health_residuals.html`.

## Environment and checks

The existing Python 3.11.9 `.venv` already has the necessary packages. v0.6 makes
joblib explicit in core requirements; no packages or deep learning libraries were
downloaded or reinstalled. On a new installation:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Optional legacy/training-test packages are in `requirements-extension.txt`.
Raw telemetry is not in Git. To reproduce the pinned GT7 working copy explicitly:

```powershell
.\.venv\Scripts\python.exe -m scripts.download_gt7
```

To reproduce ACGym explicitly, run `python -m scripts.download_acgym` (242 MB;
cached verified files are reused). All three working datasets are present in this
workspace. On another machine, copy the original attachment to
`data/raw/telemetry.parquet` separately.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.audit_v05
.\.venv\Scripts\python.exe -m scripts.audit_v06
.\.venv\Scripts\python.exe -m scripts.smoke_app
.\.venv\Scripts\python.exe -m scripts.verify_ml_v061
.\.venv\Scripts\python.exe -m scripts.assess_ml_v062
```

For a core-only installation omit the two historical DL training modules with
`--ignore=tests/test_model.py --ignore=tests/test_evaluation.py`. Real-file tests skip
if local raw datasets are absent. In VS Code, **Testing** discovers pytest tests.
Optional browser checks use the installed `websockets` package and local Chrome:
`python -m scripts.smoke_app --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
For the current Barcelona diagnosis workflow add `--release v072` (or `v072-ml`
for the shorter ML/replay path). `--release v071` retains the previous workflow; for the retained prior
workflow use `--release v063-baseline`, and type fixtures `--release v063-fixtures`.
Screenshots/logs stay under ignored `artifacts/<release>/`; temporary servers and
browsers stop afterward. Historical scenarios explicitly select the archive UI.
To investigate the original rendering independently, run
`python -m scripts.investigate_rendering_v061 --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
This executes the archived local v0.6 explorer in an ignored artifact script without
changing the checkout. The full v0.6.1 suite and actual browser results are recorded below.

## Reports

- [v0.6.3 release and FB-025/026/027 evidence](docs/RELEASE_V063_REPORT.md)
- [v0.6.3 hover interaction and performance validation](docs/HOVER_UX_TEST_V063.md)
- [v0.6.3 shared component, chart audit and study guide](docs/ARCHITECTURE_V063.md)

- [v0.6.2 release and FB-018–FB-024 evidence](docs/RELEASE_V062_REPORT.md)
- [v0.6.2 Chrome, unit and regression validation](docs/UI_TEST_REPORT_V062.md)
- [ML health assessment and recommended experiments](docs/ML_HEALTH_ASSESSMENT_V062.md)
- [v0.6.2 UI architecture](docs/ARCHITECTURE_V062.md)
- [v0.6.1 release, feedback traceability and limitations](docs/RELEASE_V061_REPORT.md)
- [v0.6.1 UI architecture and selection lifecycle](docs/ARCHITECTURE_V061.md)
- [v0.6.1 automated tests, Chrome checks and rendering investigation](docs/UI_TEST_REPORT_V061.md)
- [v0.6 dataset expansion and validation](docs/DATASET_EXPANSION_V06.md)
- [Causal and retrospective feature contracts](docs/ML_FEATURES_V06.md)
- [Real ML results and evaluation limitations](docs/ML_EVALUATION_V06.md)
- [v0.6 architecture and Python function guide](docs/ARCHITECTURE_V06.md)
- [v0.6 release and acceptance evidence](docs/RELEASE_V06_REPORT.md)
- [Recommended next release](docs/NEXT_RELEASE_RECOMMENDATION.md)
- [Dataset research, licenses and measured selection](docs/DATASET_SELECTION_V05.md)
- [Architecture and analytical formulas](docs/ARCHITECTURE_V05.md)
- [ML/DL readiness, eligibility and leakage prevention](docs/ML_DL_READINESS_V05.md)
- [Release report and actual acceptance results](docs/RELEASE_V05_REPORT.md)
- [Reproducible measured evidence](docs/DATASET_MEASUREMENTS_V05.json)

v0.4 audit/release/architecture reports remain in `docs/`. Earlier Formula 1 setup
and model notes are retained in [the historical README](docs/README_LEGACY_V03.md).
The v0.6 source and evaluation manifests are reproducible offline. Further dataset
expansion and source-clock validation should precede stronger v0.7 sequence-model
claims; the eight GT7 laps remain a feature-contract demonstration.
