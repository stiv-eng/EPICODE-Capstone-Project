# Hover validation v0.6.3

Date: 2026-10-24, Europe/Rome. Baseline: local v0.6.2 `48e99ee`, clean before
branch creation. Validation uses the existing Python 3.11 environment and installed
Chrome 156. No telemetry download or new package installation was needed.

## Automated and frozen checks

The existing 172 tests were retained. Presentation assertions now inspect actual
declared-component figure arguments through `chart_specs`, including grouped
figures, instead of requiring the former native Streamlit chart node. Numerical,
selection, availability, orientation and ML behavior assertions remain active.
The old protection test excludes ML/replay **page rendering** from the immutable
source list because that rendering change is explicitly in this release's scope;
all production ML modules and F5 configuration remain protected.

Twenty-one new tests cover original-cadence tolerance, missing/duplicate/backward time,
numeric-array and axis-geometry immutability across five chart types, duplicate
lap labels/source slots, recording identity, stable colors across channel changes,
actual trajectory endpoint measurements, grouped payload/runtime contracts,
sentinel palette resolution, unordered-time fallback, complete renderer coverage,
clockless source-index rendering, and the causal replay serialization boundary. Existing real replay tests now
also assert that revealing the final target leaves chart payloads identical.

Final full-suite result: **193 passed, 92 warnings in 116.22 s**.
`python -m pip check` reports **No broken requirements found**. Compilation and
`git diff --check` pass. No requirement or VS Code configuration changed.

Frozen verification (`python -m scripts.verify_ml_v061`):

| Corpus | Matching rows | Models | Maximum prediction deviation | Tolerance |
|---|---:|---|---:|---:|
| ACGym | 390 | Ridge, Random Forest, SVR | 2.842170943040401e-14 s | 1e-9 s |
| GT7 | 60 | Ridge, Random Forest, SVR | 1.4210854715202004e-14 s | 1e-9 s |

Targets, signed errors and allowed historical baselines also pass. The checker
does not save model artifacts or rewrite frozen evidence. Git comparison against
`48e99ee` is empty for `motorsport/`, `motorsport_prediction/`,
`motorsport_ui/ml.py`, `.vscode/`, and `requirements.txt`.

## Real Chrome interaction evidence

`scripts/smoke_ui_v063.py` extends the existing local CDP harness. It computes
actual mouse positions from rendered axes for line/scatter points and actual SVG
bar paths for histograms/category bars. It does not accept page rendering alone
as hover evidence. Its JSON records readout text, ordered IDs/colors, SVG cursor
coordinates, units, native-label counts and performance measurements.

The principal workflow covers:

- Real GT7 and ACGym Signals, Driver Inputs, all available Dynamics figures,
  Tyres and enabled Cockpit context traces; GT7 map and preserved car metadata;
  the explicit ACGym missing-coordinate explanation.
- Two verified GT7 laps with four channels, multiple times/channels, A/B row
  order/colors, all-panel cursors, actual Plotly zoom and pan, then five-channel
  remount; equivalent window and compatible ACGym recording comparisons.
- Reversed synthetic hover-event point order as an additional adversarial check;
  a real time where selection A has a measurement and B has none; explicit
  synthetic gap/null probes of the same client-side nearest-sample function.
- Cursor pixel positions checked against each rendered axis transform after
  zoom/pan/resize; no native floating labels and a panel outside the data area.
- Widths 1600, 960 and 480 CSS pixels; component readout below the chart at the
  narrow breakpoint, no horizontal document overflow, with retained line geometry.
- Keyboard stepping changes the selected observed time; a mutation observer sees
  no Python-running transition through keyboard/20 real pointer updates. Figure
  data JSON remains identical. Leaving retains the numerical readout.
- Explicitly trained ACGym ML scatter, calculated histogram bars and importance;
  trained causal replay observed-input and checkpoint-history hovers. The hidden
  final target is absent from chart payloads and displayed metrics before opt-in.

The separate `v063-fixtures` scenario mounts the actual shared renderer in a small
offline Streamlit fixture app. Real mouse movement verifies legacy lap scatter,
box distribution, categorical bars and a clockless Signals source-index chart.
These checks exercise types and renderer
contracts; they are **not** a claim of complete online FastF1/Keras page workflows.

The prior 36-check workflow was rerun using `--release v063-baseline` after updating
its native-chart DOM selectors to inspect shared component figures. All 36 original
checks pass, including three-width G-G geometry, vector-car heading/pixel size
under zoom, actual original Parquet upload, stationary CSV upload/neutral marker,
catalog/navigation state, startup training guards and hidden replay target. Its
new evidence is under `artifacts/v063-baseline/`; historical v0.6.2 evidence remains
separate. The main new workflow passes 47 interaction checks, plus 36 per-hover
budget observations and one final memory summary; fixtures add four actual-hover
checks plus four budget observations. This is **87 interaction/regression checks**,
not 128 independent interaction tests from counting the measurement rows.

