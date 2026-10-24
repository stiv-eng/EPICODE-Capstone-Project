"""Static diagnostic reports from frozen tables; no fitting or inference."""
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
COLORS={'F0':'#202b3c','F1':'#2674b9','F2':'#25834a','F3':'#dc7c15','F0W':'#9654a7'}
PARTITIONS=('train','validation','test')
PART_LABELS=('Training','Validation','Historical test (already observed)')


def csv(name):return pd.read_csv(DOCS/name)
def read(name):return json.loads((DOCS/name).read_text(encoding='utf-8'))
def write(name,text):(DOCS/name).write_text(text.strip()+'\n',encoding='utf-8',newline='\n')


def table(frame,columns,precision=3):
    rows=['| '+' | '.join(columns)+' |','|'+'|'.join(['---']*len(columns))+'|']
    for values in frame.loc[:,columns].itertuples(index=False,name=None):
        rows.append('| '+' | '.join(f'{x:.{precision}f}' if isinstance(x,(float,np.floating)) else str(x) for x in values)+' |')
    return '\n'.join(rows)


def save(fig,name):
    dest=DOCS/'figures';dest.mkdir(exist_ok=True)
    fig.savefig(dest/(name+'.png'),dpi=150)
    svg=dest/(name+'.svg');fig.savefig(svg)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
    plt.close(fig)


