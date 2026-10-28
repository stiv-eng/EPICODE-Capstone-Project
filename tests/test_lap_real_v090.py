import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motorsport.ingestion.barcelona import ROOT,MANIFEST,load_barcelona_recording
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.lap_analysis.data import spatial_source,from_session
from motorsport.lap_analysis.analysis import analyze_laps,json_facts


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_barcelona_dallara').exists(),reason='Optional local Barcelona recordings absent')
def test_real_barcelona_coordinates_are_existing_source_values_without_mutating_analysis():
    entry=next(e for e in json.loads(MANIFEST.read_text())['files'] if e['path'].endswith('.ld') and e['recording_label']=='20240304_AB')
    session=load_barcelona_recording(entry['path'])
    before=session.data.copy(deep=True)
    spatial=spatial_source(session,'barcelona:'+entry['path'],ROOT)
    assert spatial[0].shape==(len(session.data),2) and spatial[1]
    pd.testing.assert_frame_equal(session.data,before)
    a,b=from_session(session,3,spatial),from_session(session,6,spatial)
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    assert sum(s['delta_s'] for s in result.report['section_deltas'])==pytest.approx(7.873333333333335)
    assert any(s['kind']=='boundary' for s in result.report['geometry']['sections'])
    for corner in result.report['corners']:
        for k in corner['kpis']:
            if k['validity']=='valid':
                assert all(v is not None and np.isfinite(v) for v in (k['reference_value'],k['analyzed_value'],k['difference']))
    c=next(c for c in result.report['corners'] if c['section_id']=='C10')
    braking=next(k for k in c['kpis'] if k['name']=='brake_onset_position_m')
    assert braking['validity']=='uncertain' and braking['difference'] is None
    assert braking['reference_value'] is not None
    json.dumps(json_facts(result),allow_nan=False)
    pd.testing.assert_frame_equal(session.data,before)


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c').exists(),reason='Optional GT7 bundle absent')
def test_real_gt7_alignment_reconciles_and_unverified_physical_units_are_unavailable():
    session=load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')
    spatial=spatial_source(session,'gt7',ROOT)
    result=analyze_laps(from_session(session,14,spatial),from_session(session,13,spatial))
    assert result.report['status']=='valid' and abs(result.report['reconciliation']['error_s'])<1e-6
    assert result.report['laps']['measured_lap_delta_s']==pytest.approx(.094)
    unsupported={'steering_at_apex','peak_lateral_acceleration_g','mean_exit_acceleration_g'}
    for corner in result.report['corners']:
        for metric in corner['kpis']:
            if metric['name'] in unsupported:
                assert metric['validity']!='valid' and metric['difference'] is None
