"""Sequential projection to one shared trajectory, never own-distance scaling."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AlignmentConfig:
    max_offset_m: float = 12.
    reverse_tolerance_m: float = 3.
    boundary_margin_m: float = 20.
    max_clock_gap_s: float = .2
    boundary_time_tolerance_s: float = .1
    ambiguous_separation_m: float = 25.
    ambiguous_distance_m: float = 3.
    numerical_tolerance_s: float = 1e-6

    def validate(self):
        if not np.isfinite(list(self.__dict__.values())).all() or min(self.__dict__.values()) <= 0:
            raise ValueError('Alignment parameters must be finite and positive')


class TimeMap:
    """Arrival/departure inverse with retained stationary dwell and timing anchors.

    At an internal repeated position, the value is right-continuous departure.
    Between positions, interpolate departure -> next arrival. Thus a stop is a
    time jump, not lost samples or smearing over a whole corner. Lap boundaries
    are witnessed clock anchors (0,T); they are not invented sensor packets.
    """
    def __init__(self, s, t, length, duration):
        self.length, self.duration = float(length), float(duration)
        self.s = np.clip(np.maximum.accumulate(s), 0., length)
        self.t = np.clip(np.asarray(t, float), 0., duration)
        ss, tt = np.r_[0., self.s, length], np.r_[0., self.t, duration]
        starts = np.r_[0, np.flatnonzero(np.diff(ss) > 1e-8)+1]
        ends = np.r_[starts[1:]-1, len(ss)-1]
        self.unique, self.arrival, self.departure = ss[starts], tt[starts], tt[ends]
        self.repeated_progress_time_s = float(np.sum(np.maximum(0., self.departure-self.arrival)))

    def at(self, s):
        query = np.asarray(s, float)
        q = np.clip(query, 0., self.length)
        i = np.clip(np.searchsorted(self.unique, q, side='right')-1, 0, len(self.unique)-2)
        span = self.unique[i+1]-self.unique[i]
        value = self.departure[i]+(q-self.unique[i])/span*(self.arrival[i+1]-self.departure[i])
        exact = np.abs(q-self.unique[i]) < 1e-8
        value = np.where(exact, self.departure[i], value)
        value = np.where(q <= 0., 0., np.where(q >= self.length, self.duration, value))
        return float(value) if value.ndim == 0 else value

    def supports(self,start,end):
        return bool(np.isfinite([start,end]).all() and -1e-7<=start<=end<=self.length+1e-7)


@dataclass
class AlignedLap:
    lap: object
    progress: np.ndarray
    time: np.ndarray
    offsets: np.ndarray
    time_map: TimeMap | None
    quality: dict
    problem_masks: dict | None = None


def _issue(code,mask,values,limit,unit,t,progress):
    indexes=np.flatnonzero(mask)
    if not len(indexes):
        return None
    worst=int(indexes[np.argmax(values[indexes])]) if values is not None else int(indexes[0])
    return dict(code=code,sample_count=len(indexes),first_sample=int(indexes[0]),
        last_sample=int(indexes[-1]),worst_sample=worst,first_time_s=float(t[indexes[0]]),
        last_time_s=float(t[indexes[-1]]),worst_time_s=float(t[worst]),
        worst_reference_s_m=float(progress[worst]) if np.isfinite(progress[worst]) else None,
        maximum_observed=float(values[worst]) if values is not None else None,limit=limit,unit=unit)


def ambiguity_mask(geometry, config=AlignmentConfig()):
    """Flag physically near but progress-distant reference branches in 2D.

    Chunked O(N²) reference-only audit; no huge source-by-reference allocation.
    Crossings/overpasses need extra geometry and are conservatively unavailable.
    """
    xy, s, length = geometry.xy, geometry.s, geometry.length_m
    result = np.zeros(len(s), bool)
    for begin in range(0, len(s), 128):
        spatial = np.sum((xy[begin:begin+128, None, :]-xy[None, :, :])**2, axis=2)
        separation = np.abs(s[begin:begin+128, None]-s[None, :])
        separation = np.minimum(separation, length-separation)
        result[begin:begin+128] = np.any((separation > config.ambiguous_separation_m) &
                                        (spatial < config.ambiguous_distance_m**2), axis=1)
    return result


def align(lap, geometry, config=AlignmentConfig(), ambiguous=None,partial_only=False,allow_boundaries=True):
    config.validate()
    f = lap.frame
    failures = []
    if not geometry.closed:
        failures.append('Reference trajectory is not spatially closed')
    if not {'pos_x', 'pos_y', 'lap_elapsed_s'} <= set(f):
        failures.append('Metric coordinates or source lap clock unavailable')
        return AlignedLap(lap, np.array([]), np.array([]), np.array([]), None, dict(status='unavailable', reasons=failures))
    xy = f[['pos_x', 'pos_y']].to_numpy(float)
    t = f.lap_elapsed_s.to_numpy(float)
    if len(t) < 5 or not np.isfinite(t).all():
        failures.append('Nonfinite/insufficient observed positions or timestamps')
    elif (np.diff(t) < -1e-6).any():
        failures.append('Source clock discontinuity or gap')
    elif t[0] < -.001 or lap.duration_s-t[-1]<-.001:
        failures.append('Witnessed lap timing lacks sufficiently recent boundary observations')
    if failures:
        return AlignedLap(lap, np.array([]), t, np.array([]), None, dict(status='unavailable', reasons=failures))
    t = np.minimum(t, lap.duration_s)
    if (np.diff(t)>config.max_clock_gap_s).any() or t[0]>config.boundary_time_tolerance_s or lap.duration_s-t[-1]>config.boundary_time_tolerance_s:
        reason='Source clock discontinuity or gap' if (np.diff(t)>config.max_clock_gap_s).any() else 'Witnessed lap timing lacks sufficiently recent boundary observations'
        quality=dict(status='unavailable',reasons=[reason],issues=[],observed_samples=len(t))
        recent=t[0]<=config.boundary_time_tolerance_s and lap.duration_s-t[-1]<=config.boundary_time_tolerance_s
        return _recover(lap,geometry,config,ambiguous,quality,{},allow_boundaries and recent)
    if not np.isfinite(xy).all():
        quality=dict(status='unavailable',reasons=['Nonfinite observed positions; spatial gaps are not bridged'],issues=[],observed_samples=len(t))
        return _recover(lap,geometry,config,ambiguous,quality,{},allow_boundaries)
    points, length, count = geometry.xy, geometry.length_m, len(geometry.s)
    h = length/count
    vectors = np.roll(points, -1, axis=0)-points
    vv = np.sum(vectors*vectors, axis=1)
    ambiguous = ambiguity_mask(geometry, config) if ambiguous is None else ambiguous
    progress, offsets = np.empty(len(t)), np.empty(len(t))
    ambiguous_flags=np.zeros(len(t),bool)
    reverse_flags=np.zeros(len(t),bool)
    jump_flags=np.zeros(len(t),bool)
    drawdown=np.zeros(len(t))
    jump_excess=np.zeros(len(t))
    bad_ambiguity, backward, leaps = 0, 0, 0
    previous, maximum = 0., 0.
    back = int(np.ceil(config.reverse_tolerance_m/h))+3
    ahead = max(8, int(np.ceil(100./h)))
    for i, p in enumerate(xy):
        base = int(np.floor(previous/h))
        absolute = np.arange(base-back, base+ahead+1)
        indexes = absolute % count
        starts, v = points[indexes], vectors[indexes]
        u = np.clip(np.sum((p-starts)*v, axis=1)/np.maximum(vv[indexes], 1e-12), 0., 1.)
        distances = np.linalg.norm(p-(starts+u[:, None]*v), axis=1)
        candidate_progress = (absolute+u)*h
        # First sample must belong to the shared finish area. Subsequent samples
        # use sequential continuity, not an unconstrained nearest-point search.
        if i == 0:
            distances[np.abs(candidate_progress) > config.boundary_margin_m] = np.inf
        j = int(np.argmin(distances))
        current = float(candidate_progress[j])
        progress[i], offsets[i] = current, distances[j]
        if ambiguous[indexes[j]]:
            bad_ambiguity += 1
            ambiguous_flags[i]=True
        drawdown[i]=max(0.,maximum-current)
        if maximum-current > config.reverse_tolerance_m:
            backward += 1
            reverse_flags[i]=True
        if i:
            source_step = float(np.linalg.norm(xy[i]-xy[i-1]))
            if current-previous > max(5., 2*source_step+2.):
                leaps += 1
                jump_flags[i]=True
                jump_excess[i]=current-previous-max(5.,2*source_step+2.)
        maximum = max(maximum, current)
        previous = current
    if not np.isfinite(offsets).all() or np.max(offsets) > config.max_offset_m:
        failures.append('Projection too far from reference')
    if bad_ambiguity:
        failures.append('Reference has ambiguous nearby branches at matched observations')
    if backward:
        failures.append('Reverse motion / inconsistent lap direction exceeds tolerance')
    if leaps:
        failures.append('Sequential projection contains implausible progress jumps')
    if abs(progress[0]) > config.boundary_margin_m or abs(length-progress[-1]) > config.boundary_margin_m:
        failures.append('Observed circuit coverage does not match both reference boundaries')
    if np.any(progress > length+config.boundary_margin_m) or np.any(progress < -config.boundary_margin_m):
        failures.append('More than one circuit / invalid progress range')
    coverage_error=np.maximum(0.,np.maximum(-progress,progress-length))
    coverage_error[0]=max(coverage_error[0],abs(progress[0]))
    coverage_error[-1]=max(coverage_error[-1],abs(length-progress[-1]))
    masks=dict(offset=offsets>config.max_offset_m,reverse_progress=reverse_flags,
        ambiguous=ambiguous_flags,progress_jump=jump_flags,coverage=coverage_error>config.boundary_margin_m)
    measurements={'offset':(offsets,config.max_offset_m,'m'),
        'reverse_progress':(drawdown,config.reverse_tolerance_m,'m'),
        'ambiguous':(None,None,''),'progress_jump':(jump_excess,0.,'m beyond source-step allowance'),
        'coverage':(coverage_error,config.boundary_margin_m,'m')}
    issues=[issue for code,mask in masks.items()
            if (issue:=_issue(code,mask,*measurements[code],t,progress)) is not None]
    quality = dict(status='valid' if not failures else 'unavailable', reasons=failures,
        issues=issues,
        observed_samples=len(t), maximum_offset_m=float(np.max(offsets)), p95_offset_m=float(np.percentile(offsets, 95)),
        ambiguous_samples=bad_ambiguity, reverse_samples=backward, implausible_jumps=leaps,
        start_projection_m=float(progress[0]), finish_projection_gap_m=float(length-progress[-1]),
        boundary_clock_gaps_s=[float(t[0]), float(lap.duration_s-t[-1])],
        boundary_policy='Verified (0,T) timing anchors with <=100 ms source coverage and <=20 m spatial margin; no duration/time normalization',
        progress_policy='Projection onto common reference; <=3 m jitter drawdown regularized by running maximum',
        stationary_policy='Repeated progress preserves arrival/departure dwell; internal boundary uses right-continuous departure')
    time_map = None if failures else TimeMap(progress, t, length, lap.duration_s)
    if partial_only and not failures:
        failures.append('Analyzed geometry is not verified for complete spatial coverage')
        quality['status']='unavailable'
        time_map=None
    if time_map:
        quality['repeated_projected_position_time_s'] = time_map.repeated_progress_time_s
        quality['repeated_position_interpretation'] = 'Includes stationary observations, projection plateaus and boundary anchoring; not an independent vehicle-stop detector'
    masks={code:mask for code,mask in masks.items() if mask.any()}
    if time_map is None:
        return _recover(lap,geometry,config,ambiguous,quality,masks,allow_boundaries)
    return AlignedLap(lap, np.clip(np.maximum.accumulate(progress), 0., length), t, offsets, time_map, quality,masks)


def _recover(lap,geometry,config,ambiguous,quality,masks,allow_boundaries):
    from .partial import recover
    ambiguous=ambiguity_mask(geometry,config) if ambiguous is None else ambiguous
    mapping,progress,offsets,valid=recover(lap,geometry,config,ambiguous,allow_boundaries)
    t=np.minimum(lap.frame.lap_elapsed_s.to_numpy(float),lap.duration_s)
    quality['status']='partial' if mapping is not None else 'unavailable'
    quality['valid_spatial_runs']=[] if mapping is None else [
        {k:r[k] for k in ('start_s_m','end_s_m','start_time_s','end_time_s')} for r in mapping.runs]
    quality['recovery_policy']='Unique forward geometric reacquisition, >=3 observations advancing >=2 grid cells; internal boundary guards; no interpolation across holes'
    masks['unreliable']=~valid
    issue=_issue('unreliable',~valid,None,None,'',t,progress)
    if issue is not None:
        quality['issues'].append(issue)
    return AlignedLap(lap,progress,t,offsets,mapping,quality,masks)


def section_supported(aligned,section,length):
    mapping=aligned.time_map
    if mapping is None:
        return False
    start,end=section['start_s_m'],section['end_s_m']
    if section['wraps_start_finish']:
        return mapping.supports(start,length) and mapping.supports(0.,end)
    return mapping.supports(start,end)


def section_time(aligned, section, length):
    mapping = aligned.time_map
    if not section_supported(aligned,section,length):
        return None
    start, end = section['start_s_m'], section['end_s_m']
    if section['wraps_start_finish']:
        return float(mapping.at(length)-mapping.at(start)+mapping.at(end)-mapping.at(0.))
    return float(mapping.at(end)-mapping.at(start))