def figures():
    laps=csv('PACE_LAPS_V072.csv');counts=csv('PACE_COUNTS_V072.csv')
    fig,axes=plt.subplots(3,2,figsize=(13,14),layout='constrained')
    data=[laps.query('partition==@p').target_s for p in PARTITIONS]
    for values,label in zip(data,PART_LABELS):axes[0,0].hist(values,bins=np.arange(90,271,10),density=True,alpha=.45,label=label)
    axes[0,0].set(title='Unique complete-lap distributions',xlabel='Verified lap time (s)',ylabel='Density');axes[0,0].legend(fontsize=8)
    axes[0,1].boxplot(data,tick_labels=PART_LABELS,showmeans=True)
    axes[0,1].set(title='Lap-time spread (no prefix duplication)',ylabel='Lap time (s)');axes[0,1].tick_params(axis='x',labelsize=8)
    for i,band in enumerate(('fast','middle','slow')):
        values=counts.query('pace_band==@band').set_index('partition').reindex(PARTITIONS)
        axes[1,0].bar(np.arange(3)+(i-1)*.25,values.laps,width=.25,label=band)
        base=counts.loc[counts.pace_band.isin(('fast','middle','slow')[:i])].groupby('partition').proportion.sum().reindex(PARTITIONS,fill_value=0)
        axes[1,1].bar(np.arange(3),values.proportion,bottom=base,label=band)
    for ax in axes[1]:ax.set_xticks(np.arange(3),PART_LABELS,fontsize=8);ax.legend()
    axes[1,0].set(title='Pace counts: original TRAIN quartiles',ylabel='Unique laps')
    axes[1,1].set(title='Pace proportions',ylabel='Fraction of laps',ylim=(0,1))
    order=csv('PACE_BLOCKS_V072.csv').sort_values(['partition','mean_s']).physical_session_id.tolist()
    index={g:i+1 for i,g in enumerate(order)}
    for partition,label in zip(PARTITIONS,PART_LABELS):
        g=laps.query('partition==@partition')
        axes[2,0].scatter(g.physical_session_id.map(index),g.target_s,s=15,alpha=.65,label=label)
        axes[2,1].plot([10,25,50,75,90],g.target_s.quantile([.1,.25,.5,.75,.9]),'o-',label=label)
    axes[2,0].set(title='Laps by recording block',xlabel='Block index (identities in PACE_BLOCKS CSV)',ylabel='Lap time (s)');axes[2,0].legend(fontsize=8)
    axes[2,1].set(title='Quantile comparison',xlabel='Quantile (%)',ylabel='Lap time (s)');axes[2,1].legend(fontsize=8)
    save(fig,'pace_distribution_v072')
    ref=csv('REFERENCE_FROZEN_PREDICTIONS_V072.csv');cal=csv('REFERENCE_CALIBRATION_V072.csv')
    fig,axes=plt.subplots(3,2,figsize=(13,13),layout='constrained')
    for col,(partition,label) in enumerate([('validation','Original validation'),('test','Historical test (already observed)')]):
        g=ref.query('partition==@partition')
        axes[0,col].scatter(g.target_s,g.prediction_s,c=g.checkpoint_s,cmap='viridis',s=14,alpha=.6)
        axes[0,col].plot([95,220],[95,220],'k--',lw=1)
        axes[0,col].set(title=label+' · frozen SVR',xlabel='Actual (s)',ylabel='Prediction (s)')
        axes[1,col].scatter(g.target_s,g.error_s,c=g.checkpoint_s,cmap='viridis',s=14,alpha=.6)
        axes[1,col].axhline(0,color='black',lw=1)
        axes[1,col].set(title=label+' · residuals',xlabel='Actual (s)',ylabel='Prediction minus actual (s)')
        q=cal.query('partition==@partition')
        axes[2,0].plot(q.checkpoint_s,q.predicted_on_actual_slope,'o-',label=label)
        axes[2,1].plot(q.checkpoint_s,q.prediction_to_target_std,'o-',label=label)
    for ax in axes[2]:ax.axhline(1,color='black',ls='--',lw=1);ax.legend(fontsize=8);ax.set_xlabel('Checkpoint (s)')
    axes[2,0].set(title='Predicted-on-actual calibration slope',ylabel='OLS slope')
    axes[2,1].set(title='Prediction / target variability',ylabel='Sample SD ratio')
    save(fig,'reference_calibration_v072')
    overall=csv('DEVELOPMENT_OVERALL_V072.csv');folds=csv('DEVELOPMENT_FOLD_METRICS_V072.csv');details=csv('DEVELOPMENT_DETAILS_V072.csv')
    fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    names=list(COLORS)
    axes[0,0].boxplot([folds.query('variant==@v').mae_s for v in names],tick_labels=names,showmeans=True)
    axes[0,0].set(title='Five development folds (overlapping training)',ylabel='MAE (s)')
    for variant in names:
        g=details.query("variant==@variant and dimension=='checkpoint_s'").copy();g['cp']=pd.to_numeric(g.value);g=g.sort_values('cp')
        axes[0,1].plot(g.cp,g.mae_s,'o-',label=variant,color=COLORS[variant])
    axes[0,1].set(title='OOF checkpoint behavior · same 169 laps',xlabel='Observed checkpoint (s)',ylabel='MAE (s)');axes[0,1].legend()
    axes[1,0].bar(overall.variant,overall.recording_macro_mae_s,color=overall.variant.map(COLORS))
    axes[1,0].set(title='Recording-macro error: no accepted improvement',ylabel='MAE (s)')
    slow=details.query("dimension=='pace_band' and value=='slow'").set_index('variant').reindex(names)
    axes[1,1].bar(np.arange(5)-.18,slow.mae_s,width=.36,label='Slow MAE')
    axes[1,1].bar(np.arange(5)+.18,slow.bias_s.abs(),width=.36,label='Absolute slow bias')
    axes[1,1].set_xticks(np.arange(5),names);axes[1,1].set(title='Slow-tail changes remain limited',ylabel='Error (s)');axes[1,1].legend()
    save(fig,'feature_experiments_v072')
    examples=csv('DEVELOPMENT_EXAMPLES_V072.csv')
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for ax,(uid,g) in zip(axes.flat,examples.groupby('lap_uid',sort=False)):
        for variant,rows in g.groupby('variant'):
            ax.plot(rows.checkpoint_s,rows.prediction_s,'o-',label=variant,color=COLORS[variant])
        target=float(g.target_s.iloc[0]);ax.axhline(target,color='black',ls='--',label=f'Actual {target:.3f} s')
        ax.set(title=str(g.example.iloc[0])+' · '+uid[:8],xlabel='Observed checkpoint (s)',ylabel='Final lap prediction (s)');ax.legend(fontsize=8)
    save(fig,'development_examples_v072')
    correlation=csv('FEATURE_PEARSON_V072.csv').set_index('feature')
    fig,ax=plt.subplots(figsize=(13,10),layout='constrained')
    plot=ax.imshow(correlation,vmin=-1,vmax=1,cmap='coolwarm')
    ax.set_xticks(np.arange(len(correlation)),correlation.columns,rotation=70,ha='right',fontsize=8)
    ax.set_yticks(np.arange(len(correlation)),correlation.index,fontsize=8)
    ax.set_title('Original features · development Pearson correlation (correlated prefixes)')
    fig.colorbar(plot,ax=ax,label='Descriptive Pearson r');save(fig,'feature_redundancy_v072')


