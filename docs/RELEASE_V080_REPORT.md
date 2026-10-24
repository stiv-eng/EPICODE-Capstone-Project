# Release v0.8 — Dense progressive prediction and sequential ML

Branch `feat/sim-telemetry-v080`, from verified v0.7.2 `36b1267`. Initial tree
was clean; **233 baseline tests passed in157.67 s** and signed/frozen Monza, GT7
and Barcelona checks passed before branching. No push, merge, reset, branch
deletion, new telemetry acquisition or operational model promotion.

All **205 valid Barcelona laps remain preserved**. Research excludes the 36
already-inspected historical test laps before representations and uses the
original 169 development laps /40 recording blocks and five v072 folds. Unknown
physical links and overlapping training sets limit inference: these are
exploratory development results, not a fresh independent final test.

## Executed comparison

The causal elapsed-time fallback emits every 5 s, with configurable cadence and
original 10/20/30/45/60 s compatibility. There are **4134 correlated prefixes**,
19–51 per lap,5 through 255 nominal seconds, with actual source cutoffs retained.
ACTI progress semantics remain insufficiently verified; no eventual-duration
fraction or completed-distance normalization is used as track progress.

OOF MAE in seconds; every candidate sees the same available observations:

| Candidate | Full trajectory, equal lap weight | Shared 5–60 s | Original sparse points | Last scheduled point |
|---|---:|---:|---:|---:|
| SVR-SPARSE, fixed fold fit / denser inference |14.410|13.695|13.361|21.452|
| SVR-DENSE, direct target |8.602|12.836|13.058|3.227|
| SVR-REMAINING |8.733|13.502|13.587|4.066|
| Conditional remaining reference |19.503|22.641|22.641|19.893|
| RIDGE-ORDERED |12.656|14.860|14.974|6.573|
| Keras GRU |11.241|14.425|14.244|5.738|
| Training historical median |22.641|22.641|22.641|22.641|

Full-trajectory MAE averages each lap's checkpoint errors, then laps equally.
Recording macro averages lap means within blocks, then blocks equally. Shared
seconds, last-point and retrospective final10 s summaries remain separate.
Complete RMSE/bias/median/P90/max, folds, pace, calibration, spread, consistency
and checkpoint survivor counts are in [the comparison](ML_COMPARISON_V080.md).
No legitimate slow lap or outlier is removed.

## 1. Does more frequent prediction improve the practical experience?

Yes:19–51 observations replace five in experimental replay, adding feedback
between original points and beyond 60 s. **Cadence alone does not improve a shared
prediction**: original sparse outputs match frozen v072 F0 within 2.842e-14 s.
The immutable production SVR separately gets dense inference on its66 original
validation laps: sparse MAE9.868 s, dense 5–60s10.460 s, full dense 12.009 s.
Those pooled scores mix different horizons; they do not measure a cadence-only
accuracy gain. The sparse model extrapolates beyond its60 s training support.

Dense fitting separately improves shared5–60s13.695→12.836 s,0.859 s/6.27%,
with gains in four of five folds; full trajectory14.410→8.602 s, all five folds.
Original sparse-point gain is smaller:13.361→13.058 s. Dense lap-balanced loss
weights have mean 1, so total loss mass relative to sparse fixed C10 also changes.
The full gain cannot be attributed purely to density at fixed regularization.

## 2. Does remaining-time SVR improve, particularly late?

**No overall improvement in this fixed comparison.** Same dense inputs/settings:
remaining MAE12.836→13.502 s at 5–60 s,8.602→8.733 s overall,3.227→4.066 s at the
last point,5.637→5.767 s beyond 60 s. Slow absolute bias improves slightly
19.249→18.628 s while slow MAE worsens22.518→22.869 s. No tuning is added.

Remaining prediction guarantees final>=observed after explicit projection.
Six raw negatives occur; lap-balanced projection fraction0.001319 and MAE effect
−0.000762 s. Raw values remain visible. The unconstrained dense direct model has
43 outputs below observed elapsed: those failures are retained, not silently
projected. Greater spread/calibration slope alone is not accepted as improvement.

## 3. Does ordered classical ML beat aggregate SVR?

**Not at common early/middle observations or against dense SVR.** Ridge14.860 s
exceeds sparse SVR13.695 s and dense SVR12.836 s at 5–60 s. Ridge full-trajectory
12.656 s beats sparse 14.410 s, but the latter has no late training horizons.
Dense SVR8.602 s is stronger overall. Representation and estimator change together;
there is no shuffled-order control, so ordering alone is not causally isolated.

## 4. Does GRU provide an advantage over ordered Ridge?

**A qualified development gain, not demonstrated neural necessity.** GRU11.241
versus Ridge12.656 s improves full trajectories by1.415 s/11.18%, four of five
folds, recording macro10.368 versus 12.081 s. Shared 5–60 s gain is0.435 s,
14.425 versus 14.860. Early5–30 s GRU16.459 s is worse than Ridge15.826 s; late
8.786 s beats11.156 s. Dense aggregate SVR remains better overall and at 5–60 s.

Both receive identical chunks/context/cutoffs and remaining labels. GRU reserves
inner validation blocks and fits fewer laps than Ridge; regularization and
nonlinear architecture differ. This compares practical procedures, not a pure
causal effect of recurrence or order.

