# Release v0.9.2 — Lap selection and spatial diagnostics

Baseline: v0.9.1 commit `779cb59`. Branch: `feat/telemetry-lap-analysis-v092`.

## User interface

- **Reference Lap** and **Analysis Lap** now occupy two main-page columns, each
  containing **Session** and **Lap** with verified lap number/time. No lap-analysis
  session selector remains in the sidebar. Both selectors use the available source
  catalog, including installed Barcelona, Monza and GT7 recordings.
- Sessions are independent. Changing one does not silently replace the other;
  each lap list follows its own source identity. Valid per-source choices survive
  navigation, source switching and widget cleanup. Removed sources/laps fall back
  safely. Compatible cross-session comparisons remain supported; incompatible
  car/circuit selections stay visible with an explanation before analysis.
- Telemetry shading has a compact **Geometric Corner / Analysis Context** legend,
  distinct transparent approach/exit regions and a visible weighted-apex line.
  The existing boundaries and **200 m approach / 120 m exit** calculations remain
  unchanged. Title and legend spacing were checked visually.
- Remove the Maximum Curvature Point marker and toggle. Preserve maximum-curvature,
  minimum-radius and weighted-apex calculations, existing KPIs and JSON facts.

## Investigation of three actual rejected Barcelona pairs

Use the first existing LD recording for each label, reference lap 3:

| Recording / analysis lap | Maximum offset [m] | Maximum projected drawdown [m] | Result |
| --- | ---: | ---: | --- |
| 20240229_HC / 2 | 21.175 | 10.337 | Offset and projected progress rejected |
| 20240229_HC / 4 | 19.673 | 0 | Offset rejected |
| 20240304_AB / 5 | 18.085 | 5.966 | Offset and projected progress rejected |

At the maximum-offset and maximum-drawdown observations, independently projecting
against **all** reference segments agrees with the existing sequential result.
These cases have no branch ambiguity, implausible jumps or spatial-coverage
failure. They therefore provide no evidence of a lost search neighborhood or a
numerical bug that could safely make them acceptable. Timing-valid recordings
can still be unsuitable for this particular spatial comparison.

**No matching correction or threshold relaxation is justified by these cases.**
Keep the 12 m offset limit, 3 m projected-drawdown tolerance and all existing
ambiguity, continuity, clock and coverage guards. No time-based fallback is added.

Improve diagnostics instead: record issue type, complete failing-sample count,
maximum/limit, source indices/times and worst reference position **before progress
regularization**. Show translated explanations, a measurement table and colored
actual observations on the map, retaining first/last/worst samples in bounded
display traces. Explain that projected drawdown alone does not establish vehicle
reverse motion. JSON gains additive alignment issue details; rejected pairs still
produce no section comparison or corner KPIs. Accepted projections and delta
calculations are unchanged.

## Verification and limits

- **40 distinct targeted checks passed:** 29 alignment/KPI/real-lap checks and
  11 final UI, diagnostic and shared-analysis regressions. A final page check also
  passed after adjusting legend spacing. No full-suite rerun, exhaustive browser
  matrix, historical audit or performance benchmark was performed.
- A focused Chrome workflow, completed after correcting driver DOM/input handling,
  checked column layout, independent selectors, incompatibility explanations,
  accepted Barcelona/cross-recording comparisons, restored GT7 selection, context
  legend, spatial hover, highlighted rejection regions and an actual JSON download.
  Screenshots inspected; final browser console has zero errors/runtime exceptions.
- Python compilation and Git whitespace checks passed. Datasets, F5, geometry,
  KPI calculations and other analysis pages are preserved; no dependencies or AI
  functionality were introduced.

The three inspected rejections remain rejected. This small investigation does not
certify every lap pairing. Problem points are shown when projection was possible;
missing geometry/clock evidence can prevent locating a region and remains explained
textually. Map rendering is sampled; diagnostics/export retain complete counts.
