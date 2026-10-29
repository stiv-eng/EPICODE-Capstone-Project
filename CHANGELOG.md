# Final release preparation — 2026-10-29

- Preserve deterministic telemetry, comparisons, partial alignment and corner analysis.
- Keep optional manual Lap/Corner Coaching through local LM Studio, plain-text
  responses, neutral prompts and presentation-only unit/number formatting.
- Exclude obsolete FastF1 diagnostics, historical release-generation tooling,
  generated reports and caches from publication; retain source manifests and
  active regressions. Local historical resources remain on disk.
- Refresh setup, dataset acquisition and coaching instructions for a new clone.

# Release v0.9.0 — 2026-10-28

- Add Telemetry Lap Analysis alongside existing workflows: reference/analyzed
  sessions and laps, actual metric geometry, shared sections, delta decomposition,
  35 engineering KPI definitions, observed-signal overlays and strict JSON facts.
- Audit all 70 Barcelona LD exports / 205 verified laps and eight GT7 laps.
  Correct the earlier coordinate-availability conclusion: Barcelona raw metre
  world channels exist, although the old adapter omitted them.
- Implement 1.5 m spatial resampling, signed three-point curvature, configurable
  150 m corner threshold, weighted apex proxy and diagnostic maximum curvature.
  Mark unverified endpoint tangents as unclassified boundary sections.
- Align sequentially on one reference with offset, ambiguity, reverse-motion,
  timing and coverage checks. Retain stationary time and reconcile all section
  contributions with measured lap delta. Unsupported comparisons remain explicit.
- Define event persistence, units, measurement windows and quality per KPI.
  Withhold uncertain event associations and unverified physical units.
- Validate synthetic known solutions, recorded lap pairs, existing workflows,
  actual Chrome interactions, exports and the shared metre-based cursor.
  Preserve datasets, archived prediction work and F5. Add no ML/DL/LLM dependency.

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

Earlier changelogs and release reports remain in the documented archive commit.
