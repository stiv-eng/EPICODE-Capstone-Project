"""Offline unit fixtures plus an opt-in-by-presence real attachment integration."""
from io import BytesIO
from pathlib import Path
import hashlib

import numpy as np
import pandas as pd
import pytest

from motorsport.ingestion.csv_importer import read_csv
from motorsport.ingestion.parquet_importer import read_parquet
from motorsport.pipeline import load_session
from motorsport.processing.normalization import normalize
from motorsport.processing.schema import SourceProfile, SUPPLIED_V04
from motorsport.processing.validation import quality_report
from motorsport.processing.laps import detect_laps
from motorsport.analytics.session_metrics import chart_sample, session_metrics


def test_parquet_bytes_path_and_metadata(tmp_path):
    frame = pd.DataFrame({'elapsed_s': [0., 1.], 'speed_kmh': [10., 20.]})
    path = tmp_path/'sample.parquet'
    frame.to_parquet(path, index=False)
    data, metadata = read_parquet(path)
    pd.testing.assert_frame_equal(data, frame)
    pd.testing.assert_frame_equal(read_parquet(path.read_bytes())[0], frame)
    assert metadata['rows'] == 2 and metadata['row_groups'] == 1
    assert 'elapsed_s' in metadata['arrow_schema']


@pytest.mark.parametrize('delimiter', [',', ';', '\t'])
def test_csv_loading_and_pipeline(delimiter):
    raw = f'elapsed_s{delimiter}speed_kmh\n0{delimiter}12\n1{delimiter}20\n'.encode()
    frame, metadata = read_csv(raw)
    assert frame.shape == (2, 2) and metadata['format'] == 'CSV'
    assert load_session(raw, 'test.csv').metrics['speed_kmh_max'] == 20


def test_explicit_units_and_raw_preservation():
    raw = pd.DataFrame({'clock': [1000, 2000], 'velocity': [10, 20],
                        'pedal': [.2, 1.], 'brake': [False, True], 'extra': [7, 8]})
    original = raw.copy(deep=True)
    profile = SourceProfile('test', {'elapsed_s': 'clock', 'speed_kmh': 'velocity',
        'throttle_pct': 'pedal', 'brake_pct': 'brake'},
        {'elapsed_s': 'ms', 'speed_kmh': 'm/s', 'throttle_pct': 'fraction', 'brake_pct': 'fraction'})
    data, meta = normalize(raw, profile)
    np.testing.assert_allclose(data.elapsed_s, [0, 1])
    np.testing.assert_allclose(data.speed_kmh, [36, 72])
    np.testing.assert_allclose(data.throttle_pct, [20, 100])
    np.testing.assert_allclose(data.brake_pct, [0, 100])
    assert data.extra.tolist() == [7, 8] and meta['profile'] == 'test'
    pd.testing.assert_frame_equal(raw, original)


def test_no_range_based_unit_guessing():
    data, _ = normalize(pd.DataFrame({'throttle_pct': [.1, .2], 'throttle': [.1, .2]}))
    assert data.throttle_pct.tolist() == [.1, .2]
    data, _ = normalize(pd.DataFrame({'throttle': [.1, .2]}))
    assert 'throttle_pct' not in data


def test_single_channel_csv_is_not_split_on_header_letters():
    session = load_session(b'rpm\n1000\n2000\n', 'rpm.csv')
    assert session.data.columns.tolist() == ['rpm']
    assert session.metrics['rpm_max'] == 2000


def test_datetime_and_timedelta_time():
    data, _ = normalize(pd.DataFrame({'time': ['2026-01-01T00:00:00Z', '2026-01-01T00:00:02Z']}),
                        SourceProfile('date', {'elapsed_s': 'time'}, {'elapsed_s': 'datetime'}))
    assert data.elapsed_s.tolist() == [0., 2.]
    data, _ = normalize(pd.DataFrame({'elapsed_s': pd.to_timedelta([5, 6], unit='s')}))
    assert data.elapsed_s.tolist() == [0., 1.]


