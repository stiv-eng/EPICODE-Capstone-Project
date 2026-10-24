# Recommendation after v0.7.1

**Keep the inclusive Barcelona A experiment as the measured reference and
prioritize causal feature engineering.** The recovered data supports actual
training; imperfect participant/date metadata is no longer a blocking condition.
SVR beats the offline median on validation (9.868 vs 20.414 s) and the frozen test
(15.393 vs 17.901 s), but slow-test MAE 31.213 s, bias -30.167 s and P90 overall
36.705 s show that the present features do not cover the full legitimate pace range.

1. Preserve all usable data and the current signed model/results. Compare a small
   preregistered set of causal recent-window speed/pedal, observed stopping/recovery
   and phase/event summaries against the same 13-feature baseline. Verify any
   source progress semantics; never normalize by eventual distance or final target.
   Keep training-only preprocessing and fixed inclusive development populations.
2. Report checkpoint, recording-macro and slow/fast errors alongside pooled MAE.
   Later prefixes help, but validation 60 s is worse than 45 s. The nested size
   curve improves overall SVR MAE by 1.125 s while worsening slow-tail MAE by
   2.573 s; do not optimize away difficult valid laps or claim size alone explains it.
3. A bounded classical alternative may follow a feature comparison, with few
   prespecified configurations. Current Ridge/RF/SVR results do not establish that
   algorithm replacement alone fixes lost temporal information or future incidents.
4. Additional same-domain recording diversity and better source timing/session
   documentation would strengthen evidence. This is useful follow-up, not a new
   eligibility gate. Retain anonymous/date-conflict laps when technically sound.
   Native capture/resampling latency remains unproven by 50/100 Hz export grids.
5. A limited Keras experiment is a later optional research step, after defining
   a causal sequence representation and meaningful classical references. With
   103 training laps and unknown cross-capture links, the current scores provide
   no measured reason to prioritize deep learning now. No DL was added in v0.7.1.

The Barcelona test has already been evaluated and inspected. Use validation or
development-only cross-validation for changes, then reserve a **new untouched
holdout** before claiming a new final result. Do not reuse the present final test
to pick features, filter laps, tune models or reverse the validation selection.
No arbitrary number of drivers or independent groups should prevent useful
development; document actual split strength and uncertainty instead.

Keep the v0.6.3 shared hover/cursor design. Follow-up browser coverage can include
Firefox/Safari, physical touch devices and longer laptop memory sessions; current
Chrome evidence covers actual pointer/keyboard, zoom/pan, responsive widths and
offline chart payloads. Unknown cross-recording links mean the new holdout does
not establish unseen-session/driver or prospective generalization.

See [dataset audit](BARCELONA_DATASET_AUDIT_V071.md),
[measured ML health](ML_EVALUATION_V071.md) and [comparison](ML_COMPARISON_V071.md).
This recommendation does not authorize further acquisition, publication or Git
push/merge, and imposes no new gate on the delivered functioning experiment.
