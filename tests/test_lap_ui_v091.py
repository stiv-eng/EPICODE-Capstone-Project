"""Source-bound widgets and presentation regressions for the v091 fixes."""
from pathlib import Path

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from motorsport.pipeline import build_session
from motorsport.processing.laps import LapResult

ROOT=Path(__file__).resolve().parents[1]


def session(key,track,car,ids=(1,2),duration=2.):
    count=41
    t=np.arange(count)*duration/(count-1)
    frame=pd.DataFrame(dict(elapsed_s=np.r_[t,t+duration+.1],speed_kmh=100.))
    timing=LapResult(True,'witnessed synthetic test boundaries',pd.DataFrame([
        dict(lap_id=value,start_sample=i*count,end_sample=(i+1)*count,
             start_s=i*(duration+.1),end_s=i*(duration+.1)+duration,duration_s=duration+i*.05)
        for i,value in enumerate(ids)]))
    return build_session(frame,dict(filename=key,session_id=key,track_id=track,car_id=car),
                         validated_laps=timing,lap_elapsed=np.tile(t,2))


def select(app,label,value):
    next(s for s in app.selectbox if s.label==label).set_value(value).run()
    assert not app.exception


def test_session_switches_bind_laps_to_source_revision_and_restore_valid_choices(monkeypatch):
    import motorsport_ui.telemetry as telemetry
    import motorsport_ui.lap_analysis_v090 as ui
    sources={
        'upload:porsche':session('porsche','gt7','porsche'),
        'upload:barcelona':session('barcelona','barcelona','dallara',duration=3.),
        'upload:barcelona-b':session('barcelona-b','barcelona','dallara',ids=(3,4),duration=4.),
        'upload:monza':session('monza','monza','dallara'),
        'upload:other-car':session('other-car','barcelona','other'),
    }
    for module in (telemetry,ui):
        monkeypatch.setattr(module,'source_catalog',lambda include_acgym=False:{k:k for k in sources})
        monkeypatch.setattr(module,'get_source',lambda key:sources[key])
    ui.cached_analysis.clear();ui.cached_spatial.clear()
    app=AppTest.from_file(str(ROOT/'pages/16_Telemetry_Lap_Analysis.py')).run()
    assert not app.exception
    select(app,'Giro di riferimento',2)
    select(app,'Giro analizzato',1)
    select(app,'Sessione di riferimento','upload:barcelona')
    assert next(s for s in app.selectbox if s.label=='Giro di riferimento').value==1
    assert next(m for m in app.metric if m.label=='Tempo riferimento').value=='3.000 s'
    # Registry metadata filters incompatible sessions without inspecting payloads.
    app.session_state['telemetry_registry']=sources
    app.run()
    options=next(s for s in app.selectbox if s.label=='Sessione del giro analizzato').options
    assert options==['upload:barcelona','upload:barcelona-b']
    select(app,'Sessione del giro analizzato','upload:barcelona-b')
    assert next(s for s in app.selectbox if s.label=='Giro analizzato').options[0].startswith('Lap 3 ')
    select(app,'Giro analizzato',4)
    select(app,'Sessione di riferimento','upload:porsche')
    assert next(s for s in app.selectbox if s.label=='Giro di riferimento').value==2
    assert next(s for s in app.selectbox if s.label=='Giro analizzato').value==1
    select(app,'Sessione di riferimento','upload:barcelona')
    assert next(s for s in app.selectbox if s.label=='Sessione del giro analizzato').value=='upload:barcelona-b'
    assert next(s for s in app.selectbox if s.label=='Giro analizzato').value==4
    # Replace the source under the same key: an old lap ID must not survive.
    sources['upload:barcelona-b']=session('barcelona-b-v2','barcelona','dallara',ids=(7,8),duration=5.)
    app.session_state['telemetry_registry']=sources
    app.run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label=='Giro analizzato').value==7


def test_kpi_labels_cover_existing_metrics_without_mutating_json_identifiers():
    from motorsport.lap_analysis.kpis import SPECS
    from motorsport_ui.lap_analysis_v090 import KPI_LABELS,kpi_label
    assert set(KPI_LABELS)==set(SPECS)
    metric=dict(name='steering_at_apex',unit='deg')
    assert kpi_label(metric)=='Steering at Apex [deg]'
    assert metric==dict(name='steering_at_apex',unit='deg')
    assert kpi_label(dict(name='steering_at_apex',unit='source unit'))=='Steering at Apex [unità non verificata]'
