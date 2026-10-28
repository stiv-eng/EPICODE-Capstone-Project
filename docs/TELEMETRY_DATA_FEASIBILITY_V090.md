# Real-data feasibility gate v0.9.0

Audit performed **before geometry/comparison implementation**, 2026-10-28.
Baseline `1e91142`, clean tree, 167 tests passed in 120.85 s. Existing v082
analysis and archived prediction removal are verified, not merely assumed.

## Finding that corrects earlier reports

The actual 70 Barcelona LD files contain **Car Coord X, Car Coord Y and Car
Coord Z, all declared metres**, alongside `Car Pos Norm`. Earlier analysis pages
only imported a restricted channel set and incorrectly described the exports as
having no usable world coordinates. That prior conclusion is corrected here.
No coordinates are reconstructed from speed or normalized progress.

The [author's loader](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/assetto_corsa_gym/AssettoCorsaEnv/motec_loader.py)
maps world horizontal axes as `(Car Coord Y, -Car Coord X)`. Its rename is source
mapping evidence; raw file units and the following numerical audit provide
additional validation. This is a simulator world frame, not surveyed geometry.

## Measured Barcelona evidence

All 205 previously validated laps have finite X/Y. Across those laps:

| Measurement | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| Observed path length (m) | 4559.180 | 4607.169 | 5177.549 |
| Observed endpoint separation (m) | 0.383 | 1.434 | 21.588 |
| Largest source coordinate step (m) | 1.330 | 1.604 | 2.471 |
| XY distance / integrated source speed | 0.999454 | 0.999612 | 1.000163 |
| Source clock largest gap (s) | 0.0225 | 0.026 | 0.050 |

Finish-area first-point dispersion is 6.02 × 8.617 m across recordings, consistent
with different driven lines in a common frame. Stops produce up to 8704 duplicate
coordinate steps in a lap; these observations must remain in temporal analysis.
Large driven lengths and a 21.6 m endpoint gap require per-lap quality checks;
technical timing validation alone does not certify usable geometry/alignment.

Source speed (km/h), brake/throttle (%), steering (deg), lap timer (s), RPM (rpm),
gear (integer-coded), lateral/longitudinal acceleration (G) are finite in the
inspected source channels. Export frequency is declared 50/100 Hz, not a verified
native acquisition rate. Steering sign/calibration and acceleration filtering
are source conventions; comparisons keep their units without inventing physical
road-wheel angles. `Car Pos Norm` is position-like and renamed by the author to
NormalizedSplinePosition; export interpolation/latency/reverse semantics remain
unverified and it will not be used for spatial alignment.

## Other actual data

The GT7 bundle has eight validated laps with source simulator world X/Z mapped
to canonical X/Y in metres. Endpoint separations are 1.98–4.52 m, path lengths
5081.95–5107.85 m, and XY/speed distance ratios 1.00051–1.00059. Positions are
promising for geometry and common-reference projection. Steering is publisher
derived with unverified calibration, and sway/surge units are unverified: related
physical KPIs must be unavailable. The original attachment has integrated-position
provenance and no validated complete laps, so it cannot establish circuit-section
lap comparison. CSV/Parquet sources require declared metric world coordinates,
common frame and validated lap timing; column names alone are insufficient.

## Decision before proceeding

| Function | Decision |
| --- | --- |
| Spatial resampling, radius/curvature | Feasible on actual Barcelona/GT7 coordinates, with gap/jump/closure validation |
| Automatic corner segmentation and weighted apex proxy | Feasible as reference-trajectory descriptors; not authoritative circuit corners/apices |
| Spatial alignment of two laps | Feasible to investigate via sequential projection onto one reference; reject ambiguity, reverse motion, excessive offset or missing coverage |
| Corner KPIs | Feasible conditionally on aligned observations and verified channel units |
| Circuit-section time delta | Conditional on reliable common-reference alignment and explicit observed endpoint coverage; no time-normalized or independent-distance fallback |

Proceed with a separate, deterministic engine and a page-local raw-coordinate
adapter. Preserve the existing analysis source values, lap eligibility and shared
cursor implementation. Validate synthetic known geometry first, then actual
recordings and raw event overlays. Retain unsupported laps and return explicit
unavailable results instead of discarding them or manufacturing alignment.

Full source/channel and per-lap evidence is captured in
`artifacts/v090-feasibility-raw.json`; a reproducible audit runner and release
measurements accompany the final report. No model, training or LLM is introduced.
