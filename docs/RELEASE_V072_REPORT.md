# Release v0.7.2 — ML diagnosis and feature engineering

Date: 2026-10-24, Europe/Rome. Branch: `feat/sim-telemetry-v072`, created from
verified v0.7.1 `a3e99dd`. Initial tree was clean. All 211 baseline tests passed
before branching (92 existing warnings, 146.17 s); the signed reference and frozen
evidence were inspected before experimental fitting. No push, merge, branch
deletion, reset or historical artifact overwrite occurred.

## Measured engineering decision

**Preserve the current SVR as the educational/operational reference. None of the
tested compact feature variants justifies replacement. A bounded sequence-model
pilot is a useful future research comparison, not a demonstrated improvement.**

Training is not missing slow laps: 26/103 are above training Q75, across seven
blocks, and its target range reaches 259.595 s. Validation is fast-heavy (36/66
fast), versus 5/36 fast in the already-observed historical test. This composition
plausibly contributes to the original error gap; within-band errors also differ,
and the audit does not establish a single cause.

The reference predicts direct final seconds from telemetry. Historical median
is a separate baseline, not its target, input or output correction. No structural
target/baseline defect was found. Central shrinkage remains measurable: development
OOF slope 0.351 and prediction/target SD ratio 0.511.

| Fixed SVR development experiment | Features | OOF MAE | Recording-macro MAE |
|---|---:|---:|---:|
| F0: original configuration | 13 | 13.361 s | 11.332 s |
| F1: trailing-window summaries | 20 | 13.381 s | 11.361 s |
| F2: observed events/path-distance proxy | 18 | 13.424 s | 11.472 s |
| F3: combined compact descriptors | 25 | 13.400 s | 11.385 s |
| F0W: separate training-only pace weighting | 13 | 13.317 s | 12.155 s |

Comparisons use **169 development laps / 40 recording blocks / 845 correlated
prefixes per variant**, on five fixed block folds. Historical test sources are
excluded before experimental feature generation. Each fold holds out eight blocks;
held-out lap counts are 16/30/33/47/43. Training sets overlap.

The new features use actual observed timestamps, trailing five-second windows,
already observed braking/slow/recovery phases and a ground-speed distance integral.
They use neither final distance/target normalization nor future samples. Raw
normalized-progress F4 is omitted because exact ACTI export mapping/resampling
semantics remain unestablished; the speed integral is a distance proxy, not
certified track phase. This omission blocks no valid lap or other experiment.

F1/F2/F3 differences are smaller than 0.07 s and do not improve recording macro
error. Weighting improves slow MAE 36.922 -> 34.115 s but worsens middle MAE
7.668 -> 9.231 s, improves only one fold and gives only 0.044 s pooled gain.
It fails the predeclared adoption rule. More variable predictions alone are not
accepted as success. Failed variants are reported without a post-score search.

## Implementation and interface

- All 205 valid complete laps remain available; no difficult lap is discarded.
  Importers, original numerical features/training/inference and shared hover
  component are unchanged.
- A new target-free API is shared by training and experimental replay, with fixed
  feature/version/units, timestamp support and causal boundary/gap checks.
- Separate signed research artifacts bind domain, original/development identities,
  features, protocol and folds. Research inference is labelled development-only;
  production remains the v0.7.1 SVR in its original namespace.
- Diagnostics require explicit opt-in and show fold variation, pace/checkpoint
  errors, calibration and deterministic ordinary/fast/slow/difficult examples.
  Default ML charts and reference Progressive Prediction remain functional;
  final target stays hidden until retrospective reveal.
- Frozen OOF evidence is verified/reused. Missing research models can be rebuilt
  on development only without rescoring folds or historical test.
- No dependency, telemetry acquisition, live capture or v0.7.2 DL model was added.
  Static reports use the already-installed optional Matplotlib.

## Reports and exact evidence

1. [Pace distributions, metadata, formulation and shrinkage](PACE_DISTRIBUTION_AUDIT_V072.md)
2. [Original/new feature definitions, actual experiments and tradeoffs](ML_FEATURE_EXPERIMENTS_V072.md)
3. [Eight-question model assessment and sequence feasibility](ML_MODEL_ASSESSMENT_V072.md)
4. [Next-release recommendation](NEXT_RELEASE_RECOMMENDATION.md)
5. [Architecture and boundaries](ARCHITECTURE_V072.md)

The [protocol](ML_PROTOCOL_V072.json), [folds](DEVELOPMENT_FOLDS_V072.csv),
[selection](DEVELOPMENT_SELECTION_V072.json), [results/hashes](ML_RESULTS_V072.json),
[OOF predictions](DEVELOPMENT_PREDICTIONS_V072.csv),
[checkpoint/lap/block/pace metrics](DEVELOPMENT_DETAILS_V072.csv) and
[preprocessing](DEVELOPMENT_PREPROCESSING_V072.csv) are committed. Five diagnostic
figure families have PNG/SVG exports under `docs/figures/*_v072.*`. Source progress
inspection, extreme derivative evidence and similar-aggregate pairs retain source IDs.

