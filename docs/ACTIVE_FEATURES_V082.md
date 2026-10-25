# Active features v0.8.2

The application analyses **observed recorded telemetry**.

| Workflow | Preserved behavior | Source limitations |
| --- | --- | --- |
| Session Overview | Dataset/session metadata, measured-time signal means, coverage and source-quality summaries | Unavailable timing/channels remain explicit |
| Signals | Source channels, unit-aware axes, verified-lap filtering and time windows | No invented channels or timing boundaries |
| Driver Inputs | Pedal use, braking/overlap events and steering observations | Gaps and invalid samples are not filled |
| Vehicle Dynamics | Longitudinal/lateral analysis and G-G with equal axis scale | Units must be compatible |
| Tyre Analysis | Available tyre temperature, pressure, load and related measurements | Availability depends on the source |
| Cockpit | Inspection of actual recorded samples and existing context traces | Recorded playback/inspection, no simulator capture |
| Position / Track Map | Compatible measured positions and existing vehicle-orientation indicator | No world X/Y in inspected ACGym LD exports; map unavailability is explained |
| Telemetry Comparison | Selected verified laps or saved session windows, stable identities/order/colors, one shared legend and synchronized cursors | Different tracks/unknown units remain guarded |
| Optional Formula 1 analysis | Historical lap/stint summaries, descriptive tyre degradation, telemetry comparison and map | Opt-in FastF1 dependency/network; analysis only |

## Data compatibility

CSV and Parquet imports, original raw columns, explicit source mappings, declared
units, time normalization, lap identification and filtering are preserved.
GT7 Trial Mountain and ACGym Monza remain supported. All **205** previously
validated Barcelona / Dallara F317 laps are accessible through the recording
selector. Source metadata uncertainty does not discard technically validated laps.

The previous analysis loader exposed only 204 of those laps. The shared adapter
now uses the already audited 1 ms target-rounding tolerance for the missing half-ms
boundary case. No source bytes, existing valid lap timing or signal values change.

Existing analytical distance/elapsed comparison helpers and descriptive
regressions are preserved. This release implements no new delta-time method.

## Archived functionality

SVR, SVR-DENSE, remaining-time predictors, stop-aware forecasts, prediction
baselines, ordered Ridge, Keras GRU, feature engineering, model training/selection/
evaluation, model loading and experimental progressive replay are removed from
active code and navigation. Their Git recovery point is documented
[in the archive guide](archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md).

## Runtime

The default application imports no Keras, Torch, scikit-learn or joblib and
requires no signed model artifacts. Prediction-specific environment selectors,
widgets, session state and caches have been removed with their owning modules.
Analysis source/chart caches remain. VS Code F5 and the existing visual theme are
unchanged. No new prediction method or data acquisition is introduced.
