"""Threshold-defined observed engineering measurements, without causal coaching."""
from dataclasses import dataclass

import numpy as np

from .alignment import section_supported


@dataclass(frozen=True)
class KPIConfig:
    brake_on_pct: float = 5.
    brake_off_pct: float = 2.
    brake_on_persistence_s: float = .15
    brake_off_persistence_s: float = .1
    throttle_on_pct: float = 20.
    throttle_persistence_s: float = .3
    approach_m: float = 200.
    exit_m: float = 120.
    maximum_release_before_entry_m: float = 30.

    def validate(self):
        if not np.isfinite(list(self.__dict__.values())).all() or min(self.__dict__.values()) <= 0:
            raise ValueError('KPI thresholds/persistence must be finite and positive')
        if not self.brake_off_pct < self.brake_on_pct <= 100 or self.throttle_on_pct > 100:
            raise ValueError('Invalid pedal hysteresis thresholds')


# name: (unit, engineering definition, source channels)
SPECS = {
    'braking_event_count':('count','Confirmed approach events uniquely assigned to the first eligible following reference apex; spanning phases remain uncertain',['brake_pct']),
    'brake_onset_position_m':('m','First observed sample reaching configured brake-on threshold of the unique confirmed approach event, on common reference',['brake_pct','pos_x','pos_y']),
    'brake_release_position_m':('m','First observed sample below the configured brake-off threshold of a sustained release',['brake_pct','pos_x','pos_y']),
    'braking_distance_m':('m','Observed driven XY distance during the unique braking event',['brake_pct','pos_x','pos_y']),
    'braking_duration_s':('s','Observed onset-to-release time of the unique braking event',['brake_pct','lap_elapsed_s']),
    'maximum_brake_pct':('%','Maximum source brake input in the unique braking event',['brake_pct']),
    'mean_brake_pct':('%','Left-hold observed-time mean input during the unique braking event',['brake_pct']),
    'speed_at_brake_onset_kmh':('km/h','Source speed at the observed event onset sample',['brake_pct','speed_kmh']),
    'speed_at_brake_release_kmh':('km/h','Source speed at the observed release sample',['brake_pct','speed_kmh']),
    'brake_onset_to_apex_m':('m','Forward common-reference distance from brake onset to reference weighted apex proxy',['brake_pct','pos_x','pos_y']),
    'trail_braking_proxy_duration_s':('s','Observed brake>=on-threshold overlap from geometric corner entry to common apex; input proxy, not tyre-force inference',['brake_pct']),
    'speed_at_apex_kmh':('km/h','Speed interpolated from fresh observed samples at the common reference apex proxy',['speed_kmh']),
    'minimum_corner_speed_kmh':('km/h','Minimum observed speed within reference corner time boundaries',['speed_kmh']),
    'minimum_speed_position_m':('m','Common reference projection of that minimum-speed observation',['speed_kmh','pos_x','pos_y']),
    'entry_speed_kmh':('km/h','Observed/bracketed speed at reference corner entry',['speed_kmh']),
    'exit_speed_kmh':('km/h','Observed/bracketed speed at reference corner exit',['speed_kmh']),
    'mean_corner_speed_kmh':('km/h','Left-hold observed-time mean speed within the reference corner',['speed_kmh']),
    'minimum_trajectory_radius_m':('m','Inverse maximum absolute curvature of this lap smoothed metric trajectory in the reference corner',['pos_x','pos_y']),
    'maximum_trajectory_curvature_1_m':('1/m','Maximum absolute geometric curvature of this lap within the reference corner',['pos_x','pos_y']),
    'corner_traversal_time_s':('s','Difference of aligned boundary clock values; includes stationary dwell',['lap_elapsed_s','pos_x','pos_y']),
    'peak_lateral_acceleration_g':('g','Maximum observed absolute lateral source acceleration with declared g units',['g_lat']),
    'mean_absolute_lateral_acceleration_g':('g','Left-hold observed-time mean absolute lateral acceleration',['g_lat']),
    'braking_to_cornering_transition_s':('s','First sustained |lateral g|>=0.5 for .15 s in corner, minus unique brake release time',['g_lat','brake_pct']),
    'steering_at_apex':('steering unit','Original-convention steering input at the common apex proxy',['steering']),
    'peak_absolute_steering':('steering unit','Peak observed absolute steering input within the corner',['steering']),
    'steering_range':('steering unit','Observed maximum minus minimum steering input within corner',['steering']),
    'mean_absolute_steering':('steering unit','Left-hold observed-time mean absolute steering input',['steering']),
    'steering_total_variation':('steering unit','Sum of absolute source steering increments in corner',['steering']),
    'steering_rms_rate':('steering unit/s','Square root of duration-weighted squared steering rate; source convention, not a skill score',['steering','lap_elapsed_s']),
    'throttle_at_apex_pct':('%','Observed/bracketed throttle at the common weighted apex proxy',['throttle_pct']),
    'throttle_after_apex_delay_s':('s','First sustained >=threshold throttle after apex minus apex time; zero if already sustained there',['throttle_pct']),
    'throttle_after_apex_distance_m':('m','Common-reference forward distance to that sustained application',['throttle_pct','pos_x','pos_y']),
    'first_sustained_throttle_after_minimum_position_m':('m','First sustained application after the observed corner minimum-speed region',['throttle_pct','speed_kmh']),
    'maximum_exit_throttle_pct':('%','Maximum observed throttle between common apex and corner exit',['throttle_pct']),
    'mean_exit_acceleration_g':('g','Observed-time mean longitudinal source acceleration between apex and exit',['g_lon']),
}


