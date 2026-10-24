# Recommendation after v0.6.3

Preserve the current production models and prioritize independent data coverage
and a new untouched holdout. The [ML health assessment](ML_HEALTH_ASSESSMENT_V062.md)
found no confirmed target/leakage/preprocessing/split defect in the frozen experiment.
It did find central shrinkage, poor slow-tail adaptation and concentration of SVR
error in one recording. Small sample size, feature compression, session shift and
future-event uncertainty cannot be causally separated with the present split.

## First: strengthen evidence before model complexity

1. Verify source clock/export interpolation/hold semantics and capture-level absolute
   chronology. Current 50/100 Hz export grids are not proof of native live latency.
   Continue hash checks, complete-lap target validation, raw/lap deduplication and
   quarantine of ambiguous A-series identity and the WL date conflict.
2. Expand the same Monza/Dallara domain across independent dates, participants and
   pace/condition profiles. A planning target is about 20–30 new physical recording
   groups, with normal and slow/recovery behavior represented. This is a collection
   design target, not a guarantee of statistical adequacy; no acquisition is
   authorized merely by this document.
3. Before experiments, reserve a new future holdout of roughly 8–10 recording groups
   and 40–60 complete laps if feasible. Preserve full groups and specify whether
   recurring or unseen participants are being evaluated. Assess precision at the
   recording-group level, not by counting five prefixes as five independent laps.
4. Use group-aware chronological validation and a modest learning curve inside
   development sessions to distinguish data-size effects from feature/model limits.
   The already inspected v0.6 test set remains historical evidence, not a new
   selection set. Retain difficult valid laps rather than improving metrics by removal.

## Then: a small, preregistered diagnostic comparison

- Compare current aggregates with a reduced redundant allowlist and one bounded
  causal phase/event/history representation. Current source progress may be useful
  only with verified semantics and no eventual-distance/target normalization.
- Consider checkpoint-specific behavior and already observed slowing/recovery,
  evaluating all alternatives on the same rows with training-only preprocessing.
  Do not infer that Deep Learning is the solution from the existing training gap.
- Specify frozen-history and genuinely available rolling-history baselines as
  separate protocols. GT7's previous-lap baseline already beats its selected SVR
  on the two frozen test laps; ML superiority is not automatic.
- Report MAE, RMSE, signed bias, tail errors, checkpoint and recording/participant
  coverage, with group-aware uncertainty. Use one final new holdout evaluation
  after decisions are frozen; avoid dozens of variants on two validation groups.
- Only afterward consider a small sequence experiment against unchanged tabular
  references. Preserve target-free inference, explicit retrospective evaluation,
  trusted artifacts and source/unit contracts. New car/track claims need separate
  domain holdouts; future incidents remain inherently unobserved at early checkpoints.

## UI follow-up

The shared external hover/cursor work is delivered in v0.6.3; do not reintroduce
native labels or expand this into model experiments. See the release chart audit
and browser evidence for the precise verified scope.


- Test the shared readout on Firefox/Safari, physical touch devices and screen
  readers. Desktop Chrome verifies temporal keyboard stepping, 1600/960/480 px
  layout, real hover and cursor geometry; full accessibility certification remains.
- Measure long-session memory and repeated selection changes on ordinary laptops,
  including forced-GC diagnostics before calling growth a leak. Content-hashed
  browser caching removes repeated runtime transfer and grouped figures reduce
  runtime instances; separate components still parse their own Plotly runtime.
- Evaluate the strict original-cadence nearest-sample policy with users. Preserve
  explicit observed timestamps and honest missing states; do not silently enlarge
  tolerance to hide decimation gaps or expose full-lap replay targets.
- When optional FastF1 data is locally available, exercise all complete legacy page
  workflows offline. Current migration/type fixtures do not establish a full
  externally acquired weekend/Keras acceptance result.
- Obtain documented ACGym world X/Y or a verified planar heading source if needed.
  Race rank/progress must not become a fabricated map, and GT7 quaternions must not
  become heading without a documented convention.
- If the old FB-007 disappearance recurs on the user's device, collect its exact
  browser/GPU/selection/scroll and console context. The old symptom remains
  unreproduced; current SVG/section/marker/hover workflows passed the stated checks.

No new Keras network, model change, large acquisition, push, merge or publication
is authorized by this recommendation itself.
