"""Bounded development experiment and signed artifacts, isolated from v071."""
from dataclasses import dataclass
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .artifacts import LocalArtifactStore
from .training import TrainingBundle, make_models
from .features import FEATURES, CHECKPOINTS, prefix_features
from .barcelona_recovery import ROOT, DOMAIN, file_sha
from .barcelona_experiment import dump, table_write
from .development_v072 import development_pool, group_folds
from .diagnosis_v072 import pace_band
from .progression_v080 import VERSION, checkpoints, remaining_target, reconstruct, remaining_reference
from .sequences_v080 import sequence, SequenceTransform, make_gru, keras_api, raw_gru
from .evaluation_v080 import lap_weights, summarize

PROTOCOL = ROOT/'docs/ML_PROTOCOL_V080.json'
MODEL_ROOT = ROOT/'artifacts/barcelona_v080/models'
CANDIDATES = ('SVR-SPARSE', 'SVR-DENSE', 'SVR-REMAINING', 'REMAINING-REFERENCE', 'RIDGE-ORDERED', 'GRU', 'MEDIAN')


@dataclass
class DenseBundle(TrainingBundle):
    compatibility: dict
    sequence_transform: object
    remaining_mean: float
    remaining_scale: float
    training_targets: np.ndarray
    allowed_ids: tuple


def identity(corpus, development):
    return dict(version=VERSION, domain=list(DOMAIN), base_corpus_id=corpus.identity,
        development_corpus_id=development.identity, protocol_sha256=file_sha(PROTOCOL),
        folds_sha256=file_sha(ROOT/'docs/DEVELOPMENT_FOLDS_V072.csv'),
        feature_names=list(FEATURES), channels=['speed_kmh', 'throttle_pct', 'brake_pct', 'rpm', 'gear', 'steering'])


def observation_table(development):
    rows, seqs = [], []
    for source in development.laps:
        for checkpoint in checkpoints(source):
            features, quality = prefix_features(source, checkpoint)
            seq, sq = sequence(source, checkpoint)
            if quality['observed_elapsed_s'] != sq['observed_elapsed_s']:
                raise AssertionError('Representation horizons differ')
            rows.append(dict(lap_uid=source.lap_uid, physical_session_id=source.physical_session_id, **features))
            seqs.append(seq)
    observations = pd.DataFrame(rows)
    # Labels never enter checkpointing or any representation builder.
    table = observations.merge(development.targets[['lap_uid', 'target_s']], on='lap_uid', validate='many_to_one')
    table['remaining_s'] = remaining_target(table.target_s, table.observed_elapsed_s)
    table['pace_band'] = pace_band(table.target_s, 109.734, 140.04333333333335)
    table['stage'] = np.where(table.checkpoint_s <= 30, 'early_5_30s',
                              np.where(table.checkpoint_s <= 60, 'middle_35_60s', 'late_over_60s'))
    return table, seqs


def longest_indices(table):
    # Return relative indices into this table's sequence list.
    return table.reset_index(drop=True).sort_values('checkpoint_s').groupby('lap_uid').tail(1).index.to_numpy()


def inner_partition(table, fold):
    groups = sorted(table.physical_session_id.unique())
    if len(groups) < 2:
        raise ValueError('Inner early stopping needs at least two training blocks')
    n = min(4, max(1, len(groups)//5))
    validation = set(np.random.default_rng(420+fold).permutation(groups)[:n])
    return table.physical_session_id.isin(validation).to_numpy()


def working_memory():
    """OS process peak working set, bytes; no optional dependency."""
    import sys
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)]+[(n, ctypes.c_size_t) for n in
                ('peak_working_set', 'working_set', 'quota_peak_paged', 'quota_paged', 'quota_peak_nonpaged',
                 'quota_nonpaged', 'pagefile', 'peak_pagefile')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.peak_working_set)
    import resource
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform == 'darwin' else 1024)


