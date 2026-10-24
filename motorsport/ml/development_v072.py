"""Limited SVR feature comparisons on development recordings only.

The historical test is filtered out before feature generation. Nothing in this
module accepts historical test scores or changes the production reference.
"""
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .training import TrainingBundle,make_models
from .dataset import Corpus
from .features import CHECKPOINTS
from .baselines import reference_history
from .barcelona_recovery import ROOT,DOMAIN,file_sha,baseline_references
from .barcelona_experiment import dump,table_write,detailed_metrics
from .diagnosis_v072 import pace_band,calibration
from .temporal_features_v072 import VERSION,FEATURE_SETS,UNITS,feature_row,snapshot_table
from .artifacts import LocalArtifactStore

PROTOCOL=ROOT/'docs/ML_PROTOCOL_V072.json'
MODEL_ROOT=ROOT/'artifacts/barcelona_v072/models'
VARIANTS=tuple(FEATURE_SETS)


@dataclass
class DevelopmentBundle(TrainingBundle):
    compatibility: dict
    feature_sets: dict
    development_ids: tuple


def development_pool(corpus,split):
    if split.lap_uid.duplicated().any() or set(split.lap_uid)!={l.lap_uid for l in corpus.laps}:
        raise ValueError('Original split/corpus identity mismatch')
    if split.groupby('physical_session_id').partition.nunique().max()!=1:
        raise ValueError('Linked recording block crosses original partitions')
    ids=set(split.loc[split.partition.isin(['train','validation']),'lap_uid'])
    laps=[l for l in corpus.laps if l.lap_uid in ids]
    if any(l.domain!=DOMAIN for l in laps):raise ValueError('Barcelona-only development required')
    return Corpus(corpus.name+' / v072 development only',laps,
                  corpus.targets.loc[corpus.targets.lap_uid.isin(ids)].copy(),[])


def group_folds(development):
    groups=sorted({lap.physical_session_id for lap in development.laps})
    if len(groups)<5:raise ValueError('The specified five nonempty recording folds require five development blocks')
    order=np.random.default_rng(42).permutation(groups).tolist()
    lookup={group:i%5 for i,group in enumerate(order)}
    return pd.DataFrame([dict(lap_uid=l.lap_uid,physical_session_id=l.physical_session_id,fold=lookup[l.physical_session_id])
                         for l in development.laps])


def training_weights(train):
    unique=train[['lap_uid','target_s']].drop_duplicates('lap_uid').copy()
    q25,q75=map(float,unique.target_s.quantile([.25,.75]))
    unique['pace_band']=pace_band(unique.target_s,q25,q75)
    counts=unique.pace_band.value_counts()
    classes=len(counts)
    unique['weight']=unique.pace_band.map(lambda band:len(unique)/(classes*counts[band]))
    lookup=unique.set_index('lap_uid').weight
    weights=train.lap_uid.map(lookup).to_numpy(float)
    weights/=weights.mean()
    return weights,dict(q25_s=q25,q75_s=q75,class_counts=counts.to_dict())


def metrics(rows):
    result=detailed_metrics(rows)
    errors=(rows.prediction_s-rows.target_s).abs()
    macro=rows.assign(ae=errors).groupby('physical_session_id').ae.mean()
    result.update(recording_macro_mae_s=float(macro.mean()),**calibration(rows))
    return result


def compare(predictions):
    overall=[];folds=[];details=[]
    for variant,rows in predictions.groupby('variant'):
        overall.append(dict(variant=variant,**metrics(rows)))
        for fold,g in rows.groupby('fold'):folds.append(dict(variant=variant,fold=fold,**metrics(g)))
        for dimension in ('checkpoint_s','pace_band','lap_uid','physical_session_id'):
            for value,g in rows.groupby(dimension):
                details.append(dict(variant=variant,dimension=dimension,value=value,**metrics(g)))
    return pd.DataFrame(overall),pd.DataFrame(folds),pd.DataFrame(details)


