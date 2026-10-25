# Release v0.8.2 — Scope reset to Motorsport Data Analysis

The progressive final-lap-time prediction subsystem is removed from active code,
navigation, dependency declarations and CI. The surviving application provides
Session Overview, Data Explorer and Telemetry Comparison with the existing design,
selection semantics, measured-data calculations and shared hover/cursor. This
release adds no replacement predictor, new delta-time method or new dataset.

## Verified archive before removal

Incoming branch: `feat/sim-telemetry-v081`, HEAD `11c11f8`, with the delivered v081
changes uncommitted. Reverified **287 tests passed**, zero failed/skipped, 217
existing Keras/Torch warnings, 222.14 s. Preserved those changes in local commit
**`3b96553a10881ea654f5fe2a505cb7b3169d4d1d`** and created **`archive/progressive-laptime-ml-v081`**, then
`feat/scope-reset-v082`. No push, merge, reset, history rewrite or branch deletion.
The sandbox Git ownership mismatch required a per-command safe.directory setting;
global Git configuration was not changed.

The [recovery guide](archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md) documents a separate
worktree, exact commit, LF checkout for frozen hashes, original requirements and
manual backup of ignored datasets/models/paired signing keys. Git history alone
does not contain these ignored artifacts. The archival reference is local.

## Removed and retained

Removed **30 prediction implementation/UI modules**,
**5 prediction pages**, **20 dedicated
research scripts**, 5 obsolete mixed
browser/archive workflows, 19 dedicated test files,
the sequence dependency manifest and 160
prediction report/table/figure files. Every removed file exists in the archive
commit; the [reviewed file ledger](archive/RETIRED_FILES_V082.json) lists individual
paths. Removals were classified by actual dependencies and purpose, not directory
name alone. Ignored files were not moved or deleted.

The removal covers original/dense/remaining SVR, stop-aware corrections, historical
prediction baselines, ordered Ridge, Keras GRU, model stores/loaders, feature
experiments, training/selection/evaluation, experimental replay, diagnostics,
prediction caches/state and ML navigation. Existing analysis source/chart caches
remain. Metadata uncertainty now describes source limitations without obsolete
ML-corpus messages.

Preserved: CSV/Parquet/MoTeC/GT7 adapters, raw columns, declared units,
normalization, timing validation, verified laps, session windows, driver inputs,
G-G equal scales, tyre analysis, recorded Cockpit inspection, available positions,
stable comparison ordering/identities/colors and browser-only synchronized cursors.
The original optional FastF1 lap/stint/telemetry/map analysis remains; its
prediction pages are gone. Existing descriptive regression/distance-comparison
helpers are retained as analysis, with no new delta method.

## Dependency cleanup

Removed scikit-learn/joblib from core requirements; Keras/Torch/joblib from the
optional extension requirements; removed the obsolete sequence requirements and
the ML legacy CI job. Core is NumPy/Pandas/PyArrow/Plotly/Streamlit plus pytest for
verification. Optional FastF1 remains for retained Formula 1 analysis. Installed
historical packages were not uninstalled, preserving the old environment for
recovery. Normal startup does not import prediction packages or inspect models.
Both VS Code F5 configuration files are byte-identical.

## Data regression and cleanup issue found

All **73 baseline source signal hashes and overview summaries are unchanged**.
All **205 original Barcelona lap trajectories and verified times match** the
pre-cleanup inclusive data contract. **244 local files / 912,978,399 bytes** of
raw data, model binaries and F5 files are verified unchanged; five private signing
keys stay at their existing paths. No key contents or binary models are committed.

The previous analysis UI exposed only **204** Barcelona laps because it omitted
the already validated v071 **1 ms target-rounding tolerance**. The ML loader
accepted a half-ms boundary that the analysis loader did not. The new small
`motorsport/ingestion/barcelona.py` adapter moves source integrity/path utilities
out of the retired ML package and applies that same inclusive timing setting.
The affected WL stint now exposes 8 instead of 7 laps, making all 205 accessible.
This changes no raw signal, existing valid timing or analytical calculation.
See [exact regression evidence](DATA_ANALYSIS_REGRESSION_V082.json) and
[frozen pre-cleanup measurements](DATA_ANALYSIS_BASELINE_V082.json).

