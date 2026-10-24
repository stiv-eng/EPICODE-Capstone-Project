from conftest import chart_specs
"""Real source availability, equal data scales, vehicle geometry and hover contract."""
import hashlib
import io
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest

from motorsport.pipeline import build_session,load_session
from motorsport.analytics.channels import usable_channels
from motorsport.analytics.position import position_adjacency
from motorsport.analytics.orientation import transform_heading,vehicle_orientation
from motorsport_ui.gg import gg_figure
from motorsport_ui.vehicle import add_vehicle
from motorsport_ui.visuals import comparison_figure
from motorsport_ui.comparison_hover import comparison_document
from motorsport_ui.explorer_source import upload_session
import motorsport_ui.telemetry as ui
from scripts.assess_ml_v062 import write_evidence,protected_state

ROOT=Path(__file__).resolve().parents[1]


def trajectory(points):
    points=np.asarray(points,dtype=float)
    return pd.DataFrame({'elapsed_s':np.arange(len(points))*.1,'pos_x':points[:,0],'pos_y':points[:,1]})


def test_catalog_hides_only_the_audited_original_and_keeps_parquet_replacements(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    original=tmp_path/'data/raw/telemetry.parquet'
    pd.DataFrame({'elapsed_s':[0.,1.],'speed_kmh':[50.,60.]}).to_parquet(original)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    monkeypatch.setattr(ui,'SUPPLIED_HASH',hashlib.sha256(original.read_bytes()).hexdigest())
    assert str(original.resolve()) not in ui.source_catalog()
    assert str(original.resolve()) in ui.source_catalog(include_original=True)
    pd.DataFrame({'elapsed_s':[0.,1.],'speed_kmh':[70.,80.]}).to_parquet(original)
    assert str(original.resolve()) in ui.source_catalog()
    (tmp_path/'docs').mkdir()
    (tmp_path/'data/raw/acgym_monza_dallara').mkdir()
    (tmp_path/'data/raw/acgym_monza_dallara/record.ld').write_bytes(b'catalog-only fixture')
    (tmp_path/'docs/ACGYM_MANIFEST_V06.json').write_text(json.dumps({'files':[
        {'path':'record.ld','driver_label':'AB','recording_label':'20240426_AB'}]}))
    assert next(iter(ui.source_catalog(include_acgym=True)))=='acgym:record.ld'


def test_gt7_is_default_when_installed_and_original_is_not_a_demo():
    sources=ui.source_catalog(include_acgym=True)
    gt7=str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())
    if gt7 not in sources:
        pytest.skip('Pinned GT7 source unavailable')
    assert next(iter(sources))==gt7
    assert str((ROOT/'data/raw/telemetry.parquet').resolve()) not in sources
    app=AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'),default_timeout=60).run()
    assert not app.exception and app.session_state['telemetry_active_key']==gt7


@pytest.mark.parametrize('extension',['csv','parquet'])
def test_generic_upload_formats_remain_compatible(extension):
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2],'speed_kmh':[50.,60.,70.]})
    stream=io.BytesIO()
    if extension=='parquet':frame.to_parquet(stream,index=False)
    else:stream.write(frame.to_csv(index=False).encode())
    session=upload_session(stream.getvalue(),'uploaded.'+extension)
    np.testing.assert_allclose(session.data.speed_kmh,[50,60,70])
    assert len(session.data)==3


def test_original_explicit_parquet_upload_preserves_audited_mapping():
    path=ROOT/'data/raw/telemetry.parquet'
    if not path.exists():pytest.skip('Original unavailable')
    session=upload_session(path.read_bytes(),path.name)
    assert len(session.data)==116987 and not session.laps.available
    assert {'elapsed_s','pos_x','pos_y','rpm'}<=set(session.data)


