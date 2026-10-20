# v0.5 release report — 20 October 2026

## 1. Completed development

v0.5 adds six dedicated analytical pages on the stable local-data foundation:
Session Overview, Driver Inputs, Vehicle Dynamics, Tyre Analysis, generalized
Telemetry Comparison and Position Analysis. Data Explorer continues to load local
and uploaded CSV/Parquet, and now makes uploaded/manual-mapped sessions available
to all analysis pages. Source selection, caching, gap-aware charts, exports and
capability explanations are shared.

The release implements observed-time statistics, configurable pedal occupancy,
complete/partial braking events, entry-speed summaries, source-scale steering
activity, four-corner analysis, saved session windows and guarded lap comparison.
A second real telemetry collection was downloaded, pinned and audited: GT7 Trial
Mountain / Porsche 962 C. Eight laps pass recorded-data consistency validation.
Candidate whole-lap features and target/eligibility metadata prepare future work;
no new supervised model or Keras architecture was trained/redesigned.

## 2. Repository preparation and commit status

- Initial branch: `feat/sim-telemetry-v04`; working tree **clean**.
- Verified local v0.4 head: **`ae3c807`**. It is recoverable in its original branch.
- Remote metadata was fetched before development. The fetched remote v0.3 branch
  remained `4fcaf9f`; remote main remained `d16dddf`. Local v0.4 had its two local
  commits over remote v0.3 and no corresponding remote/upstream branch. It was
  not assumed to exist on GitHub.
- Created **`feat/sim-telemetry-v05` directly from `ae3c807`**. No branch deletion,
  checkout over user edits, reset, history rewrite, push, merge or PR occurred.
- Component commits:
  - **`d743747`** — observed-time session and driver-input analytics.
  - **`ff29e05`** — GT7 validation, comparison and readiness contracts.
  - **`c994b59`** — analytical pages, shared source management, final edge-case
    corrections and UI/browser coverage.
  - **`8fb5512`** — expose GT7 source rotational wheel channels in tyre analysis,
    with the corresponding real-source UI check.
- Documentation and reproducible measured evidence are committed after those
  functional components. The final Git HEAD includes the release report.
- Git metadata operations used the workspace-specific safe-directory override and
  approved elevated execution as required by the sandbox. No global Git setting
  or default branch was modified.

Existing Python 3.11.9 `.venv` was reused. **No new dependency installation or
dependency-file changes were necessary.** NumPy/Pandas/Plotly/Streamlit supply the
new functionality. The installed `websockets` package and local Chrome support
optional browser checking. Global Python and large DL packages were untouched.
The F5 launch and interpreter settings are byte-identical to v0.4.

## 3. Added and modified files

Added analytics modules: `timebase.py`, `driver_inputs.py`, `overview.py`,
`channels.py`, `comparison.py`, `position.py` and `readiness.py` under
`motorsport/analytics/`. Added `motorsport/ingestion/gt7_importer.py` and
`motorsport_ui/telemetry.py`.

Added pages:

- `pages/10_Session_Overview.py`
- `pages/11_Driver_Inputs.py`
- `pages/12_Vehicle_Dynamics.py`
- `pages/13_Tyre_Analysis.py`
- `pages/14_Session_Comparison.py`
- `pages/15_Position_Analysis.py`

Modified `streamlit_app.py`, `pages/00_Data_Explorer.py`, `motorsport/pipeline.py`,
normalization and package version. Added `scripts/download_gt7.py` and
`scripts/audit_v05.py`; extended `scripts/smoke_app.py`. Added advanced analytics,
comparison/readiness and UI test modules. Updated README and CHANGELOG.

New documentation: dataset selection, architecture, ML/DL readiness and this release
report, plus `GT7_MANIFEST_V05.json` and `DATASET_MEASUREMENTS_V05.json`.
Historical v0.4 reports remain unchanged. Raw telemetry, research downloads,
screenshots, caches and generated artifacts remain excluded from Git.

## 4. Architecture and analytical methods

