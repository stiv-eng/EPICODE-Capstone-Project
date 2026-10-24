# Recommendation after v0.7.2

**Preserve SVR v0.7.1 as the operational educational reference. The compact
feature-engineering study has reached a practical plateau under the tested
settings. A limited ordered-sequence pilot is the next research comparison;
neural superiority has not been demonstrated.**

The five-fold development study uses 169 laps / 40 recording blocks and excludes
the 36 already-observed historical test laps before feature generation. F0 MAE is
13.361 s; recent/event/combined variants are 13.381/13.424/13.400 s. None improves
recording-macro error or four of five folds. One weighting intervention reduces
pooled MAE by only 0.044 s and slow MAE by 2.807 s, while worsening recording-macro
MAE by 0.822 s and middle MAE by 1.563 s. Keep it as a documented tradeoff, not a
new preferred model. All 205 valid laps remain available and none is filtered.

Training has 26 slow laps and the widest target range. Validation's fast-heavy
composition plausibly contributes to its lower historical error, but does not
explain development slow bias (-35.804 s). F0's SD ratio 0.511 and slope 0.351
show central shrinkage. Identical early observed patterns can have different
future outcomes; neither a scalar model nor a sequence network can know an
unobserved incident with certainty.

For the next release:

1. Keep the reference, raw files, original split and frozen metrics immutable.
   Reuse the fixed development folds for research, with honest unknown-link limits.
2. Predefine one small GRU or causal 1D CNN ordered-prefix pilot, with a modest
   classical ordered-window comparator. Use six current source channels on a
   causal timestamp-supported 10 Hz grid, masking unsupported/padded values.
   A padded (845,600,6) float32 development tensor is about 12.17 MB; there remain
   only 169 unique development laps. Avoid a large architecture/parameter search.
3. Use training-only normalization and inner recording splits for early stopping;
   report every outer fold, recording-macro, checkpoint and pace tail, plus
   prediction spread/calibration and all deterministic baselines. Do not select
   on greater variability alone or cherry-pick favorable example laps.
4. Verify source phase/progress export semantics before adding a current-position
   family. The speed integral already tested is a path-distance proxy, not a
   certified phase or target-normalized fraction. Raw derivative spikes also need
   an independently specified robust representation if studied again; do not
   silently clip/remove difficult laps to rescue the present experiment.
5. Require a **new untouched final holdout** for any new final-performance claim.
   Existing historical test labels may describe distributions but cannot tune
   features, weights or architecture. Additional diverse same-domain data would
   strengthen evidence, but is not a gate on useful experiments and was not
   acquired here.

No deep-learning model was added in v0.7.2. The recommendation authorizes no push,
merge, new acquisition or live simulator recording. Scope and tensor/evaluation
details are in [model assessment](ML_MODEL_ASSESSMENT_V072.md), with actual numbers
in [feature experiments](ML_FEATURE_EXPERIMENTS_V072.md) and
[pace audit](PACE_DISTRIBUTION_AUDIT_V072.md).
