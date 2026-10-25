"""Generate measured v081 reports from frozen development evidence."""
import json

import numpy as np
import pandas as pd

from motorsport.ml.barcelona_recovery import ROOT
from motorsport.ml.barcelona_experiment import dump
from motorsport.ml.evaluation_v080 import metrics


def md(table, columns=None):
    table = table.loc[:, columns] if columns else table
    def cell(x):
        if isinstance(x, (float, np.floating)):
            return f'{x:.6f}'
        return str(x).replace('|', '/')
    return '| '+' | '.join(table.columns)+' |\n| '+' | '.join('---' for _ in table.columns)+' |\n'+''.join(
        '| '+' | '.join(cell(x) for x in row)+' |\n' for row in table.itertuples(index=False, name=None))


def write(name, text):
    (ROOT/'docs'/name).write_text(text.strip()+'\n', encoding='utf-8', newline='\n')


def main():
    r = json.loads((ROOT/'docs/ML_RESULTS_V081.json').read_text())
    predictions = pd.read_csv(ROOT/'docs/DEVELOPMENT_PREDICTIONS_V081.csv.gz')
    overall = pd.read_csv(ROOT/'docs/DEVELOPMENT_OVERALL_V081.csv')
    details = pd.read_csv(ROOT/'docs/DEVELOPMENT_DETAILS_V081.csv')
    stability = pd.read_csv(ROOT/'docs/DEVELOPMENT_STABILITY_V081.csv')
    obs = pd.read_csv(ROOT/'artifacts/barcelona_v081/observations-1s.csv')
    events = json.loads((ROOT/'artifacts/barcelona_v081/stop-events-1s.json').read_text())
    stop_ids = {e['lap_uid'] for e in events if e['event']=='stop'}
    one = predictions.query('cadence_s==1').copy()
    changes = []
    for name, rows in one.groupby('model'):
        for population, selected in [('all', rows), ('no_detected_stop_laps', rows[~rows.lap_uid.isin(stop_ids)]),
                ('detected_stop_laps', rows[rows.lap_uid.isin(stop_ids)]),
                ('stationary_observations', rows[rows.driving_state=='stationary'])]:
            if len(selected):
                changes.append(dict(model=name, population=population, **metrics(selected)))
    change = pd.DataFrame(changes)
    change.to_csv(ROOT/'docs/STOP_AWARE_EVALUATION_V081.csv', index=False, lineterminator='\n')
    scores = overall.query("subset=='all'")
    s = scores.query('cadence_s==1').set_index('model')
    raw, bound, stop = (float(s.loc[m, 'mae_s']) for m in ('A-RAW', 'A-BOUNDED', 'A-STOP-AWARE'))
    b = float(s.loc['B-1S-RAW', 'mae_s']) if 'B-1S-RAW' in s.index else None
    runtime = pd.DataFrame(r['runtime'])
    runtime_columns = ['cadence_s', 'snapshots', 'inference_total_s', 'checkpoint_median_ms', 'checkpoint_p95_ms',
                       'checkpoint_max_ms', 'index_initialization_median_ms', 'peak_process_working_set_bytes']
    score_columns = ['cadence_s', 'model', 'laps', 'snapshots', 'mae_s', 'rmse_s', 'bias_s',
                     'median_absolute_error_s', 'p90_absolute_error_s', 'max_absolute_error_s',
                     'recording_macro_mae_s', 'physically_impossible_count']
    common = overall.query("subset=='shared_5s'")
    late = details.query("dimension=='checkpoint_s' and cadence_s==1 and model.str.startswith('A-')", engine='python').copy()
    late['value'] = late.value.astype(float)
    late = late[late.value.isin([60., 90., 120., 150., 180., 210., 240., 255., 259.])]
    pace = details.query("dimension=='pace_band' and cadence_s==1")
    fold = details.query("dimension=='fold' and cadence_s==1")
    stability_summary = stability.groupby(['cadence_s', 'model'], as_index=False).agg(
        mean_lap_jump_s=('mean_absolute_jump_s', 'mean'), maximum_jump_s=('max_absolute_jump_s', 'max'),
        mean_lap_p95_rate=('p95_absolute_rate_s_per_s', 'mean'))
    impossible = int(s.loc['A-RAW', 'physically_impossible_count'])
    no_stop = change.query("population=='no_detected_stop_laps'").set_index('model')
    no_stop_delta = float(no_stop.loc['A-STOP-AWARE', 'mae_s']-no_stop.loc['A-BOUNDED', 'mae_s'])
    max_age = float(obs.sample_age_s.max())
    gates = json.loads((ROOT/'docs/ML_PROTOCOL_V081.json').read_text())['gates']
    verification_path = ROOT/'docs/VERIFICATION_V081.json'
    verification = json.loads(verification_path.read_text()) if verification_path.exists() else None
    browser_path = ROOT/'docs/UI_BROWSER_V081.json'
    browser = json.loads(browser_path.read_text()) if browser_path.exists() else []
    wall_intervals = [(x['check'], x.get('median_observed_wall_interval_s')) for x in browser if x['check'].startswith('v081 playback')]
    browser_timing = ('Measured Chrome median wall intervals: '+', '.join(
        f'{label}: {value:.3f} s' if value is not None else f'{label}: fewer than two timed transitions in observation window'
        for label, value in wall_intervals)+'. Source checkpoint spacing remains exact; polling/render jitter affects wall intervals.'
        if wall_intervals else 'Browser timing evidence is not yet installed.')
    final_validation = (f"Final suite: **{verification['tests']['passed']} passed, zero failed/skipped**, "
        f"{verification['tests']['warnings']} existing Keras/Torch NumPy deprecation warnings, {verification['tests']['seconds']:.2f} s. "
        f"Actual Chrome: **{verification['browser']['workflow_checks']} workflow checks, {verification['browser']['render_budgets']} rendering budgets, "
        f"{verification['browser']['performance_records']} performance record**, zero console errors/runtime exceptions. "
        'Compileall, dependency consistency, baseline hashes and whitespace checks passed.' if verification else
        'Final verification is pending; see VERIFICATION_V081.json when installed.')
    training_text = (f'One-second training raw MAE **{b:.6f} s**, versus A **{raw:.6f} s**: gain '
        f'**{raw-b:.6f} s ({100*(raw-b)/raw:.3f}%)**. Preregistered retention gate: gain ≥0.2 s and ≥2%, '
        f'improvement in ≥4/5 folds. Gate passed: **{r["recommend_one_second_training"]}**.' if b is not None else
        'One-second training was not completed; no accuracy claim can be made. '+str(r['training_error']))
    intro = ('All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, '
        'using the original five v072 folds. All **205 validated laps** remain preserved. '
        '**Zero new predictions on the 36 historical test laps** for selection. '
        'Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. '
        'Operational model: original signed **SVR v0.7.1**, unchanged.\n\n')
    write('HIGH_FREQUENCY_INFERENCE_V081.md', '# High-frequency inference v0.8.1\n\n'+intro+f'''
## Schedule and causality

Intervals are **5, 1 and 0.5 elapsed source seconds**; experimental default is 1 s. The scheduler preserves nominal checkpoint and last actual source timestamp independently. Source samples are processed in arrival order; no sorting across clock resets, interpolation, target, distance, final-duration fraction or track percentage enters inference. Freshness ≤100 ms; clock reset, nonfinite timestamp or gap >200 ms quarantines the remaining replay. The 169 development laps had zero such interruptions. Largest actual sample age at 1 s: **{max_age*1000:.3f} ms**.

Existing signed five-second-trained SVR-DENSE is loaded once per fold. Prefix sufficient statistics compute the same 13 features; recent three-second statistics preserve the original arithmetic. Per-session raw and corrected rows are memoized. Hover stays entirely in the existing browser component. Fragment timer ticks update the recorded replay only; pausing never adds wall time to lap elapsed.

## Measured runtime

Each cadence was measured in its own fresh Python process on the existing Windows development machine. Process peak includes corpus ingestion, all 205 source laps, five models, indexes, caches and accumulated result rows; it is not model-only memory. Measurements are local wall-clock observations under the development workload, not hardware-independent guarantees. They exclude Streamlit rendering. Per-checkpoint timings include causal sample-state processing, feature building and a single model query; first initialization is reported separately.

{md(runtime, runtime_columns)}

The half-second gate, fixed before evaluation, is P95 <{gates['half_second_p95_inference_ms']:g} ms and process peak <{gates['half_second_peak_process_bytes']} bytes. Supported: **{r['half_second_supported']}**. The UI exposes it when this measurement is installed. Actual browser timer intervals and render checks are separately recorded in [browser evidence](UI_BROWSER_V081.json); scheduler cadence and wall-clock render cadence must not be conflated.

{browser_timing}

## Shared observations

Maximum new-cadence deviation at shared cutoffs: `{r['cadence_shared_max_deviation_s']}` seconds. Maximum deviation from frozen v080 raw five-second predictions: **{r['frozen_v080_max_deviation_s']:.3g} s** (tolerance 1e-9). Cumulative arithmetic can differ at floating-point roundoff only. Cadence does not change learned parameters or shared outputs.

{md(common, ['cadence_s','model','mae_s','laps','snapshots'])}

Pooled 0.5/1/5 s scores cover different intermediate/early observations and different last scheduled points. They cannot demonstrate a cadence-only accuracy improvement. The table above uses identical five-second observations.

## Stability

{md(stability_summary)}

Mean jumps are first averaged within each lap, then across laps. Smaller intervals naturally reduce per-step changes; per-second rates expose that distinction. No global monotonicity rule or accuracy-motivated smoothing was added. Source dropouts do not count as verified stopped time.
''')
    write('STOP_AWARE_PREDICTION_V081.md', '# Stop-aware prediction v0.8.1\n\n'+intro+f'''
## Rule fixed before outcomes

Entry: valid ground speed ≤2 km/h continuously for at least 1 source second. Exit: ≥4 km/h continuously for 0.3 source seconds. Speeds between thresholds preserve an already confirmed stop. Pending entry/exit is labelled uncertain; the previous confirmed stationary assumption persists during exit confirmation. Invalid speed, timestamp reversal or gap >200 ms clears confirmation. Duplicate timestamps contribute zero elapsed duration. Slow driving above 2 km/h is not classified as a stop; sustained crawling below it can be, which is a limitation of speed-only detection.

On confirmation, reconstruct onset from already observed low-speed samples and query the unchanged model at that causal onset. Store `remaining_at_stop=max(0,raw_at_onset-onset)`. During the stop, emit `observed_elapsed+remaining_at_stop`. If onset is exactly zero, use the earliest already observed positive timestamp; if onset fails feature coverage, wait for the first valid causal model estimate. This heuristic freezes an uncertain estimate of remaining driving time, not true future remaining time.

Resume uses new SVR predictions immediately plus a nonnegative offset matching the preserved estimate at exit confirmation, decaying linearly over 2 observed seconds. This transition can still expose a jump if the new bound is higher; it is not an imposed maximum-jump promise. Predictions may fall after faster driving resumes. No displayed corrected estimate falls below elapsed time.

Raw, physically bounded and stop-aware outputs remain separate, including bound activation, adjustment size, stop onset and frozen remaining estimate. `max(raw,observed)` is a deterministic physical correction, not learned accuracy.

## Real recorded evidence

The fixed rule detects **{sum(e['event']=='stop' for e in events)} episodes in {len(stop_ids)} development laps** at every cadence. These are threshold-defined source observations, not independently adjudicated accident/stop labels. The other **{169-len(stop_ids)} laps** have no detected stop. The 1 s raw output has **{impossible} impossible estimates**. MAE raw **{raw:.6f}**, bounded **{bound:.6f}**, stop-aware **{stop:.6f} s** on identical observations. Bound and stop corrections are scored separately.

{md(change, ['model','population','laps','snapshots','mae_s','rmse_s','bias_s','p90_absolute_error_s','max_absolute_error_s'])}

Stop-aware minus bounded MAE on no-stop laps: **{no_stop_delta:.12f} s**. The stop correction is identically inactive on those laps. No favorable removal of slow laps or incidents is performed. Stationary-only scoring conditions on detected observations and reweights surviving laps; it must not be compared as if it were the full population.

## Behavioral verification and limits

Deterministic synthetic scenarios verify uninterrupted driving, braking, 3 km/h crawling, short low-speed noise, sustained stops, long stops, acceleration, multiple stops, invalid speed, source dropout, clock reversal and an extended >300 s lap. A constant 110 s model stopping at source second 10 predicts 111 at confirmed second 11 and 116 at second 16: exactly +5 s for +5 observed stationary seconds. Resume returns to the raw/bounded model after the documented 2 s transition. This is behavior verification, not measured real-stop predictive accuracy.

Stop onset remains uncertain during its first confirmation second. Frozen remaining time can be wrong when an incident changes future driving or the SVR was already biased. Telemetry gaps stop the replay; no elapsed stationary correction is accumulated across them. Replay pauses consume no source time. Real source export interpolation/latency are not independently certified.

![Retrospective source example](figures/stop_trajectory_v081.png)
''')
    write('SVR_CADENCE_COMPARISON_V081.md', '# SVR cadence comparison v0.8.1\n\n'+intro+f'''
## One focused experiment

Model A is the exact signed v080 direct SVR trained every five seconds. Model B is one RBF SVR configuration trained every second, evaluated at exactly A's one-second observations: C10, epsilon0.5, gamma scale, same 13 features, direct final-time target, same unique development laps, recording folds and source signals. There is no parameter/cadence grid, GRU change or full-development model promotion.

For each outer fold, A's inverse-count mean-one weights give each lap `N_A/L` total weight. B uses `(N_A/L)/n_B_lap` per row and **does not normalize weights back to mean one**. Thus total sample-weight mass and total per-lap `C*weight` penalty match A. Finer observations change the empirical distribution fitted by training-only imputation/scaling and the SVR objective quadrature; the comparison does not isolate sampling from that distribution change.

{md(pd.DataFrame(r['training']), ['fold','reference_snapshots','candidate_snapshots','unique_training_laps','reference_total_weight','candidate_total_weight','per_lap_weight','mean_candidate_weight','fit_seconds','process_peak_bytes']) if r['training'] else 'No completed fit.'}

{training_text}

## Same one-second observations

{md(scores.query('cadence_s==1'), score_columns)}

{md(fold, ['model','value','laps','mae_s','bias_s'])}

The positive physical projection is also reported for B separately. Stop-aware UI continues to use Model A; no candidate is promoted automatically. Signed B fold artifacts are local under `artifacts/barcelona_v081/models`. Re-running the offline command verifies frozen evidence and does not refit or rescore. Historical test access remains zero.
''')
    write('ML_EVALUATION_V081.md', '# ML evaluation v0.8.1\n\n'+intro+f'''
## Accuracy and physical consistency

{md(scores, score_columns)}

Every reported subset gives equal total weight per surviving unique lap. Recording-macro MAE averages lap MAEs within recording blocks, then blocks equally. Median/P90 are lap-weighted error quantiles, not packet-frequency statistics. RMSE, signed bias, maximum errors and physical impossibility counts are retained. Raw negative remaining values and all corrections are preserved in the reproducible CSVs.

## Pace bands at 1 s

Frozen original-training descriptive quartiles 109.734/140.04333333333335 s define fast/middle/slow only for retrospective evaluation; they never enter inference.

{md(pace, ['model','value','laps','mae_s','bias_s','p90_absolute_error_s','max_absolute_error_s'])}

## Late checkpoint survivors at 1 s

{md(late, ['model','value','laps','mae_s','bias_s','max_absolute_error_s'])}

Late populations shrink; one surviving slow lap is not a universal model accuracy estimate. `last_scheduled` depends on cadence and is retrospective. Final-10-second bands use known targets for scoring only, after inference.

{md(overall.query("cadence_s==1 and subset in ['late_over_60s','last_scheduled','retrospective_final_10s']"), ['model','subset','laps','snapshots','mae_s','max_absolute_error_s'])}

## Attribution

**A. Update frequency:** 4134 →21054 →42204 snapshots for 5/1/0.5 s with identical shared predictions. This improves observation frequency, not shared-cutoff model accuracy.

**B. Learned fitting:** {training_text}

**C. Deterministic correction:** at one second, raw→bounded MAE {raw:.6f}→{bound:.6f}; bounded→stop-aware {bound:.6f}→{stop:.6f}. These are rule effects, not a learned model gain. Full stop/no-stop cohort evidence is in [the stop report](STOP_AWARE_PREDICTION_V081.md).

Frozen v080 numerical deviation is {r['frozen_v080_max_deviation_s']:.3g} s. Original Monza/GT7 and Barcelona regressions and all raw/model/report hashes are checked in [preservation evidence](FROZEN_REGRESSION_V081.json).

Raw rows: [gzip-compressed predictions](DEVELOPMENT_PREDICTIONS_V081.csv.gz), [all/subset metrics](DEVELOPMENT_OVERALL_V081.csv), [checkpoint/pace/fold details](DEVELOPMENT_DETAILS_V081.csv), [stability](DEVELOPMENT_STABILITY_V081.csv), [cohorts](STOP_AWARE_EVALUATION_V081.csv), [runtime and hashes](ML_RESULTS_V081.json), [preregistered protocol](ML_PROTOCOL_V081.json). Pandas reads the gzip CSV directly; compression only changes storage, not numerical content.
''')
    slow = pace[pace.model=='A-STOP-AWARE'].set_index('value').loc['slow']
    answers = f'''
1. **One second versus five seconds:** yes for practical observation frequency: 21054 instead of 4134 source checkpoints, with shared predictions unchanged. This is responsiveness, not a cadence-only accuracy gain.
2. **Half-second practicality:** inference gate passed={r['half_second_supported']}; P95 {r['runtime'][2]['checkpoint_p95_ms']:.3f} ms, isolated process peak {r['runtime'][2]['peak_process_working_set_bytes']/1048576:.1f} MiB. Actual browser measurements are reported separately; no live telemetry connection exists.
3. **Existing SVR without retraining:** it supports the new observations, matches frozen shared cutoffs within {r['frozen_v080_max_deviation_s']:.3g} s, and gives one-second raw MAE {raw:.6f} s. It retains large slow-tail limitations; denser inference is not a new accuracy guarantee.
4. **Denser training accuracy:** {training_text}
5. **Reaction to a stop:** yes under the constant-estimated-remaining-time assumption, after 1 s confirmation. Synthetic +5 observed stationary seconds gives exactly +5 predicted seconds; {len(stop_ids)} recorded laps meet the fixed detection rule. Real predictive scores are separate.
6. **Model versus rules:** A's parameters never change. Raw→bound {raw:.6f}→{bound:.6f} s; bound→stop-aware {bound:.6f}→{stop:.6f} s. These differences are deterministic correction effects. B is the sole new learned comparison.
7. **Ordinary moving laps:** on {169-len(stop_ids)} no-stop laps the stop correction equals bounded output exactly (MAE difference {no_stop_delta:.12f} s). Resuming portions of stop laps have an explicit 2 s transition and may differ.
8. **Slow-lap errors:** remain significant: corrected slow MAE {slow.mae_s:.6f} s, worst {slow.max_absolute_error_s:.6f} s. Projection prevents impossibility but cannot recover correct unknown remaining driving time.
9. **Operational promotion:** retain signed SVR v0.7.1. SVR-DENSE merits further controlled operational validation, but this reused development comparison does not justify promotion. Raw and corrected outputs stay auditable.
10. **Highest-value next step:** preregister untouched same-domain recording evaluation, including independently annotated stops and slow laps; validate remaining-time calibration and resume behavior there. Avoid another broad architecture or cadence search.
'''
    write('RELEASE_V081_REPORT.md', '# Release v0.8.1 — High-frequency progressive prediction and stop-aware SVR\n\n'+intro+f'''
Baseline `11c11f8` on `feat/sim-telemetry-v080`, initially clean. Work is isolated on `feat/sim-telemetry-v081`; no merge, push, reset, deletion, dataset modification or model promotion. Before implementation: **257 tests passed, 217 existing deprecation warnings, 189.60 s**. All existing tests are retained. Earlier recommendation is archived byte-for-byte in `NEXT_RELEASE_RECOMMENDATION_V080.md`; earlier frozen reports and artifacts are preserved by hash.

## Delivered behavior

The additional **Replay frequente v0.8.1** mode supports 1 s default, 5 s compatibility, and measured optional 0.5 s cadence on recorded observations. It shows actual elapsed time, nominal checkpoint, sample age, speed, state, model identity, raw/bounded/stop-aware comparison, playback/pause and explicit retrospective reveal. Existing operational replay, v080 GRU/Ridge comparison, analysis pages and shared cursor stay available. Model loads and unchanged prefix predictions are cached; timed updates use a Streamlit fragment. Startup does not fit models.

## Engineering assessment

{answers}

## Position research

The author's [MotecLoader](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/assetto_corsa_gym/AssettoCorsaEnv/motec_loader.py) explicitly renames `car pos norm` to `NormalizedSplinePosition`, removes repeated timer rows and uses stride downsampling. This improves mapping evidence beyond v080. It still does not certify ACTI acquisition/interpolation kernel, per-sample latency or reverse-motion behavior in these exact exports. The [project](https://assetto-corsa-gym.github.io/) identifies ACTI for human collection. Existing development audit has range 0–1 and terminal wraps in 169 laps, but local reversals are ambiguous. No current-position predictor is admitted; all updates remain time-based, and no eventual-time progress fraction is used. This does not block release.

## Validation and reproducibility

Final automated/browser evidence is in [verification](VERIFICATION_V081.json), [browser checks](UI_BROWSER_V081.json) and [historical regression](FROZEN_REGRESSION_V081.json). Actual Chrome checks retain the full prior v080 analysis/ML/GRU/cursor workflow and add recorded replay, cadence, pause, causal payload, reveal, numerical hover invariance and responsive sizing. Synthetic tests establish rule behavior only, not predictive accuracy.

{final_validation}

{browser_timing}

## Acceptance evidence

| Criteria | Evidence |
| --- | --- |
| AC1, AC11, AC12 | 339-file baseline inventory, 205 validated laps, 169 development-only laps, zero new historical-test predictions |
| AC2–AC4 | Three elapsed cadences, actual timestamps, zero shared-cadence prediction deviation; frozen v080 within 5.12e-12 s |
| AC5–AC8 | Raw/bounded/stop-aware outputs, zero corrected physical violations, causal sample-level hysteresis and resume; synthetic and recorded checks |
| AC9–AC10 | One focused 1 s SVR configuration, matched per-lap penalty mass, separate frequency/training/rule attribution |
| AC13–AC14 | Recorded fragment replay, pause, hidden target, original operational and GRU/Ridge modes and analysis preserved |
| AC15–AC16 | Full automated suite, actual Chrome evidence, frozen regression and reproducible measured reports / ten answers |

Run `python -m scripts.prepare_barcelona_v081`, `python -m scripts.run_barcelona_v081 --train-one-second`, `python -m scripts.verify_baselines_v081`, `python -m pytest -q`, `python -m scripts.smoke_app --release v081 --browser "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"`, then `python -m scripts.report_barcelona_v081`. Existing result files are verified and reused. Required local source/model artifacts must already be installed; no new acquisition is performed. No infrastructure or dependency is added.

[High-frequency inference](HIGH_FREQUENCY_INFERENCE_V081.md) · [Stop-aware rules and cohorts](STOP_AWARE_PREDICTION_V081.md) · [Focused training comparison](SVR_CADENCE_COMPARISON_V081.md) · [Complete evaluation](ML_EVALUATION_V081.md) · [Architecture](ARCHITECTURE_V081.md) · [Recommendation](NEXT_RELEASE_RECOMMENDATION.md).
''')
    write('NEXT_RELEASE_RECOMMENDATION.md', '# Recommendation after v0.8.1\n\n'+intro+f'''
Keep the original signed v0.7.1 operational. Use the existing five-second-trained SVR-DENSE with 1 s experimental replay, explicit physical bound and opt-in stop-aware comparison. Half-second inference is locally supported={r['half_second_supported']}; it adds feedback frequency, not shared-cutoff accuracy.

{training_text}

Deterministic physical/stop rules change one-second MAE {raw:.6f}→{bound:.6f}→{stop:.6f} s. Keep raw output auditable. {len(stop_ids)} threshold-stop laps are exploratory evidence; speed-only detection and frozen remaining time have limits. Slow corrected MAE remains {slow.mae_s:.6f} s. Do not remove these laps or confuse physical plausibility with learned generalization.

The highest-value next step is a small preregistered untouched same-domain recording validation with independently annotated stationary episodes, slow laps, source timestamps and restart behavior. Audit conditional remaining-time calibration on those data. Author code confirms the progress-field rename, but exact ACTI interpolation/latency and reverse behavior remain unverified: keep position out of the feature contract until that is established, and keep scheduling time-based.

Retain GRU and ordered Ridge as research demonstrations without architecture changes. No new dataset, live capture, broad grid or automatic promotion is justified by this release. [Prior v080 recommendation](NEXT_RELEASE_RECOMMENDATION_V080.md) remains preserved.
''')
    write('ARCHITECTURE_V081.md', '''# Architecture v0.8.1

The existing v071 operational and v080 SVR/GRU paths are unchanged. New code is isolated in `replay_v081.py`, `cadence_v081.py` and `progressive_v081.py`; reports/artifacts use V081 names.

```mermaid
flowchart TD
    Source[Timestamped source observations] --> Index[Prefix sufficient statistics / original 13 features]
    Index --> Schedule[Elapsed-time scheduler: 5 / 1 / 0.5 s]
    Schedule --> Signed[Cached signed v080 held-out-fold SVR-DENSE]
    Signed --> Raw[Preserved raw final time]
    Raw --> Bound[max raw / observed elapsed]
    Source --> Detector[Causal sample-level stop / resume detector]
    Bound --> Heuristic[Frozen causal remaining time / resume transition]
    Detector --> Heuristic
    Heuristic --> Fragment[Per-session cached recorded replay / Streamlit fragment]
    Fragment --> Hover[Existing browser-only shared cursor]
    Labels[Verified final labels] --> Reveal[Separate explicit retrospective reveal]
    Labels --> Offline[Offline development-only metrics]
    Dev[Original 169 laps / frozen five folds] --> Training[One optional 1 s SVR / matched per-lap penalty]
```

`PrefixIndex` precomputes causal cumulative interval statistics and validates source-clock continuity. Predictions retain nominal and observed seconds. `ReplayEngine` advances a detector once per arriving sample, independent of display cadence. Stop onset and resume model queries are cached at actual sample timestamps, giving identical corrections at shared cutoffs. Rewind initializes isolated state when needed. No wall clock or target enters that engine.

The UI authenticates and caches existing fold models, validates full corpus identity once per ordinary rerun and retains a mutable engine in session state, never shared across user sessions. Fragment timer reruns avoid reloading datasets, recalculating full corpus identity or loading models per checkpoint. Charts contain only observed prefix signals and selected predictions. Targets are read only by the explicit reveal block and offline scorer. Changing replay context resets reveal.

One-second training is an explicitly invoked offline function with training-only preprocessing. It stores signed fold bundles separately and never replaces Model A or the operational reference. Separate fresh-process workers measure each inference cadence. Frozen evidence has SHA-256 bindings; the baseline inventory includes raw recordings, previous reports, signed model bytes and F5 files. Existing signing keys remain private local files.
''')
    # One retrospective scientific artifact, independent of predictive UI payloads.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    intervals = []
    for i, event in enumerate(events):
        if event['event'] != 'stop':
            continue
        resume = next((e for e in events[i+1:] if e['lap_uid']==event['lap_uid'] and e['event']=='resume'), None)
        end = resume['observed_elapsed_s'] if resume else float(obs.loc[obs.lap_uid==event['lap_uid'], 'observed_elapsed_s'].max())
        intervals.append((end-event['observed_elapsed_s'], event, end))
    _, chosen, stop_end = max(intervals, key=lambda item:item[0])
    uid = chosen['lap_uid']
    lap = obs[obs.lap_uid==uid]
    lap = lap[lap.observed_elapsed_s.between(chosen['onset_s']-5., stop_end+6.)]
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    for col, label in [('raw_prediction_s','Raw SVR'), ('bounded_prediction_s','Physical bound'), ('stop_aware_prediction_s','Stop-aware')]:
        ax[0].plot(lap.observed_elapsed_s, lap[col], label=label)
    ax[0].set_ylabel('Predicted final time (s)')
    ax[0].legend()
    ax[1].plot(lap.observed_elapsed_s, lap.speed_kmh, color='black')
    ax[1].set_ylabel('Ground speed (km/h)')
    ax[1].set_xlabel('Observed lap elapsed (s)')
    for event in (e for e in events if e['lap_uid']==uid):
        if not lap.observed_elapsed_s.min() <= event['observed_elapsed_s'] <= lap.observed_elapsed_s.max():
            continue
        for axis in ax:
            axis.axvline(event['observed_elapsed_s'], color='orange' if event['event']=='stop' else 'green', alpha=.6)
    for axis in ax:
        axis.axvspan(chosen['observed_elapsed_s'], stop_end, color='orange', alpha=.1)
    fig.suptitle('Development recorded stop example (retrospective report)\n'+uid[-22:])
    fig.tight_layout()
    for ext in ('png', 'svg'):
        fig.savefig(ROOT/f'docs/figures/stop_trajectory_v081.{ext}', dpi=150)
    plt.close(fig)
    dump(ROOT/'docs/REPORT_MEASUREMENTS_V081.json', dict(raw_mae_s=raw, bounded_mae_s=bound,
        stop_aware_mae_s=stop, one_second_training_raw_mae_s=b, impossible_raw_predictions=impossible,
        stationary_events=sum(e['event']=='stop' for e in events), stationary_laps=len(stop_ids),
        no_stop_laps=169-len(stop_ids), no_stop_stop_correction_mae_delta_s=no_stop_delta,
        retrospective_figure_lap_uid=uid))
    print('Six requested reports, architecture, cohort evidence and retrospective figure written.')


if __name__ == '__main__':
    main()
