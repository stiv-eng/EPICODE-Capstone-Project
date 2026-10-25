# ML evaluation v0.8.1

All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, using the original five v072 folds. All **205 validated laps** remain preserved. **Zero new predictions on the 36 historical test laps** for selection. Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. Operational model: original signed **SVR v0.7.1**, unchanged.


## Accuracy and physical consistency

| cadence_s | model | laps | snapshots | mae_s | rmse_s | bias_s | median_absolute_error_s | p90_absolute_error_s | max_absolute_error_s | recording_macro_mae_s | physically_impossible_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.500000 | A-BOUNDED | 169 | 42204 | 8.722702 | 16.116871 | -3.255178 | 3.974240 | 21.608380 | 134.818332 | 7.743253 | 0 |
| 0.500000 | A-RAW | 169 | 42204 | 8.800956 | 16.259369 | -3.333433 | 4.005026 | 21.826451 | 134.818332 | 7.782888 | 477 |
| 0.500000 | A-STOP-AWARE | 169 | 42204 | 8.723024 | 16.116797 | -3.254996 | 3.974566 | 21.594838 | 134.818332 | 7.742546 | 0 |
| 1.000000 | A-BOUNDED | 169 | 21054 | 8.708057 | 16.099941 | -3.254443 | 3.961307 | 21.473808 | 134.818332 | 7.733625 | 0 |
| 1.000000 | A-RAW | 169 | 21054 | 8.787312 | 16.243565 | -3.333698 | 3.982769 | 21.736421 | 134.818332 | 7.774311 | 242 |
| 1.000000 | A-STOP-AWARE | 169 | 21054 | 8.708926 | 16.100615 | -3.254381 | 3.961588 | 21.458937 | 134.818332 | 7.733399 | 0 |
| 1.000000 | B-1S-BOUNDED | 169 | 21054 | 8.465940 | 15.993371 | -3.608187 | 3.659199 | 21.427908 | 133.120262 | 7.604458 | 0 |
| 1.000000 | B-1S-RAW | 169 | 21054 | 8.540758 | 16.129608 | -3.683004 | 3.675965 | 21.654256 | 133.120262 | 7.642393 | 223 |
| 5.000000 | A-BOUNDED | 169 | 4134 | 8.527480 | 15.974076 | -3.446863 | 3.760095 | 21.420577 | 133.079700 | 7.676364 | 0 |
| 5.000000 | A-RAW | 169 | 4134 | 8.602162 | 16.126392 | -3.521545 | 3.773215 | 21.597394 | 133.079700 | 7.708781 | 43 |
| 5.000000 | A-STOP-AWARE | 169 | 4134 | 8.525098 | 15.969372 | -3.445143 | 3.756378 | 21.413271 | 133.079700 | 7.673480 | 0 |


Every reported subset gives equal total weight per surviving unique lap. Recording-macro MAE averages lap MAEs within recording blocks, then blocks equally. Median/P90 are lap-weighted error quantiles, not packet-frequency statistics. RMSE, signed bias, maximum errors and physical impossibility counts are retained. Raw negative remaining values and all corrections are preserved in the reproducible CSVs.

## Pace bands at 1 s

Frozen original-training descriptive quartiles 109.734/140.04333333333335 s define fast/middle/slow only for retrospective evaluation; they never enter inference.

