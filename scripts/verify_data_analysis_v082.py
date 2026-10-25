"""Verify original signal hashes, all 205 Barcelona laps and untouched local data."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from motorsport.analytics.overview import overview_metrics
from motorsport.ingestion.barcelona import file_sha

ROOT = Path(__file__).resolve().parents[1]


def frame_hash(frame):
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()).hexdigest()


def verify(check_local_files=True):
    from motorsport_ui.telemetry import load_local, source_signature
    baseline = json.loads((ROOT/'docs/DATA_ANALYSIS_BASELINE_V082.json').read_text(encoding='utf-8'))
    expected = baseline['barcelona_validated_laps']
    observed_ids, source_rows, changed_laps = set(), [], []
    for source in baseline['analysis_sources']:
        key = str(ROOT/source['key'].removeprefix('local:')) if source['key'].startswith('local:') else source['key']
        session = load_local(key, source_signature(key))
        assert list(session.data.loc[:, source['canonical_columns']]) == source['canonical_columns']
        assert len(session.data) == source['samples']
        assert frame_hash(session.data[source['canonical_columns']]) == source['signals_sha256'], key
        # Signal arithmetic, measured-time support and overview values stay exact.
        assert overview_metrics(session.data) == source['overview'], key
        if key.startswith('barcelona:'):
            for lap in session.laps.laps.itertuples(index=False):
                uid = session.metadata['source_sha256']+':lap:'+str(lap.lap_id)
                assert uid in expected, uid
                frozen = expected[uid]
                assert lap.duration_s == frozen['duration_s']
                frame = session.data.iloc[lap.start_sample:lap.end_sample].loc[:, frozen['columns']].reset_index(drop=True)
                assert len(frame) == frozen['samples'] and frame_hash(frame) == frozen['frame_sha256'], uid
                observed_ids.add(uid)
        if len(session.laps.laps) != source['lap_count']:
            changed_laps.append(dict(key=key, previous_laps=source['lap_count'], current_laps=len(session.laps.laps)))
        source_rows.append(dict(key=source['key'], samples=len(session.data), laps=len(session.laps.laps),
            signal_hash_unchanged=True, overview_unchanged=True))
    assert observed_ids == set(expected) and len(observed_ids) == 205
    inventory = json.loads((ROOT/'docs/archive/LOCAL_ARTIFACT_INVENTORY_V082.json').read_text(encoding='utf-8'))
    checked = 0
    if check_local_files:
        for relative, item in inventory['untouched_local_files'].items():
            path = ROOT/relative
            assert path.stat().st_size == item['bytes'] and file_sha(path) == item['sha256'], relative
            checked += 1
    result = dict(status='passed', archive_commit=baseline['archive_commit'],
        analysis_sources=len(source_rows), signal_hashes_unchanged=len(source_rows),
        overview_summaries_unchanged=len(source_rows), barcelona_validated_laps=205,
        original_lap_trajectories_unchanged=205, checked_local_files=checked,
        barcelona_rounding_recovery=changed_laps,
        explanation='Analysis previously exposed 204 laps. Apply the already verified v071 1 ms target-rounding tolerance to expose the missing independently validated lap. Raw signals, source files and existing timings unchanged.',
        sources=source_rows)
    return result


def main():
    result = verify()
    path = ROOT/'docs/DATA_ANALYSIS_REGRESSION_V082.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'}, indent=2))


if __name__ == '__main__':
    main()
