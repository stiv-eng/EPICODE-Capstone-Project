from pathlib import Path
import json

import pytest
from streamlit.testing.v1 import AppTest

from conftest import chart_specs

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_barcelona_dallara').exists(),reason='Optional local Barcelona data absent')
def test_development_diagnostics_are_optional_and_never_replace_reference():
    from motorsport.ml.barcelona_recovery import file_sha
    historical=ROOT/'docs/ML_RESULTS_V071.json';before=file_sha(historical)
    app=AppTest.from_file(str(ROOT/'pages/20_Machine_Learning.py'),default_timeout=120).run()
    assert not app.exception and len(chart_specs(app))==3
    next(c for c in app.checkbox if c.key=='show_development_v072').check().run(timeout=120)
    assert not app.exception and len(chart_specs(app))==8
    metrics={m.label:m.value for m in app.metric}
    assert metrics['Giri di sviluppo']=='169' and metrics['Blocchi di sviluppo']=='40'
    assert metrics['Test storico valutato dalle varianti']=='0'
    assert next(s for s in app.selectbox if s.label=='Modello da ispezionare').value=='SVR'
    next(s for s in app.selectbox if s.label=='Variante di sviluppo').set_value('F3').run()
    assert not app.exception and len(chart_specs(app))==8
    assert next(s for s in app.selectbox if s.label=='Modello da ispezionare').value=='SVR'
    assert file_sha(historical)==before


def test_frozen_distribution_and_fold_counts_match_unique_laps():
    import pandas as pd
    summary=pd.read_csv(ROOT/'docs/PACE_DISTRIBUTIONS_V072.csv').set_index('partition')
    assert summary.laps.to_dict()=={'test':36,'train':103,'validation':66}
    counts=pd.read_csv(ROOT/'docs/PACE_COUNTS_V072.csv')
    assert counts.groupby('partition').laps.sum().to_dict()==summary.laps.to_dict()
    folds=pd.read_csv(ROOT/'docs/DEVELOPMENT_FOLDS_V072.csv')
    assert len(folds)==folds.lap_uid.nunique()==169 and folds.physical_session_id.nunique()==40
    assert folds.groupby('physical_session_id').fold.nunique().eq(1).all()
    split=pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv')
    assert set(folds.lap_uid).isdisjoint(split.query("partition=='test'").lap_uid)
    result=json.loads((ROOT/'docs/ML_RESULTS_V072.json').read_text(encoding='utf-8'))
    assert result['historical_test_evaluations']==0 and result['selection']['selected_development_variant']=='F0'


def test_reference_artifact_and_evidence_inventory_unchanged():
    from motorsport.ml.diagnosis_v072 import verify_inventory
    inventory=json.loads((ROOT/'docs/BASELINE_PRESERVATION_V072.json').read_text(encoding='utf-8'))['sha256']
    # Model binaries are intentionally local and optional on a fresh checkout.
    installed={k:v for k,v in inventory.items() if k.startswith('docs/') or (ROOT/k).exists()}
    verify_inventory(installed)
