import json

import numpy as np
import pandas as pd
import pytest

from motorsport.ml.cadence_v081 import matched_penalty_weights, fit_one_second
from motorsport.ml.features import FEATURES
from motorsport.ml.barcelona_recovery import ROOT


def test_per_lap_and_total_loss_mass_match_original_dense_training():
    reference = pd.DataFrame({'lap_uid':['a']*3+['b']*5})
    dense = pd.DataFrame({'lap_uid':['a']*17+['b']*29})
    weights = matched_penalty_weights(dense, reference)
    assert weights.sum() == pytest.approx(len(reference))
    masses = dense.assign(weight=weights).groupby('lap_uid').weight.sum()
    np.testing.assert_allclose(masses, [4., 4.])
    assert weights.mean() != pytest.approx(1.)
    with pytest.raises(ValueError, match='populations'):
        matched_penalty_weights(dense[dense.lap_uid == 'a'], reference)


def test_preprocessing_fits_only_supplied_training_rows():
    train = pd.DataFrame({name:np.arange(1., 13.) for name in FEATURES})
    train['lap_uid'] = ['a']*6+['b']*6
    train['target_s'] = [100.]*6+[130.]*6
    reference = train.iloc[[0, 1, 6, 7]]
    model, info = fit_one_second(train, reference)
    np.testing.assert_allclose(model.named_steps['scaler'].mean_, np.full(len(FEATURES), 6.5))
    before = model.named_steps['imputer'].statistics_.copy()
    model.predict(pd.DataFrame({name:[1e9] for name in FEATURES}))
    np.testing.assert_array_equal(before, model.named_steps['imputer'].statistics_)
    assert info['candidate_total_weight'] == pytest.approx(info['reference_total_weight'])


def test_executed_development_evidence_folds_and_shared_predictions():
    path = ROOT/'docs/ML_RESULTS_V081.json'
    if not path.exists():
        pytest.skip('v081 offline measurement not yet installed')
    from motorsport.ml.barcelona_recovery import file_sha
    r = json.loads(path.read_text(encoding='utf-8'))
    assert r['development_laps'] == 169 and r['development_blocks'] == 40
    assert r['validated_laps_preserved'] == 205 and r['historical_test_evaluations'] == 0
    assert r['folds_sha256'] == file_sha(ROOT/'docs/DEVELOPMENT_FOLDS_V072.csv')
    assert r['frozen_v080_max_deviation_s'] < 1e-9
    assert max(v for d in r['cadence_shared_max_deviation_s'].values() for v in d.values()) < 1e-9
    for fit in r['training']:
        assert not set(fit['training_ids']) & set(fit['held_ids'])
        assert not set(fit['training_blocks']) & set(fit['held_blocks'])
        assert len(fit['training_ids'])+len(fit['held_ids']) == 169
        assert fit['candidate_total_weight'] == pytest.approx(fit['reference_total_weight'])
    for name, sha in r['evidence_sha256'].items():
        assert file_sha(ROOT/name) == sha


def test_current_recorded_replay_matches_frozen_moving_stop_and_long_lap_rows():
    from motorsport.ml.barcelona_recovery import load_corpus
    from motorsport.ml.dense_experiment_v080 import load_fold
    from motorsport.ml.replay_v081 import replay
    r = json.loads((ROOT/'docs/ML_RESULTS_V081.json').read_text(encoding='utf-8'))
    recorded = pd.read_csv(ROOT/'artifacts/barcelona_v081/observations-1s.csv')
    corpus, _ = load_corpus()
    sources = {lap.lap_uid:lap for lap in corpus.laps}
    ids = [recorded.lap_uid.iloc[0], recorded.loc[recorded.driving_state=='stationary', 'lap_uid'].iloc[0],
           recorded.loc[recorded.observed_elapsed_s.idxmax(), 'lap_uid']]
    for uid in set(ids):
        expected = recorded[recorded.lap_uid==uid]
        bundle, _ = load_fold(r['compatibility'], int(expected.fold.iloc[0]))
        rows, _ = replay(sources[uid], bundle)
        np.testing.assert_allclose(rows[['raw_prediction_s','bounded_prediction_s','stop_aware_prediction_s']],
            expected[['raw_prediction_s','bounded_prediction_s','stop_aware_prediction_s']], rtol=0, atol=1e-9)
        assert rows.driving_state.tolist() == expected.driving_state.tolist()
