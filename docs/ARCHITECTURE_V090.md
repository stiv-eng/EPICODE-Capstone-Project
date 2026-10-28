# Deterministic lap analysis architecture v0.9.0

The existing ingestion, normalization, Session Overview, Data Explorer and
Telemetry Comparison remain the baseline. The new analysis is isolated in
`motorsport/lap_analysis/`, without Streamlit, model dependencies or network calls.

| Module | Responsibility |
| --- | --- |
| `data.py` | Verified lap snapshots, explicit units/frame, source provenance and raw metric position attachment |
| `geometry.py` | Spatial resampling/smoothing, signed curvature, corner/straight/boundary partition and apex proxies |
| `alignment.py` | Sequential projection, ambiguity/continuity/coverage gates and elapsed-time inverse preserving stationary time |
| `kpis.py` | Observed events, physical-unit checks, temporal windows, measurements and quality |
| `analysis.py` | Compatibility, shared-reference orchestration, section conservation and strict JSON facts |
| `motorsport_ui/lap_analysis_v090.py` | Selection, cached computation, plots, measured comparisons and download |

Geometry removes consecutive stationary duplicates only in its own spatial
representation. Temporal telemetry remains unchanged. A and B use the same
reference sections and landmarks. All contributions, including the unclassified
seam when needed, partition the measured lap delta. Numerical conservation does
not independently establish sub-section alignment accuracy.

The existing shared hover renderer accepts explicit spatial cursor metadata.
The new page uses metres; previous time charts retain seconds. Hover is handled
in the browser without Python reruns. Raw signal overlays show observed samples;
analysis interpolation has separate documented quality limits.

Caches bind source signatures, explicit mappings, selected laps, every analysis
parameter and implementation signatures. Selecting a corner only changes the
presentation. JSON schema `deterministic-lap-analysis/1.0` contains provenance,
configuration, geometry, quality, event observations, measurement windows, units
and differences. `interpretations` is empty. This is a factual interface for a
future independent experiment, with no generated advice or causal inference.

Reproduce the real-data audit/evaluation using the commands in README. Run the
test suite and three Chrome scenarios, then run `scripts.finalize_v090` followed
by `scripts.report_lap_analysis_v090` to rebuild verification and reports.
