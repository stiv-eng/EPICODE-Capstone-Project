from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest

from motorsport.lap_analysis.data import LapData
from motorsport.lap_analysis.geometry import GeometryConfig, build_geometry
from motorsport.lap_analysis.alignment import TimeMap, align, ambiguity_mask
from motorsport.lap_analysis.analysis import analyze_laps, json_facts
from motorsport.lap_analysis.kpis import KPIConfig, confirmed_events
from test_lap_geometry_v090 import stadium, circle


def lap(xy=None, duration=100., identity='a'):
    xy=stadium() if xy is None else xy
    t=np.linspace(0,duration,len(xy))
    progress=np.linspace(0,1,len(xy))
    frame=pd.DataFrame(dict(lap_elapsed_s=t,pos_x=xy[:,0],pos_y=xy[:,1],speed_kmh=120-20*np.sin(progress*4*np.pi)**2,
        brake_pct=np.where(((progress>.2)&(progress<.32))|((progress>.7)&(progress<.82)),60.,0.),
        throttle_pct=np.where(progress% .5 >.32,80.,0.),steering=30*np.sin(progress*2*np.pi),g_lat=np.sin(progress*2*np.pi),g_lon=.2))
    units=dict(pos_x='m',pos_y='m',speed_kmh='km/h',brake_pct='%',throttle_pct='%',steering='deg',g_lat='g',g_lon='g')
    return LapData(identity,duration,frame,units,dict(session_id='synthetic',track_id='synthetic:stadium',car_id='fixture'),
                   'synthetic:shared-metric-frame','EXPLICIT SYNTHETIC KNOWN TRACK')


def test_identical_laps_zero_delta_and_section_time_sum():
    a=lap()
    result=analyze_laps(a,a)
    assert result.report['status']=='valid',result.report['alignment']
    assert all(abs(s['delta_s'])<1e-10 for s in result.report['section_deltas'])
    assert sum(s['reference_time_s'] for s in result.report['section_deltas'])==pytest.approx(a.duration_s)
    np.testing.assert_allclose(result.trace.delta_s,0.)
    for corner in result.report['corners']:
        for kpi in corner['kpis']:
            if kpi['validity']=='valid':assert kpi['difference']==pytest.approx(0.)
            assert {'definition','unit','reference_value','analyzed_value','temporal_window_s','validity','source_signals'}<=set(kpi)
    json.dumps(json_facts(result),allow_nan=False)
    assert isinstance(json_facts(result)['geometry']['closed'],bool)


def test_measured_final_delta_reconciles_and_swapping_reference_changes_sign():
    a,b=lap(),lap(duration=105.,identity='b')
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    assert result.trace.delta_s.iloc[-1]==pytest.approx(5.)
    assert sum(s['delta_s'] for s in result.report['section_deltas'])==pytest.approx(5.)
    swapped=analyze_laps(b,a)
    assert swapped.report['reconciliation']['final_delta_s']==pytest.approx(-5.)
    assert abs(result.report['reconciliation']['error_s'])<1e-6


def test_stationary_observations_retain_elapsed_time_and_section_contribution():
    a=lap()
    f=a.frame
    i=1100
    stop=pd.concat([f.iloc[[i]]]*101,ignore_index=True)
    stop.lap_elapsed_s=np.linspace(f.lap_elapsed_s.iloc[i],f.lap_elapsed_s.iloc[i]+5.,101)
    stop.speed_kmh=0.
    tail=f.iloc[i+1:].copy();tail.lap_elapsed_s+=5.
    changed=pd.concat([f.iloc[:i],stop,tail],ignore_index=True)
    b=replace(a,lap_id='stopped',frame=changed,duration_s=105.)
    result=analyze_laps(a,b)
    assert result.report['status']=='valid',result.report['alignment']
    assert result.analyzed.quality['observed_samples']==len(changed)
    assert result.analyzed.time_map.repeated_progress_time_s>=5.-1e-8
    assert sum(s['delta_s'] for s in result.report['section_deltas'])==pytest.approx(5.)
    assert len(result.analyzed.lap.frame)==len(changed)


