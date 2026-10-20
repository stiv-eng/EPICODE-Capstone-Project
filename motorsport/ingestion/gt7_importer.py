"""Pinned GT7 Parquet bundle adapter. Source lap counters are checked, not trusted.

GT7's lap counter leads its timer reset by one packet here. The stale boundary
packet is withheld from canonical lap labels. Host time is retained for session
inspection; only the independent lap timer supplies lap targets/alignment time.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from motorsport.pipeline import build_session
from motorsport.processing.schema import SourceProfile
from motorsport.processing.laps import LapResult

PROFILE = SourceProfile('GT7 Trial Mountain / packet units',
    {'elapsed_s':'wall_time', 'throttle_pct':'throttle', 'brake_pct':'brake',
     'steering':'steer_angle_l', 'pos_y':'pos_z', 'g_lat':'sway', 'g_lon':'surge'},
    {'elapsed_s':'s', 'throttle_pct':'byte255', 'brake_pct':'byte255'})


def validate_gt7_laps(raw):
    checked, rejected = [], []
    timer = raw.current_lap_ms.to_numpy(dtype=float)/1000
    lap_elapsed = np.full(len(raw), np.nan)
    for lap_id, group in raw.groupby('lap', sort=False):
        index = group.index.to_numpy()
        next_group = raw.loc[raw.lap.eq(lap_id+1)]
        reasons = []
        if lap_id <= 0:
            reasons.append('out-lap')
        if next_group.empty:
            reasons.append('no subsequent packet witnessing a finish/last-lap target')
        t = timer[index]
        resets = np.flatnonzero(np.diff(t)<0)+1
        start_offset = int(resets[0]) if len(resets) else 0
        segment = group.iloc[start_offset:]
        t = timer[segment.index]
        if len(resets)>1:
            reasons.append('multiple timer resets inside source lap')
        if len(t)<100 or not np.isfinite(t).all() or (np.diff(t)<=0).any():
            reasons.append('missing, repeated or nonmonotonic lap timer')
        target = float(next_group.last_lap_ms.iloc[0])/1000 if len(next_group) else np.nan
        if len(next_group) and next_group.last_lap_ms.nunique()!=1:
            reasons.append('subsequent last-lap target changes inside the next lap')
        if not np.isfinite(target) or not 20<target<600:
            reasons.append('invalid full-lap target')
        if len(t) and (t[0]>.1 or not 0 <= target-t[-1] <= .1):
            reasons.append('lap timer does not cover both boundaries within 100 ms')
        if len(t)>1 and np.max(np.diff(t))>.1:
            reasons.append('simulator timer gap exceeds 100 ms')
        distance = segment.distance_m.to_numpy(dtype=float)
        if not len(distance) or not np.isfinite(distance).all() or (np.diff(distance)<0).any() or distance[-1]<1000 or distance[0]>10:
            reasons.append('invalid driven-distance coverage')
        if not group.lap_count.eq(lap_id).all():
            reasons.append('file lap ID and packet counter disagree')
        if reasons:
            rejected.append({'source_lap':int(lap_id),'reasons':'; '.join(reasons)})
            continue
        start, end = int(segment.index[0]), int(segment.index[-1])+1
        lap_elapsed[start:end] = timer[start:end]
        checked.append({'lap_id':int(lap_id), 'start_sample':start, 'end_sample':end,
                        'start_s':float(raw.wall_time.iloc[start]-raw.wall_time.iloc[0]),
                        'end_s':float(next_group.wall_time.iloc[0]-raw.wall_time.iloc[0]),
                        'duration_s':target, 'target_source':'next lap last_lap_ms',
                        'timing_basis':'simulator lap timer', 'target_verified':True})
    result = LapResult(bool(checked),
        'Source lap counter, witnessed next-lap target, strictly increasing timer and boundary coverage checked; rejected laps are excluded.',
        pd.DataFrame(checked) if checked else LapResult(False,'').laps)
    return result, lap_elapsed, rejected


def load_gt7_bundle(directory, manifest_path=None):
    directory=Path(directory)
    manifest_path=manifest_path or Path(__file__).resolve().parents[2]/'docs/GT7_MANIFEST_V05.json'
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    frames=[]
    for item in manifest['files']:
        if not item['path'].startswith('data/laps/'):
            continue
        path=directory/item['path']
        with path.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=item['sha256']:
            raise ValueError(f'GT7 source integrity mismatch: {path.name}')
        frames.append(pd.read_parquet(path))
    raw=pd.concat(frames,ignore_index=True)
    result,lap_elapsed,rejected=validate_gt7_laps(raw)
    metadata={'format':'GT7 Parquet bundle','filename':'GT7 Trial Mountain / Porsche 962 C',
              'session_id':'gt7:'+manifest['revision'], 'source_url':'https://huggingface.co/datasets/'+manifest['repo'],
              'revision':manifest['revision'],'license':'CC-BY-4.0','author':'Ricardo Queiroz',
              'track_id':'gt7:trial_mountain:forward', 'car_id':'gt7:3373', 'driver_count':1,'session_count':1,
              'position_provenance':'source-reported simulator world coordinates; not surveyed geometry',
              'position_units':'m', 'time_basis':'capture host wall_time; lap targets use simulator timer',
              'distance_provenance':'publisher derived driven distance; no fixed common centreline reference',
              'channel_units':{'pos_x':'m','pos_y':'m','elevation_m':'m',**{f'tyre_core_{c}':'°C' for c in ['fl','fr','rl','rr']}},
              'lap_rejections':rejected, 'source_laps':int(raw.lap.nunique()),
              'derived_source_channels':['distance_m','speed_kmh','steer_angle_l','steer_angle_r','slip_*'],
              'notes':['Quaternion rotation fields are not Euler angles.',
                       'Body-motion units and derived steering calibration are unverified.',
                       'One session/driver; target and feature readiness is not evidence of generalization.']}
    session=build_session(raw,metadata,PROFILE,result,lap_elapsed)
    # Preserve the vertical world coordinate under an unambiguous canonical name.
    session.data['elevation_m']=raw.pos_y.to_numpy()
    for corner in ['fl','fr','rl','rr']:
        session.data[f'tyre_core_{corner}']=raw[f'tyre_temp_{corner}'].to_numpy()
        session.data[f'susp_{corner}']=raw[f'susp_height_{corner}'].to_numpy()
        metadata['channel_units'][f'susp_{corner}']='m'
    session.metadata['channel_units']=metadata['channel_units']
    from motorsport.processing.validation import quality_report
    session.quality=quality_report(session.data,'elapsed_s')
    return session
