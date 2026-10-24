"""Configured human ACGym LD exports, with witnessed timing targets.

Historical manifests retain the original Monza defaults. New domains must declare
their expected car, track/layout and LD venue explicitly; timing rules are shared.
"""
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from .motec import read_ld
from motorsport.pipeline import build_session
from motorsport.processing.laps import LapResult

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = {
    'Ground Speed': ('speed_kmh','km/h'), 'Engine RPM': ('rpm','rpm'),
    'Throttle Pos': ('throttle_pct','%'), 'Brake Pos': ('brake_pct','%'),
    'Steering Angle': ('steering','deg'), 'Gear': ('gear',''),
    'Session Lap Count': ('source_lap_count',''), 'Lap Time': ('source_lap_time','s'),
    'Last Lap Time': ('source_last_lap_time','s'), 'Car Pos Norm': ('source_progress',''),
    'Lap Invalidated': ('source_invalid',''), 'Session Time Left': ('source_time_left','s'),
    'CG Accel Lateral': ('g_lat','G'), 'CG Accel Longitudinal': ('g_lon','G')}


def read_beacons(path):
    body = Path(path).read_bytes()
    if len(body)>100_000 or b'<!' in body:
        raise ValueError('Unsupported/unsafe LDX document')
    tree = ET.fromstring(body)
    beacons = [float(m.attrib['Time'])/1e6 for g in tree.iter('MarkerGroup')
               if g.attrib.get('Name')=='Beacons' for m in g.iter('Marker')]
    if len(beacons)<2 or not np.isfinite(beacons).all() or (np.diff(beacons)<=0).any():
        raise ValueError('Missing/nonmonotonic source beacons')
    return np.asarray(beacons)


def validate_laps(frame, beacons, hz):
    accepted, rejected = [], []
    count = frame.source_lap_count.to_numpy()
    if not np.isfinite(count).all() or not np.allclose(count,np.round(count),atol=1e-3):
        raise ValueError('Invalid lap counter')
    count = np.round(count).astype(int)
    changes = np.r_[0,np.flatnonzero(np.diff(count)!=0)+1,len(frame)]
    elapsed = np.full(len(frame),np.nan)
    for a,b in zip(changes[:-1],changes[1:]):
        lap_id = int(count[a])+1
        reasons = []
        t = frame.source_lap_time.iloc[a:b].to_numpy()
        target = float(frame.source_last_lap_time.iloc[b]) if b<len(frame) else np.nan
        if b==len(frame) or count[b]!=count[a]+1:
            reasons.append('no witnessed consecutive finish/next-packet target')
        if not np.isfinite(target) or not 20<target<600:
            reasons.append('invalid target')
        if not np.isfinite(t).all() or len(t)<100 or (np.diff(t)<-1e-6).any() or (np.diff(t)>.2).any():
            reasons.append('lap timer reset/missing/gap over 200 ms')
        if len(t) and (t[0]>.05 or not 0<=target-t[-1]<=.05):
            reasons.append('incomplete lap timer boundary coverage')
        if not (np.isfinite(frame.source_invalid.iloc[a:b]).all() and (frame.source_invalid.iloc[a:b]<.5).all()):
            reasons.append('source invalidates lap')
        start,end = a/hz,b/hz
        matching = np.flatnonzero(np.abs(beacons-start)<.05)
        if not len(matching) or matching[0]+1>=len(beacons) or abs(beacons[matching[0]+1]-end)>.05 or abs(end-start-target)>.05:
            reasons.append('beacons/export grid/source target disagree by over 50 ms')
        # The independent countdown must track the declared export grid.
        clock = frame.source_time_left.iloc[a:b].to_numpy()
        if not np.isfinite(clock).all() or (np.diff(clock)>.05).any() or (np.diff(clock)<-.2).any() or abs(clock[0]-clock[-1]-(len(clock)-1)/hz)>.1:
            reasons.append('countdown clock gap/reset or export clock disagreement')
        progress = frame.source_progress.iloc[a:b].to_numpy()
        if not np.isfinite(progress).all() or (progress<0).any() or (progress>1.001).any() or progress[0]>.01 or progress.max()<.99:
            reasons.append('incomplete source progress coverage')
        if reasons:
            rejected.append({'source_lap':lap_id,'start_sample':int(a),'reasons':'; '.join(reasons)})
        else:
            elapsed[a:b] = t
            accepted.append({'lap_id':lap_id,'start_sample':int(a),'end_sample':int(b),
                'start_s':start,'end_s':end,'duration_s':target,'target_verified':True,
                'target_source':'witnessed next-counter Last Lap Time; LD timer + LDX beacons + countdown agreement',
                'timing_basis':f'source lap timer; {hz} Hz export grid'})
    result = LapResult(bool(accepted),'Cross-checked source counter/timer/beacons/countdown; leading partials and unwitnessed tails excluded.',pd.DataFrame(accepted))
    return result,elapsed,rejected