def channel(lap, name):
    accepted = {'speed_kmh':('km/h',), 'brake_pct':('%',), 'throttle_pct':('%',),
                'steering':('deg','rad','°'), 'g_lat':('g','G'), 'g_lon':('g','G')}
    if name not in lap.frame or lap.units.get(name) not in accepted.get(name, (lap.units.get(name),)):
        return None
    y = lap.frame[name].to_numpy(float).copy()
    if name in ('brake_pct','throttle_pct','speed_kmh'):
        limit = 500 if name=='speed_kmh' else 100
        y[(y < -1e-6) | (y > limit+1e-6)] = np.nan
    return y


def confirmed_events(t, y, config=KPIConfig()):
    """Full source-clock hysteresis; missing/gapped observations censor events."""
    if y is None:
        return []
    events, onset, low, active = [], None, None, None
    for i, value in enumerate(y):
        invalid = not np.isfinite(value) or (i and (t[i]-t[i-1] > .2 or t[i] < t[i-1]))
        if invalid:
            if active is not None:
                events.append(dict(onset_index=active, release_index=None, censored=True))
            onset = low = active = None
            continue
        if active is None:
            if value >= config.brake_on_pct:
                if onset is None:
                    onset = i
                if t[i]-t[onset] >= config.brake_on_persistence_s-1e-9:
                    active = onset
            else:
                onset = None
        elif value <= config.brake_off_pct:
            if low is None:
                low = i
            if t[i]-t[low] >= config.brake_off_persistence_s-1e-9:
                events.append(dict(onset_index=active, release_index=low, censored=active==0))
                active = onset = low = None
        else:
            low = None
    if active is not None:
        events.append(dict(onset_index=active, release_index=None, censored=True))
    return events


def _weights(t, start, end):
    return np.r_[np.maximum(0., np.minimum(t[1:], end)-np.maximum(t[:-1], start)), 0.]


def _mean(t, y, start, end, absolute=False, seam=None):
    if y is None or end <= start:
        return None
    w = _weights(t, start, end)
    if seam is not None:
        w[:-1][(t[:-1] < seam) & (t[1:] >= seam)] = 0.
    good = np.isfinite(y)
    if w.sum() <= 0 or w[good].sum()/max(end-start, 1e-12) < .99:
        return None
    return float(np.average(np.abs(y[good]) if absolute else y[good], weights=w[good]))


def _at(t, y, value):
    if y is None or value < t[0]-1e-9 or value > t[-1]+1e-9:
        return None
    i = min(len(t)-1, int(np.searchsorted(t, value, side='right'))-1)
    if abs(t[i]-value) < 1e-8:
        return float(y[i]) if np.isfinite(y[i]) else None
    if i < 0 or i+1 >= len(t) or t[i+1]-t[i] > .2 or not np.isfinite(y[i:i+2]).all():
        return None
    return float(np.interp(value, t[i:i+2], y[i:i+2]))


