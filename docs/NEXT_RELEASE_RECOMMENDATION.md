# Recommendation after v0.6.1

Prioritize a short evidence/UX follow-up before expanding model complexity. The
Explorer now shares sources/laps and exposes a recorded Cockpit, while the v0.6
causal ML contracts and measured predictions are preserved.

1. Reproduce FB-007 on the user's affected browser/GPU if it recurs. Capture the
   exact browser version, selected signals/laps, scroll position and console/context
   events. The archived v0.6 eight-channel Chrome test did not reproduce disappearance;
   the new SVG workflow passed. Do not label the original root cause resolved solely
   because the new renderer avoids GPU canvas restoration.
2. Extend browser coverage to another engine and a real mobile browser. Current
   evidence is local headless Chrome at 1600x1200 and a narrow 480x960 Cockpit viewport.
   Keep page/section transitions, shared state and source changes in the smoke suite.
3. Obtain documented world X/Y telemetry for ACGym if physical track visualization
   is needed. The inspected MoTeC export provides race rank and dimensionless progress,
   not compatible world coordinates. Do not reconstruct a track from those channels.
4. Validate coordinate units, discontinuity thresholds and a common track-distance
   reference before introducing physical corner labels or cumulative lap deltas.
   Current 20x-median spatial guards and 32-band coloring are disclosed visualization
   heuristics. Extreme values remain in the scale; they may compress ordinary colors.
5. Consider a bounded, explicit replay playback control after measuring Streamlit
   rerun cost. Keep actual sample identity/time visible and avoid changing recorded
   data or presenting retrospective playback as live acquisition.

The v0.6 sequence-model recommendation remains conditional, outside v0.6.1:

- Verify native acquisition/export-grid semantics; current LD exports declare
  50/100 Hz, which does not prove native real-time timing or interpolation latency.
- Expand independent human sessions within an explicit acquisition budget. Continue
  quarantining WL date conflicts and A-series identity ambiguity.
- Freeze a new future session holdout before model selection. The inspected v0.6
  test set is historical evidence, not a fresh unseen benchmark for subsequent work.
- Build masked observed-prefix sequence tensors with training-only scaling and
  complete lap/session partitions; test padding, gaps and future invariance.
- Compare any small Keras experiment against frozen tabular/baseline results and
  retain the target-free estimator API, trusted artifacts and explicit target reveal.

No additional acquisition, Keras training, live simulator integration, publication,
push or merge is authorized by this recommendation itself.