def fit_classical(train, seqs):
    models = {}
    sparse = train[train.checkpoint_s.isin(CHECKPOINTS)]
    models['SVR-SPARSE'] = make_models()['SVR'].fit(sparse.loc[:, FEATURES], sparse.target_s)
    weights = lap_weights(train)
    for name, y in (('SVR-DENSE', train.target_s), ('SVR-REMAINING', train.remaining_s)):
        model = make_models()['SVR']
        model.fit(train.loc[:, FEATURES], y, model__sample_weight=weights)
        models[name] = model
    prep = SequenceTransform.fit(seqs, train.loc[:, FEATURES], longest_indices(train))
    flat = prep.flat(seqs, train.loc[:, FEATURES])
    models['RIDGE-ORDERED'] = Ridge(alpha=100.).fit(flat, train.remaining_s, sample_weight=weights)
    return models, prep


def fit_gru(train, seqs, fold, epochs=20, final_epochs=None):
    keras = keras_api()
    keras.backend.clear_session()
    inner = inner_partition(train, fold) if final_epochs is None else np.zeros(len(train), bool)
    fit = train.loc[~inner]
    fit_seq = [s for s, held in zip(seqs, inner) if not held]
    prep = SequenceTransform.fit(fit_seq, fit.loc[:, FEATURES], longest_indices(fit))
    data = prep.transform(fit_seq, fit.loc[:, FEATURES])
    weights = lap_weights(fit)
    y = fit.remaining_s.to_numpy(float)
    mean = float(np.average(y, weights=weights))
    scale = max(1., float(np.sqrt(np.average((y-mean)**2, weights=weights))))
    model = make_gru(42+fold)
    options = {}
    if final_epochs is None:
        val = train.loc[inner]
        val_seq = [s for s, held in zip(seqs, inner) if held]
        options = dict(validation_data=(prep.transform(val_seq, val.loc[:, FEATURES]),
            (val.remaining_s.to_numpy()-mean)/scale, lap_weights(val)),
            callbacks=[keras.callbacks.EarlyStopping(monitor='val_loss', patience=4, restore_best_weights=True)])
    start = time.perf_counter()
    history = model.fit(data, (y-mean)/scale, sample_weight=weights, batch_size=64,
                        epochs=final_epochs or epochs, verbose=2, shuffle=True, **options).history
    duration = time.perf_counter()-start
    best = int(np.argmin(history['val_loss'])+1) if final_epochs is None else final_epochs
    info = dict(fold=fold, epochs_ran=len(history['loss']), best_epoch=best, seconds=duration,
        parameter_count=model.count_params(), process_peak_working_set_bytes=working_memory(),
        fit_laps=fit.lap_uid.nunique(), fit_blocks=fit.physical_session_id.nunique(),
        inner_validation_laps=int(train.loc[inner].lap_uid.nunique()),
        inner_validation_blocks=sorted(train.loc[inner].physical_session_id.unique()),
        fit_ids=sorted(fit.lap_uid.unique()), mean_remaining_s=mean, scale_remaining_s=scale,
        padded_fit_tensor_bytes=sum(a.nbytes for a in data.values()), padded_steps=int(data['telemetry'].shape[1]),
        backend=keras.backend.backend(), history={k:list(map(float, v)) for k, v in history.items()})
    return model, prep, mean, scale, info


def save_fold(models, prep, gru, gru_prep, mean, scale, train, allowed_ids, binding, fold, root=MODEL_ROOT):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    name = 'dense-v080-'+str(fold)
    gru_path = root/(name+'.keras')
    gru.save(gru_path)
    binding = {**binding, 'fold':fold, 'gru_sha256':file_sha(gru_path)}
    # Preprocessor for GRU is separate because inner validation cannot fit it.
    models = {**models, 'GRU-preprocessor':gru_prep}
    bundle = DenseBundle(binding['base_corpus_id'], 'Experimental v080 recording-block OOF replay',
        tuple(FEATURES), models, 'SVR-REMAINING', pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame(),
        [], pd.DataFrame(), DOMAIN, binding, prep, mean, scale,
        train[['lap_uid', 'target_s']].drop_duplicates('lap_uid').target_s.to_numpy(), tuple(allowed_ids))
    LocalArtifactStore(root).save(bundle, name)
    return bundle


