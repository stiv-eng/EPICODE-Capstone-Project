# ML/DL readiness v0.5

No new supervised model or Keras network was trained/redesigned. Historical
SVR/Keras sources remain intact; only their existing offline regression tests run
their established small training fixtures.

## Actual capability assessment

| Capability | Original Parquet | Integrated GT7 |
|---|---|---|
| Session analysis | Yes | Yes |
| Time-window comparison | Yes, repeated timestamps retained | Yes, host-clock gaps excluded from duration metrics |
| Source-coordinate position analysis | Yes; integrated, drift unverified | Yes; source-reported simulator world coordinates |
| Validated complete lap analysis | No | Yes: eight consistency-checked laps |
| Lap signal comparison by driven fraction | No | Yes; approximate spatial alignment, not a common centreline |
| Cumulative lap-time delta | No | No verified common track-distance reference |
| Verified full-lap targets | No | Eight next-lap packet targets, 103.712–108.650 s |
| Supervised ML eligible under release gate | No | No: one session and only eight accepted laps |
| Progressive lap-time DL eligible | No | No: independent evaluation coverage is insufficient |

`assess_capabilities(session)` checks observed time support, finite varying
coordinates, validated boundaries, usable per-lap distance, target durations,
actual core-signal validity and session/lap counts. Column names alone cannot
enable a feature. Reasons are displayed in Session Overview and exported measured
evidence. Lap-delta capability also invokes the alignment checks, rather than
trusting a metadata reference string alone.

The conservative eligibility gate is **at least 30 validated target laps, at least
three independent sessions, and at least 99% finite/in-range core speed, pedals
and RPM**; progressive DL additionally needs valid progress. These are release
policy thresholds to prevent premature claims, not a statistical proof of sample
adequacy. A future multi-session collection must verify grouping metadata and
representativeness rather than manually inflating a count.

## Identifiers, targets and candidate features

`TelemetrySession.metadata.session_id` identifies a local source by a content and
schema fingerprint, or a pinned source revision for the GT7 bundle. It does not
turn different files from the same physical session into independent experiments.
Canonical `lap_id` and `lap_elapsed_s` exist only for validated complete laps.
Each exported feature row contains `session_id`, `lap_id`, `lap_uid`, available
car/track identities, target time, target-verification flag and training eligibility.

GT7's target for lap n comes from the stable `last_lap_ms` field in lap n+1 and is
cross-checked against the observed in-lap timer coverage. That future packet is
used only as a **label**. Its contents are never a candidate input feature.
Out-laps, trailing fragments, stale boundary packets and inconsistent lap timers
are excluded from canonical labels. The rejected-source table remains inspectable.

`lap_features(session)` produces sample maxima and observed-time means for speed,
pedals and RPM from the **entire validated lap**. It is explicitly marked
“full lap retrospective; not causal progressive features”. Target and eligibility
fields are not a model-input list. These rows support future tabular data analysis;
whole-lap features would leak future information into an in-progress prediction.

## Future split and leakage policy

1. Establish physical session/driver/car/track IDs from source provenance. Deduplicate
   raw captures and derivative exports before assigning splits; content IDs alone
   do not establish independence.
2. Reserve complete sessions chronologically for final testing where possible.
   Fit all scalers, encoders, imputers and feature-selection choices on training
   sessions only. Keep every lap and all its prefix examples in a single split.
3. Within the training pool, validate by complete session/lap groups. A random row
   split over high-frequency telemetry is prohibited: adjacent observations and
   overlapping prefixes are not independent examples.
4. For progressive features, calculate only from samples observed at or before the
   prediction timestamp/progress. No future whole-lap means/maxima, final distance,
   final target, next-lap timing packet or held-out reference lap may enter inputs.
5. Construct distance/reference trajectories from training data or independent
   documented track geometry. Normalizing by a lap's eventual driven distance is
   retrospective visualization and cannot silently become a causal live feature.
6. Exclude or explicitly handle invalid laps, clock resets, acquisition gaps,
   unverified channel units and insufficient prefix coverage. Record per-lap
   quality/eligibility decisions alongside target provenance.
7. Report per-lap and per-session errors, data coverage and uncertainty against
   simple baselines. With the current single-session GT7 subset, a chronological
   within-session split can demonstrate code only; it cannot substantiate
   cross-driver/session generalization.

The historical `motorsport_ui/svr.py` and `motorsport_prediction/` implementations
retain their own v0.3 contracts. Adaptation to these new feature/target contracts
is deferred to v0.6/v0.7.
