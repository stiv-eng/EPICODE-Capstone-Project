"""Pedal occupancy and observed braking events; no inferred brake pressure."""
import numpy as np
import pandas as pd

from .timebase import numeric, time_support, fraction_time, weighted_signal


EVENT_COLUMNS = ['start_sample', 'end_sample', 'start_s', 'end_s', 'duration_s',
                 'entry_speed_kmh', 'complete', 'peak_brake_pct']


def braking_events(frame, threshold_pct=5., min_duration_s=.1, support=None):
    if not 0 <= threshold_pct <= 100 or min_duration_s < 0:
        raise ValueError('Brake threshold must be 0–100% and minimum duration nonnegative.')
    support = support or time_support(frame)
    brake, speed, t = (numeric(frame, c) for c in ['brake_pct', 'speed_kmh', 'elapsed_s'])
    eligible = np.isfinite(brake) & (brake >= 0) & (brake <= 100) & (support['weights'] > 0)
    active = eligible & (brake > threshold_pct)
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]]) if len(frame) else []
    ends = np.flatnonzero(active & ~np.r_[active[1:], False]) if len(frame) else []
    events = []
    for start, last in zip(starts, ends):
        duration = float(support['weights'][start:last+1].sum())
        if duration < min_duration_s:
            continue
        end = last+1
        witnessed_onset = start > 0 and eligible[start-1] and brake[start-1] <= threshold_pct
        witnessed_release = end < len(frame) and np.isfinite(brake[end]) and brake[end] <= threshold_pct
        events.append({'start_sample': int(start), 'end_sample': int(end),
                       'start_s': t[start], 'end_s': t[end], 'duration_s': duration,
                       'entry_speed_kmh': speed[start] if witnessed_onset and np.isfinite(speed[start]) and speed[start] >= 0 else np.nan,
                       'complete': bool(witnessed_onset and witnessed_release),
                       'peak_brake_pct': float(np.max(brake[start:last+1]))})
    return pd.DataFrame(events, columns=EVENT_COLUMNS)


def driver_metrics(frame, throttle_threshold=90., brake_threshold=5., min_event_s=.1, overlap_throttle_threshold=5.):
    if not all(0 <= v <= 100 for v in [throttle_threshold, brake_threshold, overlap_throttle_threshold]):
        raise ValueError('Pedal thresholds must be 0–100%.')
    support = time_support(frame)
    in_range = lambda v: (v >= 0) & (v <= 100)
    # Out-of-range canonical pedals are invalid observations, not zero input.
    valid_frame = frame.copy(deep=False)
    for c in ['throttle_pct', 'brake_pct']:
        if c in frame:
            v = numeric(frame, c)
            valid_frame[c] = np.where(in_range(v), v, np.nan)
    usage = {
        'high_throttle': fraction_time(valid_frame, ['throttle_pct'], lambda v: v>throttle_threshold, support),
        'braking': fraction_time(valid_frame, ['brake_pct'], lambda v: v>brake_threshold, support),
        'overlap': fraction_time(valid_frame, ['throttle_pct', 'brake_pct'],
                                 lambda a,b: (a>overlap_throttle_threshold) & (b>brake_threshold), support),
    }
    events = braking_events(valid_frame, brake_threshold, min_event_s, support)
    complete = events.loc[events.complete.eq(True)]
    entry = complete.entry_speed_kmh.dropna()
    steering = numeric(frame, 'steering')
    dt = np.diff(numeric(frame, 'elapsed_s'))
    valid = (support['weights'][:-1]>0) & np.isfinite(steering[:-1]) & np.isfinite(steering[1:])
    activity = float(np.abs(np.diff(steering)[valid]).sum()/dt[valid].sum()) if valid.any() else None
    return {'usage': usage, 'observed_events': len(events), 'complete_events': len(complete),
            'entry_speed_mean_kmh': float(entry.mean()) if len(entry) else None,
            'entry_speed_max_kmh': float(entry.max()) if len(entry) else None,
            'steering': weighted_signal(frame, 'steering', support),
            'steering_activity_source_units_per_s': activity}, events