def test_invalid_values_reported_without_deleting_rows():
    raw = pd.DataFrame({'elapsed_s': [0, 1, 1, .5, np.nan],
                        'speed_kmh': [10, np.inf, -5, 'bad', 501],
                        'rpm': [2000]*5, 'gear': [1, 1, 1.5, 2, 2]})
    data, meta = normalize(raw)
    q = quality_report(data, 'elapsed_s')
    assert len(data) == len(raw)
    assert data.speed_kmh.isna().sum() == 2
    assert q['time']['duplicate_values'] == 1
    assert q['time']['backward_steps'] == 1
    assert q['time']['duration_s'] is None
    assert q['time']['missing_or_nonfinite'] == 1
    assert q['constant_channels'] == ['rpm']
    by_name = {c['channel']: c for c in q['channels']}
    assert by_name['speed_kmh']['outside_limits'] == 2
    assert by_name['gear']['outside_limits'] == 1
    assert meta['notes'] and np.isinf(raw.speed_kmh.iloc[1])


def test_source_quality_missing_nonfinite_duplicates_outliers():
    values = [1.] * 8 + [2.] * 8 + [1000., np.inf, np.nan]
    q = quality_report(pd.DataFrame({'value': values}))
    assert q['missing_cells'] == 1 and q['infinite_cells'] == 1
    assert q['duplicate_rows'] == 14
    assert q['channels'][0]['iqr_outliers'] == 1


@pytest.mark.parametrize('frame', [pd.DataFrame(), pd.DataFrame({'extra': [1, 2]})])
def test_missing_time_and_position(frame):
    data, meta = normalize(frame)
    assert not detect_laps(data).available
    assert 'duration_s' not in session_metrics(data)
    assert meta['notes']


def lap_fixture():
    # Witnessed crossings at 30, 90 and 150; neither outer fragment is complete.
    t = np.arange(181, dtype=float)
    return pd.DataFrame({'elapsed_s': t, 'completed_laps': np.floor((t+30)/60),
                         'lap_progress': ((t+30) % 60)/60, 'speed_kmh': 100.})


def test_laps_require_two_witnessed_boundaries_and_exclude_fragments():
    result = detect_laps(lap_fixture())
    assert result.available
    assert result.laps.duration_s.tolist() == [60., 60.]
    assert result.laps.start_sample.tolist() == [30, 90]
    assert result.laps.end_sample.tolist() == [90, 150]


@pytest.mark.parametrize('problem', ['constant', 'reset', 'duplicate', 'counter_jump',
                                     'fractional_counter', 'invalid', 'progress_units'])
def test_unreliable_laps_are_unavailable(problem):
    frame = lap_fixture()
    if problem == 'constant':
        frame[['completed_laps', 'lap_progress']] = 0
    elif problem == 'reset':
        frame.loc[30, 'lap_progress'] = .4
    elif problem == 'duplicate':
        frame.loc[5, 'elapsed_s'] = 4
    elif problem == 'counter_jump':
        frame.loc[30:, 'completed_laps'] += 1
    elif problem == 'fractional_counter':
        frame['completed_laps'] += .5
    elif problem == 'invalid':
        frame.loc[50, 'lap_progress'] = np.nan
    elif problem == 'progress_units':
        frame['lap_progress'] *= 100
    assert not detect_laps(frame).available


def test_lap_duration_gaps_and_incomplete_recording():
    assert not detect_laps(lap_fixture(), min_lap_s=100).available
    assert not detect_laps(lap_fixture().iloc[:80]).available
    frame = lap_fixture().drop(index=range(50, 60)).reset_index(drop=True)
    result = detect_laps(frame)
    assert result.available and len(result.laps) == 1
    assert result.laps.start_s.iloc[0] == 90


