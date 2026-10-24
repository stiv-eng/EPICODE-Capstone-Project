# Model assessment v0.7.2

**Decision: preserve the current SVR as the educational reference. Stop expanding
this unsuccessful compact feature search. A small, bounded sequence-model study
is a justified next research comparison, not an established superior replacement.**

## 1. Is the existing SVR functioning correctly?

Yes within the verified contract. It fits direct final seconds from the original
13 causal columns; historical median is separate, not its target or an output
offset. The signed reference, frozen rows and current validation predictions
match. No target, preprocessing or causal-boundary defect was found. Diagnostic
export-derivative spikes concern the new F1 descriptors, not an identified defect
in the original reference target. Source latency and unknown session links remain
limitations rather than demonstrated coding errors.

## 2. Is there useful telemetry-dependent information beyond a constant reference?

Yes. F0 development OOF MAE is **13.361 s**, compared with **22.641 s** for each
fold's training median on the same 169 laps. Controlled prefix-only speed changes
change outputs; later checkpoints generally provide more information. This is a
useful demonstration, with substantial slow-tail error and imperfect calibration.

## 3. Do the tested causal features meaningfully increase reliability?

No. F1/F2/F3 MAEs are **13.381/13.424/13.400 s** against F0 **13.361 s**, with
no recording-macro improvement and improvements in only one or two folds. Fold
variation (~4.1 s SD) dwarfs the changes. These fixed configurations do not
establish that all temporal representations fail; richer features also change
RBF distance/gamma geometry and some raw derivatives are noisy. They do establish
that the tested additions do not justify replacement or a positive success claim.

## 4. Is slow-lap underprediction reduced?

Only slightly with the temporal families: F0 slow MAE/bias **36.922/-35.804 s**,
F3 **36.772/-35.474 s**. Weighting gives **34.115/-32.200 s**, but worsens middle
MAE and recording-macro error and improves only one fold. No change passes the
prespecified acceptance rule. Training contains 26 slow laps and the broadest
target range, so absence of slow examples is not the explanation. Limited
conditional coverage, information loss, fixed regularization and future events
remain plausible contributors that this dataset cannot causally separate.

## 5. Is SVR still sensible?

Yes as a compact tabular reference and educational demonstration, not a precision
race-time service. OOF slope **0.351**, prediction/target SD ratio **0.511** and
slow bias show a practical limitation. The experiment supports a plateau for
these aggregates and settings, not a universal statement that SVR cannot improve.

## 6. Would further classical ML work be useful?

A bounded, independently specified study could still be useful: verify true
current-phase semantics, test one redundant-time removal or one robust temporal
representation, and compare a small classical sequence/flattened-window baseline.
Do not begin a large C/gamma/epsilon grid or repeatedly tune this historical test.
No new classical algorithm or parameter search was added after these results.
Ridge/RF/SVR v0.7.1 remains intact; its historical-test MAE is not used to choose
any v0.7.2 variant.

## 7. Is a sequence-based deep-learning experiment justified?

As a small **feasibility experiment**, yes: a sequence retains event order that
aggregates discard. It is not proven necessary or better. At 10 s some observed
trajectories are almost identical despite targets differing by ~40 s; a network
cannot reliably observe an incident that has not happened. The effective sample
size is 169 development laps in 40 imperfect blocks, not 845 independent examples
or millions of independent time samples. Overfitting is a serious practical risk.
No sequence model or new deep-learning experiment was implemented or trained here.

## 8. What should the next release implement?

Keep the present reference and development protocol, then run one limited ordered
prefix pilot against unchanged F0, F3 and the fold-training baselines. Prefer a
small GRU or causal 1D CNN, with a simple classical ordered-window comparator,
training-only normalization and group-aware validation. Fix the comparison before
fitting, report all folds/pace tails and stop if no meaningful gain appears. A new
untouched final holdout is needed for a new final-performance claim; the present
36 historical test laps remain descriptive evidence. Verifying phase information
may be more informative than increasing network depth. No further data acquisition
or live capture is part of this release.

## Sequence feasibility specification for a future release

| Aspect | Bounded proposal |
|---|---|
| Inputs | Six existing source channels: speed, throttle, brake, RPM, gear, steering; explicit timestamps/availability masks; optional verified phase only after its semantics are established |
| Causal grid | 10 Hz timestamps up to the checkpoint; last-known observation only, no centered/right-neighbor interpolation and no joining across source discontinuities |
| Prefix sizes | 100/200/300/450/600 steps for 10/20/30/45/60 s; use checkpoint-length prefixes, never full-lap length or eventual distance |
| Tensor | At most (845,600,6) float32 before development folds; ~12.17 MB (11.60 MiB) padded values, ~0.51 MB boolean mask, timestamps ~2.03 MB if explicit |
| Missing/padding | Right-pad after train-only normalization; mask padding and unsupported channel/time cells; do not infer missing observations or let padding encode final duration |
| Resampling | Audit real timestamp support and native/export cadence separately; keep first unavailable times masked; cap permitted sample age and reject/mark gaps, not interpolate through them |
| Training size | 169 unique development laps, training folds 122–153 laps / 32 blocks; five prefixes per lap stay together; no historical-test sequences in fitting |
| Architecture budget | One small GRU (e.g. 16 hidden units) or small causal Conv1D encoder, few thousand parameters; no architecture sweep or presumption that LSTM/deeper is better |
| Normalization | Fit channel statistics and any output transform only on fold training; inverse-transform predictions to final seconds for all comparisons |
| Fitting/evaluation | Same outer five recording folds; early stopping only on an inner block split of training, not the outer evaluation fold; fixed seeds/configuration and equal lap treatment |
| Controls | F0/F3, training-median and supported previous-lap references, plus a modest classical ordered-window baseline to separate sequence information from neural architecture |
| Compute | Small inputs can be piloted on CPU; GPU optional. Measure actual memory/runtime on the first fixed pilot instead of promising a runtime or installing new infrastructure |
| Success | Consistent fold/recording gains, retained slow/fast coverage, calibrated spread and bounded complexity; not simply more variable outputs or a better single run |

Unknown capture links, recurring participant codes and partial future observability
limit any architecture. A sequence pilot is a research decision under uncertainty;
it does not justify deployment, replacement or a claim of new independent test
improvement today. See [experiments](ML_FEATURE_EXPERIMENTS_V072.md) and
[pace diagnosis](PACE_DISTRIBUTION_AUDIT_V072.md) for the measured evidence.