def load_fold(binding, fold, root=MODEL_ROOT, with_gru=False):
    root = Path(root)
    bundle = LocalArtifactStore(root).load('dense-v080-'+str(fold))
    if not isinstance(bundle, DenseBundle) or tuple(bundle.domain) != DOMAIN:
        raise ValueError('Incompatible experimental bundle')
    if any(bundle.compatibility.get(k) != v for k, v in binding.items()) or bundle.compatibility['fold'] != fold:
        raise ValueError('Experimental corpus/protocol/feature binding differs')
    gru = None
    if with_gru:
        path = root/('dense-v080-'+str(fold)+'.keras')
        # The expected digest is in the HMAC-verified bundle, not an unsigned sidecar.
        if file_sha(path) != bundle.compatibility['gru_sha256']:
            raise ValueError('Untrusted Keras model bytes')
        gru = keras_api().models.load_model(path, safe_mode=True, compile=False)
    return bundle, gru


def batch_predictions(bundle, table, seqs, gru=None):
    context = table.loc[:, FEATURES]
    elapsed = table.observed_elapsed_s.to_numpy(float)
    values = {}
    for name in ('SVR-SPARSE', 'SVR-DENSE'):
        prediction = bundle.models[name].predict(context)
        values[name] = (prediction, prediction, prediction-elapsed, np.zeros(len(table), int))
    raw = bundle.models['SVR-REMAINING'].predict(context)
    values['SVR-REMAINING'] = (reconstruct(raw, elapsed), elapsed+raw, raw, np.zeros(len(table), int))
    raw = bundle.models['RIDGE-ORDERED'].predict(bundle.sequence_transform.flat(seqs, context))
    values['RIDGE-ORDERED'] = (reconstruct(raw, elapsed), elapsed+raw, raw, np.zeros(len(table), int))
    if gru is not None:
        raw = raw_gru(gru, bundle.models['GRU-preprocessor'].transform(seqs, context),
                      bundle.remaining_mean, bundle.remaining_scale)
        values['GRU'] = (reconstruct(raw, elapsed), elapsed+raw, raw, np.zeros(len(table), int))
    reference, support = remaining_reference(bundle.training_targets, elapsed)
    values['REMAINING-REFERENCE'] = (reference, reference, reference-elapsed, support)
    median = np.full(len(table), np.median(bundle.training_targets))
    values['MEDIAN'] = (median, median, median-elapsed, np.full(len(table), len(bundle.training_targets)))
    output = []
    for model, (prediction, raw_final, raw_remaining, support) in values.items():
        output.append(table[['lap_uid', 'physical_session_id', 'checkpoint_s', 'observed_elapsed_s',
            'target_s', 'pace_band', 'stage', 'fold']].assign(model=model, prediction_s=prediction,
            raw_final_s=raw_final, raw_remaining_s=raw_remaining, reference_support=support))
    return pd.concat(output, ignore_index=True)


def predict(source, checkpoint, bundle, model, gru=None):
    """Target-free replay. Same builders/weights/inverse as batch evaluation."""
    if tuple(source.domain) != DOMAIN or tuple(bundle.domain) != DOMAIN or source.lap_uid not in bundle.allowed_ids:
        raise ValueError('Source outside this development fold')
    if tuple(bundle.feature_names) != tuple(FEATURES) or checkpoint > 600.:
        raise ValueError('Experimental feature/horizon contract differs')
    if bundle.compatibility.get('version') != VERSION or bundle.compatibility.get('protocol_sha256') != file_sha(PROTOCOL):
        raise ValueError('Experimental protocol changed')
    features, quality = prefix_features(source, checkpoint)
    context = pd.DataFrame([features], columns=FEATURES)
    elapsed = quality['observed_elapsed_s']
    support = None
    if model in ('SVR-SPARSE', 'SVR-DENSE'):
        value = float(bundle.models[model].predict(context)[0])
        raw = value-elapsed
    elif model == 'SVR-REMAINING':
        raw = float(bundle.models[model].predict(context)[0])
        value = float(reconstruct(raw, elapsed))
    elif model in ('RIDGE-ORDERED', 'GRU'):
        seq, _ = sequence(source, checkpoint)
        if model == 'RIDGE-ORDERED':
            raw = float(bundle.models[model].predict(bundle.sequence_transform.flat([seq], context))[0])
        else:
            if gru is None:
                raise ValueError('Verified GRU artifact required')
            data = bundle.models['GRU-preprocessor'].transform([seq], context)
            raw = float(raw_gru(gru, data, bundle.remaining_mean, bundle.remaining_scale)[0])
        value = float(reconstruct(raw, elapsed))
    elif model in ('REMAINING-REFERENCE', 'MEDIAN'):
        if model == 'MEDIAN':
            value = float(np.median(bundle.training_targets))
        else:
            result, count = remaining_reference(bundle.training_targets, [elapsed])
            value, support = float(result[0]), int(count[0])
        raw = value-elapsed
    else:
        raise ValueError('Unknown experimental model')
    return dict(checkpoint_s=float(checkpoint), observed_elapsed_s=elapsed, prediction_s=value,
                raw_remaining_s=raw, projected=bool(model in ('SVR-REMAINING', 'RIDGE-ORDERED', 'GRU') and raw < 0),
                reference_support=support, model=model)


