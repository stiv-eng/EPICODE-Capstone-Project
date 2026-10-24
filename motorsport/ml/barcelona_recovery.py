"""Inclusive v0.7.1 Barcelona audit, recording holdout and offline references.

Metadata uncertainty is descriptive. Only target/signal/domain/duplicate defects
exclude observations. This module never downloads data or fits a model.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from motorsport.ingestion.acgym_importer import load_acgym_recording
from .barcelona import (ROOT, RAW, MANIFEST, DOMAIN, SCHEMA_VERSION,
                        FEATURE_VERSION, UNITS, file_sha, manifest_entry_path)
from .dataset import Corpus, ReplayLap, core_coverage, lap_fingerprint
from .features import FEATURES

PROTOCOL = ROOT/'docs/BARCELONA_PROTOCOL_V071.json'


def exact_lap_hash(frame, target):
    digest = hashlib.sha256(repr((list(frame.columns), float(target))).encode())
    digest.update(pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes())
    return digest.hexdigest()


def load_corpus(root=RAW, manifest_path=MANIFEST):
    root = Path(root)
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if (manifest.get('track'), manifest.get('car')) != ('ks_barcelona-layout_gp', 'dallara_f317'):
        raise ValueError('Barcelona car/track domain required')
    config = {**manifest, 'target_rounding_s': .001, 'optional_feature_channels': True,
              'allow_unknown_date': True}
    entries = {e['path']: e for e in manifest['files']}
    records, lap_rows, exclusions, laps, targets = [], [], [], [], []
    captures, exact, signatures, parents = set(), set(), {}, {}

    def find(group):
        parents.setdefault(group, group)
        if parents[group] != group: parents[group] = find(parents[group])
        return parents[group]

    links = []
    for entry in manifest['files']:
        if not entry['path'].endswith('.ld'): continue
        entry={**entry, 'driver_label':entry.get('driver_label') or 'unknown'}
        path = manifest_entry_path(root, entry)
        record = dict(source=entry['path'], recording_label=entry['recording_label'],
                      participant_code=entry.get('driver_label', 'unknown'), validated_laps=0, eligible_laps=0)
        if not path.exists():
            records.append({**record, 'status': 'missing', 'reason': 'raw recording not installed'}); continue
        if entry.get('source_type') != 'human': raise ValueError('Nonhuman source rejected')
        for relative in (entry['path'], entry['path']+'x'):
            evidence = entries.get(relative)
            if evidence is None: raise ValueError('Unpaired recording: '+relative)
            candidate = manifest_entry_path(root, evidence)
            if not candidate.exists():
                break
            if not evidence.get('sha256') or file_sha(candidate) != evidence['sha256']:
                raise ValueError('Barcelona integrity mismatch: '+relative)
        else:
            candidate = None
        if candidate is not None:
            records.append({**record, 'status': 'missing', 'reason': 'paired timing evidence missing'}); continue
        digest = entry['sha256']
        if digest in captures:
            records.append({**record, 'status': 'duplicate', 'reason': 'exact raw capture hash'}); continue
        captures.add(digest)
        try:
            session = load_acgym_recording(path, entry, config)
        except (ValueError, OSError) as exc:
            records.append({**record, 'status': 'rejected', 'reason': str(exc)}); continue
        meta = session.metadata
        flags = meta.get('identity_quarantine', [])
        # XX is a collection, not evidence that captures share one acquisition.
        group = 'barcelona:recording:'+ (digest if entry.get('driver_label') == 'XX' else entry['recording_label'])
        find(group)
        record.update(status='imported', metadata_uncertainty='; '.join(flags),
                      header_date=meta['source_header']['date'], header_time=meta['source_header']['time'],
                      source_sha256=digest, physical_session_id=group, export_hz=meta['export_hz'],
                      samples=len(session.data), validated_laps=len(session.laps.laps))
        for rejected in meta['rejected_laps']:
            lap_rows.append(dict(source=entry['path'], physical_session_id=group, status='rejected', **rejected))
        for lap in session.laps.laps.itertuples(index=False):
            raw = session.data.iloc[lap.start_sample:lap.end_sample]
            frame = raw.reindex(columns=['lap_elapsed_s', 'speed_kmh', 'throttle_pct', 'brake_pct',
                                         'rpm', 'gear', 'steering']).reset_index(drop=True)
            uid = digest+':lap:'+str(lap.lap_id)
            coverage = min(core_coverage(frame).values())
            target = float(lap.duration_s)
            signature, full_hash = lap_fingerprint(frame), exact_lap_hash(frame, target)
            reasons = []
            if not lap.target_verified or not np.isfinite(target): reasons.append('unverified target')
            if coverage < .99: reasons.append('core signal coverage below 99%')
            if full_hash in exact: reasons.append('exact canonical lap and target duplicate')
            exact.add(full_hash)
            # Coarse similarity is evidence of possible related exports, not a
            # sufficient reason to discard a nonidentical, otherwise valid lap.
            key = (signature, round(target, 3))
            if key in signatures:
                other = signatures[key]
                if find(other) != find(group):
                    links.append(dict(left=other, right=group, reason='matching coarse trajectory and target'))
                    parents[find(group)] = find(other)
            signatures[key] = group
            timer = raw.source_lap_time.to_numpy(float)
            step = float(np.max(np.diff(timer)))
            source = ReplayLap(uid, group, meta.get('driver_id', 'unidentified'), DOMAIN,
                               (meta['session_date'], meta['recording_order'], float(lap.start_s)),
                               frame, False, meta.get('channel_units', {}).get('steering', 'unknown'))
            item = dict(lap_uid=uid, source=entry['path'], source_lap=int(lap.lap_id),
                        physical_session_id=group, driver_id=source.driver_id, target_s=target,
                        min_core_coverage=coverage, metadata_uncertainty='; '.join(flags),
                        max_timer_step_s=step, timing_quality_category=step > .1000001,
                        date_reliable=not any('date' in flag for flag in flags),
                        exact_hash=full_hash, fingerprint=signature, source_id=digest,
                        source_sha256=digest, source_url=entry['url'], source_revision=manifest['revision'],
                        target_source=lap.target_source, start_order=source.start_order, domain=DOMAIN,
                        independence_verified=False, status='excluded' if reasons else 'eligible',
                        reasons='; '.join(reasons))
            lap_rows.append(item)
            if reasons: exclusions.append(item); continue
            laps.append(source); targets.append(item); record['eligible_laps'] += 1
        records.append(record)
    for lap in laps: lap.physical_session_id = find(lap.physical_session_id)
    for row in targets+lap_rows+records:
        if row.get('physical_session_id'): row['physical_session_id'] = find(row['physical_session_id'])
    corpus = Corpus('Barcelona GP / Dallara F317 v0.7.1 inclusive human recordings',
                    sorted(laps, key=lambda lap: (lap.start_order, lap.lap_uid)), pd.DataFrame(targets), exclusions)
    old_path = ROOT/'docs/BARCELONA_AUDIT_V07.json'
    old = json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {}
    old_excluded = {r['lap_uid'] for r in old.get('lap_audit', []) if r['status'] == 'excluded'}
    old_valid = {r['lap_uid'] for r in old.get('lap_audit', []) if r.get('lap_uid')}
    ids = {lap.lap_uid for lap in laps}
    audit = dict(expected_recordings=len(records), downloaded_recordings=sum(r['status'] != 'missing' for r in records),
                 imported_recordings=sum(r['status'] == 'imported' for r in records),
                 validated_complete_laps=sum(r['validated_laps'] for r in records), eligible_laps=len(laps),
                 recording_groups=len({l.physical_session_id for l in laps}),
                 recovered_metadata_laps=len(ids & old_excluded), additional_recovered_laps=len(ids-old_valid),
                 metadata_uncertain_included=sum(bool(t['metadata_uncertainty']) for t in targets),
                 excluded_validated_laps=len(exclusions), rejected_lap_candidates=sum(r['status']=='rejected' for r in lap_rows),
                 exact_raw_duplicates=sum(r['status']=='duplicate' for r in records),
                 exact_lap_duplicates=sum('duplicate' in r['reasons'] for r in exclusions), related_capture_links=links,
                 target_distribution=corpus.targets.target_s.describe().to_dict() if targets else {},
                 records=records, lap_audit=lap_rows, revision=manifest['revision'],
                 corpus_id=corpus.identity, manifest_sha256=file_sha(manifest_path),
                 limitation='Retrospective recording holdout; unknown links and participant identities. '
                            'Recording blocks do not establish unseen-session/driver or chronological generalization.')
    return corpus, audit


def frozen_split(corpus):
    groups = sorted({lap.physical_session_id for lap in corpus.laps})
    if len(groups) < 3: raise ValueError('Three nonempty recording partitions cannot be constructed')
    order = np.random.default_rng(42).permutation(groups).tolist()
    a = max(1, min(len(order)-2, int(len(order)*.6)))
    b = max(a+1, min(len(order)-1, int(len(order)*.8)))
    assignment = {g: 'train' if i<a else 'validation' if i<b else 'test' for i,g in enumerate(order)}
    return pd.DataFrame([dict(lap_uid=l.lap_uid, physical_session_id=l.physical_session_id,
                              partition=assignment[l.physical_session_id]) for l in corpus.laps])


def data_gate(corpus, audit=None):
    reasons = []
    if not corpus.laps: reasons.append('No technically usable laps')
    if any(l.domain != DOMAIN for l in corpus.laps): reasons.append('Wrong model domain')
    targets = corpus.targets
    if len(targets) and (targets.lap_uid.duplicated().any() or targets.exact_hash.duplicated().any()
                         or not np.isfinite(targets.target_s).all() or targets.min_core_coverage.min() < .99):
        reasons.append('Invalid target, duplicate identity or insufficient core coverage')
    try: split = frozen_split(corpus)
    except ValueError as exc: reasons.append(str(exc)); split = pd.DataFrame()
    return dict(eligible=not reasons, reasons=reasons, validated_laps=len(corpus.laps),
                physical_sessions=len({l.physical_session_id for l in corpus.laps}),
                drivers=len({l.driver_id for l in corpus.laps}),
                min_core_coverage=float(targets.min_core_coverage.min()) if len(targets) else 0.,
                group_counts=split.groupby('partition').physical_session_id.nunique().to_dict() if len(split) else {},
                lap_counts=split.groupby('partition').lap_uid.nunique().to_dict() if len(split) else {})


def compatibility(corpus):
    return dict(car='dallara_f317', track='ks_barcelona-layout_gp', domain=list(DOMAIN),
                schema_version=SCHEMA_VERSION, units=UNITS, feature_version=FEATURE_VERSION,
                features=list(FEATURES), corpus_id=corpus.identity, model_version='barcelona-v071-1',
                protocol_sha256=file_sha(PROTOCOL))


def verify_compatibility(bundle, corpus):
    if tuple(bundle.domain) != DOMAIN or any(l.domain != DOMAIN for l in corpus.laps):
        raise ValueError('Model car/track mismatch: Barcelona GP / Dallara F317 required')
    if getattr(bundle, 'compatibility', None) != compatibility(corpus) or bundle.corpus_id != corpus.identity:
        raise ValueError('Model corpus/schema/units/features/protocol mismatch')
    if tuple(bundle.feature_names) != tuple(FEATURES): raise ValueError('Causal feature contract mismatch')


def baseline_references(source, history, date_reliability=None):
    permitted = [h for h in history if h.domain == source.domain and h.lap_uid != source.lap_uid]
    median = float(np.median([h.target_s for h in permitted])) if permitted else None
    capture = source.lap_uid.split(':lap:')[0]
    earlier = [h for h in permitted if h.lap_uid.split(':lap:')[0] == capture and h.end_order <= source.start_order]
    if not earlier and date_reliability and date_reliability.get(source.lap_uid, False):
        earlier = [h for h in permitted if date_reliability.get(h.lap_uid, False)
                   and h.end_order[0] < source.start_order[0]]
        if earlier:
            last_day = max(h.end_order[0] for h in earlier)
            day_rows = [h for h in earlier if h.end_order[0] == last_day]
            # Stint numbers alone do not order different same-day captures.
            if len({h.lap_uid.split(':lap:')[0] for h in day_rows}) != 1: earlier = []
            else: earlier = day_rows
    previous = max(earlier, key=lambda h:h.end_order).target_s if earlier else None
    return dict(previous_lap=previous, historical_median=median, history_laps=len(permitted))


def predict(source, checkpoint, model=None, feature_names=(), history=(), baseline='historical_median',
            model_domain=None, date_reliability=None):
    from .inference import predict as causal_predict
    result = causal_predict(source, checkpoint, model, feature_names, (), baseline, model_domain)
    reference = baseline_references(source, history, date_reliability)[baseline]
    return replace(result, baseline_s=reference,
                   predicted_final_s=result.predicted_final_s if model is not None else reference)
