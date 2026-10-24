# ML health assessment v0.6.2

This is an audit of the existing Monza / Dallara F317 experiment, not a new model
selection exercise. Production training/inference, feature definitions, artifacts,
splits and frozen v0.6 results were not changed. Test-set analysis below is descriptive
because that test set was already inspected in v0.6; it cannot become a fresh
selection benchmark for v0.7.

## Answers to the four development questions

**1. Is the system structurally and methodologically sound?** For the published
export-based, single-domain, future-recording experiment, the implementation is
coherent and no confirmed leakage, target-join, preprocessing or partition defect
was found. Audits reproduce all frozen aggregate metrics, verify the 55 source
targets and split memberships, and check both baselines against allowed training
history. Existing future-packet/clock-reset/held-out-label tests pass. This supports
the software contract, not broad statistical generalization or native live causality.

**2. Are credible algorithmic improvements worth investigating?** Yes: causal
progress/phase information, short-history event summaries, checkpoint-specific
calibration and removing redundant features deserve small development-only tests.
The present evidence does not establish which change will help. Early SVR outputs
are nearly constant, slow laps are underestimated, and the forest has a sizeable
training/validation gap. A larger network or more tuning is not an established remedy.

**3. Is the dataset the principal limitation?** Its small independent population,
skill/condition coverage and single domain are major established limits on what
can be validated. They are the strongest immediate reason to prioritize data.
The relative contributions of sample size, feature compression, regularization,
session shift and unforeseeable future events are **not causally identified** by this
one split. It would be unjustified to say that data size alone explains the error.

**4. Should we improve these models now?** Preserve the current estimators as the
working demonstration, prioritize more independent sessions and a new untouched
holdout, and preregister a small feature/phase comparison inside the development
pool. Do not tune on the old test set or start Deep Learning merely because SVR has
nonzero MAE. No production correction is currently evidenced as a prerequisite;
source-clock and identity assumptions must remain explicit and be strengthened
before stronger live/generalization claims.

## Evidence and reproducibility

Read inputs include [ML evaluation](ML_EVALUATION_V06.md),
[feature contracts](ML_FEATURES_V06.md), [dataset provenance](DATASET_EXPANSION_V06.md),
[frozen results](ML_RESULTS_V06.json), [individual errors](ACGYM_ML_ERRORS_V06.csv),
the pinned manifests and every production ML module. New calculations are in
[ML_HEALTH_EVIDENCE_V062.json](ML_HEALTH_EVIDENCE_V062.json) and
[ML_HEALTH_GROUPS_V062.csv](ML_HEALTH_GROUPS_V062.csv).

Reproduce with `python -m scripts.assess_ml_v062`. It:

1. Loads the hash-checked original adapter sessions, reconstructs the independent
   corpus and asserts exact frozen lap/session partition membership.
2. Checks every stored target against its source-validated lap, recomputes stored
   residuals and all six model/partition MAE, RMSE and bias rows at `1e-9 s` tolerance.
3. Recomputes descriptive checkpoint/lap/session/participant distributions from
   original recorded errors. Baselines are deduplicated across model rows.
4. Creates a separate development-only corpus: **29 training / 11 validation laps**.
   Exactly three fixed configurations are fitted on training prefixes, solely to
   inspect in-sample versus validation error. No test frame/label enters those fits,
   no parameter/feature variant is selected, and no artifact is saved.
5. Writes only explicitly allowlisted v0.6.2 evidence files and an ignored standalone
   residual figure, `artifacts/v062/ml_health_residuals.html`. Hashes of **16 original
   frozen-evidence/model-store files** are checked unchanged before/after.

`python -m scripts.verify_ml_v061` separately reproduces all **390 ACGym / 60 GT7**
frozen model-prediction rows within `1e-9 s`. Maximum prediction differences are
`2.842170943040401e-14 s` / `1.4210854715202004e-14 s`, consistent with CSV roundoff.
This regression is a preservation check, not a diagnostic tuning experiment.

## Population and independence

| Partition | Complete laps | Physical groups | Participant codes | Target range (s) | Median target (s) |
|---|---:|---:|---:|---:|---:|
| Training | 29 | 6 | 5 | 109.826–147.085 | 121.118 |
| Validation | 11 | 2 | 2 | 109.200–169.157 | 122.143 |
| Frozen test | 15 | 3 | 3 | 115.612–157.183 | 122.983 |

There are **55 laps, 11 physical groups, eight participant codes**, one car/track
and five prefixes per lap. The 145 training and 75 test prefixes are correlated
views of 29 and 15 laps, respectively. Laps within the same recording and repeated
participant remain related: the test has only **three recording groups**, not 75
independent opportunities to establish generalization.

