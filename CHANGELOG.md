# Release v0.8.2 — 2026-10-25

- Close the progressive final-lap-time prediction research direction. Remove
  original/dense/remaining SVR, stop-aware forecasting, ordered Ridge, GRU,
  feature experiments, model stores, training/evaluation/replay workflows and
  their dedicated interfaces/tests from the active source.
- Preserve verified v0.8.1 as local commit
  `3b96553a10881ea654f5fe2a505cb7b3169d4d1d` and
  `archive/progressive-laptime-ml-v081`; work on `feat/scope-reset-v082`.
  Document recovery in a separate worktree and manual backup of ignored assets.
- Keep Session Overview, Data Explorer, Telemetry Comparison, imports,
  normalization, chart design, shared hover/cursors and optional Formula 1 analysis.
- Extract Barcelona source integrity utilities into ingestion. Apply the existing
  verified 1 ms rounding contract to Data Analysis: 205 validated laps are now
  accessible, compared with 204 through the previous analysis adapter.
- Remove prediction dependencies from requirements/CI without uninstalling the
  existing historical environment or touching ignored model/data files.
- Record exact signal/overview regression on 73 sources, all 205 original lap
  trajectories, retired tests, browser checks and the unchanged F5 configuration.
- Add no replacement predictor, new delta-time method or new dataset.

See [release](docs/RELEASE_V082_REPORT.md) and
[archive recovery](docs/archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md).

Earlier changelogs and release reports remain in the documented archive commit.
