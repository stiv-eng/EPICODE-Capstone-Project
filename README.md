# Motorsport Telemetry Analyzer - v0.6

Local telemetry analysis, causal ML features and progressive retrospective replay.
Python 3.11, Streamlit, Plotly, Pandas, NumPy and scikit-learn; no running simulator
or FastF1 connection is needed for local analysis.

## Start in VS Code

1. Open this project folder.
2. In **Run and Debug**, select **Motorsport Telemetry Analyzer**.
3. Press **F5**. Open **Session Overview** from the sidebar.
4. Select the original `data/raw/telemetry.parquet` or **GT7 - Trial Mountain - Porsche 962 C**.

The existing `.venv` and F5 configuration are preserved. VS Code uses the selected
project interpreter; `.vscode/settings.json` points to `.venv/Scripts/python.exe`.
If a different interpreter was explicitly selected earlier, select this `.venv`
once using **Python: Select Interpreter**. Ordinary startup needs no terminal command.

## Pages

| Page | What it does |
|---|---|
| Session Overview | Recorded span versus observed duration, acquisition quality, sample/time means, gear/RPM distributions, capability assessment and candidate lap-feature export |
| Data Explorer | Cached local CSV/Parquet or in-memory uploads, explicit column/unit mappings, schema/quality and raw previews; audited GT7 bundle support |
| Driver Inputs | Configurable pedal thresholds, observed-time usage/overlap, complete/partial braking events, entry speeds, steering activity and combined signal charts |
| Vehicle Dynamics | Acceleration traces, source-scale G-G scatter, speed/lateral and steering/yaw relations, slip, loads, suspension and wheel signals |
| Tyre Analysis | FL/FR/RL/RR core/inner/middle/outer temperatures, pressures, reported wear, wheel loads/speeds where present; temporal inspection and CSV summaries |
| Telemetry Comparison | Two compatible session windows with relative time, up to 20 saved windows, or validated laps with approximate driven-distance-fraction alignment |
| Position Analysis | Source trajectory colored by speed/pedals, time window, sample marker, hover details and coordinate-quality warnings |
| Machine Learning | Dataset eligibility, causal feature selection, explicit Ridge/Random Forest/SVR training, chronological holdout errors, baseline comparison, importance and exports |
| Progressive Prediction | Retrospective checkpoint replay, observed telemetry, prediction history and optional final-target reveal; baseline, experimental and evaluated modes |

Legacy Formula 1 pages remain opt-in through the sidebar checkbox. Historical
SVR and Keras source modules are preserved. New canonical ML is separate; sequence
models remain future v0.7 work.

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
sample duration is invented. The UI distinguishes ordinary sample means and
channel-specific temporal coverage. Braking events do not split at zero-duration
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
signal-shape comparison; **cumulative lap delta remains unavailable for both real
datasets** because no verified common spatial reference exists. Arbitrary session
windows never become laps. The original/GT7 sources remain below the robust ML
gate. Only the independently identified ACGym subset passes it for elapsed-time
ML; certified causal common-distance progress and deep-learning adequacy remain
unestablished. Whole-lap summaries are descriptive, never predictive inputs.

## Load and compare another session

Choose **Carica file** in Data Explorer to upload CSV/Parquet. Use
**Mappatura colonne e unita** to declare names/units and press **Applica mappatura**.
That mapped session becomes available to the analytical pages and comparison
selectors for the current Streamlit session. Local files in `data/raw/` or
`data/demo/` are also discovered. There are no startup downloads.

In **Telemetry Comparison**, choose sessions A/B and two positive-duration time
windows. Select compatible channels and use **Salva finestra A/B** to retain a
selection in memory. Relative axes preserve each window's actual clock and duration.
For GT7 on both sides, **Giri verificati** exposes the eight accepted source IDs;
plots clearly describe approximate alignment and disable unsupported time delta.
CSV exports are available for derived metrics, events and lap-level candidate features.
Full-lap aggregates are retrospective and must not be used as causal progressive inputs.

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
```

For a core-only installation omit the two historical DL training modules with
`--ignore=tests/test_model.py --ignore=tests/test_evaluation.py`. Real-file tests skip
if local raw datasets are absent. In VS Code, **Testing** discovers pytest tests.
Optional browser checks use the installed `websockets` package and local Chrome:
`python -m scripts.smoke_app --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`.
Screenshots/logs stay under ignored `artifacts/`; the temporary server/browser stop afterward.

## Reports

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
