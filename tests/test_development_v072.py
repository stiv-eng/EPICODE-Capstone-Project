from copy import deepcopy
from dataclasses import replace
import json

import numpy as np
import pandas as pd
import pytest

from motorsport.ml import development_v072 as experiment
from motorsport.ml.dataset import Corpus,ReplayLap
from motorsport.ml.temporal_features_v072 import FEATURE_SETS,feature_row,snapshot_table
from motorsport.ml.diagnosis_v072 import population,calibration,pace_band
from motorsport.ml.barcelona_recovery import DOMAIN


@pytest.fixture(scope='module')
def data():
    laps=[];labels=[];membership=[]
    for group in range(7):
        for number in range(3):
            uid=f'capture{group}:lap:{number}'
            t=np.arange(0,85,.1)
            frame=pd.DataFrame(dict(lap_elapsed_s=t,speed_kmh=110+group*4+number+40*np.sin(t),
                throttle_pct=50+group+20*np.cos(t),brake_pct=np.where(t%10<2,40.,0.),rpm=6000+group*100,
                gear=np.nan if group==1 else 4.,steering=10*np.sin(t)))
            lap=ReplayLap(uid,f'block{group}','unknown',DOMAIN,('unknown',1,number*1000.),frame,False,'deg')
            laps.append(lap)
            labels.append(dict(lap_uid=uid,physical_session_id=lap.physical_session_id,target_s=145-group*4+number,
                driver_id='unknown',date_reliable=False,metadata_uncertainty='unknown identity',source='fixture'))
            membership.append(dict(lap_uid=uid,physical_session_id=lap.physical_session_id,
                partition='train' if group<4 else 'validation' if group<6 else 'test'))
    return Corpus('synthetic v072',laps,pd.DataFrame(labels),[]),pd.DataFrame(membership)


@pytest.fixture(scope='module')
def fitted(data,tmp_path_factory):
    corpus,split=data;root=tmp_path_factory.mktemp('v072')
    return experiment.run(corpus,output=root/'docs',model_root=root/'models',split=split),root


def test_development_excludes_historical_before_features_and_stable_group_folds(data):
    corpus,split=data
    development=experiment.development_pool(corpus,split)
    assert len(development.laps)==18
    assert set(development.targets.lap_uid).isdisjoint(split.query("partition=='test'").lap_uid)
    folds=experiment.group_folds(development)
    assert folds.groupby('physical_session_id').fold.nunique().eq(1).all()
    reversed_=deepcopy(development);reversed_.laps.reverse()
    pd.testing.assert_frame_equal(folds.sort_values('lap_uid').reset_index(drop=True),
                                 experiment.group_folds(reversed_).sort_values('lap_uid').reset_index(drop=True))


def test_unique_lap_statistics_and_common_training_pace_thresholds(data):
    corpus,split=data
    rows,(q25,q75)=population(corpus,split)
    assert len(rows)==21 and rows.lap_uid.nunique()==21
    expected=corpus.targets.loc[corpus.targets.lap_uid.isin(split.query("partition=='train'").lap_uid),'target_s']
    np.testing.assert_allclose([q25,q75],expected.quantile([.25,.75]))
    assert pace_band([q25-1,q25,q75,q75+1],q25,q75).tolist()==['fast','middle','middle','slow']


def test_same_population_every_variant_preprocessing_and_per_lap_weights(data,fitted):
    bundle,root=fitted;corpus,split=data
    predictions=bundle.predictions
    expected=set(zip(predictions.query("variant=='F0'").lap_uid,predictions.query("variant=='F0'").checkpoint_s))
    for variant,group in predictions.groupby('variant'):
        assert set(zip(group.lap_uid,group.checkpoint_s))==expected
        assert group.groupby('lap_uid').size().eq(5).all()
    dev=experiment.development_pool(corpus,split)
    table=snapshot_table(dev).merge(bundle.split[['lap_uid','fold']],on='lap_uid')
    recorded=pd.read_csv(root/'docs/DEVELOPMENT_PREPROCESSING_V072.csv')
    for (variant,fold),metadata in recorded.groupby(['variant','fold']):
        names=FEATURE_SETS[variant];train=table.loc[table.fold!=fold,names]
        expected=train.fillna(train.median()).fillna(0).mean().to_numpy()
        np.testing.assert_allclose(metadata.scaler_mean.to_numpy(),expected)
    weights=pd.read_csv(root/'docs/DEVELOPMENT_WEIGHTS_V072.csv')
    assert not weights.duplicated(['fold','lap_uid']).any()
    assert set(weights.lap_uid).issubset(set(dev.targets.lap_uid))
    for fold in table.fold.unique():
        train=table.loc[table.fold!=fold];w,info=experiment.training_weights(train)
        assert np.mean(w)==pytest.approx(1.)
        per_lap=pd.DataFrame(dict(lap_uid=train.lap_uid,weight=w)).groupby('lap_uid').weight
        assert per_lap.nunique().eq(1).all()
        unique=train[['lap_uid','target_s']].drop_duplicates('lap_uid').copy()
        unique['band']=pace_band(unique.target_s,info['q25_s'],info['q75_s'])
        unique['weight']=weights.query('fold==@fold').set_index('lap_uid').weight.reindex(unique.lap_uid).to_numpy()
        totals=unique.groupby('band').weight.sum()
        np.testing.assert_allclose(totals,totals.iloc[0])