def test_pipeline_assigns_only_validated_lap_samples():
    frame = lap_fixture()
    session = load_session(frame.to_csv(index=False).encode(), 'laps.csv')
    assert session.laps.available
    assert session.data.lap_id.iloc[:30].isna().all()
    assert session.data.lap_id.iloc[150:].isna().all()
    assert session.data.lap_elapsed_s.iloc[30] == 0
    assert 'lap_id' in {c['channel'] for c in session.quality['channels']}


def test_source_lap_ids_are_not_promoted_without_validated_boundaries():
    session = load_session(b'elapsed_s,lap_id,lap_elapsed_s\n0,1,0\n1,1,1\n', 'unverified.csv')
    assert 'lap_id' in session.raw
    assert 'lap_id' not in session.data and 'lap_elapsed_s' not in session.data
    assert not session.laps.available


def test_lap_assignment_handles_nonunique_source_index():
    frame = lap_fixture()
    frame.index = np.zeros(len(frame), dtype=int)
    stream = BytesIO()
    frame.to_parquet(stream)
    session = load_session(stream.getvalue(), 'laps.parquet')
    assert session.data.lap_id.iloc[:30].isna().all()
    assert session.data.lap_id.iloc[30:90].eq(1).all()
    assert session.data.lap_id.iloc[150:].isna().all()


def test_chart_budget_preserves_brief_peaks_and_does_not_mutate():
    frame = pd.DataFrame({'elapsed_s': np.arange(10000), 'speed_kmh': 100., 'brake_pct': 0.})
    frame.loc[3456, 'brake_pct'] = 100
    frame.loc[7890, 'speed_kmh'] = 250
    chart = chart_sample(frame, ['speed_kmh', 'brake_pct'], max_points=200)
    assert len(chart) <= 200 and len(frame) == 10000
    assert chart.index[0] == 0 and chart.index[-1] == 9999
    assert chart.brake_pct.max() == 100 and chart.speed_kmh.max() == 250
    assert session_metrics(frame)['speed_kmh_mean'] == pytest.approx(100.015)


def test_manual_disable_and_unknown_units():
    data, _ = normalize(pd.DataFrame({'elapsed_s': [0, 1], 'speed_kmh': [1, 2]}),
                        SourceProfile('manual', {'speed_kmh': '__unavailable__'}))
    assert 'speed_kmh' not in data
    with pytest.raises(ValueError, match='Unknown speed unit'):
        normalize(pd.DataFrame({'speed_kmh': [1]}), SourceProfile(units={'speed_kmh': 'mph'}))


def test_unsupported_and_malformed_files():
    with pytest.raises(ValueError, match='formats'):
        load_session(b'', 'bad.txt')
    with pytest.raises(Exception):
        read_parquet(b'not parquet')


REAL_DATA = Path(__file__).resolve().parents[1]/'data/raw/telemetry.parquet'


@pytest.mark.skipif(not REAL_DATA.exists(), reason='Real attachment is local and not committed.')
def test_real_attachment_integration_and_immutability():
    def digest():
        with REAL_DATA.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    before = digest()
    assert before == 'fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7'
    session = load_session(REAL_DATA, profile=SUPPLIED_V04)
    assert session.raw.shape == (116987, 86)
    assert session.data.elapsed_s.iloc[-1] == pytest.approx(1827.078)
    assert session.quality['time']['duplicate_values'] == 1245
    assert session.raw_quality['missing_cells'] == 0
    assert session.raw_quality['infinite_cells'] == 0
    assert len(session.raw_quality['constant_channels']) == 14
    assert session.data.throttle_pct.max() == 100
    assert session.data.brake_pct.max() == 100
    assert session.data.speed_kmh.max() == pytest.approx(260.58929443359375)
    assert not session.laps.available
    assert 'lap_id' not in session.data
    assert {'rpm', 'steering', 'pos_x', 'pos_y'}.issubset(session.data)
    assert before == digest()
