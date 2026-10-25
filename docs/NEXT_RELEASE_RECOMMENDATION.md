# Recommendation after v0.8.1

All scores are exploratory development OOF on the original **169 laps / 40 recording blocks**, using the original five v072 folds. All **205 validated laps** remain preserved. **Zero new predictions on the 36 historical test laps** for selection. Reused development folds and uncertain physical recording links limit generalization; this is not a new independent final test. Operational model: original signed **SVR v0.7.1**, unchanged.


Keep the original signed v0.7.1 operational. Use the existing five-second-trained SVR-DENSE with 1 s experimental replay, explicit physical bound and opt-in stop-aware comparison. Half-second inference is locally supported=True; it adds feedback frequency, not shared-cutoff accuracy.

One-second training raw MAE **8.540758 s**, versus A **8.787312 s**: gain **0.246554 s (2.806%)**. Preregistered retention gate: gain ≥0.2 s and ≥2%, improvement in ≥4/5 folds. Gate passed: **True**.

Deterministic physical/stop rules change one-second MAE 8.787312→8.708057→8.708926 s. Keep raw output auditable. 20 threshold-stop laps are exploratory evidence; speed-only detection and frozen remaining time have limits. Slow corrected MAE remains 22.275238 s. Do not remove these laps or confuse physical plausibility with learned generalization.

The highest-value next step is a small preregistered untouched same-domain recording validation with independently annotated stationary episodes, slow laps, source timestamps and restart behavior. Audit conditional remaining-time calibration on those data. Author code confirms the progress-field rename, but exact ACTI interpolation/latency and reverse behavior remain unverified: keep position out of the feature contract until that is established, and keep scheduling time-based.

Retain GRU and ordered Ridge as research demonstrations without architecture changes. No new dataset, live capture, broad grid or automatic promotion is justified by this release. [Prior v080 recommendation](NEXT_RELEASE_RECOMMENDATION_V080.md) remains preserved.
