"""Test offline della pipeline storica SVR."""
import numpy as np
import pandas as pd
from motorsport_ui.svr import FEATURES, fit_svr


def test_svr_smoke():
    rng = np.random.default_rng(7)
    size = 24
    data = pd.DataFrame({
        'Compound': rng.choice(['SOFT', 'MEDIUM'], size),
        'SessionType': rng.choice(['Q', 'R'], size),
        'LapNumber': np.arange(1, size + 1),
        'AvgSpeed': rng.normal(205, 4, size),
        'ThrottleMean': rng.normal(70, 6, size),
        'BrakeTime': rng.uniform(12, 18, size),
        'LapTime': rng.normal(90, 2, size),
    })
    model, predictions, scores = fit_svr(data)
    assert len(predictions) == 6
    assert np.isfinite(scores['MAE_s'])
    assert set(FEATURES).issubset(data.columns)
