"""Diagnostics preserve rejection safeguards and locate actual failing samples."""
import json

import numpy as np
import pytest

from motorsport.ingestion.barcelona import ROOT,MANIFEST,load_barcelona_recording
from motorsport.lap_analysis.data import spatial_source,from_session
from motorsport.lap_analysis.analysis import analyze_laps,json_facts
from motorsport.lap_analysis.alignment import align
from motorsport.lap_analysis.geometry import build_geometry
from test_lap_analysis_v090 import lap
from test_lap_geometry_v090 import circle


def test_rejected_projection_has_measured_diagnostics_without_regularizing_away_failures():
    a=lap(circle(100.));b=lap(circle(118.),105.,'outside limit')
    g=build_geometry(a.frame[['pos_x','pos_y']].to_numpy())
    result=align(b,g)
    assert result.time_map is None
    issue=next(i for i in result.quality['issues'] if i['code']=='offset')
    assert issue['limit']==12. and issue['maximum_observed']==pytest.approx(result.offsets.max())
    assert issue['sample_count']==int(result.problem_masks['offset'].sum())
    assert issue['first_time_s']==result.time[issue['first_sample']]
    assert result.problem_masks['offset'][issue['worst_sample']]
    # Valid projections and their original numerical conservation remain valid.
    accepted=analyze_laps(a,lap(circle(102.),105.,'supported line'))
    assert accepted.report['status']=='valid' and not accepted.analyzed.quality['issues']
    assert sum(s['delta_s'] for s in accepted.report['section_deltas'])==pytest.approx(5.)


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_barcelona_dallara').exists(),reason='Optional Barcelona recordings absent')
def test_three_investigated_barcelona_pairs_remain_rejected_with_located_problem_regions():
    from motorsport_ui.lap_analysis_v090 import trajectory_figure
    entries=json.loads(MANIFEST.read_text())['files']
    measured=[]
    for label,ids in [('20240229_HC',[2,4]),('20240304_AB',[5])]:
        entry=next(e for e in entries if e['path'].endswith('.ld') and e['recording_label']==label)
        session=load_barcelona_recording(entry['path'])
        spatial=spatial_source(session,'barcelona:'+entry['path'],ROOT)
        a=from_session(session,3,spatial)
        for lap_id in ids:
            result=analyze_laps(a,from_session(session,lap_id,spatial))
            assert result.report['status']=='unavailable'
            assert not result.report['section_deltas'] and not result.report['corners']
            assert result.report['laps']['measured_lap_delta_s']>0.
            assert result.analyzed.quality['ambiguous_samples']==0
            assert not result.analyzed.problem_masks.get('coverage',np.array([],bool)).any()
            issue=next(i for i in result.analyzed.quality['issues'] if i['code']=='offset')
            measured.append(issue['maximum_observed'])
            xy=result.analyzed.lap.frame[['pos_x','pos_y']].to_numpy()
            fig=trajectory_figure(result)
            trace=next(t for t in fig.data if t.name=='Scostamento dal riferimento · Analysis Lap')
            assert len(trace.x)<=802
            peak=issue['worst_sample']
            assert any(x==xy[peak,0] and y==xy[peak,1] for x,y in zip(trace.x,trace.y))
            assert not any(t.name=='Maximum-curvature point' for t in fig.data)
            json.dumps(json_facts(result),allow_nan=False)
    np.testing.assert_allclose(measured,[21.175120560295436,19.67291657035981,18.084507821030467],atol=1e-8)
