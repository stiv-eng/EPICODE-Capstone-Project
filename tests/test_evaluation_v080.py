import numpy as np
import pandas as pd

from motorsport.ml.evaluation_v080 import lap_weights, metrics, summarize
from motorsport.ml.dense_experiment_v080 import inner_partition


def rows():
    return pd.DataFrame(dict(lap_uid=['a', 'b', 'b', 'b'], physical_session_id=['x', 'y', 'y', 'y'],
        target_s=[100., 200., 200., 200.], prediction_s=[110., 220., 220., 220.],
        raw_final_s=[110., 220., 220., 220.], raw_remaining_s=[105., 215., 210., 205.],
        observed_elapsed_s=[5., 5., 10., 15.], checkpoint_s=[5., 5., 10., 15.],
        pace_band=['fast', 'slow', 'slow', 'slow'], stage=['early']*4, fold=[0]*4, model=['mock']*4))


def test_lap_balance_prevents_long_lap_snapshot_dominance():
    r = rows()
    w = lap_weights(r)
    np.testing.assert_allclose(w[0], w[1:].sum(), atol=1e-12)
    result = metrics(r)
    assert result['mae_s'] == 15. and result['recording_macro_mae_s'] == 15.
    assert result['bias_s'] == 15.
    assert result['laps'] == 2 and result['snapshots'] == 4


def test_checkpoint_and_pace_reports_keep_survivor_counts():
    overall, details, _ = summarize(rows())
    checkpoint = details[details.dimension == 'checkpoint_s'].set_index('value')
    assert checkpoint.loc[5., 'laps'] == 2 and checkpoint.loc[15., 'laps'] == 1
    bands = details[details.dimension == 'pace_band'].set_index('value')
    assert bands.loc['slow', 'mae_s'] == 20.
    assert overall.query("subset=='last_scheduled'").iloc[0].mae_s == 15.


def test_direct_negative_remaining_is_reported_without_claiming_projection():
    r = rows()
    r['raw_remaining_s'] = -5.
    r['model'] = 'SVR-SPARSE'
    assert metrics(r)['negative_raw_remaining'] == len(r)
    assert metrics(r)['projected_fraction'] == 0.
    r['model'] = 'SVR-REMAINING'
    assert metrics(r)['projected_fraction'] == 1.


def test_inner_groups_reproducible_and_disjoint():
    table = pd.DataFrame({'physical_session_id':np.repeat([f'g{i}' for i in range(32)], 3)})
    a = inner_partition(table, 0)
    assert a.sum() == 12
    assert not set(table.loc[a].physical_session_id) & set(table.loc[~a].physical_session_id)
    np.testing.assert_array_equal(inner_partition(table, 0), a)


def test_original_frozen_folds_are_reused_without_historical_ids():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    a = pd.read_csv(root/'docs/DEVELOPMENT_FOLDS_V080.csv')
    b = pd.read_csv(root/'docs/DEVELOPMENT_FOLDS_V072.csv')
    pd.testing.assert_frame_equal(a, b)
    historical = pd.read_csv(root/'docs/BARCELONA_SPLIT_V071.csv').query("partition=='test'")
    assert not set(a.lap_uid) & set(historical.lap_uid)
