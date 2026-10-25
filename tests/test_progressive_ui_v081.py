import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from conftest import chart_specs

ROOT = Path(__file__).resolve().parents[1]


def test_replay_default_cadence_pause_reveal_cache_and_operational_return(monkeypatch):
    import motorsport.ml.cadence_v081 as training
    monkeypatch.setattr(training, 'fit_one_second', lambda *a: (_ for _ in ()).throw(AssertionError('UI must never train')))
    app = AppTest.from_file(str(ROOT/'pages/21_Progressive_Prediction.py'), default_timeout=120).run()
    next(r for r in app.radio if r.key == 'progressive_mode').set_value('Replay frequente v0.8.1').run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.key == 'v081_cadence').value == '1 secondo'
    assert not next(t for t in app.toggle if t.key == 'v081_playing').value
    next(s for s in app.select_slider if s.key == 'v081_checkpoint').set_value(30.).run()
    assert not app.exception
    charts = chart_specs(app)
    assert len(charts) == 2
    payload = json.dumps(charts)
    assert all(s not in payload for s in ['target_s', 'pace_band', 'target_source', 'actual_s'])
    assert 'Risultato finale verificato' not in [m.label for m in app.metric]
    calls = app.session_state['v081_engine'].model_calls
    next(c for c in app.checkbox if c.key == 'v081_reveal').check().run()
    assert not app.exception and 'Risultato finale verificato' in [m.label for m in app.metric]
    assert chart_specs(app) == charts
    assert app.session_state['v081_engine'].model_calls == calls
    # Paused ordinary reruns consume neither source time nor additional inference.
    app.run()
    assert chart_specs(app) == charts and app.session_state['v081_engine'].model_calls == calls
    next(s for s in app.selectbox if s.key == 'v081_cadence').set_value('5 secondi').run()
    assert not app.exception
    slider = next(s for s in app.select_slider if s.key == 'v081_checkpoint')
    assert float(slider.options[0]) == 5.
    next(r for r in app.radio if r.key == 'progressive_mode').set_value('Riferimento operativo').run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label == 'Motore di previsione').value == 'SVR'


def test_model_resource_cache_uses_artifact_identity(monkeypatch, tmp_path):
    import motorsport_ui.progressive_v080 as ui
    calls = []
    sentinel = object()
    monkeypatch.setattr(ui, 'load_fold', lambda *a, **kw:(calls.append((a, kw)) or (sentinel, None)))
    ui.cached_fold.clear()
    try:
        first = ui.cached_fold('{}', 0, False, (1, 2), str(tmp_path))
        assert ui.cached_fold('{}', 0, False, (1, 2), str(tmp_path)) is first
        assert len(calls) == 1
        ui.cached_fold('{}', 0, False, (2, 2), str(tmp_path))
        assert len(calls) == 2
    finally:
        ui.cached_fold.clear()
