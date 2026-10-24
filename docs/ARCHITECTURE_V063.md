# Hover architecture v0.6.3

This presentation release extends [v0.6.2](ARCHITECTURE_V062.md). Source adapters,
lap validation, analytical formulas, model features, training, inference, splits,
artifacts and the offline F5 configuration are unchanged.

## Python API and data contract

`motorsport_ui/hover.py` owns three small public operations:

```python
render_chart(figure, mode='time', key='signals')
render_chart(gg_figure, mode='xy', key='gg')
render_figures([(signals, 'time'), (gg, 'xy'), (wheel_traces, 'time')], key='dynamics')
```

`prepare_figure` copies a figure, preserving its numerical arrays and geometric
constraints. It suppresses native labels with `hoverinfo='none'`, retains former
hover-template meanings as readout metadata, and creates an ordered selection
manifest. `figure_specs` serializes the prepared copies. Native Plotly binary array
encoding remains supported; the browser uses Plotly's decoded `_fullData` arrays.
No source frame or model is modified or added to component arguments.
When a source has no finite declared clock, Signals explicitly uses the source
sample index in XY mode, labels time as unavailable and draws no temporal cursor.
Dynamics preserves this mode when grouping its returned signal figures.

Temporal trace metadata contains `channel`, `unit`, `selection_id`, `tolerance`,
`ordered_time`, and optionally `sample_label` / `source_identity`. Actual source
row labels travel as customdata in Signals/Comparison. The comparison builder
creates IDs from **selection slot + source key + verified lap/window identity**.
The slot distinguishes even A and B choosing the exact same lap. Colors use those
IDs with deterministic collision resolution; each ID has one color across channels.
Labels are presentation text, never the lookup key. Explorer uses source session
identity plus its verified lap label within that source.

`signal_chart(..., render=False)` returns its bounded figure for grouping without
mounting a component. Dynamics uses this to put acceleration traces, G-G,
correlations and the selected wheel/slip family in **one component**. Only its
temporal figures synchronize time. Replay groups observed-prefix signals and
checkpoint history. ML groups its scatter and histogram; importance remains a
separate component next to its associated table/controls.

## Local runtime and lifecycle

`component()` reads `hover.html` and the already installed `get_plotlyjs()` bundle.
It creates a content-versioned directory under the OS temporary directory and
registers a Streamlit declared component serving `index.html` and `plotly.min.js`.
This needs no CDN, npm build, new dependency or Streamlit static-serving setting.
Only figure JSON travels in render arguments. The loader uses browser CacheStorage
with a content-hashed runtime URL and a Web Lock where available. Inspection of the
installed Streamlit 1.66 asset route found `Cache-Control: public` without a freshness
lifetime or validators; relying on HTTP cache alone still transferred the bundle
on remount in Chrome. Explicit cache lookup removes that repeated transfer. If
cache access is unavailable, a direct local-script fallback remains offline.
One iframe interprets one runtime for all its
figures; different components still have distinct JavaScript heaps/runtime objects.
Caching saves transfer, not all interpreter/memory cost.

The component implements Streamlit's ready/render/frame-height protocol. It never
sends a component-value message. Hover, arrows, zoom and pan do not invoke Python.
Render messages are queued; old Plotly figures and ResizeObservers are disposed
before replacing a selection. A new selection clears previous cursor/readout
state. Explorer still mounts one analytical section at a time. Legacy lap/stint
tabs became a section radio so hidden chart families do not mount eagerly.

The old `comparison_hover.py` name is a compatibility wrapper. Its standalone
`comparison_document` export uses the **same** HTML/JavaScript, with an embedded
runtime only for that standalone document. Production calls `render_chart` and
does not use the inline export. The obsolete second HTML implementation was removed.

## JavaScript interaction contract

`hover.html` separates mounting, nearest-sample selection, time cursor rendering,
temporal readouts, spatial/statistical formatting, and responsive layout:

1. `mount` creates a plot, a pointer-transparent SVG layer, and readout rows from
   the selection manifest. Rows are created once per render, in application order.
2. `plotly_hover` supplies the inspected channel or spatial point. Event point
   ordering never determines row order. Spatial templates are converted into plain
   text using `textContent`, including existing customdata and units.
