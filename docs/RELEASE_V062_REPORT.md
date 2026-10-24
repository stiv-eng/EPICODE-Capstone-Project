# Release v0.6.2 report

Date: 2026-10-24 (Europe/Rome). Local branch: `feat/sim-telemetry-v062`.
Verified parent release: v0.6.1 commit **`c47fd4a`**, preserved on
`feat/sim-telemetry-v061`. Initial working tree was clean. No remote release was
assumed and no user modification needed replacement.

## Delivered summary

This release implements UI feedback FB-018–FB-023 and a separate evidence-based
ML health assessment (FB-024). It prioritizes validated examples, filters unusable
channel choices, corrects G-G data geometry, adds actual-position vehicle replay,
and moves comparison readouts outside the signals. Production predictive models,
features, splits, targets, inference and ML/replay pages are unchanged.

Final automated result: **172 passed, 92 warnings in 102.12 s**, no failures/skips.
Real Chrome result: **36 checks passed**, exit 0, HTTP homepage/health 200.
Frozen regression: **390 ACGym + 60 GT7 model-prediction rows unchanged** within
`1e-9 s`. Dependency check reports no broken requirements. Detailed evidence and
execution limits are in [UI_TEST_REPORT_V062.md](UI_TEST_REPORT_V062.md).

## Dataset selection and availability

GT7 is the preferred installed example because it has verified laps and compatible
source coordinates. ACGym recordings follow, then other available local files and
explicit uploads. No startup download is introduced.

The specific original `data/raw/telemetry.parquet` is hidden from the default
catalog only if its content matches the audited original hash. Its file remains
intact; a future different Parquet replacement with that name remains discoverable.
`include_original=True` is an explicit developer catalog path, not the principal
UI. Actual CSV/Parquet upload remains available, including the original attachment;
its exact known mapping is recognized on explicit upload. Generic Parquet ingestion,
normalization, canonical model and pyarrow remain unchanged.

`analytics.channels.usable_channels` provides one reusable actual-data predicate.
Signals, driver choices, dynamics/tyre families and map colors exclude unsupported
text/complex values and entirely nonfinite measurements. Constants remain usable.
Families/corners require genuine available channels; paired scatters require
simultaneous finite pairs. Empty selectors are omitted and stale widget choices
are pruned without changing shared dataset/lap/window state.

## Sidebar and G-G geometry

Overview and Comparison now use supported Streamlit 📈 / 📉 page icons, matching
the existing sidebar mechanism. Real Chrome inspected their rendered navigation.

`gg_figure` checks comparable declared acceleration units, uses full finite
extents for common padded symmetric ranges, anchors Y to X at ratio 1 and constrains
both domains. A bounded responsive 660px container keeps the data area proportional;
equal outer figure dimensions alone are not treated as evidence.

Chrome measured GT7 square data areas of **430x430**, **263x263** and **212x212 px**
at viewport widths 1600, 960 and 480. ACGym measured about **433x433 px**. Actual
X/Y pixel-per-unit ratios were 1 within floating point/tolerance. Valid extremes
remain in axis limits; downsampling affects only displayed points. GT7 retains
uncalibrated source-unit labels; ACGym uses its declared g units.

## Vehicle position and heading

The map retains colored connected trajectories and adds a small six-piece top-down
vector car. Pixel-sized Plotly shapes anchor to actual selected source X/Y and keep
their size when zoom changes. The body/front artwork starts along +X and rotates
in mathematical XY, with Plotly handling SVG screen-Y conversion.

Measured heading is accepted only under a complete verified declaration of channel,
units, zero vector, physical rotation sign, planar handedness, canonical coordinate
columns and provenance, consistent with the channel's declared unit. A pure helper
also supports explicit axis-swap/reflection transforms. No current real adapter
provides that trustworthy contract; its transformations are tested synthetically.
Unlabelled angles and GT7 quaternion components are not treated as heading.

Real trajectories use the explicitly labelled estimate `atan2(dy, dx)`. The next
packet must be adjacent in the same full-resolution continuous fragment; temporal
gaps/repeats, missing positions, lap changes, removed source rows and existing spatial
jump guards break adjacency. A final packet may use a valid labelled backward
difference. Stationary/near-zero motion and isolated samples have no invented angle:
a neutral marker shows actual XY even if no connected trajectory can be drawn.

