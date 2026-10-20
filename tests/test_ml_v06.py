from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import pandas as pd
import pytest

from motorsport.ingestion.motec import read_ld
from motorsport.ingestion.acgym_importer import read_beacons,validate_laps,load_acgym_sessions
from motorsport.ml.dataset import Corpus,ReplayLap,eligibility,from_sessions,independent_subset
from motorsport.ml.features import FEATURES,prefix_features,snapshots,retrospective_features
from motorsport.ml.baselines import CompletedLap,baseline_predictions,reference_history
from motorsport.ml.training import train,chronological_split,EXPERIMENTAL
from motorsport.ml.inference import predict,retrospective_error
from motorsport.ml.artifacts import LocalArtifactStore

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def corpus():
    laps,targets=[],[]
    for session in range(5):
        for lap in range(6):
            uid=f's{session}:l{lap}';physical=f's{session}';duration=80+session*2+lap
            t=np.arange(0,duration,.1)
            frame=pd.DataFrame({'lap_elapsed_s':t,'speed_kmh':150+session+lap+20*np.sin(t/3),
                'throttle_pct':np.where(t%10>2,100.,0.),'brake_pct':np.where(t%10<=2,50.,0.),
                'rpm':6000.+session*100+lap*10,'gear':4.,'steering':10*np.sin(t)})
            order=(f'2024-01-{session+1:02}',1,lap*1000.)
            source=ReplayLap(uid,physical,f'd{session}',('track','car'),order,frame,True,'deg')
            laps.append(source)
            targets.append({'lap_uid':uid,'physical_session_id':physical,'target_s':float(duration),
                'target_source':'synthetic witnessed fixture','fingerprint':uid,'domain':source.domain,
                'min_core_coverage':1.,'start_order':order,'independence_verified':True})
    return Corpus('synthetic',laps,pd.DataFrame(targets),[])


@pytest.fixture(scope='module')
def bundle(corpus):
    return train(corpus)


def test_safe_ld_numeric_scaling_units_and_corruption(tmp_path):
    blob=bytearray(1024);struct.pack_into('<I',blob,0,0x40);struct.pack_into('<I',blob,8,512)
    struct.pack_into('<4I4H4h',blob,512,0,0,800,3,1,3,2,100,10,2,5,1)
    blob[544:549]=b'Speed';blob[584:588]=b'km/h';struct.pack_into('<3h',blob,800,0,50,100)
    path=tmp_path/'test.ld';path.write_bytes(blob)
    header,channels=read_ld(path)
    np.testing.assert_allclose(channels['Speed'].values,[20,22,24]);assert channels['Speed'].unit=='km/h'
    struct.pack_into('<I',blob,516,512);path.write_bytes(blob)
    with pytest.raises(ValueError,match='cyclic'):read_ld(path)
    struct.pack_into('<I',blob,516,0);struct.pack_into('<I',blob,520,1022);path.write_bytes(blob)
    with pytest.raises(ValueError,match='bounds'):read_ld(path)
    path.write_bytes(b'not a model or executable format')
    with pytest.raises(ValueError,match='header'):read_ld(path)


def test_ldx_rejects_entities_missing_and_nonmonotonic_beacons(tmp_path):
    path=tmp_path/'source.ldx';path.write_text('<!DOCTYPE test><LDXFile/>')
    with pytest.raises(ValueError,match='unsafe'):read_beacons(path)
    path.write_text('<LDXFile/>')
    with pytest.raises(ValueError,match='beacons'):read_beacons(path)


def test_source_laps_require_witnessed_target_beacons_and_no_gaps():
    hz=100;t=np.arange(0,30,.01)
    frame=pd.DataFrame({'source_lap_count':np.r_[np.zeros(len(t)),np.ones(10)],
        'source_lap_time':np.r_[t,np.arange(10)/hz],
        'source_last_lap_time':np.r_[np.zeros(len(t)),np.full(10,30.)],
        'source_invalid':0.,'source_time_left':100-np.arange(len(t)+10)/hz,
        'source_progress':np.r_[np.linspace(0,1,len(t)),np.arange(10)/1000]})
    result,_,rejected=validate_laps(frame,[0,30],hz)
    assert result.available and len(result.laps)==1 and len(rejected)==1
    changed=frame.copy();changed.loc[len(t):,'source_last_lap_time']=32
    assert not validate_laps(changed,[0,30],hz)[0].available
    assert not validate_laps(frame,[0,31],hz)[0].available
    changed=frame.copy();changed.loc[100:200,'source_lap_time']+=1
    assert not validate_laps(changed,[0,30],hz)[0].available
    changed=frame.copy();changed.loc[200,'source_invalid']=1
    assert not validate_laps(changed,[0,30],hz)[0].available