3. Temporal pointer movement obtains the active subplot from its real X/Y axis
   domains, converts screen X with `p2c`, and schedules an update with
   `requestAnimationFrame`. `updateTime` shares that coordinate across temporal
   figures in the component.
4. `drawCursor` maps that coordinate through **each subplot's own** `c2p` and
   axis offsets. It draws one amber SVG line per Cartesian subplot within the
   visible axis range. It never adds Plotly traces/shapes or changes data arrays.
   Relayout, afterplot and resize redraw using the updated transforms.
5. `timeReadout` updates only existing row values. The panel follows the inspected
   subplot vertically on wide layouts, within the figure height. Missing selection
   values retain their row, label and color and show `N/D`.
6. `spatialReadout` shows the actual hover point/bin/category coordinates, unit
   labels and supported customdata. A small SVG ring highlights numeric XY points;
   distributions and category bars do not acquire an artificial time axis.

Cursor and last readout persist on leave. A cursor outside a newly zoomed range is
not drawn until its time is visible again. On a focused temporal figure, left/right
arrows step through recorded displayed timestamps. Focus has a visible outline;
readouts use live-region semantics. Comprehensive screen-reader and physical
touch-device certification remains future work.

### Measurement policy

Telemetry tolerance is **0.51 times the median positive time step in the original
selected frame**, computed before display sampling. Display decimation cannot
enlarge it. The nearest displayed real sample must be within that tolerance and
have a finite Y. Otherwise the row is unavailable; there is no interpolation,
forward-fill or bridge across a recording gap. Reported sample time may differ
from cursor time and is shown explicitly. Equal-time duplicates resolve to a
recorded displayed sample deterministically; they are not averaged.

Ordered finite timestamps use binary search. Unordered/missing timestamps use a
bounded linear nearest search without changing source order. Prediction history
uses its actual checkpoint spacing, explicitly labelled as history rather than
sensor samples. No hidden full-resolution copy is added to hover payloads merely
to avoid honest `N/D` states after downsampling.

Position line geometry, adjacency and heading rules remain unchanged. Endpoint
customdata now identifies **that endpoint's** source row and color measurement;
the far endpoint no longer repeats the segment-start measurement. The line's color
continues to mean its start measurement as previously documented. Interpolated line
interiors are not invented source samples. The selected car/neutral marker retains
its real source row and original orientation provenance.

## Chart audit

All applicable chart renderers below use the shared external readout. `Time`
means synchronized cursor within their component; `XY` includes categories and
distributions with context-appropriate coordinates/statistics and no time cursor.
There are **no intentional native-floating-hover exceptions**. Overview has tables
and metrics, not hover charts. Cockpit instruments keep their recorded-sample UI.

