"""Metric geometry independent of source time, speed and completed lap duration."""
from dataclasses import dataclass, asdict

import numpy as np


@dataclass(frozen=True)
class GeometryConfig:
    spacing_m: float = 1.5
    radius_threshold_m: float = 150.
    smoothing_m: float = 9.
    min_corner_length_m: float = 12.
    merge_gap_m: float = 6.
    closure_tolerance_m: float = 8.
    maximum_source_step_m: float = 15.

    def validate(self):
        values = np.asarray(list(asdict(self).values()), float)
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError('Geometry parameters must be finite and positive')
        if not .25 <= self.spacing_m <= 10.:
            raise ValueError('Spatial resolution must be between 0.25 and 10 m')


@dataclass
class Geometry:
    s: np.ndarray
    xy: np.ndarray
    curvature: np.ndarray
    length_m: float
    closed: bool
    source_distance: np.ndarray
    sections: list
    quality: dict
    config: GeometryConfig


def three_point_curvature(xy, closed=False):
    xy = np.asarray(xy, float)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 3 or not np.isfinite(xy).all():
        raise ValueError('At least three finite X/Y points are required')
    a, b, c = np.roll(xy, 1, axis=0), xy, np.roll(xy, -1, axis=0)
    ab, bc, ac = b-a, c-b, c-a
    sides = np.linalg.norm(ab, axis=1)*np.linalg.norm(bc, axis=1)*np.linalg.norm(ac, axis=1)
    cross = ab[:, 0]*ac[:, 1]-ab[:, 1]*ac[:, 0]
    result = np.divide(2*cross, sides, out=np.zeros(len(xy)), where=sides > 1e-12)
    if not closed:
        result[[0, -1]] = np.nan
    return result


def _smooth(xy, window, closed):
    # Quadratic Savitzky-Golay weights, computed locally with NumPy only.
    window = min(window, len(xy)-(1 if len(xy) % 2 == 0 else 0))
    if window < 5:
        return xy.copy()
    half = window//2
    offsets = np.arange(-half, half+1, dtype=float)
    kernel = np.linalg.pinv(np.c_[np.ones(window), offsets, offsets**2])[0]
    padded = np.pad(xy, ((half, half), (0, 0)), mode='wrap' if closed else 'edge')
    return np.column_stack([np.convolve(padded[:, i], kernel, mode='valid') for i in (0, 1)])


def interpolate_xy(geometry, s):
    s = np.asarray(s, float)
    if geometry.closed:
        s = s % geometry.length_m
        grid, xy = np.r_[geometry.s, geometry.length_m], np.vstack([geometry.xy, geometry.xy[0]])
    else:
        grid, xy = geometry.s, geometry.xy
    return np.stack([np.interp(s, grid, xy[:, j]) for j in (0, 1)], axis=-1)


def _runs(keys, closed):
    n = len(keys)
    if not n:
        return []
    cuts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1])+1, n]
    runs = [np.arange(a, b) for a, b in zip(cuts[:-1], cuts[1:])]
    if closed and len(runs) > 1 and keys[0] == keys[-1]:
        runs = [np.r_[runs[-1], runs[0]], *runs[1:-1]]
    return runs


def segment(geometry):
    g, cfg = geometry, geometry.config
    count = len(g.s) if g.closed else len(g.s)-1
    widths = np.diff(np.r_[g.s[:count], g.length_m])
    k = np.nan_to_num(g.curvature[:count])
    keys = np.where(np.abs(k) > 1/cfg.radius_threshold_m, np.sign(k).astype(int), 0)
    if g.closed:
        keys[~np.isfinite(g.curvature[:count])]=2
    for run in _runs(keys, g.closed):
        if abs(keys[run[0]])==1 and widths[run].sum() < cfg.min_corner_length_m:
            keys[run] = 0
    # Merge only short straight holes with the SAME signed turning direction.
    for run in _runs(keys, g.closed):
        if keys[run[0]] or widths[run].sum() > cfg.merge_gap_m:
            continue
        left, right = (int(run[0])-1) % count, (int(run[-1])+1) % count
        if (g.closed or (run[0] > 0 and run[-1] < count-1)) and keys[left] == keys[right] and abs(keys[left])==1:
            keys[run] = keys[left]
    sections, counters = [], {'corner':0, 'straight':0, 'boundary':0}
    for run in _runs(keys, g.closed):
        kind = 'boundary' if keys[run[0]]==2 else ('corner' if keys[run[0]] else 'straight')
        counters[kind] += 1
        start = float(g.s[run[0]])
        length = float(widths[run].sum())
        end_unwrapped = start+length
        wraps = end_unwrapped > g.length_m+1e-7
        end = end_unwrapped-g.length_m if wraps else end_unwrapped
        local_s = np.r_[start, start+np.cumsum(widths[run])]
        indexes = np.r_[run, (int(run[-1])+1) % len(g.s)]
        if not g.closed:
            indexes[-1] = min(int(run[-1])+1, len(g.s)-1)
        weights = np.abs(np.nan_to_num(g.curvature[indexes]))
        integrate = lambda y: float(np.sum(np.diff(local_s)*(y[:-1]+y[1:])*.5))
        denominator = integrate(weights)
        apex = integrate(local_s*weights)/denominator if kind == 'corner' and denominator > 1e-12 else None
        maximum = int(run[np.argmax(np.abs(np.nan_to_num(g.curvature[run])))])
        max_k = float(np.max(np.abs(np.nan_to_num(g.curvature[run]))))
        sections.append(dict(section_id={'corner':'C','straight':'S','boundary':'B'}[kind]+f'{counters[kind]:02d}', kind=kind,
            start_s_m=start, end_s_m=float(end), length_m=length, wraps_start_finish=bool(wraps),
            direction=('left' if keys[run[0]] > 0 else 'right') if kind=='corner' else None,
            minimum_radius_m=1/max_k if max_k > 1e-12 else None,
            maximum_curvature_1_m=None if kind=='boundary' else max_k,
            curvature_weighted_apex_proxy=dict(s_m=apex % g.length_m, xy=interpolate_xy(g, apex).tolist()) if apex is not None else None,
            maximum_curvature_point=dict(s_m=float(g.s[maximum]), xy=g.xy[maximum].tolist()) if kind=='corner' else None,
            reference_indices=run.tolist()))
    return sorted(sections, key=lambda section:section['start_s_m'])


