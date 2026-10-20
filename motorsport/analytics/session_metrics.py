"""Compute on full data; downsample only the chart view."""
import numpy as np
import pandas as pd

from motorsport.processing.validation import time_quality


def session_metrics(frame):
    metrics = {'samples': len(frame)}
    if 'elapsed_s' in frame:
        metrics['duration_s'] = time_quality(frame.elapsed_s)['duration_s']
    for col in ['speed_kmh', 'throttle_pct', 'brake_pct', 'rpm']:
        if col in frame:
            values = pd.to_numeric(frame[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
            metrics[f'{col}_mean'] = float(values.mean()) if values.notna().any() else None
            metrics[f'{col}_max'] = float(values.max()) if values.notna().any() else None
    return metrics


def chart_sample(frame, channels, max_points=5000):
    """Union of per-bucket extrema preserves short braking/speed peaks.

    The point budget applies to the combined rows, not per signal. Row order
    and the first/last observations survive. Calculations never use this view.
    """
    if max_points < 4:
        raise ValueError('Chart point budget must be at least 4.')
    if len(frame) <= max_points:
        return frame
    channels = [c for c in channels if c in frame and pd.api.types.is_numeric_dtype(frame[c])]
    buckets = max(1, (max_points - 2) // max(2, 2 * len(channels)))
    selected = {0, len(frame)-1}
    for positions in np.array_split(np.arange(len(frame)), buckets):
        if not channels:
            selected.add(int(positions[0]))
        for c in channels:
            v = frame[c].iloc[positions].to_numpy(dtype=float, na_value=np.nan)
            finite = np.isfinite(v)
            if finite.any():
                good = positions[finite]
                selected.update([int(good[np.argmin(v[finite])]), int(good[np.argmax(v[finite])])])
    indices = np.array(sorted(selected))
    # Very large channel selections can exceed a single bucket's point budget.
    if len(indices) > max_points:
        indices = indices[np.linspace(0, len(indices)-1, max_points, dtype=int)]
    return frame.iloc[indices]
