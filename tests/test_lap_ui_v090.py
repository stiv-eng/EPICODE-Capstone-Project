import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from conftest import chart_specs

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c').exists(),reason='Local GT7 recording unavailable')
def test_actual_page_laps_thresholds_metric_cursor_and_cached_corner_selection(monkeypatch):
    import motorsport_ui.lap_analysis_v090 as ui
    original=ui.analyze_laps
    calls=[]
    def counted(*args,**kwargs):
        calls.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(ui,'analyze_laps',counted)
    ui.cached_analysis.clear()
    app=AppTest.from_file(str(ROOT/'pages/16_Telemetry_Lap_Analysis.py'),default_timeout=120).run()
    assert not app.exception and len(calls)==1
    assert next(n for n in app.number_input if n.key=='lap_analysis_radius').value==150.
    assert next(m for m in app.metric if m.label=='Differenza totale misurata').value=='+0.094 s'
    specs=chart_specs(app)
    assert len(specs)==4
    distance=[s for s in specs if s['layout'].get('meta',{}).get('cursor_unit')=='m']
    assert len(distance)==2 and all(s['layout']['meta']['temporal_axis'] is False for s in distance)
    corner=next(s for s in app.selectbox if s.key=='lap_analysis_corner')
    corner.set_value(corner.options[1]).run()
    assert not app.exception and len(calls)==1
    next(n for n in app.number_input if n.key=='lap_analysis_radius').set_value(200.).run()
    assert not app.exception and len(calls)==2
    assert any('raggio soglia 200' in c.value for c in app.caption)
    next(c for c in app.checkbox if c.key=='lap_analysis_maximum').check().run()
    assert not app.exception and len(calls)==2
    assert any('Maximum-curvature point' in t.get('name','') for s in chart_specs(app) for t in s['data'])


def test_page_reports_missing_geometry_without_fabricated_coordinates(monkeypatch):
    import numpy as np
    import motorsport_ui.lap_analysis_v090 as ui
    import motorsport_ui.telemetry as telemetry
    from motorsport.pipeline import build_session
    from motorsport.processing.laps import LapResult
    t=np.arange(1001)*.05
    f=pd.DataFrame(dict(elapsed_s=t,lap_elapsed_s=t,speed_kmh=100.,brake_pct=0.,throttle_pct=50.))
    timing=LapResult(True,'independently witnessed fixture timing',pd.DataFrame([dict(lap_id=1,start_sample=0,end_sample=len(f),start_s=0.,end_s=50.,duration_s=50.)]))
    session=build_session(f,dict(filename='unit-unknown.csv',session_id='fixture:missing-xy'),validated_laps=timing,lap_elapsed=t)
    for module in (ui,telemetry):
        monkeypatch.setattr(module,'source_catalog',lambda include_acgym=False:{'upload:missing-xy':'Fixture'})
        monkeypatch.setattr(module,'get_source',lambda key:session)
    ui.cached_analysis.clear();ui.cached_spatial.clear()
    app=AppTest.from_file(str(ROOT/'pages/16_Telemetry_Lap_Analysis.py'),default_timeout=60).run()
    assert not app.exception
    assert any('Analisi spaziale non disponibile' in w.value for w in app.warning)
    assert not chart_specs(app)
    assert next(m for m in app.metric if m.label=='Differenza totale misurata').value=='+0.000 s'


def test_distance_cursor_is_explicit_and_default_temporal_readout_is_preserved():
    import plotly.graph_objects as go
    from motorsport_ui.hover import prepare_figure
    fig=go.Figure(go.Scatter(x=[0.,1.5,3.],y=[1.,2.,3.]))
    fig.update_layout(meta=dict(cursor_unit='m',cursor_label='s',temporal_axis=False))
    prepared=prepare_figure(fig,'time')
    assert prepared.layout.meta['cursor_unit']=='m' and prepared.layout.meta['cursor_label']=='s'
    default=prepare_figure(go.Figure(go.Scatter(x=[0.,1.],y=[1.,2.])),'time')
    assert 'cursor_unit' not in default.layout.meta
    html=(ROOT/'motorsport_ui/hover.html').read_text(encoding='utf-8')
    assert "cursorMeta.cursor_unit||'s'" in html and "cursorMeta.cursor_label||'t'" in html
    assert 'streamlit:setComponentValue' not in html