def _sustained(t, y, begin, end, threshold, persistence):
    if y is None:
        return None
    first = None
    for i in np.flatnonzero((t >= begin) & (t <= end)):
        if np.isfinite(y[i]) and y[i] >= threshold and (i==0 or t[i]-t[i-1] <= .2):
            if first is None:
                first = i
            if t[i]-t[first] >= persistence-1e-9:
                return first
        else:
            first = None
    return None


def associated_braking_events(aligned,geometry,config):
    """Each observed event has one owner, even when approach windows overlap.

    Choose the first eligible apex after onset within the approach bound. A
    phase spanning multiple apex landmarks is retained once and marked uncertain.
    End/start fragments of the same recorded lap never form a synthetic event.
    """
    t=aligned.time;length=geometry.length_m;duration=aligned.lap.duration_s
    corners=[s for s in geometry.sections if s['kind']=='corner']
    assigned={s['section_id']:[] for s in corners}
    events=confirmed_events(t,channel(aligned.lap,'brake_pct'),config)
    for event in events:
        a,b=event['onset_index'],event['release_index']
        candidates=[]
        for section in corners:
            start=section['start_s_m'];apex=section['curvature_weighted_apex_proxy']['s_m']
            apex+=length if section['wraps_start_finish'] and apex<start else 0.
            for shift in ((0,1) if section['wraps_start_finish'] else (0,)):
                onset=float(aligned.progress[a]+shift*length)
                if start-config.approach_m<=onset<=apex:
                    candidates.append((apex-onset,section['section_id'],shift,onset,apex))
        if not candidates:
            continue
        _,owner,shift,onset,apex=min(candidates)
        release=float(aligned.progress[b]+shift*length) if b is not None else None
        reason=None
        if release is not None:
            others=[s['curvature_weighted_apex_proxy']['s_m']+cycle*length
                    for s in corners if s['section_id']!=owner for cycle in (0,1)]
            if any(apex<other<=release for other in others):
                reason='Braking association uncertain: one observed phase spans multiple corner apex landmarks'
        assigned[owner].append(dict(onset_s=onset,onset_t=float(t[a]+shift*duration),
            release_t=float(t[b]+shift*duration) if b is not None else None,
            onset_index=a,release_index=b,censored=event['censored'],shift=shift,
            association_reason=reason))
    return assigned