def test_availability_rejects_nonfinite_text_complex_boolean_preserves_constant():
    frame=pd.DataFrame({'good':[0.,1.,np.nan],'constant':20.,'missing':np.nan,'infinite':np.inf,
                        'text':['1','2','3'],'complex':[1j,2j,3j],'flag':[True,False,True]})
    assert usable_channels(frame)==['good','constant']
    assert usable_channels(frame,include_bool=True)==['good','constant','flag']
    assert usable_channels(frame.iloc[:0])==[]


def test_families_and_signal_selectors_filter_unusable_channels_and_reset_stale_values(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2],'speed_kmh':[50.,60.,70.],
                        'rpm':np.nan,'gear':['bad']*3,'tyre_core_fl':np.nan,'temp_i_fl':[20.,20.,20.],
                        'psi_fr':np.inf,'susp_fl':np.nan,'load_fl':[100.,100.,100.]})
    frame.to_csv(tmp_path/'data/raw/first.csv',index=False)
    frame.drop(columns=['load_fl','temp_i_fl']).assign(wheel_rps_fl=20.).to_csv(tmp_path/'data/raw/second.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'),default_timeout=45).run()
    assert not app.exception
    assert 'rpm' not in app.multiselect(key='explorer_channels').options
    app.radio(key='explorer_section').set_value('Vehicle Dynamics').run()
    assert app.selectbox(key='dynamics_family_choice').options==['Wheel loads']
    app.radio(key='explorer_section').set_value('Tyre Analysis').run()
    assert app.selectbox(key='tyre_family').options==['Inner temperature','Wheel load']
    app.selectbox(key='explorer_source').set_value(str((tmp_path/'data/raw/second.csv').resolve())).run()
    assert not app.exception and app.selectbox(key='tyre_family').options==['Wheel speed']
    app.radio(key='explorer_section').set_value('Vehicle Dynamics').run()
    assert not app.exception and app.selectbox(key='dynamics_family_choice').options==['Wheel speeds']


def test_no_empty_family_selector_is_created(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'speed_kmh':[np.nan,np.nan],'temp_i_fl':[np.nan,np.nan]}).to_csv(tmp_path/'data/raw/none.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'),default_timeout=45).run()
    assert not app.exception and not app.multiselect
    for section,key in [('Tyre Analysis','tyre_family'),('Vehicle Dynamics','dynamics_family_choice')]:
        app.radio(key='explorer_section').set_value(section).run()
        assert not app.exception and not any(s.key==key for s in app.selectbox)


def test_gg_scales_are_constrained_equal_with_full_extent_and_incompatible_units_refused():
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2],'g_lat':[-5.,0.,6.],'g_lon':[-1.,2.,3.]})
    session=build_session(frame,{'filename':'GG','channel_units':{'g_lat':'g','g_lon':'g'}})
    figure=gg_figure(session,session.data)
    assert figure.layout.yaxis.scaleanchor=='x' and figure.layout.yaxis.scaleratio==1
    assert figure.layout.xaxis.range==figure.layout.yaxis.range
    assert figure.layout.xaxis.range[0]<-5 and figure.layout.xaxis.range[1]>6
    assert figure.layout.xaxis.constrain==figure.layout.yaxis.constrain=='domain'
    session.metadata['channel_units']['g_lon']='m/s²'
    assert gg_figure(session,session.data) is None


@pytest.mark.parametrize('delta,expected',[( (1,0),0),((1,1),np.pi/4),((-1,1),3*np.pi/4),
    ((-1,-1),-3*np.pi/4),((1,-1),-np.pi/4),((0,1),np.pi/2),((0,-1),-np.pi/2),((-1,0),np.pi)])
def test_atan2_quadrants_vertical_and_reverse(delta,expected):
    frame=trajectory([(0,0),delta,np.asarray(delta)*2])
    theta,source=vehicle_orientation(frame,0,{})
    assert theta==pytest.approx(expected) and 'estimated' in source


