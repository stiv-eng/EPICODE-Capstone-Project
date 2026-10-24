"""Finite source-coordinate views, with explicit validity and no finish inference."""
import numpy as np
import pandas as pd

from .timebase import numeric, time_support
from .session_metrics import chart_sample


def position_view(frame,color_channel='speed_kmh',max_points=5000):
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    finite=np.isfinite(xy).all(axis=1)
    stats={'samples':len(frame),'finite_positions':int(finite.sum()),
           'invalid_positions':int((~finite).sum()),'varying':False}
    if finite.sum()<3 or not np.any(np.ptp(xy[finite],axis=0)>0):
        return frame.iloc[:0],stats
    stats['varying']=True
    available=frame.loc[finite]
    return chart_sample(available,['pos_x','pos_y',color_channel],max_points=max_points),stats


def color_channels(frame):
    """All finite real numeric channels, including preserved original signals."""
    return [c for c in frame.select_dtypes(include=['number','bool']).columns
            if not c.startswith('_ui_') and not pd.api.types.is_complex_dtype(frame[c])
            and np.isfinite(numeric(frame,c)).any()]


def position_segments(frame, color_channel=None, max_points=6000):
    """Validate adjacency before simplifying each connected run in source order.

    Break at missing positions/times, nonpositive time steps, temporal gaps
    (> max(1 s, 10 median positive dt)), changed/missing lap labels, removed
    source rows, and spatial jumps >20 times the median positive source step.
    The latter is scale invariant because source coordinate units may be unknown.
    This is a conservative visualization guard, never a geometry/lap validator.
    """
    xy=np.c_[numeric(frame,'pos_x'),numeric(frame,'pos_y')]
    n=len(frame)
    stats={'samples':n,'finite_positions':int(np.isfinite(xy).all(axis=1).sum()),
           'runs':0,'omitted_runs':0,'rendered_segments':0}
    columns=['start','end','x0','y0','x1','y1','value']
    finite_xy=xy[np.isfinite(xy).all(axis=1)]
    if n<2 or len(finite_xy)<3 or not np.any(np.ptp(finite_xy,axis=0)>0):
        return pd.DataFrame(columns=columns),stats
    t=numeric(frame,'elapsed_s');dt=np.diff(t)
    step=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    finite=np.isfinite(xy).all(axis=1)
    valid=finite[:-1]&finite[1:]&np.isfinite(dt)&(dt>0)&(dt<=time_support(frame)['gap_threshold_s'])
    if 'lap_id' in frame:
        laps=numeric(frame,'lap_id')
        valid &= np.isfinite(laps[:-1])&np.isfinite(laps[1:])&(laps[:-1]==laps[1:])
    # Data Explorer retains original indices, so filtering cannot join fragments.
    if pd.api.types.is_numeric_dtype(frame.index):
        valid &= np.diff(frame.index.to_numpy())==1
    positive=step[valid & (step>0)]
    spatial_limit=20*float(np.median(positive)) if len(positive) else np.inf
    valid &= step<=spatial_limit
    stats['spatial_jump_threshold_source_units']=spatial_limit
    stats['gap_threshold_s']=time_support(frame)['gap_threshold_s']
    edges=np.flatnonzero(valid)
    if not len(edges):
        return pd.DataFrame(columns=columns),stats
    runs=np.split(edges,np.flatnonzero(np.diff(edges)>1)+1)
    stats['runs']=len(runs)
    if len(runs)>max_points//2:
        keep=set(np.argsort([-len(r) for r in runs],kind='stable')[:max_points//2])
        stats['omitted_runs']=len(runs)-len(keep)
        runs=[r for i,r in enumerate(runs) if i in keep]
    # Reserve endpoints for every fragment, then distribute the bounded budget.
    extra=max(0,max_points-2*len(runs));total=sum(len(r)-1 for r in runs)
    starts,ends=[],[]
    for run in runs:
        count=min(len(run)+1,2+int(extra*(len(run)-1)/total) if total else 2)
        vertices=np.linspace(run[0],run[-1]+1,count,dtype=int)
        starts.extend(vertices[:-1]);ends.extend(vertices[1:])
    starts=np.asarray(starts,dtype=int);ends=np.asarray(ends,dtype=int)
    values=numeric(frame,color_channel) if color_channel else np.full(n,np.nan)
    stats['rendered_segments']=len(starts)
    return pd.DataFrame({'start':starts,'end':ends,'x0':xy[starts,0],'y0':xy[starts,1],
                         'x1':xy[ends,0],'y1':xy[ends,1],'value':values[starts]}),stats