`load_session` still handles general CSV/Parquet; `build_session` now also accepts
raw frames and independently checked lap metadata from an adapter. The GT7 adapter
handles packet scales and target consistency without changing general analytics.
Every `TelemetrySession` retains raw and canonical frames, source metadata,
quality reports, validated laps and session identity. Additional analytical
functions are independent of Streamlit.

Observed-time weights use positive finite forward intervals Δt, excluding intervals
above `max(1 second, 10 × median positive Δt)`. Repeated timestamps have zero dwell;
the final duplicate governs the next positive interval. The terminal sample adds
no invented time. Missing clock rows break support; window selection preserves
interior missing-time rows instead of bridging them. A backward clock step disables
duration-weighted metrics for that frame to avoid overlapping epochs.

Temporal mean = Σ(w×value)/Σw on channel-valid support. Pedal-use percentage =
100×Σw(condition)/Σw on valid 0–100% values; the covered seconds are exported.
Sample means remain separate. Thresholds and minimum event duration are configurable.
Braking events require contiguous supported intervals above threshold; completeness
requires witnessed onset and release. Duplicate clock rows do not fragment events.
Entry speed is the observed onset sample, and reported entry mean/max use complete
events. Steering activity is absolute variation per supported second in source
units, not calibrated steering effort or driver workload.

Session-window comparison preserves relative seconds without stretching or
inventing lap labels/time delta. Unknown-unit channels across different source
sessions are excluded unless an explicit shared unit reference exists. Up to 20
windows can be saved in Streamlit session state. Laps require accepted boundaries;
driven-distance fraction plots are retrospective approximate alignment. Cumulative
delta additionally requires a verified common track-distance reference and strictly
ordered, gap-free distance/time; neither current real dataset supplies it.

Plots use at most 5,000 selected rows, or 3,500 for dynamics scatter. Histograms
aggregate the full dataset. Render-only breaks avoid continuous lines through
acquisition gaps. The source cache uses file signatures and invalidates registered
local sessions after file replacement. Full resolution is preserved for metrics.
See [ARCHITECTURE_V05.md](ARCHITECTURE_V05.md) for formulas and function contracts.

## 5. Original dataset results

Measured with default thresholds: throttle >90%, brake >5%, overlap throttle >5%
and brake >5%, minimum observed brake event 0.1 s.

| Measurement | Actual result |
|---|---:|
| Source shape | 116,987 × 86 |
| Recorded simulator-time span | 1,827.078 s |
| Observed support | 1,824.718 s |
| Excluded gap | 2.360 s |
| Repeated clock steps | 1,245 |
| Sample mean speed | 144.863175 km/h |
| Time-weighted mean speed | 144.860349 km/h |
| Throttle above 90% | 64.649606% of valid observed time |
| Braking above 5% | 13.162198% |
| Pedal overlap | 1.022733% |
| Brake events, observed / complete | 241 / 240 |
| Mean / maximum complete-event entry speed | 164.540972 / 259.412262 km/h |
| Validated complete laps | 0 |

Both lap fields remain constant zero. Position is treated as an integrated source
trajectory with unverified drift/accuracy. No geometric lap identification, official
times, tyre degradation or setup causality is inferred.

The original Downloads file and its working copy still have SHA-256
`fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`.

## 6. Dataset research and integration results

Public Hugging Face, Kaggle, Zenodo, GitHub and academic sources were researched.
The selected GT7 bundle downloaded successfully: **29,122,896 bytes**, including
unchanged source files, card and auxiliary tables. It contains **95,796 raw rows
and 114 measured columns**, one driver/session/car/track. Its pinned revision and
all file hashes are versioned in the manifest; raw bytes are not in Git.

Accepted source lap IDs: **2, 3, 4, 5, 6, 11, 13, 14**, with packet target times
**103.712–108.650 s**. Validation checks timer monotonicity, reset/boundary coverage,
distance continuity, counter agreement and the next group's stable last-lap target.
Other source groups are rejected with reasons. The last file is not promoted to
a complete lap without a subsequent target. This is data-consistency validation,
not official sporting validity or transponder certification.