def test_time_map_uses_departure_at_stop_without_smearing_its_duration():
    mapping=TimeMap([0.,10.,10.,20.],[0.,1.,6.,7.],20.,7.)
    assert mapping.at(9.99)<1.01
    assert mapping.at(10.)==6.
    assert mapping.at(10.01)>6.
    assert mapping.at(0.)==0. and mapping.at(20.)==7.


def test_different_driven_lines_align_without_independent_distance_normalization():
    a=lap(circle(100.))
    b=lap(circle(102.),105.,'outer line')
    result=analyze_laps(a,b)
    assert result.report['status']=='valid',result.report['alignment']
    assert 1.8 < result.analyzed.quality['p95_offset_m'] < 2.2
    assert result.report['reconciliation']['final_delta_s']==pytest.approx(5.)
    assert result.geometry.length_m < build_geometry(b.frame[['pos_x','pos_y']]).length_m


@pytest.mark.parametrize('defect',['reverse','far','clock','missing','open','units','frame','car'])
def test_invalid_or_unsupported_alignment_is_explicitly_unavailable(defect):
    a,b=lap(),lap(identity='b')
    if defect=='reverse':
        b.frame[['pos_x','pos_y']]=b.frame[['pos_x','pos_y']].iloc[::-1].to_numpy()
    elif defect=='far':b.frame.pos_y+=100.
    elif defect=='clock':b.frame.loc[500:,'lap_elapsed_s']+=1.
    elif defect=='missing':b.frame.loc[500,'pos_x']=np.nan
    elif defect=='open':b.frame=b.frame.iloc[:-100].copy()
    elif defect=='units':b.units={**b.units,'pos_x':'unknown'}
    elif defect=='frame':b.coordinate_frame=None
    elif defect=='car':b.identity={**b.identity,'car_id':'other'}
    result=analyze_laps(a,b)
    assert result.report['status']==('partial' if defect in ('missing','open') else 'unavailable')
    assert result.report['alignment']['reasons']
    if result.report['status']=='unavailable':
        assert not result.report['section_deltas'] and not result.report['corners']
    else:
        assert result.report['withheld_sections']
    assert result.report['laps']['measured_lap_delta_s']==b.duration_s-a.duration_s


def test_crossing_trajectory_is_not_resolved_with_naive_nearest_point():
    theta=np.linspace(0,2*np.pi,2001)
    xy=np.c_[120*np.sin(theta),120*np.sin(2*theta)]
    a=lap(xy)
    g=build_geometry(xy)
    assert ambiguity_mask(g).any()
    result=analyze_laps(a,a)
    assert result.report['status']=='partial'
    assert any('ambiguous' in r for r in result.report['alignment']['reasons'])
    assert result.report['withheld_sections'] and result.report['unallocated_delta']['required']


def test_common_reference_boundaries_do_not_change_with_analyzed_pace():
    a=lap()
    r1=analyze_laps(a,lap(duration=105.))
    r2=analyze_laps(a,lap(duration=110.))
    assert r1.report['geometry']['sections']==r2.report['geometry']['sections']


def test_wrap_corner_sections_reconcile_and_metric_units_remain_source_units():
    xy=stadium()[:-1]
    xy=np.roll(xy,-750,axis=0);xy=np.vstack([xy,xy[0]])
    a,b=lap(xy),lap(xy,105.,'b')
    a.units['steering']=b.units['steering']='rad'
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    assert any(s['wraps_start_finish'] for s in result.report['section_deltas'])
    assert sum(s['delta_s'] for s in result.report['section_deltas'])==pytest.approx(5.)
    steering=[k for c in result.report['corners'] for k in c['kpis'] if k['name']=='steering_at_apex']
    assert all(k['unit']=='rad' for k in steering)


def test_missing_channels_and_unknown_units_return_missing_not_zero():
    a,b=lap(),lap(identity='b')
    b.frame=b.frame.drop(columns=['throttle_pct'])
    b.units['steering']='source unit'
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    for c in result.report['corners']:
        for k in c['kpis']:
            if k['name'] in ('throttle_at_apex_pct','steering_at_apex'):
                assert k['analyzed_value'] is None and k['difference'] is None
                assert k['validity']!='valid'


