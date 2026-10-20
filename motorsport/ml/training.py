"""Reproducible sklearn pipelines with complete-session/lap holdouts."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.inspection import permutation_importance

from .dataset import eligibility
from .features import FEATURES, snapshots
from .baselines import reference_history, baseline_predictions
from .evaluation import summarize

EXPERIMENTAL = 'Experimental single-session case study — insufficient evidence for generalization.'


@dataclass
class TrainingBundle:
    corpus_id: str
    mode: str
    feature_names: tuple
    models: dict
    selected_model: str
    split: pd.DataFrame
    predictions: pd.DataFrame
    reports: dict
    importance: pd.DataFrame
    history: list
    snapshot_rejections: pd.DataFrame
    domain: tuple


def chronological_split(corpus, experimental=False):
    if len(corpus.laps)<6:
        raise ValueError('At least six validated laps are required for a development split')
    if not experimental and not eligibility(corpus)['eligible']:
        raise ValueError('Robust training disabled: '+'; '.join(eligibility(corpus)['reasons']))
    sessions={lap.physical_session_id for lap in corpus.laps}
    if experimental:
        if len(sessions)!=1:
            raise ValueError('Experimental mode requires exactly one physical session')
        groups = [lap.lap_uid for lap in corpus.laps]
        unit = 'lap_uid'
    else:
        groups = sorted(sessions,key=lambda s:(min(lap.start_order for lap in corpus.laps if lap.physical_session_id==s),s))
        unit = 'physical_session_id'
    n = len(groups)
    train_end = min(n-2,max(1,int(n*.6)))
    val_end = min(n-1,max(train_end+1,int(n*.8)))
    assignment = {g:('train' if i<train_end else 'validation' if i<val_end else 'test') for i,g in enumerate(groups)}
    rows = [{'lap_uid':lap.lap_uid,'physical_session_id':lap.physical_session_id,
             'partition':assignment[getattr(lap,unit)]} for lap in corpus.laps]
    split = pd.DataFrame(rows)
    if split.lap_uid.duplicated().any() or corpus.targets.fingerprint.duplicated().any():
        raise ValueError('Duplicate lap identities or trajectories in corpus')
    if not experimental and split.groupby('physical_session_id').partition.nunique().max()!=1:
        raise ValueError('A physical session crosses evaluation partitions')
    return split


def make_models():
    estimators = {'Ridge':Ridge(alpha=10.),
        'Random Forest':RandomForestRegressor(n_estimators=120,max_depth=6,min_samples_leaf=2,random_state=42,n_jobs=1),
        'SVR':SVR(C=10.,epsilon=.5,kernel='rbf')}
    return {name:Pipeline([('imputer',SimpleImputer(strategy='median',keep_empty_features=True)),
        *([('scaler',StandardScaler())] if name!='Random Forest' else []),('model',model)])
        for name,model in estimators.items()}


def train(corpus, feature_names=None, experimental=False, checkpoints=None):
    feature_names = tuple(FEATURES if feature_names is None else feature_names)
    if not feature_names or len(set(feature_names))!=len(feature_names) or set(feature_names)-set(FEATURES):
        raise ValueError('Training accepts only the reviewed causal feature allowlist')
    if len({lap.domain for lap in corpus.laps})!=1:
        raise ValueError('Training across car/track domains is disabled')
    split = chronological_split(corpus,experimental)
    table,rejections = snapshots(corpus,**({'checkpoints':checkpoints} if checkpoints is not None else {}))
    if table.empty:
        raise ValueError('No eligible causal snapshots')
    table = table.merge(split[['lap_uid','partition']],on='lap_uid',validate='many_to_one')
    for partition,minimum in [('train',3),('validation',1),('test',1)]:
        if table.loc[table.partition==partition,'lap_uid'].nunique()<minimum:
            raise ValueError(f'Insufficient accepted laps in {partition}')
    train_rows = table.loc[table.partition=='train']
    history = reference_history(corpus,set(train_rows.lap_uid))
    baseline_map = {lap.lap_uid:baseline_predictions(lap,history) for lap in corpus.laps}
    for name in ('previous_lap','historical_median'):
        table[name] = table.lap_uid.map(lambda uid:baseline_map[uid][name])
    models = make_models()
    prediction_rows,importances = [],[]
    validation = table.loc[table.partition=='validation']
    # Eligibility and feature choice precede partitioning; no imputation, scaling
    # or feature statistic is learned from validation/test rows.
    for name,model in models.items():
        model.fit(train_rows.loc[:,feature_names],train_rows.target_s)
        for partition in ('validation','test'):
            rows = table.loc[table.partition==partition].copy()
            rows['prediction_s'] = model.predict(rows.loc[:,feature_names])
            rows['model'] = name
            rows['error_s'] = rows.prediction_s-rows.target_s
            prediction_rows.append(rows)
        if validation.lap_uid.nunique()>=5:
            importance = permutation_importance(model,validation.loc[:,feature_names],validation.target_s,
                n_repeats=3,random_state=42,scoring='neg_mean_absolute_error',n_jobs=1)
            importances.extend({'model':name,'feature':f,'mae_increase_s':float(v),
                'repeat_std_s':float(s),'partition':'validation'}
                for f,v,s in zip(feature_names,importance.importances_mean,importance.importances_std))
    predictions = pd.concat(prediction_rows,ignore_index=True)
    reports = summarize(predictions)
    selected = reports['overall'].query("partition == 'validation'").sort_values('mae_s').model.iloc[0]
    return TrainingBundle(corpus.identity,EXPERIMENTAL if experimental else 'Evaluated ML · chronological physical-session holdout',
        feature_names,models,selected,split,predictions,reports,pd.DataFrame(importances),history,rejections,corpus.laps[0].domain)
