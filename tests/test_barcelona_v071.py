from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from motorsport.ml import barcelona_recovery as recovery
from motorsport.ml import barcelona_experiment_v071 as experiment
from motorsport.ml.dataset import Corpus, ReplayLap
from motorsport.ml.features import FEATURES, snapshots
from motorsport.ml.baselines import CompletedLap
from motorsport.ingestion.acgym_importer import validate_laps

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def corpus():
    laps, targets = [], []
    for group in range(8):
        for number in range(3):
            uid=f'capture{group}:lap:{number}'
            t=np.arange(0,90,.1)
            frame=pd.DataFrame(dict(lap_elapsed_s=t, speed_kmh=110+group*3+number+20*np.sin(t/3),
                throttle_pct=60+group+10*np.sin(t), brake_pct=10+5*np.cos(t),
                rpm=6000+group*100+number*10, gear=np.nan if group==2 else 4., steering=10*np.sin(t)))
            lap=ReplayLap(uid,f'block{group}','unknown',recovery.DOMAIN,
                          (f'2024-01-{group+1:02}',1,number*1000.),frame,False,'deg')
            laps.append(lap)
            targets.append(dict(lap_uid=uid,physical_session_id=lap.physical_session_id,driver_id='unknown',
                target_s=120-group*2+number, min_core_coverage=1., exact_hash=uid, fingerprint=uid,
                timing_quality_category=False,date_reliable=False))
    return Corpus('synthetic recovery',laps,pd.DataFrame(targets),[])


@pytest.fixture(scope='module')
def trained(corpus,tmp_path_factory):
    root=tmp_path_factory.mktemp('v071')
    return experiment.run(corpus,output=root/'docs',model_root=root/'models'),root


def test_metadata_uncertainty_does_not_gate_and_split_stable(corpus):
    assert recovery.data_gate(corpus)['eligible']
    split=recovery.frozen_split(corpus)
    shuffled=deepcopy(corpus);shuffled.laps.reverse()
    pd.testing.assert_frame_equal(split.sort_values('lap_uid').reset_index(drop=True),
        recovery.frozen_split(shuffled).sort_values('lap_uid').reset_index(drop=True))
    assert split.groupby('physical_session_id').partition.nunique().eq(1).all()
    table,_=snapshots(corpus)
    joined=table.merge(split[['lap_uid','partition']],on='lap_uid')
    assert joined.groupby('lap_uid').partition.nunique().eq(1).all()
    assert joined.groupby('lap_uid').size().eq(5).all()


def test_exact_duplicate_hash_uses_full_trajectory_target(corpus):
    frame=corpus.laps[0].frame
    assert recovery.exact_lap_hash(frame,100)==recovery.exact_lap_hash(frame.copy(),100)
    changed=frame.copy();changed.loc[2,'rpm']+=1
    assert recovery.exact_lap_hash(frame,100)!=recovery.exact_lap_hash(changed,100)
    assert recovery.exact_lap_hash(frame,100)!=recovery.exact_lap_hash(frame,101)
    bad=deepcopy(corpus);bad.targets.loc[1,'exact_hash']=bad.targets.loc[0,'exact_hash']
    assert not recovery.data_gate(bad)['eligible']


