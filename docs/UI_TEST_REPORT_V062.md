# UI and regression validation v0.6.2

Executed locally on 2026-10-24 (Europe/Rome), from recoverable v0.6.1 commit
`c47fd4a`, on `feat/sim-telemetry-v062`. Python 3.11.9, Streamlit 1.66.0,
Plotly 6.9.0 and local Chrome 156.0.8078.47 were reused without new dependencies.

## Exact automated results

| Check | Observed outcome |
|---|---|
| Baseline suite | 135 passed, 92 warnings in 96.52 s |
| New v0.6.2 suite | 37 passed in 14.13 s |
| Final full acceptance suite | **172 passed, 92 warnings in 104.06 s**, no failures/skips |
| `python -m pip check` | No broken requirements found |
| `git diff --check` | Pass; informational Windows LF/CRLF notices only |
| Frozen prediction regression | All 390 ACGym + 60 GT7 rows match within 1e-9 s |
| Source integrity | Original attachment hash unchanged; 20/20 GT7 and 48/48 ACGym manifest hashes match |

Commands used `.venv/Scripts/python.exe`. The 92 warnings are the unchanged
historical Keras/PyTorch NumPy `copy` deprecations; existing small historical fixture
tests ran, but no new Keras experiment was developed. Final output is retained in
`artifacts/v062/pytest_v062_acceptance.txt`; other intermediate runs are labelled
separately. No analytical/ingestion/ML test was deleted.

### New and preserved test coverage

- **Catalog/formats:** hide the exact original hash, preserve developer opt-in and
  differently populated replacement Parquet, prefer real GT7, prioritize ACGym if
  GT7 is absent, retain generic CSV/Parquet uploads and audited original upload.
- **Usability/state:** reject all-missing/nonfinite/text/complex signals, allow
  legitimate constants, dynamically filter tyre corners and dynamics families,
  omit empty selectors and reset stale choices on source change. Existing six-section
  dataset/lap/window persistence and file-replacement tests continue to pass.
- **G-G:** identical ranges, `scaleanchor='x'`, `scaleratio=1`, constrained domains,
  full-data extent and refusal of differently declared axis units. Browser checks
  below verify the actual rendered scale, not just configuration properties.
- **Orientation:** eight known direction cases cover all quadrants, vertical and
  reverse movement; stationary/near-zero motion, missing coordinates, time/lap/row
  gaps and spatial jumps reject fabricated directions. A valid final sample can use
  a labelled backward difference. Measured headings require verified metadata and
  declared units; tests cover degrees/radians, zero axis, rotation sign, handedness
  and axis swap/reflection transformation support.
- **Vehicle/UI:** real marker XY/sample identity, pixel-sized shape anchors and
  zoom invariance; stationary coordinates render a neutral actual position. The
  slider test counts one segmentation call across a marker update, confirming
  the expensive base geometry is cached.
- **Comparison:** original shared-legend/color tests remain; the component retains
  numeric metadata, units and identity, escapes uploaded labels and suppresses
  only floating native labels. AppTest inspects the iframe's serialized figure
  instead of assuming the former native `st.plotly_chart` container.
- **ML preservation/safe diagnostics:** unchanged production file diff, original
  causal/label/group/preprocessing/artifact tests, explicit-training/replay tests,
  and a writer test that refuses frozen result and model-store paths.

Historical original-attachment UI tests now explicitly register that source as an
upload through a shared fixture. They continue exercising its real data rather
than silently switching to the new GT7 default or being skipped. Generic source
ingestion/normalization tests remain unchanged.

## Actual Chrome workflow

```powershell
.venv/Scripts/python.exe -m scripts.smoke_app --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"
```

Final exit **0**: homepage/health **HTTP 200**, **36 browser checks passed**.
The default smoke scenario is now v0.6.2. Its CDP driver uses actual mouse/keyboard
events, reads rendered Plotly dimensions and SVG geometry, interacts with actual
file inputs and saves screenshots. No simulator, network download or automatic
training is needed. Temporary browser/server processes terminate after the run.

### G-G measured physical scales

The driver reads final axis pixel lengths and numeric ranges after layout/resize.
Pixels per source unit are `axis_pixel_length / (range_max - range_min)`.

| Source / viewport width | X data pixels | Y data pixels | X/Y pixels-per-unit ratio |
|---|---:|---:|---:|
| GT7 / 1600 | 430 | 430.00000000000006 | 0.9999999999999999 |
| GT7 / 960 | 263 | 263 | 1.0 |
| GT7 / 480 | 212 | 212 | 1.0 |
| ACGym / 1600 | 433 | 432.9999999999999 | 1.0000000000000002 |

Both X/Y ranges were equal for each view. All relationships pass the `1e-6`
ratio tolerance and a 2px square-area tolerance. Screenshots were inspected:
GT7 remains labelled source units; ACGym displays declared g. Narrow layout keeps
the data area square, although the fixed-height figure leaves more surrounding
space. The diagram does not stretch across the full wide dashboard.

### Hover, marker, source and navigation checks

