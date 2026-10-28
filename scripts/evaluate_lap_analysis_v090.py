"""Fixed real-source engineering validation; no model fitting or target selection."""
import json
import logging
import time

import numpy as np
import pandas as pd

from motorsport.ingestion.barcelona import ROOT,MANIFEST,load_barcelona_recording,file_sha
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.lap_analysis.data import spatial_source,from_session
from motorsport.lap_analysis.geometry import build_geometry,GeometryConfig
from motorsport.lap_analysis.analysis import analyze_laps,json_facts

LABELS=('20240229_HC','20240304_AB','20240325_WL','20240405_NH')
OUT=ROOT/'artifacts/v090'


def main():
    logging.getLogger('streamlit').setLevel(logging.ERROR)
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    selections=[]
    for label in LABELS:
        entry=next(e for e in manifest['files'] if e['path'].endswith('.ld') and e['recording_label']==label)
        selections.append((label,'barcelona:'+entry['path'],load_barcelona_recording(entry['path'])))
    selections.append(('GT7','gt7',load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')))
    cases,metrics,sensitivity=[],[],[]
    references=[]
    for label,key,session in selections:
        spatial=spatial_source(session,key,ROOT)
        ids=session.laps.laps.sort_values('duration_s').lap_id.tolist()
        reference=from_session(session,ids[0],spatial)
        references.append((label,reference))
        for radius in (100.,150.,200.):
            g=build_geometry(reference.frame[['pos_x','pos_y']],GeometryConfig(radius_threshold_m=radius))
            sensitivity.append(dict(source=label,radius_m=radius,corners=sum(s['kind']=='corner' for s in g.sections),sections=len(g.sections)))
        fixed_sections=None
        for lap_id in ids:
            analyzed=from_session(session,lap_id,spatial)
            start=time.perf_counter();result=analyze_laps(reference,analyzed);elapsed=time.perf_counter()-start
            report=json_facts(result)
            file=OUT/f'facts-{label}-{lap_id}.json'
            file.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            if report['geometry']:
                if fixed_sections is None:fixed_sections=report['geometry']['sections']
                assert report['geometry']['sections']==fixed_sections
            reconciliation=report.get('reconciliation',{})
            case=dict(source=label,reference_lap=str(reference.lap_id),analyzed_lap=str(lap_id),
                self_comparison=str(lap_id)==reference.lap_id,status=report['status'],
                reference_time_s=reference.duration_s,analyzed_time_s=analyzed.duration_s,
                measured_delta_s=analyzed.duration_s-reference.duration_s,runtime_s=elapsed,
                corners=sum(s['kind']=='corner' for s in result.geometry.sections) if result.geometry else 0,
                sections=len(result.geometry.sections) if result.geometry else 0,
                reconciliation_error_s=reconciliation.get('error_s'),
                p95_offset_m=report['alignment'].get('analyzed',{}).get('p95_offset_m'),
                maximum_offset_m=report['alignment'].get('analyzed',{}).get('maximum_offset_m'),
                reasons='; '.join(report['alignment']['reasons']),facts_path=file.relative_to(ROOT).as_posix(),facts_sha256=file_sha(file))
            cases.append(case)
            for corner in report['corners']:
                for kpi in corner['kpis']:
                    metrics.append(dict(source=label,reference_lap=reference.lap_id,analyzed_lap=str(lap_id),
                        section_id=corner['section_id'],**{key:kpi[key] for key in ('name','unit','reference_value','analyzed_value','difference','validity','explanation')}))
            print(label,lap_id,report['status'],f'{elapsed:.3f}s',case['reasons'],flush=True)
    # One explicitly identified cross-recording same-domain test, not a search.
    cross=analyze_laps(references[1][1],references[3][1])
    cross_report=json_facts(cross)
    (OUT/'facts-cross-recording.json').write_text(json.dumps(cross_report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    table=pd.DataFrame(cases)
    table.to_csv(ROOT/'docs/LAP_ANALYSIS_CASES_V090.csv',index=False,lineterminator='\n')
    metric_table=pd.DataFrame(metrics)
    metric_table.to_csv(ROOT/'docs/KPI_MEASUREMENTS_V090.csv',index=False,lineterminator='\n')
    pd.DataFrame(sensitivity).to_csv(ROOT/'docs/CORNER_SENSITIVITY_V090.csv',index=False,lineterminator='\n')
    valid=table[table.status=='valid']
    distinct=table[~table.self_comparison]
    result=dict(baseline_commit='1e91142',case_policy='All validated laps in the first source file for four fixed recording labels, plus all eight GT7 laps; fastest lap in each source is a deterministic reference. Self checks separated. No rejection is hidden.',
        labels=list(LABELS),cases=len(table),valid_cases=len(valid),unavailable_cases=int((table.status!='valid').sum()),
        distinct_pairs=len(distinct),valid_distinct_pairs=int((distinct.status=='valid').sum()),
        maximum_reconciliation_error_s=float(valid.reconciliation_error_s.abs().max()) if len(valid) else None,
        runtime=dict(median_s=float(table.runtime_s.median()),p95_s=float(table.runtime_s.quantile(.95)),maximum_s=float(table.runtime_s.max()),
                     scope='cold deterministic engine including geometry, ambiguity audit, both projections and all KPIs; no browser rendering'),
        cross_recording=dict(reference=references[1][0],analyzed=references[3][0],status=cross_report['status'],quality=cross_report['alignment'],reconciliation=cross_report.get('reconciliation')),
        kpi_validity=metric_table.groupby(['source','validity']).size().rename('measurements').reset_index().to_dict('records'),
        evidence_sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in [ROOT/'docs/LAP_ANALYSIS_CASES_V090.csv',ROOT/'docs/KPI_MEASUREMENTS_V090.csv',ROOT/'docs/CORNER_SENSITIVITY_V090.csv']})
    (ROOT/'docs/MEASUREMENTS_V090.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('cross_recording','kpi_validity','evidence_sha256')},indent=2))


if __name__=='__main__':
    main()
