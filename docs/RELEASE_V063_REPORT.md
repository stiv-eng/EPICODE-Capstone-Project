# Release v0.6.3 — Unified Hover Experience

Date: 2026-10-24 (Europe/Rome). Local branch: `feat/sim-telemetry-v063`.
Verified baseline: **`48e99ee` on `feat/sim-telemetry-v062`**, with a clean initial
working tree. The baseline branch and history remain recoverable. No assumption
was made about a remote release.

## Delivered behavior

| Feedback | Status | Delivered result |
|---|---|---|
| FB-025 | Implemented and browser verified | Amber vertical cursor maps one real relative-time coordinate through every telemetry subplot axis; zoom, pan, resize and channel changes preserve alignment; no native floating labels |
| FB-026 | Implemented and browser verified | Readout rows are created in application selection order, A then B; source/lap/window/slot identities and colors survive pointer movement, shuffled events and unavailable measurements |
| FB-027 | Implemented across applicable renderers | Shared external readouts for temporal, scatter/G-G, XY position, distribution, category, ML/replay and optional legacy charts; type-specific behavior and explicit offline validation limits |

No production ingestion, normalization, verified-lap rule, analytical formula, ML
feature, training/inference algorithm, split, target, artifact or source dataset
was changed. ML and replay changes are rendering only. The existing offline F5
configuration and dependency set are unchanged. No model-save button, automatic
download, push, merge, history rewrite or branch deletion was invoked.

## Cursor, identities and measurement integrity

The browser converts pointer position through the active axis to a relative time,
then converts that time separately through every temporal subplot's actual axis
transform. A lightweight SVG overlay draws the cursors without changing Plotly
data or triggering Python reruns. Relayout/afterplot/resize recalculate geometry.
Cursor/readout persist on leave, and focused temporal charts support left/right
observed-sample stepping. Time figures in grouped Dynamics and replay components
also synchronize across figures.

Comparison identities include selection slot, source key and verified lap/window
identity. Thus repeated visible lap labels, or even choosing the exact same source
lap twice, remain distinct. Row order comes from the figure manifest, never the
event point array. Missing values update the existing row to `N/D`; the other row
does not move. Colors remain assigned to those identities across channels.

Readouts use nearest **real displayed samples** within 0.51 times the original
median positive source step, computed before decimation. They show recorded sample
time separately from cursor time and source row where available. No interpolation,
gap fill or hidden full-resolution telemetry payload is introduced. Unordered
timestamps use a safe bounded search. Without a finite declared clock, Signals
labels the source sample index and uses XY mode without seconds or a time cursor;
this behavior also propagates through grouped Dynamics.

Scatter/G-G/distribution/category charts display meaningful coordinates, units,
bins/counts or existing hover metadata. Position retains connected colored
geometry, full-resolution adjacency guards and the vector car/neutral marker.
Readouts identify the actual hovered endpoint and its own color measurement;
orientation is not invented. Replay sends only causal prefix signals and available
prediction/baseline history. Revealing the target changes retrospective metrics,
not chart payloads.

## Shared architecture and migration scope

`motorsport_ui/hover.py` copies/prepares figures and serves one installed Plotly
runtime per declared component. `hover.html` owns stable row mounting, Plotly
events, nearest-sample lookup, cursor geometry, numerical formatting and responsive
layout. The runtime is a content-hashed local asset, explicitly reused through
browser CacheStorage. There is a direct offline fallback if cache access fails.
No new frontend dependency or CDN is required.

Dynamics groups up to five related figures into one iframe/runtime. Replay groups
two; ML groups scatter/histogram and keeps importance beside its controls. Explorer
retains lazy section mounting. Legacy lap/stint sections now mount lazily, and
legacy progress/distance figures share a component. The comparison compatibility
wrapper and standalone document export reuse the same implementation; the obsolete
comparison-only HTML was removed.

