"""Test senza dati esterni: nessuna connessione FastF1 richiesta."""
import numpy as np
import pandas as pd
from motorsport_prediction.data import LapRecord, normalize_telemetry
from motorsport_prediction.features import build_dataset, snapshots, NUMERIC_FEATURES


def lap_record(uid='FP1:AAA:1', speed=180.0, lap_time=110.0, code='FP1'):
    seconds = np.linspace(0, 110, 441)
    raw = pd.DataFrame({
        'Time': pd.to_timedelta(seconds, unit='s'),
        'Speed': speed + np.sin(seconds/10)*4,
        'Throttle': 85.0, 'Brake': False, 'RPM': 10500, 'nGear': 7,
    })
    return LapRecord(uid, 'AAA', code, 1, lap_time, 'SOFT', 2,
                     normalize_telemetry(raw))


def test_telemetry_distance_nonnegative_and_increasing():
    lap = lap_record()
    d = lap.telemetry['distance_m'].to_numpy()
    assert np.all(np.diff(d) >= 0)
    assert 5000 < d[-1] < 6000


def test_snapshots_are_causal_wrt_future_telemetry():
    reference = lap_record(uid='FP3:AAA:1', code='FP3')
    q = lap_record(uid='Q:AAA:1', speed=186, code='Q', lap_time=108)
    full = snapshots(q, reference, steps=[0.2, 0.4, 0.6], include_finish=False)
    target = float(full.loc[1, 'elapsed_s'])
    short_lap = lap_record(uid='Q:AAA:1', speed=186, code='Q', lap_time=108)
    short_lap.telemetry = short_lap.telemetry.loc[short_lap.telemetry['elapsed_s'] <= target].copy()
    short = snapshots(short_lap, reference, steps=[0.2, 0.4, 0.6], include_finish=False)
    for col in NUMERIC_FEATURES + ['baseline_s']:
        assert np.allclose(full.loc[:1, col].to_numpy(dtype=float),
                           short.loc[:1, col].to_numpy(dtype=float))
    assert not bool(full.loc[0, 'is_finish'])


def test_dataset_has_multi_lap_snapshots():
    reference = lap_record(uid='FP3:AAA:1', code='FP3')
    laps = [lap_record(uid=f'FP1:AAA:{n}') for n in range(1, 4)]
    frame = build_dataset(laps, {'AAA': reference})
    assert frame['lap_uid'].nunique() == 3
    assert set(frame['session']) == {'FP1'}
    assert frame['target_residual_s'].notna().all()


def test_fp3_reference_is_excluded_from_training(monkeypatch):
    from motorsport_prediction import data
    fp1 = lap_record(uid='FP1:AAA:1', code='FP1')
    fp2 = lap_record(uid='FP2:AAA:1', code='FP2')
    best = lap_record(uid='FP3:AAA:1', code='FP3', lap_time=108)
    other = lap_record(uid='FP3:AAA:2', code='FP3', lap_time=109)
    monkeypatch.setattr(data, '_load_session', lambda year, event, code, cache_dir: code)
    monkeypatch.setattr(data, 'extract_laps', lambda session, code, max_per_driver:
                        {'FP1': [fp1], 'FP2': [fp2], 'FP3': [best, other]}[code])
    laps, refs, _ = data.load_practice(2024, 'Italian Grand Prix')
    assert refs['AAA'].uid == best.uid
    assert best.uid not in [lap.uid for lap in laps]
    assert other.uid in [lap.uid for lap in laps]


def test_observed_features_ignore_unknown_final_lap_time():
    ref = lap_record(uid='FP3:AAA:9', code='FP3')
    first = lap_record(uid='Q:AAA:1', code='Q', lap_time=102)
    second = lap_record(uid='Q:AAA:1', code='Q', lap_time=108)
    a = snapshots(first, ref, steps=[.2,.4,.6], include_finish=False)
    b = snapshots(second, ref, steps=[.2,.4,.6], include_finish=False)
    for col in NUMERIC_FEATURES + ['baseline_s']:
        assert np.allclose(a[col], b[col])
    assert a['actual_s'].iloc[0] != b['actual_s'].iloc[0]
