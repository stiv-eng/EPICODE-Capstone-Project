"""Release acceptance: state transitions, source truth and bounded SVG contracts."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from motorsport.pipeline import build_session
from motorsport.processing.laps import LapResult
from motorsport.analytics.position import position_segments, color_channels
from motorsport.analytics.readiness import assess_capabilities, lap_features
from motorsport.analytics.overview import overview_metrics
from motorsport_ui.selection import (SECTIONS, lap_labels, reconcile_selection,
                                     selected_frame, sample_at, selection_identity)
from motorsport_ui.visuals import comparison_figure, trajectory_figure
import motorsport_ui.telemetry as ui

ROOT=Path(__file__).resolve().parents[1]
EXPLORER=ROOT/'pages/00_Data_Explorer.py'


def fixture_session(identity='fixture'):
    frame=pd.DataFrame({'elapsed_s':100+np.arange(20)*.1,'speed_kmh':np.arange(20)+100.,
                        'throttle_pct':50.,'brake_pct':0.,'gear':3.,'rpm':6000.,
                        'pos_x':np.arange(20,dtype=float),'pos_y':np.arange(20,dtype=float)**2})
    laps=LapResult(True,'independently checked test timing',pd.DataFrame([
        {'lap_id':2,'start_sample':0,'end_sample':10,'start_s':0.,'end_s':1.,'duration_s':1.},
        {'lap_id':4,'start_sample':10,'end_sample':20,'start_s':1.,'end_s':2.,'duration_s':1.}]))
    return build_session(frame,{'filename':identity,'session_id':identity,'track_id':'fixture'},
                         validated_laps=laps,lap_elapsed=np.tile(np.arange(10)*.1,2))


def test_selection_invalidation_checks_identity_even_for_same_lap_numbers():
    state={}
    reconcile_selection(state,'a',[2,4])
    state['explorer_selected_laps']=[4]
    state['explorer_time_range']=(10,20)
    reconcile_selection(state,'a',[2,4])
    assert state['explorer_selected_laps']==[4]
    reconcile_selection(state,'b',[2,4])
    assert state['explorer_selected_laps']==[2] and state['explorer_time_range'] is None
    a=fixture_session();b=fixture_session()
    b.metadata['normalization']['profile']='changed units'
    assert selection_identity(a)!=selection_identity(b)


def test_lap_labels_and_selected_frames_only_use_verified_source_table():
    session=fixture_session()
    assert lap_labels(session)[2]=='Lap 2 — 0:01.000'
    assert selected_frame(session,[4]).lap_id.unique().tolist()==[4]
    assert selected_frame(session,[999]).empty
    assert selected_frame(session,[4,2]).index.tolist()==list(range(20))


def test_cockpit_sample_selection_returns_real_nearest_packet_no_interpolation():
    frame=pd.DataFrame({'elapsed_s':[0.,.2,np.nan,.6],'speed_kmh':[10.,30.,999.,60.]},index=[2,4,6,8])
    assert sample_at(frame,.31).name==4
    assert sample_at(frame,.1).speed_kmh==10.
    assert sample_at(frame,10).name==8
    assert sample_at(frame.iloc[:0],0) is None


def test_segments_break_at_invalid_positions_gaps_laps_jumps_and_removed_rows():
    frame=pd.DataFrame({'elapsed_s':np.arange(15)*.1,'pos_x':np.arange(15,dtype=float),
                        'pos_y':0.,'speed_kmh':np.arange(15),'lap_id':[2]*10+[4]*5})
    frame.loc[3,'pos_x']=np.nan
    frame.loc[6:,'elapsed_s']+=10
    frame.loc[12:,'pos_x']+=1000
    segments,_=position_segments(frame,'speed_kmh')
    pairs=set(zip(segments.start,segments.end))
    assert {(0,1),(1,2),(4,5),(6,7),(10,11),(12,13)}<=pairs
    assert not {(2,3),(3,4),(5,6),(9,10),(11,12)}&pairs
    assert np.all(segments.end.to_numpy()>segments.start.to_numpy())
    filtered=frame.drop(index=8)
    segments,_=position_segments(filtered,'speed_kmh')
    assert not ((segments.start==7)&(segments.end==8)).any()


def test_segment_simplification_is_bounded_and_keeps_run_endpoints():
    n=100000
    frame=pd.DataFrame({'elapsed_s':np.arange(n)*.01,'pos_x':np.arange(n),
                        'pos_y':np.sin(np.arange(n)/100),'speed_kmh':100.})
    segments,stats=position_segments(frame,'speed_kmh',max_points=1000)
    assert len(segments)<=999 and segments.start.iloc[0]==0 and segments.end.iloc[-1]==n-1
    assert np.array_equal(segments.end.to_numpy()[:-1],segments.start.to_numpy()[1:])


@pytest.mark.parametrize('values',[[10.]*10,[np.nan]*10,[1.,2.,np.nan,4.,5.,6.,7.,8.,9.,1e12]])
def test_position_colors_handle_constant_missing_and_extreme_measurements(values):
    frame=pd.DataFrame({'elapsed_s':np.arange(10)*.1,'pos_x':np.arange(10),
                        'pos_y':0.,'arbitrary_original':values,'text':['x']*10})
    channels=color_channels(frame)
    assert 'text' not in channels and ('arbitrary_original' in channels)==np.isfinite(values).any()
    segments,_=position_segments(frame,'arbitrary_original')
    fig=trajectory_figure(segments,frame,'arbitrary_original')
    assert len(fig.data)<=34
    assert all(trace.type=='scatter' for trace in fig.data)
    assert 'Infinity' not in fig.to_json()
    if max([v for v in values if np.isfinite(v)],default=0)>1e10:
        assert fig.data[0].marker.cmax==1e12


def test_all_suitable_color_channels_and_discrete_gear_legend():
    frame=fixture_session().data
    frame['original_numeric']=np.linspace(0,1,len(frame))
    frame['invalid']=np.nan
    assert {'original_numeric','speed_kmh','rpm','pos_x','gear'}<=set(color_channels(frame))
    assert 'invalid' not in color_channels(frame)
    segments,_=position_segments(frame,'gear')
    fig=trajectory_figure(segments,frame,'gear','integer')
    assert len(fig.data)==1 and fig.data[0].showlegend
    assert 'gear = 3' in fig.data[0].name


def test_comparison_has_one_shared_legend_and_stable_colors_across_channels():
    session=fixture_session()
    selections=[('source:2','Session / Lap 2',selected_frame(session,[2])),
                ('source:4','Session / Lap 4',selected_frame(session,[4]))]
    fig=comparison_figure(selections,['speed_kmh','rpm'],'lap_elapsed_s','Relative lap time',session)
    second=comparison_figure(selections,['rpm'],'lap_elapsed_s','Relative lap time',session)
    assert sum(bool(trace.showlegend) for trace in fig.data)==2
    assert fig.data[0].line.color==fig.data[1].line.color==second.data[0].line.color
    assert fig.data[2].line.color==fig.data[3].line.color==second.data[1].line.color
    assert fig.data[0].line.color!=fig.data[2].line.color
    assert max(fig.data[0].x)<1 and all(t.type=='scatter' for t in fig.data)


def test_signal_overlays_have_distinct_colors_and_bounded_rows():
    frame=pd.concat([pd.DataFrame({'elapsed_s':np.arange(2000)*.1,'lap_elapsed_s':np.arange(2000)*.1,
                                  'speed_kmh':100.,'_ui_lap':f'Lap {i}'}) for i in range(8)])
    session=fixture_session()
    script="""import streamlit as st
