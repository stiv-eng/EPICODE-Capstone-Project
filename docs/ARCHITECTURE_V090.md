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
| `motorsport/coaching.py` | Optional local LM Studio client, deterministic evidence selection and presentation-only unit/number formatting |
| `motorsport_ui/coaching.py` | Manual Lap/Corner Coaching, language/model selection and session response cache |

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
and differences. `interpretations` is empty. Optional coaching consumes a compact
copy of these facts; generated text is shown separately and never added to the
deterministic report. It is not validated causal inference.

Use the README for data acquisition, application startup and tests. The source
manifests and frozen signal/lap regression baseline remain versioned because
ingestion and relevant tests use them. Old release-generation pipelines are not
part of the maintained application.
