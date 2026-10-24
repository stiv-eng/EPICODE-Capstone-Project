# Dense and remaining-time SVR v0.8

All results below are exploratory **development OOF**, not a fresh independent test. All 169 development laps / 40 recording blocks are retained; 36 already-inspected historical test laps are excluded before representations. Source block independence is imperfect and folds overlap in fitting. Operational SVR v0.7.1 and its historical evidence remain unchanged.

## Frequency versus model fitting

SVR-SPARSE refits the original fixed C10/epsilon0.5/RBF-scale configuration on the original five checkpoints within each frozen development fold. Its learned parameters are then held fixed for all extra inference points. Original-checkpoint outputs match the frozen v072 F0 within 1e-9 s. Extra points do not change a prediction at a shared horizon. Outputs beyond 60 s extrapolate outside this sparse model's training horizons.

SVR-DENSE uses the same 13 causal features and settings with the dense schedule. SVR-REMAINING uses exactly the same dense inputs/weights but labels verified_final-observed_elapsed. At inference no target is accepted; return observed_elapsed+max(0,raw_remaining). Raw negatives/projection effects remain in CSVs. No tuning was added.

Dense loss weights are inverse snapshots per lap, normalized to mean 1; each lap contributes equal total. Imputation/scaling fit training only. More snapshots change the feature distribution **and total SVR loss mass relative to sparse fixed C10**. Thus this is a practical dense-training comparison, not a pure causal snapshot-count effect at fixed effective regularization. The direct-versus-remaining comparison does keep the exact rows, weights, preprocessing and configuration constant.

| model | all_lap_balanced_MAE | same_5_60s_MAE | original_sparse_MAE | last_scheduled_MAE | final_10s_retrospective_MAE |
| --- | --- | --- | --- | --- | --- |
| SVR-SPARSE | 14.410 | 13.695 | 13.361 | 21.452 | 21.321 |
| SVR-DENSE | 8.602 | 12.836 | 13.058 | 3.227 | 3.591 |
| SVR-REMAINING | 8.733 | 13.502 | 13.587 | 4.066 | 4.416 |
| REMAINING-REFERENCE | 19.503 | 22.641 | 22.641 | 19.893 | 18.004 |
| RIDGE-ORDERED | 12.656 | 14.860 | 14.974 | 6.573 | 7.517 |
| GRU | 11.241 | 14.425 | 14.244 | 5.738 | 6.163 |
| MEDIAN | 22.641 | 22.641 | 22.641 | 22.641 | 22.641 |

Dense minus sparse MAE at shared5–60 s: **-0.859 s**. Remaining minus dense-direct: **+0.665 s** there, **+0.839 s** at the last scheduled observation. Negative differences favor the new candidate.

## Fixed signed production SVR, separate original-validation-only trajectory

The immutable v071 SVR is also evaluated at extra points on its66 original validation laps, with no refit and no new historical-test predictions. This population is not the 169-lap OOF population and must not be mixed with it.

| schedule | laps | snapshots | lap_balanced_mae_s |
| --- | --- | --- | --- |
| sparse_compatibility | 66 | 330 | 9.868 |
| dense_5_60 s | 66 | 792 | 10.460 |
| dense_all | 66 | 1520 | 12.009 |

Different pooled schedule MAEs summarize different horizons; they do not demonstrate that increasing inference cadence improved fixed-checkpoint accuracy. The practical benefit is finer-grained feedback and coverage after 60 s, with explicit extrapolation limits for the sparse model.

## Constraint and calibration

| model | negative_raw_remaining | projected_fraction | projection_mae_change_s | final_before_observed_fraction | prediction_to_target_std | predicted_on_actual_slope |
| --- | --- | --- | --- | --- | --- | --- |
| SVR-SPARSE | 251 | 0.000 | 0.000 | 0.040 | 0.470 | 0.314 |
| SVR-DENSE | 43 | 0.000 | 0.000 | 0.007 | 0.751 | 0.638 |
| SVR-REMAINING | 6 | 0.001 | -0.001 | 0.000 | 0.797 | 0.668 |
| REMAINING-REFERENCE | 0 | 0.000 | 0.000 | 0.000 | 0.524 | 0.227 |
| RIDGE-ORDERED | 201 | 0.039 | -0.562 | 0.000 | 0.803 | 0.613 |
| GRU | 65 | 0.012 | -0.075 | 0.000 | 0.819 | 0.665 |
| MEDIAN | 499 | 0.000 | 0.000 | 0.090 | 0.130 | -0.048 |

See [comparison](ML_COMPARISON_V080.md), [checkpoints](CHECKPOINT_STRATEGY_V080.md), [dense SVR](SVR_DENSE_EXPERIMENT_V080.md), [sequences](SEQUENCE_MODEL_EXPERIMENTS_V080.md), [protocol](ML_PROTOCOL_V080.json), [results/hashes](ML_RESULTS_V080.json) and [architecture](ARCHITECTURE_V080.md).