def run(corpus, output=ROOT/'docs', model_root=MODEL_ROOT):
    output, model_root = Path(output), Path(model_root)
    dev = development_pool(corpus, pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv'))
    binding = identity(corpus, dev)
    result_path = output/'ML_RESULTS_V080.json'
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if result['compatibility'] != binding:
            raise ValueError('Frozen experiment identity differs')
        for name, sha in result['evidence_sha256'].items():
            if file_sha(output/name) != sha:
                raise ValueError('Frozen v080 evidence modified: '+name)
        print('Verified frozen v080 results; no fitting or rescoring.', flush=True)
        return result
    folds = group_folds(dev)
    pd.testing.assert_frame_equal(folds, pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V072.csv'))
    dump(output/'DEVELOPMENT_FREEZE_V080.json', dict(compatibility=binding, folds=folds.to_dict('records'),
        inner_protocol='Four outer-training blocks, seed420+fold; no outer early stopping', historical_test_evaluations=0))
    print('Building causal observations for 169 development laps only.', flush=True)
    table, seqs = observation_table(dev)
    table = table.merge(folds[['lap_uid', 'fold']], on='lap_uid', validate='many_to_one')
    table_write(output/'DEVELOPMENT_FEATURES_V080.csv', table)
    predictions, histories = [], []
    old = pd.read_csv(ROOT/'docs/DEVELOPMENT_PREDICTIONS_V072.csv').query("variant=='F0'")
    deviations = []
    for fold in range(5):
        is_train = table.fold != fold
        train, held = table.loc[is_train], table.loc[~is_train]
        train_seq = [s for s, yes in zip(seqs, is_train) if yes]
        held_seq = [s for s, yes in zip(seqs, is_train) if not yes]
        print(f'Fold {fold}: {train.lap_uid.nunique()} fit / {held.lap_uid.nunique()} held-out laps.', flush=True)
        started = time.perf_counter()
        models, prep = fit_classical(train, train_seq)
        classical_seconds = time.perf_counter()-started
        gru, gp, mean, scale, info = fit_gru(train, train_seq, fold)
        info['classical_seconds'] = classical_seconds
        bundle = save_fold(models, prep, gru, gp, mean, scale, train, held.lap_uid.unique(), binding, fold, model_root)
        pred = batch_predictions(bundle, held, held_seq, gru)
        fixed = pred[(pred.model == 'SVR-SPARSE') & pred.checkpoint_s.isin(CHECKPOINTS)]
        matched = fixed.merge(old, on=['lap_uid', 'checkpoint_s'], suffixes=('_new', '_v072'), validate='one_to_one')
        deviation = float(np.abs(matched.prediction_s_new-matched.prediction_s_v072).max())
        if len(matched) != len(held.lap_uid.unique())*5 or deviation > 1e-9:
            raise AssertionError('Sparse learned reference differs from v072')
        deviations.append(deviation)
        predictions.append(pred)
        histories.append(info)
        table_write(output/f'DEVELOPMENT_FOLD_{fold}_V080.csv', pred)
        dump(output/'GRU_HISTORY_V080.json', histories)
    predictions = pd.concat(predictions, ignore_index=True)
    table_write(output/'DEVELOPMENT_PREDICTIONS_V080.csv', predictions)
    overall, details, consistency = summarize(predictions)
    for name, frame in (('OVERALL', overall), ('DETAILS', details), ('CONSISTENCY', consistency)):
        table_write(output/f'DEVELOPMENT_{name}_V080.csv', frame)
    # All-development research fit is separate from the OOF artifacts used by UI.
    final_epochs = max(1, int(np.median([h['best_epoch'] for h in histories])))
    models, prep = fit_classical(table, seqs)
    gru, gp, mean, scale, info = fit_gru(table, seqs, 5, final_epochs=final_epochs)
    save_fold(models, prep, gru, gp, mean, scale, table, table.lap_uid.unique(), binding, 'research', model_root)
    dump(output/'GRU_RESEARCH_FIT_V080.json', info)
    # Fixed production artifact: only original validation laps, never historical test.
    from .barcelona_experiment_v071 import load_bundle as load_reference
    reference = load_reference(corpus)
    val_ids = set(reference.split.query("partition=='validation'").lap_uid)
    fixed = table[table.lap_uid.isin(val_ids)].copy()
    fixed['prediction_s'] = reference.models['SVR'].predict(fixed.loc[:, FEATURES])
    table_write(output/'FIXED_REFERENCE_TRAJECTORIES_V080.csv', fixed[['lap_uid', 'physical_session_id', 'checkpoint_s', 'observed_elapsed_s', 'target_s', 'prediction_s']])
    evidence = [*output.glob('DEVELOPMENT_*_V080.csv'), output/'DEVELOPMENT_FREEZE_V080.json',
                output/'GRU_HISTORY_V080.json', output/'GRU_RESEARCH_FIT_V080.json',
                output/'FIXED_REFERENCE_TRAJECTORIES_V080.csv', PROTOCOL,
                output/'PROGRESS_SOURCE_AUDIT_V080.csv', output/'PROGRESS_STATUS_V080.json']
    result = dict(compatibility=binding, development_laps=len(dev.laps), development_blocks=40,
        checkpoints=len(table), min_checkpoints_per_lap=int(table.groupby('lap_uid').size().min()),
        max_checkpoints_per_lap=int(table.groupby('lap_uid').size().max()),
        candidates=list(CANDIDATES), historical_test_evaluations=0, original_test_evaluations=1,
        sparse_reference_max_deviation_s=max(deviations), final_research_epochs=final_epochs,
        operational_reference='Unchanged SVR v071', evidence_sha256={p.name:file_sha(p) for p in evidence},
        overall=overall.replace({np.nan:None}).to_dict('records'))
    dump(result_path, result)
    return result


def rebuild_artifacts(corpus, model_root=MODEL_ROOT):
    """Explicit installation recovery: TRAIN/inner validation only, no OOF score."""
    if not (ROOT/'docs/ML_RESULTS_V080.json').exists():
        raise ValueError('Reconstruction requires completed frozen v080 evidence')
    result = run(corpus)  # Verifies and returns before feature generation/fitting.
    dev = development_pool(corpus, pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv'))
    table, seqs = observation_table(dev)
    folds = group_folds(dev)
    table = table.merge(folds[['lap_uid', 'fold']], on='lap_uid', validate='many_to_one')
    history = json.loads((ROOT/'docs/GRU_HISTORY_V080.json').read_text(encoding='utf-8'))
    rebuilt = []
    for fold in [0, 1, 2, 3, 4, 'research']:
        name = Path(model_root)/('dense-v080-'+str(fold))
        if name.with_suffix('.joblib').exists() and name.with_suffix('.keras').exists():
            # Verify both signatures/native bytes without deserializing Keras.
            installed, _ = load_fold(result['compatibility'], fold, root=model_root)
            if file_sha(name.with_suffix('.keras')) != installed.compatibility['gru_sha256']:
                raise ValueError('Existing GRU artifact differs; refusing silent reconstruction')
            continue
        is_train = np.ones(len(table), bool) if fold == 'research' else (table.fold != fold).to_numpy()
        train = table.loc[is_train]
        train_seq = [s for s, yes in zip(seqs, is_train) if yes]
        models, prep = fit_classical(train, train_seq)
        if fold == 'research':
            gru, gp, mean, scale, _ = fit_gru(train, train_seq, 5, final_epochs=result['final_research_epochs'])
            allowed = table.lap_uid.unique()
        else:
            best = next(h['best_epoch'] for h in history if h['fold'] == fold)
            gru, gp, mean, scale, _ = fit_gru(train, train_seq, fold, epochs=best)
            allowed = table.loc[~is_train].lap_uid.unique()
        save_fold(models, prep, gru, gp, mean, scale, train, allowed, result['compatibility'], fold, model_root)
        rebuilt.append(fold)
    print('Restored missing artifacts without outer/historical predictions: '+str(rebuilt), flush=True)
    return rebuilt