def test_no_historical_target_or_telemetry_usage_for_experiments(data,fitted,tmp_path):
    corpus,split=data;reference,_=fitted
    changed=deepcopy(corpus);historical=set(split.query("partition=='test'").lap_uid)
    changed.targets.loc[changed.targets.lap_uid.isin(historical),'target_s']=999999
    for lap in changed.laps:
        if lap.lap_uid in historical:lap.frame.loc[:,'speed_kmh']=-999999
    other=experiment.run(changed,output=tmp_path/'docs',model_root=tmp_path/'models',split=split)
    pd.testing.assert_frame_equal(reference.predictions,other.predictions)
    assert reference.selected_model==other.selected_model
    assert json.loads((tmp_path/'docs/ML_RESULTS_V072.json').read_text(encoding='utf-8'))['historical_test_evaluations']==0


def test_experimental_replay_uses_training_builder_and_version_domain_guards(data,fitted):
    corpus,split=data;bundle,_=fitted
    source=next(l for l in corpus.laps if l.lap_uid in bundle.development_ids)
    for variant in FEATURE_SETS:
        expected,_=feature_row(source,30.,variant)
        direct=float(bundle.models[variant].predict(pd.DataFrame([expected],columns=FEATURE_SETS[variant]))[0])
        assert experiment.predict_experimental(source,30.,bundle,variant).predicted_final_s==direct
    with pytest.raises(ValueError,match='domain'):experiment.predict_experimental(replace(source,domain=('other','car')),10,bundle)
    historical=next(l for l in corpus.laps if l.lap_uid not in bundle.development_ids)
    with pytest.raises(ValueError,match='Historical'):experiment.predict_experimental(historical,10,bundle)
    bad=deepcopy(bundle);bad.compatibility['feature_version']='wrong'
    with pytest.raises(ValueError,match='version'):experiment.predict_experimental(source,10,bad)


def test_repeat_run_reads_signed_bundle_and_evidence_without_refitting(data,fitted,monkeypatch):
    corpus,split=data;bundle,root=fitted
    def forbidden():raise AssertionError('Frozen development run must not refit')
    monkeypatch.setattr(experiment,'make_models',forbidden)
    repeated=experiment.run(corpus,output=root/'docs',model_root=root/'models',split=split)
    pd.testing.assert_frame_equal(bundle.predictions,repeated.predictions)


def test_rebuild_missing_research_artifact_uses_development_only_without_rescoring(data,fitted,tmp_path,monkeypatch):
    import shutil
    from sklearn.pipeline import Pipeline
    corpus,split=data;bundle,root=fitted
    shutil.copytree(root/'docs',tmp_path/'docs')
    def forbidden(*args,**kwargs):raise AssertionError('Reconstruction must not score CV or historical test')
    monkeypatch.setattr(Pipeline,'predict',forbidden)
    rebuilt=experiment.run(corpus,output=tmp_path/'docs',model_root=tmp_path/'models',split=split)
    assert rebuilt.development_ids==bundle.development_ids
    assert (tmp_path/'docs/ML_RESULTS_V072.json').read_bytes()==(root/'docs/ML_RESULTS_V072.json').read_bytes()


def test_calibration_and_macro_metrics_do_not_treat_prefixes_as_unique_laps():
    frame=pd.DataFrame(dict(target_s=[100,100,200,200],prediction_s=[120,120,170,170],
        lap_uid=['a','a','b','b'],physical_session_id=['x','x','y','y']))
    result=experiment.metrics(frame)
    assert result['laps']==result['unique_laps']==2 and result['snapshots']==4
    assert result['recording_macro_mae_s']==25.
    assert calibration(frame)['predicted_on_actual_slope']==pytest.approx(.5)


def test_selection_needs_fold_consistency_macro_gain_and_slow_tail_guard():
    overall=pd.DataFrame([dict(variant='F0',mae_s=10.,rmse_s=12.,recording_macro_mae_s=11.),
                          dict(variant='F1',mae_s=9.,rmse_s=11.,recording_macro_mae_s=10.)])
    folds=pd.DataFrame([dict(variant=v,fold=i,mae_s=10. if v=='F0' else 9. if i<4 else 10.5)
                        for v in ('F0','F1') for i in range(5)])
    details=pd.DataFrame([dict(variant=v,dimension='pace_band',value='slow',mae_s=20. if v=='F0' else 19.,bias_s=-18.)
                          for v in ('F0','F1')])
    assert experiment.select_variant(overall,folds,details)[0]=='F1'
    bad=folds.copy();bad.loc[(bad.variant=='F1')&(bad.fold==0),'mae_s']=11.
    assert experiment.select_variant(overall,bad,details)[0]=='F0'
    bad=details.copy();bad.loc[bad.variant=='F1','mae_s']=20.6
    assert experiment.select_variant(overall,folds,bad)[0]=='F0'
    bad=overall.copy();bad.loc[bad.variant=='F1','recording_macro_mae_s']=10.8
    assert experiment.select_variant(bad,folds,details)[0]=='F0'
