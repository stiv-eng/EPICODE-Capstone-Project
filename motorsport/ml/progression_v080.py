"""Causal elapsed-time checkpoints; no target or completed-distance input."""
import numpy as np

from .features import CHECKPOINTS, causal_prefix

VERSION = 'dense-sequence-v080-1'


def checkpoints(source, cadence_s=5., compatibility=False, horizon_s=None):
    if not np.isfinite(cadence_s) or cadence_s <= 0:
        raise ValueError('Cadence must be positive and finite')
    times = source.frame.lap_elapsed_s.to_numpy(float)
    # Scan in arrival order, never sort a reset or use a final target.
    valid = []
    previous = None
    for value in times:
        if not np.isfinite(value) or (previous is not None and (value < previous or value-previous > .2+1e-9)):
            break
        if horizon_s is not None and value > horizon_s:
            break
        valid.append(value)
        previous = value
    if not valid:
        return ()
    end = min(valid[-1], 600.)
    proposed = CHECKPOINTS if compatibility else np.arange(1, int(np.floor((end+1e-9)/cadence_s))+1)*cadence_s
    result = []
    for nominal in proposed:
        if nominal > end+1e-9:
            continue
        try:
            causal_prefix(source, float(nominal))
            result.append(float(nominal))
        except ValueError:
            pass
    return tuple(result)


def remaining_target(final_s, observed_s):
    result = np.asarray(final_s, float)-np.asarray(observed_s, float)
    if not np.isfinite(result).all() or (result < -1e-3).any():
        raise ValueError('Invalid verified remaining-time label')
    return np.maximum(0., result)


def reconstruct(raw_remaining, observed):
    raw = np.asarray(raw_remaining, float)
    elapsed = np.asarray(observed, float)
    if not np.isfinite(raw).all() or not np.isfinite(elapsed).all():
        raise ValueError('Nonfinite prediction')
    return elapsed+np.maximum(0., raw)


def remaining_reference(training_targets, observed):
    targets = np.asarray(training_targets, float)
    if targets.ndim != 1 or not len(targets) or not np.isfinite(targets).all():
        raise ValueError('Unique finite training targets required')
    prediction, support = [], []
    for elapsed in np.asarray(observed, float):
        surviving = targets[targets > elapsed]
        prediction.append(float(elapsed+np.median(surviving-elapsed)) if len(surviving) else float(elapsed))
        support.append(len(surviving))
    return np.asarray(prediction), np.asarray(support)
