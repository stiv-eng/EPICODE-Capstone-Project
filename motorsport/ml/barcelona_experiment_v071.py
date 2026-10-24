"""Fixed recording holdout; inclusive development and one frozen final test.

The historical numerical model and feature implementations are reused unchanged.
Development decisions and their evidence are saved before the test prediction.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from .training import TrainingBundle, make_models
from .features import FEATURES, snapshots
from .baselines import reference_history
from .evaluation import summarize
from .artifacts import LocalArtifactStore
from .barcelona_experiment import dump, table_write, detailed_metrics
from .barcelona_recovery import (ROOT, DOMAIN, PROTOCOL, compatibility, verify_compatibility,
                                 file_sha, frozen_split, data_gate, baseline_references)

MODEL_ROOT = ROOT/'artifacts/barcelona_v071/models'


@dataclass
class BarcelonaBundle(TrainingBundle):
    compatibility: dict
    date_reliability: dict
    experiment: str


def save_bundle(bundle, model_root=MODEL_ROOT):
    path = LocalArtifactStore(model_root).save(bundle, 'barcelona-v071-'+bundle.corpus_id[:16])
    meta = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    meta.update(producer='Motorsport Telemetry Analyzer v0.7.1 local Barcelona training',
                compatibility=bundle.compatibility)
    dump(path.with_suffix('.json'), meta)
    return path


def load_bundle(corpus, model_root=MODEL_ROOT):
    name = 'barcelona-v071-'+corpus.identity[:16]
    store = LocalArtifactStore(model_root)
    bundle = store.load(name)
    verify_compatibility(bundle, corpus)
    meta = json.loads(store._path(name).with_suffix('.json').read_text(encoding='utf-8'))
    if meta.get('compatibility') != bundle.compatibility: raise ValueError('Artifact provenance mismatch')
    return bundle


def score(rows, q75=None):
    result = detailed_metrics(rows)
    errors = rows.assign(ae=(rows.prediction_s-rows.target_s).abs())
    groups = errors.groupby('physical_session_id').ae.mean()
    result.update(recording_macro_mae_s=float(groups.mean()), recording_mae_min_s=float(groups.min()),
                  recording_mae_max_s=float(groups.max()), prediction_mean_s=float(rows.prediction_s.mean()),
                  prediction_std_s=float(rows.prediction_s.std()), target_std_s=float(rows.target_s.std()),
                  prediction_min_s=float(rows.prediction_s.min()), prediction_max_s=float(rows.prediction_s.max()))
    if q75 is not None:
        slow = errors.loc[errors.target_s > q75]
        result['slow_lap_mae_s'] = float(slow.ae.mean()) if len(slow) else None
    return result


def rank(scores):
    return min(scores, key=lambda r:(r['mae_s'], r['rmse_s'], abs(r['bias_s']), r['model']))['model']


def development(train, validation, q75, experiment):
    models, rows, scores = make_models(), [], []
    for name, model in models.items():
        model.fit(train.loc[:, FEATURES], train.target_s)
        predicted = validation.assign(prediction_s=model.predict(validation.loc[:, FEATURES]), model=name)
        predicted['error_s'] = predicted.prediction_s-predicted.target_s
        rows.append(predicted)
        scores.append(dict(experiment=experiment, model=name, **score(predicted, q75)))
    return models, pd.concat(rows, ignore_index=True), scores


def choose_experiment(a, b):
    """Preregistered meaningful gain on >=2 models; no test argument exists."""
    passing = []
    for name in {r['model'] for r in a}:
        left = next(r for r in a if r['model']==name)
        right = next(r for r in b if r['model']==name)
        gain = left['mae_s']-right['mae_s']
        slow_ok = (left['slow_lap_mae_s'] is None or right['slow_lap_mae_s'] is not None
                   and right['slow_lap_mae_s'] <= left['slow_lap_mae_s']+.5)
        if gain >= .5 and gain >= .05*left['mae_s'] and slow_ok and right['recording_macro_mae_s'] < left['recording_macro_mae_s']:
            passing.append(name)
    return 'B' if len(passing)>=2 else 'A'


def _bundle(corpus, selected, experiment, split, predictions, models, history, rejections, importance):
    return BarcelonaBundle(corpus.identity, 'Barcelona · retrospective recording-block holdout · experiment '+experiment,
        tuple(FEATURES), models, selected, split, predictions, summarize(predictions), importance, history,
        rejections, DOMAIN, compatibility(corpus),
        corpus.targets.set_index('lap_uid').date_reliable.to_dict(), experiment)


def run(corpus, audit=None, output=ROOT/'docs', model_root=MODEL_ROOT):
    gate = data_gate(corpus, audit)
    if not gate['eligible']: raise ValueError('; '.join(gate['reasons']))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    result_path = output/'ML_RESULTS_V071.json'
    identity = compatibility(corpus)
    model_path = Path(model_root)/('barcelona-v071-'+corpus.identity[:16]+'.joblib')
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result['compatibility'] != identity: raise ValueError('Frozen experiment differs from corpus/protocol')
        for name, digest in result['evidence_sha256'].items():
            if file_sha(output/name) != digest: raise ValueError('Frozen evidence changed: '+name)
        if model_path.exists(): return load_bundle(corpus, model_root)
        # Offline reinstall: fit TRAIN only and reuse recorded evaluation rows.
        split = pd.read_csv(output/'BARCELONA_SPLIT_V071.csv')
        table, rejections = snapshots(corpus)
        table = table.merge(split[['lap_uid', 'partition']], on='lap_uid', validate='many_to_one')
        train = table.query("partition=='train'")
        if result['experiment']=='B':
            omitted = set(corpus.targets.loc[corpus.targets.timing_quality_category, 'lap_uid'])
            train = train.loc[~train.lap_uid.isin(omitted)]
        models = make_models()
        for model in models.values(): model.fit(train.loc[:, FEATURES], train.target_s)
        bundle = _bundle(corpus, result['selected_model'], result['experiment'], split,
            pd.read_csv(output/'BARCELONA_PREDICTIONS_V071.csv'), models,
            reference_history(corpus, set(train.lap_uid)), rejections,
            pd.read_csv(output/'BARCELONA_IMPORTANCE_V071.csv'))
        save_bundle(bundle, model_root)
        return bundle
    # Freeze lap membership before any model is fitted or quality rule compared.
    split = frozen_split(corpus)
    freeze = dict(compatibility=identity, groups=split.groupby(['physical_session_id', 'partition']).size().reset_index(name='laps').to_dict('records'))
    freeze_path = output/'BARCELONA_SPLIT_V071.json'
    if freeze_path.exists() and json.loads(freeze_path.read_text(encoding='utf-8')) != freeze:
        raise ValueError('Existing split differs; preserve the experiment')
    test_marker = output/'BARCELONA_TEST_ACCESS_V071.json'
    if test_marker.exists():
        raise ValueError('Final test was already opened without a completed frozen result; preserve evidence and review the interrupted run')
    dump(freeze_path, freeze); table_write(output/'BARCELONA_SPLIT_V071.csv', split)
    table, rejections = snapshots(corpus)
    table = table.merge(split[['lap_uid', 'partition']], on='lap_uid', validate='many_to_one')
    if table.groupby('lap_uid').checkpoint_s.nunique().min() != 5 or set(table.lap_uid) != set(split.lap_uid):
        raise ValueError('Incomplete causal checkpoint population')
    train = table.query("partition=='train'")
    validation = table.query("partition=='validation'")
    full_train_ids = set(train.lap_uid)
    train_targets = corpus.targets.loc[corpus.targets.lap_uid.isin(full_train_ids), 'target_s']
    q25, q75 = map(float, train_targets.quantile([.25, .75]))
    quality_ids = set(corpus.targets.loc[corpus.targets.timing_quality_category, 'lap_uid']) & full_train_ids
    print(f'Frozen {gate["lap_counts"]}; quality-category training laps: {len(quality_ids)}', flush=True)
    models_a, predictions_a, scores_a = development(train, validation, q75, 'A')
    experiment, models, validation_predictions, scores = 'A', models_a, predictions_a, scores_a
    all_scores = list(scores_a)
    comparison = dict(quality_category='max positive source timer step >100 ms and <=200 ms',
                      excluded_training_laps=sorted(quality_ids), decision='A',
                      reason='No qualifying training laps; no filtering experiment invented')
    if quality_ids:
        filtered = train.loc[~train.lap_uid.isin(quality_ids)]
        if filtered.empty:
            comparison['reason'] = 'Filtering would remove every training lap; keep inclusive A'
        else:
            models_b, predictions_b, scores_b = development(filtered, validation, q75, 'B')
            all_scores += scores_b
            experiment = choose_experiment(scores_a, scores_b)
            comparison.update(decision=experiment, reason='Preregistered multi-model/slow-band/macro validation rule')
            if experiment=='B':
                _, repeated, _ = development(filtered, validation, q75, 'B')
                if not np.allclose(repeated.prediction_s, predictions_b.prediction_s, atol=1e-10, rtol=0):
                    raise ValueError('Filtering benefit not reproducible')
                models, validation_predictions, scores, train = models_b, predictions_b, scores_b, filtered
    table_write(output/'BARCELONA_EXPERIMENTS_V071.csv', pd.DataFrame(all_scores))
    dump(output/'BARCELONA_FILTER_DECISION_V071.json', comparison)
    selected = rank(scores)
    # Learning curve: nested seeded TRAIN groups, same fixed inclusive validation.
    groups = sorted(train.physical_session_id.unique())
    groups = np.random.default_rng(42).permutation(groups).tolist()
    counts = sorted({max(1, int(len(groups)*.5)), max(1, int(len(groups)*.75)), len(groups)})
    curves = []
    for count in counts:
        subset = train.loc[train.physical_session_id.isin(groups[:count])]
        for name, candidate in make_models().items():
            candidate.fit(subset.loc[:, FEATURES], subset.target_s)
            for label, rows in [('train', subset), ('validation', validation)]:
                predicted = rows.assign(prediction_s=candidate.predict(rows.loc[:, FEATURES]))
                curves.append(dict(training_groups=count, training_laps=subset.lap_uid.nunique(),
                                   model=name, partition=label, **score(predicted, q75)))
    table_write(output/'BARCELONA_LEARNING_CURVE_V071.csv', pd.DataFrame(curves))
    # Descriptive validation-only importance; no feature selection/refit follows.
    importance = permutation_importance(models[selected], validation.loc[:, FEATURES], validation.target_s,
                                        scoring='neg_mean_absolute_error', n_repeats=3, random_state=42, n_jobs=1)
    importance = pd.DataFrame(dict(model=selected, feature=list(FEATURES),
                                  mae_increase_s=importance.importances_mean, std_s=importance.importances_std))
    table_write(output/'BARCELONA_IMPORTANCE_V071.csv', importance)
    selection = dict(selected_model=selected, experiment=experiment, validation=scores,
                     rule=json.loads(PROTOCOL.read_text(encoding='utf-8'))['selection'], test_evaluated=False)
    dump(output/'BARCELONA_SELECTION_V071.json', selection)
    history = reference_history(corpus, set(train.lap_uid))
    reliable = corpus.targets.set_index('lap_uid').date_reliable.to_dict()
    references = {lap.lap_uid:baseline_references(lap, history, reliable) for lap in corpus.laps}
    # Sole batch evaluation of selected model on frozen test, after saved decision.
    dump(test_marker, dict(compatibility=identity, selected_model=selected, experiment=experiment,
                           selection_sha256=file_sha(output/'BARCELONA_SELECTION_V071.json'), test_evaluations=1))
    test = table.query("partition=='test'").copy()
    test['prediction_s'] = models[selected].predict(test.loc[:, FEATURES])
    test['model'] = selected; test['error_s'] = test.prediction_s-test.target_s
    predictions = pd.concat([validation_predictions, test], ignore_index=True)
    for name in ('previous_lap', 'historical_median'):
        predictions[name] = pd.to_numeric(predictions.lap_uid.map(lambda uid:references[uid][name]), errors='coerce').astype(float)
    table_write(output/'BARCELONA_PREDICTIONS_V071.csv', predictions)
    reports = summarize(predictions)
    for name, frame in reports.items(): table_write(output/f'BARCELONA_{name.upper()}_V071.csv', frame)
    diagnostic_rows = []
    bands = predictions.assign(pace_band=np.where(predictions.target_s<q25, 'fast',
                                      np.where(predictions.target_s>q75, 'slow', 'middle')))
    for dimension, frame in [('checkpoint_s', bands), ('lap_uid', bands), ('physical_session_id', bands), ('pace_band', bands)]:
        for (partition, model, value), rows in frame.groupby(['partition', 'model', dimension]):
            diagnostic_rows.append(dict(partition=partition, model=model, dimension=dimension, value=value, **score(rows)))
    table_write(output/'BARCELONA_DIAGNOSTICS_V071.csv', pd.DataFrame(diagnostic_rows))
    baselines = []
    for (partition, name), rows in predictions.groupby(['partition', 'model']):
        for baseline in ('previous_lap', 'historical_median'):
            matched = rows.loc[rows[baseline].notna()]
            baselines.append(dict(partition=partition, model=name, baseline=baseline,
                                  coverage=float(len(matched)/len(rows)), **detailed_metrics(matched, baseline)))
    table_write(output/'BARCELONA_BASELINE_DETAILS_V071.csv', pd.DataFrame(baselines))
    result = dict(status='evaluated', compatibility=identity, selected_model=selected, experiment=experiment,
                  gate=gate, validation=scores, selected_test=score(test, q75),
                  training_target_quartiles=[q25, q75], training_target_mean_s=float(train_targets.mean()),
                  training_target_median_s=float(train_targets.median()), test_evaluations=1,
                  uncertainty='Descriptive recording holdout; prefixes correlated and unknown capture links. '
                              'No certified unseen-session/driver generalization or prefix-based confidence interval.',
                  evidence_sha256={p.name:file_sha(p) for p in output.glob('BARCELONA_*_V071.csv')})
    for name in ('BARCELONA_SPLIT_V071.json', 'BARCELONA_FILTER_DECISION_V071.json',
                 'BARCELONA_SELECTION_V071.json', 'BARCELONA_TEST_ACCESS_V071.json'):
        result['evidence_sha256'][name] = file_sha(output/name)
    bundle = _bundle(corpus, selected, experiment, split, predictions, models, history, rejections, importance)
    save_bundle(bundle, model_root)
    dump(result_path, result)
    return bundle
