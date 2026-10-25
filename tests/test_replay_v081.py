from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from motorsport.ml.dataset import ReplayLap
from motorsport.ml.features import FEATURES, prefix_features
from motorsport.ml.barcelona_recovery import DOMAIN, file_sha
from motorsport.ml.dense_experiment_v080 import PROTOCOL
from motorsport.ml.progression_v080 import VERSION
from motorsport.ml.replay_v081 import (PrefixIndex, StopDetector, ReplayEngine, replay,
    physical_bound, advance_checkpoint)


class ConstantModel:
    def predict(self, frame):
        assert tuple(frame.columns) == FEATURES
        return np.full(len(frame), 110.)


@pytest.fixture
def source():
    t = np.round(np.arange(0., 40.001, .02), 8)
    return ReplayLap('dev:1', 'block:1', 'unknown', DOMAIN, (0,), pd.DataFrame(dict(
        lap_elapsed_s=t, speed_kmh=120+10*np.sin(t), throttle_pct=50+20*np.cos(t),
        brake_pct=10+5*np.sin(t), rpm=5000+100*t, gear=3., steering=20*np.sin(t))), steering_unit='deg')


@pytest.fixture
def bundle(source):
    return SimpleNamespace(domain=DOMAIN, allowed_ids=(source.lap_uid,), feature_names=FEATURES,
        compatibility=dict(version=VERSION, protocol_sha256=file_sha(PROTOCOL)), models={'SVR-DENSE':ConstantModel()})


def stopped(source, intervals=((10., 20.),)):
    f = source.frame.copy()
    for a, b in intervals:
        f.loc[f.lap_elapsed_s.between(a, b, inclusive='left'), 'speed_kmh'] = 0.
    return replace(source, frame=f)


@pytest.mark.parametrize('cadence', [5., 1., .5])
def test_schedule_uses_actual_source_cutoffs_and_fixed_elapsed_grid(source, cadence):
    idx = PrefixIndex(source)
    assert idx.schedule(cadence) == tuple(np.arange(cadence, 40.001, cadence))
    assert idx.features(10.013)['observed_elapsed_s'] == 10.
    assert idx.features(10.013)['speed_current_kmh'] == source.frame.loc[500, 'speed_kmh']


def test_cumulative_features_match_frozen_feature_builder(source):
    f = source.frame.copy()
    f.loc[200, 'speed_kmh'] = np.nan
    source = replace(source, frame=f)
    idx = PrefixIndex(source)
    for t in (.5, 5., 10.013, 30., 40.):
        expected, _ = prefix_features(source, t)
        np.testing.assert_allclose(list(idx.features(t).values()), list(expected.values()), atol=1e-9, rtol=1e-12)


@pytest.mark.parametrize('defect', ['gap', 'backward', 'missing'])
def test_clock_discontinuity_quarantines_tail_without_false_stop(source, bundle, defect):
    f = stopped(source).frame.copy()
    pos = f.index[f.lap_elapsed_s >= 10.5][0]
    if defect == 'gap':
        f = f.drop(index=range(pos, pos+25))
    elif defect == 'backward':
        f.loc[pos, 'lap_elapsed_s'] = 1.
    else:
        f.loc[pos, 'lap_elapsed_s'] = np.nan
    rows, engine = replay(replace(source, frame=f), bundle)
    assert rows.checkpoint_s.max() == 10.
    assert engine.index.clock_interrupted and not engine.events
    assert not (rows.driving_state == 'stationary').any()


def test_shared_observations_are_cadence_invariant_including_stop_and_resume(source, bundle):
    source = stopped(source)
    tables = [replay(source, bundle, c)[0].set_index('checkpoint_s') for c in (5., 1., .5)]
    for table in tables[1:]:
        pd.testing.assert_frame_equal(tables[0], table.loc[tables[0].index])


def test_future_mutation_target_and_progress_cannot_change_prefix(source, bundle):
    original, _ = replay(stopped(source), bundle, .5, horizon_s=15.)
    f = stopped(source).frame.copy()
    f.loc[f.lap_elapsed_s > 15., ['lap_elapsed_s', 'speed_kmh', 'rpm']] = [np.nan, 499., 0.]
    f['target_s'], f['progress'], f['distance_pct'] = -999., 1., .999
    changed, _ = replay(replace(source, frame=f), bundle, .5, horizon_s=15.)
    pd.testing.assert_frame_equal(original, changed)


def test_stop_adds_elapsed_stationary_seconds_and_resumes_causally(source, bundle):
    rows, engine = replay(stopped(source), bundle, .5)
    rows = rows.set_index('checkpoint_s')
    assert rows.loc[10., 'driving_state'] == 'uncertain'
    assert rows.loc[11., 'driving_state'] == 'stationary'
    assert rows.loc[16., 'stop_aware_prediction_s']-rows.loc[11., 'stop_aware_prediction_s'] == pytest.approx(5.)
    assert rows.loc[11., 'raw_prediction_s'] == 110.
    assert rows.loc[11., 'stop_aware_prediction_s'] == 111.
    assert rows.loc[20.5, 'driving_state'] == 'moving'
    assert rows.loc[20.5, 'stop_aware_prediction_s'] > 110.
    assert rows.loc[23., 'stop_aware_prediction_s'] == 110.
    assert [e['event'] for e in engine.events] == ['stop', 'resume']