Folders/dates and header agreement identify physical groups; multiple IN stints
stay in one group. Raw-capture hashes and one-second lap signatures exclude exact
copies. Fifty-one ambiguous A-series laps remain outside robust evaluation; the
WL date conflict remains quarantined. Exact deduplication does not prove that all
near-duplicates or shared conditions are independent. Participant codes are source
labels, not verified identities or measured skill ratings.

AB occurs in training and test; HC occurs in training and validation. The experiment
therefore evaluates future recording sessions with mixed recurring/new participants,
not strictly unseen-driver transfer. Participant/session identifiers are metadata,
not predictive inputs. One domain cannot support cross-car or cross-track claims.

## Structural and methodological review

| Concern | Verified implementation/evidence | Boundary of the conclusion |
|---|---|---|
| Targets and joins | Counter change, next-packet Last Lap Time, timer/grid/countdown and LDX beacons cross-check complete laps; every frozen target matches the adapter; many-to-one joins are checked | Source semantics and accepted complete valid laps define the population |
| Causal features | Prefix stops before first future/nonfinite time; later clock reset cannot bring future packets back; target/next-lap fields are absent from `ReplayLap` | Causal relative to published export, not certified pre-export interpolation latency |
| Preprocessing | Median imputer/scaler fit only on 145 training prefixes; RF appropriately omits scaling; allowlist excludes labels/provenance | Prefixes are correlated; training-row count is not independent lap count |
| Split integrity | All prefixes of a lap and all stints of a physical group stay together; exact membership matches frozen JSON | Source group identity is not external proof of independence |
| Chronology | Complete physical groups ordered by source date, recording/stint order and deterministic ties; validation/test dates follow the training period | Day/stint ordering is coarser than a verified absolute event clock; future same-day corpora need explicit capture-time validation |
| Same-day evidence | March 29 ST has stint order 1 / header 16:55, HC order 3 / 18:29; the observed order is consistent; held-out groups are on later dates | A potential coarse-clock ambiguity is a future validation concern, not an observed held-out leak |
| Features and units | Speed km/h, pedals %, RPM, reported gear and degree-qualified steering activity; all 13 training features finite in ACGym; missing optional inputs use train-only imputation | Steering/clock source calibration and information content still limit physical interpretation |
| Baselines | All held-out previous/median values match allowed, earlier, comparable training history; matched coverage is 75/75 test prefixes | These are frozen global training-history references, not an adaptive current-driver baseline |
| Evaluation | Validation MAE selected SVR before test reporting; frozen test metrics reproduce; no errors removed | Two validation groups cannot establish a stable ranking or significance |
| Serialization/UI | Local signatures checked before deserialization; training explicit; replay target hidden until requested | Trusted local store/source remains an assumption |

No discovered issue warrants declaring the architecture wrong or changing current
predictions. Eligibility is a necessary engineering gate, not a statistical guarantee.
Full-lap quality/target filters also mean the model describes accepted completed
laps; invalid or incomplete recordings may behave differently.

## What the errors mean

For each prefix, `error = prediction − verified target`. **MAE** averages absolute
errors, **RMSE** gives large misses more weight, and **bias** averages signed errors.
A negative bias means underestimating final lap time. These are pooled checkpoint
summaries, not calibrated uncertainty estimates. With five accepted checkpoints per
lap, pooled MAE also equals the mean of the 15 lap-level mean absolute errors, but
the five observations remain correlated.

| Model/reference | Validation MAE (s) | Test MAE (s) | Test RMSE (s) | Test bias (s) |
|---|---:|---:|---:|---:|
| Ridge | 9.506761 | 7.036799 | **10.259533** | -0.827959 |
| Random Forest | 9.266299 | 7.855905 | 11.125041 | -0.718241 |
| SVR, selected on validation | **9.150593** | **6.743072** | 10.837559 | -3.481268 |
| Previous training lap | 13.606909 | 12.081533 | 16.653834 | -11.953800 |
| Historical training median | 13.190727 | 9.443467 | 13.742608 | -7.375800 |

SVR's test MAE advantage over the median is **2.700394 s** (about **28.60%**), and
over the previous-lap reference **5.338461 s**. These are descriptive matched-row
improvements. SVR is not uniformly superior: Ridge has lower test RMSE and less
negative bias. Choosing Ridge now because of its already inspected test RMSE would
reuse the test for selection and is not performed.

Both frozen baselines are constant across these held-out dates: **116.540 s** for
the final allowed training lap and **121.118 s** for the training median. That is
intentional leakage protection. A real sequential replay might legitimately know
earlier completed held-out laps, but feeding them into the existing frozen benchmark
would change the estimand. An adaptive same-driver/session baseline is a future,
separately specified comparison; current results do not beat every possible baseline.

