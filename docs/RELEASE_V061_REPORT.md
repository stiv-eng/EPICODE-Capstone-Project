# Release v0.6.1 report

Date: 2026-10-24 (Europe/Rome). Branch: `feat/sim-telemetry-v061`, created from
verified local v0.6 commit `49639f4`. The initial working tree was clean and the
109-test baseline passed before implementation. No remote v0.6 availability was assumed.

## Delivered behavior

Data Explorer is now the detailed analysis environment with one cached dataset and
shared verified-lap or recording-time selection across Signals, Driver Inputs,
Vehicle Dynamics, Tyre Analysis, Cockpit and Position / Track Map. GT7 uses the same
layout and its existing reported world coordinates. ACGym is available per recording,
with additional declared tyre temperatures, pressures, loads and suspension signals
exposed solely through the UI layer. Uploaded compatible files use the same sections.

Overview displays `Channel`, `Time Measured [s]` and time-weighted `Mean`, preserving
the original measured-time calculation. Pedal utilization, distribution charts and
the visible verified-lap/features section are removed from Overview; algorithms remain.
Only unavailable capabilities receive explanations and recommended data.

Cockpit displays a selected actual recorded packet, with speed, RPM, gear, pedal
indicators, declared tyre temperatures and optional context traces. A time slider
uses measured lap time or recording time; source samples are never interpolated
into invented measurements. Cards wrap for narrow viewports.

Position renders connected line segments, preserving source order/coordinates and
breaking at missing values, time gaps/repeats, lap changes, removed rows and spatial
jumps. A 6,000-vertex budget simplifies within validated connected fragments only.
All finite real numeric canonical/original channels can color the path. Continuous
values use 32 bands over the full measured range; known discrete channels use a
legend. Missing color values are grey and constant signals remain valid.

Comparison defaults to verified laps when possible, with measured-time labels,
compatible session/track/unit guards, relative elapsed lap time and one shared
legend. Colors remain consistent across titled channel subplots. Original saved
session windows remain available as explicit windows, without inferred lap identity.

## Navigation

Top level: **Home**, **Session Overview**, **Data Explorer**, **Telemetry Comparison**,
**Machine Learning**, **Progressive Prediction**; historical FastF1 pages are opt-in.
The four former standalone analytical page scripts are preserved as compatibility
wrappers and are not registered in top-level navigation. Their reusable renderers
execute only through the active Data Explorer section.

## Shared source and selection architecture

`motorsport_ui.telemetry` retains the existing cache/registry. Page source widgets
synchronize with durable `telemetry_active_key`; section renderers receive an
already selected session/frame and cannot reload the source. Local replacement
invalidates registered content using file signatures. Uploads remain in memory.

`motorsport_ui.selection` separates durable selection state from transient widget
keys. Source/mapping/signature/verified-table identity invalidates incompatible
lap IDs, windows and dependent controls, including identical lap numbers on a
different dataset. Verified IDs/durations come exclusively from the existing
adapter validation table. The original attachment correctly uses time fallback.
Selected lap traces use their own measured `lap_elapsed_s`, never absolute timestamps.

The ACGym UI loader verifies pinned LD/LDX evidence, calls the unchanged adapter and
adds only unit/frequency/length-compatible optional channels. Its UI catalog is
separate from the unchanged multi-session ML corpus selection. There is no mixing
of recording clocks or alteration of source targets, features or evaluation groups.

See [architecture and function contracts](ARCHITECTURE_V061.md) for segment guards,
color quantization, cache keys, Cockpit packet selection and renderer responsibilities.

## Automated and browser evidence

The baseline was **109 passed / 92 warnings**. The final full suite was
**135 passed / 92 warnings in 98.93 s**, with no failures or skips. `pip check`
reported no broken requirements. Final automated results, commands,
browser artifacts and limitations are recorded in [UI_TEST_REPORT_V061.md](UI_TEST_REPORT_V061.md).
The added suite covers state persistence/invalidation, time fallback, real GT7/ACGym,
missing channels in all six sections, measured means, preserved retrospective APIs,
sample-accurate Cockpit values, segment adjacency/gaps, color edge cases and shared legends.

