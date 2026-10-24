"""Hover presentation contracts; the Chrome suite validates event/axis geometry."""
import ast
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytest

from motorsport.pipeline import build_session
from motorsport.analytics.position import position_segments
from motorsport_ui.hover import observed_tolerance,prepare_figure,figure_specs
from motorsport_ui.visuals import comparison_figure,trajectory_figure

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('times,expected',[
    ([],0),([0],0),([0,0,0],0),([0,.1,.2,100.2],.051),
    ([0,np.nan,2,2.1,2.2],.051),([3,2,1],0)])
def test_original_cadence_excludes_gaps_nulls_duplicates_and_backwards(times,expected):
    assert observed_tolerance(times)==pytest.approx(expected)


@pytest.mark.parametrize('kind',['scatter','histogram','bar','box','time'])
def test_shared_preparation_is_numeric_and_geometry_preserving(kind):
    frame=pd.DataFrame({'x':[0.,1.,2.,3.],'y':[2.,np.nan,4.,8.]})
    fig=(px.line(frame,x='x',y='y') if kind=='time' else getattr(px,kind)(frame,x='x',y='y'))
    fig.update_yaxes(scaleanchor='x',scaleratio=1)
    before=fig.to_json()
    prepared=prepare_figure(fig,'time' if kind=='time' else 'xy')
    assert fig.to_json()==before
    for original,trace in zip(fig.data,prepared.data):
        np.testing.assert_equal(trace.x,original.x)
        np.testing.assert_equal(trace.y,original.y)
        assert trace.hoverinfo=='none' and trace.hovertemplate is None
    assert prepared.layout.yaxis.scaleanchor=='x'
    assert prepared.layout.yaxis.scaleratio==1


def test_selection_slots_disambiguate_same_lap_same_source_and_same_labels():
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2],'speed_kmh':[50.,np.nan,70.]})
    session=build_session(frame,{'filename':'session'})
    fig=comparison_figure([('source:lap:2','Lap 2',frame),('source:lap:2','Lap 2',frame)],
                          ['speed_kmh'],'elapsed_s','seconds',session)
    prepared=prepare_figure(fig,'time')
    rows=prepared.layout.meta['hover_selections']
    assert [r['id'] for r in rows]==['0:source:lap:2','1:source:lap:2']
    assert rows[0]['color']!=rows[1]['color']
    assert all(t.meta['tolerance']==pytest.approx(.051) for t in prepared.data)
    assert all(t.customdata[0][0]=='0' for t in prepared.data)
    assert all(np.isnan(t.y[1]) for t in prepared.data)


def test_distinct_recordings_same_lap_remain_distinct_and_channel_changes_keep_colors():
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2],'speed_kmh':[1.,2.,3.],'rpm':[5.,6.,7.]})
    session=build_session(frame,{'filename':'source'})
    selections=[('sessionA:lap:2','Lap 2',frame),('sessionB:lap:2','Lap 2',frame)]
    a=prepare_figure(comparison_figure(selections,['speed_kmh','rpm'],'elapsed_s','seconds',session),'time')
    b=prepare_figure(comparison_figure(selections,['rpm'],'elapsed_s','seconds',session),'time')
    assert a.layout.meta['hover_selections']==b.layout.meta['hover_selections']
    assert len(a.layout.meta['hover_selections'])==2
    for t in a.data:
        row=next(r for r in a.layout.meta['hover_selections'] if r['id']==t.meta['selection_id'])
        assert row['color']==t.line.color


def test_position_endpoints_show_their_own_sample_and_measurement_not_segment_start():
    frame=pd.DataFrame({'elapsed_s':[0.,.1,.2,.3],'pos_x':[0.,1.,2.,3.],
                        'pos_y':[0.,1.,2.,3.],'speed_kmh':[50.,60.,70.,80.]},index=[10,11,12,13])
    segments,_=position_segments(frame,'speed_kmh',max_points=2)
    fig=trajectory_figure(segments,frame,'speed_kmh','km/h')
    trace=next(t for t in fig.data if t.mode=='lines')
    assert trace.customdata[0]==['10',50.] and trace.customdata[1]==['13',80.]
    assert len(fig.layout.shapes)==0


