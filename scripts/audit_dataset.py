"""Reproduce the v0.4 attachment audit: python -m scripts.audit_dataset.

The source profile is deliberately specific to the inspected attachment. This
does not establish dataset provenance or certify simulator metadata.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path

import numpy as np

from motorsport.pipeline import load_session
from motorsport.processing.schema import SUPPLIED_V04
from motorsport.processing.validation import time_quality

ROOT = Path(__file__).resolve().parents[1]


def number(value):
    return f'{value:.9g}' if isinstance(value, (float, np.floating)) else str(value)


def audit(path, output):
    session = load_session(path, profile=SUPPLIED_V04)
    raw, q = session.raw, session.raw_quality
    with path.open('rb') as source:
        sha = hashlib.file_digest(source, 'sha256').hexdigest()
    t = raw.timestamp.to_numpy()
    dt = np.diff(t)
    elapsed = t-t[0]
    x, z = raw.pos_x.to_numpy(), raw.pos_z.to_numpy()
    step = np.hypot(np.diff(x), np.diff(z))
    moving = (dt > 0) & (raw.speed_kmh.to_numpy()[1:] > 10)
    displacement_speed_ratio = step[moving]/dt[moving]/(raw.speed_kmh.to_numpy()[1:][moving]/3.6)
    velocity_norm_ratio = np.linalg.norm(raw[['vel_x', 'vel_y', 'vel_z']].to_numpy(), axis=1)*3.6/raw.speed_kmh.to_numpy()
    # Check whether positions behave like a right-endpoint integration of
    # vehicle-frame velocities rotated by heading. Exact agreement supports
    # caution about accumulated drift rather than independent GPS precision.
    heading = raw.heading.to_numpy()[1:]
    vx, vz = raw.vel_x.to_numpy()[1:], raw.vel_z.to_numpy()[1:]
    predicted_dx = (vx*np.cos(heading)-vz*np.sin(heading))*dt
    predicted_dz = (vx*np.sin(heading)+vz*np.cos(heading))*dt
    integration_error = np.hypot(np.diff(x)-predicted_dx, np.diff(z)-predicted_dz)
    radius = np.hypot(x-x[0], z-z[0])
    near = radius < 30
    entries = np.flatnonzero(near & ~np.r_[False, near[:-1]])
    exits = np.flatnonzero(near & ~np.r_[near[1:], False])
    nearest = np.array([a+np.argmin(radius[a:b+1]) for a, b in zip(entries, exits)])
    times = elapsed[nearest]
    periods = np.diff(times)
    source_times = {c: time_quality(raw[c]) for c in ['timestamp', 'wall_time']}
    lines = [
        '# Dataset audit v0.4', '',
        'Measured from the real attachment; regenerate with `python -m scripts.audit_dataset`.', '',
        f'- Audit generated (UTC): {datetime.now(timezone.utc).isoformat()}',
        f'- Input: `{path.resolve()}`',
        '- Original: `C:/Users/stefa/Downloads/telemetry.parquet` (preserved).',
        f'- Size: {path.stat().st_size:,} bytes; SHA-256: `{sha}`.',
        f'- Shape: **{len(raw):,} rows × {len(raw.columns)} columns**; {session.metadata["row_groups"]} Parquet row group.',
        '- Types: ' + ', '.join(f'{dtype}: {count}' for dtype, count in raw.dtypes.astype(str).value_counts().items()) + '.',
        '- Embedded metadata contains Pandas schema/index information only. No track, car, driver, session identity, unit dictionary, license or collection provenance is embedded.',
        '- Assetto Corsa / Imola provenance is **unverified**. Channel names and signal behavior are compatible with simulator telemetry but do not prove its origin.', '',
        '## Quality and timing', '',
        f'- Missing cells: {q["missing_cells"]}; infinite values: {q["infinite_cells"]}; exact duplicate records: {q["duplicate_rows"]}.',
        f'- Constant channels ({len(q["constant_channels"])}): ' + ', '.join(f'`{c}`' for c in q['constant_channels']) + '.',
        '- Constant does not imply erroneous: settings and ambient temperatures can be constant. Zero lap fields and water temperature cannot provide the corresponding analysis.',
    ]
    for name, stats in source_times.items():
        lines.extend([
            f'- `{name}`: span {stats["duration_s"]:.9f} s; {stats["duplicate_values"]} duplicate values; {stats["backward_steps"]} backward steps; effective rate {stats["observed_rate_hz"]:.6f} Hz.',
            f'  Median positive step {stats["median_positive_step_s"]:.9f} s ({stats["median_positive_rate_hz"]:.6f} Hz); maximum gap {stats["max_gap_s"]:.9f} s; gaps above {stats["gap_threshold_s"]:.3f} s: {stats["large_gaps"]}.',
        ])
    gap = int(np.argmax(dt))
    lines += [
        f'- Largest timestamp gap: source samples {gap}→{gap+1}, elapsed {elapsed[gap]:.6f}→{elapsed[gap+1]:.6f} s.',
        '- Approximate acquisition is 64 Hz, not a strictly uniform grid. The rounded millisecond timestamp has 1,245 repeats; wall_time preserves acquisition order but is not automatically substituted for simulator time.',
        '- Source order, duplicate timestamps and all observations are retained. Canonical nonnumeric/nonfinite values become missing, while raw values remain available.', '',
        '## Signals and units', '',
        f'- Speed: {raw.speed_kmh.min():.6f}–{raw.speed_kmh.max():.6f} km/h; sample mean {raw.speed_kmh.mean():.6f} km/h.',
        f'- Controls: throttle {raw.throttle.min():.6f}–{raw.throttle.max():.6f}; brake {raw.brake.min():.6f}–{raw.brake.max():.6f}. Both are bounded 0–1 with endpoint saturation; the attachment profile explicitly interprets these as fractional pedal signals and multiplies by 100.',
        f'- RPM: {raw.rpms.min()}–{raw.rpms.max()}; gear: {raw.gear.min()}–{raw.gear.max()}.',
        '- `timestamp` and `wall_time` spans agree to within milliseconds, supporting seconds as the time scale.',
        f'- `speed_kmh` agrees with 3.6×the velocity norm: median ratio {np.median(velocity_norm_ratio):.9f}, 1st/99th percentiles {np.quantile(velocity_norm_ratio,.01):.9f}/{np.quantile(velocity_norm_ratio,.99):.9f}. This supports the declared speed scale; it does not prove every velocity channel uses world coordinates.',
        '- `rpms`→`rpm`; `steer_angle`→`steering`; `pos_z`→canonical second planar axis `pos_y`. The original columns are retained.',
        '- Steering, accelerations, temperatures, loads, pressures and positions retain source units. Names suggest interpretations, but no unsupported degrees/radians or force conversions are applied.',
        '- Vehicle dynamics: lateral/longitudinal/vertical accelerations, velocities, attitude/rates, suspension, wheel loads, slip, wheel speeds, camber and ride heights. Controls include pedals, steering, gear and electronic settings. Tyre thermal/pressure/wear channels and fuel are present.',
        '- No fabricated distance, final lap-time targets or replacement channels are generated.', '',
        '## Position and lap investigation', '',
        f'- `lap_progress`: unique values {raw.lap_progress.unique().tolist()}; `completed_laps`: {raw.completed_laps.unique().tolist()}. Both are unusable for lap boundaries.',
        f'- Planar bounds: x {x.min():.6f}…{x.max():.6f}; z {z.min():.6f}…{z.max():.6f}; endpoint distance from origin {radius[-1]:.6f} source units.',
        f'- Finite-step planar-speed / declared-speed ratio (speed >10 km/h): median {np.median(displacement_speed_ratio):.9f}; p01/p99 {np.quantile(displacement_speed_ratio,.01):.9f}/{np.quantile(displacement_speed_ratio,.99):.9f}.',
        f'- Rotated local-velocity integration check: median per-step position residual {np.median(integration_error):.12g}, maximum {np.max(integration_error):.12g} source units. Close agreement suggests positions are integrated rather than an independent geometric reference; accumulated drift cannot be ruled out.',
        f'- Within a 30-unit radius of the initial point: {len(entries)} visits including the initial fragment. Nearest-approach elapsed times: ' + ', '.join(f'{v:.3f}' for v in times) + ' s.',
        f'- Intervisit periods span {periods.min():.3f}–{periods.max():.3f} s. These are proximity candidates, **not validated lap times**.',
        '- The initial point is not identified as a start/finish line. Proximity alone does not establish a directional finish crossing, closed-lap coverage, pit exclusion, reset exclusion or a complete first/last lap. Duration plausibility alone cannot certify boundaries.',
        '- Decision: no geometric segmentation promoted to valid laps. **0 validated complete laps**; lap-dependent controls and models remain unavailable for this attachment. Session-level analytics and the coordinate trace remain useful.', '',
        '## Suspicious observations', '',
        f'- `slip_fr` maximum {raw.slip_fr.max():.6f}, p99 {raw.slip_fr.quantile(.99):.6f}; `slip_rr` maximum {raw.slip_rr.max():.6f}, p99 {raw.slip_rr.quantile(.99):.6f}: extreme tails merit source/sensor investigation.',
        f'- `ride_height_r` minimum {raw.ride_height_r.min():.9f}; negative observations: {int((raw.ride_height_r<0).sum())}. Source units/meaning require confirmation.',
        '- IQR outliers below use 3×IQR fences only when IQR >0. Racing signals are multimodal; these flags are not evidence of corruption and no flagged observations are silently discarded.', '',
        '## Complete measured schema', '',
        '| Channel | dtype | Missing | Infinite | Unique | Min | Median | Max | Constant | 3×IQR flags |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|---:|',
    ]
    for c in q['channels']:
        lines.append('| ' + ' | '.join(number(c.get(k, '')) for k in [
            'channel', 'dtype', 'missing', 'infinite', 'unique', 'min', 'median', 'max', 'constant', 'iqr_outliers']) + ' |')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'Wrote {output}: {len(raw):,} × {len(raw.columns)}, SHA-256 {sha}')
    print('Position integration residual median/max:', np.median(integration_error), np.max(integration_error))
    print('Nearest return intervals:', periods)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'data/raw/telemetry.parquet')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/DATASET_AUDIT_V04.md')
    args = parser.parse_args()
    audit(args.input, args.output)
