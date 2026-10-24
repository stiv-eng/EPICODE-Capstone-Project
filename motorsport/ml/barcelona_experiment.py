"""Gated Barcelona protocol. Historical training/model definitions are reused.

No fitting occurs until the complete preregistered data gate passes. The selected
model alone sees the final test; existing frozen runs are verified and reused.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .training import TrainingBundle,make_models
from .features import FEATURES,snapshots
from .baselines import reference_history,baseline_predictions
from .evaluation import metrics,summarize
from .artifacts import LocalArtifactStore
from .barcelona import (ROOT,PROTOCOL,DOMAIN,data_gate,frozen_split,compatibility,
                         verify_compatibility,permissible_history,file_sha)


@dataclass
class BarcelonaBundle(TrainingBundle):
    compatibility: dict


def detailed_metrics(frame,prediction='prediction_s'):
    result=metrics(frame,prediction)
    error=(frame[prediction]-frame.target_s).dropna().abs()
    result.update(median_absolute_error_s=float(error.median()) if len(error) else None,
        p90_absolute_error_s=float(error.quantile(.9)) if len(error) else None,
        max_absolute_error_s=float(error.max()) if len(error) else None,
        groups=frame.physical_session_id.nunique())
    return result


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')


def table_write(path,frame):
    Path(path).write_text(frame.to_csv(index=False,lineterminator='\n'),encoding='utf-8',newline='\n')


def save_bundle(bundle,model_root):
    path=LocalArtifactStore(model_root).save(bundle,'barcelona-v07-'+bundle.corpus_id[:16])
    metadata=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    metadata.update(producer='Motorsport Telemetry Analyzer v0.7 local Barcelona training',compatibility=bundle.compatibility)
    dump(path.with_suffix('.json'),metadata)
    return path


def load_bundle(corpus,model_root):
    name='barcelona-v07-'+corpus.identity[:16]
    store=LocalArtifactStore(model_root)
    bundle=store.load(name)  # Local HMAC/hash verification precedes deserialization.
    verify_compatibility(bundle,corpus)
    metadata=json.loads(store._path(name).with_suffix('.json').read_text(encoding='utf-8'))
    if metadata.get('compatibility')!=bundle.compatibility:raise ValueError('Artifact domain/provenance metadata mismatch')
    return bundle


def run(corpus,audit,output=ROOT/'docs',model_root=ROOT/'artifacts/barcelona_v07/models'):
    gate=data_gate(corpus,audit)
    if not gate['eligible']:
        raise ValueError('Barcelona data gate failed; no model fit/test: '+'; '.join(gate['reasons']))
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result_path=output/'ML_RESULTS_V07.json'
    model_path=Path(model_root)/('barcelona-v07-'+corpus.identity[:16]+'.joblib')
    if result_path.exists():
        frozen=json.loads(result_path.read_text(encoding='utf-8'))
        if frozen['compatibility']!=compatibility(corpus):raise ValueError('Existing experiment differs; preserve it and preregister a separate protocol')
        for name,digest in frozen['evidence_sha256'].items():
            if file_sha(output/name)!=digest:raise ValueError('Frozen evaluation evidence changed: '+name)
        if model_path.exists():return load_bundle(corpus,model_root)
        # Reinstall a trusted model on a new machine, fitting TRAIN only. Reuse
        # all frozen evaluation rows, never predict/evaluate the final test again.
        split=pd.read_csv(output/'BARCELONA_SPLIT_V07.csv')
        table,rejections=snapshots(corpus);table=table.merge(split[['lap_uid','partition']],on='lap_uid',validate='many_to_one')
        train=table.query("partition=='train'");models=make_models()
        for model in models.values():model.fit(train.loc[:,FEATURES],train.target_s)
        predictions=pd.read_csv(output/'BARCELONA_PREDICTIONS_V07.csv')
        history=reference_history(corpus,set(train.lap_uid))
        bundle=BarcelonaBundle(corpus.identity,'Barcelona · frozen chronological grouped experiment',tuple(FEATURES),models,
            frozen['selected_model'],split,predictions,summarize(predictions),pd.DataFrame(),history,rejections,DOMAIN,compatibility(corpus))
        save_bundle(bundle,model_root);return bundle
    split=frozen_split(corpus)
    freeze=dict(compatibility=compatibility(corpus),gate=gate,groups=split.groupby(['physical_session_id','partition']).size().reset_index(name='laps').to_dict('records'))
    freeze_path=output/'BARCELONA_SPLIT_V07.json'
    if freeze_path.exists() and json.loads(freeze_path.read_text(encoding='utf-8'))!=freeze:
        raise ValueError('Existing frozen split differs')
    dump(freeze_path,freeze);table_write(output/'BARCELONA_SPLIT_V07.csv',split)
    table,rejections=snapshots(corpus)
    table=table.merge(split[['lap_uid','partition']],on='lap_uid',validate='many_to_one')
    for partition in ('train','validation','test'):
        if table.query('partition==@partition').lap_uid.nunique()!=split.query('partition==@partition').lap_uid.nunique():
            raise ValueError('Snapshot coverage differs from frozen lap population; preregister review before fitting')
    train=table.query("partition=='train'");validation=table.query("partition=='validation'")
    history=reference_history(corpus,set(train.lap_uid))
    references={lap.lap_uid:baseline_predictions(lap,permissible_history(lap,history)) for lap in corpus.laps}
    for name in ('previous_lap','historical_median'):table[name]=table.lap_uid.map(lambda uid:references[uid][name])
    train=table.query("partition=='train'");validation=table.query("partition=='validation'")
    group_days={lap.physical_session_id:lap.start_order[0] for lap in corpus.laps if lap.lap_uid in set(train.lap_uid)}
    days=sorted(set(group_days.values()))
    groups=sorted(group_days,key=lambda g:(group_days[g],g))
    train_targets=corpus.targets.loc[corpus.targets.lap_uid.isin(train.lap_uid)].target_s
    q25,q75=map(float,train_targets.quantile([.25,.75]))
    populations=[]
    for desired in sorted({max(2,len(groups)//2),max(2,int(len(groups)*.75)),len(groups)}):
        last_day=group_days[groups[desired-1]]
        population=[g for g in groups if group_days[g]<=last_day]
        if population not in populations:populations.append(population)
    curves=[]
    for population in populations:
        count=len(population)
        subset=train.loc[train.physical_session_id.isin(population)]
        for name,model in make_models().items():
            model.fit(subset.loc[:,FEATURES],subset.target_s)
            for label,rows in [('train',subset),('validation',validation)]:
                predicted=rows.assign(prediction_s=model.predict(rows.loc[:,FEATURES]))
                errors=predicted.assign(absolute_error=(predicted.prediction_s-predicted.target_s).abs())
                group_errors=errors.groupby('physical_session_id').absolute_error.mean()
                slow=errors.loc[errors.target_s>q75]
                curves.append(dict(training_groups=count,model=name,partition=label,**detailed_metrics(predicted),
                    slow_lap_mae_s=float(slow.absolute_error.mean()) if len(slow) else None,
                    group_mae_min_s=float(group_errors.min()),group_mae_max_s=float(group_errors.max()),
                    group_mae_std_s=float(group_errors.std()) if len(group_errors)>1 else None))
    table_write(output/'BARCELONA_LEARNING_CURVE_V07.csv',pd.DataFrame(curves))
    models=make_models();development=[]
    for name,model in models.items():
        model.fit(train.loc[:,FEATURES],train.target_s)
        rows=validation.assign(prediction_s=model.predict(validation.loc[:,FEATURES]),model=name)
        rows['error_s']=rows.prediction_s-rows.target_s;development.append(rows)
    validation_predictions=pd.concat(development,ignore_index=True)
    scores=pd.DataFrame([dict(model=name,**detailed_metrics(rows)) for name,rows in validation_predictions.groupby('model')])
    scores['absolute_bias_s']=scores.bias_s.abs()
    selected=scores.sort_values(['mae_s','rmse_s','absolute_bias_s','model']).iloc[0].model
    dump(output/'BARCELONA_SELECTION_V07.json',dict(selected_model=selected,rule=json.loads(PROTOCOL.read_text(encoding='utf-8'))['selection'],validation=scores.to_dict('records'),test_evaluated=False))
    # This is the sole final-test prediction call, after all development decisions.
    test=table.query("partition=='test'").copy()
    test['prediction_s']=models[selected].predict(test.loc[:,FEATURES]);test['model']=selected
    test['error_s']=test.prediction_s-test.target_s
    predictions=pd.concat([validation_predictions,test],ignore_index=True)
    predictions['participant_code']=predictions.driver_id.str.removeprefix('acgym:')
    table_write(output/'BARCELONA_PREDICTIONS_V07.csv',predictions)
    reports=summarize(predictions)
    for name,frame in reports.items():table_write(output/f'BARCELONA_{name.upper()}_V07.csv',frame)
    bands=predictions.assign(pace_band=np.where(predictions.target_s<q25,'fast',np.where(predictions.target_s>q75,'slow','middle')))
    band_rows=[dict(partition=p,model=m,pace_band=b,**detailed_metrics(g)) for (p,m,b),g in bands.groupby(['partition','model','pace_band'])]
    table_write(output/'BARCELONA_PACE_V07.csv',pd.DataFrame(band_rows))
    participant_rows=[dict(partition=p,model=m,participant_code=d,**detailed_metrics(g)) for (p,m,d),g in predictions.groupby(['partition','model','participant_code'])]
    table_write(output/'BARCELONA_PARTICIPANTS_V07.csv',pd.DataFrame(participant_rows))
    evidence={p.name:file_sha(p) for p in output.glob('BARCELONA_*_V07.csv')}
    result=dict(status='evaluated',compatibility=compatibility(corpus),selected_model=selected,gate=gate,
        selection_rule='validation MAE, RMSE, absolute bias, model name',validation=scores.to_dict('records'),
        selected_test=detailed_metrics(test),training_target_quartiles=[q25,q75],test_evaluations=1,
        uncertainty='No inferential confidence interval with fewer than eight independent final-test groups',evidence_sha256=evidence)
    dump(result_path,result)
    bundle=BarcelonaBundle(corpus.identity,'Barcelona · frozen chronological grouped experiment',tuple(FEATURES),models,selected,
        split,predictions,reports,pd.DataFrame(),history,rejections,DOMAIN,compatibility(corpus))
    save_bundle(bundle,model_root)
    return bundle
