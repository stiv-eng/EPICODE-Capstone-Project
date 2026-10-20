"""Reusable session summaries and observed-time categorical distributions."""
import numpy as np
import pandas as pd

from .timebase import numeric, time_support, weighted_signal


def overview_metrics(frame):
    support = time_support(frame)
    valid = np.ones(len(frame), dtype=bool)
    if 'elapsed_s' in frame:
        valid &= np.isfinite(numeric(frame, 'elapsed_s'))
    if 'speed_kmh' in frame:
        speed = numeric(frame, 'speed_kmh')
        valid &= np.isfinite(speed) & (speed >= 0) & (speed <= 500)
    return {'samples': len(frame), 'valid_time_speed_samples': int(valid.sum()),
            'time': {k:v for k,v in support.items() if k != 'weights'},
            'signals': {c: weighted_signal(frame, c, support) for c in
                        ['speed_kmh','throttle_pct','brake_pct','rpm','g_lat','g_lon'] if c in frame}}


def gear_distribution(frame):
    values, weights = numeric(frame, 'gear'), time_support(frame)['weights']
    valid = np.isfinite(values) & (values == np.floor(values)) & (values >= -1) & (values <= 12)
    out = pd.DataFrame({'gear': values[valid], 'samples': 1, 'observed_s': weights[valid]})
    out = out.groupby('gear', as_index=False).sum()
    total = out.observed_s.sum()
    out['time_pct'] = out.observed_s/total*100 if total else np.nan
    return out
