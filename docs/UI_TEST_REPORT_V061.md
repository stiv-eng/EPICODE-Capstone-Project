# UI and regression test report v0.6.1

Executed locally on 2026-10-24 (Europe/Rome). All results below are observed
execution results, not a checklist of planned checks.

## Environment and automated results

Windows, Python **3.11.9**, Streamlit **1.66.0**, Plotly **6.9.0**, NumPy **2.4.6**,
Pandas **2.3.3**, scikit-learn **1.9.1**, Chrome **156.0.8078.47**.
The existing environment was reused; no package installation was required.

| Check | Actual result |
|---|---|
| Local v0.6 baseline, `python -m pytest -q` | 109 passed, 92 warnings, 82.16 s |
| New v0.6.1 file, `python -m pytest tests/test_ui_v061.py -q --tb=short` | 26 passed, 31.92 s |
| Final full suite, `python -m pytest -q --tb=short` | **135 passed, 92 warnings, 98.93 s**; no failures/skips |
| `python -m pip check` | No broken requirements found |
| `git diff --check` | Pass; informational Windows LF/CRLF conversion messages only |
| Source integrity | Original SHA matches; all 20 GT7 and 48 ACGym pinned hashes match |
| Frozen real sklearn regression | 390 ACGym + 60 GT7 rows match v0.6 at absolute tolerance 1e-9 s |

All Python commands used `.venv/Scripts/python.exe`. The 92 warnings are the same
historical Keras/PyTorch NumPy `copy` keyword deprecations as the baseline. Existing
historical model fixtures ran; no new Keras model experiment was introduced.

`artifacts/pytest_v061_final.txt` retains the final full output. The initial full
refactor run also passed 134 tests; the final 135-test run includes an additional
eight-lap distinct-color regression discovered during screenshot inspection.

## Coverage of required behaviors

| Requirement | Executed evidence |
|---|---|
| Source and lap/window persistence across sections | `test_shared_laps_and_source_persist_through_sections_without_reloading`; real-source section tests; original time window remains unchanged |
| Safe dataset/mapping invalidation | Identity reconciliation test, mapping fingerprint test, real GT7-to-original reset and existing file-replacement test |
| No unnecessary source reload | `test_actual_source_loader_runs_once_during_section_switches` asserts one loader invocation across all six sections |
| Original recording-time fallback | Existing original-file integration plus real-source v0.6.1 test and Chrome interval interaction |
| GT7 verified laps and source coordinates | Eight verified labels, position-column checks, selected-lap frame tests and actual GT7 trajectory |
| ACGym validated selection and tyre channels | Real recording tests assert lap availability, declared core/inner temperatures, pressure/load/suspension channels |
| Missing data in every section | Six parameterized minimal-source section tests plus existing standalone compatibility-wrapper tests |
| Simplified Overview | Exact three column names, unchanged time-weighted Mean equality, no charts or visible pedal/features headings |
| Unavailable-only capability explanations | Row count equals unavailable flags from unchanged assessment; actual wrapped Overview messages inspected |
| Underlying lap features retained | Unchanged retrospective feature API returns verified rows; original readiness/ML tests retained |
| Correct Cockpit sample | Pure nearest-packet/tie/missing-time tests; UI slider selects source row 12 and actual speed 112.0 |
| Segment adjacency/order and discontinuities | Invalid positions, time gaps, lap changes, spatial jumps and removed-row tests; 100,000-row bounded simplification preserves run endpoints |
| Flexible trajectory color | Original numeric channel, discrete gear, constant/missing/extreme values and bounded trace count tests |
| Lap filtering and relative axes | Verified-frame tests, multi-lap Signal tests, real three-source sections and GT7/ACGym Comparison |
| Stable shared legend/colors | Figure-level two-entry legend and cross-channel colors; ACGym cross-recording UI test; actual Chrome legend DOM |
| ML and replay unchanged | All original causal/held-out-label/split/artifact/UI tests plus frozen prediction check below |
| Offline startup and launch | Existing offline/blocked-legacy-import tests; real Streamlit module entrypoint and unchanged `.vscode` files |

Existing tests were updated only where presentation intentionally changed: Overview
has no charts, sections mount one at a time, GT7 uses the common source widget,
and the fallback explanation is a caption. No analytic or ML test was removed.

## Real Chrome workflow

Command:

```powershell
.venv/Scripts/python.exe scripts/smoke_app.py --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"
```

Final exit status **0**, HTTP homepage and health endpoint **200**, **27 recorded
browser checks passed**. The driver uses local Chrome CDP and actual mouse/keyboard
events. It waits for Streamlit completion and asynchronously mounted Plotly paths.
It navigates with sidebar links to preserve application state, rather than recreating
the session on every page. Temporary server/browser processes terminate afterward.
Both direct-script and documented module launches (`python -m scripts.smoke_app`
and `python -m scripts.investigate_rendering_v061`, with the same browser argument)
were executed successfully. Their helper imports support either entrypoint.

