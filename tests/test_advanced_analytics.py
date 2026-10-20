import numpy as np
import pandas as pd
import pytest

from motorsport.analytics.timebase import time_support, weighted_signal, fraction_time
from motorsport.analytics.driver_inputs import braking_events, driver_metrics
from motorsport.analytics.overview import overview_metrics, gear_distribution
from motorsport.analytics.channels import corner_channels


def test_irregular_time_weights_repeats_and_gaps():
    frame = pd.DataFrame({'elapsed_s':[0,.1,.1,.5,3.,3.2], 'speed_kmh':[10,20,30,40,50,60]})
    support = time_support(frame, gap_s=1.)
    np.testing.assert_allclose(support['weights'], [.1,0,.4,0,.2,0])
    assert support['observed_s'] == pytest.approx(.7)
    assert support['excluded_gap_s'] == 2.5
    assert support['span_s'] == 3.2
    assert support['duplicate_steps'] == 1
    stats = weighted_signal(frame,'speed_kmh',support)
    assert stats['time_mean'] == pytest.approx(23/.7)
    assert stats['sample_mean'] == 35


def test_backward_clocks_do_not_create_overlapping_duration():
    frame = pd.DataFrame({'elapsed_s':[0,1,.5,1.5], 'speed_kmh':10})
    assert time_support(frame)['observed_s'] == 0
    assert weighted_signal(frame,'speed_kmh')['time_mean'] is None


def test_missing_signal_coverage_and_terminal_sample():
    frame = pd.DataFrame({'elapsed_s':[0,.2,.5], 'throttle_pct':[100,np.nan,100]})
    usage = fraction_time(frame,['throttle_pct'],lambda v:v>90)
    assert usage == {'active_s':.2,'covered_s':.2,'time_pct':100.}
    assert fraction_time(frame,['brake_pct'],lambda v:v>5)['time_pct'] is None


def test_braking_events_separate_gaps_and_partial_fragments():
    frame=pd.DataFrame({'elapsed_s':[0,.1,.2,.3,.4,3.,3.1,3.2,3.3],
                        'brake_pct':[0,30,40,0,50,60,0,70,80], 'speed_kmh':100})
    events=braking_events(frame,min_duration_s=.05)
    assert len(events)==3
    assert events.complete.tolist()==[True,False,False]
    assert events.duration_s.tolist()==pytest.approx([.2,.1,.1])
    assert events.entry_speed_kmh.iloc[0]==100
    assert np.isnan(events.entry_speed_kmh.iloc[1])


def test_configurable_pedal_use_overlap_and_activity():
    frame=pd.DataFrame({'elapsed_s':[0,.1,.3,.4], 'throttle_pct':[100,20,0,0],
                        'brake_pct':[0,10,10,0], 'speed_kmh':[120,110,90,80], 'steering':[0,1,1,0]})
    metrics,events=driver_metrics(frame,throttle_threshold=90,brake_threshold=5,min_event_s=.05)
    assert metrics['usage']['high_throttle']['time_pct']==pytest.approx(25)
    assert metrics['usage']['braking']['time_pct']==pytest.approx(75)
    assert metrics['usage']['overlap']['time_pct']==pytest.approx(50)
    assert metrics['entry_speed_mean_kmh']==110
    assert metrics['steering_activity_source_units_per_s']==pytest.approx(5)
    stricter,_=driver_metrics(frame,brake_threshold=20)
    assert stricter['usage']['braking']['time_pct']==0


def test_constant_and_invalid_channels_are_not_synthetic_activity():
    frame=pd.DataFrame({'elapsed_s':[0,.1,.2], 'brake_pct':[0,200,0], 'steering':0, 'gear':[1,1,2]})
    metrics,_=driver_metrics(frame)
    assert metrics['usage']['braking']['covered_s']==pytest.approx(.1)
    assert metrics['steering_activity_source_units_per_s']==0
    assert metrics['usage']['high_throttle']['time_pct'] is None
    assert gear_distribution(frame).observed_s.tolist()==pytest.approx([.2,0])
    assert corner_channels(pd.DataFrame({'tyre_core_fl':[1], 'tyre_core_rr':[2]}),'tyre_core')=={
        'FL':'tyre_core_fl','RR':'tyre_core_rr'}


def test_overview_valid_samples_and_missing_time():
    result=overview_metrics(pd.DataFrame({'elapsed_s':[0,.1,np.nan], 'speed_kmh':[100,-1,20]}))
    assert result['valid_time_speed_samples']==1
    assert weighted_signal(pd.DataFrame({'speed_kmh':[1]}),'speed_kmh')['time_mean'] is None
