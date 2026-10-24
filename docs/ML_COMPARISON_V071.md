# ML release comparison v0.7.1

Barcelona now supplies a functioning inclusive experiment. The prior v0.7 had
88 eligible laps and failed its 12-group gate: **zero Barcelona models, zero test
evaluations and no measured Barcelona MAE**. Its stopped result must not be
presented as a numerical comparator.

| Experiment | Domain | Usable laps | Train / validation / test | Selected SVR test MAE | Median baseline MAE |
|---|---|---:|---|---:|---:|
| Historical v0.6 | Monza / Dallara F317 | 55 | 29 / 11 / 15 | 6.743 s | 9.443 s |
| v0.7 checkpoint | Barcelona / Dallara F317 | 88 | Not constructed | Not evaluated | Not evaluated |
| v0.7.1 A | Barcelona / Dallara F317 | 205 | 103 / 66 / 36 | 15.393 s | 17.901 s |

These are **different domains, target distributions, recording populations and
split/baseline assumptions**. Barcelona's larger MAE cannot be attributed to more
or fewer data by comparing it with Monza. No Monza/GT7 observation or fitted
preprocessing enters Barcelona. Historical v0.6 uses identified chronological
groups and past-only history; v0.7.1 uses retrospective recording blocks and a
fixed offline training median, with a separately restricted previous-lap reference.

The defensible same-domain size comparison is v0.7.1's nested TRAIN-only learning
curve with unchanged inclusive validation. SVR MAE improves 10.993 -> 10.600 ->
9.868 s for 49/66/103 training laps; RF 13.279 -> 12.563 -> 10.819; Ridge 14.741 ->
14.005 -> 12.441. Different nested block composition still limits causal attribution.
SVR slow-band error worsens, so more laps are useful without solving the tail.

No A/B filtering score exists: the preregistered timing-quality category contains
zero training laps. A remains inclusive; there is no unsupported claim that a
cleaner subset improves learning. Ridge/RF final test scores are deliberately
absent; only validation-selected SVR saw the frozen Barcelona final test.

The original Monza and GT7 source/results/model stores remain recoverable. Their
390 + 60 frozen prediction rows were verified within 1e-9 s (observed maximum
prediction deviation 2.842e-14 s). GT7 remains the historical eight-lap,
single-recording experimental case. See [historical evaluation](ML_EVALUATION_V06.md),
[new evaluation](ML_EVALUATION_V071.md) and [release evidence](RELEASE_V071_REPORT.md).