The recommendation proposes one small GRU or causal 1D CNN comparison against
F0/F3, deterministic baselines and a classical ordered-window comparator. It
specifies causal 10 Hz alignment, six channels, variable prefix lengths, masks,
padding, training-only transforms, group-aware early stopping and realistic
sample size: 169 unique laps, not 845 independent observations. A new untouched
holdout is needed for a new final-performance claim. Neural superiority is unproven.

## Automated and frozen verification

Final full suite: **233 passed, 92 warnings in 162.07 s**. All original 211 tests
are retained. The 22 new tests cover unique-lap distributions, pace boundaries,
stable groups, optional metadata, timestamp windows/units/gaps, future/tail/target
invariance, F0 preservation, training-only preprocessing/lap weights, identical
populations, poisoned-historical-data invariance, selection guards, signed rerun/
reconstruction, feature/domain guards and diagnostic/reference UI behavior.
No existing test is suppressed or weakened. The warnings remain historical
Keras/Torch NumPy deprecations; no new sequence/DL research model is trained.

`compileall`, `pip check` (no broken requirements) and `git diff --check` pass.
V072 JSON/CSV byte identities use fixed Git LF endings. The preservation inventory
checks **46 existing reference/document/model files** unchanged on this release
installation. Local binary/key hashes describe this installation; binaries and
signing keys remain ignored rather than published.

`python -m scripts.verify_baselines_v072` passes:

- Monza: 390 original model/target/error/baseline rows; maximum prediction
  deviation 2.842e-14 s at tolerance 1e-9 s.
- GT7: 60 original rows; maximum prediction deviation 1.421e-14 s.
- Barcelona: all 1,170 stored v0.7.1 evaluation rows match the signed reference;
  330 current SVR **validation** predictions match (maximum deviation 2.842e-14 s).
  This regression requests zero new historical-test predictions. Original test
  count stays one; new experimental historical-test evaluations stay zero.

See [regression](FROZEN_REGRESSION_V072.json),
[preservation hashes](BASELINE_PRESERVATION_V072.json) and
[verification summary](VERIFICATION_V072.json). A repeated development command
reuses frozen results; reconstruction is tested with prediction calls forbidden.

## Actual browser acceptance

Installed Chrome **156.0.8078.47**, local temporary Streamlit servers, actual CDP
pointer/keyboard interaction. All scenarios finish and stop their processes.

| Scenario | Workflow checks | Rendering budgets | Final performance record |
|---|---:|---:|---:|
| Full v072 | 73 | 55 | 1 |
| Focused v072-ml | 21 | 15 | 1 |
| Retained v063-baseline | 36 | 0 | 0 |
| Retained v063-fixtures | 4 | 4 | 0 |

Full v072 covers GT7/Monza/Barcelona Explorer families, Comparison, cursor geometry,
A/B rows/colors, null/gap policy, zoom/pan, 1600/960/480 px, keyboard and no hover-
triggered Python rerun/numerical mutation. It also checks frozen reference training/
evaluation, separate validation/historical-test views, development counts, every
diagnostic chart/readout, F3 inspection without production replacement, a predefined
slow example and 60 s target-hidden reference replay/reveal. Prior scenarios cover
actual Parquet/CSV uploads, maps/orientation, GG geometry and clockless charts.

Final runs have **zero console errors/unhandled runtime exceptions**; measured
cursor transform errors are zero. [UI_BROWSER_V072.json](UI_BROWSER_V072.json)
records current evidence. Screenshots/server/console logs stay in ignored
`artifacts/v072`, `artifacts/v072-ml`, `artifacts/v063-baseline` and
`artifacts/v063-fixtures`. Scope is desktop Chrome, not every browser/device,
independent future session or live simulator latency.

## Acceptance mapping

| Criteria | Result |
|---|---|
| AC1–AC2 | Unique-lap/metadata distributions, exact TRAIN quartiles, historical composition/calibration, direct target and separate baseline verified |
| AC3–AC4 | Original 13-feature audit, development information/redundancy/pairs, compact causal recent/event/distance descriptors |
| AC5–AC8 | Identical development folds/populations; all laps retained; one training-only weighting experiment; no historical-test tuning/scoring |
| AC9 | Fold/pooled/checkpoint/lap/recording/pace/tail/spread/calibration metrics and deterministic histories |
| AC10–AC12 | Original models/numerics preserved; optional diagnostics and causal replay; 233 tests and actual browser scenarios pass |
| AC13 | No new DL model or sequence experiment trained |
| AC14 | Negative feature-engineering outcome reported; reference retained; bounded future sequence feasibility and uncertainty documented |

Reproduce on the installed verified v0.7.1 reference using the explicit commands
in README. Ordinary page visits neither train nor download anything.
