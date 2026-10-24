"""Compact causal history descriptors isolated from immutable F0 features."""
import numpy as np
import pandas as pd

from .features import FEATURES, CHECKPOINTS, prefix_features, causal_prefix
from .dataset import CORE

VERSION='causal-prefix-v072-1'
RECENT=('speed_mean_5s_kmh','speed_std_5s_kmh','speed_delta_5s_kmh',
        'deceleration_mean_5s_mps2','deceleration_max_5s_mps2',
        'braking_fraction_5s','throttle_mean_5s_pct')
EVENTS=('braking_phases_count','low_speed_observed_s','severe_slow_observed_s',
        'recovery_from_low_kmh','distance_observed_m')
FEATURE_SETS={'F0':tuple(FEATURES),'F1':tuple(FEATURES)+RECENT,
              'F2':tuple(FEATURES)+EVENTS,'F3':tuple(FEATURES)+RECENT+EVENTS,
              'F0W':tuple(FEATURES)}
UNITS=dict(zip(RECENT+EVENTS,('km/h','km/h','km/h','m/s^2','m/s^2','fraction','%',
                            'count','s','s','km/h','m')))


def _values(frame,column):
    y=pd.to_numeric(frame[column],errors='coerce').to_numpy(float).copy()
    lo,hi=CORE[column]
    y[~np.isfinite(y)|(y<lo)|(y>hi)]=np.nan
    return y


def _average(values,weights):
    valid=np.isfinite(values)&np.isfinite(weights)&(weights>0)
    return float(np.average(values[valid],weights=weights[valid])) if valid.any() else np.nan


def _phase_count(active,intervals,minimum=.2):
    count=0;duration=0.
    for on,dt in zip(active,intervals):
        if on:duration+=dt
        else:
            count+=int(duration+1e-9>=minimum);duration=0.
    # An ongoing phase counts only once its observed duration qualifies.
    return float(count+int(duration+1e-9>=minimum))


def feature_row(source,checkpoint,variant='F3'):
    if variant not in FEATURE_SETS:raise ValueError('Unknown v072 feature set')
    original,quality=prefix_features(source,checkpoint)
    if variant in ('F0','F0W'):return original,quality
    frame,_=causal_prefix(source,checkpoint)
    t=frame.lap_elapsed_s.to_numpy(float)
    dt=np.diff(t)
    speed=_values(frame,'speed_kmh');brake=_values(frame,'brake_pct');throttle=_values(frame,'throttle_pct')
    lower=max(t[0],float(checkpoint)-5.)
    recent=np.maximum(0.,t[1:]-np.maximum(t[:-1],lower))
    recent=np.where(dt>0,recent,0.)
    values=dict(original)
    if variant in ('F1','F3'):
        mean=_average(speed[:-1],recent)
        variance=_average((speed[:-1]-mean)**2,recent)
        first=max(0,int(np.searchsorted(t,lower,side='right')-1))
        pair=np.isfinite(speed[:-1])&np.isfinite(speed[1:])&(dt>0)
        deceleration=np.full(len(dt),np.nan)
        deceleration[pair]=np.maximum(0.,(speed[:-1][pair]-speed[1:][pair])/(3.6*dt[pair]))
        valid=pair&(recent>0)
        values.update(speed_mean_5s_kmh=mean,speed_std_5s_kmh=float(np.sqrt(variance)),
            speed_delta_5s_kmh=float(speed[-1]-speed[first]),
            deceleration_mean_5s_mps2=_average(deceleration,recent),
            deceleration_max_5s_mps2=float(deceleration[valid].max()) if valid.any() else np.nan,
            braking_fraction_5s=_average(np.where(np.isfinite(brake[:-1]),(brake[:-1]>=5).astype(float),np.nan),recent),
            throttle_mean_5s_pct=_average(throttle[:-1],recent))
    if variant in ('F2','F3'):
        positive=np.where(dt>0,dt,0.)
        valid=np.isfinite(speed[:-1])
        low=np.isfinite(speed)&(speed<80.)
        indices=np.flatnonzero(low)
        recovery=0.
        if len(indices) and indices[-1]<len(speed)-1:
            recovery=float(max(0.,speed[-1]-speed[indices[-1]])) if np.isfinite(speed[-1]) else np.nan
        values.update(braking_phases_count=_phase_count(np.isfinite(brake[:-1])&(brake[:-1]>=5.),positive),
            low_speed_observed_s=float(positive[valid&(speed[:-1]<80.)].sum()),
            severe_slow_observed_s=float(positive[valid&(speed[:-1]<40.)].sum()),
            recovery_from_low_kmh=recovery,
            distance_observed_m=float(np.sum(speed[:-1][valid]*positive[valid])/3.6))
    return {name:values[name] for name in FEATURE_SETS[variant]},quality


def snapshot_table(development):
    """One target-free builder for training and experimental replay, then label join."""
    rows=[]
    for source in development.laps:
        for checkpoint in CHECKPOINTS:
            features,_=feature_row(source,checkpoint,'F3')
            rows.append(dict(lap_uid=source.lap_uid,physical_session_id=source.physical_session_id,**features))
    observations=pd.DataFrame(rows)
    labels=development.targets.drop(columns='physical_session_id')
    return observations.merge(labels,on='lap_uid',validate='many_to_one')
