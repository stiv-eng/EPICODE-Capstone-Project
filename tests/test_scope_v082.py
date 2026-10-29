"""Scope and data preservation regressions after the deliberate feature removal."""
import ast
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from motorsport.ingestion.barcelona import manifest_entry_path, load_barcelona_recording
from motorsport.ingestion.acgym_importer import validate_laps

ROOT = Path(__file__).resolve().parents[1]


def test_active_import_graph_and_dependencies_do_not_reference_prediction():
    forbidden = ('motorsport.ml', 'motorsport_prediction', 'motorsport_ui.ml', 'motorsport_ui.svr',
                 'motorsport_ui.progressive', 'sklearn', 'keras', 'torch', 'joblib')
    for folder in ('motorsport', 'motorsport_ui', 'pages', 'scripts'):
        for path in (ROOT/folder).rglob('*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                imports = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                assert not any(name.startswith(forbidden) for name in imports), path
    for filename in ('requirements.txt',):
        dependencies = (ROOT/filename).read_text(encoding='utf-8').lower()
        assert all(name not in dependencies for name in ('keras', 'torch', 'scikit-learn', 'joblib'))


def test_home_navigation_is_analysis_only(monkeypatch):
    app = AppTest.from_file(str(ROOT/'streamlit_app.py'), default_timeout=45).run()
    assert not app.exception
    text = ' '.join(x.value for x in app.markdown)+str(app.caption)
    assert not any(name in text for name in ('Progressive Prediction', 'Machine Learning', 'SVR', 'GRU'))
    assert not app.checkbox
    source = (ROOT/'streamlit_app.py').read_text(encoding='utf-8')
    assert 'FastF1' not in source and 'Formula 1' not in source
    assert not (ROOT/'motorsport_ui/common.py').exists()
    assert not (ROOT/'requirements-extension.txt').exists()
    tree = ast.parse(source)
    pages = [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call) and
             getattr(n.func, 'attr', '') in ('Page','page_link') and n.args and isinstance(n.args[0], ast.Constant)]
    assert all((ROOT/page).exists() for page in pages)
    assert not any(word in source for word in ('SVR', 'GRU', 'Machine Learning', 'Progressive Prediction'))
    from motorsport.pipeline import load_session
    import motorsport_ui.telemetry as ui
    session = load_session(b'elapsed_s,speed_kmh\n0,100\n1,110\n', 'metadata.csv')
    session.metadata['identity_quarantine'] = ['uncertain participant']
    monkeypatch.setattr(ui, 'source_catalog', lambda include_acgym=False:{'upload:metadata':'Metadata fixture'})
    monkeypatch.setattr(ui, 'get_source', lambda key:session)
    overview = AppTest.from_file(str(ROOT/'pages/10_Session_Overview.py'), default_timeout=45).run()
    assert not overview.exception
    messages = ' '.join(info.value for info in overview.info)
    assert 'uncertain participant' in messages and 'corpus ML' not in messages


def test_all_active_local_pages_start_with_model_packages_and_artifacts_inaccessible():
    code = '''
import sys
from pathlib import Path
from scripts.analysis_guard import install,FORBIDDEN_ROOTS
install()
from streamlit.testing.v1 import AppTest
root=Path.cwd()
for path in ['streamlit_app.py','pages/00_Data_Explorer.py','pages/10_Session_Overview.py','pages/14_Session_Comparison.py','pages/16_Telemetry_Lap_Analysis.py']:
    app=AppTest.from_file(str(root/path),default_timeout=90).run()
    assert not app.exception,app.exception
assert not (FORBIDDEN_ROOTS & set(sys.modules))
assert 'motorsport.ml' not in sys.modules
print('All active local pages start without prediction dependencies or artifacts')
'''
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout+result.stderr


def test_barcelona_manifest_rejects_paths_outside_source_directory(tmp_path):
    with pytest.raises(ValueError, match='Unsafe'):
        manifest_entry_path(tmp_path, {'path':'../outside.ld'})
    assert manifest_entry_path(tmp_path, {'path':'capture/lap.ld'}) == tmp_path/'capture/lap.ld'


def test_barcelona_import_integrity_and_inclusive_config(tmp_path, monkeypatch):
    import motorsport.ingestion.barcelona as adapter
    ld, ldx = tmp_path/'capture.ld', tmp_path/'capture.ldx'
    ld.write_bytes(b'recorded payload')
    ldx.write_bytes(b'independent timing')
    files = [dict(path=p.name,sha256=adapter.file_sha(p),source_type='human',driver_label=None) for p in (ld,ldx)]
    manifest = tmp_path/'manifest.json'
    manifest.write_text(json.dumps(dict(track='ks_barcelona-layout_gp',car='dallara_f317',files=files)))
    calls = []
    def load(path, entry, config, analysis_only):
        calls.append(path)
        assert analysis_only and config['optional_feature_channels'] and config['allow_unknown_date']
        assert config['target_rounding_s'] == .001 and entry['driver_label']=='unknown'
        return 'verified data session'
    monkeypatch.setattr(adapter, 'load_acgym_recording', load)
    assert load_barcelona_recording('capture.ld', tmp_path, manifest) == 'verified data session'
    ldx.write_bytes(b'changed timing')
    with pytest.raises(ValueError, match='integrity'):
        load_barcelona_recording('capture.ld', tmp_path, manifest)
    assert len(calls) == 1


def test_rounding_recovers_half_ms_but_invalid_timing_is_still_rejected():
    # Retained data-validation regression from the retired mixed v071 ML suite.
    hz=100;t=np.arange(0,30,.01);t[-1]=29.9995
    frame=pd.DataFrame(dict(source_lap_count=np.r_[np.zeros(len(t)),1.],
        source_lap_time=np.r_[t,0.],source_last_lap_time=np.r_[np.zeros(len(t)),29.999],
        source_invalid=0.,source_time_left=100-np.arange(len(t)+1)/hz,
        source_progress=np.r_[np.linspace(0,1,len(t)),0.]))
    assert not validate_laps(frame,[0,30],hz)[0].available
    assert validate_laps(frame,[0,30],hz,target_rounding_s=.001)[0].available
    frame.loc[len(t),'source_last_lap_time']=32.
    assert not validate_laps(frame,[0,30],hz,target_rounding_s=.001)[0].available


def test_analysis_capability_registry_contains_no_training_gates():
    from motorsport.pipeline import load_session
    from motorsport.analytics.readiness import assess_capabilities
    session = load_session(b'elapsed_s,speed_kmh\n0,100\n1,110\n', 'fixture.csv')
    assert set(assess_capabilities(session)) == {'session_analysis','time_window_comparison','track_position_analysis',
        'validated_lap_analysis','lap_progress_comparison','cumulative_lap_delta','verified_lap_timing'}


@pytest.mark.skipif(not all((ROOT/name).exists() for name in (
    'data/raw/acgym_barcelona_dallara','data/raw/acgym_monza_dallara',
    'data/raw/gt7_trial_mountain_962c','data/raw/telemetry.parquet')),
    reason='Full optional regression corpus not installed')
def test_actual_analysis_regression_and_all_205_barcelona_laps():
    from scripts.verify_data_analysis_v082 import verify
    result = verify(check_local_files=False)
    assert result['analysis_sources']==73 and result['barcelona_validated_laps']==205
    assert result['signal_hashes_unchanged']==result['overview_summaries_unchanged']==73
    assert len(result['barcelona_rounding_recovery'])==1
