from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import motorsport_ui.telemetry as ui
from motorsport.analytics.position import position_view

ROOT=Path(__file__).resolve().parents[1]
PAGES=['10_Session_Overview.py','11_Driver_Inputs.py','12_Vehicle_Dynamics.py',
       '13_Tyre_Analysis.py','14_Session_Comparison.py','15_Position_Analysis.py']


def test_position_inputs_and_straight_trajectory():
    frame=pd.DataFrame({'pos_x':[0,1,2,np.nan],'pos_y':[0,0,0,1],'speed_kmh':100})
    trace,stats=position_view(frame)
    assert len(trace)==3 and stats['invalid_positions']==1 and stats['varying']
    empty,stats=position_view(pd.DataFrame({'speed_kmh':[1,2]}))
    assert empty.empty and stats['finite_positions']==0


@pytest.mark.parametrize('page',PAGES)
def test_pages_handle_missing_and_constant_channels(tmp_path,monkeypatch,page):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'elapsed_s':[0,.1,.2,.3], 'speed_kmh':100}).to_csv(tmp_path/'data/raw/minimal.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages'/page),default_timeout=45).run()
    assert not app.exception


@pytest.mark.skipif(not (ROOT/'data/raw/telemetry.parquet').exists(),reason='Original local attachment absent')
@pytest.mark.parametrize('page',PAGES)
def test_new_pages_plot_real_original_dataset(page,original_app):
    app=original_app(ROOT/'pages'/page)
    assert not app.exception
    assert len(app.get('plotly_chart'))+len(app.get('iframe')) >= (0 if page=='10_Session_Overview.py' else 1)
    if page=='10_Session_Overview.py':
        assert list(app.dataframe[0].value)==['Channel','Time Measured [s]','Mean']
        assert len(app.get('plotly_chart'))==0


def test_saved_windows_remain_session_windows(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'elapsed_s':np.arange(100)*.1,'speed_kmh':100}).to_csv(tmp_path/'data/raw/session.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/14_Session_Comparison.py'),default_timeout=45).run()
    save=next(button for button in app.button if button.label=='Salva finestra A')
    save.click().run()
    assert not app.exception
    assert len(app.session_state['comparison_windows'])==1
    assert app.session_state['comparison_windows'][0]['window'].label=='Session window A'
    app.radio[0].set_value('Giri verificati').run()
    assert not app.exception
    assert any('Modalità giri non disponibile' in info.value for info in app.info)


def test_registered_file_is_invalidated_after_replacement(tmp_path):
    path=tmp_path/'source.csv'
    path.write_text('elapsed_s,speed_kmh\n0,100\n1,100\n')
    source=f'''from pathlib import Path
import streamlit as st
from motorsport_ui.telemetry import get_source,register_session
path={str(path)!r}
session=get_source(path)
register_session(session,path)
st.metric('Speed',session.metrics['speed_kmh_max'])
'''
    app=AppTest.from_string(source,default_timeout=45).run()
    assert app.metric[0].value=='100.0'
    path.write_text('elapsed_s,speed_kmh\n0,200\n1,200\n2,200\n')
    app.run()
    assert not app.exception and app.metric[0].value=='200.0'


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c/data/laps/lap_015.parquet').exists(),reason='GT7 local bundle absent')
def test_gt7_comparison_and_features_ui():
    app=AppTest.from_file(str(ROOT/'pages/14_Session_Comparison.py'),default_timeout=60).run()
    bundle=str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())
    next(s for s in app.selectbox if s.label=='Sessione A').set_value(bundle)
    next(s for s in app.selectbox if s.label=='Sessione B').set_value(bundle)
    app.radio[0].set_value('Giri verificati').run()
    assert not app.exception and len(app.get('iframe'))==1
    assert any('shared track-distance' in info.value for info in app.info)


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c/data/laps/lap_015.parquet').exists(),reason='GT7 local bundle absent')
@pytest.mark.parametrize('page,key',[(p,k) for p,k in zip(PAGES,['overview','inputs','dynamics','tyres','comparison','position']) if k!='comparison'])
def test_gt7_analytical_pages(page,key):
    app=AppTest.from_file(str(ROOT/'pages'/page),default_timeout=60).run()
    app.selectbox(key=f'{key}_source').set_value(str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())).run()
    assert not app.exception
    assert len(app.get('plotly_chart')) >= (0 if key=='overview' else 1)
    if key=='tyres':
        next(s for s in app.selectbox if s.label=='Famiglia pneumatici').set_value('Wheel speed').run()
        assert not app.exception and len(app.get('plotly_chart'))==1


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c/data/laps/lap_015.parquet').exists(),reason='GT7 local bundle absent')
def test_gt7_bundle_in_data_explorer():
    app=AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'),default_timeout=60).run()
    selector=app.selectbox(key='explorer_source')
    selector.set_value(str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())).run()
    assert not app.exception
    assert len(app.multiselect(key='_explorer_laps').options)==8


def test_offline_overview_blocks_legacy_imports(tmp_path,monkeypatch):
    import importlib.abc
    import sys
    class BlockLegacy(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in {'fastf1','keras','torch'}:
                raise ImportError('No legacy libraries in local analysis')
    monkeypatch.setattr(sys,'meta_path',[BlockLegacy()]+sys.meta_path)
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'elapsed_s':[0,.1,.2],'speed_kmh':[100,110,120]}).to_csv(tmp_path/'data/raw/offline.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/10_Session_Overview.py'),default_timeout=45).run()
    assert not app.exception
