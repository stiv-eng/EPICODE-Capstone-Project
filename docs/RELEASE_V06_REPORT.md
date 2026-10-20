# Release v0.6 report

Implemented on `feat/sim-telemetry-v06`, based on verified local v0.5 commit
`793a732`. The original v0.5 branch/commit remains recoverable. No merge, push,
history rewrite, unknown pickle deserialization or third-party code execution was
performed. Existing user files and historical modules were preserved.

## Delivered behavior

The release adds a bounded human multi-session dataset, independently checked lap
targets, causal elapsed-time snapshots, past-only baselines, three sklearn pipelines,
chronological whole-session/lap evaluation, trusted local artifacts and model-agnostic
replay. Two new Streamlit pages expose explicit training and retrospective prediction.
Actual targets remain separate from predictive sources and hidden in replay until
requested. Training never starts merely from opening a page.

The eligible ACGym subset has **55 verified laps, 11 physical session groups, eight
source participant codes**, 100% valid core values and 275 causal snapshots.
The 48 original source files total **241,902,674 payload bytes**. Exact URLs,
hashes, licenses, accepted/rejected spans and clock limitations are preserved in
the [dataset expansion report](DATASET_EXPANSION_V06.md) and its linked manifests.
The source is publisher-declared CC BY 4.0; attribution and our derivations are
documented. Raw files and binary model artifacts remain ignored locally.

Ridge, Random Forest and SVR were actually trained and evaluated. Entire ACGym
sessions were assigned chronologically: 29 training laps, 11 validation laps,
15 test laps. SVR was selected on validation MAE; frozen test MAE is **6.743 s**,
RMSE **10.838 s**, bias **-3.481 s**. Frozen historical-median baseline MAE is
**9.443 s** on the same 75 test prefixes. All individual errors, matched-baseline
coverage and checkpoint/lap/session summaries are retained. This is limited
single-car/track evidence, not a generalization guarantee.

GT7's eight laps support an explicit experimental 4/2/2 lap split. Robust training
is disabled, importance is suppressed for its tiny validation set, and the required
single-session disclaimer persists. The original attachment has no verified lap
targets and displays an eligibility explanation. No full Keras experiment was run;
only the unchanged pre-existing historical tests exercise their small fixtures.

## Validation evidence

Final complete run: **109 passed, 92 warnings in 68.97 seconds**
(`.venv\Scripts\python.exe -m pytest -q`). The warnings are the unchanged
historical Keras/PyTorch NumPy copy-keyword deprecations. No tests were skipped in
this populated local workspace. This includes all 84 prior tests, plus source
reader/manifest/target checks, physical grouping
and duplicate captures, future telemetry/clock-reset invariance, label separation,
train-only preprocessing, held-out-label invariance, baseline availability,
three-model training, unknown artifact rejection before deserialization, mapping
identity invalidation, missing channels, eligibility and Streamlit workflows.

The real Chrome smoke run completed successfully (exit 0): HTTP homepage/health
200; original Data Explorer, overview, inputs, dynamics, tyres, comparison,
position; GT7 overview/lap comparison; ACGym eligibility, baseline replay, explicit
three-model training, preserved models across sidebar navigation, checkpoint
advance to 30 s, hidden target followed by explicit evaluation, and GT7 experimental
training. Screenshots were visually inspected. Local screenshots/logs are under
ignored `artifacts/`, including `ml_evaluated_v06.png`,
`replay_ml_hidden_target_v06.png`, `replay_explicit_evaluation_v06.png`, and
`gt7_experimental_ml_v06.png`. The script shuts down its temporary server/browser.

`pip check`: **No broken requirements found.** No packages were installed.
`git diff --check` passes apart from informational Windows LF/CRLF conversion
messages. Original attachment SHA-256 remains
`fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`;
all 20 pinned GT7 source hashes were checked unchanged. Historical prediction/SVR
modules, GT7 manifest, `.vscode` and both existing launch configurations have no
diff from `793a732`. The same `python -m streamlit run streamlit_app.py` launch
entrypoint was exercised by the smoke script; no interactive VS Code F5 keypress
is claimed.

## Corrected or inconclusive investigations

- Initial download accounting counted expected LFS objects as cached transfers.
  Acquisition paused conservatively; correcting against actual local files allowed
  completion without duplicate payloads or exceeding the budget.
