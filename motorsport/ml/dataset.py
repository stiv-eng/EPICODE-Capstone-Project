"""Separate predictive observations from verified labels and source identity."""
from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

CORE = {'speed_kmh':(0,500),'throttle_pct':(0,100),'brake_pct':(0,100),'rpm':(0,25000)}


@dataclass
class ReplayLap:
    lap_uid: str
    physical_session_id: str
    driver_id: str
    domain: tuple
    start_order: tuple
    frame: pd.DataFrame
    independence_verified: bool = False
    steering_unit: str = 'unknown'


@dataclass
class Corpus:
    name: str
    laps: list[ReplayLap]
    targets: pd.DataFrame
    exclusions: list

    @property
    def identity(self):
        payload = self.targets.to_json(orient='records',double_precision=12)
        digest = hashlib.sha256((self.name+payload).encode())
        # Re-mapping the same raw capture can change canonical feature values or
        # declared units without changing its verified targets. Invalidate models
        # in that case too, rather than silently reusing an earlier mapping.
        for lap in self.laps:
            digest.update(repr((lap.lap_uid,lap.domain,lap.steering_unit,list(lap.frame.columns))).encode())
            digest.update(pd.util.hash_pandas_object(lap.frame,index=True).to_numpy().tobytes())
        return digest.hexdigest()


def core_coverage(frame):
    return {c:float((np.isfinite(pd.to_numeric(frame[c],errors='coerce')) & pd.to_numeric(frame[c],errors='coerce').between(*bounds)).mean())
            if c in frame and len(frame) else 0. for c,bounds in CORE.items()}


def lap_fingerprint(frame):
    """Clock-relative 1 s signatures catch copies exported on different grids.

    Conservative exact signature check, supplemented by physical-session groups;
    this does not prove that near-duplicate trajectories are independent.
    """
    time = frame.lap_elapsed_s.to_numpy(float)
    grid = np.arange(1,int(np.nanmax(time)))
    positions = np.searchsorted(time,grid,side='right')-1
    columns = ['speed_kmh','throttle_pct','brake_pct','rpm']
    values = frame.reindex(columns=columns).iloc[positions].to_numpy(float)
    return hashlib.sha256(np.round(values,3).tobytes()).hexdigest()


def from_sessions(sessions, name='Local validated telemetry'):
    laps, targets, exclusions, signatures, captures = [], [], [], set(), set()
    for session in sessions:
        meta = session.metadata
        capture = meta.get('source_sha256',meta['session_id'])
        if capture in captures:
            exclusions.append({'source':meta['filename'],'reason':'duplicate raw capture'})
            continue
        captures.add(capture)
        exclusions.extend({'source':meta['filename'],**r} for r in meta.get('rejected_laps',meta.get('lap_rejections',[])))
        if not session.laps.available:
            continue
        for lap in session.laps.laps.itertuples(index=False):
            if not getattr(lap,'target_verified',False):
                exclusions.append({'source':meta['filename'],'reason':'target lacks independent verification'})
                continue
            frame = session.data.iloc[lap.start_sample:lap.end_sample].copy()
            # Hard input boundary: next-lap timing, labels, raw provenance and
            # whole-session KPIs never travel with a predictive replay source.
            columns = ['lap_elapsed_s','speed_kmh','throttle_pct','brake_pct','rpm','gear','steering']
            frame = frame.reindex(columns=columns).reset_index(drop=True)
            fingerprint = lap_fingerprint(frame)
            if fingerprint in signatures:
                exclusions.append({'source':meta['filename'],'source_lap':int(lap.lap_id),'reason':'duplicate derived lap signature'})
                continue
            signatures.add(fingerprint)
            physical = meta.get('physical_session_id',meta['session_id'])
            uid = capture+':lap:'+str(lap.lap_id)
            day = meta.get('session_date','1970-01-01')
            order = (day,meta.get('recording_order',0),float(lap.start_s))
            source = ReplayLap(uid,physical,meta.get('driver_id','unidentified'),
                (meta.get('track_id','unknown'),meta.get('car_id','unknown')),order,frame,
                bool(meta.get('independence_verified',False)),meta.get('channel_units',{}).get('steering','unknown'))
            laps.append(source)
            targets.append({'lap_uid':uid,'physical_session_id':physical,'driver_id':source.driver_id,
                'target_s':float(lap.duration_s),'target_source':lap.target_source,
                'source_id':capture,'source_sha256':meta.get('source_sha256'),
                'source_revision':meta.get('revision'),'source_url':meta.get('source_url'),
                'fingerprint':fingerprint,'start_order':order,
                'domain':source.domain,'min_core_coverage':min(core_coverage(frame).values()),
                'independence_verified':source.independence_verified})
    return Corpus(name,sorted(laps,key=lambda lap:lap.start_order),pd.DataFrame(targets),exclusions)


def eligibility(corpus):
    reasons = []
    targets = corpus.targets
    count = len(targets)
    sessions = len({lap.physical_session_id for lap in corpus.laps})
    if count<30: reasons.append(f'{count}/30 validated target laps')
    if sessions<3: reasons.append(f'{sessions}/3 physical sessions')
    coverage = float(targets.min_core_coverage.min()) if count else 0.
    if coverage<.99: reasons.append(f'Core coverage {coverage:.2%} is below 99%')
    if any(not lap.independence_verified for lap in corpus.laps):
        reasons.append('Physical independence is not established for every recording')
    domains = {lap.domain for lap in corpus.laps}
    if len(domains)!=1 or any('unknown' in d for d in domains):
        reasons.append('Mixed or unverified car/track domains')
    return {'eligible':not reasons,'reasons':reasons,'validated_laps':count,'physical_sessions':sessions,
            'drivers':len({lap.driver_id for lap in corpus.laps}),'min_core_coverage':coverage,
            'domain':sorted(domains),'policy':'Necessary engineering gate; not evidence of generalization'}


def independent_subset(corpus):
    """Ambiguous A-coded series stay inspectable but outside robust evaluation."""
    laps = [lap for lap in corpus.laps if lap.independence_verified]
    ids = {lap.lap_uid for lap in laps}
    targets = corpus.targets.loc[corpus.targets.lap_uid.isin(ids)].copy() if len(corpus.targets) else corpus.targets
    omitted = [{'lap_uid':lap.lap_uid,'reason':'unresolved physical independence'} for lap in corpus.laps if lap.lap_uid not in ids]
    return Corpus(corpus.name+' / independently identified recordings',laps,targets,corpus.exclusions+omitted)
