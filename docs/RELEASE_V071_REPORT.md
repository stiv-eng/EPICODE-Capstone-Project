# Release v0.7.1 — Barcelona recovery and completed ML experiment

Date: 2026-10-24, Europe/Rome. Development branch: `feat/sim-telemetry-v071`,
based on the preserved v0.7 checkpoint `23796be` on `feat/sim-telemetry-v07`.
The earlier v0.6.3 baseline remains `7e304cc`. No branch was deleted, history
reset, push or merge performed. Original downloaded telemetry remains unchanged.

## Delivered behavior

All **205 technically usable complete Barcelona / Dallara F317 laps** are admitted,
including all 116 previously excluded for uncertain identity/date metadata and
one additional lap supported by a documented 0.5 ms timing-field rounding case.
Zero validated laps are excluded for metadata, slow pace or high model error.
The old 12-group / 6–3–3 policy is preserved as historical v0.7 evidence and is
not called by the v0.7.1 training/UI path.

The reproducible recording-block split freezes **103 train / 66 validation /
36 test laps**, in 30/10/11 blocks. All prefixes/laps of a block stay together.
Blocks are not certified independent physical sessions; unknown links and source
chronology limitations are explicitly retained. No unseen-session/driver or
prospective generalization claim is made.

Ridge, Random Forest and SVR actually trained using the original 13 causal
features, five checkpoints and training-only preprocessing. Validation MAEs:

| Model | Validation MAE |
|---|---:|
| Ridge | 12.441 s |
| Random Forest | 10.819 s |
| SVR, selected | 9.868 s |

Only selected SVR was evaluated on the frozen final test, once: **MAE 15.393 s,
RMSE 22.396 s, bias -6.442 s**, versus **17.901 s** MAE for the fixed training
median. Selected-test P90 absolute error is 36.705 s. Slow-lap MAE is 31.213 s;
these valid difficult laps remain in evaluation. Repeated commands/dashboard
training actions reuse verified frozen results rather than consume test again.

Experiment A retains every valid training lap. The prespecified optional B
category (valid source timer steps >100 ms) contains zero training laps, so no
filter was invented or applied. A/B selection code is tested on synthetic cases;
no measured A/B superiority is claimed without an actual category.

The primary ML/replay UI is Barcelona. It loads compatible locally signed models,
distinguishes three-model validation from selected-only test, shows real results,
and supports 10–60 s causal replay with target hidden until explicit retrospective
reveal. Revealing target/error does not change chart/hover inputs. Existing
Explorer, Comparison and v0.6.3 shared hover/cursor code remain functional.
Monza/GT7 reproduction uses `python -m scripts.archive_app` and its separate store.

## Evidence and recommendation

- [Dataset recovery and all remaining unusable-source reasons](BARCELONA_DATASET_AUDIT_V071.md)
- [Measured evaluation, baselines, tails, checkpoints and model health](ML_EVALUATION_V071.md)
- [Release/domain comparison](ML_COMPARISON_V071.md)
- [Next-release recommendation](NEXT_RELEASE_RECOMMENDATION.md)
- [Frozen protocol](BARCELONA_PROTOCOL_V071.json), [membership](BARCELONA_SPLIT_V071.csv),
  [selection before test](BARCELONA_SELECTION_V071.json), [result/evidence hashes](ML_RESULTS_V071.json)
- [Standalone PNG figure](figures/barcelona_health_v071.png) and [SVG export](figures/barcelona_health_v071.svg)

The nested same-domain curve improves SVR validation MAE 10.993 → 10.600 → 9.868 s
for 49/66/103 training laps, while slow-band error worsens. Preserve this reference
and prioritize bounded causal feature engineering with development-only comparison
and a new untouched final holdout. No deep-learning model was added. Monza-versus-
Barcelona MAE differences cannot identify a dataset-size effect across domains.

## Automated verification

The original 193 tests are retained. Eighteen additional tests cover recovery,
metadata leniency, exact versus coarse duplicates, invalid/rounded targets, stable
whole-block splits, lap-prefix leakage, training-only imputation/scaling,
validation-only ranking, matched training baselines, frozen rerun/reinstall and
tamper/interrupted-test handling, domain/protocol compatibility, future-prefix
invariance, absent-data offline startup, and target-hidden progressive UI behavior.