All applicable charts use external readouts: Signals, Inputs, Dynamics acceleration
and wheel families, both correlations, G-G, Tyres, Cockpit context, Position,
Comparison laps/windows/distance delta, ML scatter/error histogram/importance,
replay signals/history, and every optional FastF1/legacy Plotly chart. The legacy
epoch-loss chart was also migrated from native `line_chart`. There are no retained
native-floating-hover exceptions. Instruments, tables and unavailable-capability
messages remain appropriate non-chart UI. The complete page/type/data/cursor audit,
including conditional charts and validation limits, is in
[ARCHITECTURE_V063.md](ARCHITECTURE_V063.md#chart-audit).

## Validation results

The final full pytest result is **193 passed, 92 warnings in 116.22 s**;
see the companion evidence JSON. All **172 baseline tests** remain, with **21 additional tests**.
`pip check`, compilation and whitespace checks pass. Presentation tests inspect
actual shared-component figure payloads, including grouped figures; numerical
assertions remain active. Production-source/F5/dependency diffs against `48e99ee`
are empty.

Chrome acceptance: **36 baseline checks rerun successfully**, **47 new workflow
interaction checks**, and **4 offline type/clockless hover checks**: **87 checks**.
An additional 40 per-hover budget observations and one final memory summary are
measurements, not extra interaction tests. The actual mouse workflows cover GT7
four/five-channel laps/windows, compatible ACGym recordings, fixed row IDs/colors,
missing values, zoom/pan/resize, keyboard/leave behavior, every available Explorer
family, explicitly trained ML and causal replay. The baseline rerun also verifies
the original Parquet upload, stationary upload/neutral marker, car heading/pixel
size under zoom, source catalog and G-G geometry at multiple widths.

Frozen regression passes **390 ACGym + 60 GT7 rows** for Ridge, Random Forest and
SVR, including targets/errors/baselines. Maximum prediction deviations are
**2.842170943040401e-14 s** and **1.4210854715202004e-14 s**, below **1e-9 s**.
No frozen evidence/model artifact was rewritten by the checker. Ordinary startup
does not train. Browser training was an explicit button action; no model was saved.

Representative local evidence: `artifacts/v063/comparison_cursor_v063.png`,
`comparison_960_v063.png`, `comparison_480_v063.png`, `GT7_Signals_v063.png`,
`GT7_Position_v063.png`, `ML_external_v063.png`, `replay_causal_v063.png`;
`artifacts/v063-fixtures/legacy_types_v063.png`; baseline screenshots/JSON under
`artifacts/v063-baseline/`. These ignored artifacts remain in this workspace.
Detailed interactions, corrected unsuccessful attempts, commands and remaining
limits are in [HOVER_UX_TEST_V063.md](HOVER_UX_TEST_V063.md).

## Performance and responsive observations

Installed Plotly JS is **4,851,164 bytes**; six inline copies would add
**29,106,984 bytes** before figure data. Actual current component-argument payloads
measured with AppTest are **427,776 bytes** for four-channel GT7 comparison
(one figure/component) and **995,025 bytes** for GT7 Dynamics (five figures/one
component), with no runtime embedded in those arguments.

HTTP caching alone was insufficient with the installed Streamlit asset route;
explicit browser caching fixed repeated transfer. The final main run records one
cold-load observation and 35 warm-cache observations. Runtime load/evaluation took
789.4–1561.9 ms; figure mounting 39.8–594.3 ms; measured temporal hover-frame updates
1.4–10.3 ms. Twenty real pointer events plus observation wait took 0.348 s with no
Python rerun or figure-data mutation. The main observed JS heap ranged
53.9–270.2 MB and ended at 223.9 MB after the multi-page workflow, without forced
GC. Distinct iframes still parse their own runtime; this is not a zero-cost global
instance or a long-session leak guarantee.

Readouts remain outside the plotting area and move below charts at narrow component
widths. Actual checks at 1600/960/480 px confirm no horizontal overflow and preserved
cursor alignment. G-G retains equal numeric and pixel scales. Main Chrome logs
contain 25 generic iframe/feature-policy warnings and no error/exception entries.

Known limits: physical touch, complete screen-reader behavior and other browser
engines remain untested. Narrow layouts require scrolling below tall figures.
Strict tolerance can legitimately show `N/D` between decimated observations.
Optional FastF1/Keras complete acquisition/training workflows were not exercised;
their renderers were reviewed/migrated and relevant types tested offline. The
historical FB-007 disappearance remains unreproduced; bounded SVG and scrolling/
remount protection remain in place. No private feedback master was accessed or
duplicated.

## Files and Git handoff

New implementation: `motorsport_ui/hover.py`, `motorsport_ui/hover.html`.
Updated UI: `comparison_hover.py`, `visuals.py`, `telemetry.py`, `dynamics.py`,
`gg.py`, `position.py`, `streamlit_app.py`, pages `01`, `02`, `03`, both `04`
legacy pages, `05`, `14`, `20`, `21`. Inputs/Tyres/Cockpit and standalone wrappers
inherit the migration through `signal_chart`.

New tests/harness: `tests/test_hover_v063.py`, `scripts/smoke_ui_v063.py`,
`scripts/hover_fixture_specs.py`, `scripts/hover_fixture_app.py`. Updated
`scripts/smoke_app.py`, baseline browser selectors in `smoke_ui_v062.py`,
`tests/conftest.py` and six retained UI test modules.

Documentation: README, CHANGELOG, this report, `HOVER_UX_TEST_V063.md`,
`ARCHITECTURE_V063.md` (including a Python/JavaScript study guide),
`HOVER_EVIDENCE_V063.json`, and `NEXT_RELEASE_RECOMMENDATION.md`.

Local implementation commits: `9a5d26b` (shared hover and chart migrations),
`19c3c56` (clockless source-index guard), and `3309fca` (Python/Chrome validation).
The documentation/evidence commit follows these in Git.
The final commit is available with `git log -1 --oneline`; final branch/clean-tree
status is checked after committing. The v0.6.2 branch is intact and an ancestor.
No push or merge was performed.
