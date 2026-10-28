"""Measured v090 reports and standalone figures from real recorded laps."""
from dataclasses import asdict
import json

import numpy as np
import pandas as pd

from motorsport.ingestion.barcelona import ROOT,MANIFEST,load_barcelona_recording
from motorsport.ingestion.gt7_importer import load_gt7_bundle
from motorsport.lap_analysis.data import spatial_source,from_session
from motorsport.lap_analysis.analysis import analyze_laps
from motorsport.lap_analysis.geometry import GeometryConfig
from motorsport.lap_analysis.alignment import AlignmentConfig
from motorsport.lap_analysis.kpis import SPECS,KPIConfig


def write(name,text):
    (ROOT/'docs'/name).write_text(text.strip()+'\n',encoding='utf-8',newline='\n')


def md(frame,columns):
    def cell(value):
        return f'{value:.6f}' if isinstance(value,(float,np.floating)) else str(value).replace('|','/')
    table=frame[columns]
    return '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+''.join('| '+' | '.join(cell(v) for v in row)+' |\n' for row in table.itertuples(index=False,name=None))


def save_figure(fig,path):
    fig.savefig(path,dpi=150)
    if path.suffix=='.svg':
        # Matplotlib's multiline SVG paths contain cosmetic trailing spaces.
        path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    entries=json.loads(MANIFEST.read_text(encoding='utf-8'))['files']
    entry=next(e for e in entries if e['path'].endswith('.ld') and e['recording_label']=='20240304_AB')
    sessions=[('barcelona','barcelona:'+entry['path'],load_barcelona_recording(entry['path']),3,6),
              ('gt7','gt7',load_gt7_bundle(ROOT/'data/raw/gt7_trial_mountain_962c'),14,13)]
    output=[]
    (ROOT/'docs/figures').mkdir(exist_ok=True)
    for label,key,session,a_id,b_id in sessions:
        spatial=spatial_source(session,key,ROOT)
        result=analyze_laps(from_session(session,a_id,spatial),from_session(session,b_id,spatial))
        assert result.report['status']=='valid'
        g=result.geometry
        fig,axes=plt.subplots(1,2,figsize=(13,6))
        for section in g.sections:
            idx=section['reference_indices']+[(section['reference_indices'][-1]+1)%len(g.s)]
            axes[0].plot(g.xy[idx,0],g.xy[idx,1],color='#ee7733' if section['kind']=='corner' else ('#aa66aa' if section['kind']=='boundary' else '#9aa2a9'),lw=2)
            if section['kind']=='corner':
                apex=section['curvature_weighted_apex_proxy'];maximum=section['maximum_curvature_point']
                axes[0].plot(*apex['xy'],'o',color='#009988',ms=5)
                axes[0].plot(*maximum['xy'],'x',color='#aa3377',ms=5)
                axes[0].annotate(section['section_id'],apex['xy'],fontsize=7)
        axes[0].set_aspect('equal');axes[0].set_xlabel('Source world X (m)');axes[0].set_ylabel('Source world Y (m)')
        axes[0].set_title('Orange corners / grey straights / purple unclassified seam\nGreen: weighted apex proxy; magenta: maximum curvature',fontsize=10)
        axes[1].plot(g.s,np.abs(g.curvature),lw=.8)
        axes[1].axhline(1/150,color='red',ls='--',label='150 m radius threshold')
        axes[1].set_xlabel('Reference distance (m)');axes[1].set_ylabel('|curvature| (1/m)');axes[1].legend()
        fig.suptitle(label.upper()+' real recorded lap '+str(a_id)+'; inferred sections, not official corner labels')
        fig.tight_layout(rect=[0,0,1,.93])
        for ext in ('png','svg'):
            path=ROOT/f'docs/figures/geometry_{label}_v090.{ext}';save_figure(fig,path);output.append(path.relative_to(ROOT).as_posix())
        plt.close(fig)
        section_id='C10' if label=='barcelona' else 'C09'
        section=next(s for s in g.sections if s['section_id']==section_id)
        start,end=section['start_s_m']-120,section['end_s_m']+80
        fig,axes=plt.subplots(3,1,figsize=(11,8),sharex=True)
        for aligned,color,tag in [(result.reference,'#4477aa','Reference'),(result.analyzed,'#ee7733','Analyzed')]:
            p=aligned.progress;mask=(p>=start)&(p<=end);f=aligned.lap.frame
            axes[0].plot(p[mask],f.speed_kmh.to_numpy()[mask],color=color,label=tag)
            axes[1].plot(p[mask],f.brake_pct.to_numpy()[mask],color=color,label=tag+' brake')
            axes[1].plot(p[mask],f.throttle_pct.to_numpy()[mask],color=color,ls='--',label=tag+' throttle')
        trace=result.trace.query('@start<=reference_s_m<=@end')
        axes[2].plot(trace.reference_s_m,trace.delta_s,color='#228833')
        for axis in axes:
            for position,style in [(section['start_s_m'],':'),(section['curvature_weighted_apex_proxy']['s_m'],'--'),(section['end_s_m'],':')]:
                axis.axvline(position,color='black',ls=style,alpha=.5)
        axes[0].set_ylabel('Speed (km/h)');axes[0].legend()
        axes[1].set_ylabel('Observed input (%)');axes[1].legend(ncol=2)
        axes[2].set_ylabel('Cumulative delta B-A (s)');axes[2].set_xlabel('Common reference position (m)')
        fig.suptitle(label.upper()+' '+section_id+' raw-observation review; dashed black = common weighted apex proxy\nInput differences are observations, not causes of the measured time difference')
        fig.tight_layout()
        for ext in ('png','svg'):
            path=ROOT/f'docs/figures/corner_{label}_v090.{ext}';save_figure(fig,path);output.append(path.relative_to(ROOT).as_posix())
        plt.close(fig)
    return output