ORIGINAL_FEATURES='''
| Feature | Physical interpretation / units | Source and calculation at checkpoint | Target relation, redundancy and information loss |
|---|---|---|---|
| checkpoint_s | Requested observed horizon, s | Fixed 10/20/30/45/60 s | Same five horizons for every lap; context for interactions, not a standalone pace label; nearly duplicates observed elapsed |
| observed_elapsed_s | Last available source lap timer, s | Final timestamp in permitted causal prefix | Close to checkpoint with source-grid offset; no final time; near duplicate can emphasize time in kernel geometry |
| speed_current_kmh | Current ground speed, km/h | Last valid observed Ground Speed | Instantaneous phase/pace cue; cannot describe prior braking or later incidents; correlated with RPM/gear |
| speed_mean_kmh | Mean observed speed, km/h | Forward time-weighted left-hold mean from lap start; terminal sample has zero duration | Strong pace cue, averages away order and phase; partly redundant with distance/time and recent speed |
| speed_recent_mean_kmh | Recent speed, km/h | Same weighting over trailing 3 s ending at last observed timestamp | Local phase cue; loses within-window order; correlated with current and global speed |
| speed_recent_std_kmh | Recent speed variability, km/h | Weighted population SD in same trailing 3 s | Slowing/acceleration magnitude without direction; two reversed histories may match |
| throttle_mean_pct | Observed throttle utilization, % | Time-weighted Throttle Pos over prefix | Control/pace cue but loses burst ordering and subsequent recovery; correlated with high-throttle fraction |
| brake_mean_pct | Observed brake intensity, % | Time-weighted Brake Pos over prefix | Combines braking strength and duration; cannot distinguish number/order of phases; correlated with brake-on fraction |
| throttle_high_fraction | High-throttle time, fraction | Weighted fraction Throttle Pos >=90% | Describes already observed commitment; threshold compresses pedal magnitude/order; overlaps mean throttle |
| braking_fraction | Brake-on time, fraction | Weighted fraction Brake Pos >=5% | Preserves total brake-on support, not events or timing; overlaps mean brake |
| rpm_current | Current engine speed, rpm | Last observed Engine RPM | Speed/gear/driver cue; cannot describe earlier shift history or later driving |
| gear_current | Current reported gear, source category | Last observed Gear, no invented gear remapping | Discrete speed/phase cue, overlaps RPM/speed; optional missing values use fold-training imputation |
| steering_activity_deg_s | Recent steering activity, deg/s | Sum of absolute Steering Angle changes / positive duration over trailing 3 s, only with declared degrees | Turn/input cue without direction/order; export noise can matter; optional absence stays missing |
'''