Final full suite: **211 passed, 92 warnings in 160.63 s**. The warnings are the
existing Keras/Torch NumPy deprecations from historical tests; none were suppressed.
After the final missing-label annotation, 38 relevant engine/UI/historical tests
pass again; the final primary UI checks also pass (2/2).
`compileall`, `pip check` (no broken requirements) and `git diff --check` pass.
No package installation, requirements change or VS Code/F5 change was needed.

`python -m scripts.verify_ml_v061` verifies **390 Monza + 60 GT7** historical
prediction/target/error/baseline rows at tolerance 1e-9 s. Maximum prediction
deviations: 2.842e-14 s and 1.421e-14 s respectively. Their numerical modules,
historical evidence and model-store namespace were not overwritten.

The second explicit `python -m scripts.run_barcelona_v071` succeeds by frozen
result reuse. Every recorded evidence hash matches; `test_evaluations` stays 1.
V071 JSON/CSV evidence has explicit Git LF attributes so Windows checkout
conversion cannot silently change byte hashes or the protocol identity.
Model reconstruction without a local artifact is independently tested to fit
TRAIN only, with held-out prediction calls forbidden.

## Actual browser verification

Actual installed Chrome **156.0.8078.47**, headless via CDP, with local temporary
Streamlit servers. Prior suites use the explicit historical archive environment;
the current suite uses the normal Barcelona entrypoint. Test harness corrections
support searchable virtualized select menus, wait for source-change reruns, and
inspect decoded Plotly arrays when checking displayed numerical MAE.

- `--release v063-baseline`: **36 prior checks pass**, including real original
  Parquet/stationary CSV uploads, scales, map position/orientation, GG geometry,
  multi-lap/window hover, archived ML startup and hidden-target replay.
- `--release v063`: **47 workflow checks pass**, plus 36 rendering-budget records
  and one final performance summary. Pointer/keyboard, time cursor geometry,
  A/B row/color stability, null/gap states, zoom/pan, 1600/960/480 px widths and
  no hover-triggered Python rerun/numerical mutation are retained.
- `--release v063-fixtures`: **4 type/clockless interactions pass**, plus four
  rendering-budget records.
- `--release v071`: **65 workflow checks pass**, plus 49 rendering-budget records
  and one final performance summary, with zero console errors/runtime exceptions.
  Extended Barcelona acceptance is recorded in
  [browser evidence](UI_BROWSER_V071.json) and [verification summary](VERIFICATION_V071.json).
  It covers Barcelona Explorer families, verified-lap Comparison, the inclusive
  population/split, explicit training/frozen reuse, three ML charts, displayed
  test MAE, validation model switching, selected-only test, progressive 60 s
  replay and target reveal preserving causal chart payloads.

The isolated `--release v071-ml` scenario also passes 13 ML/replay checks and
nine rendering-budget records. Checkpoint keyboard interaction uses the actual
native range input, including its observed export-sample offset within 100 ms.

Screenshots, local server/console logs and full per-run measurements remain in
ignored `artifacts/v071`, `artifacts/v063`, `artifacts/v063-baseline` and
`artifacts/v063-fixtures`. Servers/Chrome stop when each scenario finishes.
This evidence covers desktop Chrome; it does not certify every browser, physical
touch device, live simulator latency or an independently acquired future session.

## Acceptance mapping

| Criteria | Delivered evidence |
|---|---|
| AC1–AC4: reconsider quarantine, include usable data, no metadata/12-group block | Inclusive loader, 116+1 recovery, zero validated metadata exclusions, 205 eligible laps |
| AC5: reproducible split | Saved seed-42 recording-block membership before fitting |
| AC6: development-only optional filtering | Preregistered quality category/rule, zero qualifying TRAIN laps, inclusive A retained |
| AC7–AC8: actual models, baselines, health | Three validation fits, selected-only final test, learning curve and diagnostic CSVs |
| AC9: selected model in primary UI/replay | Compatible signed V071 artifact, separate validation/test, target-hidden causal replay |
| AC10: recoverable history | v0.7 commit/branch, unchanged raw files, separate historical stores, 450-row frozen regression |
| AC11: automated/browser validation | 211 automated tests; retained prior and current real Chrome evidence |
| AC12: complete health/recommendation | Measured evaluation, comparison and next-release documents linked above |

Reproduction is offline after acquisition. Dataset binaries, local signing keys
and model binaries remain ignored; committed tables/protocols/reports preserve the
measured experiment. No automated download is attached to ordinary app startup.
