# Release v0.9.0 — Deterministic Telemetry Lap Analysis

Baseline **v0.8.2 commit `1e91142`**, initially clean and reverified: **167 tests
passed, 120.85 s**. The scope reset is complete: archived progressive prediction
modules remain absent. Work is isolated on `feat/telemetry-lap-analysis-v090`.
The baseline branch/commit and `archive/progressive-laptime-ml-v081` remain intact.
No source dataset, ignored model/key or F5 file is modified; no push, merge, reset,
branch deletion, model training or AI integration is performed.

## Delivered behavior

**Telemetry Lap Analysis** complements the existing pages. Select a reference and
analyzed lap/session, inspect verified lap times, spatial quality, measured final
delta, inferred corners/straights, weighted apex proxies, optional maximum-curvature
markers, cumulative delta, section contributions, focused KPIs and raw selected-
corner signals. Threshold 150 m and geometric quality parameters are visible and
configurable. All sections are defined on one reference; changing B does not
redefine them. Invalid alignment shows reasons and whole-lap observations, without
fabricated corner losses or a normalized-time fallback.

The fact export schema is **`deterministic-lap-analysis/1.0`**: source/car/circuit,
lap identities/times, coordinate provenance, alignment quality, parameters,
reference geometry, all section deltas, event observations, KPI units/windows/
differences/validity, signal availability and an empty interpretations list. Core
code is independent of Streamlit. No ML/DL/LLM/API/prompt/coaching implementation
is introduced. JSON export works without a server rerun.

## Ten engineering answers

1. **Does real data have usable X/Y?** Yes: all 70 Barcelona LD files already
   contain metric Car Coord X/Y/Z. Earlier reports inspected only imported columns
   and wrongly concluded there were no usable coordinates. This release corrects
   that conclusion by auditing the actual files, before geometry implementation.
   All 205 laps have finite XY. GT7 also has metre world X/Z. The original
   integrated-position attachment has no validated complete laps and is unsupported.
2. **Which channels are trustworthy?** Barcelona speed km/h, brake/throttle %,
   steering deg, lap timer s, RPM, gear and g acceleration have source declarations;
   export cadence is 50/100 Hz, not independently certified native acquisition.
   World XY agrees with integrated speed within about 0.06%, with plausible shared
   circuit/finish geometry. `Car Pos Norm` is not used. GT7 pedal/time/position data
   support analysis; derived steering calibration and sway/surge physical units do
   not support physical steering/acceleration KPIs.
3. **Does 150 m behave sensibly?** It yields interpretable driven-line sections:
   17–19 corners on selected Barcelona references and 10 on GT7. The threshold,
   minimum length, signed-direction and short-gap rules remain inspectable.
   Sensitivity is reported rather than tuning counts to official corners.
4. **Is weighted centre suitable?** Yes as a repeatable operational **proxy**:
   distance-weighted integration is tested on known shapes, wrap and changing
   temporal sampling. It is less tied to one extreme curvature sample than argmax,
   which remains diagnostic. Physical/racing-apex accuracy has not been established.
5. **Are boundaries stable across laps?** Exactly identical for every B using a
   fixed reference, verified in the 32 real cases. Across different reference
   driving lines/parameters, boundaries and counts can change; there is no certified
   canonical circuit segmentation yet.
6. **Can laps be aligned?** Conditionally: 18/27 distinct within-source pairs pass,
   plus an AB→NH cross-recording pair. Nine cases are unavailable for excessive
   offset/reverse progress. Five identity cases are separated from those counts.
   This does not claim all pairings of the 205 laps are reliable.
7. **Does delta reconcile?** Yes on every accepted case, maximum error
   7.11e-15 s against witnessed timing
   anchors; corners, straights and unclassified boundary include the whole lap. This is a numerical
   conservation check, not independent sub-section timing accuracy.
8. **Which KPIs work?** Common-landmark/entry/exit/minimum speed, traversal times,
   observed braking/throttle events, supported steering and g statistics, plus
   each driven line's geometry within common reference windows. Null/uncertain
   values and exact measurement definitions are retained, not converted to zero.
9. **What remains ambiguous?** Missing/censored/multiple pedal events, distant
   approach-event association, raw-unit GT7 steering/acceleration, poor spatial
   matches, source boundary gaps, seam chronology and physical apex meaning.
   No input is asserted to cause a measured time loss.
