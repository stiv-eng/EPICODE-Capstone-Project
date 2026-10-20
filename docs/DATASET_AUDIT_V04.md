# Dataset audit v0.4

Measured from the real attachment; regenerate with `python -m scripts.audit_dataset`.

- Audit generated (UTC): 2026-10-20T18:52:08.111532+00:00
- Input: `C:\Users\stefa\Desktop\EPICODE\CAPSTONE PROJECT\data\raw\telemetry.parquet`
- Original: `C:/Users/stefa/Downloads/telemetry.parquet` (preserved).
- Size: 55,558,924 bytes; SHA-256: `fcec6ac8a8625f493e3440646c499a6991d76a2bd15d81d87d765662eef0b9e7`.
- Shape: **116,987 rows × 86 columns**; 1 Parquet row group.
- Types: float64: 83, int64: 3.
- Embedded metadata contains Pandas schema/index information only. No track, car, driver, session identity, unit dictionary, license or collection provenance is embedded.
- Assetto Corsa / Imola provenance is **unverified**. Channel names and signal behavior are compatible with simulator telemetry but do not prove its origin.

## Quality and timing

- Missing cells: 0; infinite values: 0; exact duplicate records: 0.
- Constant channels (14): `lap_progress`, `completed_laps`, `brake_temp_fl`, `brake_temp_fr`, `brake_temp_rl`, `brake_temp_rr`, `turbo_boost`, `drs`, `tc`, `abs`, `brake_bias`, `air_temp`, `road_temp`, `water_temp`.
- Constant does not imply erroneous: settings and ambient temperatures can be constant. Zero lap fields and water temperature cannot provide the corresponding analysis.
- `timestamp`: span 1827.078000000 s; 1245 duplicate values; 0 backward steps; effective rate 64.029012 Hz.
  Median positive step 0.016000000 s (62.500000 Hz); maximum gap 2.360000000 s; gaps above 1.000 s: 1.
- `wall_time`: span 1827.081349611 s; 0 duplicate values; 0 backward steps; effective rate 64.028895 Hz.
  Median positive step 0.015571117 s (64.221467 Hz); maximum gap 2.358424187 s; gaps above 1.000 s: 1.
- Largest timestamp gap: source samples 116983→116984, elapsed 1824.687000→1827.047000 s.
- Approximate acquisition is 64 Hz, not a strictly uniform grid. The rounded millisecond timestamp has 1,245 repeats; wall_time preserves acquisition order but is not automatically substituted for simulator time.
- Source order, duplicate timestamps and all observations are retained. Canonical nonnumeric/nonfinite values become missing, while raw values remain available.

## Signals and units

- Speed: 1.005120–260.589294 km/h; sample mean 144.863175 km/h.
- Controls: throttle 0.000000–1.000000; brake 0.000000–1.000000. Both are bounded 0–1 with endpoint saturation; the attachment profile explicitly interprets these as fractional pedal signals and multiplies by 100.
- RPM: 76–8396; gear: 0–6.
- `timestamp` and `wall_time` spans agree to within milliseconds, supporting seconds as the time scale.
- `speed_kmh` agrees with 3.6×the velocity norm: median ratio 1.000149798, 1st/99th percentiles 0.998447033/1.000777656. This supports the declared speed scale; it does not prove every velocity channel uses world coordinates.
- `rpms`→`rpm`; `steer_angle`→`steering`; `pos_z`→canonical second planar axis `pos_y`. The original columns are retained.
- Steering, accelerations, temperatures, loads, pressures and positions retain source units. Names suggest interpretations, but no unsupported degrees/radians or force conversions are applied.
- Vehicle dynamics: lateral/longitudinal/vertical accelerations, velocities, attitude/rates, suspension, wheel loads, slip, wheel speeds, camber and ride heights. Controls include pedals, steering, gear and electronic settings. Tyre thermal/pressure/wear channels and fuel are present.
- No fabricated distance, final lap-time targets or replacement channels are generated.

## Position and lap investigation

