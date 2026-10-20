"""Explicit session windows and validated-lap alignment; no arbitrary lap deltas."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .timebase import numeric, time_support, weighted_signal
from .channels import signal_unit


@dataclass(frozen=True)
class SessionWindow:
    session_id: str
    start_s: float
    end_s: float
    label: str = 'Session window'


def select_window(frame, start_s, end_s):
    if not np.isfinite([start_s,end_s]).all() or end_s <= start_s:
        raise ValueError('Select a finite, positive-duration session window.')
    t=numeric(frame,'elapsed_s')
    if (np.diff(t)<0).any():
        raise ValueError('Window timing requires a nondecreasing source clock.')
    positions=np.flatnonzero(np.isfinite(t) & (t>=start_s) & (t<=end_s))
    if not len(positions):
        raise ValueError('No observations inside this session window.')
    # Retain unknown timestamps between selected endpoints: deleting them would
    # bridge unsupported time and silently invent duration coverage.
    view=frame.iloc[positions[0]:positions[-1]+1].copy(deep=False)
    view['relative_s']=numeric(view,'elapsed_s')-start_s
    return view


def common_channels(left, right, channels):
    accepted, rejected=[],{}
    for channel in channels:
        if channel not in left.data or channel not in right.data:
            rejected[channel]='channel missing in one session'
            continue
        ua,ub=signal_unit(left,channel),signal_unit(right,channel)
        unknown=ua=='source unit' or ub=='source unit'
        reference=left.metadata.get('unit_reference_id')
        same_reference=bool(reference and reference==right.metadata.get('unit_reference_id'))
        if ua!=ub or (unknown and left.metadata['session_id']!=right.metadata['session_id'] and not same_reference):
            rejected[channel]='source units/calibration are not compatible'
        else:
            accepted.append(channel)
    return accepted,rejected


def compare_windows(left, right, left_range, right_range, channels):
    common,rejected=common_channels(left,right,channels)
    a=select_window(left.data,*left_range)
    b=select_window(right.data,*right_range)
    rows=[]
    for c in common:
        av,bv=weighted_signal(a,c),weighted_signal(b,c)
        rows.append({'channel':c,'unit':signal_unit(left,c),
                     'A_time_mean':av['time_mean'],'B_time_mean':bv['time_mean'],
                     'A_covered_s':av['covered_s'],'B_covered_s':bv['covered_s']})
    return a,b,pd.DataFrame(rows),rejected


def lap_trace(session, lap_id):
    if not session.laps.available or lap_id not in session.laps.laps.lap_id.to_list():
        raise ValueError('A validated complete lap is required.')
    lap=session.data.loc[session.data.lap_id.eq(lap_id).fillna(False)].copy(deep=False)
    d=numeric(lap,'distance_m')
    if len(d)<3 or not np.isfinite(d).all() or (np.diff(d)<0).any() or d[-1]<=d[0]:
        raise ValueError('This lap has no usable monotonic distance/progress reference.')
    lap['normalized_driven_progress']=(d-d[0])/(d[-1]-d[0])
    return lap


def cumulative_lap_delta(left,right,left_id,right_id,points=500):
    """B−A only for an explicitly verified shared track-distance reference.

    Normalized driven distance is insufficient: different racing lines do not
    establish identical spatial positions at the same normalized fraction.
    """
    reference=left.metadata.get('distance_reference_id')
    if not reference or reference!=right.metadata.get('distance_reference_id'):
        raise ValueError('No verified shared track-distance reference; cumulative lap delta is unavailable.')
    a,b=lap_trace(left,left_id),lap_trace(right,right_id)
    for lap in [a,b]:
        t=numeric(lap,'lap_elapsed_s');d=numeric(lap,'distance_m')
        if not np.isfinite(t).all() or (np.diff(t)<=0).any() or (np.diff(d)<=0).any() or time_support(lap.assign(elapsed_s=t))['large_gaps']:
            raise ValueError('Lap alignment needs finite, strictly increasing distance/time without gaps.')
    low=max(a.distance_m.iloc[0],b.distance_m.iloc[0]);high=min(a.distance_m.iloc[-1],b.distance_m.iloc[-1])
    if high<=low:
        raise ValueError('No shared distance coverage.')
    grid=np.linspace(low,high,points)
    return pd.DataFrame({'distance_m':grid,'delta_s':np.interp(grid,b.distance_m,b.lap_elapsed_s)-np.interp(grid,a.distance_m,a.lap_elapsed_s)})
