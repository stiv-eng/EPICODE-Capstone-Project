"""Source-aware dynamics and four-corner channel discovery."""
import numpy as np
import pandas as pd

from .timebase import numeric
CORNERS = ('fl', 'fr', 'rl', 'rr')
TYRE_FAMILIES = {
    'Core temperature': 'tyre_core', 'Inner temperature': 'temp_i',
    'Middle temperature': 'temp_m', 'Outer temperature': 'temp_o',
    'Pressure': 'psi', 'Wear (source reported)': 'wear',
    'Wheel load': 'load', 'Wheel speed': 'wheel_speed',
}


def corner_channels(frame, prefix):
    return {corner.upper(): f'{prefix}_{corner}' for corner in CORNERS if f'{prefix}_{corner}' in frame}


def signal_unit(session, channel):
    explicit = session.metadata.get('channel_units', {})
    if channel in explicit:
        return explicit[channel]
    from motorsport.processing.schema import CANONICAL_UNITS
    return CANONICAL_UNITS.get(channel, 'source unit')


def usable_channels(frame, candidates=None, include_bool=False):
    """Actual finite real measurements; constants are legitimate, text is not.

    Availability is evaluated on the selected frame, so a channel may disappear
    when all its measurements lie outside the selected laps/window. No data is
    removed or imputed by this UI eligibility check.
    """
    candidates=list(frame) if candidates is None else candidates
    return [c for c in candidates if c in frame and not c.startswith('_ui_')
            and pd.api.types.is_numeric_dtype(frame[c])
            and not pd.api.types.is_complex_dtype(frame[c])
            and (include_bool or not pd.api.types.is_bool_dtype(frame[c]))
            and np.isfinite(numeric(frame,c)).any()]


def available_corners(frame, prefix):
    return {corner:c for corner,c in corner_channels(frame,prefix).items() if c in usable_channels(frame,[c])}


def paired_channels(frame, x, y, minimum=2):
    return (len(usable_channels(frame,[x,y]))==2 and
            int(np.isfinite(np.c_[numeric(frame,x),numeric(frame,y)]).all(axis=1).sum())>=minimum)