GT7 provides a useful counterexample to blanket ML-superiority claims. Recomputed
frozen CSV results from its experimental **4/2/2 lap split in one recording** give
test MAE **3.175213 s Ridge / 3.216453 s RF / 2.655780 s SVR**, versus **2.075000 s**
for the previous-training-lap baseline and **3.349000 s** for the training median.
All three models' test bias is positive. SVR beats the median but loses to the
previous-lap reference on those two test laps; a low absolute error is not proof
of useful improvement over an appropriate baseline. The tiny same-session population
cannot establish generalization or select an architecture. No new GT7 fit or tuning
is performed for this diagnosis.

SVR test residuals have **36 positive / 39 negative** values, signed median
**-0.271819 s**, median absolute error **3.423003 s**, 90th-percentile absolute error
**15.466553 s** and maximum **37.278817 s**. Thus a small signed median coexists
with a negative mean bias and a severe tail. The full errors remain in the assessment.

## Checkpoint and horizon behavior

| Checkpoint (s) | Test laps | SVR MAE (s) | RMSE (s) | Bias (s) |
|---:|---:|---:|---:|---:|
| 10 | 15 | 9.470686 | 13.901665 | -7.647252 |
| 20 | 15 | 7.344753 | 11.071623 | -3.836186 |
| 30 | 15 | 5.937101 | 10.525745 | -3.233985 |
| 45 | 15 | 6.316485 | 10.528691 | -2.034414 |
| 60 | 15 | 4.646338 | 7.055614 | -0.654502 |

Later information generally helps, but 45 s MAE is worse than 30 s and improvement
is not guaranteed per lap. At 10 s, all 15 test laps receive SVR values in only
**120.548594–121.477715 s**, despite actual times spanning 115.612–157.1825 s.
The early model is essentially near the training center; a reasonable prediction
there can reflect a plausible prior, not detailed knowledge of the eventual lap.

Descriptively, the checkpoints observe about **5.9–9.2%** of a completed lap at
10 s and **35.5–54.9%** at 60 s. The model is still forecasting a substantial
unobserved remainder. These fractions use final labels only for this retrospective
analysis and never enter the predictive feature contract.

## Complete laps, sessions and participant effects

| Frozen test group / participant | Laps | SVR MAE (s) | Bias (s) | Share of total SVR absolute error |
|---|---:|---:|---:|---:|
| 20240424_KW / KW | 5 | 4.332106 | +0.471003 | 21.42% |
| 20240425_RRK / RRK | 5 | 3.432849 | +0.666935 | 16.97% |
| 20240426_AB / AB | 5 | 12.464262 | -11.581741 | **61.62%** |

The severe tail is concentrated, not spread uniformly. AB already occurs in
training, so this cannot simply be attributed to an unseen participant identifier.
Session conditions, incidents, driving variability and incomplete feature coverage
are competing explanations; no causal attribution to skill/setup is established.
Per-participant aggregation is descriptive and confounded with the three test
recording groups. Full lap/session/participant rows are retained in the group CSV.

The largest miss is AB **lap 2**, verified **157.1825 s**, predicted **119.903683 s**
at 30 s (error **-37.278817 s**). Its 10/45 s errors are also about -36 s, so
these are repeated views of one difficult lap rather than three independent
failures. Retrospective telemetry shows speed **6.655 km/h at 60 s**, a minimum
of **0 km/h at 74.01 s**, and **18.0 measured seconds below 30 km/h after 60 s**
(9.82 s before/through 60 s). This documents a slow/stationary segment; it does
not identify a collision, spin, pit visit or cause from speed alone.

Other large cases include AB lap 4 (145.0775 s, about 12.955 s below 30 km/h before
60 s) and KW lap 2 (137.1875 s, about 16.02 s below 30 km/h before 60 s). Some
slow behavior is already observed, while some future delay is unavailable at the
checkpoint. Better temporal features may help the first case; no causal model can
know an unobserved future event's exact duration. None of these laps was excluded.

## Regression toward central times

Training-only target quartiles are **115.443333 s / 131.997500 s**. SVR behaves
differently across those predefined bands:

| Population | Laps / prefixes | MAE (s) | Bias (s) |
|---|---:|---:|---:|
| Test within training middle band | 9 / 45 | 3.139449 | +1.084151 |
| Test slower than training Q75 | 6 / 30 | 12.148507 | -10.329396 |
| Validation faster than training Q25 | 4 / 20 | 5.642587 | +5.553317 |
| Validation slower than training Q75 | 3 / 15 | 21.032602 | -21.032602 |

There are no test laps below training Q25, so test behavior for that band cannot
be estimated. The validation slow tail extends beyond the training maximum;
the test also contains times above it.

