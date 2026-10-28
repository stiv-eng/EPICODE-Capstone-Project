"""Partial inverse clocks, window validity and signed residual conservation."""
import json

import numpy as np
import pytest

from motorsport.lap_analysis.analysis import analyze_laps,json_facts
from motorsport.lap_analysis.alignment import section_supported
from motorsport_ui.lap_analysis_v090 import trajectory_figure,contribution_figure
from test_lap_analysis_v090 import lap
from test_lap_geometry_v090 import circle


def excursion(duration=105.,two=False):
    b=lap(duration=duration,identity='localized unsupported positions')
    spans=[(100,250,1.)]+([(1200,1360,-1.)] if two else [])
    for start,end,sign in spans:
        b.frame.loc[start:end-1,'pos_y']+=sign*30.*np.sin(np.linspace(0,np.pi,end-start))
    return b


@pytest.mark.parametrize('duration',[95.,105.])
def test_multiple_invalid_regions_recover_without_bridging_and_have_one_signed_residual(duration):
    a,b=lap(),excursion(duration,two=True)
    result=analyze_laps(a,b);r=result.report
    assert r['status']=='partial'
    assert len(result.analyzed.time_map.runs)>=3
    runs=result.analyzed.time_map.runs
    assert all(left['end_s_m']<right['start_s_m'] for left,right in zip(runs,runs[1:]))
    for left,right in zip(runs,runs[1:]):
        middle=(left['end_s_m']+right['start_s_m'])/2
        assert np.isnan(result.analyzed.time_map.at(middle))
        assert not result.analyzed.time_map.supports(left['end_s_m'],right['start_s_m'])
    assert r['section_deltas'] and r['withheld_sections']
    assert len({s['section_id'] for s in r['section_deltas']})==len(r['section_deltas'])
    for measured in r['section_deltas']:
        assert section_supported(result.reference,measured,result.geometry.length_m)
        assert section_supported(result.analyzed,measured,result.geometry.length_m)
    valid_length=sum((s['end_s_m']-s['start_s_m'])%result.geometry.length_m or result.geometry.length_m for s in r['section_deltas'])
    withheld_length=sum(s['end_s_m']-s['start_s_m'] for s in r['withheld_sections'])
    assert valid_length+withheld_length==pytest.approx(result.geometry.length_m)
    intervals=[]
    for section in r['section_deltas']+r['withheld_sections']:
        start,end=section['start_s_m'],section['end_s_m']
        intervals.extend([(start,result.geometry.length_m),(0.,end)] if section['wraps_start_finish'] else [(start,end)])
    intervals.sort()
    assert intervals[0][0]==pytest.approx(0.) and intervals[-1][1]==pytest.approx(result.geometry.length_m)
    assert all(left[1]==pytest.approx(right[0],abs=1e-7) for left,right in zip(intervals,intervals[1:]))
    residual=r['unallocated_delta']
    assert residual['kind']=='accounting_residual' and residual['independently_measured'] is False
    assert sum(s['delta_s'] for s in r['section_deltas'])+residual['value_s']==pytest.approx(duration-100.,abs=1e-10)
    assert residual['value_s']*(duration-100)>0
    assert abs(r['reconciliation']['error_s'])<1e-10
    figure=contribution_figure(r)
    assert sum(t.name.startswith('Delta non attribuito') for t in figure.data)==1
    json.dumps(json_facts(result),allow_nan=False)