GT7 session time is host capture time: **2,038.917117 s** span and **1,598.577043 s**
observed support, with six large gaps. Accepted lap timing uses the separate
simulator timer; host capture duration is never substituted for a final lap target.
Pedal bytes convert explicitly to percent. Source-reported world x/z positions,
temperatures and suspension units are supported where documented; body-motion and
derived steering scales remain unverified. Quaternion fields do not become heading.

ACGym is the larger future acquisition candidate; only its listing/card and one
six-row human-session summary were inspected, not its raw laps. The inspected ESRL
CSV contains **476 aggregate rows from 124 PID values at Laguna Seca**, differing
from the repository's advertised historical study; it cannot provide causal raw
prefixes. Other candidates have unverified licenses, timing sequences or raw inputs.
The selected GT7 source carries publisher-declared CC-BY-4.0 attribution, documented
with its stated scope. Public access is never treated as blanket redistribution
permission. See [DATASET_SELECTION_V05.md](DATASET_SELECTION_V05.md).

Capabilities are based on data/validation. Both integrated sources support session,
time-window and source-position analysis. GT7 also supports verified targets and
approximate lap signal comparison. Both have **false supervised ML and progressive
DL eligibility** under the conservative independent-coverage gate; current eight
GT7 laps are a small integration case study, not an adequate generalization dataset.
Feature exports are explicitly full-lap retrospective. Future evaluation should
hold out complete sessions chronologically and keep each lap's prefixes together;
see [ML_DL_READINESS_V05.md](ML_DL_READINESS_V05.md).

## 7. Actually executed validation

Final applicable full suite:

```text
.venv/Scripts/python.exe -m pytest -q tests
84 passed, 92 warnings in 47.20s

.venv/Scripts/python.exe -m pip check
No broken requirements found.
```

All real-file tests ran locally; there were no skipped tests in that full run.
Coverage includes irregular clocks, duplicate and missing timestamps, gaps,
threshold usage, onset/release fragments, duplicate-safe event continuity, exact
byte-pedal full scale, invalid samples, window selection/relative alignment,
unit compatibility, guarded lap deltas, four-corner discovery, position validity,
capability gates, validated/rejected GT7 laps, unchanged real inputs, registry
invalidation, all new pages with missing channels and both real datasets, and the
entire unchanged historical test suite.

Components were tested incrementally: 35 relevant tests after initial analytics;
34 after the initial source/comparison contracts; then progressively expanded full
and UI suites, culminating in the result above. Development checks exposed and
corrected duplicate-clock event fragmentation, byte-scale floating-point overshoot,
missing-time window bridging and stale registered-file caching. A navigation
filename collision was resolved with the unique new comparison module/route.

`python -m scripts.audit_v05` generated measured evidence successfully.
`python -m scripts.download_gt7` verified the existing local bundle without
overwriting any file. Every manifest file was hashed again; all hashes match.
VS Code JSON parsed and `git diff --check` found no whitespace errors. Git diff
against `ae3c807` confirms **no changes** to `.vscode`, historical analytics/SVR,
the prediction package or the five preexisting historical test modules.

The final Chrome headless smoke command completed with exit code 0, checked local
HTTP homepage/health **200**, rendered all six new original-data pages, selected
GT7 in a real browser, and rendered its overview and validated-lap comparison.
Screenshots inspected include overview, inputs, dynamics, tyres, window comparison,
source trajectory, GT7 overview and GT7 lap comparison. The corrected input counts,
source-unit warnings, coordinate marker, eight-lap workflow and disabled cumulative
delta were visible. Screenshots/logs stay in ignored `artifacts/*_v05.png`.
The smoke script stops its temporary server and browser after completion.

Early attempts at browser dropdown automation failed because the installed
Streamlit uses different controls than assumed. Actual rendered DOM was inspected
and real CDP mouse events then completed the final check. These were automation
selector failures, not claimed successful application tests. No final automated
test or browser-smoke failure remains unresolved.

