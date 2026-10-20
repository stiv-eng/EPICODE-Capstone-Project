"""Offline reproducible source/target audit and explicitly requested ML fit."""
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from motorsport.ingestion.acgym_importer import load_acgym_sessions
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.ml.dataset import from_sessions,independent_subset,eligibility
from motorsport.ml.features import snapshots
from motorsport.ml.training import train
from motorsport.ml.artifacts import LocalArtifactStore

ROOT=Path(__file__).resolve().parents[1]


def audit():
    started=time.perf_counter()
    manifest=json.loads((ROOT/'docs/ACGYM_MANIFEST_V06.json').read_text())
    sessions,rejected_recordings=load_acgym_sessions()
    all_corpus=from_sessions(sessions,'ACGym human Monza / Dallara F317')
    all_corpus.exclusions.extend(rejected_recordings)
    corpus=independent_subset(all_corpus)
    table,rejected_snapshots=snapshots(corpus)
    rows,recordings=[],[]
    for session in sessions:
        meta=session.metadata
        recordings.append({'recording':meta['filename'],'physical_session_id':meta['physical_session_id'],
            'driver_id':meta['driver_id'],'header':meta['source_header'],'export_hz':meta['export_hz'],
            'independence_verified':meta['independence_verified'],'rows':len(session.data),
            'lap_targets':len(session.laps.laps),'rejected_laps':len(meta['rejected_laps']),
            'source_sha256':meta['source_sha256']})
        for lap in session.laps.laps.to_dict('records'):
            rows.append({'recording':meta['filename'],'status':'timing validated',**lap,
                         'independence_verified':meta['independence_verified']})
        for rejected in meta['rejected_laps']:
            rows.append({'recording':meta['filename'],'status':'rejected',**rejected,
                         'independence_verified':meta['independence_verified']})
    pd.DataFrame(rows).to_csv(ROOT/'docs/ACGYM_LAP_AUDIT_V06.csv',index=False)
    report={'repo':manifest['repo'],'revision':manifest['revision'],
        'payload_bytes':sum(e['bytes'] for e in manifest['files']),'files':len(manifest['files']),
        'verified_recordings':len(sessions),'rejected_recordings':rejected_recordings,
        'timing_validated_laps':len(all_corpus.laps),'independence_excluded_laps':len(all_corpus.laps)-len(corpus.laps),
        'rejected_lap_segments':sum(len(s.metadata['rejected_laps']) for s in sessions),
        'core_export_rows':sum(len(s.data) for s in sessions),
        'gate':eligibility(corpus),'target_min_s':float(corpus.targets.target_s.min()),
        'target_max_s':float(corpus.targets.target_s.max()),'accepted_snapshots':len(table),
        'rejected_snapshots':len(rejected_snapshots),'recordings':recordings,
        'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','pyarrow','scikit-learn','streamlit','joblib']}}
    ledger=ROOT/'artifacts/acgym_download_ledger.json'
    if ledger.exists():
        report['download_ledger']=json.loads(ledger.read_text())
    (ROOT/'docs/DATASET_MEASUREMENTS_V06.json').write_text(json.dumps(report,indent=2)+'\n')
    results={}
    for label,selected,experimental in [('ACGym',corpus,False),('GT7',from_sessions([
        load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')],'GT7 experimental'),True)]:
        bundle=train(selected,experimental=experimental)
        store=LocalArtifactStore(ROOT/'artifacts/models')
        store.save(bundle,'audit-v06-'+label.lower())
        restored=store.load('audit-v06-'+label.lower())
        if not restored.predictions.equals(bundle.predictions):
            raise ValueError('Artifact roundtrip differs')
        selected_columns=['model','partition','physical_session_id','lap_uid','checkpoint_s',
            'target_s','target_source','prediction_s','error_s','previous_lap','historical_median']
        bundle.predictions[selected_columns].to_csv(ROOT/f'docs/{label.upper()}_ML_ERRORS_V06.csv',index=False)
        split=bundle.split.merge(selected.targets[['lap_uid','start_order','driver_id']] if 'driver_id' in selected.targets
            else selected.targets[['lap_uid','start_order']],on='lap_uid',validate='one_to_one')
        results[label]={'mode':bundle.mode,'corpus_id':selected.identity,'selected_model':bundle.selected_model,
            'split':json.loads(split.to_json(orient='records')),'features':bundle.feature_names,
            'metrics':{name:json.loads(frame.to_json(orient='records',double_precision=12)) for name,frame in bundle.reports.items() if name!='individual'},
            'importance':bundle.importance.to_dict('records'),'artifact_roundtrip_verified':True,
            'train_laps':int(bundle.split.query("partition=='train'").lap_uid.nunique()),
            'validation_laps':int(bundle.split.query("partition=='validation'").lap_uid.nunique()),
            'test_laps':int(bundle.split.query("partition=='test'").lap_uid.nunique())}
        print(label,bundle.reports['overall'].to_string(index=False),flush=True)
    results['execution_seconds']=round(time.perf_counter()-started,3)
    (ROOT/'docs/ML_RESULTS_V06.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Offline audit complete in',results['execution_seconds'],'s')


if __name__=='__main__':
    audit()