- `lap_progress`: unique values [0.0]; `completed_laps`: [0]. Both are unusable for lap boundaries.
- Planar bounds: x -1150.962281…687.368045; z -146.589825…873.624159; endpoint distance from origin 293.530646 source units.
- Finite-step planar-speed / declared-speed ratio (speed >10 km/h): median 1.000111058; p01/p99 0.998321930/1.000728760.
- Rotated local-velocity integration check: median per-step position residual 2.43584807845e-14, maximum 1.2698186461e-13 source units. Close agreement suggests positions are integrated rather than an independent geometric reference; accumulated drift cannot be ruled out.
- Within a 30-unit radius of the initial point: 16 visits including the initial fragment. Nearest-approach elapsed times: 0.000, 132.093, 255.906, 379.593, 501.890, 624.750, 744.484, 863.515, 982.718, 1103.859, 1222.812, 1342.062, 1459.359, 1577.734, 1693.547, 1817.125 s.
- Intervisit periods span 115.813–132.093 s. These are proximity candidates, **not validated lap times**.
- The initial point is not identified as a start/finish line. Proximity alone does not establish a directional finish crossing, closed-lap coverage, pit exclusion, reset exclusion or a complete first/last lap. Duration plausibility alone cannot certify boundaries.
- Decision: no geometric segmentation promoted to valid laps. **0 validated complete laps**; lap-dependent controls and models remain unavailable for this attachment. Session-level analytics and the coordinate trace remain useful.

## Suspicious observations

- `slip_fr` maximum 1462.292725, p99 3.599917; `slip_rr` maximum 98.037071, p99 1.292796: extreme tails merit source/sensor investigation.
- `ride_height_r` minimum -0.022941589; negative observations: 12. Source units/meaning require confirmation.
- IQR outliers below use 3×IQR fences only when IQR >0. Racing signals are multimodal; these flags are not evidence of corruption and no flagged observations are silently discarded.

## Complete measured schema