def test_loader_recovers_metadata_and_excludes_only_exact_copy(tmp_path,monkeypatch,corpus):
    files=[]
    for i,code in enumerate(['A','XX','WL']):
        path=f'20240401_{code}/laps/stint_1.ld'
        for suffix in ('','x'):
            candidate=tmp_path/(path+suffix);candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(b'payload')
            files.append(dict(path=path+suffix,recording_label=f'20240401_{code}',driver_label=code,
                              source_type='human',sha256=f'hash{i}{suffix}',url='https://example.test/source'))
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps(dict(track='ks_barcelona-layout_gp',car='dallara_f317',revision='pinned',files=files)),encoding='utf-8')
    hashes={e['path']:e['sha256'] for e in files}
    monkeypatch.setattr(recovery,'file_sha',lambda p:hashes.get(Path(p).relative_to(tmp_path).as_posix(),'manifest'))
    def fake_load(path,entry,config):
        assert config['optional_feature_channels'] and config['target_rounding_s']==.001
        frame=corpus.laps[0].frame.copy()
        if entry['driver_label']=='XX':frame.loc[2,'rpm']+=1
        frame['source_lap_time']=frame.lap_elapsed_s
        meta=dict(source_header={'date':'different date','time':'00:00'},identity_quarantine=['unresolved identity','date disagreement'],
                  export_hz=10,session_date='unknown',recording_order=1,driver_id='unknown',channel_units={'steering':'deg'},rejected_laps=[])
        laps=pd.DataFrame([dict(lap_id=1,start_sample=0,end_sample=len(frame),start_s=0,duration_s=100.,target_verified=True,target_source='fixture')])
        return SimpleNamespace(data=frame,metadata=meta,laps=SimpleNamespace(laps=laps))
    monkeypatch.setattr(recovery,'load_acgym_recording',fake_load)
    result,audit=recovery.load_corpus(tmp_path,manifest)
    assert len(result.laps)==2 and audit['metadata_uncertain_included']==2
    assert audit['exact_lap_duplicates']==1 and audit['related_capture_links']
    # Nonidentical coarse-signature match stays admitted and linked as one block.
    assert len({l.physical_session_id for l in result.laps})==1


def test_rounding_recovers_half_ms_but_invalid_target_still_rejected():
    hz=100;t=np.arange(0,30,.01);t[-1]=29.9995
    frame=pd.DataFrame(dict(source_lap_count=np.r_[np.zeros(len(t)),1.],
        source_lap_time=np.r_[t,0.],source_last_lap_time=np.r_[np.zeros(len(t)),29.999],
        source_invalid=0.,source_time_left=100-np.arange(len(t)+1)/hz,
        source_progress=np.r_[np.linspace(0,1,len(t)),0.]))
    assert not validate_laps(frame,[0,30],hz)[0].available
    assert validate_laps(frame,[0,30],hz,target_rounding_s=.001)[0].available
    frame.loc[len(t),'source_last_lap_time']=32.
    assert not validate_laps(frame,[0,30],hz,target_rounding_s=.001)[0].available


def test_selection_train_only_preprocessing_and_frozen_test(corpus,trained,monkeypatch):
    bundle,root=trained
    split=bundle.split
    table,_=snapshots(corpus)
    joined=table.merge(split[['lap_uid','partition']],on='lap_uid')
    rows=joined.query("partition=='train'").loc[:,FEATURES]
    expected=rows.fillna(rows.median()).mean().to_numpy()
    np.testing.assert_allclose(bundle.models['Ridge'].named_steps['scaler'].mean_,expected)
    assert set(bundle.history[i].lap_uid for i in range(len(bundle.history)))==set(split.query("partition=='train'").lap_uid)
    scores=bundle.reports['overall'].query("partition=='validation'").to_dict('records')
    assert bundle.selected_model==experiment.rank(scores)
    assert set(bundle.predictions.query("partition=='test'").model)=={bundle.selected_model}
    assert set(bundle.predictions.query("partition=='validation'").model)=={'Ridge','Random Forest','SVR'}
    result=json.loads((root/'docs/ML_RESULTS_V071.json').read_text(encoding='utf-8'))
    assert result['test_evaluations']==1 and result['experiment']=='A'
    def forbidden():raise AssertionError('Frozen rerun must not refit or repredict')
    monkeypatch.setattr(experiment,'make_models',forbidden)
    repeated=experiment.run(corpus,output=root/'docs',model_root=root/'models')
    pd.testing.assert_frame_equal(bundle.predictions,repeated.predictions)
    assert json.loads((root/'docs/ML_RESULTS_V071.json').read_text(encoding='utf-8'))==result


def test_baselines_use_training_only_and_require_supported_previous_order(corpus,trained):
    bundle,_=trained
    heldout=set(bundle.split.query("partition=='test'").lap_uid)
    source=next(lap for lap in corpus.laps if lap.lap_uid in heldout)
    refs=recovery.baseline_references(source,bundle.history,bundle.date_reliability)
    assert refs['previous_lap'] is None
    assert refs['historical_median']==np.median([h.target_s for h in bundle.history])
    same=CompletedLap(source.lap_uid.split(':lap:')[0]+':lap:prior',source.domain,
                      (*source.start_order[:2],source.start_order[2]-1),99.)
    assert recovery.baseline_references(source,[same],{})['previous_lap']==99.
    foreign=replace(same,domain=('other','car'))
    assert recovery.baseline_references(source,[foreign],{})['historical_median'] is None