def test_grouped_payload_contains_no_plotly_runtime_and_maintains_modes():
    specs=figure_specs([(go.Figure(go.Scatter(x=[0.,1.],y=[2.,3.])),'time'),
                        (go.Figure(go.Scatter(x=[2.,3.],y=[4.,5.])),'xy')])
    assert [s['layout']['meta']['hover_mode'] for s in specs]==['time','xy']
    assert len(json.dumps(specs))<20000
    html=(ROOT/'motorsport_ui/hover.html').read_text(encoding='utf-8')
    assert html.count("new URL('plotly.min.js'")==1 and "caches.open('motorsport-plotly-runtime-v1')" in html
    assert 'streamlit:setComponentValue' not in html


def test_streamlit_palette_tokens_are_resolved_without_changing_color_measurements():
    fig=go.Figure(go.Scatter(x=[0.,1.],y=[2.,3.],mode='markers',
                            marker=dict(color=[10.,20.],coloraxis='coloraxis')))
    fig.update_layout(coloraxis=dict(colorscale=[[0,'#000011'],[1,'#000020']]))
    prepared=prepare_figure(fig)
    np.testing.assert_equal(prepared.data[0].marker.color,[10.,20.])
    assert all(not color.startswith('#0000') for _,color in prepared.layout.coloraxis.colorscale)
    bar=prepare_figure(go.Figure(go.Bar(x=['feature'],y=[.3],marker_color='#000001')))
    assert bar.data[0].marker.color=='#636EFA'
    assert bar.layout.yaxis.automargin


def test_unordered_temporal_trace_is_flagged_for_safe_bounded_search():
    fig=go.Figure(go.Scatter(x=[0.,2.,1.,np.nan],y=[1.,2.,3.,4.]))
    prepared=prepare_figure(fig,'time')
    assert prepared.data[0].meta['ordered_time'] is False
    np.testing.assert_equal(prepared.data[0].x,fig.data[0].x)


def test_clockless_signal_index_is_not_presented_as_measured_time():
    from streamlit.testing.v1 import AppTest
    from conftest import chart_specs
    app=AppTest.from_file(str(ROOT/'scripts/hover_fixture_app.py'),default_timeout=30).run()
    assert not app.exception
    spec=chart_specs(app)[-1]
    assert spec['layout']['meta']['hover_mode']=='xy'
    assert spec['layout']['meta']['temporal_axis'] is False
    assert spec['layout']['xaxis']['title']['text']=='Indice campione sorgente (tempo non disponibile)'
    assert 'Campione sorgente' in spec['data'][0]['meta']['readout_template']


def test_all_chart_rendering_uses_shared_api_including_optional_legacy():
    for directory in ('pages','motorsport_ui'):
        for path in (ROOT/directory).glob('*.py'):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                           and n.func.attr in {'plotly_chart','line_chart','altair_chart','scatter_chart'}
                           for n in ast.walk(tree)),path


def test_computation_and_launch_sources_unchanged_from_verified_v062():
    protected=['motorsport','motorsport_prediction','motorsport_ui/ml.py','.vscode','requirements.txt']
    r=subprocess.run(['git','diff','--name-only','48e99ee','--',*protected],cwd=ROOT,
                     capture_output=True,text=True,check=True)
    assert not r.stdout.strip()


def test_replay_payload_is_explicitly_prefix_and_prediction_only():
    # Real replay/training behavior is also exercised by the retained ML UI tests.
    source=(ROOT/'pages/21_Progressive_Prediction.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    rendering=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Expr)
                   and isinstance(n.value,ast.Call) and getattr(n.value.func,'id','')=='render_figures')
    reveal=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.If)
                and isinstance(n.test,ast.Call) and getattr(n.test.func,'attr','')=='checkbox')
    assert rendering<reveal
    assert "signals=prefix[['lap_elapsed_s','speed_kmh','throttle_pct','brake_pct']]" in source
    assert "pd.DataFrame([asdict(p) for p in predictions]).drop(columns='quality')" in source
