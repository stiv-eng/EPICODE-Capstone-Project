"""Read frozen evidence, audit joins/splits and run three fixed development fits.

No production model or frozen result writer is called. Diagnostic fitting sees
only training/validation laps, uses the existing fixed estimators, and never
selects/tunes a variant against the inspected final test set.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motorsport.ingestion.acgym_importer import load_acgym_sessions
from motorsport.ml.dataset import from_sessions,independent_subset,Corpus
from motorsport.ml.features import snapshots,FEATURES
from motorsport.ml.training import chronological_split,make_models
from motorsport.ml.evaluation import metrics
from motorsport.ml.baselines import reference_history,baseline_predictions

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_OUTPUTS={ROOT/'docs/ML_HEALTH_EVIDENCE_V062.json',ROOT/'docs/ML_HEALTH_GROUPS_V062.csv'}


def write_evidence(path,content):
    path=Path(path).resolve()
    if path not in {p.resolve() for p in ALLOWED_OUTPUTS}:
        raise ValueError('Only separate v0.6.2 diagnostic evidence can be written')
    path.write_text(content,encoding='utf-8')


def protected_state():
    paths=[p for p in (ROOT/'docs').glob('*V06*') if 'V061' not in p.name and 'V062' not in p.name and p.is_file()]
    paths+=list((ROOT/'artifacts/models').rglob('*')) if (ROOT/'artifacts/models').exists() else []
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def residual_stats(frame,column='prediction_s'):
    result=metrics(frame,column)
    error=frame[column]-frame.target_s
    result.update(median_error_s=float(error.median()),median_absolute_error_s=float(error.abs().median()),
                  p90_absolute_error_s=float(error.abs().quantile(.9)),max_absolute_error_s=float(error.abs().max()),
                  positive_errors=int((error>0).sum()),negative_errors=int((error<0).sum()),
                  actual_min_s=float(frame.target_s.min()),actual_max_s=float(frame.target_s.max()),
                  prediction_min_s=float(frame[column].min()),prediction_max_s=float(frame[column].max()))
    return result


def assess():
    protected=protected_state()
    frozen=json.loads((ROOT/'docs/ML_RESULTS_V06.json').read_text(encoding='utf-8'))['ACGym']
    errors=pd.read_csv(ROOT/'docs/ACGYM_ML_ERRORS_V06.csv')
    sessions,rejected=load_acgym_sessions()
    corpus=independent_subset(from_sessions(sessions,'v0.6.2 diagnostic audit'))
    split=chronological_split(corpus)
    old_split=pd.DataFrame(frozen['split'])
    current=split.sort_values('lap_uid').reset_index(drop=True)
    old=old_split[list(current)].sort_values('lap_uid').reset_index(drop=True)
    pd.testing.assert_frame_equal(current,old)
    targets=corpus.targets
    joined=errors.merge(targets[['lap_uid','target_s','driver_id','fingerprint']],on='lap_uid',suffixes=('','_verified'),validate='many_to_one')
    np.testing.assert_allclose(joined.target_s,joined.target_s_verified,rtol=0,atol=1e-9)
    np.testing.assert_allclose(joined.error_s,joined.prediction_s-joined.target_s,rtol=0,atol=1e-9)
    assert not targets.fingerprint.duplicated().any()
    assert split.groupby('physical_session_id').partition.nunique().max()==1
    verified=[]
    for row in frozen['metrics']['overall']:
        selected=joined.loc[(joined.model==row['model'])&(joined.partition==row['partition'])]
        actual=metrics(selected)
        for name in ('mae_s','rmse_s','bias_s'):
            np.testing.assert_allclose(actual[name],row[name],rtol=0,atol=1e-9)
        verified.append({'model':row['model'],'partition':row['partition'],**residual_stats(selected)})
    baselines=[]
    # One copy per lap/checkpoint; model rows must not multiply baseline evidence.
    unique=joined.drop_duplicates(['partition','lap_uid','checkpoint_s'])
    for partition,frame in unique.groupby('partition'):
        for column in ('previous_lap','historical_median'):
            usable=frame.loc[np.isfinite(frame[column])]
            baselines.append({'partition':partition,'baseline':column,**residual_stats(usable,column)})
    groups=[]
    for by in ('checkpoint_s','lap_uid','physical_session_id','driver_id'):
        for (model,partition,key),frame in joined.groupby(['model','partition',by]):
            groups.append({'group_by':by,'group':str(key),'model':model,'partition':partition,**residual_stats(frame)})
    group_table=pd.DataFrame(groups)
    target_rows=targets.merge(split[['lap_uid','partition']],on='lap_uid',validate='one_to_one')
    population=[]
    for partition,frame in target_rows.groupby('partition'):
        population.append({'partition':partition,'laps':len(frame),'sessions':frame.physical_session_id.nunique(),
            'drivers':frame.driver_id.nunique(),'min_s':float(frame.target_s.min()),'q25_s':float(frame.target_s.quantile(.25)),
            'median_s':float(frame.target_s.median()),'q75_s':float(frame.target_s.quantile(.75)),
            'max_s':float(frame.target_s.max()),'std_s':float(frame.target_s.std())})
    train_targets=target_rows.query("partition=='train'").target_s
    history=reference_history(corpus,set(split.loc[split.partition=='train','lap_uid']))
    source_by_uid={lap.lap_uid:lap for lap in corpus.laps}
    for uid,frame in joined.groupby('lap_uid'):
        expected=baseline_predictions(source_by_uid[uid],history)
        for column in ('previous_lap','historical_median'):
            np.testing.assert_allclose(frame[column],expected[column],rtol=0,atol=1e-9)
    q25,q75=train_targets.quantile([.25,.75])
    band=lambda values:np.select([values<q25,values>q75],['faster_than_training_Q25','slower_than_training_Q75'],default='training_middle')
    joined['target_band']=band(joined.target_s)
    bands=[]
    for (model,partition,key),frame in joined.groupby(['model','partition','target_band']):
        bands.append({'model':model,'partition':partition,'band':key,**residual_stats(frame)})
    relationships=[]
    for (model,partition),frame in joined.groupby(['model','partition']):
        # Average each lap's checkpoints before correlation to avoid pretending
        # that five copies of a target are five independent physical examples.
        laps=frame.groupby('lap_uid').agg(target_s=('target_s','first'),prediction_s=('prediction_s','mean'))
        residual=laps.prediction_s-laps.target_s
        relationships.append({'model':model,'partition':partition,'laps':len(laps),
            'prediction_vs_target_slope':float(np.polyfit(laps.target_s,laps.prediction_s,1)[0]),
            'residual_target_correlation':float(residual.corr(laps.target_s)),
            'mean_lap_prediction_min_s':float(laps.prediction_s.min()),'mean_lap_prediction_max_s':float(laps.prediction_s.max())})
    svr=joined.query("model=='SVR' and partition=='test'")
    concentration=[]
    total=(svr.prediction_s-svr.target_s).abs().sum()
    for key,frame in svr.groupby('physical_session_id'):
        concentration.append({'session':key,'driver':frame.driver_id.iloc[0],
            'absolute_error_share':float((frame.prediction_s-frame.target_s).abs().sum()/total),**residual_stats(frame)})
    # Development diagnostics: exactly three fixed-model fits; no test frames or
    # labels enter this table, and no model selection/parameter change is performed.
    dev_ids=set(split.loc[split.partition!='test','lap_uid'])
    dev=Corpus('diagnostic development only',[lap for lap in corpus.laps if lap.lap_uid in dev_ids],
               targets.loc[targets.lap_uid.isin(dev_ids)].copy(),[])
    table,rejections=snapshots(dev)
    assert rejections.empty
    table=table.merge(split[['lap_uid','partition']],on='lap_uid',validate='many_to_one')
    assert set(table.partition)=={'train','validation'}
    training=table.query("partition=='train'")
    diagnostics=[]
    for name,model in make_models().items():
        model.fit(training.loc[:,FEATURES],training.target_s)
        for partition,frame in table.groupby('partition'):
            measured=frame.assign(prediction_s=model.predict(frame.loc[:,FEATURES]))
            diagnostics.append({'experiment':'fixed v0.6 configuration / development-only / no tuning',
                'model':name,'partition':partition,'evaluation':'in-sample' if partition=='train' else 'existing validation',
                **residual_stats(measured)})
    correlations=training.loc[:,FEATURES].corr()
    redundant=[{'left':a,'right':b,'correlation':float(correlations.loc[a,b])}
               for i,a in enumerate(FEATURES) for b in FEATURES[i+1:]
               if pd.notna(correlations.loc[a,b]) and abs(correlations.loc[a,b])>=.9]
    feature_status=[{'feature':c,'finite_fraction':float(np.isfinite(training[c]).mean()),
                     'std':float(training[c].std()),'unique_values':int(training[c].nunique())} for c in FEATURES]
    # Whole-lap targets are used here only to describe checkpoint coverage.
    coverage=[{'checkpoint_s':checkpoint,'min_lap_fraction':float((checkpoint/targets.target_s).min()),
               'median_lap_fraction':float((checkpoint/targets.target_s).median()),
               'max_lap_fraction':float((checkpoint/targets.target_s).max())} for checkpoint in (10,20,30,45,60)]
    train_drivers=set(target_rows.query("partition=='train'").driver_id)
    driver_overlap={partition:sorted(train_drivers&set(frame.driver_id)) for partition,frame in target_rows.groupby('partition') if partition!='train'}
    gt7_errors=pd.read_csv(ROOT/'docs/GT7_ML_ERRORS_V06.csv')
    gt7_frozen=json.loads((ROOT/'docs/ML_RESULTS_V06.json').read_text(encoding='utf-8'))['GT7']
    gt7_rows=[]
    for row in gt7_frozen['metrics']['overall']:
        frame=gt7_errors.loc[(gt7_errors.model==row['model'])&(gt7_errors.partition==row['partition'])]
        measured=metrics(frame)
        for name in ('mae_s','rmse_s','bias_s'):
            np.testing.assert_allclose(measured[name],row[name],rtol=0,atol=1e-9)
        gt7_rows.append({'model':row['model'],'partition':row['partition'],**measured})
    gt7_baselines=[]
    for partition,frame in gt7_errors.drop_duplicates(['partition','lap_uid','checkpoint_s']).groupby('partition'):
        for baseline in ('previous_lap','historical_median'):
            gt7_baselines.append({'partition':partition,'baseline':baseline,**metrics(frame,baseline)})
    slow_cases=[]
    for uid in svr.assign(abs_error=lambda f:f.error_s.abs()).sort_values('abs_error',ascending=False).lap_uid.drop_duplicates().head(3):
        lap=source_by_uid[uid];frame=lap.frame
        t=frame.lap_elapsed_s.to_numpy();speed=frame.speed_kmh.to_numpy();weights=np.r_[np.diff(t),0.]
        slow_cases.append({'scope':'retrospective descriptive full-lap telemetry, never a predictive feature',
            'lap_uid':uid,'session':lap.physical_session_id,'verified_target_s':float(targets.set_index('lap_uid').loc[uid,'target_s']),
            'speed_at_60_kmh':float(speed[np.searchsorted(t,60,side='right')-1]),
            'minimum_speed_kmh':float(speed.min()),'minimum_speed_at_s':float(t[np.argmin(speed)]),
            'seconds_below_30_kmh_before_60':float(weights[(t<=60)&(speed<30)].sum()),
            'seconds_below_30_kmh_after_60':float(weights[(t>60)&(speed<30)].sum())})
    assert protected_state()==protected,'Original frozen evidence/model artifacts changed'
    evidence={'scope':'v0.6.2 descriptive frozen audit + fixed development-only diagnostics; no tuning',
        'audit':{'verified_laps':len(targets),'physical_sessions':split.physical_session_id.nunique(),
                 'participants':targets.driver_id.nunique(),'source_recording_rejections':len(rejected),
                 'splits_match_frozen':True,'targets_match_source':True,'exact_signatures_unique':True,
                 'frozen_baselines_match_allowed_training_history':True,
                 'frozen_files_and_model_artifacts_unchanged':True,'protected_files':len(protected)},
        'population':population,'overall':verified,'baselines':baselines,'target_bands':bands,
        'training_target_band_thresholds_s':[float(q25),float(q75)],'lap_level_relationships':relationships,
        'svr_test_session_concentration':concentration,
        'largest_svr_test_errors':svr.assign(abs_error_s=lambda x:x.error_s.abs()).nlargest(10,'abs_error_s')[
            ['lap_uid','physical_session_id','driver_id','checkpoint_s','target_s','prediction_s','error_s']].to_dict('records'),
        'development_diagnostics':diagnostics,'feature_status_training_only':feature_status,
        'high_feature_correlations_training_only':redundant,'checkpoint_fraction_descriptive_only':coverage,
        'participant_overlap_with_training':driver_overlap,
        'gt7_experimental_frozen_audit':{'scope':'single-session 4/2/2 lap split; no new fitting',
                                       'overall':gt7_rows,'baselines':gt7_baselines},
        'largest_error_lap_telemetry_descriptive_only':slow_cases,
        'source_session_headers':[{'session':s.metadata['physical_session_id'],'driver':s.metadata['driver_id'],
            'date':s.metadata['source_header']['date'],'time':s.metadata['source_header']['time'],
            'export_hz':s.metadata['export_hz']} for s in sessions if s.metadata['independence_verified']]}
    write_evidence(ROOT/'docs/ML_HEALTH_EVIDENCE_V062.json',json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    write_evidence(ROOT/'docs/ML_HEALTH_GROUPS_V062.csv',group_table.to_csv(index=False))
    folder=ROOT/'artifacts/v062';folder.mkdir(parents=True,exist_ok=True)
    figure=make_subplots(rows=1,cols=2,subplot_titles=['Frozen test: mean prediction per complete lap','SVR frozen errors by checkpoint'])
    for name,frame in joined.query("partition=='test'").groupby('model'):
        laps=frame.groupby('lap_uid').agg(target_s=('target_s','first'),prediction_s=('prediction_s','mean'))
        figure.add_trace(go.Scatter(x=laps.target_s,y=laps.prediction_s,name=name,mode='markers'),row=1,col=1)
    lo,hi=svr.target_s.min(),svr.target_s.max()
    figure.add_trace(go.Scatter(x=[lo,hi],y=[lo,hi],name='Identity',mode='lines',line=dict(dash='dash')),row=1,col=1)
    for session,frame in svr.groupby('physical_session_id'):
        figure.add_trace(go.Scatter(x=frame.checkpoint_s,y=frame.error_s,name=session,mode='markers'),row=1,col=2)
    figure.update_xaxes(title_text='Verified lap time (s)',row=1,col=1)
    figure.update_yaxes(title_text='Mean across five checkpoint predictions (s)',row=1,col=1)
    figure.update_xaxes(title_text='Checkpoint (s)',row=1,col=2)
    figure.update_yaxes(title_text='Prediction − verified (s)',row=1,col=2)
    figure.update_layout(title='v0.6.2 descriptive audit — frozen v0.6 results, no new selection',height=620,template='plotly_dark')
    figure.write_html(folder/'ml_health_residuals.html',include_plotlyjs=True)
    print(json.dumps({'audit':evidence['audit'],'population':population,'diagnostics':diagnostics,
                      'svr_test_sessions':concentration,'relationships':relationships},indent=2))
    return evidence


if __name__=='__main__':
    assess()