def main():
    measured=json.loads((ROOT/'docs/MEASUREMENTS_V090.json').read_text(encoding='utf-8'))
    cases=pd.read_csv(ROOT/'docs/LAP_ANALYSIS_CASES_V090.csv')
    sensitivity=pd.read_csv(ROOT/'docs/CORNER_SENSITIVITY_V090.csv')
    kpis=pd.read_csv(ROOT/'docs/KPI_MEASUREMENTS_V090.csv')
    audit=pd.read_csv(ROOT/'docs/BARCELONA_SPATIAL_AUDIT_V090.csv')
    verification_path=ROOT/'docs/VERIFICATION_V090.json'
    verification=json.loads(verification_path.read_text(encoding='utf-8')) if verification_path.exists() else None
    validation=(f"Final suite: **{verification['tests']['passed']} passed**, zero failures/errors/skips, "
        f"{verification['tests']['seconds']:.2f} s. Actual Chrome: {verification['browser']['total_records']} recorded checks/budgets, "
        f"{verification['browser']['unexpected_errors']} unexpected errors, zero runtime exceptions. The six known console events from negative probes of retired routes remain recorded separately."
        if verification else 'Final suite/browser verification is pending; see VERIFICATION_V090.json when installed.')
    geometry_config=asdict(GeometryConfig());alignment_config=asdict(AlignmentConfig());kpi_config=asdict(KPIConfig())
    write('CORNER_DETECTION_V090.md',f'''# Corner detection and weighted apex proxy v0.9.0

The engine consumes **actual metric X/Y**. Barcelona coordinates are read from
existing LD channels with the author's Y/-X horizontal mapping. No velocity or
normalized-progress reconstruction is used. See [the pre-implementation gate](TELEMETRY_DATA_FEASIBILITY_V090.md).

## Spatial numerical contract

Cumulative source distance is the Euclidean sum of successive XY steps. Missing
coordinates, jumps >{geometry_config['maximum_source_step_m']:g} m or insufficient
extent are rejected. Consecutive duplicate points are removed only from geometry;
all source timestamps and telemetry packets remain in temporal analysis.
Interpolation occurs on spatial distance, independently of lap duration/speed.
Closed grids use N=ceil(L/1.5) cells with uniform L/N spacing. Open paths retain an
endpoint but never receive cyclic indexing. Closure requires endpoint distance
≤{geometry_config['closure_tolerance_m']:g} m. The small final geometric chord is
explicit; it is not a fabricated sensor observation.

Closure alone does not verify tangent continuity. When the closing chord exceeds
0.1 grid spacing and its cosine with either endpoint tangent is below 0.8, the
engine withholds curvature within `max(smoothing_m, 2*closure_m+2*spacing_m)`
of the seam. This is a purple, unclassified **B boundary section**, retaining all
time contribution. It prevents a small lateral endpoint mismatch from creating
a false tight corner; it does not label unknown curvature as a straight.

Default smoothing is a quadratic Savitzky-Golay filter over approximately
{geometry_config['smoothing_m']:g} spatial metres, implemented with NumPy. At
1.5 m spacing this uses seven points. Cyclic padding is used only for closed
geometry. Filtered geometry remains an estimated driven line, not track boundaries.

Signed three-point curvature is `2*cross/(a*b*c)`; radius is its reciprocal
magnitude, with straight/degenerate values safely zero/infinite. Open endpoints
have unavailable curvature. Default corner rule is strictly **|kappa|>1/150 m**.
Minimum corner length {geometry_config['min_corner_length_m']:g} m suppresses tiny
runs; straight holes ≤{geometry_config['merge_gap_m']:g} m merge only between equal
turn signs. Opposite signs separate chicanes. Runs crossing start/finish are locally
unwrapped. Straights remain in the complete partition; no known corner count is forced.

## Primary and secondary landmarks

`curvature_weighted_apex_proxy` uses trapezoidal distance integration of
`s*abs(kappa)` divided by that of `abs(kappa)`, on a locally unwrapped section.
It is interpolated back to the smoothed trajectory. `maximum_curvature_point`
is preserved separately as a diagnostic; it does not replace the weighted centre.
The reference's sections and apex positions are shared by A and B. Per-lap
minimum radius uses each lap's own geometry **inside those same reference windows**.

Known circles/straights, clockwise/anticlockwise paths, noise, stationary duplicates,
nonuniform source sampling and start/finish wrapping are tested. The weighted
centre stays stable when sampling the same path at different speeds. These tests
establish numerical behavior, not physical racing-apex accuracy.

## Actual fixed-reference sensitivity

{md(sensitivity,['source','radius_m','corners','sections'])}

At 150 m the selected Barcelona reference laps yield 17–19 geometric corners;
GT7 yields 10. Different reference driving lines and parameters can alter counts
and boundaries. They are **not official circuit-corner labels**. Raising the
threshold can merge adjacent same-direction runs, so counts need not increase
monotonically. Across analyzed laps using the same reference, boundaries are
identical by construction and verified in all 32 evaluated cases.

![Actual Barcelona reference geometry](figures/geometry_barcelona_v090.png)

![Actual GT7 reference geometry](figures/geometry_gt7_v090.png)
''')
    write('LAP_ALIGNMENT_V090.md',f'''# Common spatial lap alignment v0.9.0

Alignment projects observed X/Y onto segments of **one reference trajectory**.
It never assumes equal independent driven distance means equal circuit position,
and never aligns by completed-time percentage or `Car Pos Norm`.

## Quality and continuity rules

Both laps need compatible declared metric coordinate frames, vehicle/circuit
identities, spatial closure and verified complete timing. A chunked all-reference
audit identifies branches closer than {alignment_config['ambiguous_distance_m']:g} m
but more than {alignment_config['ambiguous_separation_m']:g} m apart in circuit
progress. Matched observations in these regions are unavailable, including
crossings/overpasses without a validated disambiguation signal.

Projection searches a sequential local neighborhood (approximately 100 m ahead,
limited behind), with a source-step-based forward-jump check. Distance from the
reference must be ≤{alignment_config['max_offset_m']:g} m. Drawdown >
{alignment_config['reverse_tolerance_m']:g} m rejects reverse/inconsistent motion.
Smaller projection jitter is regularized with a running maximum and disclosed.
No telemetry is removed to improve matches. A failed complete-lap match returns
explicit reasons and no invented section losses/KPIs. Validated timing laps remain
available in the application regardless of spatial eligibility.

## Time inverse and stationary observations

Repeated projected positions retain first arrival and last departure. At an
internal repeated position t(s) is right-continuous departure; between positions
it interpolates departure to next arrival. Thus stationary time remains a jump,
not removed packets or an assumed zero-duration stop. Reported repeated-progress
time also includes projection plateaus/boundary anchoring and is **not** an
independent vehicle-stop classifier.

Timing anchors `(s=0,t=0)` and `(s=L,t=verified_lap_time)` are allowed only with
source timing within {alignment_config['boundary_time_tolerance_s']:g} s and spatial
boundary coverage within {alignment_config['boundary_margin_m']:g} m. The old 1 ms
target-rounding contract can clip a tiny terminal timer overshoot. These anchors
are explicit timing evidence, not invented XY/sensor packets. No interior time
rescaling is performed. Boundary signal KPIs remain unavailable without observed
bracketing samples.

`delta(s)=t_B(s)-t_A(s)`. Section contribution is the difference between its end
and start delta. Wrapped sections sum their finish and start pieces. The complete
corner/straight/unclassified-boundary partition reconciles with the final measured delta at tolerance
**{alignment_config['numerical_tolerance_s']:g} s**. This is a numerical conservation
check tied to witnessed timing anchors, **not independent proof of sub-section
position/timing accuracy**.

## Actual recorded results

The fixed validation covers {measured['cases']} cases across four Barcelona
recording labels and all eight GT7 laps. {measured['valid_cases']} cases are valid,
{measured['unavailable_cases']} explicitly unavailable. Five cases are identity
checks: among {measured['distinct_pairs']} distinct within-recording pairs,
{measured['valid_distinct_pairs']} pass. One additional explicitly specified AB→NH
cross-recording pair passes. Maximum section reconciliation error among valid
cases is {measured['maximum_reconciliation_error_s']:.3g} s.

{md(cases,['source','reference_lap','analyzed_lap','self_comparison','status','measured_delta_s','p95_offset_m','maximum_offset_m','reasons'])}

The nine rejections involve excessive line offset and/or reverse progress under
the documented limits; they are retained, not silently replaced by time alignment.
These selected source checks do not establish successful pairwise alignment of
all 205 laps. Source geometry was audited for all 205 separately.
''')
    definitions=pd.DataFrame([dict(name=name,unit=spec[0],definition=spec[1],signals=', '.join(spec[2])) for name,spec in SPECS.items()])
    availability=kpis.groupby(['source','validity']).size().rename('measurements').reset_index()
    write('DETERMINISTIC_KPI_DEFINITIONS_V090.md',f'''# Deterministic KPI definitions v0.9.0

All measurements are retrospective facts or explicitly named operational proxies.
They are not causal explanations or coaching. The engine returns {len(SPECS)}
focused per-corner metrics with definition, original/compatible unit, A/B values,
difference, actual temporal measurement windows, source signals and quality/reason.
The reference-corner spatial context is stored separately because approach and
exit windows extend beyond the geometric corner.

## Event and measurement contract

Brake entry is ≥{kpi_config['brake_on_pct']:g}% sustained for
{kpi_config['brake_on_persistence_s']:g} s; release is ≤
{kpi_config['brake_off_pct']:g}% for {kpi_config['brake_off_persistence_s']:g} s.
Use actual elapsed timestamps, never packet counts. Missing samples or clock gaps
>0.2 s censor events. Detect full-lap events first; consider observed onsets within
{kpi_config['approach_m']:g} m before reference corner entry through its apex.
All events are retained; multiple/censored events do not receive an invented
primary phase. An event released >{kpi_config['maximum_release_before_entry_m']:g} m
before geometric entry has **uncertain corner association**: observed phase values
are kept, but a claimed corner-braking difference is withheld. This quality rule
was added after raw-overlay review found an earlier completed event in an approach
window; it avoids presenting unrelated phases as a valid braking comparison.

Throttle application is ≥{kpi_config['throttle_on_pct']:g}% for
{kpi_config['throttle_persistence_s']:g} s, searched from common apex or observed
minimum-speed region through an exit extension of {kpi_config['exit_m']:g} m.
Already sustained application at apex gives an explicitly operational zero delay;
no clear application gives null with explanation. Full-lap temporal summaries stay
available even when spatial geometry is unsupported.

Means use observed-time left-hold weights with ≥99% support; terminal samples have
no invented dwell. Landmark values interpolate only fresh, finite source brackets
≤0.2 s apart. Peaks/minima are observed values. Wrapped corners combine two pieces
of the selected lap for section accounting, but do not infer continuous event
chronology, rates or signal interpolation across their artificial seam.

Steering remains in the declared source convention (deg/rad); incompatible or
unverified units cannot produce a numerical difference. G-based acceleration
requires explicit g/G units. GT7 derived steering calibration and sway/surge units
remain unverified, so their physical KPIs are unavailable. Brake input is not
actual deceleration; reduced steering is not automatically better. The operational
trail-braking proxy is brake-input overlap with the geometric entry-to-apex
window, not a tyre-force/weight-transfer estimate.

Common circuit **position** differences use signed shortest circular displacement;
other compatible scalars use analyzed minus reference. Distances during braking
use that lap's actual driven XY distance, not normalized reference distance.

{md(definitions,['name','unit','definition','signals'])}

## Actual availability (including identity checks)

{md(availability,['source','validity','measurements'])}

Counts describe measurement availability, not accuracy on an independent labelled
coaching dataset. Missing/censored events, distant associations and unknown units
remain visible. Raw values and event sample indices are retained in JSON and
[the measured KPI table](KPI_MEASUREMENTS_V090.csv).

![Barcelona raw input and speed review](figures/corner_barcelona_v090.png)
''')
    tests=verification['tests']['passed'] if verification else 'pending'
    write('RELEASE_V090_REPORT.md',f'''# Release v0.9.0 — Deterministic Telemetry Lap Analysis

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
   {measured['maximum_reconciliation_error_s']:.3g} s against witnessed timing
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

Cold engine median **{measured['runtime']['median_s']:.3f} s**, P95
**{measured['runtime']['p95_s']:.3f} s**, maximum
**{measured['runtime']['maximum_s']:.3f} s** across 32 fixed cases, including
geometry, ambiguity checks, both projections and all KPIs; excludes browser
rendering. Source/analysis caches bind recordings, units/mappings, lap IDs,
parameters and implementation file stamps. Corner selection and hover reuse the
analysis. The shared cursor now accepts explicit `s`/metre metadata, while default
temporal displays retain their original `t`/seconds behavior. Original renderers,
normalization, timing eligibility, source values and F5 are preserved.

{validation}

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
| AC15 | {validation} |
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
''')
    write('NEXT_RELEASE_RECOMMENDATION.md', '''# Recommendation after deterministic Telemetry Lap Analysis v0.9.0

Keep this release deterministic. The next step is a **small manual technical
validation**, not another model or an automatic coaching layer.

| Decision item | Focused proposal |
| --- | --- |
| User problem | Determine whether displayed corner and pedal differences are useful and correctly associated with the selected driving phase |
| Simplest viable alternative | Use the existing raw telemetry comparison and the new fact table side by side, without new algorithms |
| Expected practical benefit | Identify misleading phase associations or unstable geometric proxies before users interpret them as driving advice |
| Evidence needed | Human annotations for a few corners on two fixed accepted Barcelona lap pairs, plus visible raw brake/throttle/speed traces |
| Small feasibility check | Review three corners, compare weighted/maximum-curvature landmarks, explain null/uncertain KPIs and repeat with one modest threshold change |
| Development gate | Add a narrowly justified refinement only when the manual review demonstrates a concrete measurement or usability problem |

Retain all valid timing laps and the explicit spatial rejection rules. Do not
relax quality thresholds merely to increase the successful alignment count. If
GT7 steering/acceleration measurements become important, obtain their source
calibration/unit contract first. If a later LLM demonstration is selected, limit
it initially to faithful summaries of these structured facts and validity flags;
evaluate it separately for unsupported causal statements. No ML, DL or LLM
development is justified merely by the future Capstone architecture.
''')
    output=figures()
    (ROOT/'docs/FIGURES_V090.json').write_text(json.dumps(dict(source='actual recorded Barcelona/GT7; no synthetic circuit presented as real',files=output),indent=2)+'\n',encoding='utf-8')
    print('Measured v090 reports, recommendation and real-source figures generated.',flush=True)


if __name__=='__main__':
    main()