def _corner_values(aligned, section, geometry, own_geometry, config):
    lap, t = aligned.lap, aligned.time
    length, duration = geometry.length_m, lap.duration_s
    if not section_supported(aligned,section,length):
        return ({name:None for name in SPECS},
                {name:'Unreliable spatial alignment intersects the corner or its timing boundaries' for name in SPECS},
                [],{name:[None,None] for name in SPECS})
    start_s, end_s = section['start_s_m'], section['end_s_m']
    wrap = section['wraps_start_finish']
    start, end = aligned.time_map.at(start_s), aligned.time_map.at(end_s)+(duration if wrap else 0.)
    apex_s = section['curvature_weighted_apex_proxy']['s_m']
    apex = aligned.time_map.at(apex_s)+(duration if wrap and apex_s < start_s else 0.)
    # A locally unwrapped copy supports corners across start/finish. Original
    # temporal observations remain untouched, including every stationary sample.
    tt = np.r_[t, t+duration] if wrap else t
    pp = np.r_[aligned.progress, aligned.progress+length] if wrap else aligned.progress
    yy = {name:channel(lap,name) for name in ('speed_kmh','brake_pct','throttle_pct','steering','g_lat','g_lon')}
    if wrap:
        yy = {name:np.r_[y,y] if y is not None else None for name,y in yy.items()}
    inside = (tt >= start) & (tt <= end)
    values = {name:None for name in SPECS}
    windows = {name:[float(start),float(end)] for name in SPECS}
    explanations = {}
    def measured(name, value):
        values[name] = float(value) if value is not None and np.isfinite(value) else None
    def average(y, first, last, absolute=False):
        return _mean(tt,y,first,last,absolute,seam=duration if wrap else None)
    def at(y, when):
        if wrap and t[-1] < when < duration+t[0]:
            return None
        return _at(tt,y,when)
    speed, brake, throttle, steer, lat, lon = [yy[name] for name in ('speed_kmh','brake_pct','throttle_pct','steering','g_lat','g_lon')]
    measured('corner_traversal_time_s', float(end-start))
    for name, y, when in [('speed_at_apex_kmh',speed,apex),('entry_speed_kmh',speed,start),
                         ('exit_speed_kmh',speed,end),('steering_at_apex',steer,apex),('throttle_at_apex_pct',throttle,apex)]:
        measured(name,at(y,when))
    measured('mean_corner_speed_kmh',average(speed,start,end))
    minimum_index = None
    if speed is not None and np.any(inside & np.isfinite(speed)):
        indices = np.flatnonzero(inside & np.isfinite(speed))
        minimum_index = int(indices[np.argmin(speed[indices])])
        measured('minimum_corner_speed_kmh',float(speed[minimum_index]))
        measured('minimum_speed_position_m',float(pp[minimum_index] % length))
    if own_geometry is not None:
        raw_distance = own_geometry.source_distance
        own_k = np.interp(raw_distance, np.r_[own_geometry.s,own_geometry.length_m],
                          np.r_[own_geometry.curvature,own_geometry.curvature[0]])
        if wrap:
            own_k = np.r_[own_k,own_k]
        if inside.any() and np.isfinite(own_k[inside]).all():
            k = float(np.max(np.abs(own_k[inside])))
            measured('maximum_trajectory_curvature_1_m',k)
            measured('minimum_trajectory_radius_m',1/k if k > 1e-12 else None)
        else:
            explanations['maximum_trajectory_curvature_1_m']=explanations['minimum_trajectory_radius_m']='Own trajectory curvature unavailable within the selected reference window'
    else:
        explanations['maximum_trajectory_curvature_1_m']=explanations['minimum_trajectory_radius_m']='Own trajectory geometry unavailable; curvature is not inferred across missing or jumped coordinates'
    for name,y,absolute,mean in [('peak_lateral_acceleration_g',lat,True,False),
            ('mean_absolute_lateral_acceleration_g',lat,True,True),
            ('peak_absolute_steering',steer,True,False),('mean_absolute_steering',steer,True,True)]:
        if y is not None and np.any(inside & np.isfinite(y)):
            measured(name,_mean(tt,y,start,end,absolute,seam=duration if wrap else None) if mean else float(np.max(np.abs(y[inside & np.isfinite(y)]))))
    if steer is not None:
        mask = inside & np.isfinite(steer)
        if mask.any():
            measured('steering_range',float(np.ptp(steer[mask])))
        dt = np.diff(tt)
        valid = inside[:-1] & inside[1:] & np.isfinite(steer[:-1]) & np.isfinite(steer[1:]) & (dt>0) & (dt<=.2)
        if wrap:
            valid[len(t)-1] = False
        if valid.any():
            dy = np.diff(steer)[valid]
            measured('steering_total_variation',float(np.abs(dy).sum()))
            measured('steering_rms_rate',float(np.sqrt(np.sum(dy**2/dt[valid])/dt[valid].sum())))
    if throttle is not None:
        exit_mask = (tt>=apex) & (tt<=end) & np.isfinite(throttle)
        if exit_mask.any():
            measured('maximum_exit_throttle_pct',float(throttle[exit_mask].max()))
        # Follow the same reference for a short exit window, never the next lap
        # unless this corner itself wraps start/finish.
        # Do not claim the next corner's throttle reapplication as this exit.
        local_end=end_s+(length if wrap else 0.)
        next_entry=min((s['start_s_m']+cycle*length for s in geometry.sections
                        if s['kind']=='corner' and s['section_id']!=section['section_id']
                        for cycle in (0,1,2) if s['start_s_m']+cycle*length>=local_end-1e-8),default=np.inf)
        exit_s=min(local_end+config.exit_m,next_entry,length*(2 if wrap else 1))
        search_end=aligned.time_map.at(exit_s-length if exit_s>length else exit_s)+(duration if exit_s>length else 0.)
        search_end = max(end, min(search_end, float(tt[-1]))) if np.isfinite(search_end) else np.nan
        # A wrapped section joins two observed pieces of this SAME lap, not a
        # verified next-lap event sequence. Never bridge its seam for persistence.
        throttle_end = min(search_end,float(t[-1])) if wrap and apex < duration else search_end
        for name in ('throttle_after_apex_delay_s','throttle_after_apex_distance_m'):
            windows[name]=[float(apex),float(throttle_end)]
        application = _sustained(tt,throttle,apex,throttle_end,config.throttle_on_pct,config.throttle_persistence_s)
        if application is not None:
            already = at(throttle,apex)
            active = already is not None and already >= config.throttle_on_pct and tt[application]-apex <= .2
            measured('throttle_after_apex_delay_s',0. if active else float(tt[application]-apex))
            measured('throttle_after_apex_distance_m',0. if active else float(max(0.,pp[application]-(apex_s+(length if wrap and apex_s<start_s else 0.)))))
        if minimum_index is not None:
            min_end = min(search_end,float(t[-1])) if wrap and tt[minimum_index] < duration else search_end
            windows['first_sustained_throttle_after_minimum_position_m']=[float(tt[minimum_index]),float(min_end)]
            application_min = _sustained(tt,throttle,tt[minimum_index],min_end,config.throttle_on_pct,config.throttle_persistence_s)
            if application_min is not None:
                measured('first_sustained_throttle_after_minimum_position_m',float(pp[application_min] % length))
    measured('mean_exit_acceleration_g',_mean(tt,lon,apex,end,seam=duration if wrap else None))
    windows['maximum_exit_throttle_pct']=windows['mean_exit_acceleration_g']=[float(apex),float(end)]
    expanded=associated_braking_events(aligned,geometry,config)[section['section_id']]
    measured('braking_event_count',float(len(expanded)) if brake is not None else None)
    approach_start = aligned.time_map.at(max(0.,start_s-config.approach_m))
    for name in list(SPECS)[:10]:
        windows[name]=[float(approach_start),float(apex)]
    if len(expanded)==1 and not expanded[0]['censored']:
        event = expanded[0]
        a,b,shift = event['onset_index'],event['release_index'],event['shift']
        onset_t, release_t = event['onset_t'],event['release_t']
        for name in list(SPECS)[1:10]:
            windows[name]=[float(onset_t),float(max(release_t,apex) if name=='brake_onset_to_apex_m' else release_t)]
        measured('brake_onset_position_m',float(aligned.progress[a]))
        measured('brake_release_position_m',float(aligned.progress[b]))
        measured('braking_duration_s',release_t-onset_t)
        if own_geometry is not None:
            measured('braking_distance_m',float(own_geometry.source_distance[b]-own_geometry.source_distance[a]))
        elif {'pos_x','pos_y'}<=set(lap.frame):
            phase_xy=lap.frame[['pos_x','pos_y']].to_numpy(float)[a:b+1]
            if np.isfinite(phase_xy).all():
                measured('braking_distance_m',float(np.linalg.norm(np.diff(phase_xy,axis=0),axis=1).sum()))
        measured('brake_onset_to_apex_m',float(apex_s+(length if wrap and apex_s<start_s else 0.)-event['onset_s']))
        base_brake = channel(lap,'brake_pct')
        measured('maximum_brake_pct',float(np.nanmax(base_brake[a:b+1])))
        measured('mean_brake_pct',_mean(t,base_brake,float(t[a]),float(t[b])))
        measured('speed_at_brake_onset_kmh',_at(t,channel(lap,'speed_kmh'),float(t[a])))
        measured('speed_at_brake_release_kmh',_at(t,channel(lap,'speed_kmh'),float(t[b])))
        release_s=float(aligned.progress[b]+shift*length)
        if start_s-release_s > config.maximum_release_before_entry_m:
            for name in list(SPECS)[1:10]+['braking_to_cornering_transition_s']:
                explanations[name]='Braking association uncertain: observed event released more than configured distance before geometric corner entry'
        if event['association_reason']:
            for name in list(SPECS)[1:10]+['braking_to_cornering_transition_s']:
                explanations[name]=event['association_reason']
        if lat is not None:
            transition_end = min(end,float(t[-1])) if wrap else end
            transition = _sustained(tt,np.abs(lat),start,transition_end,.5,.15)
            windows['braking_to_cornering_transition_s']=[float(min(start,release_t)),float(end)]
            if transition is not None:
                measured('braking_to_cornering_transition_s',float(tt[transition]-release_t))
    else:
        reason = 'No confirmed braking event' if not expanded else 'Multiple or boundary-censored braking events; no unique primary phase'
        for name in list(SPECS)[:10]:
            if name!='braking_event_count':
                explanations[name]=reason
    if brake is not None:
        w = _weights(tt,start,apex)
        if wrap:
            w[len(t)-1] = 0.
        good = np.isfinite(brake)
        if w.sum()>0 and w[good].sum()/w.sum()>=.99:
            measured('trail_braking_proxy_duration_s',float(w[good & (brake>=config.brake_on_pct)].sum()))
    windows['trail_braking_proxy_duration_s']=[float(start),float(apex)]
    if hasattr(aligned.time_map,'supports_time'):
        for name,window in windows.items():
            if not aligned.time_map.supports_time(*window):
                values[name]=None
                explanations[name]='Unreliable spatial alignment intersects the required measurement window'
    return values, explanations, expanded, windows