The full Chrome smoke workflow passed **27 recorded checks**, visiting all six
sections for each real source, switching datasets inside one application session,
selecting verified GT7 laps, revisiting charts, advancing Cockpit and progressive
sliders, comparing GT7/ACGym laps and checking the original fallback. Individual
comparison channel legends are suppressed; the real shared legend has two entries.
Screenshots were inspected, including trajectory, multiple-lap Signals, tyre-aware
Cockpit, Overview, Comparison and the narrow Cockpit viewport.

The frozen-prediction regression compared **390 ACGym rows and 60 GT7 rows** for
Ridge, Random Forest and SVR with v0.6 CSVs. All predictions, targets, errors and
baselines match within `1e-9 s`; maximum prediction deviations were respectively
`2.842170943040401e-14 s` and `1.4210854715202004e-14 s`. SVR selection is unchanged.
No new Keras experiment was run. Existing historical fixture tests remain in the suite.

## Rendering investigation and limitations

FB-007 is **partially implemented**, with validated mitigation and an unresolved
original reproduction. The archived v0.6 Explorer was executed from Git in an ignored
artifact script, with eight channels, tab switches and scrolling to the top/bottom
of its long figure. Chrome reported two figures, six GL canvases, zero observed
`webglcontextlost` events and no application exception. The original disappearance
did not reproduce. Context exhaustion or a CSS defect is therefore not claimed.

The new detailed renderers use bounded SVG, explicit dimensions, stable chart keys
and one mounted analytical section. Actual Chrome scroll/remount checks found
visible paths with no WebGL canvases. No global overflow/height CSS patch was added.
This establishes the tested workflow's stability, not every browser/GPU combination.

Other limits are intentional:

- ACGym's inspected export lacks compatible world X/Y. `Position` is rank and
  normalized progress is not a physical track map. Its map section explains the
  missing requirement; declared tyre and dynamics channels are available.
- Original integrated coordinates can drift; GT7 simulator coordinates are not
  surveyed geometry. No certified track/corner/start-line claims are made.
- Spatial discontinuity detection is a disclosed scale-independent heuristic;
  display simplification can omit very short fragments when the budget is exceeded.
  Continuous colors are quantized to 32 bands; extreme values remain in the scale.
- Real browser testing used headless local Chrome, with a narrow desktop viewport
  for Cockpit. Other engines, real phones and the user's intermittent GPU condition
  remain untested. Upload/mapping coverage is automated; no browser file-dialog claim.
- Source-unit limitations, original missing laps, experimental GT7 ML eligibility,
  independent-session gates and unsupported cumulative delta remain in force.
- The F5 launch configuration is unchanged and its Streamlit module/entrypoint was
  exercised. An actual interactive VS Code F5 keypress was not automated.

## Feedback traceability for this release

This table records implementation evidence for the release; it is not a replacement
master feedback register. The private Google Docs register was not accessed or modified.