def load_acgym_recording(path, entry, manifest, *, analysis_only=False):
    path = Path(path)
    header, channels = read_ld(path,CHANNELS)
    missing = set(CHANNELS)-set(channels)
    if missing:
        raise ValueError('Required source channels missing: '+', '.join(sorted(missing)))
    frequencies = {c.hz for c in channels.values()}
    lengths = {len(c.values) for c in channels.values()}
    if len(frequencies)!=1 or len(lengths)!=1:
        raise ValueError('Mixed export rates/lengths require a separately validated alignment')
    for name,(canonical,unit) in CHANNELS.items():
        if channels[name].unit!=unit:
            raise ValueError(f'Unexpected unit for {name}: {channels[name].unit}')
    hz = frequencies.pop()
    raw = pd.DataFrame({CHANNELS[name][0]:c.values for name,c in channels.items()})
    raw['elapsed_s'] = np.arange(len(raw))/hz
    car=manifest.get('car','dallara_f317')
    track=manifest.get('track','monza')
    if header['vehicle']!=car or header['venue']!=manifest.get('header_venue','monza'):
        raise ValueError('Car/track header disagrees with selected domain')
    day = datetime.strptime(header['date'],'%d/%m/%Y')
    date_matches=day.strftime('%Y%m%d')==entry['recording_label'][:8]
    if not date_matches and track=='monza':
        raise ValueError('Header date and recording folder disagree')
    timing_failure=None
    try:result,elapsed,rejected = validate_laps(raw,read_beacons(path.with_suffix('.ldx')),hz)
    except ValueError as exc:
        if not analysis_only:raise
        timing_failure=str(exc)
        result=LapResult(False,'Timing evidence unavailable: '+timing_failure,pd.DataFrame())
        elapsed=np.full(len(raw),np.nan);rejected=[]
    recording = entry['recording_label']
    # A_12/A_21 order variants have uncertain independence: conservatively group
    # every A-coded export into one physical unit, rather than inflate sessions.
    namespace='acgym' if track=='monza' else 'acgym:'+track
    physical = namespace+':A:unresolved-series' if entry['driver_label']=='A' else namespace+':'+recording
    stint = int(re.search(r'stint_(\d+)',path.stem).group(1))
    metadata = {'filename':recording+' / '+path.stem,'format':'MoTeC LD/LDX',
        'session_id':namespace+':'+entry['sha256'],'physical_session_id':physical,
        'driver_id':'acgym:'+entry['driver_label'],'session_date':day.isoformat(),
        'recording_order':stint,'car_id':'ac:'+car,'track_id':'ac:'+track,'export_hz':hz,
        'independence_verified':entry['driver_label']!='A' and (track=='monza' or (entry['driver_label']!='XX' and date_matches)),
        'source_sha256':entry['sha256'],'source_url':entry['url'],
        'source_header':header,'license':manifest['license'],'revision':manifest['revision'],
        'channel_units':{'steering':'deg','g_lat':'g','g_lon':'g'},
        'time_basis':f'{hz} Hz source export grid, checked against source countdown; native acquisition rate unproven',
        'rejected_laps':rejected,'session_count':1,'driver_count':1}
    if track!='monza':
        metadata['recording_label']=recording
        metadata['identity_quarantine']=(['unresolved participant/capture identity'] if entry['driver_label'] in ('A','XX') else [])
        if not date_matches:metadata['identity_quarantine'].append('header date and recording folder disagree')
        if timing_failure:
            metadata['identity_quarantine'].append(timing_failure)
            metadata['independence_verified']=False
    return build_session(raw,metadata,validated_laps=result,lap_elapsed=elapsed)


def load_acgym_sessions(directory=None,manifest_path=None):
    directory = Path(directory or ROOT/'data/raw/acgym_monza_dallara')
    manifest = json.loads(Path(manifest_path or ROOT/'docs/ACGYM_MANIFEST_V06.json').read_text(encoding='utf-8'))
    sessions, rejected_recordings, seen = [], [], set()
    for entry in manifest['files']:
        path = (directory/entry['path']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('Unsafe source manifest path')
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=entry.get('sha256'):
            raise ValueError('ACGym source integrity mismatch: '+entry['path'])
        if path.suffix=='.ld':
            if digest in seen:
                continue
            seen.add(digest)
            try:
                sessions.append(load_acgym_recording(path,entry,manifest))
            except ValueError as exc:
                rejected_recordings.append({'source':entry['path'],'reason':str(exc)})
    return sessions,rejected_recordings