@pytest.mark.parametrize('checkpoint',[10,20,30,45,60])
def test_progressive_target_hidden_and_future_invariance(corpus,trained,checkpoint):
    bundle,_=trained;source=corpus.laps[-1];changed=deepcopy(source)
    changed.frame.loc[changed.frame.lap_elapsed_s>checkpoint,'speed_kmh']=-999
    kwargs=dict(model=bundle.models[bundle.selected_model],feature_names=bundle.feature_names,
                history=bundle.history,model_domain=bundle.domain)
    assert recovery.predict(source,checkpoint,**kwargs)==recovery.predict(changed,checkpoint,**kwargs)
    assert not hasattr(source,'target_s')
    with pytest.raises(ValueError,match='domain'):recovery.predict(replace(source,domain=('foreign','car')),checkpoint,**kwargs)


def test_artifact_domain_and_protocol_compatibility(corpus,trained):
    bundle,_=trained
    recovery.verify_compatibility(bundle,corpus)
    bad=deepcopy(bundle);bad.compatibility['units']={}
    with pytest.raises(ValueError,match='mismatch'):recovery.verify_compatibility(bad,corpus)
    bad=deepcopy(bundle);bad.domain=('monza','car')
    with pytest.raises(ValueError,match='mismatch'):recovery.verify_compatibility(bad,corpus)


def test_filter_rule_requires_meaningful_consistent_slow_safe_gain():
    def scores(mae,slow=20):return [dict(model=m,mae_s=mae,recording_macro_mae_s=mae,slow_lap_mae_s=slow) for m in ['Ridge','RF','SVR']]
    assert experiment.choose_experiment(scores(10),scores(9.8))=='A'
    assert experiment.choose_experiment(scores(10),scores(9,21))=='A'
    assert experiment.choose_experiment(scores(10),scores(9))=='B'


def test_missing_artifact_rebuild_fits_only_train_without_heldout_prediction(corpus,trained,tmp_path,monkeypatch):
    import shutil
    from sklearn.pipeline import Pipeline
    bundle,root=trained
    shutil.copytree(root/'docs',tmp_path/'docs')
    def forbidden(*args,**kwargs):raise AssertionError('Reinstall must not predict validation/test')
    monkeypatch.setattr(Pipeline,'predict',forbidden)
    restored=experiment.run(corpus,output=tmp_path/'docs',model_root=tmp_path/'models')
    assert restored.selected_model==bundle.selected_model
    assert (tmp_path/'docs/ML_RESULTS_V071.json').read_bytes()==(root/'docs/ML_RESULTS_V071.json').read_bytes()


def test_frozen_evidence_tampering_and_interrupted_test_refused(corpus,trained,tmp_path):
    import shutil
    _,root=trained
    shutil.copytree(root/'docs',tmp_path/'docs')
    with (tmp_path/'docs/BARCELONA_PREDICTIONS_V071.csv').open('a',encoding='utf-8') as stream:stream.write('changed')
    with pytest.raises(ValueError,match='Frozen evidence changed'):
        experiment.run(corpus,output=tmp_path/'docs',model_root=root/'models')
    (tmp_path/'docs/ML_RESULTS_V071.json').unlink()
    with pytest.raises(ValueError,match='already opened'):
        experiment.run(corpus,output=tmp_path/'docs',model_root=root/'models')


def test_actual_recovery_audit_and_old_release_preserved():
    audit=json.loads((ROOT/'docs/BARCELONA_AUDIT_V071.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'docs/BARCELONA_AUDIT_V07.json').read_text(encoding='utf-8'))
    assert audit['eligible_laps']==205 and audit['recovered_metadata_laps']==116
    assert audit['additional_recovered_laps']==1 and audit['excluded_validated_laps']==0
    assert old['eligible_laps']==88 and old['validated_complete_laps']==204
    assert audit['exact_raw_duplicates']==audit['exact_lap_duplicates']==0
