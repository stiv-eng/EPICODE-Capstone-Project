# High-frequency inference v0.8.1

All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, using the original five v072 folds. All **205 validated laps** remain preserved. **Zero new predictions on the 36 historical test laps** for selection. Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. Operational model: original signed **SVR v0.7.1**, unchanged.


## Schedule and causality

Intervals are **5, 1 and 0.5 elapsed source seconds**; experimental default is 1 s. The scheduler preserves nominal checkpoint and last actual source timestamp independently. Source samples are processed in arrival order; no sorting across clock resets, interpolation, target, distance, final-duration fraction or track percentage enters inference. Freshness ≤100 ms; clock reset, nonfinite timestamp or gap >200 ms quarantines the remaining replay. The 169 development laps had zero such interruptions. Largest actual sample age at 1 s: **30.000 ms**.

Existing signed five-second-trained SVR-DENSE is loaded once per fold. Prefix sufficient statistics compute the same 13 features; recent three-second statistics preserve the original arithmetic. Per-session raw and corrected rows are memoized. Hover stays entirely in the existing browser component. Fragment timer ticks update the recorded replay only; pausing never adds wall time to lap elapsed.

## Measured runtime

Each cadence was measured in its own fresh Python process on the existing Windows development machine. Process peak includes corpus ingestion, all 205 source laps, five models, indexes, caches and accumulated result rows; it is not model-only memory. Measurements are local wall-clock observations under the development workload, not hardware-independent guarantees. They exclude Streamlit rendering. Per-checkpoint timings include causal sample-state processing, feature building and a single model query; first initialization is reported separately.

| cadence_s | snapshots | inference_total_s | checkpoint_median_ms | checkpoint_p95_ms | checkpoint_max_ms | index_initialization_median_ms | peak_process_working_set_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5.000000 | 4134 | 9.714981 | 1.899950 | 2.365020 | 32.949000 | 8.116200 | 281477120 |
| 1.000000 | 21054 | 38.951768 | 1.611800 | 2.547235 | 43.120000 | 8.739700 | 305156096 |
| 0.500000 | 42204 | 70.610173 | 1.557800 | 2.006985 | 40.241400 | 8.623000 | 336551936 |


The half-second gate, fixed before evaluation, is P95 <100 ms and process peak <1500000000 bytes. Supported: **True**. The UI exposes it when this measurement is installed. Actual browser timer intervals and render checks are separately recorded in [browser evidence](UI_BROWSER_V081.json); scheduler cadence and wall-clock render cadence must not be conflated.

Measured Chrome median wall intervals: v081 playback and pause 5 secondi: fewer than two timed transitions in observation window, v081 playback and pause 1 secondo: 1.109 s, v081 playback and pause 0.5 secondi: 0.485 s. Source checkpoint spacing remains exact; polling/render jitter affects wall intervals.

## Shared observations

Maximum new-cadence deviation at shared cutoffs: `{'1.0': {'raw_prediction_s': 0.0, 'bounded_prediction_s': 0.0, 'stop_aware_prediction_s': 0.0}, '0.5': {'raw_prediction_s': 0.0, 'bounded_prediction_s': 0.0, 'stop_aware_prediction_s': 0.0}}` seconds. Maximum deviation from frozen v080 raw five-second predictions: **5.12e-12 s** (tolerance 1e-9). Cumulative arithmetic can differ at floating-point roundoff only. Cadence does not change learned parameters or shared outputs.

| cadence_s | model | mae_s | laps | snapshots |
| --- | --- | --- | --- | --- |
| 0.500000 | A-BOUNDED | 8.527480 | 169 | 4134 |
| 0.500000 | A-RAW | 8.602162 | 169 | 4134 |
| 0.500000 | A-STOP-AWARE | 8.525098 | 169 | 4134 |
| 1.000000 | A-BOUNDED | 8.527480 | 169 | 4134 |
| 1.000000 | A-RAW | 8.602162 | 169 | 4134 |
| 1.000000 | A-STOP-AWARE | 8.525098 | 169 | 4134 |
| 1.000000 | B-1S-BOUNDED | 8.406661 | 169 | 4134 |
| 1.000000 | B-1S-RAW | 8.476960 | 169 | 4134 |
| 5.000000 | A-BOUNDED | 8.527480 | 169 | 4134 |
| 5.000000 | A-RAW | 8.602162 | 169 | 4134 |
| 5.000000 | A-STOP-AWARE | 8.525098 | 169 | 4134 |


Pooled 0.5/1/5 s scores cover different intermediate/early observations and different last scheduled points. They cannot demonstrate a cadence-only accuracy improvement. The table above uses identical five-second observations.

## Stability

| cadence_s | model | mean_lap_jump_s | maximum_jump_s | mean_lap_p95_rate |
| --- | --- | --- | --- | --- |
| 0.500000 | A-BOUNDED | 1.159361 | 27.849791 | 7.880963 |
| 0.500000 | A-RAW | 1.169696 | 27.849791 | 7.935421 |
| 0.500000 | A-STOP-AWARE | 1.157692 | 27.849791 | 7.871820 |
| 1.000000 | A-BOUNDED | 1.768139 | 23.965506 | 5.573201 |
| 1.000000 | A-RAW | 1.784179 | 29.071862 | 5.619429 |
| 1.000000 | A-STOP-AWARE | 1.763918 | 23.965506 | 5.564594 |
| 1.000000 | B-1S-BOUNDED | 1.581604 | 24.776944 | 4.804553 |
| 1.000000 | B-1S-RAW | 1.596209 | 27.763780 | 4.843840 |
| 5.000000 | A-BOUNDED | 3.507746 | 34.527355 | 1.959836 |
| 5.000000 | A-RAW | 3.529205 | 34.527355 | 1.966650 |
| 5.000000 | A-STOP-AWARE | 3.506905 | 34.527355 | 1.956318 |


Mean jumps are first averaged within each lap, then across laps. Smaller intervals naturally reduce per-step changes; per-second rates expose that distinction. No global monotonicity rule or accuracy-motivated smoothing was added. Source dropouts do not count as verified stopped time.
