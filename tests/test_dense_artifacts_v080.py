from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motorsport.ml.barcelona_recovery import ROOT
from motorsport.ml.dense_experiment_v080 import load_fold, predict, batch_predictions, CANDIDATES
from motorsport.ml.features import prefix_features
from motorsport.ml.sequences_v080 import sequence


@pytest.fixture(scope='module')
def installed():
    path = ROOT/'docs/ML_RESULTS_V080.json'
    if not path.exists():
        pytest.skip('Executed local v080 experiment not installed')
    from motorsport.ml.barcelona_recovery import load_corpus
    corpus, _ = load_corpus()
    result = json.loads(path.read_text(encoding='utf-8'))
    folds = pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V080.csv')
    return corpus, result, folds


def test_executed_comparison_population_and_frozen_sparse_reference(installed):
    corpus, result, folds = installed
    pred = pd.read_csv(ROOT/'docs/DEVELOPMENT_PREDICTIONS_V080.csv')
    assert len(corpus.laps) == 205 and result['development_laps'] == 169
    assert result['historical_test_evaluations'] == 0 and result['original_test_evaluations'] == 1
    assert result['sparse_reference_max_deviation_s'] < 1e-9
    assert set(pred.model) == set(CANDIDATES)
    keys = ['lap_uid', 'checkpoint_s', 'observed_elapsed_s', 'target_s', 'fold']
    reference = pred.query("model=='SVR-SPARSE'")[keys].reset_index(drop=True)
    for _, table in pred.groupby('model', sort=False):
        pd.testing.assert_frame_equal(table[keys].reset_index(drop=True), reference)
    assert reference.lap_uid.nunique() == 169
    assert reference.checkpoint_s.max() > 200
    for name, digest in result['evidence_sha256'].items():
        from motorsport.ml.barcelona_recovery import file_sha
        assert file_sha(ROOT/'docs'/name) == digest


def test_saved_models_batch_replay_and_future_invariance(installed):
    corpus, result, folds = installed
    source = next(lap for lap in corpus.laps if lap.lap_uid in set(folds.query('fold==0').lap_uid))
    bundle, gru = load_fold(result['compatibility'], 0, with_gru=True)
    features, _ = prefix_features(source, 65.)
    seq, _ = sequence(source, 65.)
    row = dict(lap_uid=source.lap_uid, physical_session_id=source.physical_session_id,
        **features, target_s=-999., pace_band='poison', stage='poison', fold=0)
    batch = batch_predictions(bundle, pd.DataFrame([row]), [seq], gru).set_index('model')
    changed = source.frame.copy()
    changed.loc[changed.lap_elapsed_s > 65., ['speed_kmh', 'rpm']] = 0.
    for model in CANDIDATES:
        replay = predict(source, 65., bundle, model, gru)
        mutated = predict(replace(source, frame=changed), 65., bundle, model, gru)
        np.testing.assert_allclose(replay['prediction_s'], batch.loc[model, 'prediction_s'], atol=1e-4)
        assert replay == mutated
    for model in ('SVR-REMAINING', 'RIDGE-ORDERED', 'GRU'):
        assert predict(source, 65., bundle, model, gru)['prediction_s'] >= features['observed_elapsed_s']
    historical = next(lap for lap in corpus.laps if lap.lap_uid not in set(folds.lap_uid))
    with pytest.raises(ValueError, match='outside'):
        predict(historical, 30., bundle, 'SVR-REMAINING')
    with pytest.raises(ValueError, match='outside'):
        predict(replace(source, domain=('other', 'car')), 30., bundle, 'GRU', gru)


def test_early_stopping_never_uses_outer_blocks(installed):
    _, _, folds = installed
    histories = json.loads((ROOT/'docs/GRU_HISTORY_V080.json').read_text(encoding='utf-8'))
    for history in histories:
        fold = history['fold']
        outer = folds.query('fold==@fold')
        assert not set(history['inner_validation_blocks']) & set(outer.physical_session_id)
        assert not set(history['fit_ids']) & set(outer.lap_uid)
        assert history['epochs_ran'] <= 20 and history['parameter_count'] < 3000
        assert history['seconds'] > 0 and history['process_peak_working_set_bytes'] > 0


def test_keras_digest_is_checked_before_deserializing(installed, tmp_path, monkeypatch):
    import shutil
    import motorsport.ml.dense_experiment_v080 as module
    _, result, _ = installed
    for name in ['.local-signing-key', 'dense-v080-0.joblib', 'dense-v080-0.json', 'dense-v080-0.keras']:
        shutil.copyfile(module.MODEL_ROOT/name, tmp_path/name)
    (tmp_path/'dense-v080-0.keras').write_bytes(b'not an authentic Keras model')
    monkeypatch.setattr(module, 'keras_api', lambda:pytest.fail('Deserialization must not run before integrity verification'))
    with pytest.raises(ValueError, match='Untrusted'):
        load_fold(result['compatibility'], 0, tmp_path, with_gru=True)


def test_rerun_reuses_frozen_results_without_model_fit(installed, monkeypatch):
    import motorsport.ml.dense_experiment_v080 as module
    corpus, result, _ = installed
    monkeypatch.setattr(module, 'observation_table', lambda *a:pytest.fail('Frozen rerun must not generate or fit snapshots'))
    assert module.run(corpus)['evidence_sha256'] == result['evidence_sha256']
