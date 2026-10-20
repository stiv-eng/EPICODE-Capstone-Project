# v0.4 release report — 20 October 2026

## A. Development summary

Motorsport Telemetry Analyzer now opens without simulator access and analyzes the
real local Parquet attachment. The new Data Explorer supports cached local files
and in-memory CSV/Parquet uploads, explicit source mappings and units, metadata,
raw/canonical previews, quality diagnostics, full-session metrics, selectable
signals, chart-only downsampling and an optional position trace. Complete laps
are exposed only after boundary validation. The real attachment supports session
analysis; its lap information is insufficient for validated lap analysis.

The homepage and navigation describe the simulator-independent direction.
Historical Formula 1 dashboards are available through an opt-in legacy group.
Existing SVR/Keras features and models have been preserved for later migration.
No v0.5 features, supervised training on this attachment, pushes, merges or PRs
were performed.

## B. Repository and environment preparation

### Initial state and recovery

- Workspace: `C:/Users/stefa/Desktop/EPICODE/CAPSTONE PROJECT`.
- Initial branch/status: **not applicable**; the supplied folder had no `.git`
  directory and `git status` returned “not a git repository”. It contained the
  application, five historical test modules, `.venv`, local FastF1 cache,
  `.vscode/launch.json` and `diagnose_fastf1.py`.
- Initial source files were archived before modifications in
  `artifacts/baseline_before_v04_20261020_204501.zip` (ignored by Git).
- Remote branch heads were inspected using `git ls-remote`, then fetched from
  `https://github.com/stiv-eng/EPICODE-Capstone-Project.git`.
- Verified v0.3 head: `4fcaf9f1eaf6e288fdb5aef2b23128f24508963e` on
  `origin/feat/streamlit-capstone-v03`. Its latest change fixes telemetry extraction
  from FastF1 Lap objects. Remote main was
  `d16dddf0dfc2adfe6f2ce5557d0bae7dcd954697`.
- Git was initialized on **`feat/sim-telemetry-v04`**, based on that verified v0.3
  commit. The index was read without checking out or overwriting workspace files.
- Local differences were inspected and preserved, including changes already in
  `motorsport_ui/common.py`, `motorsport_prediction/data.py`, launch settings,
  diagnostics and encoding differences. A synopsis tracked remotely was already
  absent locally; this preexisting absence is recorded in the baseline commit.
- Local baseline commit: **`a47945d`**, “chore: preserve supplied workspace before
  v0.4 development”. It is a child of the verified v0.3 head. Release changes are
  committed after this baseline on the same development branch.
- Local branches: `feat/sim-telemetry-v04`; fetched refs include remote main and
  remote v0.3. No local main was checked out or changed. No branches were deleted,
  no history rewritten and no user modifications discarded.
- The sandbox account required a per-command Git `safe.directory` override for
  this specific workspace; no global Git configuration was changed. Git metadata
  writes and remote access used approved elevated execution where necessary.

### Python environment

The valid existing `.venv` was reused: **Python 3.11.9, 64 bit, Windows**. All core
and historical dependencies were already installed. **No packages were installed
or reinstalled**, and the global Python environment was not modified.

| Package | Installed version |
|---|---|
| numpy | 2.4.6 |
| pandas | 2.3.3 |
| pyarrow | 26.0.0 |
| plotly | 6.9.0 |
| streamlit | 1.66.0 |
| scikit-learn | 1.9.1 |
| pytest | 9.1.1 |
| keras | 3.15.1 |
| torch | 2.14.1 |
| fastf1 | 3.8.3 |

`requirements.txt` now contains the core local-analysis dependencies.
`requirements-extension.txt` includes core plus optional historical FastF1,
Keras/PyTorch and model-artifact support. `pip check` reports **No broken
requirements found**. Historical Keras/PyTorch tests emit 92 NumPy copy-keyword
deprecation warnings; there are no failing tests or reported dependency conflicts.

### VS Code and directories

The first launch profile in `.vscode/launch.json` is **Motorsport Telemetry
Analyzer**, using `debugpy`, module `streamlit`, arguments `run streamlit_app.py`,
workspace working directory and integrated terminal. The existing launch profile
is preserved. `.vscode/settings.json` points at `.venv/Scripts/python.exe` and
enables pytest. Installed extensions include Python and Python Debugger
(`ms-python.debugpy-2026.6.0-win32-x64`); a separate debugpy wheel is not necessary
for VS Code's extension-provided adapter.

Added the missing `data/raw`, `data/processed`, `data/demo`, `motorsport` subpackages
and scripts. Existing UI and prediction packages remain. `.gitignore` excludes
raw/processed/demo data, `.venv`, caches, screenshots, backups and model artifacts.

## C. Actual dataset analysis

