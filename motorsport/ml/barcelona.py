"""Single-domain Barcelona corpus audit and preregistered grouped split.

The historical Monza/GT7 corpus and numerical training path remain unchanged.
No network call is made here. Raw originals and identity exclusions are retained.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from motorsport.ingestion.acgym_importer import load_acgym_recording
from motorsport.ingestion.motec import read_ld
from .dataset import Corpus,from_sessions
from .features import FEATURES

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/acgym_barcelona_dallara'
MANIFEST=ROOT/'docs/BARCELONA_MANIFEST_V07.json'
PROTOCOL=ROOT/'docs/BARCELONA_PROTOCOL_V07.json'
DOMAIN=('ac:ks_barcelona-layout_gp','ac:dallara_f317')
FEATURE_VERSION='causal-prefix-v06'
SCHEMA_VERSION='canonical-telemetry-v06'
UNITS={'speed_kmh':'km/h','throttle_pct':'%','brake_pct':'%','rpm':'rpm','steering':'deg','gear':'reported source gear'}


def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def manifest_entry_path(root,entry):
    root=Path(root).resolve();path=(root/entry['path']).resolve()
    if not path.is_relative_to(root):raise ValueError('Unsafe Barcelona manifest path')
    return path


def load_corpus(root=RAW,manifest_path=MANIFEST):
    root=Path(root);manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if (manifest.get('track'),manifest.get('car'))!=('ks_barcelona-layout_gp','dallara_f317'):
        raise ValueError('Barcelona corpus must use exactly its declared car/track domain')
    entries={e['path']:e for e in manifest['files']}
    records,lap_rows,exclusions,laps,tables=[],[],[],[],[]
    seen_captures,seen_laps=set(),set()
    for entry in manifest['files']:
        if not entry['path'].endswith('.ld'):continue
        path=manifest_entry_path(root,entry)
        row=dict(source=entry['path'],recording_label=entry['recording_label'],participant_code=entry['driver_label'],
                 bytes=entry['bytes'],validated_laps=0,eligible_laps=0)
        if not path.exists():records.append({**row,'status':'missing','reason':'run the explicit acquisition command'});continue
        if entry.get('source_type')!='human':raise ValueError('Nonhuman source rejected before import')
        companion=entries.get(entry['path']+'x')
        if companion is None:raise ValueError('Unpaired Barcelona manifest recording')
        if not manifest_entry_path(root,companion).is_file() or not companion.get('sha256'):
            records.append({**row,'status':'missing','reason':'paired timing evidence not installed/verified yet'});continue
        # Both the numerical payload and independent timing evidence are pinned.
        for relative in (entry['path'],entry['path']+'x'):
            evidence=entries.get(relative)
            if evidence is None:raise ValueError('Unpaired Barcelona recording')
            candidate=manifest_entry_path(root,evidence)
            if not candidate.is_file() or not evidence.get('sha256') or file_sha(candidate)!=evidence['sha256']:
                raise ValueError('Barcelona integrity mismatch/missing timing evidence: '+relative)
        digest=entry['sha256']
        if digest in seen_captures:
            records.append({**row,'status':'duplicate','reason':'duplicate raw capture hash'});continue
        seen_captures.add(digest)
        try:session=load_acgym_recording(path,entry,manifest)
        except (ValueError,OSError) as exc:
            header,_=read_ld(path,[])
            row.update(header_date=header['date'],header_time=header['time'],header_driver=header['driver'],
                       header_car=header['vehicle'],header_venue=header['venue'])
            records.append({**row,'status':'rejected','reason':str(exc)});continue
        meta=session.metadata
        quarantine=list(meta.get('identity_quarantine',[]))
        row.update(header_date=meta['source_header']['date'],header_time=meta['source_header']['time'],
            header_driver=meta['source_header']['driver'],header_car=meta['source_header']['vehicle'],
            header_venue=meta['source_header']['venue'],physical_session_id=meta['physical_session_id'],
            export_hz=meta['export_hz'],samples=len(session.data),validated_laps=len(session.laps.laps),
            source_sha256=digest,reason='; '.join(quarantine),status='quarantined' if quarantine else 'imported',
            position_available=bool({'pos_x','pos_y'}<=set(session.data)))
        for rejected in meta['rejected_laps']:
            lap_rows.append(dict(source=entry['path'],physical_session_id=meta['physical_session_id'],
                                 participant_code=entry['driver_label'],status='rejected',**rejected))
        part=from_sessions([session],'Barcelona')
        targets=part.targets.set_index('lap_uid') if len(part.targets) else part.targets
        for source in part.laps:
            target=targets.loc[source.lap_uid].to_dict()
            reasons=list(quarantine)
            if source.domain!=DOMAIN:reasons.append('wrong domain')
            if target['min_core_coverage']<.99:reasons.append('core signal coverage below 99%')
            if target['fingerprint'] in seen_laps:reasons.append('duplicate derived lap signature')
            seen_laps.add(target['fingerprint'])
            audit=dict(source=entry['path'],source_lap=source.lap_uid.split(':lap:')[-1],
                physical_session_id=source.physical_session_id,participant_code=entry['driver_label'],
                lap_uid=source.lap_uid,target_s=target['target_s'],min_core_coverage=target['min_core_coverage'],
                status='excluded' if reasons else 'eligible',reasons='; '.join(reasons))
            lap_rows.append(audit)
            if reasons:exclusions.append(audit);continue
            laps.append(source);tables.append({'lap_uid':source.lap_uid,**target});row['eligible_laps']+=1
        records.append(row)
    corpus=Corpus('Barcelona GP / Dallara F317 · validated human recordings',
                  sorted(laps,key=lambda lap:(lap.start_order,lap.lap_uid)),pd.DataFrame(tables),exclusions)
    targets=corpus.targets
    audit=dict(published_laps=247,published_stints=70,published_steps=612557,
        expected_recordings=sum(e['path'].endswith('.ld') for e in manifest['files']),
        downloaded_recordings=sum(r['status']!='missing' for r in records),
        imported_recordings=sum(r['status'] in ('imported','quarantined') for r in records),
        validated_complete_laps=sum(r['validated_laps'] for r in records),
        eligible_laps=len(laps),independent_groups=len({l.physical_session_id for l in laps}),
        participant_codes=sorted({l.driver_id.removeprefix('acgym:') for l in laps}),
        rejected_laps=sum(r['status']=='rejected' for r in lap_rows),
        excluded_validated_laps=sum(r['status']=='excluded' for r in lap_rows),
        target_distribution=targets.target_s.describe().to_dict() if len(targets) else {},
        records=records,lap_audit=lap_rows,revision=manifest['revision'],manifest_sha256=file_sha(manifest_path),
        corpus_id=corpus.identity,clock_limitation='Export grid and source timers validated; native acquisition/resampling latency unproven. Header times are coarse; no cross-capture same-day baseline ordering is assumed.')
    return corpus,audit


def frozen_split(corpus):
    """Whole recording/date blocks; do not invent chronology within one day."""
    groups={lap.physical_session_id:min(l.start_order[0] for l in corpus.laps if l.physical_session_id==lap.physical_session_id)
            for lap in corpus.laps}
    days=sorted(set(groups.values()));n=len(groups);candidates=[]
    for a in range(1,len(days)-1):
        for b in range(a+1,len(days)):
            assignment={g:'train' if day<days[a] else 'validation' if day<days[b] else 'test' for g,day in groups.items()}
            counts={p:sum(v==p for v in assignment.values()) for p in ('train','validation','test')}
            if counts['train']<6 or counts['validation']<3 or counts['test']<3:continue
            score=sum(abs(counts[p]-n*f) for p,f in [('train',.6),('validation',.2),('test',.2)])
            candidates.append((score,days[a],days[b],assignment))
    if not candidates:raise ValueError('Insufficient date-separated groups for the preregistered 6/3/3 minimum')
    assignment=min(candidates,key=lambda row:row[:3])[3]
    return pd.DataFrame([dict(lap_uid=lap.lap_uid,physical_session_id=lap.physical_session_id,
                              partition=assignment[lap.physical_session_id]) for lap in corpus.laps])


def data_gate(corpus,audit=None):
    policy=json.loads(PROTOCOL.read_text(encoding='utf-8'))['data_gate'];reasons=[]
    groups=len({lap.physical_session_id for lap in corpus.laps})
    drivers=len({lap.driver_id for lap in corpus.laps})
    for actual,required,label in [(groups,policy['minimum_independent_groups'],'independent groups'),
        (len(corpus.laps),policy['minimum_validated_eligible_laps'],'eligible laps'),
        (drivers,policy['minimum_identified_participant_codes'],'identified participant codes')]:
        if actual<required:reasons.append(f'{actual}/{required} {label}')
    if any(lap.domain!=DOMAIN or not lap.independence_verified for lap in corpus.laps):reasons.append('Unverified independence/domain')
    if len(corpus.targets) and (corpus.targets.fingerprint.duplicated().any() or corpus.targets.min_core_coverage.min()<.99):
        reasons.append('Duplicate trajectories or insufficient core coverage')
    if len(corpus.targets) and (corpus.targets.lap_uid.duplicated().any() or
        set(corpus.targets.lap_uid)!={lap.lap_uid for lap in corpus.laps} or
        not np.isfinite(corpus.targets.target_s).all()):reasons.append('Invalid/duplicate target identity')
    try:split=frozen_split(corpus)
    except ValueError as exc:reasons.append(str(exc));split=pd.DataFrame()
    if audit and audit['downloaded_recordings']!=audit['expected_recordings']:reasons.append('Acquisition incomplete: audit all inspected human recordings first')
    return dict(eligible=not reasons,reasons=reasons,validated_laps=len(corpus.laps),physical_sessions=groups,
        drivers=drivers,min_core_coverage=float(corpus.targets.min_core_coverage.min()) if len(corpus.targets) else 0.,
        group_counts=split.groupby('partition').physical_session_id.nunique().to_dict() if len(split) else {},
        lap_counts=split.groupby('partition').lap_uid.nunique().to_dict() if len(split) else {})


def permissible_history(source,history):
    """Only same-capture witnessed order or a strictly earlier calendar date."""
    capture=source.lap_uid.split(':lap:')[0]
    return [h for h in history if h.end_order[0]<source.start_order[0] or h.lap_uid.split(':lap:')[0]==capture]


def compatibility(corpus):
    return dict(car='dallara_f317',track='ks_barcelona-layout_gp',domain=list(DOMAIN),
        schema_version=SCHEMA_VERSION,units=UNITS,feature_version=FEATURE_VERSION,
        features=list(FEATURES),corpus_id=corpus.identity,model_version='barcelona-v07-1',protocol_sha256=file_sha(PROTOCOL))


def verify_compatibility(bundle,corpus):
    if bundle.domain!=DOMAIN or any(l.domain!=DOMAIN for l in corpus.laps):raise ValueError('Model car/track mismatch: Barcelona GP / Dallara F317 required')
    if getattr(bundle,'compatibility',None)!=compatibility(corpus) or bundle.corpus_id!=corpus.identity:
        raise ValueError('Model corpus/schema/units/feature/model version differs from the installed Barcelona corpus')
    if tuple(bundle.feature_names)!=tuple(FEATURES):raise ValueError('Model causal feature contract mismatch')