| model | value | laps | mae_s | bias_s | p90_absolute_error_s | max_absolute_error_s |
| --- | --- | --- | --- | --- | --- | --- |
| A-BOUNDED | fast | 62 | 3.687846 | 2.971178 | 9.468555 | 31.481918 |
| A-BOUNDED | middle | 69 | 5.749844 | -0.091957 | 12.888280 | 42.379568 |
| A-BOUNDED | slow | 38 | 22.270419 | -19.154444 | 53.517720 | 134.818332 |
| A-RAW | fast | 62 | 3.688817 | 2.970206 | 9.468555 | 31.481918 |
| A-RAW | middle | 69 | 5.754258 | -0.096371 | 12.888280 | 42.379568 |
| A-RAW | slow | 38 | 22.613296 | -19.497320 | 54.336583 | 134.818332 |
| A-STOP-AWARE | fast | 62 | 3.687846 | 2.971178 | 9.468555 | 31.481918 |
| A-STOP-AWARE | middle | 69 | 5.749319 | -0.092482 | 12.889562 | 42.379568 |
| A-STOP-AWARE | slow | 38 | 22.275238 | -19.153212 | 53.381992 | 134.818332 |
| B-1S-BOUNDED | fast | 62 | 3.112934 | 2.234510 | 7.491921 | 30.037749 |
| B-1S-BOUNDED | middle | 69 | 5.687483 | -0.284778 | 12.736717 | 41.159382 |
| B-1S-BOUNDED | slow | 38 | 22.244885 | -19.175618 | 53.243292 | 133.120262 |
| B-1S-RAW | fast | 62 | 3.113371 | 2.234073 | 7.491921 | 30.037749 |
| B-1S-RAW | middle | 69 | 5.691766 | -0.289061 | 12.736717 | 41.159382 |
| B-1S-RAW | slow | 38 | 22.569136 | -19.499869 | 54.029574 | 133.120262 |


## Late checkpoint survivors at 1 s

| model | value | laps | mae_s | bias_s | max_absolute_error_s |
| --- | --- | --- | --- | --- | --- |
| A-BOUNDED | 60.000000 | 169 | 9.435041 | -3.952392 | 113.459866 |
| A-BOUNDED | 90.000000 | 169 | 7.127229 | -4.244352 | 103.333356 |
| A-BOUNDED | 120.000000 | 76 | 9.712833 | -4.656515 | 88.256772 |
| A-BOUNDED | 150.000000 | 26 | 13.097701 | -7.325172 | 79.003814 |
| A-BOUNDED | 180.000000 | 10 | 12.746238 | -11.156917 | 55.548065 |
| A-BOUNDED | 210.000000 | 4 | 18.057132 | -18.057132 | 45.523529 |
| A-BOUNDED | 240.000000 | 1 | 19.605000 | -19.605000 | 19.605000 |
| A-BOUNDED | 255.000000 | 1 | 4.605000 | -4.605000 | 4.605000 |
| A-BOUNDED | 259.000000 | 1 | 0.600000 | -0.600000 | 0.600000 |
| A-RAW | 60.000000 | 169 | 9.435041 | -3.952392 | 113.459866 |
| A-RAW | 90.000000 | 169 | 7.127229 | -4.244352 | 103.333356 |
| A-RAW | 120.000000 | 76 | 9.712833 | -4.656515 | 88.256772 |
| A-RAW | 150.000000 | 26 | 13.097701 | -7.325172 | 79.003814 |
| A-RAW | 180.000000 | 10 | 13.532724 | -11.943403 | 55.548065 |
| A-RAW | 210.000000 | 4 | 26.721776 | -26.721776 | 45.523529 |
| A-RAW | 240.000000 | 1 | 60.753615 | -60.753615 | 60.753615 |
| A-RAW | 255.000000 | 1 | 55.134049 | -55.134049 | 55.134049 |
| A-RAW | 259.000000 | 1 | 62.682484 | -62.682484 | 62.682484 |
| A-STOP-AWARE | 60.000000 | 169 | 9.435041 | -3.952392 | 113.459866 |
| A-STOP-AWARE | 90.000000 | 169 | 7.122137 | -4.239261 | 103.333356 |
| A-STOP-AWARE | 120.000000 | 76 | 9.724011 | -4.645336 | 88.256772 |
| A-STOP-AWARE | 150.000000 | 26 | 13.097701 | -7.325172 | 79.003814 |
| A-STOP-AWARE | 180.000000 | 10 | 12.746238 | -11.156917 | 55.548065 |
| A-STOP-AWARE | 210.000000 | 4 | 18.057132 | -18.057132 | 45.523529 |
| A-STOP-AWARE | 240.000000 | 1 | 19.605000 | -19.605000 | 19.605000 |
| A-STOP-AWARE | 255.000000 | 1 | 4.605000 | -4.605000 | 4.605000 |
| A-STOP-AWARE | 259.000000 | 1 | 0.600000 | -0.600000 | 0.600000 |