Line segmentation and direction share `position_adjacency`, avoiding inconsistent
boundary rules. `trajectory_base` caches the line/adjacency/stats; a regression test
confirms a marker slider update invokes segmentation only once. Source/selection
revision resets incompatible zoom while preserving it during marker updates.
Using the next packet for this retrospective visual estimate never changes causal
ML frames/features. ACGym still explains absent XY rather than reconstructing a map
from race rank or progress.

## Comparison hover/readout

The old native unified hover still floated near inspected traces. Instead of
assuming an offset setting solved that problem, a small offline HTML component
now reserves a side column outside the chart rectangle. It inlines the already
installed Plotly runtime, suppresses native floating labels while retaining hover
events, and displays the actual event value, unit, measured relative timestamp,
source/lap/window identity and selection color. Values persist after unhover.

The existing shared Plotly legend remains once per selection across all channel
subplots. Its anchor/top margin account for wrapping at the smaller plot width.
The component escapes embedded JSON/untrusted labels and uses `textContent` for
readouts; no CDN or additional frontend package is added.

Actual mouse hover over GT7 speed/throttle/brake lap plots, speed/brake windows,
and ACGym laps produced two readout entries with no floating labels. Readout left
edge was outside chart right edge. Final screenshots were inspected, including:
`artifacts/v062/gt7_lap_hover_{1,2,3}_v062.png`,
`gt7_window_hover_{1,3}_v062.png` and `acgym_lap_hover_v062.png`.

Tradeoffs are explicit: the iframe repeats the installed Plotly bundle and reserves
horizontal space; narrow touch/accessibility behavior is not certified. It does
not send hover events back into Python. Streamlit's generic iframe wrapper emits
feature-policy/sandbox warnings; no captured runtime exceptions/console errors
occurred in the successful workflow.

## Machine Learning health assessment

The [full engineering/student report](ML_HEALTH_ASSESSMENT_V062.md) directly answers
all four diagnostic questions and distinguishes structural issues, model/feature
limitations and dataset limitations. Calculations are retained in the new
[JSON evidence](ML_HEALTH_EVIDENCE_V062.json) and
[checkpoint/lap/session/participant CSV](ML_HEALTH_GROUPS_V062.csv).

Findings:

- No confirmed target, leakage, preprocessing or split implementation defect was
  found in the frozen export-based experiment. All 55 source targets, split groups,
  six ACGym and six GT7 model/partition metric rows and allowed ACGym baselines
  reproduce. Group/source-clock limitations remain explicit.
- SVR's ACGym test MAE is **6.743072470361 s**, RMSE **10.837559352607 s**, bias
  **-3.481267678433 s** (rounded here to the frozen report precision). Its median
  absolute error is 3.423 s, but one AB recording contributes **61.62%** of total
  absolute error. This is 75 correlated prefixes from 15 laps in three groups.
- Early predictions cluster near central training times; slow laps are underestimated.
  At 10 s, SVR test predictions span only 120.549–121.478 s. Specific difficult laps
  contain measured slow/stationary segments, including delay after the last 60 s
  checkpoint. No difficult lap is removed or assigned a speculative incident cause.
- Fixed development-only fits show training/validation gaps, especially RF, and
  correlated aggregate features. These justify bounded future experiments but
  do not prove a particular replacement model, pure overfitting or that Deep Learning
  will win. GT7's previous-lap baseline beats selected SVR on its two frozen test laps.
- Independent data coverage is a major limitation, but the relative contributions
  of data size, feature compression, session shift and future uncertainty remain
  unresolved. Preserve current models, collect independent groups/new holdouts and
  preregister small development-only feature/phase tests.

`assess_ml_v062` fits exactly three existing fixed configurations on the development
training pool for descriptive training-versus-validation checks. No test telemetry/
labels enter those fits, no parameter variant is tuned or selected, no artifact is
saved, and outputs are allowlisted to separate v0.6.2 evidence. Sixteen original
frozen-evidence/model-store files remain hash-identical. No new Keras network,
Deep Learning phase or dataset acquisition occurred.

The independent frozen regression matches all prediction/target/error/baseline
columns at `1e-9 s`. Maximum prediction deviations are only
**2.842170943040401e-14 s ACGym / 1.4210854715202004e-14 s GT7**, consistent with
CSV roundoff. `motorsport/ml`, prediction packages, ML/replay pages and their UI
module have no diff from `c47fd4a`.

## Feedback completion

This is release traceability, not a replacement master feedback register. The
private register was not accessed or modified.

