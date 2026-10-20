"""Prefix features are evaluated in source lap time, never final distance/time."""
import numpy as np
import pandas as pd

from .dataset import CORE, core_coverage

CHECKPOINTS = (10.,20.,30.,45.,60.)
FEATURES = ('checkpoint_s','observed_elapsed_s','speed_current_kmh','speed_mean_kmh',
    'speed_recent_mean_kmh','speed_recent_std_kmh','throttle_mean_pct','brake_mean_pct',
    'throttle_high_fraction','braking_fraction','rpm_current','gear_current','steering_activity_deg_s')


def causal_prefix(source, checkpoint):
    if not np.isfinite(checkpoint) or checkpoint<=0:
        raise ValueError('Checkpoint must be positive and finite')
    # Only the selected prefix is validated/aggregated. No property of the tail
    # (length, final target, future gaps or final progress) affects this result.
    time = pd.to_numeric(source.frame.lap_elapsed_s,errors='coerce').to_numpy(float)
    boundary = np.flatnonzero(~np.isfinite(time) | (time>checkpoint))
    end = int(boundary[0]) if len(boundary) else len(time)
    frame = source.frame.iloc[:end].copy()
    if frame.empty:
        raise ValueError('No observations at this checkpoint')
    t = frame.lap_elapsed_s.to_numpy(float)
    if (np.diff(t)<0).any() or t[0]>.1 or checkpoint-t[-1]>.1:
        raise ValueError('Prefix lacks monotonic boundary coverage within 100 ms')
    dt = np.diff(t)
    if (dt>.2).any():
        raise ValueError('Prefix has a source-clock gap over 200 ms')
    coverage = min(core_coverage(frame).values())
    if coverage<.99:
        raise ValueError('Prefix key-signal coverage is below 99%')
    return frame,{'status':'accepted','min_core_coverage':coverage,'observed_elapsed_s':float(t[-1]),
                  'coverage_fraction':float((t[-1]-t[0])/checkpoint),'samples':len(frame)}


def prefix_features(source, checkpoint):
    frame, quality = causal_prefix(source,checkpoint)
    t = frame.lap_elapsed_s.to_numpy(float)
    weights = np.r_[np.diff(t),0.]
    def values(column):
        if column not in frame:
            return np.full(len(frame),np.nan)
        result = pd.to_numeric(frame[column],errors='coerce').to_numpy(float).copy()
        if column in CORE:
            lower,upper = CORE[column]
            result[(result<lower) | (result>upper)] = np.nan
        return result
    def mean(column):
        y = values(column)
        valid = np.isfinite(y)
        if column in CORE:
            valid &= (y>=CORE[column][0]) & (y<=CORE[column][1])
        return float(np.average(y[valid],weights=weights[valid])) if weights[valid].sum()>0 else np.nan
    def fraction(column, threshold):
        y = values(column); valid = np.isfinite(y) & (y>=0) & (y<=100)
        return float(np.average(y[valid]>=threshold,weights=weights[valid])) if weights[valid].sum()>0 else np.nan
    recent = t>=t[-1]-3.
    recent_speed = values('speed_kmh')[recent]
    rw = weights[recent]
    valid = np.isfinite(recent_speed) & (recent_speed>=0) & (recent_speed<=500)
    recent_mean = float(np.average(recent_speed[valid],weights=rw[valid])) if rw[valid].sum()>0 else np.nan
    recent_std = float(np.sqrt(np.average((recent_speed[valid]-recent_mean)**2,weights=rw[valid]))) if rw[valid].sum()>0 else np.nan
    steering = values('steering')[recent]
    rt = t[recent]
    positive = np.diff(rt)>0
    activity = np.nan
    if source.steering_unit=='deg' and len(rt)>1 and np.isfinite(steering).all() and positive.any():
        activity = float(np.abs(np.diff(steering)[positive]).sum()/np.diff(rt)[positive].sum())
    result = {'checkpoint_s':float(checkpoint),'observed_elapsed_s':float(t[-1]),
        'speed_current_kmh':float(values('speed_kmh')[-1]),'speed_mean_kmh':mean('speed_kmh'),
        'speed_recent_mean_kmh':recent_mean,'speed_recent_std_kmh':recent_std,
        'throttle_mean_pct':mean('throttle_pct'),'brake_mean_pct':mean('brake_pct'),
        'throttle_high_fraction':fraction('throttle_pct',90),'braking_fraction':fraction('brake_pct',5),
        'rpm_current':float(values('rpm')[-1]),'gear_current':float(values('gear')[-1]),
        'steering_activity_deg_s':activity}
    # Every returned predictive value has a fixed, reviewed numeric name.
    return result,quality


def snapshots(corpus, checkpoints=CHECKPOINTS):
    rows, rejected = [], []
    for lap in corpus.laps:
        for checkpoint in sorted(set(checkpoints)):
            try:
                features,quality = prefix_features(lap,checkpoint)
                rows.append({'lap_uid':lap.lap_uid,'physical_session_id':lap.physical_session_id,
                             **features,**{f'quality_{k}':v for k,v in quality.items()}})
            except ValueError as exc:
                rejected.append({'lap_uid':lap.lap_uid,'checkpoint_s':checkpoint,'reason':str(exc)})
    features = pd.DataFrame(rows)
    if features.empty:
        return features,pd.DataFrame(rejected)
    # The sole label join occurs after generation, outside feature computation.
    labels = corpus.targets.drop(columns='physical_session_id')
    return features.merge(labels,on='lap_uid',validate='many_to_one'),pd.DataFrame(rejected)


def retrospective_features(corpus):
    """Whole-lap summaries for exploration only; never accepted by training."""
    rows = []
    for lap in corpus.laps:
        t = lap.frame.lap_elapsed_s.to_numpy(float)
        w = np.r_[np.diff(t),0.]
        rows.append({'lap_uid':lap.lap_uid,'feature_contract':'retrospective whole-lap; unavailable during replay',
            'full_lap_mean_speed_kmh':float(np.average(lap.frame.speed_kmh,weights=w)),
            'full_lap_braking_fraction':float(np.average(lap.frame.brake_pct>=5,weights=w))})
    return pd.DataFrame(rows).merge(corpus.targets,on='lap_uid',validate='one_to_one') if rows else pd.DataFrame()