Late populations shrink; one surviving slow lap is not a universal model accuracy estimate. `last_scheduled` depends on cadence and is retrospective. Final-10-second bands use known targets for scoring only, after inference.

| model | subset | laps | snapshots | mae_s | max_absolute_error_s |
| --- | --- | --- | --- | --- | --- |
| A-BOUNDED | late_over_60s | 169 | 10914 | 5.589449 | 115.616107 |
| A-BOUNDED | last_scheduled | 169 | 169 | 1.795681 | 12.601127 |
| A-BOUNDED | retrospective_final_10s | 169 | 1686 | 2.643181 | 24.320373 |
| A-RAW | late_over_60s | 169 | 10914 | 5.698736 | 115.616107 |
| A-RAW | last_scheduled | 169 | 169 | 3.682375 | 62.682484 |
| A-RAW | retrospective_final_10s | 169 | 1686 | 3.538204 | 64.327611 |
| A-STOP-AWARE | late_over_60s | 169 | 10914 | 5.592619 | 115.616107 |
| A-STOP-AWARE | last_scheduled | 169 | 169 | 1.795681 | 12.601127 |
| A-STOP-AWARE | retrospective_final_10s | 169 | 1686 | 2.643181 | 24.320373 |
| B-1S-BOUNDED | late_over_60s | 169 | 10914 | 5.465100 | 113.452111 |
| B-1S-BOUNDED | last_scheduled | 169 | 169 | 1.970558 | 12.552791 |
| B-1S-BOUNDED | retrospective_final_10s | 169 | 1686 | 2.578425 | 22.966520 |
| B-1S-RAW | late_over_60s | 169 | 10914 | 5.567804 | 113.452111 |
| B-1S-RAW | last_scheduled | 169 | 169 | 3.693517 | 62.013769 |
| B-1S-RAW | retrospective_final_10s | 169 | 1686 | 3.428083 | 63.604482 |


## Attribution

**A. Update frequency:** 4134 →21054 →42204 snapshots for 5/1/0.5 s with identical shared predictions. This improves observation frequency, not shared-cutoff model accuracy.

**B. Learned fitting:** One-second training raw MAE **8.540758 s**, versus A **8.787312 s**: gain **0.246554 s (2.806%)**. Preregistered retention gate: gain ≥0.2 s and ≥2%, improvement in ≥4/5 folds. Gate passed: **True**.

**C. Deterministic correction:** at one second, raw→bounded MAE 8.787312→8.708057; bounded→stop-aware 8.708057→8.708926. These are rule effects, not a learned model gain. Full stop/no-stop cohort evidence is in [the stop report](STOP_AWARE_PREDICTION_V081.md).

Frozen v080 numerical deviation is 5.12e-12 s. Original Monza/GT7 and Barcelona regressions and all raw/model/report hashes are checked in [preservation evidence](FROZEN_REGRESSION_V081.json).

Raw rows: [gzip-compressed predictions](DEVELOPMENT_PREDICTIONS_V081.csv.gz), [all/subset metrics](DEVELOPMENT_OVERALL_V081.csv), [checkpoint/pace/fold details](DEVELOPMENT_DETAILS_V081.csv), [stability](DEVELOPMENT_STABILITY_V081.csv), [cohorts](STOP_AWARE_EVALUATION_V081.csv), [runtime and hashes](ML_RESULTS_V081.json), [preregistered protocol](ML_PROTOCOL_V081.json). Pandas reads the gzip CSV directly; compression only changes storage, not numerical content.