10. **Enough for a future LLM demonstration?** The structured facts are a credible
    deterministic input contract, including explicit limitations. A later system
    could summarize verified observations; this release proves neither coaching
    effectiveness nor causal driving diagnosis. No AI component is needed to use it.

## Measured runtime and scope

Cold engine median **1.276 s**, P95
**1.544 s**, maximum
**1.922 s** across 32 fixed cases, including
geometry, ambiguity checks, both projections and all KPIs; excludes browser
rendering. Source/analysis caches bind recordings, units/mappings, lap IDs,
parameters and implementation file stamps. Corner selection and hover reuse the
analysis. The shared cursor now accepts explicit `s`/metre metadata, while default
temporal displays retain their original `t`/seconds behavior. Original renderers,
normalization, timing eligibility, source values and F5 are preserved.

Final suite: **209 passed**, zero failures/errors/skips, 149.53 s. Actual Chrome: 151 recorded checks/budgets, 0 unexpected errors, zero runtime exceptions. The six known console events from negative probes of retired routes remain recorded separately.

Synthetic tests establish numerical properties only. Actual source validation
uses every valid lap in four prespecified recording files and all eight GT7 laps;
rejections are included. Real Barcelona/GT7 maps and raw input/speed overlays were
generated and visually inspected. The earlier-completed-brake-event association
failure found during review is explicitly quality-flagged, not turned into a
claim that a different braking position caused a corner loss.

## Acceptance evidence

| Criteria | Evidence and qualification |
| --- | --- |
| AC1 | Verified v0.8.2 commit/branch and archived prediction reference retained; 244 protected local files, 73 original source signals/overview summaries and all 205 lap trajectories checked unchanged |
| AC2 | Pre-implementation feasibility gate plus full 70-file/205-lap coordinate audit and GT7 source contracts |
| AC3–AC6 | Known numerical geometry tests, configurable 150 m rule, weighted apex as primary and optional maximum-curvature diagnostic; real figures linked below |
| AC7–AC8 | Explicit rejection checks, 18/27 distinct accepted within-source pairs plus cross-recording case, complete section conservation to measured timing anchors |
| AC9–AC10 | 35 documented KPI definitions, units/windows/events and per-value quality; missing physical units and uncertain phases withheld |
| AC11–AC12 | New page plus actual Chrome regression of existing imports, analysis pages, G-G and synchronized cursors; F5 files unchanged |
| AC13–AC14 | Versioned JSON fact export with empty interpretations; independent engine, no ML/DL/LLM code or new dependency |
| AC15 | Final suite: **209 passed**, zero failures/errors/skips, 149.53 s. Actual Chrome: 151 recorded checks/budgets, 0 unexpected errors, zero runtime exceptions. The six known console events from negative probes of retired routes remain recorded separately. |
| AC16 | Unsupported geometry/alignment, unclassified seam, unknown units and ambiguous events remain explicit, without synthetic replacement |

## Limitations and next experiment

Geometry is a filtered simulator driven line, not surveyed boundaries. Projection
can fail on reverse/off-reference motion, 2D crossings, offsets and incomplete
coverage. Fixed quality limits deliberately refuse unsupported complete-lap
decomposition. Sampling/anchors/filtering limit physical precision; sub-ms numeric
reconciliation is not sub-ms measurement accuracy. Generic imports need declared
metric world coordinates/frame and independently verified complete timing.

The smallest justified next experiment is manual review of a few fixed Barcelona
corners on two accepted lap pairs: compare raw event traces and weighted proxies
with explicit human annotations, check uncertain associations and parameter
sensitivity. Establish usefulness before considering more KPIs or any ML/LLM.

[Pre-implementation feasibility](TELEMETRY_DATA_FEASIBILITY_V090.md) ·
[Corner method](CORNER_DETECTION_V090.md) · [Alignment](LAP_ALIGNMENT_V090.md) ·
[KPI definitions](DETERMINISTIC_KPI_DEFINITIONS_V090.md) ·
[Case table](LAP_ANALYSIS_CASES_V090.csv) · [Runtime/evidence](MEASUREMENTS_V090.json) ·
[Verification](VERIFICATION_V090.json) · [Recommendation](NEXT_RELEASE_RECOMMENDATION.md).
