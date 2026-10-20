"""Reproduce measured v0.5 analytics and capability evidence for local datasets."""
import hashlib
import json
from pathlib import Path

from motorsport.pipeline import load_session
from motorsport.processing.schema import SUPPLIED_V04
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.analytics.overview import overview_metrics
from motorsport.analytics.driver_inputs import driver_metrics
from motorsport.analytics.readiness import assess_capabilities,lap_features

ROOT=Path(__file__).resolve().parents[1]


def audit():
    evidence={}
    for name,path in [('original',ROOT/'data/raw/telemetry.parquet'),
                      ('gt7',ROOT/'data/raw/gt7_trial_mountain_962c')]:
        if not path.exists():
            evidence[name]={'available':False};continue
        session=load_gt7_bundle(path) if path.is_dir() else load_session(path,profile=SUPPLIED_V04)
        metrics,events=driver_metrics(session.data)
        evidence[name]={'available':True,'session_id':session.metadata['session_id'],
            'raw_shape':list(session.raw.shape),'overview':overview_metrics(session.data),
            'driver_default_thresholds':{'throttle_pct':90,'brake_pct':5,'overlap_throttle_pct':5,'min_event_s':.1},
            'driver_metrics':metrics,'source_quality':{k:v for k,v in session.raw_quality.items() if k!='channels'},
            'validated_laps':session.laps.laps.to_dict('records'),
            'rejected_laps':session.metadata.get('lap_rejections',[]),
            'capabilities':assess_capabilities(session),'candidate_lap_features':lap_features(session).to_dict('records')}
        if path.is_file():
            with path.open('rb') as stream:evidence[name]['sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
    output=ROOT/'docs/DATASET_MEASUREMENTS_V05.json'
    output.write_text(json.dumps(evidence,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print('Measured evidence:',output)
    for name,data in evidence.items():
        if data['available']:
            print(name,data['raw_shape'],'validated laps',len(data['validated_laps']),
                  'events',data['driver_metrics']['observed_events'],data['driver_metrics']['complete_events'])


if __name__=='__main__':
    audit()
