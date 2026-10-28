"""Reproduce the actual source/coordinate feasibility audit without ML or fitting."""
import json
import logging

import numpy as np
import pandas as pd

from motorsport.ingestion.barcelona import ROOT,RAW,MANIFEST,load_barcelona_recording,file_sha
from motorsport.ingestion.motec import read_ld
from motorsport.ingestion.gt7_importer import load_gt7_bundle


def main():
    logging.getLogger('streamlit').setLevel(logging.ERROR)
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    sources,laps=[],[]
    for entry in manifest['files']:
        if not entry['path'].endswith('.ld'):
            continue
        header,channels=read_ld(RAW/entry['path'])
        session=load_barcelona_recording(entry['path'])
        selected={name:dict(unit=ch.unit,export_hz=ch.hz,samples=len(ch.values),finite_fraction=float(np.isfinite(ch.values).mean()))
                  for name,ch in channels.items() if name in ('Car Coord X','Car Coord Y','Car Coord Z','Car Pos Norm','Ground Speed',
                    'Brake Pos','Throttle Pos','Steering Angle','Gear','Engine RPM','Lap Time','CG Accel Lateral','CG Accel Longitudinal')}
        sources.append(dict(source=entry['path'],recording_label=entry['recording_label'],channels=selected,
            coordinate_mapping='world X=Car Coord Y, world Y=-Car Coord X, elevation=Car Coord Z',
            coordinate_origin='direct source simulator coordinates, declared metres; no progress/velocity reconstruction'))
        xy=np.c_[channels['Car Coord Y'].values,-channels['Car Coord X'].values]
        for lap in session.laps.laps.itertuples(index=False):
            a,b=int(lap.start_sample),int(lap.end_sample)
            f=session.data.iloc[a:b];t=f.lap_elapsed_s.to_numpy(float)
            positions=xy[a:b];step=np.linalg.norm(np.diff(positions,axis=0),axis=1)
            speed=f.speed_kmh.to_numpy(float)/3.6
            integral=float(np.sum(np.diff(t)*(speed[1:]+speed[:-1])*.5))
            laps.append(dict(source=entry['path'],lap_id=int(lap.lap_id),duration_s=float(lap.duration_s),samples=len(f),
                finite_xy=bool(np.isfinite(positions).all()),closure_m=float(np.linalg.norm(positions[-1]-positions[0])),
                length_m=float(step.sum()),maximum_step_m=float(step.max()),zero_distance_steps=int((step<1e-8).sum()),
                xy_to_speed_ratio=float(step.sum()/integral),maximum_clock_gap_s=float(np.diff(t).max()),
                duplicate_clock_steps=int((np.diff(t)==0).sum()),first_x_m=float(positions[0,0]),first_y_m=float(positions[0,1])))
    assert len(laps)==205 and len(sources)==70
    gt=load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c')
    gt_rows=[]
    for lap in gt.laps.laps.itertuples(index=False):
        f=gt.data.iloc[lap.start_sample:lap.end_sample]
        p=f[['pos_x','pos_y']].to_numpy(float);t=f.lap_elapsed_s.to_numpy(float)
        gt_rows.append(dict(lap_id=int(lap.lap_id),duration_s=float(lap.duration_s),samples=len(f),
            closure_m=float(np.linalg.norm(p[-1]-p[0])),length_m=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),
            max_clock_gap_s=float(np.diff(t).max())))
    result=dict(audit='Real raw signals; initial feasibility gate documented before geometry implementation',
        baseline_commit='1e91142',manifest_sha256=file_sha(MANIFEST),barcelona_recordings=70,barcelona_laps=205,
        missing_xy_laps=sum(not r['finite_xy'] for r in laps),barcelona_sources=sources,
        coordinate_frame_evidence='Same declared metre channels, plausible closed circuits, finish-area agreement across 70 recordings, observed path distance agrees with integrated ground speed; not surveyed track geometry',
        normalized_progress_decision='Do not use for alignment: exact export interpolation/latency/reverse contract unverified',
        gt7=dict(validated_laps=8,coordinate_source='packet world X/Z, metre declaration in pinned adapter',
            derived_signals=['speed_kmh','distance_m','steer_angle_l','steer_angle_r'],
            unverified_signals=['derived steering calibration','sway/surge physical acceleration units'],laps=gt_rows),
        original_attachment=dict(validated_complete_laps=0,geometry='integrated-position provenance unverified; unsupported for circuit-section comparison'))
    (ROOT/'docs/DATA_FEASIBILITY_V090.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    pd.DataFrame(laps).to_csv(ROOT/'docs/BARCELONA_SPATIAL_AUDIT_V090.csv',index=False,lineterminator='\n')
    print('Audited 70 Barcelona recordings /205 laps and eight GT7 laps; original sources unchanged.',flush=True)


if __name__=='__main__':
    main()
