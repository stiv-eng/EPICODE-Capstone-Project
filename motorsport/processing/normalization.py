"""Normalize declared channels without sorting, filling or deleting source rows."""
import numpy as np
import pandas as pd

from .schema import CANONICAL, CANONICAL_UNITS


def normalize(frame, profile=CANONICAL):
    if not frame.columns.is_unique:
        raise ValueError('Duplicate column names are not supported.')
    out = frame.copy(deep=False)
    notes, mappings = [], {}
    for target in CANONICAL_UNITS:
        source = profile.columns.get(target, target)
        if source not in frame:
            if target in out and target in profile.columns:
                out = out.drop(columns=[target])
            continue
        unit = profile.units.get(target, CANONICAL_UNITS[target])
        values = frame[source]
        if target == 'elapsed_s' and unit == 'datetime':
            time = pd.to_datetime(values, errors='coerce', utc=True)
            numeric = (time - time.dropna().iloc[0]).dt.total_seconds() if time.notna().any() else pd.Series(np.nan, index=frame.index)
        elif target == 'elapsed_s' and pd.api.types.is_timedelta64_dtype(values):
            numeric = values.dt.total_seconds()
        else:
            numeric = pd.to_numeric(values, errors='coerce').astype(float)
            if target == 'elapsed_s':
                factors = {'s': 1., 'ms': .001, 'us': .000001, 'ns': .000000001}
                if unit not in factors:
                    raise ValueError(f'Unknown time unit: {unit}. Declare s, ms, us, ns or datetime.')
                numeric = numeric * factors[unit]
            elif target == 'speed_kmh':
                if unit == 'm/s':
                    numeric = numeric * 3.6
                elif unit != 'km/h':
                    raise ValueError(f'Unknown speed unit: {unit}')
            elif target in {'throttle_pct', 'brake_pct'}:
                if unit == 'fraction':
                    numeric = numeric * 100
                elif unit == 'byte255':
                    numeric = numeric / 2.55
                elif unit != '%':
                    raise ValueError(f'Unknown control unit: {unit}')
        numeric = numeric.replace([np.inf, -np.inf], np.nan)
        if target == 'elapsed_s' and numeric.notna().any():
            numeric = numeric - numeric.dropna().iloc[0]
        out[target] = numeric
        coerced = int((values.notna() & numeric.isna()).sum())
        if coerced:
            notes.append(f'{source} → {target}: {coerced} invalid/nonfinite values represented as missing; raw values retained.')
        mappings[target] = {'source': source, 'source_unit': unit,
                            'canonical_unit': CANONICAL_UNITS[target]}
    if 'elapsed_s' not in out:
        notes.append('No declared time channel: plots use sample index; timing metrics and laps are unavailable.')
    if 'steering' in mappings:
        notes.append('Steering is preserved in source units; degrees/radians are not inferred.')
    if {'pos_x', 'pos_y'}.issubset(out):
        notes.append('Position is a source coordinate trace, not a certified circuit map or finish line.')
    return out, {'profile': profile.name, 'mappings': mappings, 'notes': notes}