## 8. Acceptance and known limits

| Criterion | Evidence / status |
|---|---|
| AC1 Offline VS Code launch | Existing F5/interpreter settings unchanged and valid; equivalent Streamlit startup and legacy-import-blocked tests pass. Physical F5/debugger UI interaction was not automated. |
| AC2 Overview on original | Full-data metrics and real browser rendering passed. |
| AC3 Inputs/dynamics/tyres | Real original and GT7 script/widget tests passed; original pages visually inspected. |
| AC4 Window comparison | Relative-time comparison, saved selections and compatible-unit guards tested; no window lap-time delta. |
| AC5 Position | Real trajectory, marker/coloring, finite-position diagnostics and explicit drift/accuracy limitations rendered. |
| AC6 Missing/unavailable features | Synthetic missing/constant fixtures and real lap-mode guards pass. |
| AC7 Dataset discovery | Five sourced candidates documented; GT7 bytes integrated and eight targets validated. |
| AC8 Capability assessment | Data-based flags and reasons shown/exported for both sources. |
| AC9 Historical models | SVR/Keras/feature/analytics source unchanged; historical tests pass. |
| AC10 Applicable tests | 84 passed; 92 known historical Keras/NumPy deprecation warnings. |
| AC11 Sources unchanged | Original/copy and all downloaded GT7 hashes match their baselines. |
| AC12 Recoverability | v0.4 branch retained; separate v0.5 component and documentation commits; no remote publication. |

The 92 warnings concern historical Keras/PyTorch NumPy copy-keyword compatibility;
they do not correspond to failed tests or a `pip check` incompatibility. A fresh
empty environment and remote GitHub CI were not executed. The OS upload picker
was not exercised in Chrome; upload bytes/mappings and shared source registration
are covered at reader/widget levels. Legacy FastF1 downloads were not tested.

Neither real dataset supplies verified common track geometry or enough independent
lap sessions for robust ML/DL evaluation. Unknown units remain unknown. Saved
windows and uploaded sources are scoped to the current Streamlit session; CSV
exports are the persistent handoff. Threshold-sensitive event counts and observed
time estimates are defined analytical measurements, not ground-truth coaching labels.

## 9. Exact run and test instructions

Open `C:/Users/stefa/Desktop/EPICODE/CAPSTONE PROJECT` in VS Code. In **Run and
Debug**, choose **Motorsport Telemetry Analyzer**, then press **F5**. The `.venv`
interpreter is configured. If VS Code retains a previously selected interpreter,
select `.venv/Scripts/python.exe` once with **Python: Select Interpreter**.

Open **Session Overview** and select the original file or GT7 in **Dataset
analizzato**. Use the dedicated pages for inputs, dynamics, tyres and trajectory.
For other files, upload/map in **Data Explorer** first. In **Telemetry Comparison**,
choose sessions A/B, intervals and compatible channels; save windows if needed.
For GT7 on both sides, select **Giri verificati** and source lap IDs. Keep the
approximate-alignment and unsupported-delta explanations with any exported result.

VS Code **Testing** discovers pytest automatically. The equivalent terminal command
from the project folder is:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.audit_v05
```

On a core-only installation, omit the two optional historical DL test modules with
`--ignore=tests/test_model.py --ignore=tests/test_evaluation.py`. On another machine,
copy the original Parquet separately and run the explicit `scripts.download_gt7`
command for the pinned public bundle; tests requiring absent raw files will skip.

## 10. Recommendations for v0.6

Use the GT7 subset to validate feature/target joins, quality filtering and grouped
evaluation code with simple baselines, preserving its small single-session scope.
Acquire a bounded, provenance-tracked ACGym human subset spanning several sessions
and drivers; audit units, time continuity, complete targets and track metadata
before migration. Clarify the ESRL aggregate-table license before reuse and inspect
its processed labels for leakage. Reserve whole chronological sessions before
building any prefix dataset. Migrate historical SVR/Keras only when the data and
evaluation design support the intended claims.
