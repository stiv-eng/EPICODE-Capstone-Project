# Release v0.9.3 — Partial alignment and unallocated delta

Baseline: v0.9.2 `ac8ade6`. Branch: `feat/telemetry-lap-analysis-v093`.

## Delivered behavior

Keep the original numerical path for fully valid comparisons. Local failures now
permit independent, trustworthy spatial/time runs before and after excluded areas.
Distance, ambiguity, reverse-progress, source-step and timing safeguards remain;
invalid positions never acquire invented common progress or interpolated clocks.

Reacquisition requires a unique forward geometric match, at least three consecutive
observations advancing two spatial grid cells, and consistency with observed travel
since the last trusted point. It cannot revisit prior allocated progress. Internal
run boundaries reserve one grid cell for uncertain transitions. Missing coordinates,
acquisition jumps and clock gaps break runs; incompatible frames/units and invalid
clocks can still prevent spatial analysis entirely.

Intersect the reliable domains of **both** laps, then partition the existing
reference sections on those common domains. Fully supported sections retain their
IDs; reliable fragments use suffixes such as `S01.1`. Each contribution uses only
trustworthy common spatial/time endpoints. Excluded intervals and transitions
carry **no individual delta**. Their complement is explicit and non-overlapping.

`unallocated_delta = independently measured lap delta − sum(measured contributions)`

Display **one combined “Delta non attribuito — Allineamento spaziale non disponibile”**
bar, with a distinct hatch/color, even when its value is zero. Preserve either sign.
It is an accounting residual, not an independently measured loss or a causal
explanation. No off-track claim or time-normalized alignment fallback is introduced.

Fully supported corners remain inspectable. Their existing KPI definitions are
unchanged; each required temporal window must also be supported. An intersecting
hole makes that measurement unavailable. Incomplete corners retain unavailable KPI
records, while trustworthy fragments can still contribute measured section time.
The cumulative delta and observed signal traces break across unsupported regions.

On the map, blue observations show recovered alignment and contrasting points mark
excluded/transition areas, with reasons in hover and diagnostics. **🏁** marks the
last actual reference position within the existing verified timing-boundary
tolerance (100 ms); no exact official finish position or line is reconstructed.
The geometric seam/unclassified boundary remains separate. The marker is omitted
when the position/timing evidence is missing.

## Focused actual-recording results

Reference lap 3 in each of the same two Barcelona recordings investigated in v0.9.2:

| Analysis lap | Status | Timed sections/fragments | Whole corners inspectable | Measured delta [s] | Unallocated [s] | Total [s] |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| HC 20240229 / 2 | partial | 37 | 17 | +7.142235 | +9.062765 | +16.205000 |
| HC 20240229 / 4 | partial | 37 | 17 | +2.758124 | +3.869376 | +6.627500 |
| AB 20240304 / 5 | partial | 41 | 18 | +20.074516 | +22.922150 | +42.996667 |
| AB 20240304 / 6 | valid | 40 | 19 | +7.873333 | 0 | +7.873333 |

Display values are rounded; accounting uses full precision. All three former
whole-comparison rejections now recover useful partial analysis without accepting
their unreliable regions. Partial reconciliation error is zero in these checks.
All **40 section records/times/deltas** for accepted AB 3→6 exactly match the
pre-existing accepted facts; GT7's +0.094 s comparison also remains valid.

## Verification and remaining limits

**44 distinct targeted regression cases have passing coverage**, including local
and multiple holes, missing/jumped coordinates, restart, negative residuals,
non-overlapping complete spatial partitions, clock gaps, ambiguous crossings,
KPI-window exclusion, total-only fallback, normal comparisons, selection state and
finish-marker provenance. Existing whole-rejection assertions were updated to the
new partial behavior and rechecked. Final targeted page/map checks passed; Python
compilation and Git whitespace checks passed. The complete suite was not rerun.

A focused Chrome workflow checked valid GT7 and partial HC 3→2, one reconciled
residual, actual JSON download, a valid corner after the failure and the visible
recorded checkered marker. Screenshots inspected; final browser console has no
errors/runtime exceptions. Driver loading/output-encoding corrections required no
application workaround. No historical dataset audit, benchmark or browser matrix.

Some regions remain unavailable by design. If a lap's own complete geometry cannot
be built, its curvature/radius KPIs remain unavailable rather than bridging missing
positions. Global clock/frame/reference-geometry failures may yield only total delta and residual.
Datasets and F5 settings are unchanged; no dependencies or ML/DL/LLM components were added.
The existing JSON schema/identifiers are retained, with additive partial-status,
coverage, withheld-interval, residual and recorded-marker facts.
