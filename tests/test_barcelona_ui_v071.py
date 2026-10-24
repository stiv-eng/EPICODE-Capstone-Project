from pathlib import Path
import json

import pytest
from streamlit.testing.v1 import AppTest

from conftest import chart_specs
import motorsport_ui.ml as ui

ROOT=Path(__file__).resolve().parents[1]


def test_missing_barcelona_is_explicit_offline_and_never_downloads(tmp_path,monkeypatch):
    monkeypatch.setattr(ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(ROOT/'pages/20_Machine_Learning.py'),default_timeout=60).run()
    assert not app.exception and not app.button
    assert any('non installato' in m.value for m in app.info)
    assert 'run_barcelona_v071' in app.code[0].value


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_barcelona_dallara').exists(),reason='Optional local Barcelona payload absent')
def test_primary_barcelona_frozen_training_and_progressive_hidden_target():
    from motorsport.ml.barcelona_recovery import file_sha
    result=ROOT/'docs/ML_RESULTS_V071.json'
    before=file_sha(result)
    app=AppTest.from_file(str(ROOT/'pages/20_Machine_Learning.py'),default_timeout=120).run()
    assert not app.exception and app.metric[0].value=='205'
    assert app.metric[1].label=='Blocchi di recording' and app.metric[1].value=='51'
    assert len(chart_specs(app)) in (0,3)  # Fresh installs may not have a signed local bundle yet.
    next(b for b in app.button if b.label=='Addestra e valuta i tre modelli').click().run(timeout=120)
    assert not app.exception and file_sha(result)==before
    assert len(chart_specs(app))==3
    assert next(s for s in app.selectbox if s.label=='Modello da ispezionare').options==['SVR']
    next(r for r in app.radio if r.label=='Partizione di valutazione').set_value('validation').run()
    assert not app.exception
    assert set(next(s for s in app.selectbox if s.label=='Modello da ispezionare').options)=={'Ridge','Random Forest','SVR'}
    replay=AppTest.from_file(str(ROOT/'pages/21_Progressive_Prediction.py'),default_timeout=120).run()
    assert not replay.exception and replay.metric[0].value=='205'
    assert next(s for s in replay.selectbox if s.label=='Motore di previsione').value=='SVR'
    assert 'Risultato finale verificato' not in [m.label for m in replay.metric]
    next(s for s in replay.select_slider if s.label=='Checkpoint trascorso (s)').set_value(60.).run()
    assert not replay.exception
    charts=chart_specs(replay)
    payload=json.dumps(charts)
    assert 'target_s' not in payload and 'target_source' not in payload
    next(c for c in replay.checkbox if c.label.startswith('Mostra valutazione retrospettiva')).check().run()
    assert not replay.exception and 'Risultato finale verificato' in [m.label for m in replay.metric]
    assert chart_specs(replay)==charts and file_sha(result)==before