| Feedback | Status | Main files | Executed evidence | Limits |
|---|---|---|---|---|
| FB-018 | Implemented | `telemetry.py`, `explorer_source.py`; catalog/upload tests | Exact-original hide/replacement/fallback tests; GT7 default; actual browser original upload | File retained; explicit developer/upload access intentionally remains |
| FB-019 | Implemented | `streamlit_app.py` | Actual rendered navigation icon checks and screenshot | Uses platform emoji presentation |
| FB-020 | Implemented | `gg.py`, `dynamics.py` | Unit-range/anchor tests and four actual Chrome pixel-scale measurements | Unknown GT7 units remain uncalibrated; narrow figure has extra surrounding space |
| FB-021 | Implemented | `analytics/channels.py`, `widgets.py`, Signals/Inputs/Dynamics/Tyres/Position renderers | Finite/type/constant tests, family/corner filtering, empty/stale selectors and retained shared-state suite | Availability follows current selection; compatible units still require source declarations |
| FB-022 | Implemented | `analytics/orientation.py`, shared adjacency, `vehicle.py`, Position | Quadrants/vertical/reverse/boundary/heading tests; actual sample changes, pixel orientation, zoom and stationary browser checks | Real examples use labelled estimates; ACGym lacks compatible XY; measured heading tested synthetically |
| FB-023 | Implemented | `comparison_hover.py/.html`, `visuals.py`, Comparison page | Six actual multi-plot lap/window hover checks, outside-panel geometry, two legend entries, inspected screenshots | Desktop Chrome scope; extra inline runtime payload and reserved width; no mobile accessibility certification |
| FB-024 | Implemented assessment; predictive models unchanged | Separate audit script, evidence, health report, existing regression script/tests | Recomputed targets/splits/metrics/baselines; 3 fixed development-only diagnostic fits; 450 frozen prediction rows match | Dataset versus model causal contribution remains inconclusive; no optimization on old test |

## Known limits, data and launch preservation

All AC1–AC16 are covered within the explicit source/browser scope. Important
qualifications remain: ACGym has no usable world XY, no real dataset declares
trusted planar heading, current coordinate accuracy is source-specific, and desktop
hover validation is not a universal mobile/engine guarantee. The old FB-007
intermittent disappearance remains unreproduced; v0.6.2 does not claim a new root cause.

The original attachment SHA-256 remains
`fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`;
all 20 GT7 and 48 ACGym manifest hashes match. Existing model artifacts, frozen
results, source adapters, canonical model, Parquet/CSV support and dependency files
are preserved. VS Code launch/settings have no diff. The same offline Streamlit
module/entrypoint was exercised; an interactive F5 keypress was not automated.

## Files, commits and handoff

New code:
`motorsport/analytics/orientation.py`,
`motorsport_ui/{gg,widgets,vehicle,comparison_hover}.py`,
`motorsport_ui/comparison_hover.html`, `scripts/assess_ml_v062.py`,
`scripts/smoke_ui_v062.py`, `tests/conftest.py`, `tests/test_ui_v062.py`.

Modified code:
`motorsport/analytics/{channels,position}.py`,
`motorsport_ui/{telemetry,explorer_source,inputs,dynamics,tyres,position,visuals}.py`,
`pages/00_Data_Explorer.py`, `pages/14_Session_Comparison.py`, `streamlit_app.py`,
`scripts/smoke_app.py`, and the existing Explorer/advanced/v0.6.1 UI tests.

New documentation/evidence:
this report, `UI_TEST_REPORT_V062.md`, `ARCHITECTURE_V062.md`,
`ML_HEALTH_ASSESSMENT_V062.md`, `ML_HEALTH_EVIDENCE_V062.json`,
`ML_HEALTH_GROUPS_V062.csv`. Updated `README.md`, `CHANGELOG.md` and
`NEXT_RELEASE_RECOMMENDATION.md`. No dataset or historical module was removed.
Browser logs/screenshots and the standalone diagnostic figure remain ignored under
`artifacts/v062/`.

Local component commits:

- `927c172`: source-aware controls, square G-G, vehicle orientation and readout UI.
- `ef660fb`: neutral measured positions and validated-example fallback priority.
- `4f09b68`: safe ML health audit/evidence, 37 new tests and Chrome workflow.
- `e34dd6e`: release, architecture, validation and ML assessment documentation.
- A final portable-newline correction makes generated diagnostic CSV output clean
  on Windows without changing parsed values; its exact commit hash is available
  through `git log -1 --oneline`.

Final branch remains local with a clean working tree checked after committing.
v0.6.1 is an ancestor and its branch is intact. No push, merge, reset, branch
deletion, history rewrite or publication was performed.
