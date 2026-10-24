from conftest import chart_specs
from pathlib import Path
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import motorsport_ui.ml as ui
import motorsport_ui.telemetry as telemetry

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('page',['20_Machine_Learning.py','21_Progressive_Prediction.py'])
def test_ml_pages_handle_no_validated_targets(tmp_path,monkeypatch,page):
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame({'elapsed_s':[0,.1,.2],'speed_kmh':[100]*3}).to_csv(tmp_path/'data/raw/minimal.csv',index=False)
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    monkeypatch.setattr(telemetry,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages'/page),default_timeout=45)
    app.session_state['ml_archive_mode']=True
    app.run()
    assert not app.exception and app.metric[0].value=='0'
    assert not app.button and any('target' in info.value for info in app.info)


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_monza_dallara').exists(),reason='Optional bounded ACGym corpus absent')
def test_explicit_training_persistence_and_replay_hides_final_target():
    app=AppTest.from_file(str(ROOT/'pages/20_Machine_Learning.py'),default_timeout=60)
    app.session_state['ml_archive_mode']=True
    app.run()
    assert not app.exception and app.metric[0].value=='55'
    assert len(chart_specs(app))==0
    next(b for b in app.button if b.label=='Addestra e valuta i tre modelli').click().run(timeout=60)
    assert not app.exception and len(chart_specs(app))==3
    saved=app.session_state['ml_bundles']
    app.run()
    assert app.session_state['ml_bundles'].keys()==saved.keys()
    replay=AppTest.from_file(str(ROOT/'pages/21_Progressive_Prediction.py'),default_timeout=60)
    replay.session_state['ml_archive_mode']=True
    replay.session_state['ml_bundles']=saved
    replay.run()
    assert not replay.exception and len(chart_specs(replay))==2
    assert 'Risultato finale verificato' not in [m.label for m in replay.metric]
    assert 'Errore previsto − verificato' not in [m.label for m in replay.metric]
    next(s for s in replay.select_slider if s.label=='Checkpoint trascorso (s)').set_value(30.).run()
    assert not replay.exception and 29.9<float(next(m.value for m in replay.metric if m.label=='Tempo osservato').split()[0])<=30.
    hidden_specs=chart_specs(replay)
    payload=json.dumps(hidden_specs)
    assert 'target_s' not in payload and 'actual_s' not in payload and 'target_source' not in payload
    next(c for c in replay.checkbox if c.label.startswith('Mostra valutazione')).check().run()
    assert not replay.exception and 'Risultato finale verificato' in [m.label for m in replay.metric]
    assert chart_specs(replay)==hidden_specs


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c').exists(),reason='Optional GT7 bundle absent')
def test_gt7_training_is_explicit_experimental_opt_in():
    app=AppTest.from_file(str(ROOT/'pages/20_Machine_Learning.py'),default_timeout=60)
    app.session_state['ml_archive_mode']=True
    app.run()
    bundle_key=str((ROOT/'data/raw/gt7_trial_mountain_962c').resolve())
    next(s for s in app.selectbox if s.label=='Dataset ML').set_value(bundle_key).run()
    assert not app.exception and app.metric[0].value=='8'
    train_button=next(b for b in app.button if b.label=='Addestra e valuta i tre modelli')
    assert train_button.disabled and any('Experimental single-session' in w.value for w in app.warning)
    next(c for c in app.checkbox if c.label=='Abilita caso di studio sperimentale').check().run()
    next(b for b in app.button if b.label=='Addestra e valuta i tre modelli').click().run(timeout=60)
    assert not app.exception and len(chart_specs(app))==2


def test_offline_ml_module_imports_do_not_load_legacy_or_network(tmp_path):
    import subprocess
    import sys
    code='''
import importlib.abc,sys,socket
class BlockLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'keras','torch','fastf1'}:
            raise ImportError('Legacy dependencies blocked for offline ML')
sys.meta_path.insert(0,BlockLegacy())
def unavailable(*args,**kwargs):raise AssertionError('Unexpected network connection')
socket.create_connection=unavailable
from motorsport.ml import dataset,features,baselines,training,evaluation,inference,artifacts
from motorsport_ui import ml
assert not any(name in sys.modules for name in ['keras','torch','fastf1'])
print('offline imports passed')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