| Browser flow | Actual result |
|---|---|
| Overview/Comparison sidebar icons | Rendered 📈 / 📉 text checked in actual navigation; screenshot inspected |
| Catalog before uploads | GT7 default; original `telemetry.parquet` absent from built-in option labels |
| GT7 and ACGym, all six Explorer sections | Passed, including scrolling, filtered families and Cockpit slider updates |
| GT7 vehicle at first/intermediate/final packet | Actual source sample/XY changes; final packet uses a labelled backward estimate |
| Actual car screen orientation | Windshield vector agrees with `(cos(theta), -sin(theta))`; alignment dot product >0.9 |
| Vehicle zoom | SVG artwork bounds remain within 0.2px of prior dimensions; actual-data anchor preserved |
| ACGym position | Explains missing compatible XY; no invented geometry or icon position |
| GT7 lap hover | Mouse interactions over speed, throttle and brake produce measured values/units and both lap identities |
| GT7 window hover | Speed/brake readouts preserve explicit window identities and measured relative times |
| ACGym lap hover | Values and both selected lap identities render correctly |
| Readout placement | Panel left boundary is outside chart right boundary; two entries, one shared legend, zero floating native labels |
| Original Parquet file upload | Actual `DOM.setFileInputFiles` upload succeeds; 116,987 rows, audited mapping and time fallback; source trajectory displayed |
| Stationary CSV upload | Actual XY (12,-8), null direction, zero car shapes and visible neutral indicator |
| Machine Learning | Feature/training controls render, zero model-result charts until explicit training |
| Progressive Prediction | Baseline charts render; final target remains hidden |

The custom comparison panel reduced the chart width enough to wrap the shared
legend in an early screenshot. Explicit bottom anchoring and top space corrected
the title/legend overlap; final screenshots show separate readable rows. The panel
keeps inspected values after unhover and displays each source's actual timestamp
rather than inventing interpolation.

The readout is an offline iframe containing the installed Plotly runtime. It adds
no frontend package/CDN, but repeats the bundle and reserves width. Narrow mobile
touch/keyboard hover interaction has not been certified. Chrome logs contain eight
unrecognized feature-policy warnings and four generic `allow-scripts` plus
`allow-same-origin` iframe sandbox warnings from Streamlit's iframe wrapper; there
were no captured runtime exceptions or console errors. These warnings are recorded,
not reported as a clean/empty console or concealed as a visual fix.

Evidence under ignored `artifacts/v062/`:

- `UI_BROWSER_V062.json`: all 36 checks, numerical axis/shape/readout observations.
- `home_icons_v062.png`, `gt7_gg_{desktop,960,480}_v062.png`, `acgym_gg_desktop_v062.png`.
- `gt7_vehicle_{start,middle,end,before_zoom,zoom}_v062.png`.
- `gt7_lap_hover_{1,2,3}_v062.png`, `gt7_window_hover_{1,3}_v062.png`, `acgym_lap_hover_v062.png`.
- `original_uploaded_position_v062.png`, `stationary_neutral_position_v062.png`,
  real-source section/Cockpit screenshots, ML/replay screenshots.
- `browser_console_v062.json`, `smoke_server.log`, `DATA_INTEGRITY_V062.json`.

## ML health and regression checks

`python -m scripts.assess_ml_v062` succeeded. It checks targets, split membership,
all frozen model/partition aggregate metrics and allowed historical baselines,
and produces separate diagnostic evidence. Exactly three existing fixed ACGym
model configurations are fitted on training-only prefixes with validation-only
evaluation; test telemetry/labels never enter those diagnostic fits. GT7's frozen
CSV metrics are recomputed without a new fit. Original frozen evidence/model-store
hashes remain unchanged (16 checked files).

`python -m scripts.verify_ml_v061` succeeded. Every current/frozen model, partition,
lap UID and checkpoint matches: 390 ACGym and 60 GT7 rows. All prediction/target/error/
baseline columns match within absolute `1e-9 s`; maximum prediction deviations are
`2.842170943040401e-14 s` and `1.4210854715202004e-14 s`. Selected SVR remains unchanged.
Logs are `ml_health_run.txt` and `frozen_regression.txt`; the complete diagnosis is in
[ML_HEALTH_ASSESSMENT_V062.md](ML_HEALTH_ASSESSMENT_V062.md).

## Limits and corrected attempts

- An initial hover driver observed a previous iframe layout while switching to
  window mode. The driver now waits for matching axis/source metadata and moves
  the pointer into the actual final chart before checking readout contents.
- Initial new unit assertions wrongly omitted an available wheel-load family and
  treated an available elapsed-time channel as absent; fixture/expectations were
  corrected to test true availability, rather than hiding valid signals.
- Real source examples do not have a verified planar heading declaration. Measured
  heading conversion is tested synthetically; real maps use labelled estimates.
- Browser evidence covers one desktop Chrome version and narrow desktop resizing,
  not all GPUs/engines or real mobile devices. The previous FB-007 intermittent
  symptom remains unreproduced; this release does not invent a root cause for it.
- The existing VS Code launch files and Streamlit entrypoint remain unchanged.
  The same module launch was exercised; an interactive F5 keypress was not automated.
