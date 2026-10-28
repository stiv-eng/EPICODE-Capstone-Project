"""Pure deterministic analysis with a versioned JSON fact contract."""
from dataclasses import dataclass, asdict
import time

import numpy as np
import pandas as pd

from .data import capabilities
from .geometry import GeometryConfig, build_geometry
from .alignment import AlignmentConfig, align, ambiguity_mask, section_time,section_supported
from .kpis import KPIConfig, compare_corner, whole_lap, channel, _at


@dataclass
class Analysis:
    report: dict
    geometry: object = None
    reference: object = None
    analyzed: object = None
    trace: object = None


def analyze_laps(reference, analyzed, geometry_config=GeometryConfig(), alignment_config=AlignmentConfig(), kpi_config=KPIConfig()):
    started = time.perf_counter()
    geometry_config.validate()
    alignment_config.validate()
    kpi_config.validate()
    report = dict(schema_version='deterministic-lap-analysis/1.0', kind='recorded_observation_analysis',
        status='unavailable', source=dict(reference=reference.identity,analyzed=analyzed.identity),
        laps=dict(reference_id=reference.lap_id,analyzed_id=analyzed.lap_id,
                  reference_time_s=reference.duration_s,analyzed_time_s=analyzed.duration_s,
                  measured_lap_delta_s=analyzed.duration_s-reference.duration_s),
        config=dict(geometry=asdict(geometry_config),alignment=asdict(alignment_config),kpis=asdict(kpi_config)),
        signal_availability=dict(reference=capabilities(reference),analyzed=capabilities(analyzed)),
        coordinate_contract=dict(reference=reference.position_provenance,analyzed=analyzed.position_provenance,
                                 reference_frame=reference.coordinate_frame,analyzed_frame=analyzed.coordinate_frame),
        whole_lap=dict(reference=whole_lap(reference,kpi_config),analyzed=whole_lap(analyzed,kpi_config)),
        alignment=dict(status='unavailable',reasons=[]),geometry=None,section_deltas=[],corners=[],
        interpretations=[],policy='Facts and operational proxies only; no input-to-time causal attribution or coaching')
    result = Analysis(report)
    def accounting(complete=False):
        delta=analyzed.duration_s-reference.duration_s
        measured=float(sum(s['delta_s'] for s in report['section_deltas']))
        residual=0. if complete else float(delta-measured)
        report['unallocated_delta']=dict(value_s=residual,required=not complete,
            label='Unallocated Delta — Spatial Alignment Unavailable',kind='accounting_residual',
            independently_measured=False,
            explanation='Measured lap delta minus reliable non-overlapping section contributions; includes withheld sections and uncertain transitions, not an individually measured or causal loss')
        report['reconciliation']=dict(final_delta_s=float(delta),section_sum_delta_s=measured,
            unallocated_delta_s=residual,error_s=float(measured+residual-delta),
            tolerance_s=alignment_config.numerical_tolerance_s,
            interpretation='Accounting conservation to independently verified full-lap timing, not proof of spatial accuracy or causal loss')
    def unavailable(reason):
        report['alignment']['reasons'].append(reason)
        accounting()
        report['runtime_s'] = time.perf_counter()-started
        return result
    if any(reference.identity.get(key) != analyzed.identity.get(key) for key in ('track_id','car_id')):
        return unavailable('Circuit or vehicle identity differs')
    if not reference.coordinate_frame or reference.coordinate_frame != analyzed.coordinate_frame:
        return unavailable('A compatible declared metric coordinate frame is unavailable')
    if any(lap.units.get('pos_x') != 'm' or lap.units.get('pos_y') != 'm' for lap in (reference,analyzed)):
        return unavailable('Metric horizontal coordinate units are required')
    f=reference.frame
    if {'pos_x','pos_y','lap_elapsed_s'}<=set(f) and len(f):
        last=f.iloc[-1];gap=reference.duration_s-float(last.lap_elapsed_s)
        if np.isfinite([last.pos_x,last.pos_y,gap]).all() and -.001<=gap<=alignment_config.boundary_time_tolerance_s:
            report['finish_marker']=dict(xy=[float(last.pos_x),float(last.pos_y)],
                observed_time_s=float(last.lap_elapsed_s),verified_boundary_time_s=reference.duration_s,
                boundary_gap_s=gap,kind='recorded_near_finish_observation',official_line=False,
                explanation='Last observed reference position within the existing verified timing-boundary tolerance; no official line or exact finish position inferred')
    try:
        geometry = build_geometry(reference.frame[['pos_x','pos_y']].to_numpy(float),geometry_config)
    except (KeyError,ValueError) as exc:
        return unavailable('Reference geometry: '+str(exc))
    result.geometry = geometry
    report['geometry'] = dict(length_m=geometry.length_m,closed=geometry.closed,quality=geometry.quality,
        reference_lap_id=reference.lap_id,sections=geometry.sections,
        apex_policy='curvature_weighted_apex_proxy; reference location shared by both laps; not a verified track-boundary apex')
    if not geometry.closed:
        return unavailable('Open reference geometry: no cyclic lap alignment or complete circuit decomposition')
    try:
        own_b = geometry if reference is analyzed else build_geometry(analyzed.frame[['pos_x','pos_y']].to_numpy(float),geometry_config)
    except (KeyError,ValueError) as exc:
        own_b=None
        report['own_geometry_limitation']=str(exc)
    complete_geometry=own_b is not None and own_b.closed
    coordinates=analyzed.frame[['pos_x','pos_y']].to_numpy(float) if {'pos_x','pos_y'}<=set(analyzed.frame) else np.empty((0,2))
    witnessed_closure=len(coordinates)>1 and np.isfinite(coordinates[[0,-1]]).all() and np.linalg.norm(coordinates[0]-coordinates[-1])<=geometry_config.closure_tolerance_m
    ambiguous = ambiguity_mask(geometry,alignment_config)
    a=align(reference,geometry,alignment_config,ambiguous)
    b=align(analyzed,geometry,alignment_config,ambiguous,partial_only=not complete_geometry,allow_boundaries=bool(witnessed_closure))
    result.reference,result.analyzed = a,b
    complete=complete_geometry and a.quality['status']=='valid' and b.quality['status']=='valid'
    report['alignment'] = dict(status='valid' if complete else ('partial' if a.time_map and b.time_map else 'unavailable'),
        reasons=a.quality['reasons']+b.quality['reasons'],reference=a.quality,analyzed=b.quality,
        method='Sequential segment projection onto the same reference XY; nonlocal-branch ambiguity audit')
    if not a.time_map or not b.time_map:
        accounting()
        report['runtime_s'] = time.perf_counter()-started
        return result
    domains=lambda aligned: ([(0.,geometry.length_m)] if aligned.quality['status']=='valid' else
                             [(r['start_s_m'],r['end_s_m']) for r in aligned.time_map.runs])
    common=sorted((max(x0,y0),min(x1,y1)) for x0,x1 in domains(a) for y0,y1 in domains(b)
                  if min(x1,y1)-max(x0,y0)>1e-8)
    report['alignment']['common_valid_regions']=[dict(start_s_m=x0,end_s_m=x1) for x0,x1 in common]
    report['withheld_sections']=[]
    def measured_section(section,start,end,identifier,wrap=False,clipped=False):
        window=dict(section,start_s_m=start,end_s_m=end,wraps_start_finish=wrap)
        ta,tb=section_time(a,window,geometry.length_m),section_time(b,window,geometry.length_m)
        item=dict(section_id=identifier,kind=section['kind'],start_s_m=start,end_s_m=end,
            wraps_start_finish=wrap,reference_time_s=ta,analyzed_time_s=tb,delta_s=tb-ta,validity='valid')
        if clipped:
            item.update(parent_section_id=section['section_id'],partial_section=True)
        report['section_deltas'].append(item)
    for section in geometry.sections:
        ta,tb = section_time(a,section,geometry.length_m),section_time(b,section,geometry.length_m)
        if ta is not None and tb is not None:
            measured_section(section,section['start_s_m'],section['end_s_m'],section['section_id'],section['wraps_start_finish'])
        else:
            pieces=[(section['start_s_m'],geometry.length_m),(0.,section['end_s_m'])] if section['wraps_start_finish'] else [(section['start_s_m'],section['end_s_m'])]
            fragment=0
            for first,last in pieces:
                cursor=first
                supported=[(max(first,lo),min(last,hi)) for lo,hi in common if min(last,hi)-max(first,lo)>1e-8]
                for lo,hi in supported+[(last,last)]:
                    if lo-cursor>1e-8:
                        report['withheld_sections'].append(dict(section_id=section['section_id'],kind=section['kind'],
                            start_s_m=cursor,end_s_m=lo,wraps_start_finish=False,validity='unavailable',
                            reason='Unreliable correspondence or transition; no individual time contribution, included only in combined residual'))
                    if hi-lo>1e-8:
                        fragment+=1
                        measured_section(section,lo,hi,section['section_id']+'.'+str(fragment),clipped=True)
                    cursor=hi
        if section['kind']=='corner':
            report['corners'].append(compare_corner(a,b,section,geometry,geometry,own_b,kpi_config))
    accounting(complete)
    if abs(report['reconciliation']['error_s']) > alignment_config.numerical_tolerance_s:
        report['status']='unavailable'
        report['alignment']['status']='unavailable'
        report['alignment']['reasons'].append('Section times do not reconcile with witnessed full-lap timing')
        report['section_deltas'],report['corners']=[],[]
        accounting()
    else:
        report['status']='valid' if complete else ('partial' if report['section_deltas'] else 'unavailable')
    grid = np.r_[geometry.s,geometry.length_m]
    result.trace = pd.DataFrame(dict(reference_s_m=grid,reference_time_s=a.time_map.at(grid),analyzed_time_s=b.time_map.at(grid)))
    result.trace['delta_s'] = result.trace.analyzed_time_s-result.trace.reference_time_s
    report['runtime_s'] = time.perf_counter()-started
    return result


def json_facts(analysis):
    """Sanitize optional nonfinite scalars without converting missing values to zero."""
    def clean(value):
        if isinstance(value,dict):
            return {str(key):clean(item) for key,item in value.items()}
        if isinstance(value,(list,tuple,np.ndarray)):
            return [clean(item) for item in value]
        if isinstance(value,(float,np.floating)):
            return float(value) if np.isfinite(value) else None
        if isinstance(value,(bool,np.bool_)):
            return bool(value)
        if isinstance(value,(int,np.integer)):
            return int(value)
        return value
    return clean(analysis.report)