| Actual flow | Result |
|---|---|
| Home and consolidated sidebar | Rendered; optional legacy tools stay off |
| Original: all six Explorer sections | Passed; recorded-time fallback, plots and Cockpit; actual colored source trajectory |
| GT7: all six sections | Passed with a verified lap and available world coordinates/tyre core temperatures |
| GT7: explicitly select all eight verified laps | Passed; relative lap-time overlays and distinct colors; selection persists on section revisits |
| ACGym: all six sections | Passed; declared tyres/Cockpit available; Position clearly explains absent world X/Y |
| Scroll at start/end/center of analytical charts | Passed; visible nonempty SVG paths retained, zero analytical GL canvases |
| Repeated Signals/Position/Cockpit section revisits | Passed without losing the shared selection |
| Dataset changes original -> GT7 -> ACGym -> original | Passed; appropriate lap/window controls reset safely |
| Cockpit instant slider on all three real sources | Passed; actual packet/time changes observed |
| GT7 and ACGym lap comparison | Passed; one two-entry legend serves channel subplots |
| Original fallback after source changes | Passed; recording interval can be advanced |
| Machine Learning | Page/feature controls render without automatic training |
| Progressive Prediction | Baseline workflow renders; checkpoint advances; final target stays hidden |
| 480x960 Cockpit viewport | Cards visibly wrap; document has no horizontal overflow |

The final captured browser log `browser_console_release_v061.json` is an empty array:
no captured console/log/exception events. This does not replace the screenshot and
DOM checks or claim behavior in another browser engine.

Local ignored evidence under `artifacts/`:

- `UI_BROWSER_V061.json`: all 27 recorded checks and chart dimensions/path counts.
- `home_v061.png`, each `{original,gt7,acgym}_{signals,driver_inputs,vehicle_dynamics,tyre_analysis,cockpit,position}_v061.png`.
- `gt7_selected_laps_v061.png`, `overview_v061.png`,
  `gt7_lap_comparison_v061.png`, `acgym_comparison_v061.png`.
- `ml_unchanged_v061.png`, `progressive_unchanged_v061.png`, `cockpit_narrow_v061.png`.
- `browser_console_release_v061.json`; temporary server diagnostics in `smoke_server.log`.

Screenshots were visually inspected. Issues found during inspection were corrected:
long ACGym comparison labels were shortened to recording/stint, technical lap columns
were replaced with a concise selection table, unavailable-capability explanations
were changed to wrapped messages, and eight simultaneous lap traces received unique
colors. The final narrow screenshot shows the Cockpit cards, not just the page header.

## FB-007 investigation

Command:

```powershell
.venv/Scripts/python.exe scripts/investigate_rendering_v061.py --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"
```

The script reads `49639f4:pages/00_Data_Explorer.py` from local Git and executes
that archived page in an ignored artifact script. It does not checkout/reset or
overwrite source data. It reuses the current source-registration helper; the original
dataset's old eager tabs and `Scattergl` plot code itself remain unchanged.

Chrome selected eight channels, switched Signals/Position tabs repeatedly and
scrolled to the top/bottom/center of the long plot. Observed result: **two figures,
six GL canvases, zero context-loss events and no application exception**. Both upper
and lower screenshots contain rendered traces. The intermittent disappearance did
**not reproduce**, and no console events established a GPU/context-loss cause.

Inspected concerns: eager hidden-tab chart mounting, anonymous chart identity,
multi-panel dimensions, Streamlit reruns, GPU canvas lifecycle and CSS/overflow.
No custom scrolling/overflow override was found in the old local analytical page.
The refactor now mounts one section, gives detailed figures stable keys/dimensions
and uses bounded SVG while keeping extrema downsampling. Real scrolling passed;
the original causal diagnosis remains unconfirmed. FB-007 is reported as partial.

Evidence: `RENDERING_BASELINE_V061.json`, `browser_console_baseline_v061.json`,
`v06_baseline_eight_channels_v061.png`, `v06_baseline_eight_channels_bottom_v061.png`.

## Frozen ML prediction comparison

`python -m scripts.verify_ml_v061` completed with exit **0**. It executes only the
unchanged sklearn workflows, joins every current/frozen row by model, partition,
lap UID and checkpoint, verifies identical populations, and compares prediction,
target, error and permitted prior-baseline columns at absolute tolerance `1e-9 s`.
Historical CSVs and saved model files are not overwritten.

| Source | Matched rows | Maximum prediction deviation | Selected model |
|---|---:|---:|---|
| ACGym | 390 | 2.842170943040401e-14 s | SVR, unchanged |
| GT7 experimental | 60 | 1.4210854715202004e-14 s | SVR, unchanged |

Evidence: `artifacts/ML_REGRESSION_V061.json`. All three model families, frozen
targets and baselines match; tiny differences are CSV floating-point roundoff.
`git diff 49639f4 -- motorsport/ml motorsport_prediction motorsport_ui/ml.py
pages/20_Machine_Learning.py pages/21_Progressive_Prediction.py` is empty.

## Honest execution limits and failed attempts

- Initial Chrome launch inside the filesystem sandbox terminated before navigation.
  The authorized local browser workflow succeeded outside that sandbox. No resulting
  failed launch was counted as a browser acceptance check.
- An early smoke assertion checked before Plotly mounted; the driver now waits for
  actual rendered paths. Another attempt contained an invalid JavaScript newline in
  a fallback assertion; expression exceptions now surface explicitly and it was fixed.
- The first test iteration found a missing renderer import and assertions tied to the
  old presentation; both were fixed before final successful runs.
- The original v0.6 symptom remains unreproduced, so a universal disappearing-chart
  fix or confirmed GPU root cause is not claimed.
- Browser coverage uses one local headless Chrome version. A narrow desktop viewport
  does not certify a physical mobile device. Browser upload/file-dialog and other
  engine coverage are not claimed; upload-style manual mappings and in-memory
  registered sessions are covered by automated Streamlit tests.
- The F5 configuration/entrypoint is preserved and exercised through the same
  Streamlit module launch. An interactive VS Code keypress was not automated.