- Accessible original: `C:/Users/stefa/Downloads/telemetry.parquet`.
- Working copy: `data/raw/telemetry.parquet`, **55,558,924 bytes**.
- Both SHA-256 values:
  `fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`.
- **116,987 rows, 86 channels**, one row group; 83 float64 and three int64 columns.
- **1,827.078 seconds**, effective acquisition **64.029012 Hz**. Simulator time is
  nondecreasing, with **1,245 repeated values**, no backward steps, and one large
  **2.36-second gap** near the end. Wall-clock time has no repeated values.
- Missing cells: **0**; infinities: **0**; exact duplicate records: **0**.
- **14 constant channels**, including both lap channels, four brake temperatures,
  several settings, ambient temperatures and zero water temperature.
- Speed spans **1.005120–260.589294 km/h**, sample mean **144.863175 km/h**;
  RPM spans 76–8,396; gear spans 0–6. Pedals, steering, accelerations, velocities,
  wheel dynamics, tyre thermal/pressure/wear data and fuel are present.
- Attachment mappings: seconds from `timestamp`; `rpms`→`rpm`;
  `throttle`/`brake` 0–1→percentage; `steer_angle`→`steering`;
  `pos_z`→second planar canonical axis `pos_y`. Unknown source units are retained.
  Time and speed scales were cross-checked against wall-time and velocity norms.
- `lap_progress` and `completed_laps` are **always zero**. There are **zero
  validated complete laps**. Sixteen proximity visits to the initial point
  (including the initial fragment) show periodicity, but are not lap labels.
- Positions agree with integrated rotated vehicle velocities to approximately
  1e-13 source units per step. They are not an independent position reference;
  accumulated drift, unknown finish location and incomplete fragments prevent
  geometric lap certification in this release.
- Extreme slip tails and 12 negative rear ride-height observations are flagged
  for investigation without automatic removal.
- Embedded metadata contains Pandas schema/index information, with no verified
  car, track, driver, session, provenance, license or unit dictionary. Assetto
  Corsa / Imola identity remains **unverified**.

The full 86-column schema, measured statistics, timing and geometric investigation
are in [DATASET_AUDIT_V04.md](DATASET_AUDIT_V04.md). The report is reproducible with
`python -m scripts.audit_dataset`; no substitute telemetry was generated.

## D. Architecture

Independent file readers feed an explicit `SourceProfile` normalizer, then quality
diagnostics, conservative lap validation and session metrics. `TelemetrySession`
retains original and canonical frames plus metadata and reports. No UI imports
exist in that pipeline. Original rows and channel values remain recoverable;
canonical unparseable/nonfinite values become missing, and unsupported lap labels
remain only in the raw representation until boundaries are validated.

The Streamlit page caches bounded numbers of sessions, including source file
mtime/size or uploaded bytes and mappings in its keys. Full data feeds all
calculations. Plotly uses extrema-preserving chart views capped at 5,000 rows;
the verified default signal view contains 3,267 rows from all 116,987 samples.
Source coordinates are displayed with an explicit accuracy warning.

Six source files across `motorsport_prediction/` and the historical analytics/SVR
modules were compared with the pre-change ZIP and found byte-identical. Existing
legacy tests and page sources are preserved. Core and optional dependencies and
CI checks are separated. See [ARCHITECTURE_V04.md](ARCHITECTURE_V04.md).

## E. Executed validation and acceptance

Final execution:

```text
.venv/Scripts/python.exe -m pytest -q tests
44 passed, 92 warnings in 17.68s

.venv/Scripts/python.exe -m pip check
No broken requirements found.
```

Coverage includes Parquet path/bytes/metadata, CSV delimiter and single-channel
loading, unit conversions, datetime/timedelta origins, missing channels/time/
position, nonfinite and invalid samples, constants, duplicates, timestamp order,
quality statistics, complete and incomplete laps, inconsistent counters/progress,
gaps, implausible durations, duplicate source indexes, chart budgets and brief
peaks, real attachment normalization/immutability, UI controls/manual mappings,
and the original analytics, SVR and Keras/PyTorch tests.

`python -m scripts.audit_dataset` generated the measured audit successfully.
`python -m scripts.smoke_app --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"`
started a temporary local server, verified HTTP homepage and health responses
**200**, waited for actual rendered content via Chrome's local debugging endpoint,
and captured home, overview, signals and position views. All four screenshots
were inspected visually; the dark UI, navigation, quality warnings, four signal
plots and colored coordinate trace rendered successfully. Artifacts are local:
`artifacts/home_v04.png`, `explorer_v04.png`, `signals_v04.png`, `position_v04.png`.
The server and headless browser were stopped by the script. Browser execution
needed elevation because the sandbox blocked Chrome's GPU subprocess; the approved
local retry succeeded.