Averaging the five predictions within each test lap, prediction-versus-target
slopes are **0.313 Ridge / 0.257 RF / 0.317 SVR**; the identity slope would be 1.
SVR's lap-mean predictions span **117.801–134.622 s**, much narrower than actual
targets. Its lap-level residual/actual correlation is **-0.887**. This is consistent
with central shrinkage and inadequate slow-tail adaptation. Residual/target
correlation is partly mathematical because the target is subtracted in the residual;
the slopes, ranges and explicit band errors provide additional evidence. No
correlation is presented as a causal mechanism or significance test.

## Model and feature limitations versus dataset limitations

The isolated fixed-configuration fits produce:

| Model | In-sample training MAE (s) | Existing validation MAE (s) |
|---|---:|---:|
| Ridge | 7.421093 | 9.506761 |
| Random Forest | 3.978978 | 9.266299 |
| SVR | 5.944651 | 9.150593 |

In-sample scores are optimistic descriptions, not a new benchmark. The forest's
larger gap is consistent with fitting training-specific patterns, but session
shift and the small validation population prevent identifying pure overfitting.
SVR already has training bias **-2.430302 s** and substantial tail errors; model
regularization, compressed features and limited examples of slowing can all matter.
Ridge's comparatively high training error does not by itself prove that a nonlinear
sequence model will solve the task. The three validation MAEs are close, using only
two recording groups; their rank is not shown statistically stable.

The 13 features are causal aggregates/current values with sensible declared units.
They compress order, duration and location of events. The same elapsed checkpoint
can correspond to different track positions for different laps. A fixed 3 s recent
window and whole-prefix averages may hide specific braking/recovery patterns.

Training-only feature correlations include checkpoint/observed-time **0.99999994**,
throttle mean/high-throttle fraction **0.974**, current/recent mean speed **0.957**,
and current speed/gear **0.942**. Redundancy is measured; deleting features is not
automatically beneficial, especially with only six training sessions. Importance
from correlated prefixes/features is not a physical causal ranking.

The practical diagnosis separates three categories:

- **Structural/methodological:** no confirmed implementation fault in the frozen
  experiment; verify source timing, independence and absolute chronology more
  deeply before extending its claims. No leakage fix is invented to explain MAE.
- **Algorithm/feature:** measured central shrinkage, checkpoint dependence and
  compression/redundancy justify controlled causal feature/phase experiments. A
  superior replacement architecture has not been demonstrated.
- **Data:** six training groups, two validation groups, slow-tail/session variability,
  a three-group test, recurring participants and one domain sharply limit both
  learning coverage and the strength of the diagnosis. Source 50/100 Hz exports
  and held samples do not certify native acquisition or resampling latency.

## Prioritized experiment plan for v0.7

1. Preserve this frozen benchmark and current estimator APIs. Validate source
   acquisition/resampling/hold semantics and capture-level absolute chronology;
   retain quarantines and deduplication evidence. This is required for stronger
   real-time claims even if current export-based regression remains useful.
2. Expand the **same car/track** across independent dates, participants and balanced
   normal/slow/recovery conditions. As a planning target, seek roughly **20–30 new
   recording groups**, not thousands of prefixes from one drive. Retain all valid
   difficult laps and collect meaningful condition metadata. Those counts are a
   design target, not a statistical sufficiency guarantee.
3. Before any variants, reserve a new chronological holdout of about **8–10 physical
   recording groups**, aiming for roughly **40–60 complete laps** with varied pace.
   Preserve whole sessions and specify a separate participant-disjoint evaluation
   if unseen-driver performance is a claim. More independent groups may be needed;
   estimate precision/power from group-level errors rather than prefix count.
4. Inside the remaining development sessions, use chronological/group-aware folds
   and a small learning curve. Compare the same fixed estimator at increasing
   numbers of independent sessions to test the data-limitation hypothesis.
5. Preregister a small comparison: current aggregates, reduced redundant features,
   and a causal phase/event summary (for example verified current source progress,
   duration of low-speed/recovery already observed, or short bounded histories).
   No eventual-distance normalization, future sample or target-derived progress.
   Match model/baseline rows and keep preprocessing inside each training fold.
6. Specify frozen and genuinely available rolling-history baselines as distinct
   protocols. Compare by checkpoint and group, including slow laps, with cluster-aware
   uncertainty. Do not pool correlated prefixes into false sample-size claims.
7. Only after those results consider a small sequence model against frozen tabular
   references. Temporal order may add information; Deep Learning is not presumed
   better and cannot recover unobserved future incidents. A different car/track
   requires a separate domain evaluation rather than a universal accuracy claim.

No new acquisition, production retraining change, hyperparameter search or Deep
Learning implementation is part of this release.