from motorsport_ui.telemetry import signal_chart
signal_chart(st.session_state['frame'],['speed_kmh'],st.session_state['session'],key='test_chart')
"""
    app=AppTest.from_string(script,default_timeout=45)
    app.session_state['frame']=frame
    app.session_state['session']=session
    app.run()
    assert not app.exception
    spec=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len({t['line']['color'] for t in spec['data']})==8
    assert all(t['type']=='scatter' for t in spec['data'])
    assert any('16,000 campioni' in c.value for c in app.caption)


def test_shared_laps_and_source_persist_through_sections_without_reloading(monkeypatch):
    session=fixture_session()
    calls=[]
    monkeypatch.setattr(ui,'source_catalog',lambda include_acgym=False:{'upload:test':'Fixture'})
    def load(key):
        calls.append(key)
        return session
    monkeypatch.setattr(ui,'get_source',load)
    app=AppTest.from_file(str(EXPLORER),default_timeout=45).run()
    app.multiselect(key='_explorer_laps').set_value([4]).run()
    for section in SECTIONS:
        app.radio(key='explorer_section').set_value(section).run()
        assert not app.exception
        assert app.session_state['telemetry_active_key']=='upload:test'
        assert app.session_state['explorer_selected_laps']==[4]
        assert app.multiselect(key='_explorer_laps').value==[4]


def test_actual_source_loader_runs_once_during_section_switches(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    fixture_session().raw.to_csv(tmp_path/'data/raw/session.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    original=ui.load_local;calls=[]
    def counted(key,signature):
        calls.append(key)
        return original(key,signature)
    monkeypatch.setattr(ui,'load_local',counted)
    app=AppTest.from_file(str(EXPLORER),default_timeout=45).run()
    for section in SECTIONS:
        app.radio(key='explorer_section').set_value(section).run()
        assert not app.exception
    assert len(calls)==1


def test_cockpit_renderer_displays_selected_packet_values(monkeypatch):
    session=fixture_session()
    monkeypatch.setattr(ui,'source_catalog',lambda include_acgym=False:{'upload:test':'Fixture'})
    monkeypatch.setattr(ui,'get_source',lambda key:session)
    app=AppTest.from_file(str(EXPLORER),default_timeout=45).run()
    app.multiselect(key='_explorer_laps').set_value([4]).run()
    app.radio(key='explorer_section').set_value('Cockpit').run()
    slider=next(s for s in app.slider if s.label=='Istante replay (s)')
    slider.set_value(.2).run()
    assert not app.exception
    assert any('Campione sorgente 12' in c.value for c in app.caption)
    assert any('112.0' in m.value and 'SPEED' in m.value for m in app.markdown)


@pytest.mark.parametrize('section',SECTIONS)
def test_every_section_handles_missing_channels(tmp_path,monkeypatch,section):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'other':[1.,2.,3.]}).to_csv(tmp_path/'data/raw/minimal.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(EXPLORER),default_timeout=45).run()
    app.radio(key='explorer_section').set_value(section).run()
    assert not app.exception


def test_overview_simplifies_presentation_preserves_weighted_mean_and_features(monkeypatch):
    session=fixture_session()
    monkeypatch.setattr(ui,'source_catalog',lambda include_acgym=False:{'upload:test':'Fixture'})
    monkeypatch.setattr(ui,'get_source',lambda key:session)
    app=AppTest.from_file(str(ROOT/'pages/10_Session_Overview.py'),default_timeout=45).run()
    assert not app.exception
    table=app.dataframe[0].value
    assert list(table)==['Channel','Time Measured [s]','Mean'] and not app.get('plotly_chart')
    assert table.iloc[0]['Mean']==overview_metrics(session.data)['signals']['speed_kmh']['time_mean']
    titles=[s.value for s in app.subheader]
    assert not any('pedali' in s.lower() or 'feature' in s.lower() for s in titles)
    unavailable=ui.unavailable_capabilities(session)
    assert len(unavailable)==sum(not c['available'] for c in assess_capabilities(session).values())
    assert len(lap_features(session))==2


@pytest.mark.parametrize('source',['original','gt7','acgym'])
def test_real_sources_all_sections_laps_fallback_and_invalidation(source,original_app):
    catalog=ui.source_catalog(include_acgym=True,include_original=True)
    if source=='original':
        key=str((ROOT/'data/raw/telemetry.parquet').resolve())
    elif source=='gt7':
        key=str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())
    else:
        key=next((k for k in catalog if k.startswith('acgym:')),None)
    if key not in catalog:
        pytest.skip('Audited local source unavailable')
    app=original_app(EXPLORER)
    if source=='original':
        key='upload:original'
    app.selectbox(key='explorer_source').set_value(key).run()
    assert not app.exception
    if source=='original':
        assert not app.session_state['explorer_selected_laps']
        app.slider(key='_explorer_range').set_value((10.,20.)).run()
    else:
        ids=list(app.multiselect(key='_explorer_laps').value)
        assert ids
        if source=='gt7':
            assert len(app.multiselect(key='_explorer_laps').options)==8
        session=app.session_state['telemetry_registry'][key]
        assert session.laps.available
        if source=='gt7':
            assert {'pos_x','pos_y'}<=set(session.data)
        if source=='acgym':
            assert {'tyre_core_fl','temp_i_fr','psi_rl','load_rr','susp_fl'}<=set(session.data)
            assert session.metadata['channel_units']['tyre_core_fl']=='°C'
        all_ids=list(lap_labels(session))
        app.multiselect(key='_explorer_laps').set_value(all_ids[:2]).run()
    for section in SECTIONS:
        app.radio(key='explorer_section').set_value(section).run()
        assert not app.exception
        if source=='original':
            assert app.session_state['explorer_time_range']==(10.,20.)
        else:
            assert app.session_state['explorer_selected_laps']==all_ids[:2]
    if source=='gt7':
        original='upload:original'
        app.selectbox(key='explorer_source').set_value(original).run()
        assert not app.exception and app.session_state['explorer_selected_laps']==[]
        assert app.session_state['explorer_time_range'] is not None


def test_acgym_cross_recording_comparison_and_incompatible_track_guard():
    keys=[k for k in ui.source_catalog(include_acgym=True) if k.startswith('acgym:')]
    if len(keys)<2:
        pytest.skip('Two local ACGym recordings required')
    app=AppTest.from_file(str(ROOT/'pages/14_Session_Comparison.py'),default_timeout=60).run()
    next(s for s in app.selectbox if s.label=='Sessione A').set_value(keys[0]).run()
    next(s for s in app.selectbox if s.label=='Sessione B').set_value(keys[1]).run()
    assert not app.exception and app.radio[0].value=='Giri verificati'
    assert len(app.get('iframe'))==1
    import re
    def component_spec(app):
        html=app.get('iframe')[0].proto.srcdoc
        return json.loads(re.search(r'id="comparison-data" type="application/json">(.*?)</script>',html,re.S).group(1))
    spec=component_spec(app)
    colors=[t['line']['color'] for t in spec['data']]
    app.multiselect[0].set_value(['rpm']).run()
    spec=component_spec(app)
    assert [t['line']['color'] for t in spec['data']]==[colors[0],colors[len(colors)//2]]
    gt7=str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())
    if gt7 in ui.source_catalog():
        next(s for s in app.selectbox if s.label=='Sessione B').set_value(gt7).run()
        assert not app.exception and not app.get('plotly_chart')
        assert any('tracciato comune non verificata' in i.value for i in app.info)


def test_navigation_has_only_consolidated_analytics_routes():
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=45).run()
    assert not app.exception
    source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
    for legacy_analytics in ('11_Driver_Inputs.py','12_Vehicle_Dynamics.py','13_Tyre_Analysis.py','15_Position_Analysis.py'):
        assert f"st.Page('pages/{legacy_analytics}'" not in source
    for route in ('overview','comparison','ml','replay'):
        assert f"url_path='{route}'" in source