def select_variant(overall,folds,details):
    baseline=overall.set_index('variant').loc['F0']
    slow=details.query("dimension=='pace_band' and value=='slow'").set_index('variant')
    base_folds=folds.query("variant=='F0'").set_index('fold')
    decisions=[]
    for candidate in overall.variant:
        if candidate=='F0':continue
        row=overall.set_index('variant').loc[candidate]
        gains=base_folds.mae_s-folds.query('variant==@candidate').set_index('fold').mae_s
        gain=float(baseline.mae_s-row.mae_s)
        slow_ok=(candidate in slow.index and 'F0' in slow.index and slow.loc[candidate,'mae_s']<=slow.loc['F0','mae_s']+.5
                 and abs(slow.loc[candidate,'bias_s'])<=abs(slow.loc['F0','bias_s'])+.5)
        accepted=bool(gain>=.5 and gain>=.05*baseline.mae_s and
                      baseline.recording_macro_mae_s-row.recording_macro_mae_s>=.25 and
                      (gains>0).sum()>=4 and slow_ok)
        decisions.append(dict(variant=candidate,mae_gain_s=gain,relative_mae_gain=gain/baseline.mae_s,
            macro_gain_s=float(baseline.recording_macro_mae_s-row.recording_macro_mae_s),
            improved_folds=int((gains>0).sum()),slow_guard_passed=bool(slow_ok),qualifies=accepted))
    qualified=[r['variant'] for r in decisions if r['qualifies']]
    chosen=(overall.loc[overall.variant.isin(qualified)].sort_values(['mae_s','recording_macro_mae_s','rmse_s','variant']).iloc[0].variant
            if qualified else 'F0')
    return chosen,decisions


def compatibility(corpus,development,folds):
    return dict(domain=list(DOMAIN),base_corpus_id=corpus.identity,development_corpus_id=development.identity,
        feature_version=VERSION,feature_sets={k:list(v) for k,v in FEATURE_SETS.items()},additional_units=UNITS,
        protocol_sha256=file_sha(PROTOCOL),fold_identity=pd.util.hash_pandas_object(folds,index=False).sum().item(),
        model_version='development-svr-v072-1',historical_test_evaluations=0)


def save_bundle(bundle,model_root=MODEL_ROOT):
    path=LocalArtifactStore(model_root).save(bundle,'development-v072-'+bundle.corpus_id[:16])
    metadata=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    metadata.update(producer='Motorsport Telemetry Analyzer v072 experimental development SVR',compatibility=bundle.compatibility)
    dump(path.with_suffix('.json'),metadata)
    return path


def fit_development_models(table):
    models={};weights,_=training_weights(table)
    for variant in VARIANTS:
        model=make_models()['SVR'];names=FEATURE_SETS[variant]
        model.fit(table.loc[:,names],table.target_s,**({'model__sample_weight':weights} if variant=='F0W' else {}))
        models[variant]=model
    return models


def research_bundle(development,folds,predictions,models,selected,identity,overall,folds_report,details):
    return DevelopmentBundle(development.identity,'EXPERIMENTAL development-only CV; no new final test',
        FEATURE_SETS[selected],models,selected,folds,predictions,
        dict(overall=overall,folds=folds_report,details=details),pd.DataFrame(),[],pd.DataFrame(),DOMAIN,
        identity,FEATURE_SETS,tuple(sorted(development.targets.lap_uid)))


def load_bundle(corpus,model_root=MODEL_ROOT,split=None):
    split=split if split is not None else pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv')
    development=development_pool(corpus,split);folds=group_folds(development)
    store=LocalArtifactStore(model_root);name='development-v072-'+development.identity[:16]
    bundle=store.load(name)
    metadata=json.loads(store._path(name).with_suffix('.json').read_text(encoding='utf-8'))
    if bundle.compatibility!=compatibility(corpus,development,folds) or metadata.get('compatibility')!=bundle.compatibility:
        raise ValueError('Experimental domain/corpus/features/protocol metadata differs')
    return bundle


def predict_experimental(source,checkpoint,bundle,variant=None):
    if tuple(source.domain)!=DOMAIN or tuple(bundle.domain)!=DOMAIN:raise ValueError('Experimental model domain mismatch')
    if source.lap_uid not in bundle.development_ids:raise ValueError('Historical test/new sources are outside this development-only model')
    if bundle.compatibility.get('feature_version')!=VERSION or bundle.compatibility.get('protocol_sha256')!=file_sha(PROTOCOL):
        raise ValueError('Experimental feature/protocol version mismatch')
    variant=variant or bundle.selected_model
    if variant not in FEATURE_SETS or tuple(bundle.feature_sets.get(variant,()))!=FEATURE_SETS[variant]:
        raise ValueError('Experimental feature set mismatch')
    row,quality=feature_row(source,checkpoint,variant)
    value=float(bundle.models[variant].predict(pd.DataFrame([row],columns=FEATURE_SETS[variant]))[0])
    from .inference import Prediction
    return Prediction(float(checkpoint),value,None,quality['observed_elapsed_s'],quality,
                      'Experimental v072 development replay; fitted on development data')


