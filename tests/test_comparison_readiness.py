from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motorsport.pipeline import load_session
from motorsport.analytics.comparison import select_window,compare_windows,lap_trace,cumulative_lap_delta
from motorsport.analytics.readiness import assess_capabilities,lap_features
from motorsport.ingestion.gt7_importer import load_gt7_bundle,validate_gt7_laps
from motorsport.processing.normalization import normalize
from motorsport.processing.schema import SourceProfile
from motorsport.analytics.timebase import time_support


def simple_session(offset=0):
    frame=pd.DataFrame({'elapsed_s':np.arange(11)*.1,'speed_kmh':100+offset,'steering':offset})
    return load_session(frame.to_csv(index=False).encode(),'fixture.csv')


def test_window_relative_axis_no_interpolation_or_lap_delta():
    left,right=simple_session(),simple_session(10)
    a,b,stats,rejected=compare_windows(left,right,(.2,.8),(.4,.9),['speed_kmh','steering','brake_pct'])
    assert a.relative_s.iloc[0]==pytest.approx(0)
    assert b.relative_s.iloc[0]==pytest.approx(0)
    assert stats.channel.to_list()==['speed_kmh']
    assert stats.B_time_mean.iloc[0]==pytest.approx(110)
    assert set(rejected)=={'steering','brake_pct'}
    assert 'delta_s' not in a


def test_invalid_and_empty_windows():
    with pytest.raises(ValueError):select_window(simple_session().data,1,1)
    with pytest.raises(ValueError):select_window(simple_session().data,2,3)
    with pytest.raises(ValueError):select_window(pd.DataFrame({'elapsed_s':[1,0]}),0,2)


def test_byte_pedals_have_exact_valid_full_scale_without_clamping_bad_data():
    out,_=normalize(pd.DataFrame({'raw':[0,255,256]}),
                    SourceProfile('byte',{'throttle_pct':'raw'},{'throttle_pct':'byte255'}))
    assert out.throttle_pct.iloc[1]==100.
    assert out.throttle_pct.iloc[2]>100.


def test_window_keeps_unknown_clock_rows_as_support_breaks():
    frame=pd.DataFrame({'elapsed_s':[0,.1,np.nan,.3,.4],'speed_kmh':100})
    selected=select_window(frame,0,.4)
    assert len(selected)==5
    assert time_support(selected)['observed_s']==pytest.approx(.2)


def test_capabilities_are_not_enabled_by_column_names_alone():
    s=load_session(b'elapsed_s,pos_x,pos_y,lap_id,speed_kmh\n0,0,0,1,100\n1,0,0,1,100\n','bad.csv')
    flags=assess_capabilities(s)
    assert flags['session_analysis']['available']
    assert flags['time_window_comparison']['available']
    assert not flags['track_position_analysis']['available']
    assert not flags['validated_lap_analysis']['available']
    assert not flags['supervised_ml_eligible']['available']
    assert lap_features(s).empty


def gt7_fixture():
    frames=[]
    for lap_id in [1,2,3]:
        t=np.arange(600)*.05
        if lap_id>1:t[0]=30
        frames.append(pd.DataFrame({'lap':lap_id,'lap_count':lap_id,'current_lap_ms':t*1000,
                                    'last_lap_ms':30000,'distance_m':np.linspace(0,5000,600),
                                    'wall_time':lap_id*30+np.arange(600)*.05}))
    return pd.concat(frames,ignore_index=True)


def test_gt7_boundaries_targets_and_final_fragment():
    raw=gt7_fixture()
    laps,timer,rejected=validate_gt7_laps(raw)
    assert laps.available and laps.laps.lap_id.tolist()==[1,2]
    assert laps.laps.duration_s.tolist()==[30,30]
    assert np.isnan(timer[600])  # Packet counter leads timer reset.
    assert np.isnan(timer[1200:]).all()  # No witnessed final target.
    assert rejected[-1]['source_lap']==3
    raw.loc[700,'current_lap_ms']=raw.loc[699,'current_lap_ms']
    result,_,_=validate_gt7_laps(raw)
    assert result.laps.lap_id.tolist()==[1]


def valid_lap_session():
    t=np.arange(181,dtype=float)
    source=pd.DataFrame({'elapsed_s':t,'lap_progress':((t+30)%60)/60,
                         'completed_laps':np.floor((t+30)/60),
                         'distance_m':((t+30)%60)*100,'speed_kmh':180})
    return load_session(source.to_csv(index=False).encode(),'laps.csv')


def test_delta_requires_verified_reference_and_has_expected_sign():
    a,b=valid_lap_session(),valid_lap_session()
    assert lap_trace(a,1).normalized_driven_progress.iloc[-1]==1
    with pytest.raises(ValueError,match='shared track-distance'):
        cumulative_lap_delta(a,b,1,1)
    a.metadata['distance_reference_id']=b.metadata['distance_reference_id']='fixture-track'
    b.data.loc[b.data.lap_id.eq(1).fillna(False),'lap_elapsed_s']*=1.1
    delta=cumulative_lap_delta(a,b,1,1)
    assert delta.delta_s.iloc[-1]==pytest.approx(5.9)
    features=lap_features(a)
    assert features.target_verified.all()
    assert not features.supervised_eligible.any()
    assert features.feature_scope.str.contains('retrospective').all()


REAL=Path(__file__).resolve().parents[1]/'data/raw/gt7_trial_mountain_962c'


@pytest.mark.skipif(not (REAL/'data/laps/lap_015.parquet').exists(),reason='Optional local GT7 bundle absent')
def test_real_gt7_integration():
    session=load_gt7_bundle(REAL)
    assert session.raw.shape==(95796,114)
    assert session.laps.laps.lap_id.tolist()==[2,3,4,5,6,11,13,14]
    assert len(session.metadata['lap_rejections'])==8
    assert session.data.throttle_pct.max()==pytest.approx(100)
    flags=assess_capabilities(session)
    assert flags['full_lap_targets']['available'] and flags['validated_lap_analysis']['available']
    assert flags['lap_progress_comparison']['available']
    assert not flags['cumulative_lap_delta']['available']
    assert not flags['progressive_dl_eligible']['available']
    features=lap_features(session)
    assert len(features)==8 and features.target_lap_time_s.min()==pytest.approx(103.712)
