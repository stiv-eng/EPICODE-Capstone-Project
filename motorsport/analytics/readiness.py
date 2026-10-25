"""Evidence-based capabilities for measured telemetry analysis."""
import numpy as np

from .timebase import numeric, time_support
from .comparison import lap_trace,cumulative_lap_delta


def assess_capabilities(session):
    frame=session.data
    support=time_support(frame)
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    good=xy[np.isfinite(xy).all(axis=1)]
    position=len(good)>=3 and bool(np.any(np.ptp(good,axis=0)>0))
    laps=session.laps.laps
    validated=session.laps.available and len(laps)>0 and 'lap_id' in frame
    verified_timing=bool(validated and np.isfinite(laps.duration_s).all() and (laps.duration_s>0).all())
    timing= support['observed_s']>0 and support['backward_steps']==0
    progress=False
    if validated:
        try:
            for lap_id in laps.lap_id:
                lap_trace(session,lap_id)
            progress=True
        except ValueError:
            pass
    delta_ready=False
    if progress and session.metadata.get('distance_reference_id'):
        try:
            ids=laps.lap_id.tolist()
            cumulative_lap_delta(session,session,ids[0],ids[min(1,len(ids)-1)])
            delta_ready=True
        except ValueError:
            pass
    flags={
        'session_analysis':(bool(len(frame) and any(np.isfinite(numeric(frame,c)).any() for c in frame.select_dtypes('number'))), 'At least one finite numeric source signal.'),
        'time_window_comparison':(timing,'Positive observed-time support and no backward clock steps required.'),
        'track_position_analysis':(position,'Finite varying source coordinates; provenance/accuracy remain source-specific.'),
        'validated_lap_analysis':(bool(validated),session.laps.reason),
        'lap_progress_comparison':(progress,'Complete laps with finite monotonic driven distance; normalized fraction is approximate spatial alignment.'),
        'cumulative_lap_delta':(delta_ready, 'Requires an explicitly verified common track-distance reference, strict distance/time ordering and gap-free coverage; driven distance alone is insufficient.'),
        'verified_lap_timing':(verified_timing,'Lap times require independently validated complete timing boundaries.'),
    }
    return {key:{'available':bool(value),'reason':reason} for key,(value,reason) in flags.items()}
