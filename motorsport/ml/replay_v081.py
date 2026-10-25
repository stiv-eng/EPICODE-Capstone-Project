"""Target-free, sample-clock inference and transparent stationary correction.

No fitting, target, wall clock, track percentage or eventual duration is used.
The 13-feature contract and signed v080 fold models remain unchanged.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .dataset import CORE
from .features import FEATURES
from .barcelona_recovery import DOMAIN, file_sha
from .dense_experiment_v080 import PROTOCOL
from .progression_v080 import VERSION

CADENCES = (5., 1., .5)
STOP_SPEED_KMH = 2.
RESUME_SPEED_KMH = 4.
STOP_CONFIRM_S = 1.
RESUME_CONFIRM_S = .3
RESUME_BLEND_S = 2.
MAX_GAP_S = .2
MAX_AGE_S = .1


class PrefixIndex:
    """Prefix sufficient statistics with the original left-sample time weights.

    Each cumulative value at index i only includes intervals ending at i.
    Recent statistics keep the original NumPy arithmetic. Invalid clock tails
    are quarantined in arrival order, never sorted or repaired with future data.
    """
    def __init__(self, source):
        self.source = source
        clock = pd.to_numeric(source.frame.lap_elapsed_s, errors='coerce').to_numpy(float)
        end = 0
        for i, t in enumerate(clock):
            if not np.isfinite(t) or (i and (t < clock[i-1] or t-clock[i-1] > MAX_GAP_S)):
                break
            end = i+1
        self.t = clock[:end].copy()
        self.clock_interrupted = end != len(clock)
        self.values, self.sums, self.durations, self.coverage = {}, {}, {}, {}
        dt = np.diff(self.t)
        for column in ('speed_kmh', 'throttle_pct', 'brake_pct', 'rpm', 'gear', 'steering'):
            y = pd.to_numeric(source.frame.reindex(columns=[column])[column], errors='coerce').to_numpy(float)[:end].copy()
            if column in CORE:
                lo, hi = CORE[column]
                y[(y < lo) | (y > hi)] = np.nan
            self.values[column] = y
            valid = np.isfinite(y)
            self.coverage[column] = np.cumsum(valid)
            self.sums[column] = np.r_[0., np.cumsum(np.where(valid[:-1], y[:-1], 0.)*dt)]
            self.durations[column] = np.r_[0., np.cumsum(valid[:-1]*dt)]
        for name, column, threshold in [('high', 'throttle_pct', 90.), ('braking', 'brake_pct', 5.)]:
            y = self.values[column]
            self.sums[name] = np.r_[0., np.cumsum((np.isfinite(y[:-1]) & (y[:-1] >= threshold))*dt)]
        self.cache = {}

    def position(self, nominal):
        if not np.isfinite(nominal) or not 0 < nominal <= 600:
            raise ValueError('Checkpoint outside finite (0, 600] support')
        i = int(np.searchsorted(self.t, nominal, side='right'))-1
        if i < 0 or self.t[0] > .1 or nominal-self.t[i] > MAX_AGE_S:
            raise ValueError('No fresh monotonic prefix within 100 ms')
        if min(self.coverage[c][i]/(i+1) for c in CORE) < .99:
            raise ValueError('Prefix key-signal coverage is below 99%')
        return i

    def schedule(self, cadence_s=1., horizon_s=None):
        if cadence_s not in CADENCES:
            raise ValueError('Supported cadence: 5, 1 or 0.5 seconds')
        end = min(self.t[-1], 600., horizon_s if horizon_s is not None else 600.) if len(self.t) else 0.
        points = []
        for nominal in np.arange(1, int(np.floor((end+1e-9)/cadence_s))+1)*cadence_s:
            try:
                self.position(float(nominal))
                points.append(float(nominal))
            except ValueError:
                pass
        return tuple(points)

    def features(self, nominal):
        if nominal in self.cache:
            return self.cache[nominal].copy()
        i = self.position(nominal)
        t = self.t[:i+1]
        start = int(np.searchsorted(t, t[-1]-3., side='left'))
        w = np.r_[np.diff(t[start:]), 0.]
        speed = self.values['speed_kmh'][start:i+1]
        good = np.isfinite(speed)
        duration = w[good].sum()
        mean = float(np.average(speed[good], weights=w[good])) if duration > 0 else np.nan
        std = float(np.sqrt(np.average((speed[good]-mean)**2, weights=w[good]))) if duration > 0 else np.nan
        steering = self.values['steering'][start:i+1]
        dt = np.diff(t[start:])
        positive = dt > 0
        activity = np.nan
        if self.source.steering_unit == 'deg' and len(dt) and np.isfinite(steering).all() and positive.any():
            activity = float(np.abs(np.diff(steering)[positive]).sum()/dt[positive].sum())
        def avg(column, numerator=None):
            denom = self.durations[column][i]
            return float(self.sums[numerator or column][i]/denom) if denom > 0 else np.nan
        f = dict(checkpoint_s=float(nominal), observed_elapsed_s=float(t[-1]),
            speed_current_kmh=float(self.values['speed_kmh'][i]), speed_mean_kmh=avg('speed_kmh'),
            speed_recent_mean_kmh=mean, speed_recent_std_kmh=std,
            throttle_mean_pct=avg('throttle_pct'), brake_mean_pct=avg('brake_pct'),
            throttle_high_fraction=avg('throttle_pct', 'high'), braking_fraction=avg('brake_pct', 'braking'),
            rpm_current=float(self.values['rpm'][i]), gear_current=float(self.values['gear'][i]),
            steering_activity_deg_s=activity)
        self.cache[nominal] = f
        return f.copy()


@dataclass
class StopDetector:
    previous_s: float | None = None
    low_since_s: float | None = None
    high_since_s: float | None = None
    stationary: bool = False
    state: str = 'uncertain'

    def update(self, elapsed, speed):
        """Return confirmation events, based on valid arriving source samples."""
        if (not np.isfinite(elapsed) or not np.isfinite(speed) or not 0 <= speed <= 500 or
                (self.previous_s is not None and (elapsed < self.previous_s or elapsed-self.previous_s > MAX_GAP_S))):
            self.previous_s = None
            self.low_since_s = self.high_since_s = None
            self.stationary = False
            self.state = 'uncertain'
            return 'invalid'
        # Repeated timestamps cannot establish persistence or elapsed stop time.
        self.previous_s = elapsed
        if self.stationary:
            if speed >= RESUME_SPEED_KMH:
                if self.high_since_s is None:
                    self.high_since_s = elapsed
                self.state = 'uncertain'
                if elapsed-self.high_since_s >= RESUME_CONFIRM_S-1e-9:
                    self.stationary = False
                    self.low_since_s = self.high_since_s = None
                    self.state = 'moving'
                    return 'resume'
            else:
                self.high_since_s = None
                self.state = 'stationary'
        elif speed <= STOP_SPEED_KMH:
            if self.low_since_s is None:
                self.low_since_s = elapsed
            self.state = 'uncertain'
            if elapsed-self.low_since_s >= STOP_CONFIRM_S-1e-9:
                self.stationary = True
                self.state = 'stationary'
                return 'stop'
        else:
            self.low_since_s = None
            self.state = 'moving'
        return None


def physical_bound(raw, elapsed):
    if not np.isfinite(raw) or not np.isfinite(elapsed) or elapsed < 0:
        raise ValueError('Finite prediction and nonnegative source time required')
    return max(float(raw), float(elapsed))


class ReplayEngine:
    """Incremental replay: cached model/prefix queries, sample-based stop state.

    Rewind creates a fresh engine. Cadence never enters the state detector.
    """
    def __init__(self, source, bundle):
        if (tuple(source.domain) != DOMAIN or tuple(bundle.domain) != DOMAIN or
                source.lap_uid not in bundle.allowed_ids):
            raise ValueError('Source outside this development fold/domain')
        if (tuple(bundle.feature_names) != FEATURES or bundle.compatibility.get('version') != VERSION or
                bundle.compatibility.get('protocol_sha256') != file_sha(PROTOCOL)):
            raise ValueError('Incompatible experimental feature/protocol binding')
        self.source, self.bundle = source, bundle
        self.index = PrefixIndex(source)
        self.detector = StopDetector()
        self.cursor = 0
        self.remaining_at_stop = None
        self.stop_onset_s = None
        self.resume_s = None
        self.resume_offset_s = 0.
        self.raw_cache, self.rows, self.events = {}, {}, []
        self.model_calls = 0

    def raw(self, nominal):
        if nominal not in self.raw_cache:
            f = self.index.features(nominal)
            self.raw_cache[nominal] = float(self.bundle.models['SVR-DENSE'].predict(pd.DataFrame([f], columns=FEATURES))[0])
            self.model_calls += 1
        return self.raw_cache[nominal]

    def predict(self, nominal):
        if nominal in self.rows:
            return self.rows[nominal].copy()
        i = self.index.position(nominal)
        if i < self.cursor-1:
            raise ValueError('Replay rewind requires a new engine')
        while self.cursor <= i:
            t = float(self.index.t[self.cursor])
            speed = float(self.index.values['speed_kmh'][self.cursor])
            event = self.detector.update(t, speed)
            if event == 'invalid':
                self.remaining_at_stop = None
                self.resume_s = None
            elif event == 'stop':
                self.stop_onset_s = float(self.detector.low_since_s)
                anchor = self.stop_onset_s
                # A stop beginning at t=0 has no valid weighted prefix yet.
                # Use the earliest already observed, feature-valid sample.
                if anchor <= 0:
                    anchor = next((float(x) for x in self.index.t[:self.cursor+1] if x > 0), t)
                try:
                    self.index.position(anchor)
                except ValueError:
                    # An onset prefix can fail the 99% coverage gate even when
                    # later observed prefixes recover. Never fabricate an anchor.
                    self.remaining_at_stop = None
                else:
                    self.remaining_at_stop = max(0., self.raw(anchor)-anchor)
                self.resume_s = None
                self.events.append(dict(event='stop', observed_elapsed_s=t, onset_s=self.stop_onset_s,
                                        remaining_at_stop_s=self.remaining_at_stop))
            elif event == 'resume':
                bounded = physical_bound(self.raw(t), t)
                self.resume_offset_s = max(0., t+self.remaining_at_stop-bounded) if self.remaining_at_stop is not None else 0.
                self.resume_s = t
                self.remaining_at_stop = None
                self.events.append(dict(event='resume', observed_elapsed_s=t, offset_s=self.resume_offset_s))
            self.cursor += 1
        f = self.index.features(nominal)
        elapsed = f['observed_elapsed_s']
        raw = self.raw(nominal)
        bounded = physical_bound(raw, elapsed)
        if self.detector.stationary and self.remaining_at_stop is None:
            # First valid causal model estimate after an unavailable onset.
            self.remaining_at_stop = bounded-elapsed
        corrected = bounded
        if self.detector.stationary and self.remaining_at_stop is not None:
            corrected = elapsed+self.remaining_at_stop
        elif self.resume_s is not None:
            corrected += self.resume_offset_s*max(0., 1.-(elapsed-self.resume_s)/RESUME_BLEND_S)
        corrected = physical_bound(corrected, elapsed)
        row = dict(checkpoint_s=float(nominal), observed_elapsed_s=elapsed,
            sample_age_s=float(nominal-elapsed), speed_kmh=f['speed_current_kmh'],
            driving_state=self.detector.state, raw_prediction_s=raw,
            bounded_prediction_s=bounded, stop_aware_prediction_s=corrected,
            bound_active=bool(raw < elapsed), bound_adjustment_s=bounded-raw,
            stop_adjustment_s=corrected-bounded,
            stop_onset_s=self.stop_onset_s if self.detector.stationary else None,
            remaining_at_stop_s=self.remaining_at_stop,
            model='SVR-DENSE v0.8 / experimental v0.8.1')
        self.rows[nominal] = row
        return row.copy()


def replay(source, bundle, cadence_s=1., horizon_s=None):
    engine = ReplayEngine(source, bundle)
    return pd.DataFrame([engine.predict(t) for t in engine.index.schedule(cadence_s, horizon_s)]), engine


def advance_checkpoint(points, current, playing):
    """One recorded checkpoint per replay tick; a pause consumes no lap time."""
    i = points.index(current)
    return points[min(i+1, len(points)-1)] if playing else current
