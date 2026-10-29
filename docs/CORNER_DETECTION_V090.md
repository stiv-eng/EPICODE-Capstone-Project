# Corner detection and weighted apex proxy v0.9.0

The engine consumes **actual metric X/Y**. Barcelona coordinates are read from
existing LD channels with the author's Y/-X horizontal mapping. No velocity or
normalized-progress reconstruction is used.

## Spatial numerical contract

Cumulative source distance is the Euclidean sum of successive XY steps. Missing
coordinates, jumps >15 m or insufficient
extent are rejected. Consecutive duplicate points are removed only from geometry;
all source timestamps and telemetry packets remain in temporal analysis.
Interpolation occurs on spatial distance, independently of lap duration/speed.
Closed grids use N=ceil(L/1.5) cells with uniform L/N spacing. Open paths retain an
endpoint but never receive cyclic indexing. Closure requires endpoint distance
≤8 m. The small final geometric chord is
explicit; it is not a fabricated sensor observation.

Closure alone does not verify tangent continuity. When the closing chord exceeds
0.1 grid spacing and its cosine with either endpoint tangent is below 0.8, the
engine withholds curvature within `max(smoothing_m, 2*closure_m+2*spacing_m)`
of the seam. This is a purple, unclassified **B boundary section**, retaining all
time contribution. It prevents a small lateral endpoint mismatch from creating
a false tight corner; it does not label unknown curvature as a straight.

Default smoothing is a quadratic Savitzky-Golay filter over approximately
9 spatial metres, implemented with NumPy. At
1.5 m spacing this uses seven points. Cyclic padding is used only for closed
geometry. Filtered geometry remains an estimated driven line, not track boundaries.

Signed three-point curvature is `2*cross/(a*b*c)`; radius is its reciprocal
magnitude, with straight/degenerate values safely zero/infinite. Open endpoints
have unavailable curvature. Default corner rule is strictly **|kappa|>1/150 m**.
Minimum corner length 12 m suppresses tiny
runs; straight holes ≤6 m merge only between equal
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

| source | radius_m | corners | sections |
| --- | --- | --- | --- |
| 20240229_HC | 100.000000 | 14 | 28 |
| 20240229_HC | 150.000000 | 18 | 36 |
| 20240229_HC | 200.000000 | 17 | 33 |
| 20240304_AB | 100.000000 | 16 | 34 |
| 20240304_AB | 150.000000 | 19 | 40 |
| 20240304_AB | 200.000000 | 17 | 36 |
| 20240325_WL | 100.000000 | 11 | 22 |
| 20240325_WL | 150.000000 | 17 | 34 |
| 20240325_WL | 200.000000 | 16 | 32 |
| 20240405_NH | 100.000000 | 15 | 32 |
| 20240405_NH | 150.000000 | 19 | 40 |
| 20240405_NH | 200.000000 | 18 | 38 |
| GT7 | 100.000000 | 8 | 16 |
| GT7 | 150.000000 | 10 | 20 |
| GT7 | 200.000000 | 16 | 32 |


At 150 m the selected Barcelona reference laps yield 17–19 geometric corners;
GT7 yields 10. Different reference driving lines and parameters can alter counts
and boundaries. They are **not official circuit-corner labels**. Raising the
threshold can merge adjacent same-direction runs, so counts need not increase
monotonically. Across analyzed laps using the same reference, boundaries are
identical by construction and verified in all 32 evaluated cases.

Inspect the reference geometry and selected-corner signals directly in
Telemetry Lap Analysis using the installed recordings.
