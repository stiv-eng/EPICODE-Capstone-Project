"""Unique approach-event ownership and bounded exit attribution."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from motorsport.lap_analysis.alignment import TimeMap
from motorsport.lap_analysis.data import LapData
from motorsport.lap_analysis.kpis import KPIConfig,associated_braking_events,compare_corner


def comparison(brake_end=310.,throttle_on=430.):
    s=np.arange(0.,1000.1,.5);t=s/10.
    frame=pd.DataFrame(dict(lap_elapsed_s=t,brake_pct=np.where((s>=150)&(s<=brake_end),60.,0.),
        throttle_pct=np.where((s>=throttle_on)&(s<=throttle_on+10),80.,0.),speed_kmh=36.))
    lap=LapData('synthetic',100.,frame,dict(brake_pct='%',throttle_pct='%',speed_kmh='km/h'),{})
    aligned=SimpleNamespace(lap=lap,time=t,progress=s,time_map=TimeMap(s,t,1000.,100.))
    corners=[dict(section_id=identifier,kind='corner',start_s_m=start,end_s_m=end,wraps_start_finish=False,
                  curvature_weighted_apex_proxy=dict(s_m=apex))
             for identifier,start,end,apex in [('C01',300.,400.,350.),('C02',440.,520.,480.)]]
    geometry=SimpleNamespace(length_m=1000.,sections=corners)
    return aligned,geometry


def test_early_braking_is_measured_once_despite_overlapping_approach_windows():
    aligned,geometry=comparison()
    events=associated_braking_events(aligned,geometry,KPIConfig())
    assert len(events['C01'])==1 and not events['C02']
    assert events['C01'][0]['onset_s']==150.  # 150 m before entry; previously missed
    metrics={m['name']:m for m in compare_corner(aligned,aligned,geometry.sections[0],geometry,None,None)['kpis']}
    assert metrics['brake_onset_position_m']['validity']=='valid'
    assert metrics['braking_distance_m']['validity']=='unavailable'  # no invented XY
    assert metrics['throttle_after_apex_distance_m']['reference_value']==pytest.approx(80.)
    assert metrics['throttle_after_apex_delay_s']['reference_value']==pytest.approx(8.)


def test_spanning_brake_phase_is_uncertain_and_next_corner_throttle_is_not_claimed():
    aligned,geometry=comparison(brake_end=500.,throttle_on=445.)
    events=associated_braking_events(aligned,geometry,KPIConfig())
    assert len(events['C01'])==1 and not events['C02']
    assert 'multiple corner' in events['C01'][0]['association_reason']
    metrics={m['name']:m for m in compare_corner(aligned,aligned,geometry.sections[0],geometry,None,None)['kpis']}
    assert metrics['brake_onset_position_m']['validity']=='uncertain'
    assert metrics['brake_onset_position_m']['difference'] is None
    assert metrics['throttle_after_apex_delay_s']['reference_value'] is None
