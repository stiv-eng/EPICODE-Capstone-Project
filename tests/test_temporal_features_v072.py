from copy import deepcopy
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from motorsport.ml.dataset import ReplayLap
from motorsport.ml.barcelona_recovery import DOMAIN
from motorsport.ml.features import prefix_features,FEATURES
from motorsport.ml.temporal_features_v072 import feature_row,FEATURE_SETS,UNITS,_phase_count


@pytest.fixture
def source():
    t=np.arange(0,81,.05)
    frame=pd.DataFrame(dict(lap_elapsed_s=t,speed_kmh=150+40*np.sin(t),
        throttle_pct=np.where(t%10>3,100.,0.),brake_pct=np.where(t%10<=3,50.,0.),
        rpm=6000.,gear=4.,steering=20*np.sin(t/2)))
    return ReplayLap('capture:lap:1','recording','unknown',DOMAIN,('unknown',1,0.),frame,False,'deg')


@pytest.mark.parametrize('checkpoint',[10,20,30,45,60])
def test_all_variants_use_only_available_prefix_and_f0_bit_identity(source,checkpoint):
    changed=deepcopy(source)
    future=changed.frame.lap_elapsed_s>checkpoint
    changed.frame.loc[future,['speed_kmh','brake_pct','throttle_pct','rpm','gear','steering']]=-9999
    future_rows=np.flatnonzero(future)
    changed.frame.loc[future_rows[1:],'lap_elapsed_s']=0.
    for variant,names in FEATURE_SETS.items():
        before,_=feature_row(source,checkpoint,variant)
        after,_=feature_row(changed,checkpoint,variant)
        assert tuple(before)==names
        np.testing.assert_allclose(list(before.values()),list(after.values()),rtol=0,atol=0,equal_nan=True)
        original,_=prefix_features(source,checkpoint)
        assert {k:before[k] for k in FEATURES}==original


def test_actual_timestamp_window_clips_left_hold_support_without_centering(source):
    t=np.array([0.,.1,.2,.3,.4,.5])
    source.frame=pd.DataFrame(dict(lap_elapsed_s=t,speed_kmh=[36,72,72,108,108,144],
                                   throttle_pct=[0,20,40,60,80,100],brake_pct=0.,rpm=6000.,gear=4.,steering=0.))
    # Repeated pattern sampled on deliberately irregular actual intervals.
    t=np.r_[np.arange(0,5,.1),5.03,5.19,np.arange(5.3,10.001,.1)]
    source.frame=pd.DataFrame(dict(lap_elapsed_s=t,speed_kmh=np.where(t<5.1,36.,72.),
                                   throttle_pct=50.,brake_pct=0.,rpm=6000.,gear=4.,steering=0.))
    values,_=feature_row(source,10.,'F3')
    weights=np.maximum(0.,t[1:]-np.maximum(t[:-1],5.))
    expected=np.average(source.frame.speed_kmh.to_numpy()[:-1],weights=weights)
    assert values['speed_mean_5s_kmh']==pytest.approx(expected)
    assert values['distance_observed_m']==pytest.approx(np.sum(source.frame.speed_kmh.to_numpy()[:-1]*np.diff(t))/3.6)
    assert values['distance_observed_m']>100 and values['speed_delta_5s_kmh']==36


def test_deceleration_is_metres_per_second_squared_with_actual_dt(source):
    source.frame['speed_kmh']=250-source.frame.lap_elapsed_s*3.6
    values,_=feature_row(source,30.,'F3')
    assert values['deceleration_mean_5s_mps2']==pytest.approx(1.)
    assert values['deceleration_max_5s_mps2']==pytest.approx(1.)
    assert UNITS['deceleration_mean_5s_mps2']=='m/s^2'
    assert UNITS['distance_observed_m']=='m'


def test_gaps_invalid_boundaries_and_unavailable_optional_channels(source):
    changed=deepcopy(source);changed.frame=changed.frame.loc[~changed.frame.lap_elapsed_s.between(7,8)]
    with pytest.raises(ValueError,match='gap'):feature_row(changed,10.,'F3')
    changed=deepcopy(source);changed.frame=changed.frame.drop(columns=['gear','steering'])
    values,_=feature_row(changed,10.,'F3')
    assert np.isnan(values['gear_current']) and np.isnan(values['steering_activity_deg_s'])
    changed.frame.loc[changed.frame.lap_elapsed_s<2,'lap_elapsed_s']+=1
    with pytest.raises(ValueError,match='boundary'):feature_row(changed,10.,'F3')


def test_no_target_or_final_distance_normalization_and_tail_length_invariance(source):
    shorter=replace(source,frame=source.frame.loc[source.frame.lap_elapsed_s<=11].copy())
    assert feature_row(source,10.,'F3')==feature_row(shorter,10.,'F3')
    source.frame['target_s']=1e9;source.frame['final_distance_m']=1e-9;source.frame['source_progress']=1.
    assert feature_row(source,10.,'F3')==feature_row(shorter,10.,'F3')
    assert all('target' not in n and 'final_distance' not in n and 'progress' not in n for n in FEATURE_SETS['F3'])


def test_observed_event_durations_no_future_confirmation(source):
    source.frame['speed_kmh']=np.where(source.frame.lap_elapsed_s<2,36.,100.)
    source.frame['brake_pct']=np.where(source.frame.lap_elapsed_s.between(9.8,10),20.,0.)
    values,_=feature_row(source,10.,'F2')
    assert values['low_speed_observed_s']==pytest.approx(2.)
    assert values['severe_slow_observed_s']==pytest.approx(2.)
    assert values['recovery_from_low_kmh']==64.
    assert values['braking_phases_count']==1.
    assert _phase_count([True,False],[.05,.1])==0
    assert _phase_count([True,True],[.1,.1])==1