def test_brake_persistence_hysteresis_multiple_events_and_censoring():
    t=np.round(np.arange(0.,10.001,.02),6)
    y=np.zeros(len(t));y[(t>=1)&(t<=1.08)]=30.
    y[(t>=2)&(t<=3)]=60.;y[(t>=5)&(t<=6)]=40.
    y[(t>=2.5)&(t<=2.54)]=0.
    events=confirmed_events(t,y)
    assert len(events)==2 and not any(e['censored'] for e in events)
    assert t[events[0]['onset_index']]==2.
    y[(t>=5.5)&(t<=5.52)]=np.nan
    assert any(e['censored'] for e in confirmed_events(t,y))


def test_no_brake_or_throttle_event_does_not_invent_measurements():
    a=lap();a.frame.brake_pct=0.;a.frame.throttle_pct=0.
    result=analyze_laps(a,a)
    for c in result.report['corners']:
        k={r['name']:r for r in c['kpis']}
        assert k['braking_event_count']['reference_value']==0
        for name in ('brake_onset_position_m','throttle_after_apex_delay_s'):
            assert k[name]['reference_value'] is None and k[name]['validity']=='unavailable'


def test_kpi_configuration_is_checked_before_analysis():
    a=lap()
    with pytest.raises(ValueError):analyze_laps(a,a,kpi_config=KPIConfig(brake_off_pct=20.))


def test_missing_finish_observations_cannot_be_repaired_by_duration_scaling():
    a,b=lap(),lap(identity='b')
    b.duration_s+=5.
    result=analyze_laps(a,b)
    assert result.report['status']=='partial'
    assert any('boundary observations' in reason for reason in result.report['alignment']['reasons'])
    assert np.isnan(result.analyzed.time_map.at(result.geometry.length_m))
    assert all(abs(s['delta_s'])<1e-9 for s in result.report['section_deltas'])
    assert result.report['unallocated_delta']['value_s']==pytest.approx(5.)


def test_unverified_normalized_progress_cannot_replace_coordinates():
    a,b=lap(),lap(identity='b')
    b.frame=b.frame.drop(columns=['pos_x','pos_y'])
    b.frame['source_progress']=np.linspace(0,1,len(b.frame))
    b.coordinate_frame=None
    result=analyze_laps(a,b)
    assert result.report['status']=='unavailable' and not result.report['section_deltas']


def test_known_steering_rate_and_mean_speed_measurements():
    a=lap()
    a.frame.steering=2.*a.frame.lap_elapsed_s
    a.frame.speed_kmh=120.
    result=analyze_laps(a,a)
    for corner in result.report['corners']:
        values={k['name']:k for k in corner['kpis']}
        assert values['steering_rms_rate']['reference_value']==pytest.approx(2.)
        assert values['mean_corner_speed_kmh']['reference_value']==pytest.approx(120.)


def test_distant_approach_event_is_not_claimed_as_a_valid_corner_braking_difference():
    a=lap()
    # The first event ends far before the geometric corner; values remain
    # observable, but association with that corner is explicitly uncertain.
    a.frame.brake_pct=0.
    t=a.frame.lap_elapsed_s.to_numpy()
    a.frame.loc[(t>=20)&(t<=20.5),'brake_pct']=60.
    result=analyze_laps(a,a)
    flagged=[k for c in result.report['corners'] for k in c['kpis'] if k['explanation'] and 'association' in k['explanation']]
    assert flagged and all(k['validity']=='uncertain' and k['difference'] is None for k in flagged)


def test_unverified_own_seam_curvature_cannot_have_valid_null_or_nan_metrics():
    a=lap(circle())
    xy=circle();xy[-1,1]+=2.
    b=lap(xy,105.,'offset seam')
    result=analyze_laps(a,b)
    assert result.report['status']=='valid'
    all_metrics=[k for c in result.report['corners'] for k in c['kpis']]
    for k in all_metrics:
        if k['validity']=='valid':
            assert all(v is not None and np.isfinite(v) for v in (k['reference_value'],k['analyzed_value'],k['difference']))
    curvature=next(k for k in all_metrics if k['name']=='minimum_trajectory_radius_m')
    assert curvature['analyzed_value'] is None and curvature['validity']=='unavailable'
    json.dumps(json_facts(result),allow_nan=False)
