"""Il test di training e' indipendente da FastF1 e dallo Streamlit server."""
import numpy as np
from motorsport_prediction.features import build_dataset, ALL_FEATURES
from motorsport_prediction.model import fit_model, replay_predictions
from test_features import lap_record


def test_training_and_replay_smoke():
    ref = lap_record(uid='FP3:AAA:1', code='FP3')
    laps = []
    for i in range(10):
        record = lap_record(uid=f'FP1:AAA:{i}', speed=178 + i, lap_time=109 - i*0.15)
        laps.append(record)
    dataset = build_dataset(laps, {'AAA': ref})
    fitted = fit_model(dataset, epochs=2)
    assert fitted.metrics['train_laps'] + fitted.metrics['validation_laps'] == 10
    assert fitted.metrics['validation_snapshots'] > 0
    q = lap_record(uid='Q:AAA:20', speed=189, lap_time=106.7, code='Q')
    result = replay_predictions(q, ref, fitted)
    assert len(result) >= 2
    assert np.isfinite(result['prediction_s']).all()
    assert result.iloc[-1]['prediction_s'] == q.lap_time_s
    assert set(ALL_FEATURES).issubset(dataset.columns)