@pytest.mark.parametrize('checkpoint',[10,20,30,45,60])
def test_future_telemetry_and_future_clock_reset_do_not_change_prefix(corpus,bundle,checkpoint):
    lap=corpus.laps[-1];altered=deepcopy(lap)
    future=altered.frame.lap_elapsed_s>checkpoint
    altered.frame.loc[future,['speed_kmh','throttle_pct','brake_pct','rpm','steering']]=-999999
    # A future reset after the first unavailable sample cannot enter a prefix.
    indices=np.flatnonzero(future)
    altered.frame.loc[indices[1:],'lap_elapsed_s']=0
    before=predict(lap,checkpoint,bundle.models['Ridge'],bundle.feature_names,bundle.history,model_domain=bundle.domain)
    after=predict(altered,checkpoint,bundle.models['Ridge'],bundle.feature_names,bundle.history,model_domain=bundle.domain)
    assert before==after


def test_target_is_not_part_of_predictive_source_or_features(corpus):
    changed=deepcopy(corpus);changed.targets['target_s']+=999
    a,_=snapshots(corpus);b,_=snapshots(changed)
    pd.testing.assert_frame_equal(a.loc[:,FEATURES],b.loc[:,FEATURES])
    assert not hasattr(corpus.laps[0],'target_s')
    assert 'full_lap_mean_speed_kmh' in retrospective_features(corpus)
    with pytest.raises(ValueError,match='allowlist'):train(corpus,['target_s'])
    with pytest.raises(ValueError,match='allowlist'):train(corpus,['full_lap_mean_speed_kmh'])


def test_corpus_identity_invalidates_models_after_mapping_or_unit_change(corpus):
    changed=deepcopy(corpus)
    changed.laps[0].frame['steering']*=2
    assert changed.identity!=corpus.identity
    changed=deepcopy(corpus);changed.laps[0].steering_unit='unknown'
    assert changed.identity!=corpus.identity


def test_checkpoints_missing_channels_gaps_and_out_of_range(corpus):
    lap=deepcopy(corpus.laps[0])
    with pytest.raises(ValueError,match='boundary'):prefix_features(lap,100)
    with pytest.raises(ValueError,match='positive'):prefix_features(lap,-1)
    lap.frame['brake_pct']=np.nan
    with pytest.raises(ValueError,match='99%'):prefix_features(lap,10)


def test_optional_channels_and_sparse_invalid_current_value_are_missing_not_fabricated(corpus):
    lap=deepcopy(corpus.laps[0])
    lap.frame=lap.frame.drop(columns=['gear','steering'])
    last=lap.frame.index[lap.frame.lap_elapsed_s<=10][-1]
    lap.frame.loc[last,'speed_kmh']=1000
    features,quality=prefix_features(lap,10)
    assert np.isnan(features['speed_current_kmh']) and np.isnan(features['gear_current'])
    assert np.isnan(features['steering_activity_deg_s']) and quality['min_core_coverage']>=.99
    lap=deepcopy(corpus.laps[0]);lap.frame=lap.frame.loc[~lap.frame.lap_elapsed_s.between(4,6)]
    with pytest.raises(ValueError,match='gap'):prefix_features(lap,10)
    lap=deepcopy(corpus.laps[0]);lap.frame['speed_kmh']=1000
    with pytest.raises(ValueError,match='99%'):prefix_features(lap,10)


def test_baselines_exclude_current_future_and_other_domain(corpus):
    source=corpus.laps[2]
    history=reference_history(corpus,{x.lap_uid for x in corpus.laps})
    result=baseline_predictions(source,history)
    assert result['history_laps']==2 and result['previous_lap']==81 and result['historical_median']==80.5
    assert baseline_predictions(corpus.laps[0],history)['previous_lap'] is None
    hostile=[CompletedLap('foreign',('other','car'),('2000',1,0),1),
             CompletedLap(source.lap_uid,source.domain,('2000',1,0),1)]
    assert baseline_predictions(source,hostile)['history_laps']==0


def test_split_integrity_no_heldout_baseline_labels_and_train_only_preprocessing(corpus,bundle):
    assert eligibility(corpus)['eligible']
    assert bundle.split.groupby('physical_session_id').partition.nunique().eq(1).all()
    table,_=snapshots(corpus)
    joined=table.merge(bundle.split[['lap_uid','partition']],on='lap_uid')
    train_rows=joined.loc[joined.partition=='train',list(bundle.feature_names)]
    expected=train_rows.fillna(train_rows.median()).mean().to_numpy()
    np.testing.assert_allclose(bundle.models['Ridge'].named_steps['scaler'].mean_,expected)
    train_ids=set(bundle.split.query("partition=='train'").lap_uid)
    assert {x.lap_uid for x in bundle.history}<=train_ids
    assert set(bundle.predictions.partition)=={'validation','test'}
    assert set(bundle.predictions.lap_uid).isdisjoint(train_ids)
    for model in ('Ridge','SVR','Random Forest'):
        assert model in bundle.models
    assert set(bundle.reports)=={'overall','by_checkpoint','by_session','by_lap','baselines','individual'}


