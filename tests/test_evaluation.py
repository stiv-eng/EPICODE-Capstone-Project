import numpy as np
from motorsport_prediction.features import build_dataset
from motorsport_prediction.model import fit_model, evaluate_qualifying, summarize_qualifying
from test_features import lap_record


def test_qualifying_evaluation_is_out_of_training():
    ref = lap_record(uid='FP3:AAA:8', code='FP3')
    train_laps = [lap_record(uid=f'FP1:AAA:{i}', speed=176+i, lap_time=110-i*.1)
                  for i in range(10)]
    model = fit_model(build_dataset(train_laps, {'AAA': ref}), epochs=1)
    q = lap_record(uid='Q:AAA:1', speed=182, lap_time=108, code='Q')
    evaluation = evaluate_qualifying([q], {'AAA': ref}, model)
    assert set(evaluation['session']) == {'Q'}
    assert len(evaluation) >= 3
    assert not evaluation['is_finish'].any()
    assert np.isfinite(evaluation[['prediction_s','baseline_s','actual_s']]).all().all()
    metrics, laps, stage = summarize_qualifying(evaluation)
    assert metrics['laps'] == 1
    assert laps['snapshots'].iloc[0] == len(evaluation)
    assert not stage.empty
    assert model.validation_predictions['session'].eq('FP1').all()