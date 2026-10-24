# Motorsport Telemetry Analyzer - v0.6.1

Lap-based telemetry exploration, a recorded Cockpit, causal ML and retrospective replay.
Python 3.11, Streamlit, Plotly, Pandas, NumPy and scikit-learn; no running simulator
or FastF1 connection is needed for local analysis.

## Start in VS Code

1. Open this project folder.
2. In **Run and Debug**, select **Motorsport Telemetry Analyzer**.
3. Press **F5**. Open **Data Explorer** from the sidebar.
4. Select the original `data/raw/telemetry.parquet`, **GT7**, or an **ACGym** recording.

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
| Machine Learning | Dataset eligibility, causal feature selection, explicit Ridge/Random Forest/SVR training, chronological holdout errors, baseline comparison, importance and exports |
| Progressive Prediction | Retrospective checkpoint replay, observed telemetry, prediction history and optional final-target reveal; baseline, experimental and evaluated modes |

Legacy Formula 1 pages remain opt-in through the sidebar checkbox. Historical
SVR and Keras source modules are preserved. New canonical ML is separate; sequence
models remain future v0.7 work.

## Explore recorded telemetry

Use **Dataset analizzato** in the sidebar once, then switch **Sezione analitica**.
GT7 and ACGym offer measured labels such as `Lap 2 — 1:48.650`. Select one or
several verified laps; Signals overlays each using its own elapsed lap time.
The original attachment has no complete validated laps and offers a recording-time
window instead. Dataset, revision or mapping changes reset incompatible selections.
Uploaded compatible CSV/Parquet files use the same six sections and capability checks.

Driver Inputs retains configurable pedal usage and braking events; Dynamics and
Tyres retain their existing analytics and exports. Cockpit selects a real recorded
packet with an instant slider and shows only available measurements, including tyre
temperatures with declared units. This is recorded replay. Position draws connected,
colored source-coordinate segments, breaks at unsupported gaps/fragments/lap changes,
and allows any finite real numeric channel as color. Continuous colors use 32 bands
over the full measured range; gear uses discrete colors; missing color values are grey.
The display is bounded to 6,000 position vertices, with full-resolution calculations.

ACGym selection is per recording rather than a concatenation of independent clocks.
Its UI adds declared tyre temperatures, pressures, loads and suspension travel without
altering the ML adapter. The inspected export has no compatible world X/Y; race rank
and normalized progress are not converted into coordinates. Original integrated
positions and GT7 reported world positions retain their accuracy warnings.

Detailed charts use bounded SVG traces and mount one analytical section at a time.
Chrome scrolling and section/dataset switching passed. The original intermittent
disappearance was **not reproduced** on the archived v0.6 page; a universal GPU/browser
fix is not claimed. See the [UI validation report](docs/UI_TEST_REPORT_V061.md).

## Train and replay

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
```

For a core-only installation omit the two historical DL training modules with
`--ignore=tests/test_model.py --ignore=tests/test_evaluation.py`. Real-file tests skip
if local raw datasets are absent. In VS Code, **Testing** discovers pytest tests.
Optional browser checks use the installed `websockets` package and local Chrome:
`python -m scripts.smoke_app --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
Screenshots/logs stay under ignored `artifacts/`; the temporary server/browser stop afterward.
To investigate the original rendering independently, run
`python -m scripts.investigate_rendering_v061 --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
This executes the archived local v0.6 explorer in an ignored artifact script without
changing the checkout. The full v0.6.1 suite and actual browser results are recorded below.

## Reports

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
