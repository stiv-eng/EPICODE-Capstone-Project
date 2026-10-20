# ML feature contracts v0.6

Two independent contracts exist. `retrospective_features(corpus)` reports
whole-lap time-weighted mean speed and braking fraction for descriptive analysis.
Those columns are unavailable to the progressive trainer. The v0.5 retrospective
lap-feature exports are also preserved unchanged.

`prefix_features(replay_lap, checkpoint)` reads only the ordered source prefix
ending before the first timestamp beyond the checkpoint. A future clock reset
cannot make later packets re-enter the prefix. The function receives no target,
final distance, full-lap KPI, next-lap packet, driver skill label or best-lap time.

## Checkpoints and quality

Defaults: **10, 20, 30, 45, 60 s**, configurable in the pure snapshot/training APIs.
Only elapsed-time checkpoints are supported. These are timestamps from a verified
source lap timer, not percentages computed using eventual lap distance.

A prefix must begin within 100 ms of zero and end within 100 ms of its requested
checkpoint. Time must be finite and nondecreasing; no step may exceed 200 ms.
Each of speed 0–500 km/h, pedals 0–100%, and RPM 0–25,000 must have at least 99%
finite/in-range values. Missing key channels reject the checkpoint, not the whole
application. Repeated held source-clock values have zero dwell. No forward value
or interval ending outside the prefix is included. The terminal sample has zero
added dwell. Quality retains actual observed elapsed time, sample count,
clock coverage fraction, key-channel coverage and status.

The selected source's own upstream resampling is outside our causal guarantee;
see the [dataset clock limitations](DATASET_EXPANSION_V06.md).

## Fixed predictive allowlist

| Feature | Definition and unit |
|---|---|
| `checkpoint_s` | Requested elapsed-time checkpoint, seconds |
| `observed_elapsed_s` | Last observed source lap-timer value at/before checkpoint, seconds |
| `speed_current_kmh` | Speed in the last available packet, km/h |
| `speed_mean_kmh` | Left-hold, positive-duration weighted speed since observed lap start, km/h |
| `speed_recent_mean_kmh` | Same mean over observed samples in the most recent 3 s, km/h |
| `speed_recent_std_kmh` | Weighted population standard deviation over that recent window, km/h |
| `throttle_mean_pct` | Time-weighted valid throttle so far, % |
| `brake_mean_pct` | Time-weighted valid brake so far, % |
| `throttle_high_fraction` | Fraction of valid pedal-observed duration at throttle >=90%, 0–1 |
| `braking_fraction` | Fraction at brake >=5%, 0–1 |
| `rpm_current` | Last observed engine RPM |
| `gear_current` | Last observed reported gear |
| `steering_activity_deg_s` | Sum of absolute changes over positive source-time intervals in recent 3 s / supported duration, deg/s; only when degrees are declared |

Means exclude nonfinite/out-of-range key values; quality still counts those values
as invalid. Optional unknown steering is NaN, not an invented conversion. Imputation
is learned exclusively from training rows. The UI excludes wholly unavailable
features from the initial selection; users can inspect/select the fixed allowlist.
No learned feature-selection step or hyperparameter search uses validation/test
statistics. Previous completed-lap context is exposed through the two deterministic
baselines rather than added as a hidden predictive feature.

## Snapshot and label separation

`ReplayLap` contains identity, physical-session/participant metadata, car/track
domain, chronological start order, declared steering units and a reduced telemetry
frame. It has **no target field**. Current/last/best-lap source timing fields and
source progress are not retained in that frame.

`Corpus.targets` separately records the verified target seconds, target source,
source ID/revision/URL, per-file SHA-256 when applicable, lap fingerprint, lap UID, physical-session ID, participant ID,
chronology, domain, coverage and source-independence decision. `snapshots` first
computes causal rows, then attaches this table in a checked many-to-one join.
All prefixes of a lap receive the same split assignment. Target/provenance and
quality columns can be exported for audit but are refused by the trainer as inputs.
For GT7, the bundle revision identifies the collection; its individual file hashes
remain in the v0.5 manifest. The revision is never mislabelled as a file SHA-256.

ACGym produces 275 accepted rows: 55 laps × five checkpoints, no checkpoint
rejections. GT7 produces 40: eight laps × five checkpoints. No snapshot is an
independent physical lap; reported counts always distinguish both.

## Acceptance evidence

`tests/test_ml_v06.py` changes future speed, controls, RPM, steering and a future
clock reset at each default checkpoint and asserts unchanged earlier predictions.
It changes attached final labels and checks identical features. Separate tests
change held-out target labels and check that fitted model predictions and historical
baselines are unchanged. These checks protect the dependency boundary, not just
column names. Parser/target tests reject corrupt bounds, cycles, entities,
unsupported boundaries, inconsistent target/beacon times and invalidated laps.
