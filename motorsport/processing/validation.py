"""Measured quality diagnostics. Flags never imply automatic sample removal."""
import numpy as np
import pandas as pd


LIMITS = {'speed_kmh': (0, 500), 'throttle_pct': (0, 100),
          'brake_pct': (0, 100), 'rpm': (0, 25000), 'gear': (-1, 12)}


def time_quality(values):
    values = pd.to_numeric(values, errors='coerce').to_numpy(dtype=float, na_value=np.nan)
    valid = np.isfinite(values)
    dt = np.diff(values)
    positive = dt[np.isfinite(dt) & (dt > 0)]
    median = float(np.median(positive)) if len(positive) else None
    duration = float(values[-1] - values[0]) if len(values) > 1 and valid.all() and not (dt < 0).any() else None
    gap_limit = max(1.0, 10 * median) if median else 1.0
    return {
        'missing_or_nonfinite': int((~valid).sum()),
        'duplicate_values': int(pd.Series(values[valid]).duplicated().sum()),
        'backward_steps': int((dt < 0).sum()),
        'median_positive_step_s': median,
        'median_positive_rate_hz': 1 / median if median else None,
        'observed_rate_hz': (len(values)-1) / duration if duration and duration > 0 else None,
        'duration_s': duration, 'gap_threshold_s': gap_limit,
        'large_gaps': int((dt > gap_limit).sum()),
        'max_gap_s': float(positive.max()) if len(positive) else None,
    }


def quality_report(frame, time_column=None):
    channels = []
    for name in frame:
        s = frame[name]
        entry = {'channel': str(name), 'dtype': str(s.dtype), 'missing': int(s.isna().sum()),
                 'unique': int(s.nunique()), 'constant': bool(s.nunique() == 1),
                 'infinite': 0, 'outside_limits': 0, 'iqr_outliers': 0}
        if pd.api.types.is_numeric_dtype(s):
            values = s.to_numpy(dtype=float, na_value=np.nan)
            entry['infinite'] = int(np.isinf(values).sum())
            finite = values[np.isfinite(values)]
            if len(finite):
                q1, q3 = np.quantile(finite, [.25, .75])
                iqr = q3 - q1
                entry.update(min=float(finite.min()), max=float(finite.max()),
                             median=float(np.median(finite)))
                # IQR flags are exploratory, not proof of sensor corruption.
                if iqr > 0:
                    entry['iqr_outliers'] = int(((finite < q1-3*iqr) | (finite > q3+3*iqr)).sum())
                if name in LIMITS:
                    low, high = LIMITS[name]
                    entry['outside_limits'] = int(((finite < low) | (finite > high)).sum())
                    if name == 'gear':
                        entry['outside_limits'] += int(((finite >= low) & (finite <= high) & (finite != np.floor(finite))).sum())
        channels.append(entry)
    return {'rows': len(frame), 'columns': len(frame.columns),
            'duplicate_rows': int(frame.duplicated().sum()),
            'missing_cells': sum(c['missing'] for c in channels),
            'infinite_cells': sum(c['infinite'] for c in channels),
            'constant_channels': [c['channel'] for c in channels if c['constant']],
            'channels': channels,
            'time': time_quality(frame[time_column]) if time_column in frame else None}
