# Recommendation after v0.8

**Keep SVR v0.7.1 operational. Dense direct SVR is the most useful candidate for a controlled follow-up; development evidence does not authorize promotion.**

The 169-lap / 40-block experiment uses 4134 causal time checkpoints with equal lap weight. Dense direct SVR improves full-trajectory MAE 14.410 -> 8.602 s against sparse training, and shared 5-60 s 13.695 -> 12.836 s. Remaining-target SVR is slightly worse than dense direct overall and near completion. GRU 11.241 s beats ordered Ridge 12.656 s overall but remains behind dense SVR; it worsens middle-pace error versus Ridge. A deeper network or broad search is not justified by these results.

The next bounded release should:

1. Preserve current raw files, valid laps, signed references and frozen results. Preregister genuinely untouched same-domain evaluation observations when available. The 36 historical test laps remain already-observed evidence.
2. Match sparse/dense **total per-lap SVR penalty mass** in a focused control. Current inverse-prefix weights balance laps, but normalization to mean one changes total loss relative to the five-prefix fixed-C reference. Do not attribute the entire gain solely to density.
3. Test one separately specified physically consistent late bound or calibrated remaining model. Dense direct has 43 predictions below observed time, and its single 255 s observation has 55.134 s error despite 3.227 s mean last-point error. Preserve raw outputs and slow-tail reporting.
4. Obtain an authoritative ACTI `Car Pos Norm` mapping and interpolation/latency contract before percentage checkpoints. Numerical range/wrap evidence alone is insufficient. Keep causal elapsed cadence and survivor counts explicit; never infer percent from eventual duration.
5. Retain the compact trained GRU as the capstone sequence demonstration. If a future study must isolate neural/order effects, preregister matched fitting groups and one order-destruction control. Current Ridge/GRU share chunks but differ in fitting population, regularization and nonlinear architecture.

No new acquisition, push, merge, live capture or operational model replacement is part of this recommendation. See [eight conclusions](RELEASE_V080_REPORT.md), [comparison](ML_COMPARISON_V080.md), [protocol](ML_PROTOCOL_V080.json) and [sequence evidence](SEQUENCE_MODEL_EXPERIMENTS_V080.md).
