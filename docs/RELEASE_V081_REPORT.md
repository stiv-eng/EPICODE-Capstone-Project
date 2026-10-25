# Release v0.8.1 — High-frequency progressive prediction and stop-aware SVR

All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, using the original five v072 folds. All **205 validated laps** remain preserved. **Zero new predictions on the 36 historical test laps** for selection. Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. Operational model: original signed **SVR v0.7.1**, unchanged.


Baseline `11c11f8` on `feat/sim-telemetry-v080`, initially clean. Work is isolated on `feat/sim-telemetry-v081`; no merge, push, reset, deletion, dataset modification or model promotion. Before implementation: **257 tests passed, 217 existing deprecation warnings, 189.60 s**. All existing tests are retained. Earlier recommendation is archived byte-for-byte in `NEXT_RELEASE_RECOMMENDATION_V080.md`; earlier frozen reports and artifacts are preserved by hash.

## Delivered behavior

The additional **Replay frequente v0.8.1** mode supports 1 s default, 5 s compatibility, and measured optional 0.5 s cadence on recorded observations. It shows actual elapsed time, nominal checkpoint, sample age, speed, state, model identity, raw/bounded/stop-aware comparison, playback/pause and explicit retrospective reveal. Existing operational replay, v080 GRU/Ridge comparison, analysis pages and shared cursor stay available. Model loads and unchanged prefix predictions are cached; timed updates use a Streamlit fragment. Startup does not fit models.

## Engineering assessment


1. **One second versus five seconds:** yes for practical observation frequency: 21054 instead of 4134 source checkpoints, with shared predictions unchanged. This is responsiveness, not a cadence-only accuracy gain.
2. **Half-second practicality:** inference gate passed=True; P95 2.007 ms, isolated process peak 321.0 MiB. Actual browser measurements are reported separately; no live telemetry connection exists.
3. **Existing SVR without retraining:** it supports the new observations, matches frozen shared cutoffs within 5.12e-12 s, and gives one-second raw MAE 8.787312 s. It retains large slow-tail limitations; denser inference is not a new accuracy guarantee.
4. **Denser training accuracy:** One-second training raw MAE **8.540758 s**, versus A **8.787312 s**: gain **0.246554 s (2.806%)**. Preregistered retention gate: gain ≥0.2 s and ≥2%, improvement in ≥4/5 folds. Gate passed: **True**.
5. **Reaction to a stop:** yes under the constant-estimated-remaining-time assumption, after 1 s confirmation. Synthetic +5 observed stationary seconds gives exactly +5 predicted seconds; 20 recorded laps meet the fixed detection rule. Real predictive scores are separate.
6. **Model versus rules:** A's parameters never change. Raw→bound 8.787312→8.708057 s; bound→stop-aware 8.708057→8.708926 s. These differences are deterministic correction effects. B is the sole new learned comparison.
7. **Ordinary moving laps:** on 149 no-stop laps the stop correction equals bounded output exactly (MAE difference 0.000000000000 s). Resuming portions of stop laps have an explicit 2 s transition and may differ.
8. **Slow-lap errors:** remain significant: corrected slow MAE 22.275238 s, worst 134.818332 s. Projection prevents impossibility but cannot recover correct unknown remaining driving time.
9. **Operational promotion:** retain signed SVR v0.7.1. SVR-DENSE merits further controlled operational validation, but this reused development comparison does not justify promotion. Raw and corrected outputs stay auditable.
10. **Highest-value next step:** preregister untouched same-domain recording evaluation, including independently annotated stops and slow laps; validate remaining-time calibration and resume behavior there. Avoid another broad architecture or cadence search.


## Position research

The author's [MotecLoader](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/assetto_corsa_gym/AssettoCorsaEnv/motec_loader.py) explicitly renames `car pos norm` to `NormalizedSplinePosition`, removes repeated timer rows and uses stride downsampling. This improves mapping evidence beyond v080. It still does not certify ACTI acquisition/interpolation kernel, per-sample latency or reverse-motion behavior in these exact exports. The [project](https://assetto-corsa-gym.github.io/) identifies ACTI for human collection. Existing development audit has range 0–1 and terminal wraps in 169 laps, but local reversals are ambiguous. No current-position predictor is admitted; all updates remain time-based, and no eventual-time progress fraction is used. This does not block release.

## Validation and reproducibility

Final automated/browser evidence is in [verification](VERIFICATION_V081.json), [browser checks](UI_BROWSER_V081.json) and [historical regression](FROZEN_REGRESSION_V081.json). Actual Chrome checks retain the full prior v080 analysis/ML/GRU/cursor workflow and add recorded replay, cadence, pause, causal payload, reveal, numerical hover invariance and responsive sizing. Synthetic tests establish rule behavior only, not predictive accuracy.

Final suite: **287 passed, zero failed/skipped**, 217 existing Keras/Torch NumPy deprecation warnings, 194.18 s. Actual Chrome: **99 workflow checks, 55 rendering budgets, 1 performance record**, zero console errors/runtime exceptions. Compileall, dependency consistency, baseline hashes and whitespace checks passed.

Measured Chrome median wall intervals: v081 playback and pause 5 secondi: fewer than two timed transitions in observation window, v081 playback and pause 1 secondo: 1.109 s, v081 playback and pause 0.5 secondi: 0.485 s. Source checkpoint spacing remains exact; polling/render jitter affects wall intervals.

## Acceptance evidence

| Criteria | Evidence |
| --- | --- |
| AC1, AC11, AC12 | 339-file baseline inventory, 205 validated laps, 169 development-only laps, zero new historical-test predictions |
| AC2–AC4 | Three elapsed cadences, actual timestamps, zero shared-cadence prediction deviation; frozen v080 within 5.12e-12 s |
| AC5–AC8 | Raw/bounded/stop-aware outputs, zero corrected physical violations, causal sample-level hysteresis and resume; synthetic and recorded checks |
| AC9–AC10 | One focused 1 s SVR configuration, matched per-lap penalty mass, separate frequency/training/rule attribution |
| AC13–AC14 | Recorded fragment replay, pause, hidden target, original operational and GRU/Ridge modes and analysis preserved |
| AC15–AC16 | Full automated suite, actual Chrome evidence, frozen regression and reproducible measured reports / ten answers |

Run `python -m scripts.prepare_barcelona_v081`, `python -m scripts.run_barcelona_v081 --train-one-second`, `python -m scripts.verify_baselines_v081`, `python -m pytest -q`, `python -m scripts.smoke_app --release v081 --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`, then `python -m scripts.report_barcelona_v081`. Existing result files are verified and reused. Required local source/model artifacts must already be installed; no new acquisition is performed. No infrastructure or dependency is added.

[High-frequency inference](HIGH_FREQUENCY_INFERENCE_V081.md) · [Stop-aware rules and cohorts](STOP_AWARE_PREDICTION_V081.md) · [Focused training comparison](SVR_CADENCE_COMPARISON_V081.md) · [Complete evaluation](ML_EVALUATION_V081.md) · [Architecture](ARCHITECTURE_V081.md) · [Recommendation](NEXT_RELEASE_RECOMMENDATION.md).
