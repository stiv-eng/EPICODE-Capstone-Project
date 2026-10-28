# Release v0.9.1 — UI and corner analysis refinement

Baseline: stable v0.9.0 commit `6dc4a27`. Development branch:
`feat/telemetry-lap-analysis-v091`. All five requested improvements are delivered.

## Changes

1. **Session/lap selection.** The sidebar now says **Sessione di riferimento**.
   Previously its “analyzed” label obscured its role, while the independent B
   selector allowed a different circuit/car. Both lap widgets also reused fixed
   keys across sources and relied on deleting widget state during reruns.
   Widgets now bind to source identity, revision/mapping and verified lap table;
   durable per-source choices survive widget cleanup and navigation. Changed or
   removed lap IDs are revalidated. Known incompatible B sessions are filtered
   using existing metadata/manifests, without loading every recording; selected
   sessions receive a final identity check before lap analysis. Compatible
   cross-recording comparisons remain available. Existing analysis caches already
   included source identities; no cache bypass or forced repeated loading was needed.
2. **Legacy F1 removed.** Remove the three F1 pages, navigation toggle, exclusive
   FastF1 loader/analytics, their three exclusive tests and optional dependency
   manifest. Keep shared chart components and all simulator analysis workflows.
3. **Readable KPIs.** All 35 existing metrics have engineering labels with units
   in tables, summaries and expanded definitions. Unverified steering units are
   labelled explicitly. Internal identifiers and the JSON schema/export remain
   intact; no new KPI is introduced.
4. **Corner context and event ownership.** Raw aligned plots show approximately
   **200 m before entry and 120 m after exit**, including adjacent sections,
   shaded geometric boundaries and the weighted apex marker. Braking uses the
   same wider approach limit, assigning each detected phase once to the first
   eligible following apex. Phases spanning multiple apex landmarks remain
   uncertain. The existing early-release uncertainty guard is retained. Throttle
   exit searches stop at the next corner entry, so its later application cannot
   be attributed to the preceding exit. Pedal thresholds/persistence are unchanged.
5. **Legible subplot axes.** Increase row height and separation, reserve a left
   margin, split labels/units over two lines and set title standoff. Preserve the
   stacked signals, units and synchronized metre-based cursor.

## Verification

- Four essential new regression tests cover same-number laps across session
  changes, restoring selections, source replacement, label coverage, early braking,
  overlapping approaches, uncertain spanning phases and bounded throttle attribution.
- Focused checks passed. Run the complete suite **once**: **209 passed** in 146 s;
  one old test still expected the removed F1 checkbox. Update that expectation
  to assert its absence and rerun **only that test: 1 passed**. All 210 current
  tests therefore have passing coverage; the complete suite was not repeated.
- One focused Chrome scenario, with a driver serialization correction, checked
  GT7 → Barcelona → GT7, matching lap lists, incompatible-session filtering and
  selection restoration. Actual Barcelona plots rendered all landmarks, six
  nonoverlapping Y-axis titles and functioning spatial hover. Screenshot inspected;
  browser console contained no errors or runtime exceptions.
- Python compilation and Git whitespace checks passed. No separate historical audits,
  performance benchmarks or exhaustive browser matrices were run.

Geometry, the **150 m threshold**, section-time decomposition, datasets and F5 are
unchanged. No new dependencies or ML/DL/LLM functionality were added.

## Remaining limits

Event ownership is an explicit geometric association, not causal driving advice.
Phases outside the bounded approach, censored/multiple events and early releases
can remain unavailable or uncertain. Spatial seam context uses fragments of the
same recorded lap and does not establish event continuity into another lap.
Unverified source geometry/units retain the existing availability restrictions.
