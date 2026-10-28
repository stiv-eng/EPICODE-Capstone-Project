"""Observed lap contracts and a separate raw-coordinate adapter for analysis."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from motorsport.ingestion.motec import read_ld


@dataclass
class LapData:
    lap_id: str
    duration_s: float
    frame: pd.DataFrame
    units: dict
    identity: dict
    coordinate_frame: str | None = None
    position_provenance: str = 'unverified'


def spatial_source(session, key, root):
    """Return X/Y and their declared contract without mutating existing views.

    ACTI horizontal mapping follows the author's loader: Y, -X. The raw LD
    channels already exist; no synthetic position or resampling is introduced.
    """
    meta = session.metadata
    if key.startswith(('barcelona:', 'acgym:')):
        barcelona = key.startswith('barcelona:')
        folder = 'acgym_barcelona_dallara' if barcelona else 'acgym_monza_dallara'
        relative = key.split(':', 1)[1]
        directory = (Path(root)/'data/raw'/folder).resolve()
        path = (directory/relative).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('Unsafe coordinate source path')
        _, channels = read_ld(path, {'Car Coord X', 'Car Coord Y', 'Car Coord Z'})
        if not {'Car Coord X', 'Car Coord Y'} <= set(channels):
            return None, None, 'Source has no horizontal Car Coord channels'
        for channel in channels.values():
            if channel.unit != 'm' or channel.hz != meta.get('export_hz') or len(channel.values) != len(session.data):
                return None, None, 'Coordinate units/export grid do not match telemetry'
        xy = np.c_[channels['Car Coord Y'].values, -channels['Car Coord X'].values]
        return xy, str(meta.get('track_id'))+':acti-world-Y-minusX-v1', 'source simulator Car Coord Y / -Car Coord X, metres'
    units = meta.get('channel_units', {})
    if {'pos_x', 'pos_y'} <= set(session.data) and meta.get('position_units') == 'm':
        frame_id = meta.get('coordinate_frame_id')
        if str(meta.get('session_id', '')).startswith('gt7:'):
            frame_id = str(meta.get('track_id'))+':gt7-world-XZ-v1'
        if frame_id and units.get('pos_x') == units.get('pos_y') == 'm':
            return session.data[['pos_x', 'pos_y']].to_numpy(float), frame_id, meta.get('position_provenance', 'declared metric world coordinates')
    return None, None, 'Metric world-coordinate units and a shared frame are not established for this source'


def from_session(session, lap_id, spatial=None):
    rows = session.laps.laps
    if not session.laps.available or lap_id not in set(rows.lap_id):
        raise ValueError('Select an independently validated complete lap')
    row = rows.set_index('lap_id').loc[lap_id]
    a, b = int(row.start_sample), int(row.end_sample)
    frame = session.data.iloc[a:b].copy().reset_index(drop=True)
    xy, frame_id, provenance = spatial if spatial is not None else (None, None, 'Coordinates unavailable')
    if xy is not None:
        frame['pos_x'], frame['pos_y'] = xy[a:b, 0], xy[a:b, 1]
    else:
        frame = frame.drop(columns=['pos_x', 'pos_y'], errors='ignore')
    units = {}
    for channel in ('speed_kmh', 'brake_pct', 'throttle_pct', 'steering', 'g_lat', 'g_lon', 'rpm', 'gear'):
        mapping = session.metadata.get('normalization', {}).get('mappings', {}).get(channel, {})
        units[channel] = session.metadata.get('channel_units', {}).get(channel, mapping.get('canonical_unit', 'unknown'))
    if xy is not None:
        units.update(pos_x='m', pos_y='m')
    identity = {key:session.metadata.get(key) for key in ('session_id', 'track_id', 'car_id', 'revision', 'source_sha256', 'filename', 'derived_source_channels')}
    identity['source_lap_id'] = str(lap_id)
    return LapData(str(lap_id), float(row.duration_s), frame, units, identity, frame_id, provenance)


def capabilities(lap):
    return {channel:dict(available=channel in lap.frame and bool(np.isfinite(pd.to_numeric(lap.frame[channel], errors='coerce')).any()),
                         unit=lap.units.get(channel, 'unknown')) for channel in
            ('pos_x', 'pos_y', 'speed_kmh', 'brake_pct', 'throttle_pct', 'steering', 'g_lat', 'g_lon', 'rpm', 'gear')}
