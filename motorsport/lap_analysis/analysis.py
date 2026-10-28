"""Pure deterministic analysis with a versioned JSON fact contract."""
from dataclasses import dataclass, asdict
import time

import numpy as np
import pandas as pd

from .data import capabilities
from .geometry import GeometryConfig, build_geometry
from .alignment import AlignmentConfig, align, ambiguity_mask, section_time
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
    def unavailable(reason):
        report['alignment']['reasons'].append(reason)
        report['runtime_s'] = time.perf_counter()-started
        return result
    if any(reference.identity.get(key) != analyzed.identity.get(key) for key in ('track_id','car_id')):
        return unavailable('Circuit or vehicle identity differs')
    if not reference.coordinate_frame or reference.coordinate_frame != analyzed.coordinate_frame:
        return unavailable('A compatible declared metric coordinate frame is unavailable')
    if any(lap.units.get('pos_x') != 'm' or lap.units.get('pos_y') != 'm' for lap in (reference,analyzed)):
        return unavailable('Metric horizontal coordinate units are required')
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
        return unavailable('Analyzed geometry: '+str(exc))
    if not own_b.closed:
        return unavailable('Analyzed trajectory does not satisfy spatial closure tolerance')
    ambiguous = ambiguity_mask(geometry,alignment_config)
    a,b = align(reference,geometry,alignment_config,ambiguous),align(analyzed,geometry,alignment_config,ambiguous)
    result.reference,result.analyzed = a,b
    report['alignment'] = dict(status='valid' if a.time_map and b.time_map else 'unavailable',
        reasons=a.quality['reasons']+b.quality['reasons'],reference=a.quality,analyzed=b.quality,
        method='Sequential segment projection onto the same reference XY; nonlocal-branch ambiguity audit')
    if not a.time_map or not b.time_map:
        report['runtime_s'] = time.perf_counter()-started
        return result
    for section in geometry.sections:
        ta,tb = section_time(a,section,geometry.length_m),section_time(b,section,geometry.length_m)
        report['section_deltas'].append(dict(section_id=section['section_id'],kind=section['kind'],
            start_s_m=section['start_s_m'],end_s_m=section['end_s_m'],wraps_start_finish=section['wraps_start_finish'],
            reference_time_s=ta,analyzed_time_s=tb,delta_s=tb-ta,validity='valid'))
        if section['kind']=='corner':
            report['corners'].append(compare_corner(a,b,section,geometry,geometry,own_b,kpi_config))
    delta = analyzed.duration_s-reference.duration_s
    error = float(sum(s['delta_s'] for s in report['section_deltas'])-delta)
    report['reconciliation'] = dict(final_delta_s=float(b.time_map.at(geometry.length_m)-a.time_map.at(geometry.length_m)),
        section_sum_delta_s=float(sum(s['delta_s'] for s in report['section_deltas'])),
        error_s=error,tolerance_s=alignment_config.numerical_tolerance_s,
        interpretation='Numerical reconciliation to witnessed lap timing anchors, not independent validation of sub-section alignment accuracy')
    if abs(error) > alignment_config.numerical_tolerance_s:
        report['status']='unavailable'
        report['alignment']['status']='unavailable'
        report['alignment']['reasons'].append('Section times do not reconcile with witnessed full-lap timing')
        report['section_deltas'],report['corners']=[],[]
    else:
        report['status']='valid'
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