def main():
    figures()
    distribution=csv('PACE_DISTRIBUTIONS_V072.csv');counts=csv('PACE_COUNTS_V072.csv');laps=csv('PACE_LAPS_V072.csv')
    reference_cal=csv('REFERENCE_CALIBRATION_V072.csv');composition=read('PACE_COMPOSITION_V072.json')
    overall=csv('DEVELOPMENT_OVERALL_V072.csv');details=csv('DEVELOPMENT_DETAILS_V072.csv');folds=csv('DEVELOPMENT_FOLD_METRICS_V072.csv')
    selection=read('DEVELOPMENT_SELECTION_V072.json');phase=read('DIAGNOSIS_PHASE_A_V072.json')
    q25,q75=phase['common_pace_quartiles_s']
    summary=folds.groupby('variant',as_index=False).mae_s.agg(['mean','std','min','max']).reset_index()
    participant_rows=pd.DataFrame([dict(partition=p,codes=', '.join(sorted(g.driver_id.unique())),
        uncertain_laps=int(g.metadata_uncertainty.fillna('').ne('').sum())) for p,g in laps.groupby('partition')])
    write('PACE_DISTRIBUTION_AUDIT_V072.md',f'''
# Pace distribution and reference diagnosis v0.7.2

The model is exposed to slow laps: **26/103 training laps (25.24%)**, across seven
recording blocks, exceed the original training Q75. Training includes the slowest
valid lap, 259.595 s, compared with historical-test maximum 212.650 s. Lack of
any slow training examples or an insufficient target range is not supported.
Representation within individual driving/recording conditions remains limited.

## Unique-lap distributions and metadata

Counts are complete **unique laps**, not five correlated prefixes per lap.
Exact frozen memberships and verified source targets are reloaded rather than
using rounded narrative values. Recomputed common thresholds are Q25
**{q25!r} s**, Q75 **{q75!r} s**, matching v0.7.1 within 1e-10 s.
Fast is strictly below Q25, slow strictly above Q75; the boundary values are middle.

{table(distribution,['partition','laps','recording_blocks','mean_s','median_s','std_s','min_s','max_s','q10_s','q25_s','q50_s','q75_s','q90_s'])}

`test` in every table means **historical test, already observed**. It is never a
new independent test in v0.7.2.

{table(counts,['partition','pace_band','laps','proportion','recording_blocks'])}

Training: 26 fast / 51 middle / 26 slow. Validation: **36 / 18 / 12**, verified.
Historical test: **5 / 20 / 11**, verified. Validation is 54.55% fast, versus
13.89% on historical test; slow proportions are 18.18% versus 30.56%.
Source codes and uncertainties are:

{table(participant_rows,['partition','codes','uncertain_laps'])}

Codes A/XX and date conflicts do not become invented people. Stints in explicit
recording folders stay together; XX captures use their actual export blocks.
The 51 total blocks are not 51 certified independent physical sessions.
[Per-block lap ranges](PACE_BLOCKS_V072.csv), [lap-level membership](PACE_LAPS_V072.csv)
and original-source flags preserve what is known. No usable lap is deleted.

![Histograms, boxes, quantiles, bands and recording-level target spread](figures/pace_distribution_v072.png)

## Does distribution composition plausibly contribute to the error gap?

Yes, descriptively. Frozen validation MAE is **{composition['validation_mae_s']:.3f} s**,
historical test MAE **{composition['historical_test_mae_s']:.3f} s**. Applying frozen
validation *band-specific errors* to the historical test's observed band proportions
gives **{composition['validation_band_errors_at_historical_test_mix_s']:.3f} s**.
That descriptive composition difference is **{composition['composition_difference_s']:.3f} s**;
**{composition['remaining_within_band_difference_s']:.3f} s** remains from differing
within-band outcomes. This assumes unchanged conditional errors, which the actual
data does not establish; it is **not a causal decomposition**, a corrected test
score, training weights or evidence that rebalancing fixes the model. The small
numbers of slow-lap blocks and uncertain cross-capture links limit attribution.

## Is the reference implementation defective or using the baseline as its target?

No structural target/baseline defect was found. The existing pipeline fits
`model.fit(X[13 causal columns], target_s)` and returns direct final seconds.
There is no median subtraction/addition or baseline column in X. Historical median
is a separate frozen TRAIN reference, **122.164 s**, computed from unique permitted
training targets. Previous-lap history has separate chronological/capture guards.
The signed artifact and all 1,170 stored v0.7.1 evaluation rows are preserved.

Telemetry matters: a controlled +/-10 km/h change to already observed speed in
three deterministic development laps changes predictions. For the median-pace
development example at 60 s, predictions are **120.131 / 116.833 / 114.045 s** for
-10 / unchanged / +10 km/h. This is input sensitivity, not a physical intervention
or new validation score. Frozen validation SVR MAE 9.868 s already beats its
20.414 s median reference; the new group-CV comparison separately verifies utility.

## Central shrinkage and checkpoint spread

OLS slopes regress **prediction on actual target**, so a slope below one indicates
compressed responses; this is not the inverse calibration regression.

{table(reference_cal,['partition','checkpoint_s','prediction_mean_s','target_std_s','prediction_std_s','prediction_to_target_std','predicted_on_actual_slope'])}

At 10 s predictions cluster near 121 s, with SD around 5.3–5.5 s. At historical
test 60 s the SD ratio is 0.527 and slope 0.333; original validation reaches
0.789 and 0.693. Increasing spread is useful only when accompanied by lower error
and better calibration, not merely less constant outputs.

![Frozen reference calibration and residuals; test clearly historical](figures/reference_calibration_v072.png)

These patterns support central regression with limited predictive information,
fixed SVR regularization/kernel geometry, recording shift and unobserved future
events as plausible contributors. They do not identify a single cause. Slow-lap
underprediction exists in development too; historical-test distribution alone
cannot explain it. No experimental model is scored on the historical test.
''')
    new_definitions='''
| Family / features | Definition and units | Causal boundary / limitations |
|---|---|---|
| F1 speed_mean_5s_kmh, speed_std_5s_kmh | Weighted mean / population SD of trailing ground speed, km/h | Actual left-hold intervals clipped to [checkpoint-5,last observation]; no centered window |
| F1 speed_delta_5s_kmh | Current minus last-known speed at window start, km/h | Backward lookup, no future interpolation; order-sensitive net change |
| F1 deceleration_mean_5s_mps2, deceleration_max_5s_mps2 | Positive part of -(v[i+1]-v[i])/(3.6*actual_dt), weighted mean / maximum in window | Both timestamps already observed; dt>0; estimated export derivative, not a calibrated accelerometer |
| F1 braking_fraction_5s, throttle_mean_5s_pct | Weighted fraction brake>=5%, and mean throttle % | Supported trailing intervals only; terminal sample has no invented duration |
| F2 braking_phases_count | Number of observed brake>=5% runs with >=0.2 s already witnessed | Ongoing run counts only after observed duration qualifies; no future completion confirmation |
| F2 low_speed_observed_s, severe_slow_observed_s | Observed supported seconds below 80 / 40 km/h | Fixed physical low/severe-slow descriptors; no lap removed; missing values are not interpolated |
| F2 recovery_from_low_kmh | Current minus speed at most recent below-80 sample; nonnegative, 0 while low/no prior low | Captures already observed recovery only; future slowing remains unknown |
| F2 distance_observed_m | Sum(v_left * positive actual_dt)/3.6, metres | Observed ground-speed path-distance proxy; no track length, future distance, normalized fraction or coordinates |
'''
    pair=csv('FEATURE_TEMPORAL_PAIRS_V072.csv').iloc[0]
    write('ML_FEATURE_EXPERIMENTS_V072.md',f'''
# Causal feature experiments v0.7.2

**No new feature variant qualifies for adoption.** Four fixed representations
and one independent weighting intervention were evaluated once on identical
development folds. The production v0.7.1 SVR remains unchanged.

## Original 13-feature audit

Features only receive the chronological prefix. All source units are checked by
the existing importer; optional gear/steering missing values are imputed using
fold training only. No participant/source identifiers, targets, next-lap timing,
whole-lap metrics or eventual distance enter the feature matrix.

{ORIGINAL_FEATURES}

Correlation/information diagnostics use development only, one lap per checkpoint
for target associations. [Feature information](FEATURE_INFORMATION_V072.csv)
records Pearson/Spearman and seed-42 kNN mutual information. They are descriptive
associations, not causal effects; laps share recording conditions, and pooling
the five prefixes would overstate independent sample size. Constant features
receive zero reported mutual information.

The checkpoint/observed-time Pearson correlation is **0.999999942**. Current speed,
recent/global speed, RPM/gear and pedal means/fractions also overlap. No correlated
feature was automatically removed. A removal study would be a separate controlled
experiment; the preregistered small experiment set was not expanded post-score.

![Pooled development feature correlations; prefixes are correlated](figures/feature_redundancy_v072.png)

Development pairs support the compression concern without proving its cause:

- At 10 s, different blocks have mean speeds **227.061 / 226.636 km/h**, full
  throttle, no braking and nearly matching recent speed, yet targets
  **142.542 / 102.793 s**. The full original feature distance is only 0.018 in
  TRAIN-standardized coordinates. Very similar observed prefixes cannot reveal
  a later incident with certainty, even with a sequence model.
- At {pair.checkpoint_s:.0f} s another pair has nearly equal mean speed
  **{pair.left_speed_mean_kmh:.3f} / {pair.right_speed_mean_kmh:.3f} km/h** and throttle
  **{pair.left_throttle_mean_pct:.3f} / {pair.right_throttle_mean_pct:.3f}%**, but
  **{pair.left_braking_phases_count:.0f} / {pair.right_braking_phases_count:.0f}** brake
  phases and **{pair.left_low_speed_observed_s:.3f} / {pair.right_low_speed_observed_s:.3f} s**
  below 80 km/h, with targets **{pair.left_target_s:.3f} / {pair.right_target_s:.3f} s**.
  Similar means do not imply identical ordered behavior. The remaining original
  features can also differ; this is not proof that the full 13-vector is identical
  or that the added descriptors must improve prediction. Exact pairs are in
  [original neighbors](FEATURE_SIMILAR_LAPS_V072.csv) and
  [temporal pairs](FEATURE_TEMPORAL_PAIRS_V072.csv).

## New definitions and limited experiment set

{new_definitions}

F0: 13 original features. F1: original + seven trailing-window features (**20**).
F2: original + five event/distance summaries (**18**). F3: their union (**25**).
F0W: the original **13** features with one training-only loss-weight intervention.
Feature identity is `causal-prefix-v072-1`; complete names/units and protocol are
bound to the signed experimental artifact. F0 calls the original feature builder
unchanged, verified bit-for-bit at every checkpoint.

Window intervals straddling the lower boundary are clipped by time; a last-known
sample before that boundary may support the beginning of the interval. No future
right-neighbor or centered interpolation is used. Prefix source-clock gaps over
200 ms and invalid boundaries fail the unchanged causal quality check. There is
no assumed uniform sample count and no imputed final interval.

Thresholds are fixed before fitting: 5% brake follows the original convention;
0.2 s excludes isolated export packets from an event count; 80/40 km/h describe
low/severe slowing in this formula-car domain. They are descriptors, not exclusion
rules or thresholds fitted to validation/test errors.

## Progress investigation and feature-quality limitations

`Car Pos Norm` is present. A development-only inspection covers all **169 laps**;
19 have some decreasing source-prefix steps. Reverse/recovery motion can be
legitimate and was not removed or forced monotonic. The author's
[NeurIPS paper, Appendix F](https://proceedings.neurips.cc/paper_files/paper/2024/file/b91ea2ba1b6521940e204b7b81d5ef47-Paper-Datasets_and_Benchmarks_Track.pdf)
describes a normalized spline-position API and ACTI human-data recording, but does
not independently establish the exact `Car Pos Norm` export mapping or resampling
semantics. **F4 raw normalized progress was therefore omitted as preregistered**;
bounded values alone are insufficient to assert that mapping. This does not block
any valid lap or the other experiments. The speed-integral proxy needs neither
a track constant nor eventual completed distance; it is not a certified track phase.

The distance proxy is largely a nonlinear interaction of mean speed and observed
duration, not necessarily independent information. At 10 s all 169 development
laps have zero sustained braking, zero below-80 duration and zero below-40 duration:
the event family cannot distinguish those early prefixes. At 60 s below-80 duration
has Spearman association **0.820** with final time, but is related to existing
speed/input aggregates and does not guarantee incremental SVR benefit.

Raw deceleration estimates also contain extreme spikes: one development source
drops **87.235 -> 56.105 km/h over 0.020 s**, yielding **432.361 m/s²** at 59.2825 s.
The cause is unestablished (possible collision/recovery or export effects);
this is not a calibrated braking-acceleration reading. No post-score clipping,
lap deletion or redesigned retry was performed. This limitation may impair F1,
but its effect is not isolated by the current experiment. See
[new-feature distributions](FEATURE_NEW_INFORMATION_V072.csv),
[source inspection](PROGRESS_SOURCE_AUDIT_V072.csv) and
[reproducible spike evidence](FEATURE_SPIKE_CASE_V072.json).

## Exact development protocol

The original TRAIN+validation pool supplies **169 laps / 40 recording blocks /
845 correlated snapshots**. The historical 36 test laps are excluded **before
feature generation**. Sort block IDs, seed-42 permute, assign index modulo five.
Every fold has eight held-out blocks; held-out lap counts are **16/30/33/47/43**.
All prefixes of a lap and all known-linked captures remain together. No driver
stratification or identity certainty requirement is introduced.

All variants use RBF SVR C=10, epsilon=0.5, gamma=scale, fold-training median
imputation and fold-training standard scaling; no parameter grid or refit on a
fold's held-out observations. Gamma's default adapts to the number of scaled
features: added correlated/noisy dimensions change kernel geometry, so this study
does not isolate representation from every regularization effect. It does
establish the outcome of the fixed, fair, limited configurations tested.

Comparison bands use the original TRAIN Q25/Q75 for common descriptive reporting.
Those constants are not predictive inputs or loss weights. Fold preprocessing,
loss weights and deterministic baseline histories see only the fold's training
population. Complete [membership](DEVELOPMENT_FOLDS_V072.csv),
[fit metadata](DEVELOPMENT_PREPROCESSING_V072.csv), [freeze](DEVELOPMENT_FREEZE_V072.json)
and [protocol](ML_PROTOCOL_V072.json) precede the fitted experiment.

## Actual out-of-fold results (same population for every variant)

{table(overall,['variant','mae_s','rmse_s','bias_s','median_absolute_error_s','p90_absolute_error_s','max_absolute_error_s','recording_macro_mae_s','prediction_to_target_std','predicted_on_actual_slope'])}

Fold variation is large compared with the feature changes:

{table(summary,['variant','mean','std','min','max'])}

Means/std in this table treat the five fold scores equally; pooled MAE weights
their unequal lap counts. Folds overlap in fitting data and are not independent
replications. No narrow prefix-based confidence interval or formal significance
claim is made. F0 fold MAE ranges **6.914–16.957 s**; the new-family pooled changes
are only **+0.020/+0.063/+0.039 s**. F1/F3 improve two folds, F2 one.

{table(details.query("dimension=='pace_band'"),['variant','value','laps','mae_s','bias_s'])}

## Weighting is separate, not a filtered dataset

F0W derives its Q25/Q75 from unique **fold-training** targets and assigns
`n_training_laps / (3*n_class_laps)` per lap, normalized to mean snapshot weight one.
Each lap's five prefixes share its weight; no lap gains weight merely from
duplicate prefix counting. Imputation/scaling remain unweighted and identical
to F0. Validation/test labels never set weights. All valid laps remain.

The intervention addresses middle-band loss dominance and observed development
slow bias, not absent slow examples. It improves pooled MAE by only **0.044 s
(0.33%)**, improves only **one of five folds**, and worsens recording-macro MAE
**11.332 -> 12.155 s**. Slow MAE improves **36.922 -> 34.115 s** and slow bias
**-35.804 -> -32.200 s**, while middle MAE worsens **7.668 -> 9.231 s**. SD ratio
increases 0.511 -> 0.583 and calibration slope 0.351 -> 0.397, but greater spread
does not establish a better overall model. Weighting is retained as an informative
negative tradeoff and is not adopted.

## Baselines, checkpoint/lap/recording behavior and examples

Each fold's median reference uses unique fold-training targets only. On all 169
OOF laps its MAE is **22.641 s**, versus **13.361 s** for F0. Previous-lap is
available for **64/169 laps**, with MAE **24.310 s** versus **10.086 s** for F0 on
the same available rows. Missing chronological evidence produces unavailable,
not borrowed held-out targets. [Matched fold baselines](DEVELOPMENT_BASELINES_V072.csv)
retain coverage; pooled scores cannot substitute for matched-population scores.

![Fold variation, checkpoint, recording-macro and slow-tail comparisons](figures/feature_experiments_v072.png)

[Detailed checkpoint/lap/block/pace metrics](DEVELOPMENT_DETAILS_V072.csv) include
MAE/RMSE/bias/median/P90/max, spread and calibration. No individual high-error
lap or recording is dropped. The deterministic illustrations are development
10th/50th/90th-percentile nearest targets (98.803/116.333/163.837 s) plus the
worst F0 OOF lap (259.595 s), with all five variants and all checkpoints shown.
They were not selected for favorable prediction gains.

![Ordinary, fast, slow and difficult development histories](figures/development_examples_v072.png)

## Decision and reproducibility

Adoption required >=0.5 s and >=5% pooled MAE gain, >=0.25 s recording-macro gain,
improvement in >=4/5 folds and no >0.5 s worsening in slow MAE/absolute bias.
**None qualifies; F0 remains selected.** No new experimental engine replaces
production. No failed variant is hidden and no further search was added.

`python -m scripts.run_barcelona_v072` verifies/reuses frozen development evidence.
Missing local research artifacts can be rebuilt on DEVELOPMENT only without
rescoring folds or historical test. `python -m scripts.report_barcelona_v072`
regenerates these reports/PNG/SVG from tables without model inference.
`python -m scripts.verify_baselines_v072` verifies historical Monza/GT7 and the
Barcelona reference. [Frozen preservation](BASELINE_PRESERVATION_V072.json) retains
original file/model hashes; original v0.7.1 test count stays one and new experimental
historical-test evaluations stay **zero**.
''')
    write('ML_MODEL_ASSESSMENT_V072.md','''
# Model assessment v0.7.2

**Decision: preserve the current SVR as the educational reference. Stop expanding
this unsuccessful compact feature search. A small, bounded sequence-model study
is a justified next research comparison, not an established superior replacement.**

## 1. Is the existing SVR functioning correctly?

Yes within the verified contract. It fits direct final seconds from the original
13 causal columns; historical median is separate, not its target or an output
offset. The signed reference, frozen rows and current validation predictions
match. No target, preprocessing or causal-boundary defect was found. Diagnostic
export-derivative spikes concern the new F1 descriptors, not an identified defect
in the original reference target. Source latency and unknown session links remain
limitations rather than demonstrated coding errors.

## 2. Is there useful telemetry-dependent information beyond a constant reference?

Yes. F0 development OOF MAE is **13.361 s**, compared with **22.641 s** for each
fold's training median on the same 169 laps. Controlled prefix-only speed changes
change outputs; later checkpoints generally provide more information. This is a
useful demonstration, with substantial slow-tail error and imperfect calibration.

## 3. Do the tested causal features meaningfully increase reliability?

No. F1/F2/F3 MAEs are **13.381/13.424/13.400 s** against F0 **13.361 s**, with
no recording-macro improvement and improvements in only one or two folds. Fold
variation (~4.1 s SD) dwarfs the changes. These fixed configurations do not
establish that all temporal representations fail; richer features also change
RBF distance/gamma geometry and some raw derivatives are noisy. They do establish
that the tested additions do not justify replacement or a positive success claim.

## 4. Is slow-lap underprediction reduced?

Only slightly with the temporal families: F0 slow MAE/bias **36.922/-35.804 s**,
F3 **36.772/-35.474 s**. Weighting gives **34.115/-32.200 s**, but worsens middle
MAE and recording-macro error and improves only one fold. No change passes the
prespecified acceptance rule. Training contains 26 slow laps and the broadest
target range, so absence of slow examples is not the explanation. Limited
conditional coverage, information loss, fixed regularization and future events
remain plausible contributors that this dataset cannot causally separate.

## 5. Is SVR still sensible?

Yes as a compact tabular reference and educational demonstration, not a precision
race-time service. OOF slope **0.351**, prediction/target SD ratio **0.511** and
slow bias show a practical limitation. The experiment supports a plateau for
these aggregates and settings, not a universal statement that SVR cannot improve.

## 6. Would further classical ML work be useful?

A bounded, independently specified study could still be useful: verify true
current-phase semantics, test one redundant-time removal or one robust temporal
representation, and compare a small classical sequence/flattened-window baseline.
Do not begin a large C/gamma/epsilon grid or repeatedly tune this historical test.
No new classical algorithm or parameter search was added after these results.
Ridge/RF/SVR v0.7.1 remains intact; its historical-test MAE is not used to choose
any v0.7.2 variant.

## 7. Is a sequence-based deep-learning experiment justified?

As a small **feasibility experiment**, yes: a sequence retains event order that
aggregates discard. It is not proven necessary or better. At 10 s some observed
trajectories are almost identical despite targets differing by ~40 s; a network
cannot reliably observe an incident that has not happened. The effective sample
size is 169 development laps in 40 imperfect blocks, not 845 independent examples
or millions of independent time samples. Overfitting is a serious practical risk.
No sequence model or new deep-learning experiment was implemented or trained here.

## 8. What should the next release implement?

Keep the present reference and development protocol, then run one limited ordered
prefix pilot against unchanged F0, F3 and the fold-training baselines. Prefer a
small GRU or causal 1D CNN, with a simple classical ordered-window comparator,
training-only normalization and group-aware validation. Fix the comparison before
fitting, report all folds/pace tails and stop if no meaningful gain appears. A new
untouched final holdout is needed for a new final-performance claim; the present
36 historical test laps remain descriptive evidence. Verifying phase information
may be more informative than increasing network depth. No further data acquisition
or live capture is part of this release.

## Sequence feasibility specification for a future release

| Aspect | Bounded proposal |
|---|---|
| Inputs | Six existing source channels: speed, throttle, brake, RPM, gear, steering; explicit timestamps/availability masks; optional verified phase only after its semantics are established |
| Causal grid | 10 Hz timestamps up to the checkpoint; last-known observation only, no centered/right-neighbor interpolation and no joining across source discontinuities |
| Prefix sizes | 100/200/300/450/600 steps for 10/20/30/45/60 s; use checkpoint-length prefixes, never full-lap length or eventual distance |
| Tensor | At most (845,600,6) float32 before development folds; ~12.17 MB (11.60 MiB) padded values, ~0.51 MB boolean mask, timestamps ~2.03 MB if explicit |
| Missing/padding | Right-pad after train-only normalization; mask padding and unsupported channel/time cells; do not infer missing observations or let padding encode final duration |
| Resampling | Audit real timestamp support and native/export cadence separately; keep first unavailable times masked; cap permitted sample age and reject/mark gaps, not interpolate through them |
| Training size | 169 unique development laps, training folds 122–153 laps / 32 blocks; five prefixes per lap stay together; no historical-test sequences in fitting |
| Architecture budget | One small GRU (e.g. 16 hidden units) or small causal Conv1D encoder, few thousand parameters; no architecture sweep or presumption that LSTM/deeper is better |
| Normalization | Fit channel statistics and any output transform only on fold training; inverse-transform predictions to final seconds for all comparisons |
| Fitting/evaluation | Same outer five recording folds; early stopping only on an inner block split of training, not the outer evaluation fold; fixed seeds/configuration and equal lap treatment |
| Controls | F0/F3, training-median and supported previous-lap references, plus a modest classical ordered-window baseline to separate sequence information from neural architecture |
| Compute | Small inputs can be piloted on CPU; GPU optional. Measure actual memory/runtime on the first fixed pilot instead of promising a runtime or installing new infrastructure |
| Success | Consistent fold/recording gains, retained slow/fast coverage, calibrated spread and bounded complexity; not simply more variable outputs or a better single run |

Unknown capture links, recurring participant codes and partial future observability
limit any architecture. A sequence pilot is a research decision under uncertainty;
it does not justify deployment, replacement or a claim of new independent test
improvement today. See [experiments](ML_FEATURE_EXPERIMENTS_V072.md) and
[pace diagnosis](PACE_DISTRIBUTION_AUDIT_V072.md) for the measured evidence.
''')
    write('NEXT_RELEASE_RECOMMENDATION.md','''
# Recommendation after v0.7.2

**Preserve SVR v0.7.1 as the operational educational reference. The compact
feature-engineering study has reached a practical plateau under the tested
settings. A limited ordered-sequence pilot is the next research comparison;
neural superiority has not been demonstrated.**

The five-fold development study uses 169 laps / 40 recording blocks and excludes
the 36 already-observed historical test laps before feature generation. F0 MAE is
13.361 s; recent/event/combined variants are 13.381/13.424/13.400 s. None improves
recording-macro error or four of five folds. One weighting intervention reduces
pooled MAE by only 0.044 s and slow MAE by 2.807 s, while worsening recording-macro
MAE by 0.822 s and middle MAE by 1.563 s. Keep it as a documented tradeoff, not a
new preferred model. All 205 valid laps remain available and none is filtered.

Training has 26 slow laps and the widest target range. Validation's fast-heavy
composition plausibly contributes to its lower historical error, but does not
explain development slow bias (-35.804 s). F0's SD ratio 0.511 and slope 0.351
show central shrinkage. Identical early observed patterns can have different
future outcomes; neither a scalar model nor a sequence network can know an
unobserved incident with certainty.

For the next release:

1. Keep the reference, raw files, original split and frozen metrics immutable.
   Reuse the fixed development folds for research, with honest unknown-link limits.
2. Predefine one small GRU or causal 1D CNN ordered-prefix pilot, with a modest
   classical ordered-window comparator. Use six current source channels on a
   causal timestamp-supported 10 Hz grid, masking unsupported/padded values.
   A padded (845,600,6) float32 development tensor is about 12.17 MB; there remain
   only 169 unique development laps. Avoid a large architecture/parameter search.
3. Use training-only normalization and inner recording splits for early stopping;
   report every outer fold, recording-macro, checkpoint and pace tail, plus
   prediction spread/calibration and all deterministic baselines. Do not select
   on greater variability alone or cherry-pick favorable example laps.
4. Verify source phase/progress export semantics before adding a current-position
   family. The speed integral already tested is a path-distance proxy, not a
   certified phase or target-normalized fraction. Raw derivative spikes also need
   an independently specified robust representation if studied again; do not
   silently clip/remove difficult laps to rescue the present experiment.
5. Require a **new untouched final holdout** for any new final-performance claim.
   Existing historical test labels may describe distributions but cannot tune
   features, weights or architecture. Additional diverse same-domain data would
   strengthen evidence, but is not a gate on useful experiments and was not
   acquired here.

No deep-learning model was added in v0.7.2. The recommendation authorizes no push,
merge, new acquisition or live simulator recording. Scope and tensor/evaluation
details are in [model assessment](ML_MODEL_ASSESSMENT_V072.md), with actual numbers
in [feature experiments](ML_FEATURE_EXPERIMENTS_V072.md) and
[pace audit](PACE_DISTRIBUTION_AUDIT_V072.md).
''')
    print('Generated pace/feature/model/recommendation reports and five PNG/SVG figure sets from frozen tables.')


if __name__=='__main__':main()
