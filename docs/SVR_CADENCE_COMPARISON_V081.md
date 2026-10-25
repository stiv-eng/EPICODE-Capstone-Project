# SVR cadence comparison v0.8.1

All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, using the original five v072 folds. All **205 validated laps** remain preserved. **Zero new predictions on the 36 historical test laps** for selection. Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. Operational model: original signed **SVR v0.7.1**, unchanged.


## One focused experiment

Model A is the exact signed v080 direct SVR trained every five seconds. Model B is one RBF SVR configuration trained every second, evaluated at exactly A's one-second observations: C10, epsilon0.5, gamma scale, same 13 features, direct final-time target, same unique development laps, recording folds and source signals. There is no parameter/cadence grid, GRU change or full-development model promotion.

For each outer fold, A's inverse-count mean-one weights give each lap `N_A/L` total weight. B uses `(N_A/L)/n_B_lap` per row and **does not normalize weights back to mean one**. Thus total sample-weight mass and total per-lap `C*weight` penalty match A. Finer observations change the empirical distribution fitted by training-only imputation/scaling and the SVR objective quadrature; the comparison does not isolate sampling from that distribution change.

| fold | reference_snapshots | candidate_snapshots | unique_training_laps | reference_total_weight | candidate_total_weight | per_lap_weight | mean_candidate_weight | fit_seconds | process_peak_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3716 | 18938 | 153 | 3716.000000 | 3716.000000 | 24.287582 | 0.196219 | 14.089877 | 545660928 |
| 1 | 3401 | 17326 | 139 | 3401.000000 | 3401.000000 | 24.467626 | 0.196295 | 12.554999 | 550494208 |
| 2 | 3229 | 16448 | 136 | 3229.000000 | 3229.000000 | 23.742647 | 0.196316 | 10.701990 | 550682624 |
| 3 | 2965 | 15089 | 122 | 2965.000000 | 2965.000000 | 24.303279 | 0.196501 | 8.758823 | 551501824 |
| 4 | 3225 | 16415 | 126 | 3225.000000 | 3225.000000 | 25.595238 | 0.196467 | 10.668885 | 553467904 |


One-second training raw MAE **8.540758 s**, versus A **8.787312 s**: gain **0.246554 s (2.806%)**. Preregistered retention gate: gain ≥0.2 s and ≥2%, improvement in ≥4/5 folds. Gate passed: **True**.

## Same one-second observations

| cadence_s | model | laps | snapshots | mae_s | rmse_s | bias_s | median_absolute_error_s | p90_absolute_error_s | max_absolute_error_s | recording_macro_mae_s | physically_impossible_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.000000 | A-BOUNDED | 169 | 21054 | 8.708057 | 16.099941 | -3.254443 | 3.961307 | 21.473808 | 134.818332 | 7.733625 | 0 |
| 1.000000 | A-RAW | 169 | 21054 | 8.787312 | 16.243565 | -3.333698 | 3.982769 | 21.736421 | 134.818332 | 7.774311 | 242 |
| 1.000000 | A-STOP-AWARE | 169 | 21054 | 8.708926 | 16.100615 | -3.254381 | 3.961588 | 21.458937 | 134.818332 | 7.733399 | 0 |
| 1.000000 | B-1S-BOUNDED | 169 | 21054 | 8.465940 | 15.993371 | -3.608187 | 3.659199 | 21.427908 | 133.120262 | 7.604458 | 0 |
| 1.000000 | B-1S-RAW | 169 | 21054 | 8.540758 | 16.129608 | -3.683004 | 3.675965 | 21.654256 | 133.120262 | 7.642393 | 223 |


| model | value | laps | mae_s | bias_s |
| --- | --- | --- | --- | --- |
| A-BOUNDED | 0 | 16 | 11.780489 | -7.961393 |
| A-BOUNDED | 1 | 30 | 8.955115 | -3.108626 |
| A-BOUNDED | 2 | 33 | 10.073838 | -5.910382 |
| A-BOUNDED | 3 | 47 | 10.185525 | -4.507100 |
| A-BOUNDED | 4 | 43 | 4.729395 | 1.802709 |
| A-RAW | 0 | 16 | 11.804221 | -7.985126 |
| A-RAW | 1 | 30 | 9.054210 | -3.207721 |
| A-RAW | 2 | 33 | 10.094588 | -5.931131 |
| A-RAW | 3 | 47 | 10.380050 | -4.701624 |
| A-RAW | 4 | 43 | 4.734375 | 1.797729 |
| A-STOP-AWARE | 0 | 16 | 11.775811 | -7.966200 |
| A-STOP-AWARE | 1 | 30 | 8.949319 | -3.106290 |
| A-STOP-AWARE | 2 | 33 | 10.081300 | -5.909032 |
| A-STOP-AWARE | 3 | 47 | 10.186914 | -4.505862 |
| A-STOP-AWARE | 4 | 43 | 4.731351 | 1.800724 |
| B-1S-BOUNDED | 0 | 16 | 11.747072 | -8.010129 |
| B-1S-BOUNDED | 1 | 30 | 8.613170 | -3.540382 |
| B-1S-BOUNDED | 2 | 33 | 10.066592 | -6.038250 |
| B-1S-BOUNDED | 3 | 47 | 10.109371 | -4.626967 |
| B-1S-BOUNDED | 4 | 43 | 4.117619 | 0.960921 |
| B-1S-RAW | 0 | 16 | 11.770230 | -8.033287 |
| B-1S-RAW | 1 | 30 | 8.705701 | -3.632912 |
| B-1S-RAW | 2 | 33 | 10.085249 | -6.056907 |
| B-1S-RAW | 3 | 47 | 10.294904 | -4.812499 |
| B-1S-RAW | 4 | 43 | 4.121387 | 0.957153 |


The positive physical projection is also reported for B separately. Stop-aware UI continues to use Model A; no candidate is promoted automatically. Signed B fold artifacts are local under `artifacts/barcelona_v081/models`. Re-running the offline command verifies frozen evidence and does not refit or rescore. Historical test access remains zero.