## 5. Does GRU improve every pace band?

**No.** GRU fast/middle/slow MAEs6.324/10.133/21.274 s versus Ridge
7.918/9.241/26.586 s: middle worsens. Against dense SVR3.232/5.764/22.518 s,
GRU worsens fast/middle and slightly improves slow. Slow bias remains−15.034 s.

## 6. What explains remaining errors?

Measurements support sparse late extrapolation, remaining central shrinkage,
broad slow-tail error and limited recording coverage. Dense fitting helps at
shared times; ordered models do not dominate aggregate SVR. The v072 similar10 s
prefixes with different eventual targets remain evidence of early ambiguity,
not proof of a specific unobserved future incident.

Future incidents, insufficient conditional diversity, chunk information loss
and regularization/calibration remain plausible contributors. This study cannot
identify one predominant causal explanation or establish physical independence.
At 255 s only one difficult259.595 s lap remains: dense-direct error55.134 s,
remaining31.440 s; GRU/Ridge/reference return the elapsed lower bound with4.605 s
error. Low mean last-point error across 169 laps must not conceal this failure.

## 7. Which model remains operational?

**Original signed SVR v0.7.1.** Dense direct is the strongest practical research
candidate here, but reused development evidence cannot promote it. Historical
results are unchanged and experimental historical-test evaluations stay zero.
New untouched observations are required for a new final-performance claim.

## 8. What should the next release develop?

Preregister a small dense-SVR follow-up matching total per-lap penalty mass,
with one separately specified physically consistent late bound and genuinely
untouched same-domain observations when available. Obtain an exact ACTI export
contract before percentages. Retain GRU as a reproducible capstone demonstration;
avoid an architecture grid. If pure neural/order attribution is required, match
fitting groups and predeclare one order-destruction control in the next study.

## Implementation and actual compute

Six channels undergo backward-only 10 Hz sampling, then whole-prefix ordered2 s
compression. Ridge/GRU also receive the same 13-feature causal context. Fixed600 s
support, actual partial chunks, training-only transformations and explicit
boolean padding masks avoid60 s truncation and eventual-length inputs. Compression
loses sub 2 s order; this CPU/memory tradeoff is documented.

GRU actually trained: Keras 3.15.1/Torch 2.14.1 CPU, two threads,1737 parameters.
Five outer folds use four inner training blocks for early stopping. Best epochs
11/20/2/20/11, runs15/20/6/20/15. Outer training514.204 s; separate all 169-lap
research fit11 epochs/108.766 s. Peak OS working set935219200 bytes during outer
work,1083219968 bytes including final fit; includes corpus/sklearn/backend, not
GRU-exclusive memory. No GPU or infrastructure installation.

Opt-in replay loads the fold that excluded the selected lap, reproducing OOF,
rather than the all-development research fit. Compatible artifacts are signed;
native Keras bytes are verified against an authenticated digest before safe-mode
loading. Target/pace/error data do not enter predictive figures or inference.
Explicit reveal adds retrospective metrics without changing causal charts.
Normal reruns do not train; the default operational mode remains unchanged.

## Verification and acceptance

[Verification summary](VERIFICATION_V080.json), [browser records](UI_BROWSER_V080.json),
[98-file preservation inventory](BASELINE_PRESERVATION_V080.json),
[frozen regressions](FROZEN_REGRESSION_V080.json), [checkpoints](CHECKPOINT_STRATEGY_V080.md),
[SVR](SVR_DENSE_EXPERIMENT_V080.md), [sequences](SEQUENCE_MODEL_EXPERIMENTS_V080.md),
[architecture](ARCHITECTURE_V080.md) and [next steps](NEXT_RELEASE_RECOMMENDATION.md).
Six standalone PNG/SVG figure families accompany the reports.

Preservation checks cover98 v071/v072 document/model/F5 hashes,450 historical
Monza/GT7 rows,1170 stored Barcelona rows and330 current validation predictions
within 1e-9 s, without new historical-test predictions. Existing tests are retained
without weakening; exact final test/browser counts are in the linked summary.

| Acceptance | Evidence |
|---|---|
|AC1,AC11,AC12|205 laps,98 preserved hashes, historical exclusion, operational signed reference|
|AC2,AC3|Causal configurable5 s cadence, real timestamps, cadence-only and dense-fit comparisons|
|AC4,AC5|Executed remaining SVR, raw constraints, training-only conditional reference|
|AC6,AC7|Executed Ridge/GRU; actual history, memory and duration|
|AC8–AC10|Same4134 observations, block folds, equal-lap metrics, early/late/pace/tails|
|AC13|Opt-in OOF model inspection, dense replay, hidden target and explicit reveal|
|AC14|Full automated suite, real Chrome workflows and historical regressions|
|AC15,AC16|Eight measured conclusions, negative outcomes retained, next research recommendation|

Final complete suite: **257 passed, zero skipped, 217 Keras/Torch NumPy deprecation warnings, 189.52 s**. All 233 original tests are retained and 24 new tests pass. Actual Chrome: **88 v080 workflow checks +55 render budgets +1 performance record**, plus **36 retained archive checks** and **4 legacy fixture checks +4 budgets**. All three scenarios have zero console errors/runtime exceptions. Compileall, pip check and whitespace checks pass.