def compare_corner(reference, analyzed, section, geometry, own_a, own_b, config=KPIConfig()):
    a, ar, events_a, window_a = _corner_values(reference,section,geometry,own_a,config)
    b, br, events_b, window_b = _corner_values(analyzed,section,geometry,own_b,config)
    output = []
    for name,(unit,definition,signals) in SPECS.items():
        av,bv = a[name],b[name]
        steering_metric = unit.startswith('steering unit')
        ua = reference.lap.units.get('steering') if steering_metric else unit
        ub = analyzed.lap.units.get('steering') if steering_metric else unit
        if steering_metric and unit.endswith('/s'):
            ua,ub = str(ua)+'/s',str(ub)+'/s'
        compatible = ua==ub
        spatial=next((reason for reason in (ar.get(name),br.get(name)) if reason and reason.startswith('Unreliable spatial')),None)
        association=spatial or ar.get(name) or br.get(name)
        valid = av is not None and bv is not None and compatible and association is None
        reason = None if valid else (spatial or ('Incompatible source units' if not compatible else association or 'Missing channel/verified unit, insufficient observed support, or no sustained event'))
        difference=bv-av if valid else None
        position=name in ('brake_onset_position_m','brake_release_position_m','minimum_speed_position_m','first_sustained_throttle_after_minimum_position_m')
        if valid and position:
            difference=(difference+geometry.length_m/2)%geometry.length_m-geometry.length_m/2
        output.append(dict(name=name,definition=definition,unit=ua if compatible else 'incompatible',
            reference_value=av,analyzed_value=bv,difference=difference,
            difference_definition='Signed shortest common-reference position difference around the closed lap' if position else 'Analyzed minus reference in compatible source units',
            reference_unit=ua,analyzed_unit=ub,validity='valid' if valid else ('unavailable' if spatial else ('uncertain' if reason and ('Multiple' in reason or 'association' in reason or not compatible) else 'unavailable')),
            explanation=reason, reference_corner_window=dict(start_s_m=section['start_s_m'],end_s_m=section['end_s_m'],wraps=section['wraps_start_finish']),
            temporal_window_s=dict(reference=window_a[name],analyzed=window_b[name]),source_signals=signals,kind='measured_fact'))
    return dict(section_id=section['section_id'],kpis=output,braking_events=dict(reference=events_a,analyzed=events_b))


def whole_lap(lap, config=KPIConfig()):
    t = lap.frame.lap_elapsed_s.to_numpy(float)
    if len(t)<2 or not np.isfinite(t).all() or (np.diff(t)<0).any() or (np.diff(t)>.2).any():
        return dict(status='unavailable',reason='Invalid observed source clock')
    speed,brake,throttle = [channel(lap,name) for name in ('speed_kmh','brake_pct','throttle_pct')]
    return dict(status='valid',window='whole observed lap; no spatial/corner attribution',
        observed_duration_s=float(t[-1]-t[0]),mean_speed_kmh=_mean(t,speed,float(t[0]),float(t[-1])),
        minimum_speed_kmh=float(np.nanmin(speed)) if speed is not None and np.isfinite(speed).any() else None,
        mean_brake_pct=_mean(t,brake,float(t[0]),float(t[-1])),
        mean_throttle_pct=_mean(t,throttle,float(t[0]),float(t[-1])),
        confirmed_braking_events=len(confirmed_events(t,brake,config)) if brake is not None else None)