def test_kpi_windows_intersecting_a_hole_are_unavailable_but_supported_corners_retain_measurements():
    a,b=lap(),excursion()
    result=analyze_laps(a,b);baseline=analyze_laps(a,lap(duration=105.))
    assert result.report['status']=='partial'
    blocked=[];supported=[]
    for corner in result.report['corners']:
        for metric in corner['kpis']:
            window=metric['temporal_window_s']['analyzed']
            if not result.analyzed.time_map.supports_time(*window):
                assert metric['analyzed_value'] is None and metric['difference'] is None
                assert metric['validity']=='unavailable'
                blocked.append(metric['name'])
        speed=next(k for k in corner['kpis'] if k['name']=='speed_at_apex_kmh')
        if speed['validity']=='valid':supported.append(speed)
    assert blocked and supported
    assert any('brake' in name or 'braking' in name for name in blocked)
    for metric in supported:
        assert np.isfinite(metric['reference_value']) and np.isfinite(metric['analyzed_value'])
    # An unaffected corner still has the same source speed/steering measurements.
    for corner in result.report['corners']:
        old=next(c for c in baseline.report['corners'] if c['section_id']==corner['section_id'])
        for metric in corner['kpis']:
            if metric['name'] in ('speed_at_apex_kmh','steering_at_apex') and metric['validity']=='valid':
                prior=next(k for k in old['kpis'] if k['name']==metric['name'])
                assert metric['analyzed_value']==pytest.approx(prior['analyzed_value'])


def test_no_reliable_section_has_only_total_and_unallocated_remainder():
    result=analyze_laps(lap(circle(100.)),lap(circle(118.),95.,'unsupported line'))
    r=result.report
    assert r['status']=='unavailable' and not r['section_deltas']
    assert r['unallocated_delta']['required'] and r['unallocated_delta']['value_s']==-5.
    assert r['reconciliation']['error_s']==0.
    assert len(contribution_figure(r).data)==1


def test_finish_flag_uses_observed_reference_position_without_inventing_official_line():
    a=lap();result=analyze_laps(a,lap(duration=105.))
    marker=result.report['finish_marker']
    assert marker['official_line'] is False
    np.testing.assert_array_equal(marker['xy'],a.frame[['pos_x','pos_y']].iloc[-1])
    fig=trajectory_figure(result)
    flags=[annotation for annotation in fig.layout.annotations if annotation.text=='🏁']
    assert len(flags)==1
    assert flags[0].x==marker['xy'][0] and flags[0].y==marker['xy'][1]
    a=lap();a.frame=a.frame.iloc[:-100].copy()
    unsupported=analyze_laps(a,lap())
    assert 'finish_marker' not in unsupported.report


def test_fully_valid_path_has_original_section_values_and_no_residual():
    a,b=lap(),lap(duration=105.)
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    assert not result.report['unallocated_delta']['required']
    assert result.report['unallocated_delta']['value_s']==0.
    for section in result.report['section_deltas']:
        assert section['analyzed_time_s']==pytest.approx(section['reference_time_s']*1.05)
    assert result.trace.delta_s.iloc[-1]==pytest.approx(5.)


def test_reacquisition_after_lost_coordinates_never_forces_the_bad_observations():
    a,b=lap(),lap(identity='lost local neighborhood')
    b.frame.loc[200:350,['pos_x','pos_y']]+=np.array([500.,300.])
    result=analyze_laps(a,b)
    assert result.report['status']=='partial'
    assert np.isnan(result.analyzed.progress[200:351]).all()
    assert np.isfinite(result.analyzed.progress[500:]).any()
    assert any(s['start_s_m']>400. for s in result.report['section_deltas'])
    assert abs(result.report['reconciliation']['error_s'])<1e-9


def test_clock_gap_and_ambiguous_crossing_remain_holes_in_the_partial_inverse():
    a,b=lap(),lap(identity='clock gap')
    b.frame.loc[500:,'lap_elapsed_s']+=1.;b.duration_s+=1.
    result=analyze_laps(a,b)
    assert result.report['status']=='partial'
    assert not result.analyzed.time_map.supports_time(24.,27.)
    assert result.report['unallocated_delta']['required']
    theta=np.linspace(0,2*np.pi,2001)
    crossing=lap(np.c_[120*np.sin(theta),120*np.sin(2*theta)])
    ambiguous=analyze_laps(crossing,crossing)
    assert ambiguous.report['status']=='partial'
    assert np.isnan(ambiguous.analyzed.time_map.at(0.))
    assert np.isnan(ambiguous.analyzed.time_map.at(ambiguous.geometry.length_m/2))