@pytest.mark.parametrize('speed', [12., 3., 25.])
def test_slow_corner_and_braking_are_not_stops(source, bundle, speed):
    f = source.frame.copy()
    f.loc[f.lap_elapsed_s.between(10, 20), 'speed_kmh'] = speed
    rows, engine = replay(replace(source, frame=f), bundle)
    assert not engine.events
    np.testing.assert_array_equal(rows.bounded_prediction_s, rows.stop_aware_prediction_s)


def test_short_low_speed_period_hysteresis_and_noise(source, bundle):
    source = stopped(source, ((10., 10.8), (15., 25.)))
    f = source.frame.copy()
    f.loc[f.lap_elapsed_s.between(18., 18.1), 'speed_kmh'] = 4.5
    f.loc[f.lap_elapsed_s.between(20., 21.), 'speed_kmh'] = 3.
    rows, engine = replay(replace(source, frame=f), bundle, .5)
    assert sum(e['event'] == 'stop' for e in engine.events) == 1
    assert sum(e['event'] == 'resume' for e in engine.events) == 1
    assert rows.set_index('checkpoint_s').loc[21., 'driving_state'] == 'stationary'


def test_multiple_stops_and_invalid_samples_require_reconfirmation(source, bundle):
    rows, engine = replay(stopped(source, ((5., 10.), (20., 30.))), bundle)
    assert [e['event'] for e in engine.events] == ['stop', 'resume', 'stop', 'resume']
    detector = StopDetector()
    for t in np.arange(0., 1.21, .1):
        detector.update(t, 0.)
    assert detector.stationary
    assert detector.update(1.3, np.nan) == 'invalid'
    detector.update(1.4, 0.)
    assert detector.state == 'uncertain' and not detector.stationary
    detector.update(5., 0.)
    assert detector.state == 'uncertain' and not detector.stationary


def test_physical_bound_and_extended_valid_slow_lap(source, bundle):
    f = pd.concat([source.frame.assign(lap_elapsed_s=source.frame.lap_elapsed_s+i*40).iloc[:-1]
                   for i in range(8)], ignore_index=True)
    f.speed_kmh = 0.
    rows, _ = replay(replace(source, frame=f), bundle)
    assert rows.bound_active.any()
    assert (rows.bounded_prediction_s >= rows.observed_elapsed_s).all()
    assert (rows.stop_aware_prediction_s >= rows.observed_elapsed_s).all()
    assert rows.stop_aware_prediction_s.iloc[-1]-rows.stop_aware_prediction_s.iloc[-6] == pytest.approx(5.)
    assert physical_bound(4., 10.) == 10.
    with pytest.raises(ValueError):
        physical_bound(np.nan, 10.)


def test_cached_queries_and_pause_do_not_add_wall_time(source, bundle):
    engine = ReplayEngine(source, bundle)
    first = engine.predict(10.)
    calls = engine.model_calls
    assert engine.predict(10.) == first and engine.model_calls == calls
    assert advance_checkpoint((5., 10., 15.), 10., False) == 10.
    assert advance_checkpoint((5., 10., 15.), 10., True) == 15.
    assert advance_checkpoint((5., 10., 15.), 15., True) == 15.
    with pytest.raises(ValueError, match='rewind'):
        engine.predict(5.)


def test_stale_checkpoint_is_skipped_without_interpolation(source):
    f = source.frame.loc[~source.frame.lap_elapsed_s.between(9.9, 10.)].copy()
    idx = PrefixIndex(replace(source, frame=f))
    assert 10. not in idx.schedule(1.) and 11. in idx.schedule(1.)
    with pytest.raises(ValueError, match='fresh'):
        idx.features(10.)


def test_unavailable_onset_uses_first_valid_observed_estimate(source, bundle):
    f = stopped(source, ((.5, 20.),)).frame.copy()
    f.loc[f.lap_elapsed_s <= .02, 'rpm'] = np.nan
    rows, _ = replay(replace(source, frame=f), bundle, .5)
    stationary = rows[rows.driving_state == 'stationary']
    assert len(stationary) > 5
    assert stationary.stop_aware_prediction_s.iloc[-1]-stationary.stop_aware_prediction_s.iloc[-6] == pytest.approx(2.5)


@pytest.mark.parametrize('change', ['domain', 'uid', 'features', 'version', 'protocol'])
def test_model_and_operational_isolation(source, bundle, change):
    if change == 'domain':
        source = replace(source, domain=('other', 'car'))
    elif change == 'uid':
        source = replace(source, lap_uid='historical-test')
    elif change == 'features':
        bundle.feature_names = ('progress',)
    else:
        bundle.compatibility['version' if change == 'version' else 'protocol_sha256'] = 'wrong'
    with pytest.raises(ValueError):
        ReplayEngine(source, bundle)
