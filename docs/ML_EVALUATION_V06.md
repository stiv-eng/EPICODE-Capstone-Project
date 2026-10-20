# ML evaluation v0.6

The independently identified ACGym subset passes the minimum engineering gate:
55 verified laps, 11 physical recording groups, eight participant codes, one
Monza/Dallara domain, 100% valid key-signal coverage. This remains a small,
heterogeneous simulator case study with limited independent sessions.

## Frozen methodology

Sessions are ordered by source date, then physical ID for deterministic same-date
ties. The earliest six sessions provide **29 train laps / 145 prefixes**; the next
two sessions provide **11 validation laps / 55 prefixes**; the latest three provide
**15 test laps / 75 prefixes**. Every prefix of every lap stays together. Multiple
stints of one session stay together. No telemetry-row random split is used.
Exact memberships, driver labels and chronology are in
[ML_RESULTS_V06.json](ML_RESULTS_V06.json).

The three models use the same 13 causal features and fixed modest configurations:

- Ridge: alpha 10, training-median imputation, then training-fitted standardization.
- Random Forest: 120 trees, depth <=6, leaf size >=2, seed 42, one worker,
  training-median imputation. Tree inputs do not need scaling.
- RBF SVR: C=10, epsilon=0.5 s, default scale gamma, training-median imputation and
  training-fitted standardization.

No tuning grid or adaptive feature search was justified by 11 validation laps in
only two sessions. Parameters were not tuned after inspecting test results. Models
remain fitted only on training data; there is no train+validation refit before
reporting test scores. The lowest validation MAE selects **SVR**. All three frozen
test results remain available as an audit; comparing them is not a new selection
step. No Keras architecture was trained for v0.6.

## Deterministic references

The previous-valid-lap and historical-median baselines use only comparable-domain
laps belonging to **training**, whose completed end order precedes the replayed
lap's start. Current, future, validation and test labels are never history entries.
Thus these are deliberately frozen historical references; validation/test outcomes
do not update them even when a later replay would chronologically know the result.
The first comparable lap has no baseline. There is no fallback to a future median
or final-distance formula. Comparisons use exactly the rows where both model and
baseline predictions are available, with matched-row/lap coverage shown.

## Measured ACGym results

All errors are `predicted - verified`, in seconds. The following pooled prefix
statistics cover five checkpoints per lap; they are **75 correlated prefixes from
15 independent lap groups in three physical sessions**, not 75 independent laps.

| Model | Validation MAE | Test MAE | Test RMSE | Test bias |
|---|---:|---:|---:|---:|
| Ridge | 9.507 | 7.037 | 10.260 | -0.828 |
| Random Forest | 9.266 | 7.856 | 11.125 | -0.718 |
| SVR (selected on validation) | 9.151 | 6.743 | 10.838 | -3.481 |

On the same 75 test prefixes, previous-lap MAE is **12.082 s**, and historical
median MAE is **9.443 s**. SVR improves pooled MAE by **5.338 s** and **2.700 s**
respectively. The selected model's RMSE is larger than Ridge's, and its bias is
negative; a lower MAE is not uniform superiority.

| SVR test checkpoint | Laps | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| 10 s | 15 | 9.471 | 13.902 | -7.647 |
| 20 s | 15 | 7.345 | 11.072 | -3.836 |
| 30 s | 15 | 5.937 | 10.526 | -3.234 |
| 45 s | 15 | 6.316 | 10.529 | -2.034 |
| 60 s | 15 | 4.646 | 7.056 | -0.655 |

Later checkpoints are not guaranteed to improve every lap. Timing-invalid and
identity-ambiguous records were excluded before training; large test errors were
not removed. Skill, conditions and auto-shift settings differ across recordings.
One test participant (AB) appears in an earlier training session; this evaluates
future recordings, with a mixture of recurring and unseen participants, not strict
unseen-driver performance. Participant IDs themselves are not model inputs.

[ACGYM_ML_ERRORS_V06.csv](ACGYM_ML_ERRORS_V06.csv) retains every validation/test
prediction and verified target provenance. The machine-readable results report
MAE/RMSE/bias by checkpoint and session. Complete-lap summaries retain checkpoint
count, mean prediction, MAE/RMSE/bias across that lap's prefixes. These quantify
the trajectory of predictions, not independent repeated measurements. No confidence
interval, formal significance or broad generalization claim is made from this split.

Validation permutation importance uses three repetitions, seed 42, reporting MAE
increase in seconds for each feature/model. It is shown only with >=5 validation
laps; correlated prefix features limit interpretation. It neither selects features
nor uses test rows. The complete importance table is in the results JSON.

## GT7 development mode

**Experimental single-session case study — insufficient evidence for generalization.**

GT7 remains eight complete laps, one physical recording, 40 snapshots. Robust
training is disabled. An explicit opt-in permits chronological **4 train / 2
validation / 2 test laps**, with every prefix kept together. Its held-out laps are
from the same session; the UI and bundle retain the experimental disclaimer.
The small validation set suppresses importance estimation. Individual predictions
are in [GT7_ML_ERRORS_V06.csv](GT7_ML_ERRORS_V06.csv); all diagnostic aggregate
values are in the results JSON. They verify the pipeline, not predictive ability.

## Reproduction and artifact handling

Run `python -m scripts.audit_v06` explicitly with the cached datasets present.
It reads/hashes originals, audits laps, fits all models, exports measured reports
and verifies both locally saved model roundtrips. The measured sequential run
completed in about eight seconds in this environment. Versions are recorded in
[DATASET_MEASUREMENTS_V06.json](DATASET_MEASUREMENTS_V06.json).

`LocalArtifactStore.save` saves models **with preprocessing and feature order**.
It hashes and signs the bytes using a local store key. `load` accepts only a
bounded local basename and checks local provenance, SHA-256 and HMAC **before**
joblib deserialization. Unknown uploads, downloads and modified artifacts are
refused. The store and signing key are trusted application state and must not be
replaced with untrusted files. The UI exports CSV and saves bundles locally; it
does not offer an arbitrary model-file upload. Binary artifacts/keys remain under
ignored `artifacts/models/` and are not committed or downloaded by the application.