- The first file's 100 Hz grid did not describe every file. Measured later exports
  are 50 Hz; the adapter/audit now preserve each file's declared rate. No native
  acquisition-rate claim is made.
- One WL export has inconsistent folder/header dates and remains quarantined.
  Six A-series exports contain 51 timing-valid laps but unresolved independence;
  they are excluded from robust evaluation rather than counted as extra sessions.
- Tiny summary CSV `steps` counts were unsuitable for deciding LD lap coverage.
  Source timers, beacons, counter and countdown provide the accepted evidence.
- Initial browser driver attempts failed on asynchronous page navigation,
  synthetic checkbox clicks and an assumed explicit slider role. The driver now
  waits for page-specific content, uses real mouse clicks and the rendered native
  range input. The final complete browser run passed. These failed driver attempts
  were not reported as successful application checks.
- The first new UI test used a nonexistent AppTest state accessor. It was corrected
  to assert the visible no-training state; the complete subsequent suite passed.
- Final provenance review separated bundle revision IDs from optional per-file
  SHA-256 fields and carried forward GT7's original rejected-lap evidence. The
  numerical audit and complete 109-test suite were rerun successfully afterward.
- Source export timing semantics, uncertain near-duplicates, settings shifts,
  small session counts and calibration remain limitations. No common-distance
  reference, live simulator connection, hyperparameter search or Keras architecture
  is claimed.

## Git delivery

- `9b83c52`: bounded acquisition, safe numeric reader and validated source targets.
- `a15e2a3`: causal ML pipelines, past-only baselines, holdouts and measured evidence.
- `2831f45`: explicit training/replay dashboards and offline/browser integration.
- `bee0f97`: separate bundle/file provenance and preserve GT7 rejection evidence.
- The following documentation handoff commit contains this report, README,
  changelog and next-release recommendation. Its final hash is available through
  `git log -1 --oneline`; the branch remains local with no upstream push.

The final working tree is checked clean after committing the documentation. All
implementation/evidence is on `feat/sim-telemetry-v06`; v0.5 is its ancestor.

## Changed files

New Python files:

```text
motorsport/ingestion/motec.py
motorsport/ingestion/acgym_importer.py
motorsport/ml/__init__.py
motorsport/ml/dataset.py
motorsport/ml/features.py
motorsport/ml/baselines.py
motorsport/ml/training.py
motorsport/ml/evaluation.py
motorsport/ml/inference.py
motorsport/ml/artifacts.py
motorsport_ui/ml.py
pages/20_Machine_Learning.py
pages/21_Progressive_Prediction.py
scripts/download_acgym.py
scripts/audit_v06.py
tests/test_ml_v06.py
tests/test_ml_ui_v06.py
```

Modified existing files:

```text
streamlit_app.py
scripts/smoke_app.py
requirements.txt
README.md
CHANGELOG.md
data/raw/README.md
```

New documentation/evidence:

```text
docs/ACGYM_MANIFEST_V06.json
docs/ACGYM_LAP_AUDIT_V06.csv
docs/DATASET_MEASUREMENTS_V06.json
docs/ACGYM_ML_ERRORS_V06.csv
docs/GT7_ML_ERRORS_V06.csv
docs/ML_RESULTS_V06.json
docs/DATASET_EXPANSION_V06.md
docs/ML_FEATURES_V06.md
docs/ML_EVALUATION_V06.md
docs/ARCHITECTURE_V06.md
docs/RELEASE_V06_REPORT.md
docs/NEXT_RELEASE_RECOMMENDATION.md
```

See [architecture and Python function guide](ARCHITECTURE_V06.md) for a technical
walkthrough, [feature definitions](ML_FEATURES_V06.md) for physical meaning and
leakage boundaries, [evaluation](ML_EVALUATION_V06.md) for specifications/results,
and the [v0.7 recommendation](NEXT_RELEASE_RECOMMENDATION.md) for next work.

## Acceptance

AC1–AC14 are covered by the delivered code and executed checks: prior dashboard
and datasets remain functional; causal feature/baseline/model APIs and leakage
tests pass; splits preserve lap/physical-session identities; both new UI workflows
operate; the additional corpus was acquired safely and integrated; ineligible
robust training is refused; launch configuration and v0.5 baseline are preserved.
This acceptance concerns engineering behavior and honest reporting, not proof of
statistical adequacy or real-time deployment readiness.
