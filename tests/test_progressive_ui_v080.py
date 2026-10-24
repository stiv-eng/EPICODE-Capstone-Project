import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import chart_specs

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT/'artifacts/barcelona_v080/models/dense-v080-0.keras').exists(), reason='Optional executed local artifacts absent')
def test_experimental_replay_is_opt_in_target_hidden_and_all_models_available(monkeypatch):
    import motorsport.ml.dense_experiment_v080 as experiment
    monkeypatch.setattr(experiment, 'fit_gru', lambda *a, **k:pytest.fail('UI must never train'))
    app = AppTest.from_file(str(ROOT/'pages/21_Progressive_Prediction.py'), default_timeout=120).run()
    assert not app.exception
    assert next(r for r in app.radio if r.key == 'progressive_mode').value == 'Riferimento operativo'
    assert next(s for s in app.selectbox if s.label == 'Motore di previsione').value == 'SVR'
    next(r for r in app.radio if r.key == 'progressive_mode').set_value('Confronto sperimentale v0.8').run()
    assert not app.exception
    assert set(experiment.CANDIDATES) <= set(next(m for m in app.multiselect if m.key == 'v080_models').options)
    next(m for m in app.multiselect if m.key == 'v080_models').set_value(['GRU', 'RIDGE-ORDERED', 'SVR-REMAINING']).run(timeout=120)
    next(s for s in app.select_slider if s.key == 'v080_checkpoint').set_value(65.).run(timeout=120)
    assert not app.exception and len(chart_specs(app)) == 2
    assert next(m for m in app.metric if m.label == 'Tempo osservato sperimentale').value.startswith('64.') or next(m for m in app.metric if m.label == 'Tempo osservato sperimentale').value.startswith('65.')
    charts = chart_specs(app)
    payload = json.dumps(charts)
    assert 'target_s' not in payload and 'target_source' not in payload and 'pace_band' not in payload
    assert 'Risultato finale verificato' not in [m.label for m in app.metric]
    next(c for c in app.checkbox if c.key == 'v080_reveal').check().run(timeout=120)
    assert not app.exception and 'Risultato finale verificato' in [m.label for m in app.metric]
    assert chart_specs(app) == charts
    next(s for s in app.selectbox if s.key == 'v080_cadence').set_value('Compatibilità 10/20/30/45/60 s').run(timeout=120)
    assert not app.exception and next(s for s in app.select_slider if s.key == 'v080_checkpoint').options == ['10.0', '20.0', '30.0', '45.0', '60.0']


def test_new_modules_keep_keras_lazy_and_offline():
    import subprocess
    import sys
    code = '''
import sys,socket,importlib.abc
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in {'keras','torch','fastf1'}:raise ImportError('optional dependency blocked')
sys.meta_path.insert(0,Block())
socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network forbidden'))
from motorsport.ml import progression_v080,sequences_v080,dense_experiment_v080,evaluation_v080
from motorsport_ui import progressive_v080
assert not any(n in sys.modules for n in ['keras','torch','fastf1'])
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