def test_changing_heldout_labels_does_not_change_fitted_models_or_baselines(corpus,bundle):
    changed=deepcopy(corpus)
    heldout=set(bundle.split.query("partition!='train'").lap_uid)
    changed.targets.loc[changed.targets.lap_uid.isin(heldout),'target_s']+=500
    other=train(changed)
    for model in bundle.models:
        a=bundle.predictions.query('model==@model').reset_index(drop=True)
        b=other.predictions.query('model==@model').reset_index(drop=True)
        np.testing.assert_allclose(a.prediction_s,b.prediction_s)
        np.testing.assert_allclose(a.historical_median,b.historical_median)


def test_duplicate_ids_signatures_and_small_dataset_gates(corpus):
    duplicate=deepcopy(corpus);duplicate.targets.loc[1,'fingerprint']=duplicate.targets.loc[0,'fingerprint']
    with pytest.raises(ValueError,match='Duplicate'):chronological_split(duplicate)
    small=Corpus('small',corpus.laps[:6],corpus.targets.iloc[:6].copy(),[])
    assert not eligibility(small)['eligible']
    with pytest.raises(ValueError,match='disabled'):train(small)
    trained=train(small,experimental=True)
    assert trained.mode==EXPERIMENTAL
    tiny=Corpus('tiny',corpus.laps[:2],corpus.targets.iloc[:2].copy(),[])
    with pytest.raises(ValueError,match='six'):train(tiny,experimental=True)
    with pytest.raises(ValueError,match='exactly one'):train(corpus,experimental=True)


def test_inference_domain_guard_baseline_and_explicit_evaluation(corpus,bundle):
    lap=corpus.laps[-1]
    prediction=predict(lap,10,history=bundle.history)
    assert prediction.predicted_final_s==prediction.baseline_s
    assert retrospective_error(prediction,100)==prediction.predicted_final_s-100
    with pytest.raises(ValueError,match='domain'):
        predict(replace(lap,domain=('other','track')),10,bundle.models['Ridge'],bundle.feature_names,model_domain=bundle.domain)


def test_local_artifact_roundtrip_rejects_unknown_or_tampered_before_deserialization(tmp_path,bundle,monkeypatch):
    store=LocalArtifactStore(tmp_path/'models');path=store.save(bundle,'fixture')
    restored=store.load('fixture');assert restored.corpus_id==bundle.corpus_id
    pd.testing.assert_frame_equal(restored.predictions,bundle.predictions)
    path.write_bytes(b'hostile pickle placeholder')
    import motorsport.ml.artifacts as artifacts
    monkeypatch.setattr(artifacts.joblib,'load',lambda *_:pytest.fail('Untrusted artifact deserialized'))
    with pytest.raises(ValueError,match='modified'):store.load('fixture')
    with pytest.raises(ValueError,match='Unknown'):store.load('unknown')
    with pytest.raises(ValueError,match='name'):store.load('../outside')


@pytest.mark.skipif(not (ROOT/'data/raw/acgym_monza_dallara').exists(),reason='Optional bounded ACGym corpus absent')
def test_real_acgym_manifest_targets_duplicate_captures_and_gate():
    manifest=json.loads((ROOT/'docs/ACGYM_MANIFEST_V06.json').read_text())
    assert sum(e['bytes'] for e in manifest['files'])==241902674<300000000
    for entry in manifest['files']:
        path=ROOT/'data/raw/acgym_monza_dallara'/entry['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    sessions,rejected=load_acgym_sessions()
    assert len(sessions)==18 and len(rejected)==1 and 'date' in rejected[0]['reason']
    corpus=from_sessions(sessions,'ACGym')
    assert len(corpus.laps)==106 and not eligibility(corpus)['eligible']
    duplicate=from_sessions(sessions+sessions[:1],'ACGym')
    assert len(duplicate.laps)==106 and any(x.get('reason')=='duplicate raw capture' for x in duplicate.exclusions)
    independent=independent_subset(corpus);gate=eligibility(independent)
    assert gate['eligible'] and gate['validated_laps']==55 and gate['physical_sessions']==11 and gate['drivers']==8
    table,rejected=snapshots(independent)
    assert len(table)==275 and rejected.empty and table.target_source.str.contains('Last Lap Time').all()


@pytest.mark.skipif(not (ROOT/'data/raw/gt7_trial_mountain_962c').exists(),reason='Optional GT7 bundle absent')
def test_gt7_experimental_workflow():
    from motorsport.ingestion.gt7_importer import load_gt7_bundle
    session=load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')
    corpus=from_sessions([session],'GT7')
    assert len(corpus.exclusions)==len(session.metadata['lap_rejections'])>0
    assert corpus.targets.source_sha256.isna().all()  # bundle revision is not a file SHA
    assert corpus.targets.source_revision.eq(session.metadata['revision']).all()
    assert len(corpus.laps)==8 and not eligibility(corpus)['eligible']
    table,rejected=snapshots(corpus)
    assert len(table)==40 and rejected.empty
    trained=train(corpus,experimental=True)
    assert trained.mode==EXPERIMENTAL and trained.importance.empty