| Feedback | Status | Relevant files | Verified evidence | Remaining limitation |
|---|---|---|---|---|
| FB-001 | Implemented | `pages/10_Session_Overview.py` | Overview UI asserts exact columns and equality to unchanged weighted mean | None in requested presentation |
| FB-002 | Implemented | Overview; `motorsport_ui/inputs.py` | Removed pedal section; six-section tests exercise Driver Inputs with usage/events | Source pedal availability |
| FB-003 | Implemented | Overview | UI asserts no Plotly charts in Overview; Signals/Dynamics remain accessible | None in requested removal |
| FB-004 | Implemented | `motorsport_ui/telemetry.py`; Overview | Unavailable-row count matches actual capability flags; recommendations render with wrapping text | Legacy readiness gate remains conservative; ML corpus assessment stays on ML page |
| FB-005 | Implemented | Overview | No visible feature section; unchanged `lap_features` still returns verified rows | Retrospective features remain Python API data |
| FB-006 | Implemented | `selection.py`; Explorer; `telemetry.py` | Real GT7/ACGym selected laps, time fallback and SVG elapsed-lap overlays; Chrome multi-lap flow | Original has no validated laps |
| FB-007 | Partially implemented | `telemetry.py`, `dynamics.py`, `visuals.py`; browser scripts | Archived v0.6 reproduction attempt; new scrolling/remount checks and inspected screenshots | Original intermittent symptom/root cause not reproduced; other browser/GPU combinations unverified |
| FB-008 | Implemented | `motorsport/analytics/position.py`; `motorsport_ui/position.py`, `visuals.py` | Segment order/gap/lap/jump tests; real connected original/GT7 trajectories | Display simplification and source-accuracy limits disclosed |
| FB-009 | Implemented | `telemetry.py`, `explorer_source.py`, `acgym.py`; Explorer | Same six sections on three real sources; minimal/upload-style mapping tests; GT7 coordinates exposed | ACGym map lacks world X/Y; browser file dialog not exercised |
| FB-010 | Implemented | `streamlit_app.py`; Explorer; reusable renderer modules | Navigation test excludes four former analytical routes; Chrome visits all sections | Standalone wrappers retained for compatibility only |
| FB-011 | Implemented | `cockpit.py`, `selection.py` | Nearest-packet unit/UI checks, slider advance for three sources, inspected tyre cards and narrow viewport | Recorded replay; missing/unknown-unit temperatures are hidden |
| FB-012 | Implemented | `pages/14_Session_Comparison.py`; `selection.py` | Lap mode defaults; ACGym cross-recording test; GT7/ACGym browser comparison; track/unit guards | No common-distance cumulative delta without verified geometry |
| FB-013 | Implemented | Comparison; `visuals.py` | Figure asserts exactly two legend entries, stable colors across channels; real browser legend inspection | Two comparison selections retained from existing workflow |
| FB-014 | Implemented | Position analytics; `visuals.py` | Arbitrary original numeric channel, continuous/extreme/missing/constant tests and discrete gear legend | Unknown units remain labelled source units; extremes may compress color contrast |
| FB-015 | Implemented | Position analytics/renderer | Connected polylines, bounded trace grouping and real source trajectory screenshots | Segments are a bounded source-coordinate display |
| FB-016 | Implemented | Shared selection; Position renderer | GT7/ACGym/original state tests; GT7 lap map, multi-lap revisit and original window browser flow | ACGym cannot draw absent world coordinates |
| FB-017 | Unchanged as requested | ML modules/pages unchanged; regression script and existing tests | Full ML/replay tests and 450 frozen model-prediction rows match | Existing statistical/source-clock limitations preserved |

## Acceptance status

AC1-AC5 and AC7-AC13 pass within the supplied data capabilities. AC6's lap-based
Signals behavior passes; its original disappearing-chart root cause remains
qualified under FB-007. AC14 passes for the stated Chrome coverage. AC15 passes:
original SHA-256 is `fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`,
all **20 GT7** and **48 ACGym** pinned file hashes match, and existing history/data
remain preserved. AC16 preserves the unchanged F5 configuration and exercised entrypoint,
with the interactive-keypress limitation stated above.

## Files and Git handoff

Added UI modules:
`motorsport_ui/{selection,explorer_source,acgym,inputs,dynamics,tyres,cockpit,position,visuals}.py`.

Added checks:
`tests/test_ui_v061.py`, `scripts/smoke_ui_v061.py`,
`scripts/investigate_rendering_v061.py`, `scripts/verify_ml_v061.py`.

Modified existing files:
`streamlit_app.py`, `motorsport_ui/telemetry.py`, `motorsport/analytics/position.py`,
`pages/{00_Data_Explorer,10_Session_Overview,11_Driver_Inputs,12_Vehicle_Dynamics,13_Tyre_Analysis,14_Session_Comparison,15_Position_Analysis}.py`,
`scripts/smoke_app.py`, `tests/test_data_explorer.py`, `tests/test_advanced_ui.py`,
`README.md`, `CHANGELOG.md`, `docs/NEXT_RELEASE_RECOMMENDATION.md`.

New documentation: this report, `ARCHITECTURE_V061.md`, `UI_TEST_REPORT_V061.md`.
No historical source files or dataset files were removed. Local screenshots/logs and
validation JSON remain ignored under `artifacts/`, rather than adding raw data to Git.

The implementation commits are `6a07810` (shared exploration, Cockpit and trajectories)
and `e222d4f` (lap comparison, three-source browser checks and frozen ML regression).
`ea36f5a` verifies both direct and module browser-script entrypoints. The final
handoff commit contains documentation only. The
final hashes are available in `git log --oneline 49639f4..HEAD`. The original v0.6
branch and commit remain intact. No reset, history rewrite, branch deletion, merge,
remote push or publication was performed. Final working-tree status is checked after
the handoff commit.