## Automated tests and actual Chrome

**167 tests passed**, zero failed/errors/skipped/warnings,
**122.61 s**. Dedicated prediction cases were deliberately
retired: **128 cases**, individually recorded in
[the test ledger](archive/RETIRED_TESTS_V082.json). The data-only half-ms timing
regression was relocated from the mixed ML suite. Eight new scope/compatibility
checks were added; the original launch guard was renamed and preserved. Mixed
tests lose only assertions protecting the deliberately removed ML gates/feature
table; their data/geometry/hover/timing assertions remain.

The surviving suite protects ingestion, normalization, timing, filtering, lap
ordering, source/selection state, G-G scaling, track geometry, hover/cursors and
the original F5 files. A clean subprocess starts all four active local pages with
Keras/Torch/sklearn/joblib imports and model file/stat access forbidden. The same
guard is enabled in every browser-server run. No ignored file is moved to make
this test pass.

| Chrome scenario | Workflows | Render budgets | Performance records | Expected removed-route 404s | Expected page-not-found messages | Unexpected errors |
| --- | --- | --- | --- | --- | --- | --- |
| v082 | 56 | 40 | 1 | 4 | 2 | 0 |
| uploads | 34 | 0 | 0 | 0 | 0 | 0 |
| fixtures | 4 | 4 | 0 | 0 | 0 | 0 |

The four 404 network requests and two Streamlit page-not-found console messages
come exclusively from deliberately opening `/ml` and `/replay`. They are retained
in [console evidence](UI_BROWSER_CONSOLE_V082.json), separately classified from
unexpected errors; none is silently discarded. Normal surviving workflows have
zero unexpected console errors and zero runtime exceptions. The removed pages
cannot execute; normal navigation exposes only analysis.

Browser checks retain GT7/Monza/Barcelona sections and comparison, real pointer
and keyboard cursors, zoom/pan alignment, stable selection rows, unavailable/gap
handling, 20 hover updates without Python rerun/numerical mutation, responsive
480/960/1600 layouts, actual Parquet/CSV file uploads, stationary position and
clockless/legacy renderer fixtures. Shared hover/render implementation files are
unchanged. Compileall, pip check and whitespace checks pass. See
[verification](VERIFICATION_V082.json) and [full browser evidence](UI_BROWSER_V082.json).

## Launch and future direction

Use the unchanged VS Code **Motorsport Telemetry Analyzer → F5**, or:

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open Data Explorer, choose a recording or upload CSV/Parquet, then inspect signals
or compare verified laps/windows. No prediction model artifacts are required.
The [active feature list](ACTIVE_FEATURES_V082.md), [architecture](ARCHITECTURE_V082.md)
and updated README describe this scope.

The research direction is closed. Two conditional future options are easier
recording selection and better import mapping guidance, evaluated explicitly for
user problem, simplest alternative, practical benefit, required evidence and a
small feasibility check in [the recommendation](NEXT_RELEASE_RECOMMENDATION.md).
The user will choose a direction separately; neither is started here.

## Acceptance

| Criteria | Evidence |
| --- | --- |
| AC1, AC12 | Exact archived commit/reference, preserved incoming work, separate-worktree recovery instructions |
| AC2 | Protected local file digests unchanged, ignored assets/keys kept, manual backup inventory |
| AC3, AC4 | Reviewed source/page/workflow removal, import-graph guard and retired-route checks |
| AC5–AC7 | Source/overview/lap regression, existing analysis tests, real browser geometry and cursor checks |
| AC8, AC9 | Lean dependency declarations/CI, guarded startup with model packages/artifacts inaccessible |
| AC10 | Complete surviving/new test suite and three actual Chrome scenarios |
| AC11 | Updated README/CHANGELOG, active features, architecture, archive and recommendation |
