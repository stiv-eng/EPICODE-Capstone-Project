"""Build descriptive release reports/figures from frozen evidence; never fit/predict."""
from collections import Counter
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'artifacts/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DOCS=ROOT/'docs'


def read(name):return json.loads((DOCS/name).read_text(encoding='utf-8'))
def csv(name):return pd.read_csv(DOCS/name)
def write(name,body):(DOCS/name).write_text(body.strip()+'\n',encoding='utf-8',newline='\n')


def table(frame,columns,precision=3):
    result=['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    for row in frame.loc[:,columns].itertuples(index=False,name=None):
        result.append('| '+' | '.join(f'{v:.{precision}f}' if isinstance(v,(float,np.floating)) else str(v) for v in row)+' |')
    return '\n'.join(result)


def main():
    audit=read('BARCELONA_AUDIT_V071.json');result=read('ML_RESULTS_V071.json')
    validation=pd.DataFrame(result['validation'])
    predictions=csv('BARCELONA_PREDICTIONS_V071.csv')
    selected=predictions.query("model=='SVR'")
    checkpoint=csv('BARCELONA_BY_CHECKPOINT_V071.csv').query("model=='SVR'")
    diagnostics=csv('BARCELONA_DIAGNOSTICS_V071.csv')
    pace=diagnostics.query("model=='SVR' and dimension=='pace_band'")
    curves=csv('BARCELONA_LEARNING_CURVE_V071.csv')
    baseline=csv('BARCELONA_BASELINE_DETAILS_V071.csv')
    importance=csv('BARCELONA_IMPORTANCE_V071.csv').sort_values('mae_increase_s',ascending=False)
    rejected=[r for r in audit['lap_audit'] if r['status']=='rejected']
    reasons=Counter(reason for r in rejected for reason in r['reasons'].split('; '))
    rejected_recordings=pd.DataFrame([dict(source=r['source'],reason=r['reason']) for r in audit['records'] if r['status']=='rejected'])
    files=read('BARCELONA_MANIFEST_V07.json')['files']
    gate=result['gate']
    split=csv('BARCELONA_SPLIT_V071.csv').groupby('partition').agg(laps=('lap_uid','nunique'),recording_blocks=('physical_session_id','nunique')).reset_index()
    split['snapshots']=split.laps*5
    figures=DOCS/'figures';figures.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout='constrained')
    for partition,group in checkpoint.groupby('partition'):
        axes[0,0].plot(group.checkpoint_s,group.mae_s,'o-',label=partition)
    axes[0,0].set(xlabel='Observed telemetry (s)',ylabel='MAE (s)',title='Selected SVR: checkpoint behavior');axes[0,0].legend()
    test=selected.query("partition=='test'")
    scatter=axes[0,1].scatter(test.target_s,test.prediction_s,c=test.checkpoint_s,cmap='viridis',s=16,alpha=.7)
    axes[0,1].plot([95,220],[95,220],'k--',lw=1)
    axes[0,1].set(xlabel='Verified target (s)',ylabel='Prediction (s)',title='Frozen test: 36 laps / 180 correlated prefixes')
    fig.colorbar(scatter,ax=axes[0,1],label='Checkpoint (s)')
    for name,group in curves.query("partition=='validation'").groupby('model'):
        axes[1,0].plot(group.training_laps,group.mae_s,'o-',label=name)
    axes[1,0].set(xlabel='Nested training laps (whole recording blocks)',ylabel='Validation MAE (s)',title='Fixed validation; no test selection');axes[1,0].legend()
    for partition,group in selected.groupby('partition'):
        axes[1,1].hist(group.error_s,bins=np.arange(-100,61,10),alpha=.5,label=partition)
    axes[1,1].set(xlabel='Prediction minus target (s)',ylabel='Correlated prefixes',title='Large slow-tail underprediction retained');axes[1,1].legend()
    fig.savefig(figures/'barcelona_health_v071.png',dpi=160);fig.savefig(figures/'barcelona_health_v071.svg');plt.close(fig)
    svg=figures/'barcelona_health_v071.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',
                   encoding='utf-8',newline='\n')
    write('BARCELONA_DATASET_AUDIT_V071.md',f'''
# Barcelona dataset recovery v0.7.1

All **205 technically valid complete laps** are eligible. The 116 laps previously
excluded solely for uncertain participant/capture metadata or date conflicts are
recovered, plus one objectively supported timer-rounding case. No valid lap was
removed for being slow, atypical or difficult to predict.

## Source, integrity and scope

The preserved acquisition contains **70 LD recordings, 70 paired LDX files and
11 laps_info CSV files**, totaling **{sum(e['bytes'] for e in files):,} bytes** in
17 author folders. No additional download was needed in v0.7.1. All LD/LDX hashes
are rechecked against [the pinned manifest](BARCELONA_MANIFEST_V07.json), revision
`{audit['revision']}`. Human provenance follows the author's pinned catalogue;
SAC/MPC/AI policies, pickle payloads and other car/track domains are excluded.
Attribution: Remonda et al., *A Simulation Benchmark for Autonomous Racing with
Large-Scale Human Data*, NeurIPS 2024 / AssettoCorsaGym / dasGringuen. Source-declared
license: CC BY 4.0; the original files stay unchanged and ignored by Git.

The publication's 247 laps / 70 stints / 612,557 human steps are source-level
counts, not an assertion that 247 independently verified complete targets can be
reconstructed from these exports. Our measured counts are:

| Measure | v0.7 | v0.7.1 |
|---|---:|---:|
| Downloaded recordings | 70 | 70 |
| Recordings imported for validated targets | 62 | 62 |
| Complete cross-checked targets | 204 | 205 |
| Eligible complete laps | 88 | 205 |
| Validated laps excluded only for metadata | 116 | 0 |
| Remaining rejected candidate spans in imported recordings | 82 | 81 |
| Exact raw/lap duplicates found | 0 / 0 | 0 / 0 |

117 admitted laps retain metadata uncertainty flags, including the additional WL
lap. A, XX and WL are included; unknown codes are not invented driver identities.
Core speed/pedals/RPM coverage is **100%** for every admitted lap. Every lap supports
all five causal checkpoints: **1,025 snapshots**. Optional steering/gear absence
is supported by existing training-only imputation, rather than requiring every
telemetry channel. All currently admitted exports supply those channels.

## Objective extra recovery and retained target checks

WL `20240325_WL/...stint_2.ld`, source lap 12: source final timer **98.8475 s**,
witnessed next-counter Last Lap Time **98.847 s**, export-grid duration **98.860 s**.
The old nonnegative final-timer difference rejected 0.5 ms of field rounding.
v0.7.1 allows at most **1 ms** negative difference, with all other checks intact:
consecutive witnessed counter, valid next-packet target, increasing lap timer,
<=200 ms timer steps, initial timer <=50 ms, LDX start/end and export/target
agreement <=50 ms, countdown agreement, source invalidation and progress coverage.
The historical Monza default remains zero negative tolerance. An unwitnessed
tail, absent beacon or contradictory target is never reconstructed as a lap.

## Every remaining unusable source/span

Eight recordings lack usable increasing paired beacon evidence:

{table(rejected_recordings,['source','reason'])}

Their unverified internal spans are not added to the denominator of 81 rejected
candidates from the 62 timing-importable recordings. NiM has a 965-byte LDX with
Details and no Beacons, TotalLaps=1 while LD counters run 15..22; metadata leniency
cannot supply a missing independent boundary. Such recordings remain available
for signal exploration through the analysis-only adapter.

Reasons across the 81 rejected candidate spans overlap:

{table(pd.DataFrame([dict(reason=k,spans=v) for k,v in reasons.items()]),['reason','spans'])}

[BARCELONA_LAPS_V071.csv](BARCELONA_LAPS_V071.csv) records every accepted/rejected
candidate with source, source lap/start sample and all reasons. The
[recording ledger](BARCELONA_RECORDINGS_V071.csv) covers all 70 recordings.
No remaining candidate fails only a participant/date criterion.

## Actual duplicate checks and split assumptions

Raw SHA-256 detects exact repeated captures. A second hash covers every canonical
feature-safe lap sample and verified target, excluding source identity from the
hash. It found **0 exact lap duplicates**. Matching 1-second rounded trajectory
signatures with consistent targets would link recording groups while retaining
nonidentical laps; **0 such cross-capture links** were found. These checks do not
prove every near-duplicate or unknown session link absent.

Explicit recording-folder stints stay together. XX is a mixed-date collection;
each actual LD capture forms a block, with no assumed common participant. A-series
folders remain distinct recording blocks, without claimed physical independence.
Same/missing driver labels alone never merge groups. The resulting **51 blocks**
are export/recording units, not 51 certified independent physical sessions.

Seed-42 permutation of sorted blocks freezes approximately 60/20/20 membership
before fitting or filtering. Unequal block sizes give:

{table(split,['partition','recording_blocks','laps','snapshots'])}

All prefixes and laps of a block remain together. See exact
[memberships](BARCELONA_SPLIT_V071.csv), [freeze](BARCELONA_SPLIT_V071.json) and
[preregistered protocol](BARCELONA_PROTOCOL_V071.json). Unknown capture links,
recurring participants and inconsistent absolute chronology limit independence.
This is an **offline retrospective recording-block holdout**, not evidence of
unseen-session, unseen-driver or prospective chronological generalization.

Corpus identity: `{audit['corpus_id']}`. The v0.7 audit/protocol and downloaded raw
files remain preserved; only dedicated V071 evidence is produced.
''')
    write('ML_EVALUATION_V071.md',f'''
# Barcelona ML evaluation v0.7.1

**SVR was selected on validation MAE and evaluated once on the frozen test.**
Experiment A uses every technically valid training lap: 103 train, 66 validation,
36 test, five checkpoints per lap. No Monza/GT7 rows enter this experiment.

## Fixed implementation and decision order

The existing 13 causal features and 10/20/30/45/60 s checkpoints are unchanged.
Ridge alpha=10; Random Forest 120 trees/depth 6/minimum leaf 2/seed 42/one worker;
RBF SVR C=10/epsilon=0.5/default scale gamma. Imputation medians and Ridge/SVR
scalers fit TRAIN only. All models remain fitted on training; no final refit on
validation/test. Feature prefixes never receive targets, final distance, whole-lap
KPIs, future signals, participant names or source IDs as predictors.

The split is saved before fitting. Validation ranks MAE, RMSE, absolute bias,
then model name. The chosen experiment/model and validation evidence are saved
before the single final-test prediction. Ridge/RF have **validation results only**.
The selected SVR has validation and test results; test did not select it.

Experiment B was preregistered only for valid laps with measured positive timer
steps >100 ms, within the accepted 200 ms limit. **No training lap met that
category**, so no filtering comparison was invented and no valid lap excluded.
The implemented optional comparison uses identical inclusive validation/test,
requiring >=0.5 s and >=5% improvement on >=2 models, improved recording-macro
error and no >0.5 s slow-band degradation, followed by deterministic repetition.
See [filter decision](BARCELONA_FILTER_DECISION_V071.json).

## Measured validation (66 laps / 330 correlated prefixes / 10 blocks)

Errors are prediction minus verified target, seconds.

{table(validation,['model','mae_s','rmse_s','bias_s','median_absolute_error_s','p90_absolute_error_s','max_absolute_error_s','recording_macro_mae_s'])}

## Selected SVR frozen test (36 laps / 180 correlated prefixes / 11 blocks)

{table(pd.DataFrame([result['selected_test']]),['mae_s','rmse_s','bias_s','median_absolute_error_s','p90_absolute_error_s','max_absolute_error_s','recording_macro_mae_s'])}

Recording mean absolute errors range **5.047–31.637 s** on test. The pooled score
weights laps equally (each has five prefixes); recording-macro MAE weights blocks
equally. Unknown links limit independent-group interpretation. These are
descriptive results without prefix-based confidence intervals or significance claims.

## Deterministic baselines and matched coverage

Historical median is **122.164 s**, computed from unique training targets and fixed
before held-out evaluation. It is an offline pretraining reference; no absolute
acquisition chronology or online availability is claimed. Held-out targets never
update history. Previous-lap requires an earlier witnessed training lap in the
same capture, or a uniquely supported earlier training capture/date. Ambiguous
same-day capture order/date-conflict sources produce an unavailable previous-lap
reference, without borrowing validation/test labels.

{table(baseline.query("model=='SVR'"),['partition','baseline','coverage','laps','mae_s','rmse_s','bias_s','median_absolute_error_s','p90_absolute_error_s'])}

On all 36 test laps SVR improves median-reference MAE by **2.508 s (14.0%)**.
Previous-lap is available for 24/36 test laps: its MAE is **21.179 s**, versus
**16.486 s** for SVR on exactly those laps (gain 4.693 s). The 15.393 s overall SVR
score is a different population and must not replace the matched 16.486 s score.
Validation previous-reference coverage is 34/66 laps. See complete
[matched comparisons](BARCELONA_BASELINES_V071.csv).

## Checkpoints and legitimate pace tails

{table(checkpoint,['partition','checkpoint_s','mae_s','rmse_s','bias_s'])}

Test MAE declines 18.717 -> 13.670 s from 10 to 60 s; validation improves overall
17.363 -> 7.405 s, with a 45-to-60 s deterioration (6.701 -> 7.405). More telemetry
helps on aggregate but does not guarantee monotonically better individual estimates.

Pace bands use unique TRAIN Q25 **109.734 s** and Q75 **140.043 s**, frozen before
test. Fast <Q25, slow >Q75, remaining laps middle; none is removed.

{table(pace,['partition','value','laps','mae_s','bias_s','prediction_mean_s'])}

## Model health and learning curve

1. **Baseline improvement exists**, but test error/tails remain large. SVR test
   MAE 15.393 s, RMSE 22.396 s and P90 36.705 s are insufficient for a precision
   race-engineering prediction claim.
2. **Central shrinkage persists.** At test 10 s prediction SD is 5.286 s versus
   target SD 24.866 s, centered at 120.857 s near the training median. At 60 s
   prediction SD expands to 13.103 s, still far below the target SD. Pooled test
   prediction range is 104.745–170.711 s despite targets reaching 212.650 s.
3. **Pace discrimination is partial.** Test fast/middle/slow mean predictions are
   116.264/124.818/133.241 s. Slow laps have MAE 31.213 s and bias -30.167 s;
   fast-lap bias is +9.633 s. Similar slow underprediction exists on validation.
4. **More same-domain training data helps overall validation**, for this nested
   seed-42 block curve. It does not uniformly help the slow tail, and a single
   ordering cannot separate sample-size effects from composition differences.

{table(curves.query("partition=='validation'"),['model','training_groups','training_laps','mae_s','recording_macro_mae_s','slow_lap_mae_s'])}

SVR validation MAE improves **10.993 -> 10.600 -> 9.868 s** for 49/66/103 train laps;
its slow-band MAE worsens **23.150 -> 23.497 -> 25.723 s**. Full-population train
MAE is 13.625 s (SVR), 9.755 s (RF), 16.625 s (Ridge). SVR's lower validation
than training error is consistent with differing pace/population composition;
it is not evidence that a train-only preprocessing check can be skipped.

5. **Large errors retain meaningful telemetry cases.** The largest test error
   (-88.939 s at 10 s) is capture `d83f92f1...`, source lap 1, target 212.650 s.
   Its first 10 s average 219.372 km/h, near-full throttle and no braking; at 60 s
   observed mean speed is 139.336 km/h and prediction remains 137.370 s.
   Aggregate prefixes lose phase/event ordering and cannot observe later incidents.
   This pattern is descriptive, not a confirmed cause or a license to remove it.
6. **The 13 features are a useful baseline but remain limiting.** Validation-only
   permutation importance ranks mean speed (+4.198 s MAE), mean throttle (+3.693 s)
   and high-throttle fraction (+2.351 s) highest. Features are correlated and five
   prefixes per lap are correlated; these are not causal effects. No feature
   selection was performed using these diagnostics.
7. **Next step: bounded causal feature engineering**, preserving this reference.
   Compare past-window speed/input/event summaries and verified source progress
   with validated semantics, without eventual-distance normalization. Evaluate
   checkpoint/slow-tail tradeoffs on development data and reserve a new final
   holdout for any changed model. Switching to deep learning is not supported
   merely by the current residuals.

![Frozen checkpoint, calibration, learning-curve and error diagnostics](figures/barcelona_health_v071.png)

[SVG export](figures/barcelona_health_v071.svg). All figures read already frozen
prediction tables; report generation does not run model inference. Full lap/block
metrics and median/P90/max errors are in [diagnostics](BARCELONA_DIAGNOSTICS_V071.csv),
[lap summaries](BARCELONA_BY_LAP_V071.csv), [recording summaries](BARCELONA_BY_SESSION_V071.csv)
and [individual causal rows](BARCELONA_PREDICTIONS_V071.csv).

## Reproduction and retained test

`python -m scripts.run_barcelona_v071` runs offline after explicit acquisition.
The initial local experiment has **test_evaluations=1**. Subsequent commands and
the dashboard verify frozen evidence hashes and reuse results; they do not choose
another model or re-evaluate the final batch. A missing local model can be rebuilt
using TRAIN only while retaining frozen evaluation CSVs. An interrupted test access
without completed results fails closed instead of silently consuming test again.
Artifacts live in ignored `artifacts/barcelona_v071/models`, signed by the existing
local SHA/HMAC store before deserialization, with car/track, schema, units, feature,
model/protocol and corpus identity checks. No historical model is overwritten.

The UI loads compatible local artifacts without fitting. Its explicit training
button creates the experiment on a fresh installation or reuses the frozen local
run. Progressive Prediction uses only observed prefixes and the selected model;
verified target/error appear only after retrospective reveal and never enter the
chart/hover payload. Interactive replay is separate from batch test evaluation.
''')
    write('ML_COMPARISON_V071.md','''
# ML release comparison v0.7.1

Barcelona now supplies a functioning inclusive experiment. The prior v0.7 had
88 eligible laps and failed its 12-group gate: **zero Barcelona models, zero test
evaluations and no measured Barcelona MAE**. Its stopped result must not be
presented as a numerical comparator.

| Experiment | Domain | Usable laps | Train / validation / test | Selected SVR test MAE | Median baseline MAE |
|---|---|---:|---|---:|---:|
| Historical v0.6 | Monza / Dallara F317 | 55 | 29 / 11 / 15 | 6.743 s | 9.443 s |
| v0.7 checkpoint | Barcelona / Dallara F317 | 88 | Not constructed | Not evaluated | Not evaluated |
| v0.7.1 A | Barcelona / Dallara F317 | 205 | 103 / 66 / 36 | 15.393 s | 17.901 s |

These are **different domains, target distributions, recording populations and
split/baseline assumptions**. Barcelona's larger MAE cannot be attributed to more
or fewer data by comparing it with Monza. No Monza/GT7 observation or fitted
preprocessing enters Barcelona. Historical v0.6 uses identified chronological
groups and past-only history; v0.7.1 uses retrospective recording blocks and a
fixed offline training median, with a separately restricted previous-lap reference.

The defensible same-domain size comparison is v0.7.1's nested TRAIN-only learning
curve with unchanged inclusive validation. SVR MAE improves 10.993 -> 10.600 ->
9.868 s for 49/66/103 training laps; RF 13.279 -> 12.563 -> 10.819; Ridge 14.741 ->
14.005 -> 12.441. Different nested block composition still limits causal attribution.
SVR slow-band error worsens, so more laps are useful without solving the tail.

No A/B filtering score exists: the preregistered timing-quality category contains
zero training laps. A remains inclusive; there is no unsupported claim that a
cleaner subset improves learning. Ridge/RF final test scores are deliberately
absent; only validation-selected SVR saw the frozen Barcelona final test.

The original Monza and GT7 source/results/model stores remain recoverable. Their
390 + 60 frozen prediction rows were verified within 1e-9 s (observed maximum
prediction deviation 2.842e-14 s). GT7 remains the historical eight-lap,
single-recording experimental case. See [historical evaluation](ML_EVALUATION_V06.md),
[new evaluation](ML_EVALUATION_V071.md) and [release evidence](RELEASE_V071_REPORT.md).
''')
    write('NEXT_RELEASE_RECOMMENDATION.md','''
# Recommendation after v0.7.1

**Keep the inclusive Barcelona A experiment as the measured reference and
prioritize causal feature engineering.** The recovered data supports actual
training; imperfect participant/date metadata is no longer a blocking condition.
SVR beats the offline median on validation (9.868 vs 20.414 s) and the frozen test
(15.393 vs 17.901 s), but slow-test MAE 31.213 s, bias -30.167 s and P90 overall
36.705 s show that the present features do not cover the full legitimate pace range.

1. Preserve all usable data and the current signed model/results. Compare a small
   preregistered set of causal recent-window speed/pedal, observed stopping/recovery
   and phase/event summaries against the same 13-feature baseline. Verify any
   source progress semantics; never normalize by eventual distance or final target.
   Keep training-only preprocessing and fixed inclusive development populations.
2. Report checkpoint, recording-macro and slow/fast errors alongside pooled MAE.
   Later prefixes help, but validation 60 s is worse than 45 s. The nested size
   curve improves overall SVR MAE by 1.125 s while worsening slow-tail MAE by
   2.573 s; do not optimize away difficult valid laps or claim size alone explains it.
3. A bounded classical alternative may follow a feature comparison, with few
   prespecified configurations. Current Ridge/RF/SVR results do not establish that
   algorithm replacement alone fixes lost temporal information or future incidents.
4. Additional same-domain recording diversity and better source timing/session
   documentation would strengthen evidence. This is useful follow-up, not a new
   eligibility gate. Retain anonymous/date-conflict laps when technically sound.
   Native capture/resampling latency remains unproven by 50/100 Hz export grids.
5. A limited Keras experiment is a later optional research step, after defining
   a causal sequence representation and meaningful classical references. With
   103 training laps and unknown cross-capture links, the current scores provide
   no measured reason to prioritize deep learning now. No DL was added in v0.7.1.

The Barcelona test has already been evaluated and inspected. Use validation or
development-only cross-validation for changes, then reserve a **new untouched
holdout** before claiming a new final result. Do not reuse the present final test
to pick features, filter laps, tune models or reverse the validation selection.
No arbitrary number of drivers or independent groups should prevent useful
development; document actual split strength and uncertainty instead.

Keep the v0.6.3 shared hover/cursor design. Follow-up browser coverage can include
Firefox/Safari, physical touch devices and longer laptop memory sessions; current
Chrome evidence covers actual pointer/keyboard, zoom/pan, responsive widths and
offline chart payloads. Unknown cross-recording links mean the new holdout does
not establish unseen-session/driver or prospective generalization.

See [dataset audit](BARCELONA_DATASET_AUDIT_V071.md),
[measured ML health](ML_EVALUATION_V071.md) and [comparison](ML_COMPARISON_V071.md).
This recommendation does not authorize further acquisition, publication or Git
push/merge, and imposes no new gate on the delivered functioning experiment.
''')
    print('Generated dataset, evaluation, comparison, recommendation and PNG/SVG from frozen evidence.')


if __name__=='__main__':main()