def run(corpus,output=ROOT/'docs',model_root=MODEL_ROOT,split=None):
    split=split if split is not None else pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv')
    development=development_pool(corpus,split)
    folds=group_folds(development)
    identity=compatibility(corpus,development,folds)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result_path=output/'ML_RESULTS_V072.json'
    if result_path.exists():
        frozen=json.loads(result_path.read_text(encoding='utf-8'))
        if frozen['compatibility']!=identity:raise ValueError('Frozen v072 development experiment differs')
        for name,digest in frozen['evidence_sha256'].items():
            if file_sha(output/name)!=digest:raise ValueError('Frozen v072 evidence changed: '+name)
        artifact=Path(model_root)/('development-v072-'+development.identity[:16]+'.joblib')
        if artifact.exists():return load_bundle(corpus,model_root,split)
        # Fresh checkout: rebuild research models on DEVELOPMENT only, preserving
        # all OOF evidence without scoring any held-out fold or historical test.
        table=snapshot_table(development)
        models=fit_development_models(table)
        bundle=research_bundle(development,folds,pd.read_csv(output/'DEVELOPMENT_PREDICTIONS_V072.csv'),models,
            frozen['selection']['selected_development_variant'],identity,
            pd.read_csv(output/'DEVELOPMENT_OVERALL_V072.csv'),pd.read_csv(output/'DEVELOPMENT_FOLD_METRICS_V072.csv'),
            pd.read_csv(output/'DEVELOPMENT_DETAILS_V072.csv'))
        save_bundle(bundle,model_root)
        return bundle
    table_write(output/'DEVELOPMENT_FOLDS_V072.csv',folds)
    dump(output/'DEVELOPMENT_FREEZE_V072.json',dict(compatibility=identity,
        fold_recordings=folds.groupby('fold').physical_session_id.nunique().to_dict(),
        fold_laps=folds.groupby('fold').lap_uid.nunique().to_dict(),historical_test_role='excluded before feature generation'))
    table=snapshot_table(development).merge(folds[['lap_uid','fold']],on='lap_uid',validate='many_to_one')
    if not table.groupby('lap_uid').checkpoint_s.nunique().eq(len(CHECKPOINTS)).all():
        raise ValueError('A development lap lost a checkpoint')
    original_train=set(split.query("partition=='train'").lap_uid)
    original_targets=development.targets.loc[development.targets.lap_uid.isin(original_train),'target_s']
    q25,q75=map(float,original_targets.quantile([.25,.75]))
    table['pace_band']=pace_band(table.target_s,q25,q75)
    predictions=[];preprocessing=[];weight_rows=[];fit_rows=[]
    reliability=development.targets.set_index('lap_uid').date_reliable.to_dict()
    for fold in sorted(table.fold.unique()):
        train=table.loc[table.fold!=fold];validation=table.loc[table.fold==fold]
        history=reference_history(development,set(train.lap_uid))
        refs={l.lap_uid:baseline_references(l,history,reliability) for l in development.laps if l.lap_uid in set(validation.lap_uid)}
        weights,weight_info=training_weights(train)
        weight_rows.extend(dict(fold=int(fold),lap_uid=uid,weight=float(weight),**weight_info)
                           for uid,weight in zip(train.lap_uid,weights))
        for variant in VARIANTS:
            names=FEATURE_SETS[variant]
            model=make_models()['SVR']
            kwargs={'model__sample_weight':weights} if variant=='F0W' else {}
            model.fit(train.loc[:,names],train.target_s,**kwargs)
            scored=validation[['lap_uid','physical_session_id','driver_id','checkpoint_s','fold','target_s','pace_band']].copy()
            scored['variant']=variant;scored['prediction_s']=model.predict(validation.loc[:,names])
            scored['error_s']=scored.prediction_s-scored.target_s
            for baseline in ('historical_median','previous_lap'):
                scored[baseline]=pd.to_numeric(scored.lap_uid.map(lambda uid:refs[uid][baseline]),errors='coerce').astype(float)
            predictions.append(scored)
            for i,name in enumerate(names):
                preprocessing.append(dict(fold=int(fold),variant=variant,feature=name,
                    imputer_median=float(model.named_steps['imputer'].statistics_[i]),
                    scaler_mean=float(model.named_steps['scaler'].mean_[i]),
                    scaler_scale=float(model.named_steps['scaler'].scale_[i]),training_laps=train.lap_uid.nunique()))
            fit_rows.append(dict(fold=int(fold),variant=variant,training_laps=train.lap_uid.nunique(),
                validation_laps=validation.lap_uid.nunique(),training_blocks=train.physical_session_id.nunique(),
                validation_blocks=validation.physical_session_id.nunique(),support_vectors=len(model.named_steps['model'].support_),
                **metrics(scored)))
        print('Completed development fold',int(fold),':',train.lap_uid.nunique(),'train /',validation.lap_uid.nunique(),'held-out laps',flush=True)
    predictions=pd.concat(predictions,ignore_index=True)
    overall,fold_metrics,details=compare(predictions)
    chosen,decisions=select_variant(overall,fold_metrics,details)
    table_write(output/'DEVELOPMENT_PREDICTIONS_V072.csv',predictions)
    table_write(output/'DEVELOPMENT_OVERALL_V072.csv',overall)
    table_write(output/'DEVELOPMENT_FOLD_METRICS_V072.csv',pd.DataFrame(fit_rows))
    table_write(output/'DEVELOPMENT_DETAILS_V072.csv',details)
    table_write(output/'DEVELOPMENT_PREPROCESSING_V072.csv',pd.DataFrame(preprocessing))
    table_write(output/'DEVELOPMENT_WEIGHTS_V072.csv',pd.DataFrame(weight_rows).drop_duplicates(['fold','lap_uid']))
    table_write(output/'DEVELOPMENT_FEATURES_V072.csv',table)
    baseline_rows=[]
    for (variant,fold),rows in predictions.groupby(['variant','fold']):
        for baseline in ('historical_median','previous_lap'):
            matched=rows.loc[rows[baseline].notna()]
            baseline_rows.append(dict(variant=variant,fold=int(fold),baseline=baseline,coverage=len(matched)/len(rows),
                **detailed_metrics(matched,baseline),matched_model_mae_s=detailed_metrics(matched)['mae_s']))
    table_write(output/'DEVELOPMENT_BASELINES_V072.csv',pd.DataFrame(baseline_rows))
    selection=dict(selected_development_variant=chosen,production_reference='immutable v071 SVR',
                   convincing_improvement=chosen!='F0',decisions=decisions,historical_test_evaluations=0)
    dump(output/'DEVELOPMENT_SELECTION_V072.json',selection)
    # Prespecified examples: pace quantiles plus the hardest F0 OOF development lap.
    ordered=development.targets.sort_values(['target_s','lap_uid'])
    examples=[dict(example=label,lap_uid=ordered.iloc[int(q*(len(ordered)-1))].lap_uid)
              for label,q in [('fast',.1),('ordinary',.5),('slow',.9)]]
    worst=predictions.query("variant=='F0'").groupby('lap_uid').error_s.apply(lambda x:x.abs().mean()).sort_values(ascending=False).index[0]
    examples.append(dict(example='difficult F0 OOF',lap_uid=worst))
    examples=pd.DataFrame(examples).drop_duplicates('lap_uid')
    table_write(output/'DEVELOPMENT_EXAMPLES_V072.csv',predictions.merge(examples,on='lap_uid',validate='many_to_one'))
    # Final research artifacts use all DEVELOPMENT only, never the historical test.
    models=fit_development_models(table)
    bundle=research_bundle(development,folds,predictions,models,chosen,identity,overall,fold_metrics,details)
    save_bundle(bundle,model_root)
    result=dict(status='development_evaluated',compatibility=identity,selection=selection,
        development_laps=len(development.laps),development_blocks=len({l.physical_session_id for l in development.laps}),
        checkpoints_per_lap=len(CHECKPOINTS),overall=overall.to_dict('records'),historical_test_evaluations=0,
        evidence_sha256={p.name:file_sha(p) for p in output.glob('DEVELOPMENT_*_V072.csv')})
    result['evidence_sha256']['DEVELOPMENT_SELECTION_V072.json']=file_sha(output/'DEVELOPMENT_SELECTION_V072.json')
    result['evidence_sha256']['DEVELOPMENT_FREEZE_V072.json']=file_sha(output/'DEVELOPMENT_FREEZE_V072.json')
    dump(result_path,result)
    return bundle