| Page / section | Chart family | Readout data | Mode / cursor | Validation / scope |
|---|---|---|---|---|
| Explorer / Signals | Stacked temporal channels and selected laps | Channel, units, lap, real timestamp/source row | Time / all panels | Real GT7 + ACGym |
| Driver Inputs (also standalone page 11) | Pedal/steering/RPM traces | Same measured signal contract | Time / all panels | Real GT7 + ACGym |
| Dynamics (also page 12) | Acceleration traces | g_lat/g_lon, declared source units, lap/time/sample | Time / shared with family | Real GT7 + ACGym |
| Dynamics | G-G | Lateral/longitudinal acceleration, units, speed if available, source row | XY / none; 1:1 geometry retained | Real GT7 + ACGym |
| Dynamics | Speed–lateral and steering–yaw correlations | Both coordinates/units, color, source row | XY / none | Available real GT7 + ACGym pairs |
| Dynamics | Selected wheel/load/slip/suspension family | Channel, unit, lap/time/source row | Time / shared with accelerations | Real available families |
| Tyres (also page 13) | Selected temperature/pressure/load family | Channel, declared unit, lap/time/source row | Time / all panels | Real GT7 + ACGym |
| Cockpit | Optional context traces | Recorded signals and source timestamp/row | Time / all panels | Real GT7 + ACGym; instruments unchanged |
| Position (also page 15) | Colored connected trajectory and car/neutral point | Actual endpoint XY, row, color-channel value/unit; marker XY/row | XY / point ring, no time cursor | Real GT7, synthetic stationary, original AppTest; ACGym unavailable explained |
| Telemetry Comparison / verified laps | Stacked channel overlays | Fixed A/B identities/colors, channel/unit, sample timestamp/row | Time / every channel | Real GT7 and compatible ACGym |
| Telemetry Comparison / windows | Stacked relative-window overlays | Fixed source/window slot, relative time/sample | Time / every channel | Real GT7 |
| Telemetry Comparison | Optional cumulative delta | Verified reference distance (m), delta (s) | XY / none | Guarded unavailable on current sources; existing formula tests retained |
| ML | Predicted versus actual scatter | Verified/predicted seconds, checkpoint, lap UID | XY / none | Real explicitly trained ACGym |
| ML | Error histogram | Error-bin coordinate (s), observed bin count | XY / none | Real ACGym calculated histogram bars |
| ML | Permutation importance bars | Feature category, validation MAE increase | XY / none | Real ACGym |
| Progressive Prediction | Causal observed-input traces | Prefix time, speed km/h, inputs % | Time / shared with history | Real trained replay, target-free payload |
| Progressive Prediction | Prediction/baseline checkpoint history | Checkpoint and predicted/baseline seconds | Time / shared with observed prefix | Actual history only; target reveal remains metrics-only |
| Legacy 01 / Lap times | Lap scatter and box distribution | Driver, lap/time, stint/tyre life; box values | XY / none | Offline shared-renderer/type fixtures; full FastF1 acquisition not exercised |
| Legacy 01 / Stints | Horizontal stint bars | Driver, chronological lap extent, stint, compound, best seconds | XY / none | Migrated; source reviewed, no new external session fetch |
| Legacy 01 / Regression | Degradation slope bars | Driver/compound, slope, stint, r², sample count | XY / none | Migrated; existing analytical tests retained |
| Legacy 02 | Five distance-aligned channel panels | Selection ID, distance, channel/units | XY / none: X is distance, not time | Migrated; offline family contract, no FastF1 workflow claim |
| Legacy 02 | Distance delta | Distance and cumulative seconds | XY / none | Rendering only; existing interpolation formula unchanged |
| Legacy 03 | XY track line + speed markers | Actual FastF1 XY and speed km/h | XY / point ring | Migrated; no geometry reconstruction |
| Legacy 04 SVR | Actual/predicted scatter | Existing targets, predictions, driver/lap hover fields | XY / none | Migrated; historical computations unchanged |
| Legacy 04 Evaluation | Stage MAE grouped bars | Stage, method, MAE seconds | XY / none | Migrated; category/bar fixture |
| Legacy 05 | Epoch loss/validation-loss chart (formerly Streamlit line_chart) | Epoch, series, Huber loss | XY / none: epochs are not seconds | Migrated to shared Plotly renderer; no Keras training experiment |
| Legacy 05 | Completion-percentage prediction history | Completion %, predicted/baseline seconds; finish-only target line | XY / none: X is progress | Migrated; causal/finish logic unchanged |
| Legacy 05 | Observed telemetry versus distance | Observed distance and speed | XY / none | Grouped with progress figure, unchanged causal prefix |

## Study guide

Start with `comparison_figure` in `visuals.py`: follow a selection's identity and
original-cadence tolerance into trace metadata. Then read `prepare_figure` and
`render_figures` in `hover.py`, and inspect the actual component arguments in
`tests/conftest.py::chart_specs`.

In `hover.html`, read `mount` → `updateTime` → `drawCursor` → `timeReadout`.
The key distinction is cursor time versus an available observed sample time.
Read `nearest` to see why a gap yields `N/D`. Then compare `spatialReadout` and
`templateText`, which preserve coordinate/template meanings without a time cursor.
Finally study `scripts/smoke_ui_v063.py`: its real mouse coordinates come from
rendered axes or bar paths, and cursor assertions compare actual SVG positions
after zoom, pan and resize. Performance and remaining limits are recorded in
[HOVER_UX_TEST_V063.md](HOVER_UX_TEST_V063.md).