## Attempts corrected before acceptance

Early browser runs stopped on harness assumptions: the map's invisible colorbar
trace was chosen as a sample, a window-radio label was outdated, and raw histogram
arrays were treated as XY samples. The harness now excludes dummy traces, selects
the real label and hovers rendered histogram bars. A synthetic fixture injected
into the live replay component could be replaced by a legitimate Streamlit render;
fixtures now run in a separate real fixture app. One source-dropdown click missed
during responsive layout settling; the common click helper now pauses briefly
after scrolling before measuring and clicking. Failed attempts are not accepted
as successful interaction evidence.

Visual inspection also caught two production presentation issues that were fixed:
Streamlit's special near-black palette tokens need explicit resolution outside its
native frontend, and continuous-color hover values must use Plotly's decoded
`fullData` arrays. The shared renderer now uses a dark theme, resolves those tokens,
preserves the numerical color arrays/ranges, and gives category axes automatic
margins. Histogram readouts name bins/counts instead of displaying an undefined
point index.

## Performance and limits

The installed runtime is **4,851,164 bytes**. Six inline copies would contribute
29,106,984 bytes before figure data. Production component arguments contain no
runtime source. Dynamics groups up to five figures into one iframe/runtime;
replay groups two into one; ML uses two components for three figures. SVG sampling
budgets are unchanged. Explorer sections mount lazily. Legacy lap/stint sections
also mount lazily, and legacy progress/distance figures share a component.

An initial HTTP-cache-only approach still transferred the compressed runtime on
component remount (about 1.48 MB per fetch). Inspection of Streamlit's installed
component route explained the absent freshness lifetime/validators. The final
loader explicitly caches the content-hashed local response in browser CacheStorage,
with a Web Lock for simultaneous requests and a direct local fallback if storage
is unavailable. Browser records distinguish the first `local-fetch` from later
`cache` loads. Each iframe still pays runtime parsing/heap cost; this is not a
single JavaScript instance across the whole dashboard. Measured heap, payload,
load and hover-frame timings are summarized in `HOVER_EVIDENCE_V063.json` and the
release report; they are local desktop observations, not hardware-independent SLOs.
The main run observed one cold runtime load and 35 warm-cache observations;
temporal pointer-to-frame updates took 1.4–10.3 ms. Plot mounting took 39.8–594.3 ms,
runtime load/evaluation 789.4–1561.9 ms. Largest individual figure-data payload was
1,999,493 JSON characters; JS heap observations ranged 53.9–270.2 MB, ending at
223.9 MB after the multi-page workflow without forced garbage collection. This
does not establish absence of long-session leaks. Twenty actual pointer events
completed in 0.348 s including the 0.2 s observation wait, with no Python rerun.
Main Chrome console: 25 generic iframe/feature-policy warnings, zero exceptions
or error entries. They are retained in the local console log.

Known limits: full physical touch, screen-reader and non-Chrome browser testing
were not performed. Keyboard sample stepping and responsive desktop emulation
were exercised. Narrow layouts require scrolling to the panel below tall figures.
Downsampling may legitimately yield `N/D` between retained real samples under the
strict original-cadence tolerance. Optional FastF1 acquisition/weekend training is
not exercised offline. The historical FB-007 disappearance remains unreproduced;
bounded SVG, actual scrolling and section remount checks remain in use.

## Reproduction and screenshots

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe -m scripts.verify_ml_v061
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.smoke_app --release v063 --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
.\.venv\Scripts\python.exe -m scripts.smoke_app --release v063-fixtures --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
.\.venv\Scripts\python.exe -m scripts.smoke_app --release v063-baseline --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

The harness stops its temporary server/browser after each run. Local ignored
evidence: `artifacts/v063/UI_BROWSER_V063.json`, `browser_console_v063.json`,
`smoke_server.log`; representative PNGs `comparison_cursor_v063.png`,
`comparison_960_v063.png`, `comparison_480_v063.png`, `GT7_Signals_v063.png`,
`GT7_Position_v063.png`, `GT7_Vehicle_v063.png`, `ACGym_Signals_v063.png`,
`ML_external_v063.png`, `replay_causal_v063.png`. Legacy fixtures have equivalent
JSON/logs and `legacy_types_v063.png` under `artifacts/v063-fixtures/`.
These screenshots are available in this workspace and are not committed datasets.
