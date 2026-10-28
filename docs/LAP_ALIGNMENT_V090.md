# Common spatial lap alignment v0.9.0

Alignment projects observed X/Y onto segments of **one reference trajectory**.
It never assumes equal independent driven distance means equal circuit position,
and never aligns by completed-time percentage or `Car Pos Norm`.

## Quality and continuity rules

Both laps need compatible declared metric coordinate frames, vehicle/circuit
identities, spatial closure and verified complete timing. A chunked all-reference
audit identifies branches closer than 3 m
but more than 25 m apart in circuit
progress. Matched observations in these regions are unavailable, including
crossings/overpasses without a validated disambiguation signal.

Projection searches a sequential local neighborhood (approximately 100 m ahead,
limited behind), with a source-step-based forward-jump check. Distance from the
reference must be ≤12 m. Drawdown >
3 m rejects reverse/inconsistent motion.
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
source timing within 0.1 s and spatial
boundary coverage within 20 m. The old 1 ms
target-rounding contract can clip a tiny terminal timer overshoot. These anchors
are explicit timing evidence, not invented XY/sensor packets. No interior time
rescaling is performed. Boundary signal KPIs remain unavailable without observed
bracketing samples.

`delta(s)=t_B(s)-t_A(s)`. Section contribution is the difference between its end
and start delta. Wrapped sections sum their finish and start pieces. The complete
corner/straight/unclassified-boundary partition reconciles with the final measured delta at tolerance
**1e-06 s**. This is a numerical conservation
check tied to witnessed timing anchors, **not independent proof of sub-section
position/timing accuracy**.

## Actual recorded results

The fixed validation covers 32 cases across four Barcelona
recording labels and all eight GT7 laps. 23 cases are valid,
9 explicitly unavailable. Five cases are identity
checks: among 27 distinct within-recording pairs,
18 pass. One additional explicitly specified AB→NH
cross-recording pair passes. Maximum section reconciliation error among valid
cases is 7.11e-15 s.

| source | reference_lap | analyzed_lap | self_comparison | status | measured_delta_s | p95_offset_m | maximum_offset_m | reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20240229_HC | 3 | 3 | True | valid | 0.000000 | 0.011842 | 0.144625 | nan |
| 20240229_HC | 3 | 4 | False | unavailable | 6.627500 | 9.209276 | 19.672917 | Projection too far from reference |
| 20240229_HC | 3 | 1 | False | unavailable | 10.827500 | 5.069684 | 16.654407 | Projection too far from reference |
| 20240229_HC | 3 | 2 | False | unavailable | 16.205000 | 12.768573 | 21.175121 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240229_HC | 3 | 5 | False | unavailable | 52.767500 | 18.679868 | 21.779064 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240304_AB | 3 | 3 | True | valid | 0.000000 | 0.011538 | 0.464812 | nan |
| 20240304_AB | 3 | 6 | False | valid | 7.873333 | 2.939909 | 4.845667 | nan |
| 20240304_AB | 3 | 2 | False | valid | 16.110000 | 2.410418 | 3.942154 | nan |
| 20240304_AB | 3 | 4 | False | valid | 19.566667 | 6.164712 | 8.820281 | nan |
| 20240304_AB | 3 | 5 | False | unavailable | 42.996667 | 17.972576 | 18.084508 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240304_AB | 3 | 1 | False | valid | 48.296667 | 2.358337 | 4.466904 | nan |
| 20240325_WL | 14 | 14 | True | valid | 0.000000 | 0.011048 | 0.024095 | nan |
| 20240325_WL | 14 | 15 | False | valid | 0.030000 | 1.400893 | 1.933613 | nan |
| 20240325_WL | 14 | 13 | False | valid | 0.079000 | 1.273680 | 2.994586 | nan |
| 20240325_WL | 14 | 9 | False | valid | 0.316000 | 1.488395 | 2.291794 | nan |
| 20240325_WL | 14 | 12 | False | valid | 0.534000 | 1.599131 | 2.573533 | nan |
| 20240325_WL | 14 | 11 | False | valid | 0.576000 | 1.722869 | 2.516104 | nan |
| 20240325_WL | 14 | 10 | False | valid | 0.652000 | 1.535381 | 2.654454 | nan |
| 20240325_WL | 14 | 8 | False | valid | 1.955000 | 1.266116 | 2.223684 | nan |
| 20240405_NH | 3 | 3 | True | valid | 0.000000 | 0.012692 | 0.688640 | nan |
| 20240405_NH | 3 | 5 | False | unavailable | 15.020000 | 8.060034 | 21.489440 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240405_NH | 3 | 4 | False | unavailable | 30.823333 | 22.044101 | 25.002125 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240405_NH | 3 | 2 | False | unavailable | 36.266667 | 16.569729 | 24.156387 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| 20240405_NH | 3 | 1 | False | unavailable | 86.650000 | 20.241133 | 20.348620 | Projection too far from reference; Reverse motion / inconsistent lap direction exceeds tolerance |
| GT7 | 14 | 14 | True | valid | 0.000000 | 0.005427 | 0.266770 | nan |
| GT7 | 14 | 13 | False | valid | 0.094000 | 5.543045 | 11.274258 | nan |
| GT7 | 14 | 11 | False | valid | 1.835000 | 4.615459 | 6.994560 | nan |
| GT7 | 14 | 5 | False | valid | 2.122000 | 4.723431 | 10.820211 | nan |
| GT7 | 14 | 6 | False | valid | 2.538000 | 3.708230 | 5.412058 | nan |
| GT7 | 14 | 3 | False | valid | 2.945000 | 3.506935 | 5.456875 | nan |
| GT7 | 14 | 4 | False | valid | 3.847000 | 3.694108 | 6.552316 | nan |
| GT7 | 14 | 2 | False | valid | 4.938000 | 4.084292 | 7.838206 | nan |


The nine rejections involve excessive line offset and/or reverse progress under
the documented limits; they are retained, not silently replaced by time alignment.
These selected source checks do not establish successful pairwise alignment of
all 205 laps. Source geometry was audited for all 205 separately.
