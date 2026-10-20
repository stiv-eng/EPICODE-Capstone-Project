"""Independent partitions only; always retain individual errors and coverage."""
import numpy as np
import pandas as pd


def metrics(frame, prediction='prediction_s'):
    valid = np.isfinite(frame[prediction]) & np.isfinite(frame.target_s)
    subset = frame.loc[valid]
    error = subset[prediction]-subset.target_s
    return {'snapshots':len(subset),'laps':subset.lap_uid.nunique(),
            'mae_s':float(error.abs().mean()) if len(error) else np.nan,
            'rmse_s':float(np.sqrt((error**2).mean())) if len(error) else np.nan,
            'bias_s':float(error.mean()) if len(error) else np.nan}


def summarize(predictions):
    if predictions.empty:
        return {}
    overall = pd.DataFrame([{'model':m,'partition':p,**metrics(g)}
        for (m,p),g in predictions.groupby(['model','partition'])])
    by_checkpoint = pd.DataFrame([{'model':m,'partition':p,'checkpoint_s':c,**metrics(g)}
        for (m,p,c),g in predictions.groupby(['model','partition','checkpoint_s'])])
    by_session = pd.DataFrame([{'model':m,'partition':p,'physical_session_id':s,**metrics(g)}
        for (m,p,s),g in predictions.groupby(['model','partition','physical_session_id'])])
    by_lap = predictions.assign(error_s=predictions.prediction_s-predictions.target_s)
    by_lap = by_lap.groupby(['model','partition','physical_session_id','lap_uid'],as_index=False).agg(
        checkpoints=('checkpoint_s','count'),mean_prediction_s=('prediction_s','mean'),
        target_s=('target_s','first'),mae_across_checkpoints_s=('error_s',lambda x:x.abs().mean()),
        rmse_across_checkpoints_s=('error_s',lambda x:np.sqrt((x**2).mean())),
        bias_across_checkpoints_s=('error_s','mean'))
    baseline_rows=[]
    for (model,partition),group in predictions.groupby(['model','partition']):
        for baseline in ('previous_lap','historical_median'):
            matched = group.loc[group[baseline].notna()]
            baseline_mae = metrics(matched,baseline)['mae_s']
            model_mae = metrics(matched)['mae_s']
            baseline_rows.append({'model':model,'partition':partition,'baseline':baseline,
                'matched_snapshots':len(matched),'matched_laps':matched.lap_uid.nunique(),
                'baseline_mae_s':baseline_mae,'model_mae_s':model_mae,
                'improvement_s':baseline_mae-model_mae})
    return {'overall':overall,'by_checkpoint':by_checkpoint,'by_session':by_session,
            'by_lap':by_lap,'baselines':pd.DataFrame(baseline_rows),'individual':predictions}
