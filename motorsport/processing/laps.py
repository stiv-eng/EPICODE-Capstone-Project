"""Validate complete laps from agreeing counters and progress, never XY alone."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class LapResult:
    available: bool
    reason: str
    laps: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(
        columns=['lap_id', 'start_sample', 'end_sample', 'start_s', 'end_s', 'duration_s']))


def detect_laps(frame, min_lap_s=20., max_lap_s=600.):
    required = {'elapsed_s', 'completed_laps', 'lap_progress'}
    if not required.issubset(frame):
        return LapResult(False, 'Validated laps require time, completed_laps and lap_progress; position alone is insufficient.')
    t, counter, progress = (pd.to_numeric(frame[c], errors='coerce').to_numpy(dtype=float, na_value=np.nan)
                            for c in ['elapsed_s', 'completed_laps', 'lap_progress'])
    if len(t) < 3 or not np.isfinite(np.c_[t, counter, progress]).all():
        return LapResult(False, 'Lap channels contain missing/invalid samples or too few observations.')
    if np.unique(counter).size < 2 or np.unique(progress).size < 2:
        return LapResult(False, 'Lap counter/progress are constant: complete laps cannot be validated.')
    dt, dc = np.diff(t), np.diff(counter)
    if (dt <= 0).any() or (counter < 0).any() or (counter != np.floor(counter)).any() or not np.isin(dc, [0, 1]).all():
        return LapResult(False, 'Lap validation requires strictly increasing time and consecutive integer counters.')
    if ((progress < 0) | (progress > 1)).any():
        return LapResult(False, 'Lap progress must use explicitly declared 0–1 units.')
    changes = np.flatnonzero(dc == 1) + 1
    resets = np.flatnonzero(np.diff(progress) < -.5) + 1
    if not np.array_equal(changes, resets) or any(progress[i-1] < .9 or progress[i] > .1 for i in changes):
        return LapResult(False, 'Counter increments and near-finish progress resets disagree.')
    # The leading and trailing fragments have no pair of witnessed boundaries.
    gap_limit = max(1., float(np.median(dt)) * 10)
    laps = []
    for start, end in zip(changes[:-1], changes[1:]):
        duration = t[end] - t[start]
        if min_lap_s <= duration <= max_lap_s and np.max(dt[start:end]) <= gap_limit:
            laps.append({'lap_id': int(counter[start]), 'start_sample': int(start),
                         'end_sample': int(end), 'start_s': t[start],
                         'end_s': t[end], 'duration_s': duration})
    if not laps:
        return LapResult(False, 'No complete lap has two witnessed, consistent boundaries and a plausible duration without large gaps.')
    return LapResult(True, 'Complete laps validated from agreeing counter and progress transitions. Leading/trailing fragments and laps with gaps are excluded.', pd.DataFrame(laps))
