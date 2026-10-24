"""Generate reports and six standalone figure families from executed OOF tables."""
import json
import os
import re

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT/'artifacts/matplotlib'))


def readable_prose(text):
    words = ('At', 'at', 'beyond', 'every', 'after', 'before', 'from', 'through', 'within',
        'versus', 'the', 'all', 'original', 'across', 'of', 'per', 'same', 'other',
        'only', 'observed', 'sparse', 'dense', 'raw', 'actual', 'valid', 'mean',
        'first', 'last', 'support', 'most', 'nonoverlapping', 'sub', 'Keras', 'Torch',
        'one', 'max', 'batch', 'patience', 'alpha', 'five', 'four', 'Shared')
    text = re.sub(r'\b('+'|'.join(words)+r')(?=\d)', r'\1 ', text)
    return re.sub(r'(?<=\d)(Hz|ms|s|epochs|bytes|chunks|parameters|laps)\b', r' \1', text)


def markdown(frame, precision=3):
    # No optional tabulate dependency.
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return f'{v:.{precision}f}'
        return str(v).replace('|', '/')
    return '\n'.join(['| '+' | '.join(map(str, frame.columns))+' |',
                      '| '+' | '.join(['---']*len(frame.columns))+' |']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False, name=None)])


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from motorsport.ml.barcelona_recovery import file_sha
    from motorsport.ml.evaluation_v080 import metrics
    from motorsport.ml.barcelona_experiment import dump, table_write
    output = ROOT/'docs'
    result = json.loads((output/'ML_RESULTS_V080.json').read_text(encoding='utf-8'))
    for name, digest in result['evidence_sha256'].items():
        if file_sha(output/name) != digest:
            raise ValueError('Frozen input changed: '+name)
    pred = pd.read_csv(output/'DEVELOPMENT_PREDICTIONS_V080.csv')
    overall = pd.read_csv(output/'DEVELOPMENT_OVERALL_V080.csv')
    details = pd.read_csv(output/'DEVELOPMENT_DETAILS_V080.csv')
    history = json.loads((output/'GRU_HISTORY_V080.json').read_text(encoding='utf-8'))
    consistency = pd.read_csv(output/'DEVELOPMENT_CONSISTENCY_V080.csv')
    progress = json.loads((output/'PROGRESS_STATUS_V080.json').read_text(encoding='utf-8'))
    fixed = pd.read_csv(output/'FIXED_REFERENCE_TRAJECTORIES_V080.csv')
    models = result['candidates']
    colors = dict(zip(models, plt.get_cmap('tab10').colors))
    plt.rcParams.update({'font.size':9, 'axes.grid':True, 'grid.alpha':.2})
    figures = output/'figures'
    figures.mkdir(exist_ok=True)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(figures/(name+'_v080.png'), dpi=160)
        svg = figures/(name+'_v080.svg')
        fig.savefig(svg, metadata={'Date':None})
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8', newline='\n')
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, height_ratios=[3, 1])
    for model in models:
        d = details[(details.model == model)&(details.dimension == 'checkpoint_s')].copy()
        d['second'] = d.value.astype(float)
        d = d.sort_values('second')
        axes[0].plot(d.second, d.mae_s, label=model, color=colors[model])
    d = pred[pred.model == 'SVR-SPARSE'].groupby('checkpoint_s').lap_uid.nunique()
    axes[1].step(d.index, d.values, where='mid')
    axes[0].set(ylabel='OOF MAE (s)', title='Elapsed-time checkpoints; changing surviving-lap population')
    axes[0].axvline(60, color='black', ls=':', label='Sparse training support ends')
    axes[0].legend(ncols=3)
    axes[1].set(xlabel='Nominal elapsed checkpoint (s), not circuit percentage', ylabel='Surviving laps')
    save(fig, 'progression')
    for kind in ('calibration', 'residuals'):
        fig, axes = plt.subplots(3, 3, figsize=(13, 11))
        for ax, model in zip(axes.flat, models):
            d = pred[pred.model == model]
            y = d.prediction_s if kind == 'calibration' else d.prediction_s-d.target_s
            ax.scatter(d.target_s, y, s=3, alpha=.12, color=colors[model])
            if kind == 'calibration':
                ax.plot([90, 270], [90, 270], '--', color='black')
            else:
                ax.axhline(0, color='black', ls='--')
            ax.set(title=model, xlabel='Verified final target (s)', ylabel='Predicted final (s)' if kind == 'calibration' else 'Prediction minus target (s)')
        for ax in list(axes.flat)[len(models):]:
            ax.axis('off')
        fig.suptitle('Retrospective development OOF; correlated prefixes, no new historical test')
        save(fig, kind)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    pace = details[details.dimension == 'pace_band'].pivot(index='model', columns='value', values='mae_s').reindex(models)
    pace[['fast', 'middle', 'slow']].plot.bar(ax=axes[0], rot=35)
    bias = details[details.dimension == 'pace_band'].pivot(index='model', columns='value', values='bias_s').reindex(models)
    bias[['fast', 'middle', 'slow']].plot.bar(ax=axes[1], rot=35)
    axes[0].set(title='Lap-balanced pace MAE', ylabel='Seconds')
    axes[1].set(title='Lap-balanced signed pace bias', ylabel='Seconds')
    save(fig, 'pace')
    unique = pred[pred.model == 'SVR-SPARSE'][['lap_uid', 'target_s']].drop_duplicates('lap_uid')
    selected = {}
    for label, q in [('fast', .1), ('ordinary', .5), ('slow', .9)]:
        selected[label] = unique.iloc[(unique.target_s-unique.target_s.quantile(q)).abs().argmin()].lap_uid
    worst = pred[pred.model == 'SVR-SPARSE'].assign(ae=lambda d:abs(d.prediction_s-d.target_s)).groupby('lap_uid').ae.mean().idxmax()
    selected['difficult'] = worst
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    examples = []
    for ax, (label, uid) in zip(axes.flat, selected.items()):
        d = pred[pred.lap_uid == uid]
        for model in models:
            row = d[d.model == model].sort_values('observed_elapsed_s')
            ax.plot(row.observed_elapsed_s, row.prediction_s, label=model, color=colors[model])
        ax.axhline(d.target_s.iloc[0], color='black', ls='--', label='Verified target (retrospective)')
        ax.set(title=label+' · '+uid[-12:], xlabel='Actually observed elapsed seconds', ylabel='Final-time prediction (s)')
        examples.append(d.assign(example=label))
    axes[0, 0].legend(fontsize=7)
    save(fig, 'trajectories')
    table_write(output/'DEVELOPMENT_EXAMPLES_V080.csv', pd.concat(examples, ignore_index=True))
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, h in zip(axes.flat, history):
        for name in ('loss', 'val_loss'):
            ax.plot(np.arange(1, len(h['history'][name])+1), h['history'][name], label=name)
        ax.axvline(h['best_epoch'], ls=':', color='black')
        ax.set(title=f"Outer fold {h['fold']} · inner best epoch {h['best_epoch']}",
               xlabel='Epoch', ylabel='Standardized remaining MSE + L2')
        ax.legend()
    axes[1, 2].axis('off')
    save(fig, 'gru_history')
    all_scores = overall.query("subset=='all'").set_index('model').reindex(models)
    shared = overall.query("subset=='shared_60s'").set_index('model').reindex(models)
    sparse = overall.query("subset=='sparse'").set_index('model').reindex(models)
    late = overall.query("subset=='last_scheduled'").set_index('model').reindex(models)
    tail = overall.query("subset=='retrospective_final_10s'").set_index('model').reindex(models)
    stages = details[details.dimension == 'stage'][['model', 'value', 'laps', 'snapshots', 'mae_s', 'bias_s']]
    pace = details[details.dimension == 'pace_band'][['model', 'value', 'laps', 'mae_s', 'bias_s']]
    display = pd.DataFrame({'model':models, 'all_lap_balanced_MAE':all_scores.mae_s.values,
        'same_5_60s_MAE':shared.mae_s.values, 'original_sparse_MAE':sparse.mae_s.values,
        'last_scheduled_MAE':late.mae_s.values, 'final_10s_retrospective_MAE':tail.mae_s.values})
    table_write(output/'MODEL_COMPARISON_V080.csv', display)
    costs = pd.DataFrame([{k:h[k] for k in ('fold', 'fit_laps', 'fit_blocks', 'inner_validation_laps',
             'epochs_ran', 'best_epoch', 'seconds', 'classical_seconds', 'parameter_count',
             'process_peak_working_set_bytes', 'padded_fit_tensor_bytes', 'padded_steps')} for h in history])
    table_write(output/'COMPUTE_V080.csv', costs)
    joined = pred[pred.model == 'SVR-SPARSE'][['lap_uid', 'checkpoint_s', 'prediction_s']].merge(
        pred[pred.model == 'SVR-DENSE'][['lap_uid', 'checkpoint_s', 'prediction_s']], on=['lap_uid', 'checkpoint_s'], suffixes=('_sparse', '_dense'))
    ablations = dict(cadence_only_max_change_at_shared_checkpoint_s=result['sparse_reference_max_deviation_s'],
        dense_minus_sparse_mae_shared_60s=float(shared.loc['SVR-DENSE', 'mae_s']-shared.loc['SVR-SPARSE', 'mae_s']),
        remaining_minus_direct_mae_shared_60s=float(shared.loc['SVR-REMAINING', 'mae_s']-shared.loc['SVR-DENSE', 'mae_s']),
        remaining_minus_direct_mae_last_scheduled=float(late.loc['SVR-REMAINING', 'mae_s']-late.loc['SVR-DENSE', 'mae_s']),
        ordered_ridge_minus_remaining_svr_mae_shared_60s=float(shared.loc['RIDGE-ORDERED', 'mae_s']-shared.loc['SVR-REMAINING', 'mae_s']),
        gru_minus_ordered_ridge_mae_shared_60s=float(shared.loc['GRU', 'mae_s']-shared.loc['RIDGE-ORDERED', 'mae_s']),
        gru_minus_ordered_ridge_mae_all=float(all_scores.loc['GRU', 'mae_s']-all_scores.loc['RIDGE-ORDERED', 'mae_s']),
        caveats='No causal architecture/order isolation: classical estimator/regularization differ, and GRU inner fit uses fewer laps. Dense loss weights have equal lap mass but sum to dense snapshot count, so total regularization mass changes relative to sparse C10. No verified position feature exists.')
    dump(output/'ABLATIONS_V080.json', ablations)
    fixed_stats = []
    for label, rows in [('sparse_compatibility', fixed[fixed.checkpoint_s.isin([10, 20, 30, 45, 60])]),
                        ('dense_5_60s', fixed[fixed.checkpoint_s <= 60]), ('dense_all', fixed)]:
        error = abs(rows.prediction_s-rows.target_s)
        fixed_stats.append(dict(schedule=label, laps=rows.lap_uid.nunique(), snapshots=len(rows),
            lap_balanced_mae_s=float(rows.assign(error=error).groupby('lap_uid').error.mean().mean())))
    table_write(output/'FIXED_REFERENCE_METRICS_V080.csv', pd.DataFrame(fixed_stats))
    common = ('All results below are exploratory **development OOF**, not a fresh independent test. '
        'All 169 development laps / 40 recording blocks are retained; 36 already-inspected historical test laps '
        'are excluded before representations. Source block independence is imperfect and folds overlap in fitting. '
        'Operational SVR v0.7.1 and its historical evidence remain unchanged.\n\n')
    links = '\n\nSee [comparison](ML_COMPARISON_V080.md), [checkpoints](CHECKPOINT_STRATEGY_V080.md), '
    links += '[dense SVR](SVR_DENSE_EXPERIMENT_V080.md), [sequences](SEQUENCE_MODEL_EXPERIMENTS_V080.md), '
    links += '[protocol](ML_PROTOCOL_V080.json), [results/hashes](ML_RESULTS_V080.json) and [architecture](ARCHITECTURE_V080.md).\n'
    checkpoint_doc = '# Checkpoint strategy v0.8\n\n'+common+f'''Use the **elapsed-time fallback**, default every 5 s, configurable in replay. Compatibility remains 10/20/30/45/60 s. There are {result['checkpoints']} actual correlated observations, {result['min_checkpoints_per_lap']}–{result['max_checkpoints_per_lap']} per lap. A checkpoint uses the last source sample at or before its nominal second, with <=100 ms freshness. Preserve this exact observed timestamp. No time fraction, eventual duration, final distance, centered interpolation or invented circuit percentage is used.

The source scan stops on the first missing/reset clock or gap >200 ms. No later observation repairs that prefix. Schedule emission depends on observations arriving; source-tail mutation cannot change an already emitted checkpoint. Near completion the last scheduled point is less than5s from the end on this valid population; it is identified retrospectively for scoring only.

## Progress investigation and decision

The [author project](https://assetto-corsa-gym.github.io/) identifies ACTI as its human-data exporter. The [primary paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/b91ea2ba1b6521940e204b7b81d5ef47-Paper-Datasets_and_Benchmarks_Track.pdf), Appendix F.4, describes a simulator normalized track-position input. This documents the simulator interface; it does not certify an exact mapping to `Car Pos Norm` in these human LD exports. The author's [conversion code](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/motec_to_pickle.py) and [configuration](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/motec_to_pickle_config.yml) did not establish the missing exact mapping/interpolation/latency contract during this investigation.

Full development-only inspection: range {progress['minimum']}–{progress['maximum']}, {progress['laps_with_backward_steps']} laps with negative steps, {progress['laps_with_large_negative_steps']} with a large wrap. Every lap includes a terminal position wrap while the lap timer/counter still belongs to the outgoing lap. For example the first AB lap crosses 0.999933 at174.91s to0.000167 at174.93s. This is compatible with a finish-line position channel, but numeric compatibility is not independent semantic verification. Additional local reversals can reflect reverse motion or export effects; not every negative step is a fault. All laps are retained.

Source declared units are blank, export rates50/100Hz; native sensor cadence and interpolation kernels are not established. Values are position-like and plausibly independent of eventual target, but this inference is insufficient to enable percentage thresholds. No production5% scheduler is exposed. This avoids pretending that eventual time fractions are track progress. [Per-lap source evidence](PROGRESS_SOURCE_AUDIT_V080.csv) records ranges, endpoints, discontinuities and export cadence.

## Deterministic remaining-time reference

For unique permitted training targets T and observed elapsed t, return median(T given T>t), equivalently t+median(T-t given T>t). In-lap survival is available at prediction time. If no training lap survives, remaining is0 and support0 is reported. This is a **survival-conditioned elapsed-time population baseline**, not a physical position or remaining-distance model. Long late laps can have very small support and severe selection bias. Held-out targets never update the profile. MEDIAN remains the unconditional training-target baseline.

![MAE and changing survivor counts](figures/progression_v080.png)

Compare models at the same observation; do not interpret lower MAE on the shrinking late population as a within-lap causal gain. Shared5–60s, original sparse checkpoints, early/middle/late, last-scheduled and retrospective final10s reports are separate. The retrospective bands never enter inference/UI before reveal.
'''+links
    svr_doc = '# Dense and remaining-time SVR v0.8\n\n'+common+'''## Frequency versus model fitting

SVR-SPARSE refits the original fixed C10/epsilon0.5/RBF-scale configuration on the original five checkpoints within each frozen development fold. Its learned parameters are then held fixed for all extra inference points. Original-checkpoint outputs match the frozen v072 F0 within1e-9s. Extra points do not change a prediction at a shared horizon. Outputs beyond60s extrapolate outside this sparse model's training horizons.

SVR-DENSE uses the same13 causal features and settings with the dense schedule. SVR-REMAINING uses exactly the same dense inputs/weights but labels verified_final-observed_elapsed. At inference no target is accepted; return observed_elapsed+max(0,raw_remaining). Raw negatives/projection effects remain in CSVs. No tuning was added.

Dense loss weights are inverse snapshots per lap, normalized to mean1; each lap contributes equal total. Imputation/scaling fit training only. More snapshots change the feature distribution **and total SVR loss mass relative to sparse fixed C10**. Thus this is a practical dense-training comparison, not a pure causal snapshot-count effect at fixed effective regularization. The direct-versus-remaining comparison does keep the exact rows, weights, preprocessing and configuration constant.

'''+markdown(display)+f'''

Dense minus sparse MAE at shared5–60s: **{ablations['dense_minus_sparse_mae_shared_60s']:+.3f}s**. Remaining minus dense-direct: **{ablations['remaining_minus_direct_mae_shared_60s']:+.3f}s** there, **{ablations['remaining_minus_direct_mae_last_scheduled']:+.3f}s** at the last scheduled observation. Negative differences favor the new candidate.

## Fixed signed production SVR, separate original-validation-only trajectory

The immutable v071 SVR is also evaluated at extra points on its66 original validation laps, with no refit and no new historical-test predictions. This population is not the169-lap OOF population and must not be mixed with it.

'''+markdown(pd.DataFrame(fixed_stats))+'''

Different pooled schedule MAEs summarize different horizons; they do not demonstrate that increasing inference cadence improved fixed-checkpoint accuracy. The practical benefit is finer-grained feedback and coverage after60s, with explicit extrapolation limits for the sparse model.

## Constraint and calibration

'''+markdown(all_scores[['negative_raw_remaining', 'projected_fraction', 'projection_mae_change_s',
        'final_before_observed_fraction', 'prediction_to_target_std', 'predicted_on_actual_slope']].reset_index())+links
    seq_doc = '# Ordered-window and GRU experiments v0.8\n\n'+common+'''## Shared causal representation

Six channels: validated speed km/h, throttle/brake%, RPM, gear, steering degrees when declared. At10Hz use only the last known source sample, at most200ms old. No future neighbor or gap interpolation. Append the actual terminal observation when off-grid. Compress the entire observed prefix into ordered nonoverlapping2s chunks: six means, six availability fractions and observed chunk duration/2. No prefix is truncated at60s. Fixed support600s/301chunks is a model contract, independent of the eventual evaluated lap length. The last partial chunk is retained.

This is a compact sequence of actual observations, not raw10Hz input to the recurrent layer. Compression loses sub2s order and is an explicit CPU/memory tradeoff. Chronological chunks retain whole-prefix order. Core source defects reject the same checkpoint for all candidates; optional channels remain missing, with indicators and training-only imputation. Zero padding has a separate boolean mask; genuine zero-valued telemetry remains observed.

Sequence means/std/imputation use longest-prefix training chunks once per lap, without duplicated-prefix statistics or padding. Context uses the same13 original causal features, with training-only imputer/scaler. Ridge and GRU receive the same chunk information and context at exactly the same observation cutoff. Ridge flattens ordered chunks with fixed padding/masks; GRU consumes variable-length chunks and explicit masks. No target-normalized sequence length exists.

## Fixed candidates and actual training

RIDGE-ORDERED: alpha100, standardized chunk values and context, remaining-time target, lap-balanced loss. GRU: one16-unit Keras GRU, L2=.001, concatenated context, Dense8 ReLU and linear output; **1737 trainable parameters**. Predict standardized remaining seconds, invert using training-only weighted mean/std, then add observed elapsed and explicitly project negative remaining values. Adam.003 clipnorm1, MSE, batch64, max20epochs, seed42+fold, early-stop patience4, restore best weights. One architecture, no search.

Reuse five outer recording folds. GRU reserves four outer-training blocks for early stopping, fits all preprocessing/output transforms on the other28 blocks, and never monitors outer held-out loss. Classical models fit all32 outer-training blocks. This common outer evaluation is fair as a comparison of practical training procedures; **it does not isolate architecture causally**, because GRU has fewer fitting laps and a different regularizer. No superiority is attributed solely to temporal order or neural recurrence.

Existing Keras3.15.1/Torch2.14.1 CPU backend, two Torch threads, deterministic algorithms. No CUDA/container/GPU install. Keras and Torch load only for explicit training or GRU selection. Record actual cumulative process peak working set (includes corpus, sklearn and Keras, not GRU-exclusive memory), tensor sizes and per-fold durations:

'''+markdown(costs)+f'''

Total outer GRU fitting time: **{costs.seconds.sum():.1f}s**. Final all169 research model uses the median outer-selected best epoch count, **{result['final_research_epochs']}**, and has no independent evaluation. UI uses held-out-fold artifacts instead, so its experimental predictions reproduce OOF rather than the all-development in-sample fit.

![Actual inner training and validation histories](figures/gru_history_v080.png)

'''+markdown(display[display.model.isin(['SVR-REMAINING', 'RIDGE-ORDERED', 'GRU', 'REMAINING-REFERENCE'])])+f'''

GRU minus ordered Ridge MAE: **{ablations['gru_minus_ordered_ridge_mae_shared_60s']:+.3f}s** at common5–60s, **{ablations['gru_minus_ordered_ridge_mae_all']:+.3f}s** across lap-balanced full trajectories. Negative favors GRU. Inspect pace/fold/late tradeoffs before recommending anything. A weak result is retained without adding models or retuning.

Each fold has a signed classical bundle and a native.keras file. Verify native bytes against a digest inside the HMAC-authenticated bundle before safe_mode deserialization. Domain, protocol, feature order, corpus/dev identity and fold are bound. Only development IDs belonging to the evaluated fold may use OOF replay. The historical model namespaces remain unchanged. Normal Streamlit reruns do not train.
'''+links
    comparison_doc = '# ML comparison v0.8\n\n'+common+markdown(display)+'''\n
Primary full-trajectory scores give each lap equal weight, irrespective of checkpoint count. RMSE, bias, median/P90/max, recording macro, calibration and spread are in the complete table below. Weighted quantiles interpolate centers of cumulative weights. Recording macro averages lap means within each block, then blocks equally. No prefix-based significance or confidence interval is claimed.

'''+markdown(all_scores[['mae_s', 'rmse_s', 'bias_s', 'median_absolute_error_s', 'p90_absolute_error_s',
    'max_absolute_error_s', 'recording_macro_mae_s', 'prediction_to_target_std', 'predicted_on_actual_slope']].reset_index())+'''

## Early, middle and late actual elapsed seconds

'''+markdown(stages)+'''\n
Selected actual-second checkpoints below make changing late coverage explicit.
The complete progression is in DEVELOPMENT_DETAILS_V080.csv. A255s checkpoint
contains only one very slow lap; a small mean last-scheduled error across169 laps
does not imply a small error on that lap.

'''+markdown(details[(details.dimension == 'checkpoint_s') &
    pd.to_numeric(details.value, errors='coerce').isin([5, 10, 30, 60, 90, 120, 180, 240, 255])]
    [['model', 'value', 'laps', 'mae_s', 'bias_s']])+'''\n
## Fast / middle / slow, without removing outliers

Descriptive thresholds are the frozen original TRAIN109.734/140.04333333333335s, never features or held-out loss weights. Each band contains the same unique laps across candidates.

'''+markdown(pace)+'''\n
![Pace error and bias](figures/pace_v080.png)

![Retrospective calibration](figures/calibration_v080.png)

![Residuals versus verified final time](figures/residuals_v080.png)

## Trajectory consistency and examples

Consecutive prediction-error improvements are measured per lap, then averaged across laps. No model is guaranteed to improve monotonically. Jumps show responsiveness and instability; smaller jumps alone are not accuracy. More cadence yields more feedback, not automatically smoother predictions.

'''+markdown(consistency.groupby('model')[['fraction_error_improved', 'mean_prediction_jump_s', 'max_prediction_jump_s',
    'first_absolute_error_s', 'last_absolute_error_s']].mean().reset_index())+'''

Examples are development10th/50th/90th-percentile nearest targets plus worst sparse-SVR mean trajectory error. This is a deterministic retrospective descriptive selection, not favorable cherry-picking or inference input.

![Full observed-lap histories for ordinary and difficult laps](figures/trajectories_v080.png)

## What is and is not isolated

Extra inference: exactly unchanged predictions at the original shared points. Dense fitting: compare matching observations, noting altered training distribution and effective total loss mass. Remaining target: same dense SVR information/weights/configuration, so target formulation is isolated within this setup. Ordered Ridge versus SVR changes representation and estimator simultaneously. GRU versus Ridge shares the same chunk information/remaining target, but training population, nonlinear architecture and regularization differ. No shuffled-order control is fitted, so the study cannot identify a pure effect of temporal ordering. No explicit track-progress feature is admitted.

The original operational SVR is not ranked using in-sample production predictions against OOF candidates. Its unchanged configuration is represented by OOF SVR-SPARSE, while the immutable artifact's separate66-lap validation trajectory is clearly labelled. New final-performance claims need genuinely untouched observations.
'''+links
    texts = {'CHECKPOINT_STRATEGY_V080.md':checkpoint_doc, 'SVR_DENSE_EXPERIMENT_V080.md':svr_doc,
             'SEQUENCE_MODEL_EXPERIMENTS_V080.md':seq_doc, 'ML_COMPARISON_V080.md':comparison_doc}
    for name, text in texts.items():
        (output/name).write_text(readable_prose(text), encoding='utf-8', newline='\n')
    print('Generated four measured experiment reports, six PNG/SVG figure families and comparison evidence.')


if __name__ == '__main__':
    main()