Both VS Code JSON files parsed successfully. `git diff --check` found no whitespace
errors. Ignore rules were checked for the real Parquet, `.venv` and screenshots.
Original and copied dataset hashes were checked again after tests. Historical
source preservation was verified against the initial ZIP.

| Criterion | Result and limit |
|---|---|
| AC1 F5 | Configured and JSON validated; interpreter/extensions present; equivalent Streamlit launch works. Physical F5/debugger UI interaction was not automated. |
| AC2 Offline startup | Passed: home test blocks legacy imports; real local explorer and browser smoke need no FastF1 services. |
| AC3 Real Parquet import | Passed: full attachment loaded. |
| AC4 Canonical fields | Passed: declared units/mappings tested; timestamp quality issues remain flagged. |
| AC5 Measured quality report | Passed: generated from actual bytes with full schema. |
| AC6 Real telemetry graphs | Passed: script tests and inspected Chrome screenshots. |
| AC7 Missing channels | Passed: synthetic UI/unit fixtures remain usable. |
| AC8 Validated boundaries | Passed: incomplete/unreliable laps excluded; real lap controls unavailable. |
| AC9 Historical ML/DL | Passed: six source files byte-identical; historical tests pass. |
| AC10 Automated tests | Passed: 44 tests, including real integration; no skips in this local run. |
| AC11 Raw file preserved | Passed: original and copy hashes unchanged and equal. |
| AC12 Recoverable release | Local baseline ZIP and Git baseline/release commits on the development branch; no remote publication. |

CI workflow changes were prepared but **not run on GitHub**. Fresh-install behavior
in a second empty virtual environment was not tested; the existing valid project
environment was reused as requested. CSV/Parquet upload reading is tested via bytes;
the upload selector/prompt is tested, but an OS file picker was not exercised in
the browser. Legacy FastF1 remote downloads were not validated by this release.

## F. User instructions

1. Open `C:/Users/stefa/Desktop/EPICODE/CAPSTONE PROJECT` in VS Code.
2. In **Run and Debug**, choose **Motorsport Telemetry Analyzer** and press **F5**.
   The project interpreter is configured as `.venv/Scripts/python.exe`. If VS Code
   retains an earlier explicit interpreter selection, select this `.venv` once.
3. Select **Data Explorer**. The local `data/raw/telemetry.parquet` is listed and
   its audited profile is selected automatically after a content-hash match.
4. Inspect **Dataset e qualità**, then **Segnali** to choose signals and sample
   intervals, and **Posizione** to view the source-coordinate trace.
5. For a new dataset, choose **Carica file**, upload CSV/Parquet, and expand
   **Mappatura colonne e unità** if its names or units differ. Declare the mappings
   and press **Applica mappatura**. Canonical missing signals produce explanations.
6. **Giri** explains why this attachment has no certified laps. Another file with
   validated counter/progress transitions can expose complete laps and their
   telemetry. No partial fragments become valid laps.
7. Use the sidebar legacy checkbox only when you want historical Formula 1 pages.
   Their optional dependencies and FastF1 resources are separate from local data.

No PowerShell commands are needed for ordinary startup. Raw telemetry is excluded
from Git, so another machine needs a separate copy in `data/raw/telemetry.parquet`.

## G. Recommendations for v0.5

| Area | Attachment suitability | Missing requirements / next step |
|---|---|---|
| Lap Time Analysis | Insufficient for certified lap times | Real finish crossings or reliable counters/progress, complete boundaries, track identity and lap validity flags |
| Telemetry Comparison | Good for session windows; insufficient for certified lap alignment | Valid lap IDs, comparable distance/progress, consistent car/track/setup metadata |
| Driver KPI Analysis | Useful for exploratory session-level pedal/speed/steering distributions | Verified units/calibration; event/driver IDs and validated segments for comparable braking/cornering KPIs |
| Machine Learning | Useful for unsupervised signal exploration and pipeline development | Multiple sessions/drivers/setups, explicit targets and labels, quality filtering, session/lap-grouped splits |
| Dynamic Lap Time Prediction with Keras | Insufficient for honest supervised lap-time training/evaluation | Reliable final-lap targets, complete laps, causal distance/progress, many independent training/validation/test laps and consistent reference laps |

Prefer an exporter with simulator session/car/track metadata, source unit
definitions, monotonic high-resolution simulator time, valid lap counters and
normalized progress, lap validity/pit flags, and genuine world coordinates or
distance. A verified source export from Assetto Corsa, ACC, iRacing, or a documented
CSV/Parquet collection could supply these fields. Compare the replacement file
with this attachment using the same audit before selecting it for lap-dependent
features. Do not infer final lap targets from the current unvalidated proximity
periods or use them to train the historical Keras model.
