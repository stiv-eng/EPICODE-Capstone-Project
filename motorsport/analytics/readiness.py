"""Evidence-based dataset capabilities and non-leaking lap-level candidate features."""
import numpy as np
import pandas as pd

from .timebase import numeric, time_support, weighted_signal
from .comparison import lap_trace,cumulative_lap_delta


def assess_capabilities(session):
    frame=session.data
    support=time_support(frame)
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    good=xy[np.isfinite(xy).all(axis=1)]
    position=len(good)>=3 and bool(np.any(np.ptp(good,axis=0)>0))
    laps=session.laps.laps
    validated=session.laps.available and len(laps)>0 and 'lap_id' in frame
    targets=bool(validated and np.isfinite(laps.duration_s).all() and (laps.duration_s>0).all())
    timing= support['observed_s']>0 and support['backward_steps']==0
    progress=False
    if validated:
        try:
            for lap_id in laps.lap_id:
                lap_trace(session,lap_id)
            progress=True
        except ValueError:
            pass
    limits={'speed_kmh':(0,500),'throttle_pct':(0,100),'brake_pct':(0,100),'rpm':(0,25000)}
    signal_ready=all(c in frame and np.mean(np.isfinite(numeric(frame,c)) &
        (numeric(frame,c)>=lo) & (numeric(frame,c)<=hi))>=.99 for c,(lo,hi) in limits.items())
    delta_ready=False
    if progress and session.metadata.get('distance_reference_id'):
        try:
            ids=laps.lap_id.tolist()
            cumulative_lap_delta(session,session,ids[0],ids[min(1,len(ids)-1)])
            delta_ready=True
        except ValueError:
            pass
    # A conservative release gate, not a statistical sample-size guarantee.
    enough=targets and len(laps)>=30 and session.metadata.get('session_count',1)>=3
    supervised=bool(enough and signal_ready)
    flags={
        'session_analysis':(bool(len(frame) and any(np.isfinite(numeric(frame,c)).any() for c in frame.select_dtypes('number'))), 'At least one finite numeric source signal.'),
        'time_window_comparison':(timing,'Positive observed-time support and no backward clock steps required.'),
        'track_position_analysis':(position,'Finite varying source coordinates; provenance/accuracy remain source-specific.'),
        'validated_lap_analysis':(bool(validated),session.laps.reason),
        'lap_progress_comparison':(progress,'Complete laps with finite monotonic driven distance; normalized fraction is approximate spatial alignment.'),
        'cumulative_lap_delta':(delta_ready, 'Requires an explicitly verified common track-distance reference, strict distance/time ordering and gap-free coverage; driven distance alone is insufficient.'),
        'full_lap_targets':(targets,'Targets require independently validated complete timing boundaries.'),
        'supervised_ml_eligible':(supervised,'Release gate: ≥30 validated target laps, ≥3 independent sessions, ≥99% finite core signals. This does not guarantee generalization.'),
        'progressive_dl_eligible':(bool(supervised and progress),'Requires the supervised gate plus validated progress; split complete sessions/laps and use causal prefixes only.'),
    }
    return {key:{'available':bool(value),'reason':reason} for key,(value,reason) in flags.items()}


def lap_features(session):
    rows=[]
    capabilities=assess_capabilities(session)
    if not session.laps.available:
        return pd.DataFrame()
    for lap in session.laps.laps.itertuples(index=False):
        frame=session.data.loc[session.data.lap_id.eq(lap.lap_id).fillna(False)]
        row={'session_id':session.metadata['session_id'],'lap_id':lap.lap_id,
             'lap_uid':f"{session.metadata['session_id']}:{lap.lap_id}",
             'target_lap_time_s':lap.duration_s,'target_verified':True,
             'track_id':session.metadata.get('track_id'), 'car_id':session.metadata.get('car_id'),
             'supervised_eligible':capabilities['supervised_ml_eligible']['available'],
             'progressive_dl_eligible':capabilities['progressive_dl_eligible']['available'],
             'feature_scope':'full lap retrospective; not causal progressive features'}
        for channel in ['speed_kmh','throttle_pct','brake_pct','rpm']:
            stats=weighted_signal(frame.assign(elapsed_s=frame.lap_elapsed_s),channel)
            row[channel+'_time_mean']=stats['time_mean']
            row[channel+'_max']=stats['max']
        rows.append(row)
    return pd.DataFrame(rows)