@pytest.mark.parametrize('case',['stationary','near_zero','missing','time_gap','lap_change','spatial_jump','removed_row'])
def test_orientation_respects_actual_fragment_boundaries(case):
    frame=trajectory([(0,0),(1,0),(2,0),(3,0),(4,0)])
    if case=='stationary':frame.loc[1,['pos_x','pos_y']]=[0,0]
    if case=='near_zero':frame.loc[1,['pos_x','pos_y']]=[1e-14,0]
    if case=='missing':frame.loc[1,'pos_x']=np.nan
    if case=='time_gap':frame.loc[1:,'elapsed_s']+=10
    if case=='lap_change':frame['lap_id']=[1,2,2,2,2]
    if case=='spatial_jump':frame.loc[0,'pos_x']=-1000
    if case=='removed_row':frame.index=[0,2,3,4,5]
    theta,source=vehicle_orientation(frame,0,{})
    assert theta is None and 'unavailable' in source


def test_final_packet_uses_valid_backward_difference_and_untrusted_angles_are_not_used():
    frame=trajectory([(0,0),(0,1),(0,2)])
    frame['rot_z']=999.
    theta,label=vehicle_orientation(frame,2,{'channel_units':{'rot_z':'unknown'}})
    assert theta==pytest.approx(np.pi/2) and 'backward' in label
    frame.loc[1,'pos_x']=np.nan
    assert vehicle_orientation(frame,2,{})[0] is None


@pytest.mark.parametrize('unit,angle,zero,rotation,handedness,matrix,expected',[
    ('deg',90,[1,0],'ccw','right',None,np.pi/2),('rad',np.pi/2,[1,0],'cw','right',None,-np.pi/2),
    ('deg',90,[0,1],'ccw','right',None,np.pi),('deg',90,[1,0],'ccw','left',None,-np.pi/2),
    ('deg',0,[1,0],'cw','right',[[0,1],[1,0]],np.pi/2)])
def test_verified_heading_transform_conventions(unit,angle,zero,rotation,handedness,matrix,expected):
    assert transform_heading(angle,unit,zero,rotation,handedness,matrix)==pytest.approx(expected)


def test_measured_heading_requires_complete_verified_metadata_and_declared_units():
    frame=trajectory([(0,0),(1,0),(2,0)]);frame['heading']=90.
    convention={'verified':True,'channel':'heading','unit':'deg','zero_vector':[1,0],
                'positive_rotation':'ccw','handedness':'right','coordinate_columns':['pos_x','pos_y'],
                'provenance':'synthetic verified convention'}
    metadata={'channel_units':{'heading':'deg'},'planar_heading':convention}
    theta,description=vehicle_orientation(frame,0,metadata)
    assert theta==pytest.approx(np.pi/2) and 'measured' in description
    convention['verified']=False
    assert vehicle_orientation(frame,0,metadata)[0]==0
    convention['verified']=True;metadata['channel_units']['heading']='unknown'
    assert vehicle_orientation(frame,0,metadata)[0]==0


def test_car_shapes_anchor_to_selected_sample_and_keep_pixel_size_under_zoom():
    figure=add_vehicle(go.Figure(),12.,-8.,np.pi/2,'estimated')
    assert len(figure.layout.shapes)==6
    assert all(s.xanchor==12. and s.yanchor==-8. and s.xsizemode==s.ysizemode=='pixel' for s in figure.layout.shapes)
    assert figure.data[-1].x[0]==12 and figure.data[-1].y[0]==-8
    paths=[s.path for s in figure.layout.shapes]
    figure.update_xaxes(range=[-100,100]);figure.update_yaxes(range=[-100,100])
    assert paths==[s.path for s in figure.layout.shapes]
    neutral=add_vehicle(go.Figure(),12.,-8.,None,'unavailable')
    assert not neutral.layout.shapes and neutral.data[-1].marker.symbol is None