| Channel | dtype | Missing | Infinite | Unique | Min | Median | Max | Constant | 3×IQR flags |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| timestamp | float64 | 0 | 0 | 115742 | 692571.453 | 693483.796 | 694398.531 | False | 0 |
| wall_time | float64 | 0 | 0 | 116987 | 1.7802332e+09 | 1.78023411e+09 | 1.78023503e+09 | False | 0 |
| lap_progress | float64 | 0 | 0 | 1 | 0 | 0 | 0 | True | 0 |
| completed_laps | int64 | 0 | 0 | 1 | 0 | 0 | 0 | True | 0 |
| speed_kmh | float64 | 0 | 0 | 116408 | 1.00512016 | 141.775604 | 260.589294 | False | 0 |
| rpms | int64 | 0 | 0 | 4561 | 76 | 5761 | 8396 | False | 0 |
| gear | int64 | 0 | 0 | 7 | 0 | 3 | 6 | False | 0 |
| throttle | float64 | 0 | 0 | 167 | 0 | 1 | 1 | False | 0 |
| brake | float64 | 0 | 0 | 13058 | 0 | 0 | 1 | False | 0 |
| clutch | float64 | 0 | 0 | 145 | 0 | 1 | 1 | False | 0 |
| steer_angle | float64 | 0 | 0 | 51331 | -0.899999976 | 0 | 0.899999976 | False | 28035 |
| g_lat | float64 | 0 | 0 | 116903 | -2.92047119 | 0.0538782477 | 3.03708076 | False | 23 |
| g_vert | float64 | 0 | 0 | 116905 | -1.25929344 | 0.000166613667 | 2.69317961 | False | 2413 |
| g_lon | float64 | 0 | 0 | 116731 | -2.25887966 | 0.26538837 | 2.03248024 | False | 4204 |
| vel_x | float64 | 0 | 0 | 112888 | -8.14249229 | -0.018453598 | 9.73583508 | False | 9238 |
| vel_y | float64 | 0 | 0 | 116434 | -0.873414457 | 0.385908514 | 1.27732706 | False | 266 |
| vel_z | float64 | 0 | 0 | 116487 | -0.077954419 | 39.367836 | 72.3845444 | False | 0 |
| slip_angle | float64 | 0 | 0 | 116969 | -0.329678639 | -0.000467747988 | 0.373531916 | False | 12486 |
| yaw_rate | float64 | 0 | 0 | 116944 | -1.29734838 | 0.00491072005 | 1.47644281 | False | 13342 |
| pitch_rate | float64 | 0 | 0 | 116934 | -0.879077077 | -0.000588816823 | 0.598293006 | False | 2686 |
| roll_rate | float64 | 0 | 0 | 116914 | -1.22244036 | -0.000330749899 | 1.91836464 | False | 3307 |
| heading | float64 | 0 | 0 | 116559 | -3.14157224 | 0.0148689449 | 3.14149666 | False | 0 |
| pitch | float64 | 0 | 0 | 116859 | -0.105618134 | -0.00703909621 | 0.120537683 | False | 756 |
| roll | float64 | 0 | 0 | 116898 | -0.118150279 | 0.00279945345 | 0.10103897 | False | 968 |
| susp_fl | float64 | 0 | 0 | 114376 | 0.0306703113 | 0.051482901 | 0.0875026584 | False | 7 |
| susp_fr | float64 | 0 | 0 | 113857 | 0.0296791531 | 0.0525083393 | 0.091811873 | False | 35 |
| susp_rl | float64 | 0 | 0 | 115618 | 0.0309330896 | 0.0540031269 | 0.0951382965 | False | 123 |
| susp_rr | float64 | 0 | 0 | 115314 | 0.0295645408 | 0.0550149903 | 0.109566703 | False | 494 |
| load_fl | float64 | 0 | 0 | 115740 | 0 | 3583.29736 | 25818.0762 | False | 80 |
| load_fr | float64 | 0 | 0 | 115564 | 0 | 3872.65576 | 23630.4434 | False | 90 |
| load_rl | float64 | 0 | 0 | 115755 | 0 | 4254.06934 | 14362.5469 | False | 68 |
| load_rr | float64 | 0 | 0 | 115430 | 0 | 4551.19531 | 23401.293 | False | 175 |
| slip_fl | float64 | 0 | 0 | 116055 | 0 | 0.0997842029 | 26.9566574 | False | 7525 |
| slip_fr | float64 | 0 | 0 | 115941 | 0 | 0.102234602 | 1462.29272 | False | 7615 |
| slip_rl | float64 | 0 | 0 | 116068 | 0 | 0.234702647 | 5.62011003 | False | 4011 |
| slip_rr | float64 | 0 | 0 | 115900 | 0 | 0.238921717 | 98.0370712 | False | 3422 |
| psi_fl | float64 | 0 | 0 | 105431 | 16 | 23.2140675 | 24.0634155 | False | 4035 |
| psi_fr | float64 | 0 | 0 | 106562 | 16 | 23.9360256 | 25.467062 | False | 4879 |
| psi_rl | float64 | 0 | 0 | 102444 | 17 | 24.0686569 | 24.7484741 | False | 4849 |
| psi_rr | float64 | 0 | 0 | 101973 | 17 | 24.5095272 | 25.2048798 | False | 4775 |
| tyre_core_fl | float64 | 0 | 0 | 109964 | 26 | 71.0879211 | 76.3963547 | False | 4035 |
| tyre_core_fr | float64 | 0 | 0 | 111107 | 26 | 75.6001587 | 85.169136 | False | 4879 |
| tyre_core_rl | float64 | 0 | 0 | 108077 | 26 | 70.1791077 | 74.4279633 | False | 4849 |
| tyre_core_rr | float64 | 0 | 0 | 107705 | 26 | 72.9345474 | 77.2804947 | False | 4775 |
| temp_i_fl | float64 | 0 | 0 | 112988 | 26.0008926 | 68.5691757 | 81.3371124 | False | 1688 |
| temp_i_fr | float64 | 0 | 0 | 113864 | 26.0011501 | 77.9915466 | 101.627251 | False | 1649 |
| temp_i_rl | float64 | 0 | 0 | 108627 | 26.0009117 | 68.0122375 | 75.3350754 | False | 1994 |
| temp_i_rr | float64 | 0 | 0 | 109760 | 26.0029278 | 74.2061081 | 82.883194 | False | 1786 |
| temp_m_fl | float64 | 0 | 0 | 113050 | 26.0009155 | 69.9536591 | 83.9575119 | False | 1768 |
| temp_m_fr | float64 | 0 | 0 | 113733 | 26.0009155 | 74.7041168 | 96.2750092 | False | 1688 |
| temp_m_rl | float64 | 0 | 0 | 108789 | 26.000906 | 68.970108 | 76.5256653 | False | 2211 |
| temp_m_rr | float64 | 0 | 0 | 109885 | 26.002636 | 71.897377 | 80.3504944 | False | 1805 |
| temp_o_fl | float64 | 0 | 0 | 113374 | 26.0012646 | 72.7609711 | 88.4839172 | False | 1646 |
| temp_o_fr | float64 | 0 | 0 | 113557 | 26.0010033 | 72.5728912 | 92.420578 | False | 1676 |
| temp_o_rl | float64 | 0 | 0 | 108821 | 26.0012112 | 71.3842468 | 79.1704865 | False | 2014 |
| temp_o_rr | float64 | 0 | 0 | 109697 | 26.0028496 | 70.831543 | 79.2553024 | False | 1755 |
| wear_fl | float64 | 0 | 0 | 52891 | 99.0875092 | 99.5708847 | 100 | False | 0 |
| wear_fr | float64 | 0 | 0 | 56229 | 98.8582458 | 99.4525757 | 100 | False | 0 |
| wear_rl | float64 | 0 | 0 | 82424 | 99.1017761 | 99.5777206 | 100 | False | 0 |
| wear_rr | float64 | 0 | 0 | 85975 | 99.0001297 | 99.5130005 | 100 | False | 0 |
| brake_temp_fl | float64 | 0 | 0 | 1 | 26 | 26 | 26 | True | 0 |
| brake_temp_fr | float64 | 0 | 0 | 1 | 26 | 26 | 26 | True | 0 |
| brake_temp_rl | float64 | 0 | 0 | 1 | 26 | 26 | 26 | True | 0 |
| brake_temp_rr | float64 | 0 | 0 | 1 | 26 | 26 | 26 | True | 0 |
| wheel_speed_fl | float64 | 0 | 0 | 115869 | 0 | 119.250458 | 221.507431 | False | 0 |
| wheel_speed_fr | float64 | 0 | 0 | 115802 | 0 | 119.815384 | 221.80545 | False | 0 |
| wheel_speed_rl | float64 | 0 | 0 | 116489 | -3.79218936 | 111.997803 | 205.150635 | False | 0 |
| wheel_speed_rr | float64 | 0 | 0 | 116455 | -3.79218936 | 112.144714 | 205.150635 | False | 0 |
| camber_fl | float64 | 0 | 0 | 115566 | -0.24870263 | -0.0382025354 | 0.28377673 | False | 10890 |
| camber_fr | float64 | 0 | 0 | 115639 | -0.28150034 | 0.038846083 | 0.283794165 | False | 10985 |
| camber_rl | float64 | 0 | 0 | 116182 | -0.283790827 | -0.0292259492 | 0.272720873 | False | 2996 |
| camber_rr | float64 | 0 | 0 | 116356 | -0.283779085 | 0.0283481274 | 0.283792645 | False | 2446 |
| ride_height_f | float64 | 0 | 0 | 8920 | 0.00708770752 | 0.0751266479 | 0.216033936 | False | 622 |
| ride_height_r | float64 | 0 | 0 | 9990 | -0.0229415894 | 0.0754852295 | 0.200714111 | False | 1029 |
| cg_height | float64 | 0 | 0 | 9801 | 0.314659119 | 0.352394104 | 0.479076385 | False | 257 |
| turbo_boost | float64 | 0 | 0 | 1 | 0 | 0 | 0 | True | 0 |
| drs | float64 | 0 | 0 | 1 | 0 | 0 | 0 | True | 0 |
| tc | float64 | 0 | 0 | 1 | 0.100000001 | 0.100000001 | 0.100000001 | True | 0 |
| abs | float64 | 0 | 0 | 1 | 0.0799999982 | 0.0799999982 | 0.0799999982 | True | 0 |
| brake_bias | float64 | 0 | 0 | 1 | 0.659999967 | 0.659999967 | 0.659999967 | True | 0 |
| air_temp | float64 | 0 | 0 | 1 | 26 | 26 | 26 | True | 0 |
| road_temp | float64 | 0 | 0 | 1 | 34 | 34 | 34 | True | 0 |
| water_temp | float64 | 0 | 0 | 1 | 0 | 0 | 0 | True | 0 |
| fuel | float64 | 0 | 0 | 82595 | 21.8296013 | 38.6302681 | 55 | False | 0 |
| pos_x | float64 | 0 | 0 | 115742 | -1150.96228 | -465.047751 | 687.368045 | False | 0 |
| pos_z | float64 | 0 | 0 | 115742 | -146.589825 | 356.961817 | 873.624159 | False | 0 |