def build_geometry(xy, config=GeometryConfig()):
    config.validate()
    xy = np.asarray(xy, float)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 5 or not np.isfinite(xy).all():
        raise ValueError('Geometry requires finite observed X/Y; missing points are not bridged')
    steps = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    if steps.max(initial=0.) > config.maximum_source_step_m:
        raise ValueError('Coordinate jump / spatial acquisition gap exceeds the configured limit')
    source_s = np.r_[0., np.cumsum(steps)]
    keep = np.r_[True, steps > 1e-8]
    points, source_unique = xy[keep], source_s[keep]
    if len(points) < 5 or source_s[-1] < config.spacing_m*4:
        raise ValueError('Stationary or insufficient spatial extent')
    closure = float(np.linalg.norm(points[-1]-points[0]))
    closed = closure <= config.closure_tolerance_m
    length = float(source_s[-1]+(closure if closed else 0.))
    if closed and closure > 1e-8:
        points, source_unique = np.vstack([points, points[0]]), np.r_[source_unique, length]
    if closed:
        count = int(np.ceil(length/config.spacing_m))
        grid = np.arange(count)*length/count
    else:
        grid = np.unique(np.r_[np.arange(0., length, config.spacing_m), length])
    resampled = np.column_stack([np.interp(grid, source_unique, points[:, j]) for j in (0, 1)])
    actual_spacing = float(np.median(np.diff(grid)))
    window = max(1, 2*int(round(config.smoothing_m/actual_spacing/2))+1)
    window = min(window,len(grid)-(1 if len(grid)%2==0 else 0))
    resampled = _smooth(resampled, window, closed)
    curvature = three_point_curvature(resampled, closed)
    masked_seam=False
    if closed and closure>max(1e-8,.1*actual_spacing):
        # Endpoint proximity does not establish a physically smooth closing
        # chord. Different start/finish lateral positions or overlap can create
        # a false hairpin at the seam; withhold its curvature rather than invent
        # a corner or spread a correction along the observed driving line.
        unique_xy=xy[keep]
        forward_start=unique_xy[min(4,len(unique_xy)-1)]-unique_xy[0]
        forward_end=unique_xy[-1]-unique_xy[max(0,len(unique_xy)-5)]
        closing=unique_xy[0]-unique_xy[-1]
        cosine=lambda direction: float(np.dot(closing,direction)/(np.linalg.norm(closing)*max(np.linalg.norm(direction),1e-12)))
        if min(cosine(forward_start),cosine(forward_end))<.8:
            buffer=max(config.smoothing_m,2*closure+2*actual_spacing)
            curvature[(grid<buffer)|(grid>length-buffer)]=np.nan
            masked_seam=True
    geometry = Geometry(grid, resampled, curvature, length, closed, source_s, [],
        dict(status='valid' if closed else 'open', observed_closure_m=closure,
            geometry_duplicate_samples_removed=int((~keep).sum()), temporal_samples_preserved=len(xy),
            actual_spacing_m=actual_spacing, smoothing_points=window,
            seam_curvature_available=not masked_seam,
            seam_curvature_unavailable_samples=int(np.sum(~np.isfinite(curvature))) if closed else 0,
            closure_policy='Observed small endpoint gap closed geometrically only; temporal boundary anchors remain separately identified'), config)
    geometry.sections = segment(geometry)
    return geometry