def test_stationary_coordinates_render_a_neutral_measured_position(tmp_path,monkeypatch):
    (tmp_path/'data/raw').mkdir(parents=True)
    trajectory([(12.,-8.)]*3).to_csv(tmp_path/'data/raw/stationary.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/00_Data_Explorer.py'),default_timeout=45).run()
    app.radio(key='explorer_section').set_value('Position / Track Map').run()
    assert not app.exception and len(chart_specs(app))==1
    figure=chart_specs(app)[0]
    assert figure['layout']['meta']['vehicle_theta'] is None
    assert figure['layout']['meta']['vehicle_x']==12 and figure['layout']['meta']['vehicle_y']==-8
    assert not figure['layout'].get('shapes')


def test_marker_slider_tracks_real_source_sample_without_rebuilding_geometry(original_app,monkeypatch):
    import motorsport_ui.position as position_ui
    position_ui.trajectory_base.clear()
    original=position_ui.position_segments
    calls=[]
    def counted(frame,color):
        calls.append(len(frame))
        return original(frame,color)
    monkeypatch.setattr(position_ui,'position_segments',counted)
    app=original_app(ROOT/'pages/00_Data_Explorer.py')
    app.radio(key='explorer_section').set_value('Position / Track Map').run()
    app.slider(key='position_instant').set_value(100).run()
    assert not app.exception
    figure=chart_specs(app)[0]
    point=app.dataframe[-1].value.iloc[0]
    session=app.session_state['telemetry_registry']['upload:original']
    assert figure['layout']['meta']['vehicle_sample']=='100'
    assert figure['layout']['meta']['vehicle_x']==pytest.approx(float(session.data.pos_x.iloc[100]))
    assert point.elapsed_s==session.data.elapsed_s.iloc[100]
    assert len(calls)==1


def test_comparison_readout_keeps_numeric_units_identity_legend_and_escapes_labels():
    session=build_session(pd.DataFrame({'elapsed_s':[0.,1.],'speed_kmh':[50.,60.]}),{'filename':'source'})
    frame=session.data.assign(relative_s=[0.,1.])
    figure=comparison_figure([('a','Lap <unsafe>',frame),('b','Window B',frame)],['speed_kmh'],'relative_s','seconds',session)
    assert sum(bool(t.showlegend) for t in figure.data)==2
    assert all(t.hoverinfo=='none' and t.meta['unit']=='km/h' for t in figure.data)
    document=comparison_document(figure)
    payload=re.search(r'id="comparison-data" type="application/json">(.*?)</script>',document,re.S).group(1)
    assert '<unsafe>' not in payload
    assert json.loads(payload)['data'][0]['name']=='Lap <unsafe>'
    assert "chart.on('plotly_hover'" in document and 'readout-column' in document and '<script src=' not in document


def test_diagnostic_writer_rejects_original_results_and_model_artifacts(tmp_path,monkeypatch):
    before=protected_state()
    for path in [ROOT/'docs/ML_RESULTS_V06.json',ROOT/'docs/ACGYM_ML_ERRORS_V06.csv',ROOT/'artifacts/models/model.joblib',tmp_path/'any.json']:
        with pytest.raises(ValueError,match='separate v0.6.2'):
            write_evidence(path,'changed')
    assert before==protected_state()
    import scripts.assess_ml_v062 as audit
    output=tmp_path/'ML_HEALTH_GROUPS_V062.csv'
    monkeypatch.setattr(audit,'ALLOWED_OUTPUTS',{output})
    write_evidence(output,'channel,value\nspeed,50\n')
    assert output.read_bytes()==b'channel,value\nspeed,50\n'


def test_ml_production_sources_and_launch_are_unchanged():
    import subprocess
    files=['motorsport/ml','motorsport_prediction','.vscode']
    result=subprocess.run(['git','diff','--name-only','--diff-filter=M','c47fd4a','--',*files],cwd=ROOT,capture_output=True,text=True,check=True)
    assert not result.stdout.strip()
