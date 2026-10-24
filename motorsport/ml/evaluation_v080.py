"""Lap-balanced dense-prefix metrics; labels enter only this evaluation layer."""
import numpy as np
import pandas as pd


def lap_weights(rows):
    weights = 1./rows.groupby('lap_uid').lap_uid.transform('size').to_numpy(float)
    return weights/weights.mean()


def quantile(x, w, q):
    order = np.argsort(x)
    x, w = np.asarray(x)[order], np.asarray(w)[order]
    return float(np.interp(q, (np.cumsum(w)-w/2)/w.sum(), x))


def metrics(rows):
    w = lap_weights(rows)
    y = rows.target_s.to_numpy(float)
    p = rows.prediction_s.to_numpy(float)
    e = p-y
    ae = np.abs(e)
    avg = lambda a: float(np.average(a, weights=w))
    ym, pm = avg(y), avg(p)
    ysd, psd = np.sqrt(avg((y-ym)**2)), np.sqrt(avg((p-pm)**2))
    lap = rows.assign(ae=ae).groupby(['physical_session_id', 'lap_uid']).ae.mean()
    return dict(laps=rows.lap_uid.nunique(), snapshots=len(rows), blocks=rows.physical_session_id.nunique(),
        mae_s=avg(ae), rmse_s=np.sqrt(avg(e*e)), bias_s=avg(e),
        median_absolute_error_s=quantile(ae, w, .5), p90_absolute_error_s=quantile(ae, w, .9),
        max_absolute_error_s=float(ae.max()), recording_macro_mae_s=float(lap.groupby(level=0).mean().mean()),
        prediction_to_target_std=float(psd/ysd) if ysd > 1e-9 else None,
        predicted_on_actual_slope=avg((y-ym)*(p-pm))/(ysd*ysd) if ysd > 1e-9 else None,
        prediction_mean_s=pm, target_mean_s=ym,
        negative_raw_remaining=int((rows.raw_remaining_s < 0).sum()),
        projected_fraction=avg(((rows.raw_remaining_s < 0) &
            rows.model.isin(['SVR-REMAINING', 'RIDGE-ORDERED', 'GRU'])).astype(float)),
        projection_mae_change_s=avg(ae-np.abs(rows.raw_final_s.to_numpy(float)-y)),
        final_before_observed_fraction=avg((p < rows.observed_elapsed_s.to_numpy(float)).astype(float)))


def summarize(predictions):
    overall, details, consistency = [], [], []
    for model, rows in predictions.groupby('model'):
        subsets = dict(all=rows, shared_60s=rows[rows.checkpoint_s <= 60],
            sparse=rows[rows.checkpoint_s.isin([10, 20, 30, 45, 60])],
            last_scheduled=rows.sort_values('checkpoint_s').groupby('lap_uid').tail(1),
            retrospective_final_10s=rows[(rows.target_s-rows.observed_elapsed_s) <= 10])
        for subset, table in subsets.items():
            if len(table):
                overall.append(dict(model=model, subset=subset, **metrics(table)))
        for dimension in ('checkpoint_s', 'pace_band', 'stage', 'fold', 'lap_uid', 'physical_session_id'):
            for value, table in rows.groupby(dimension):
                details.append(dict(model=model, dimension=dimension, value=value, **metrics(table)))
        for uid, table in rows.groupby('lap_uid'):
            table = table.sort_values('checkpoint_s')
            error = np.abs(table.prediction_s.to_numpy()-table.target_s.to_numpy())
            jumps = np.abs(np.diff(table.prediction_s.to_numpy()))
            consistency.append(dict(model=model, lap_uid=uid, pairs=len(jumps),
                fraction_error_improved=float((np.diff(error) < 0).mean()) if len(jumps) else None,
                mean_prediction_jump_s=float(jumps.mean()) if len(jumps) else None,
                max_prediction_jump_s=float(jumps.max()) if len(jumps) else None,
                first_absolute_error_s=float(error[0]), last_absolute_error_s=float(error[-1])))
    return pd.DataFrame(overall), pd.DataFrame(details), pd.DataFrame(consistency)
