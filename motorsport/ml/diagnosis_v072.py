"""Read-only diagnosis of the preserved Barcelona reference and populations.

Historical test rows are descriptive frozen evidence, never experimental inputs.
No estimator is fitted in this module except a diagnostic training-only scaler
for distances between development feature vectors (not a prediction model).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler

from .barcelona_recovery import ROOT, file_sha
from .barcelona_experiment import dump, table_write
from .features import FEATURES, snapshots


def preserved_inventory(root=ROOT):
    root=Path(root)
    paths=[*root.glob('docs/*V071*'), *root.glob('docs/*V06.*'),
           *root.glob('artifacts/barcelona_v071/models/*'), *root.glob('artifacts/models/*')]
    return {str(p.relative_to(root)).replace('\\','/'):file_sha(p) for p in paths if p.is_file()}


def verify_inventory(inventory,root=ROOT):
    differences=[name for name,digest in inventory.items() if not (Path(root)/name).exists() or file_sha(Path(root)/name)!=digest]
    if differences:raise ValueError('Preserved reference changed: '+', '.join(differences))


def population(corpus,split):
    if set(split.lap_uid)!={lap.lap_uid for lap in corpus.laps} or split.lap_uid.duplicated().any():
        raise ValueError('Frozen population differs from corpus')
    if split.groupby('physical_session_id').partition.nunique().max()!=1:
        raise ValueError('Frozen recording block crosses partitions')
    columns=['lap_uid','physical_session_id','driver_id','target_s','metadata_uncertainty','source']
    labels=corpus.targets.loc[:,columns]
    rows=labels.merge(split[['lap_uid','partition']],on='lap_uid',validate='one_to_one')
    train=rows.query("partition=='train'")
    q25,q75=map(float,train.target_s.quantile([.25,.75]))
    rows['pace_band']=pace_band(rows.target_s,q25,q75)
    return rows,(q25,q75)


def pace_band(target,q25,q75):
    return np.where(np.asarray(target)<q25,'fast',np.where(np.asarray(target)>q75,'slow','middle'))


def calibration(rows):
    actual=rows.target_s.to_numpy(float);predicted=rows.prediction_s.to_numpy(float)
    spread=float(np.std(actual,ddof=1)) if len(actual)>1 else 0.
    predicted_spread=float(np.std(predicted,ddof=1)) if len(actual)>1 else 0.
    slope,intercept=map(float,np.polyfit(actual,predicted,1)) if spread>1e-10 else (np.nan,np.nan)
    return dict(target_mean_s=float(actual.mean()),prediction_mean_s=float(predicted.mean()),
                target_std_s=spread,prediction_std_s=predicted_spread,
                prediction_to_target_std=predicted_spread/spread if spread else np.nan,
                predicted_on_actual_slope=slope,predicted_on_actual_intercept_s=intercept,
                unique_laps=rows.lap_uid.nunique(),snapshots=len(rows))


def audit_source_progress(development,output=ROOT/'docs'):
    from motorsport.ingestion.motec import read_ld
    from .barcelona_recovery import RAW
    rows=[]
    for source,group in development.targets.groupby('source'):
        _,channels=read_ld(RAW/source,['Car Pos Norm','Session Lap Count','Lap Time'])
        count=np.round(channels['Session Lap Count'].values).astype(int)
        for lap in group.itertuples(index=False):
            mask=count==int(lap.source_lap)-1
            t=channels['Lap Time'].values[mask];p=channels['Car Pos Norm'].values[mask]
            observed=p[(t<=60)&np.isfinite(t)]
            rows.append(dict(lap_uid=lap.lap_uid,source=source,export_hz=channels['Car Pos Norm'].hz,
                declared_unit=channels['Car Pos Norm'].unit,samples_to_60s=len(observed),
                min_progress=float(observed.min()),max_progress=float(observed.max()),
                decreasing_steps=int((np.diff(observed)<-1e-6).sum()),current_at_60=float(observed[-1])))
    frame=pd.DataFrame(rows);output=Path(output)
    table_write(output/'PROGRESS_SOURCE_AUDIT_V072.csv',frame)
    dump(output/'PROGRESS_STATUS_V072.json',dict(development_laps_inspected=len(frame),channel='Car Pos Norm',
        min_progress=float(frame.min_progress.min()),max_progress=float(frame.max_progress.max()),
        laps_with_decreasing_prefix_steps=int((frame.decreasing_steps>0).sum()),
        decision='Raw normalized-position F4 omitted as preregistered: exact ACTI export mapping/resampling semantics not established. '
        'Bounded position-like values are not proof of that mapping. Backward motion can be legitimate; no lap is removed. '
        'Only independent causal ground-speed integration enters F2/F3, in metres without final-distance normalization.'))


def new_feature_information(table,output=ROOT/'docs'):
    from .temporal_features_v072 import RECENT,EVENTS
    rows=[]
    for checkpoint,group in table.groupby('checkpoint_s'):
        for name in RECENT+EVENTS:
            y=group[name]
            rows.append(dict(checkpoint_s=checkpoint,feature=name,unique_laps=group.lap_uid.nunique(),
                mean=float(y.mean()),std=float(y.std()),min=float(y.min()),max=float(y.max()),q95=float(y.quantile(.95)),
                zero_fraction=float(y.eq(0).mean()),missing_fraction=float(y.isna().mean()),
                spearman_r=float(y.corr(group.target_s,method='spearman')) if y.nunique()>1 else np.nan))
    table_write(Path(output)/'FEATURE_NEW_INFORMATION_V072.csv',pd.DataFrame(rows))


def audit(corpus,bundle,output=ROOT/'docs'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    split=pd.read_csv(ROOT/'docs/BARCELONA_SPLIT_V071.csv')
    rows,(q25,q75)=population(corpus,split)
    old=json.loads((ROOT/'docs/ML_RESULTS_V071.json').read_text(encoding='utf-8'))
    if not np.allclose([q25,q75],old['training_target_quartiles'],rtol=0,atol=1e-10):
        raise ValueError('Frozen training quantiles differ')
    summaries=[];counts=[]
    for partition,group in rows.groupby('partition'):
        y=group.target_s
        summaries.append(dict(partition=partition,label='historical test (already observed)' if partition=='test' else partition,
            laps=len(group),recording_blocks=group.physical_session_id.nunique(),participant_codes=group.driver_id.nunique(),
            metadata_uncertain_laps=int(group.metadata_uncertainty.fillna('').ne('').sum()),
            mean_s=float(y.mean()),median_s=float(y.median()),std_s=float(y.std()),min_s=float(y.min()),max_s=float(y.max()),
            **{f'q{int(q*100)}_s':float(y.quantile(q)) for q in [.1,.25,.5,.75,.9]}))
        for band in ('fast','middle','slow'):
            selected=group.loc[group.pace_band==band]
            counts.append(dict(partition=partition,pace_band=band,laps=len(selected),proportion=len(selected)/len(group),
                               recording_blocks=selected.physical_session_id.nunique()))
    table_write(output/'PACE_LAPS_V072.csv',rows)
    table_write(output/'PACE_DISTRIBUTIONS_V072.csv',pd.DataFrame(summaries))
    table_write(output/'PACE_COUNTS_V072.csv',pd.DataFrame(counts))
    blocks=rows.groupby(['partition','physical_session_id'],as_index=False).agg(
        laps=('lap_uid','size'),participant_code=('driver_id','first'),mean_s=('target_s','mean'),
        median_s=('target_s','median'),min_s=('target_s','min'),max_s=('target_s','max'))
    table_write(output/'PACE_BLOCKS_V072.csv',blocks)
    reference=bundle.predictions.query("model=='SVR'").copy()
    reference['pace_band']=pace_band(reference.target_s,q25,q75)
    reference['partition_label']=reference.partition.replace({'test':'historical test (already observed)'})
    reference['distance_from_training_median_s']=reference.prediction_s-old['training_target_median_s']
    table_write(output/'REFERENCE_FROZEN_PREDICTIONS_V072.csv',reference)
    band_error=reference.assign(ae=(reference.prediction_s-reference.target_s).abs()).groupby(['partition','pace_band']).ae.mean()
    validation_error=float((reference.query("partition=='validation'").prediction_s-reference.query("partition=='validation'").target_s).abs().mean())
    historical_error=float((reference.query("partition=='test'").prediction_s-reference.query("partition=='test'").target_s).abs().mean())
    test_mix=rows.query("partition=='test'").pace_band.value_counts(normalize=True)
    standardized=sum(float(test_mix[band])*float(band_error.loc[('validation',band)]) for band in test_mix.index)
    dump(output/'PACE_COMPOSITION_V072.json',dict(validation_mae_s=validation_error,historical_test_mae_s=historical_error,
        validation_band_errors_at_historical_test_mix_s=standardized,composition_difference_s=standardized-validation_error,
        remaining_within_band_difference_s=historical_error-standardized,
        interpretation='Descriptive frozen-score standardization only; assumes unchanged conditional band errors, '
        'does not establish a causal decomposition and is not training weighting or model selection.'))
    calibration_rows=[dict(partition=p,checkpoint_s=c,**calibration(g))
                      for (p,c),g in reference.groupby(['partition','checkpoint_s'])]
    table_write(output/'REFERENCE_CALIBRATION_V072.csv',pd.DataFrame(calibration_rows))
    # Restrict every feature-information diagnostic to development before features
    # are calculated. Historical test sources/labels cannot reach these helpers.
    dev_ids=set(rows.query("partition!='test'").lap_uid)
    from .dataset import Corpus
    development=Corpus(corpus.name+' / development only',[l for l in corpus.laps if l.lap_uid in dev_ids],
                       corpus.targets.loc[corpus.targets.lap_uid.isin(dev_ids)].copy(),[])
    features,rejected=snapshots(development)
    if len(rejected):raise ValueError('Unexpected development checkpoint rejection')
    corr=features.loc[:,FEATURES].corr(method='spearman')
    table_write(output/'FEATURE_REDUNDANCY_V072.csv',corr.rename_axis('feature').reset_index())
    table_write(output/'FEATURE_PEARSON_V072.csv',features.loc[:,FEATURES].corr().rename_axis('feature').reset_index())
    information=[]
    for checkpoint,group in features.groupby('checkpoint_s'):
        x=group.loc[:,FEATURES].copy().fillna(group.loc[:,FEATURES].median()).fillna(0)
        mi=mutual_info_regression(x,group.target_s,random_state=42)
        for i,name in enumerate(FEATURES):
            information.append(dict(checkpoint_s=checkpoint,feature=name,unique_laps=len(group),
                pearson_r=float(group[name].corr(group.target_s)) if group[name].nunique()>1 else np.nan,
                spearman_r=float(group[name].corr(group.target_s,method='spearman')) if group[name].nunique()>1 else np.nan,
                mutual_information=float(mi[i]) if group[name].nunique()>1 else 0.))
    table_write(output/'FEATURE_INFORMATION_V072.csv',pd.DataFrame(information))
    # Neighbors with similar observed aggregates and different final targets.
    # These are explanatory development examples, not exclusions or model tuning.
    original_train=set(rows.query("partition=='train'").lap_uid)
    selected_features=[f for f in FEATURES if f not in ('checkpoint_s','observed_elapsed_s')]
    fitting=features.loc[features.lap_uid.isin(original_train),selected_features]
    medians=fitting.median().fillna(0)
    scaler=StandardScaler().fit(fitting.fillna(medians))
    pairs=[]
    for checkpoint,group in features.groupby('checkpoint_s'):
        group=group.reset_index(drop=True)
        x=scaler.transform(group[selected_features].fillna(medians))
        for i in range(len(group)):
            candidates=[j for j in range(i+1,len(group)) if group.iloc[i].physical_session_id!=group.iloc[j].physical_session_id
                        and abs(group.iloc[i].target_s-group.iloc[j].target_s)>=20
                        and abs(group.iloc[i].speed_mean_kmh-group.iloc[j].speed_mean_kmh)<=2
                        and abs(group.iloc[i].throttle_mean_pct-group.iloc[j].throttle_mean_pct)<=3]
            for j in candidates:
                left,right=group.iloc[i],group.iloc[j]
                pairs.append(dict(checkpoint_s=checkpoint,left_lap_uid=left.lap_uid,right_lap_uid=right.lap_uid,
                    scaled_feature_distance=float(np.linalg.norm(x[i]-x[j])),
                    left_target_s=left.target_s,right_target_s=right.target_s,
                    left_mean_speed_kmh=left.speed_mean_kmh,right_mean_speed_kmh=right.speed_mean_kmh,
                    left_throttle_mean_pct=left.throttle_mean_pct,right_throttle_mean_pct=right.throttle_mean_pct,
                    left_braking_fraction=left.braking_fraction,right_braking_fraction=right.braking_fraction,
                    left_recent_speed_kmh=left.speed_recent_mean_kmh,right_recent_speed_kmh=right.speed_recent_mean_kmh))
    pairs=pd.DataFrame(pairs).sort_values('scaled_feature_distance').head(12) if pairs else pd.DataFrame()
    table_write(output/'FEATURE_SIMILAR_LAPS_V072.csv',pairs)
    # A small causal sensitivity check on development sources; original reference
    # model only, no refit and no historical-test inference.
    from copy import deepcopy
    from .features import prefix_features
    by_uid={l.lap_uid:l for l in development.laps}
    ordered=rows.query("partition!='test'").sort_values(['target_s','lap_uid'])
    example_ids=[ordered.iloc[int(q*(len(ordered)-1))].lap_uid for q in [.1,.5,.9]]
    sensitivity=[]
    for uid in example_ids:
        source=by_uid[uid]
        for checkpoint in (10.,60.):
            for delta in (-10.,0.,10.):
                altered=deepcopy(source)
                observed=altered.frame.lap_elapsed_s<=checkpoint
                altered.frame.loc[observed,'speed_kmh']=(altered.frame.loc[observed,'speed_kmh']+delta).clip(0,500)
                values,_=prefix_features(altered,checkpoint)
                prediction=float(bundle.models['SVR'].predict(pd.DataFrame([values],columns=FEATURES))[0])
                sensitivity.append(dict(lap_uid=uid,checkpoint_s=checkpoint,speed_perturbation_kmh=delta,prediction_s=prediction))
    table_write(output/'REFERENCE_SENSITIVITY_V072.csv',pd.DataFrame(sensitivity))
    result=dict(corpus_id=corpus.identity,lap_counts=rows.groupby('partition').lap_uid.nunique().to_dict(),
        common_pace_quartiles_s=[q25,q75],reference_formulation='Direct final lap-time seconds, no median subtraction/addition or baseline feature',
        input_boundary='Only the original 13 causal feature columns reach model.fit/predict; labels join after feature construction',
        diagnostic_development_laps=len(development.laps),historical_test_role='Frozen descriptive rows only; excluded before feature diagnostics',
        experimental_models_fitted=0,source_progress_decision='Car Pos Norm exists; author paper documents normalized spline position. '
        'The exact ACTI export mapping/resampling semantics are not independently established. Omit raw normalized-progress F4; '
        'a causal integrated ground-speed distance proxy may be evaluated without a track-length normalization.',
        primary_source='https://proceedings.neurips.cc/paper_files/paper/2024/file/b91ea2ba1b6521940e204b7b81d5ef47-Paper-Datasets_and_Benchmarks_Track.pdf',
        limitations='Recording blocks and participant codes do not certify independent physical sessions; correlated checkpoints are not independent laps.')
    dump(output/'DIAGNOSIS_PHASE_A_V072.json',result)
    return development,rows,result
