from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from motorsport.ml.dataset import ReplayLap
from motorsport.ml.features import prefix_features
from motorsport.ml.progression_v080 import checkpoints, remaining_target, reconstruct, remaining_reference
from motorsport.ml.barcelona_recovery import DOMAIN


@pytest.fixture
def source():
    t = np.arange(0., 80.001, .02)
    frame = pd.DataFrame(dict(lap_elapsed_s=t, speed_kmh=140+10*np.sin(t), throttle_pct=50+20*np.cos(t),
        brake_pct=10+5*np.sin(t), rpm=5000+100*t, gear=np.full(len(t), 3.), steering=np.sin(t)*20))
    return ReplayLap('dev:lap:1', 'recording-a', 'unknown', DOMAIN, (0,), frame, steering_unit='deg')


def test_dense_scheduling_is_configurable_and_compatible(source):
    assert checkpoints(source) == tuple(np.arange(5., 81., 5.))
    assert checkpoints(source, 10.) == tuple(np.arange(10., 81., 10.))
    assert checkpoints(source, compatibility=True) == (10., 20., 30., 45., 60.)
    for bad in (0., -1., float('nan')):
        with pytest.raises(ValueError):
            checkpoints(source, bad)


def test_schedule_and_features_unchanged_when_future_mutates(source):
    frame = source.frame.copy()
    frame.loc[frame.lap_elapsed_s > 35, ['lap_elapsed_s', 'speed_kmh']] = [float('nan'), 499.]
    changed = replace(source, frame=frame)
    assert checkpoints(changed, horizon_s=30.) == checkpoints(source, horizon_s=30.)
    assert prefix_features(changed, 30.) == prefix_features(source, 30.)


@pytest.mark.parametrize('defect', ['gap', 'backward', 'missing'])
def test_schedule_stops_at_source_discontinuity(source, defect):
    frame = source.frame.copy()
    pos = frame.index[frame.lap_elapsed_s > 32][0]
    if defect == 'gap':
        frame = frame.drop(index=range(pos, pos+25)).reset_index(drop=True)
    elif defect == 'backward':
        frame.loc[pos, 'lap_elapsed_s'] = 1.
    else:
        frame.loc[pos, 'lap_elapsed_s'] = np.nan
    assert checkpoints(replace(source, frame=frame)) == (5., 10., 15., 20., 25., 30.)


def test_real_source_cutoff_never_interpolates(source):
    f, q = prefix_features(source, 10.013)
    assert q['observed_elapsed_s'] == 10.
    assert f['speed_current_kmh'] == source.frame.loc[source.frame.lap_elapsed_s == 10., 'speed_kmh'].iloc[0]
    assert remaining_target(100., q['observed_elapsed_s']) == 90.
    np.testing.assert_allclose(reconstruct([-4., 15.], [10., 20.]), [10., 35.])
    with pytest.raises(ValueError):
        remaining_target(10., 20.)


def test_conditional_reference_uses_only_training_targets():
    p, n = remaining_reference([100., 120., 200.], [50., 110., 210.])
    np.testing.assert_allclose(p, [120., 160., 210.])
    assert n.tolist() == [3, 2, 0]
