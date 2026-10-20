"""Feature engineering strettamente causale: ogni riga usa solo il prefisso osservato."""
import numpy as np
import pandas as pd

NUMERIC_FEATURES = [
    'progress', 'elapsed_s', 'reference_elapsed_s', 'delta_s',
    'speed_kmh', 'reference_speed_kmh', 'speed_delta_kmh',
    'mean_speed_so_far_kmh', 'mean_speed_last_3s_kmh',
    'throttle', 'brake', 'rpm', 'gear', 'tyre_life',
]
CATEGORICAL_FEATURES = ['driver', 'compound']
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _baseline(current_time, ref_time, ref_final):
    return max(float(current_time), float(current_time) + float(ref_final) - float(ref_time))


def snapshots(lap, reference, steps=None, include_finish=True):
    """Esegue snapshot ai traguardi di distanza noti del giro FP3 di riferimento.

    Il calcolo non normalizza MAI per la distanza finale del giro corrente.
    L'ultima riga (finish) e' possibile solo a giro concluso.
    """
    if steps is None:
        steps = np.linspace(0.05, 0.95, 19)
    raw = lap.telemetry
    ref = reference.telemetry
    if raw.empty or ref.empty:
        return pd.DataFrame()
    ref_d = ref['distance_m'].to_numpy(dtype=float)
    ref_t = ref['elapsed_s'].to_numpy(dtype=float)
    ref_v = ref['Speed'].to_numpy(dtype=float)
    dist = raw['distance_m'].to_numpy(dtype=float)
    times = raw['elapsed_s'].to_numpy(dtype=float)
    speeds = raw['Speed'].to_numpy(dtype=float)
    track_length = float(ref_d[-1])
    if track_length <= 0:
        return pd.DataFrame()
    result = []
    for fraction in steps:
        target_distance = float(fraction) * track_length
        i = int(np.searchsorted(dist, target_distance, side='left'))
        if i >= len(raw):
            continue  # Distanza non ancora percorsa: niente dati del futuro.
        elapsed = times[i]
        progress = min(float(dist[i] / track_length), 1.0)
        ref_elapsed = float(np.interp(dist[i], ref_d, ref_t))
        ref_speed = float(np.interp(dist[i], ref_d, ref_v))
        # Finestra mobile chiusa all'indice corrente (non comprende tempi futuri).
        j = int(np.searchsorted(times, elapsed - 3.0, side='left'))
        observed_mean = (dist[i] / max(elapsed - times[0], 0.1)) * 3.6
        row = raw.iloc[i]
        base = _baseline(elapsed, ref_elapsed, reference.lap_time_s)
        result.append({
            'driver': lap.driver, 'compound': lap.compound,
            'progress': progress, 'elapsed_s': elapsed,
            'reference_elapsed_s': ref_elapsed, 'delta_s': elapsed - ref_elapsed,
            'speed_kmh': speeds[i], 'reference_speed_kmh': ref_speed,
            'speed_delta_kmh': speeds[i] - ref_speed,
            'mean_speed_so_far_kmh': observed_mean,
            'mean_speed_last_3s_kmh': float(np.mean(speeds[j:i+1])),
            'throttle': float(row['Throttle']), 'brake': float(row['Brake']),
            'rpm': float(row['RPM']), 'gear': float(row['nGear']),
            'tyre_life': lap.tyre_life,
            'lap_uid': lap.uid, 'session': lap.session,
            'baseline_s': base, 'actual_s': lap.lap_time_s,
            'target_residual_s': lap.lap_time_s - base,
            'is_finish': False,
        })
    if include_finish and len(raw) > 0:
        # Il traguardo viene rivelato soltanto quando il giro risulta terminato.
        last = result[-1].copy() if result else None
        if last is not None:
            last.update({
                'progress': 1.0, 'elapsed_s': lap.lap_time_s,
                'baseline_s': lap.lap_time_s,
                'actual_s': lap.lap_time_s,
                'target_residual_s': 0.0, 'is_finish': True,
            })
            result.append(last)
    return pd.DataFrame(result)


def build_dataset(laps, references):
    frames = [snapshots(lap, references[lap.driver], include_finish=False)
              for lap in laps if lap.driver in references]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise ValueError('Dataset vuoto: nessuno snapshot utilizzabile.')
    return pd.concat(frames, ignore_index=True)
