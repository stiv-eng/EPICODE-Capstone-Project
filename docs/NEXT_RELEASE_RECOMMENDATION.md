# Recommendation after v0.6

Develop v0.7 as a **bounded Keras sequence-model experiment**, with a frozen
session holdout and continued tabular/baseline comparison. Do not treat the 30-lap
engineering gate or the current SVR result as evidence that a deep model has
enough independent data.

1. Validate upstream acquisition/resampling semantics. The current LD grids are
   50/100 Hz exports; source packet timestamps and export interpolation/hold latency
   need verification before claiming native real-time prediction. Prefer a documented
   numeric raw export; do not deserialize unknown dataset pickle files.
2. Expand the same car/track with independent human recording sessions first,
   preserving hotspot limits and explicit download budgets. Resolve/quarantine the
   WL date conflict and A-series identities rather than silently adding their laps.
3. Reserve a new final test period before experiments. Use grouped rolling
   session-validation folds inside the remaining development data; optionally hold
   out participants separately to distinguish future sessions from unseen drivers.
   The current v0.6 test set has already been inspected and must not become a fresh
   unseen test for subsequent model selection.
4. Build masked prefix sequence tensors using observed source time only. Fit any
   scaling/resampling parameters on training data, preserve all prefixes of a lap
   in one group, and test padding, variable lengths, gaps and future invariance.
   No final-distance normalization, future packets or completed-lap statistics.
5. Start with a small Keras sequence network and early stopping on grouped
   validation. Compare each checkpoint against frozen v0.6 Ridge/RF/SVR and the
   permitted historical baselines. Report per-lap/session errors, coverage and
   driver/conditions shifts; avoid model-size or accuracy claims based on prefix count.
6. Wrap the model behind `ml.inference.predict`'s target-free estimator contract.
   Preserve explicit retrospective target reveal and trusted local artifact handling.
   Live simulator ingestion and calibrated uncertainty require separate validation.

The v0.6 corpus provides a useful engineering and presentation foundation: 55
usable laps / 11 source-identified sessions, 275 causal checkpoints, three fitted
models and auditable independent errors. It supports this next experiment; it does
not yet support broad cross-car, cross-track, real-world or live generalization claims.
