"""Observed-time support for irregular telemetry, without filling acquisition gaps."""
import numpy as np
import pandas as pd


def numeric(frame, column):
    if column not in frame:
        return np.full(len(frame), np.nan)
    return pd.to_numeric(frame[column], errors='coerce').to_numpy(dtype=float, na_value=np.nan)


def time_support(frame, gap_s=None):
    """Left-hold weights [t_i,t_i+1); repeats get zero weight, gaps are excluded.

    Any backward step disables duration statistics to avoid counting overlapping
    clock epochs. Missing timestamps break support locally. No terminal dwell is
    invented after the final observation.
    """
    t = numeric(frame, 'elapsed_s')
    dt = np.diff(t)
    positive = dt[np.isfinite(dt) & (dt > 0)]
    limit = float(gap_s) if gap_s is not None else max(1., 10*float(np.median(positive))) if len(positive) else 1.
    if not np.isfinite(limit) or limit <= 0:
        raise ValueError('Gap threshold must be finite and positive.')
    backward = bool(np.any(dt < 0))
    accepted = np.isfinite(dt) & (dt > 0) & (dt <= limit) & ~np.full(len(dt), backward)
    weights = np.r_[np.where(accepted, dt, 0.), 0.] if len(t) else np.array([])
    finite = t[np.isfinite(t)]
    span = float(t[-1]-t[0]) if len(t)>1 and np.isfinite(t[[0,-1]]).all() and not backward else None
    return {'weights': weights, 'gap_threshold_s': limit,
            'observed_s': float(weights.sum()), 'span_s': span,
            'excluded_gap_s': float(dt[np.isfinite(dt) & (dt > limit)].sum()),
            'duplicate_steps': int(np.sum(dt == 0)), 'backward_steps': int(np.sum(dt < 0)),
            'invalid_time_samples': int(len(t)-len(finite)),
            'large_gaps': int(np.sum(dt > limit))}


def weighted_signal(frame, column, support=None):
    support = support or time_support(frame)
    values = numeric(frame, column)
    valid = np.isfinite(values) & (support['weights'] > 0)
    duration = float(support['weights'][valid].sum())
    return {'covered_s': duration,
            'time_mean': float(np.average(values[valid], weights=support['weights'][valid])) if duration else None,
            'sample_mean': float(np.mean(values[np.isfinite(values)])) if np.isfinite(values).any() else None,
            'min': float(np.min(values[np.isfinite(values)])) if np.isfinite(values).any() else None,
            'max': float(np.max(values[np.isfinite(values)])) if np.isfinite(values).any() else None}


def fraction_time(frame, columns, predicate, support=None):
    support = support or time_support(frame)
    values = [numeric(frame, c) for c in columns]
    valid = np.logical_and.reduce([np.isfinite(v) for v in values]) & (support['weights'] > 0)
    covered = float(support['weights'][valid].sum())
    active = valid & predicate(*values)
    active_s = float(support['weights'][active].sum())
    return {'active_s': active_s, 'covered_s': covered,
            'time_pct': 100*active_s/covered if covered else None}
