# Dataset expansion v0.6

The release integrates **55 verified lap targets from 11 separately identified
human recording sessions and eight participant codes**, all Monza / Dallara F317.
All accepted laps have 100% finite/in-range speed, throttle, brake and RPM values.
This satisfies the project's engineering gate; it does not establish generalization.

## Provenance, acquisition and cost

Source: [AssettoCorsaGym](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym),
pinned revision `ad1df12c49cce10f159ba31967744750bb9edd8b`.
Attribution: the Assetto Corsa Gym research team / dasGringuen, associated with
[A Simulation Benchmark for Autonomous Racing with Large-Scale Human Data](https://assetto-corsa-gym.github.io/).
Publisher-declared [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Original exports are retained unchanged locally. Our decoding, filtering,
canonical mappings and summaries are modifications/derivations, not source labels.
No simulator/game assets or original telemetry are committed to Git.

The publisher distinguishes human records from SAC trajectories in its
[dataset card](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym#dataset-summary)
and [recording catalogue](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/data/paths.yml).
The selected participant IDs appear under human recordings. SAC/MPC paths are
excluded; the catalogue itself has an ambiguous MPC type entry, so directory
names alone are not accepted as evidence of human driving.

Remote file listings and the pinned Hugging Face `paths-info` sizes were inspected
before downloads. **48 files, 241,902,674 payload bytes (241.903 decimal MB)** were
acquired, leaving 58,097,326 bytes below the 300,000,000-byte payload cap. The
manifest records every exact size, pinned URL and SHA-256. LFS objects were checked
against the published SHA-256; ordinary Git objects against their Git blob IDs.
Existing files were reused, never overwritten or downloaded twice. The source-size
response and research pages add small metadata overhead; HTTP/TLS traffic and
browser-tool research transfers were not measured as network-layer byte counts.
No dependencies were downloaded.

The first acquisition stopped because an initial ledger incorrectly counted
expected LFS objects as already received. The ledger was corrected against actual
files before continuing; every transfer succeeded, no payload was repeated.
The corrected acquisition ledger is preserved in
[DATASET_MEASUREMENTS_V06.json](DATASET_MEASUREMENTS_V06.json).

All raw originals are ignored under `data/raw/acgym_monza_dallara/`. Short local
paths preserve the original filenames while avoiding Windows path-length issues.
[ACGYM_MANIFEST_V06.json](ACGYM_MANIFEST_V06.json) is the full machine-readable
acquisition manifest. `python -m scripts.download_acgym` is an **explicit** manual
download command; neither startup nor a page visit runs it. Verified local files
are reused without network requests.

## Numeric reader and clocks

`motorsport/ingestion/motec.py` reads bounded little-endian numeric LD structures.
It checks magic, linked channel pointers/cycles, file/sample bounds, numeric
encodings and frequencies. It executes no downloaded code and never reads pickle.
The companion XML reader rejects DTD/entity declarations and oversized documents.

The implementation uses public factual format descriptions from
[racingmagick](https://pages.tobi.lutke.com/racingmagick/motec_format) and
[motecldparser's field specification](https://pkg.go.dev/github.com/riccardotornesello/motecldparser/ldfile).
The actual ACGym layout puts the eight-byte short name before the unit and uses
116-byte linked channel blocks, differing from the racingmagick example. The
reader follows pointers rather than assuming a fixed stride; unsupported layouts
fail rather than guessing. Integer physical scaling is
`(raw / scale * 10**(-decimals) + shift) * multiplier` with documented zero-factor
fallbacks. Known source units must match before canonical normalization.

Canonical channels: speed km/h, controls %, RPM rpm, gear as reported, steering
degrees, lateral/longitudinal acceleration g. Source lap count, current/last lap
time (s), normalized car position and session countdown remain audited raw fields.

Each file's selected channels share a declared **50 or 100 Hz export grid**.
The first inspected file is 100 Hz; later files include 50 Hz. Repeated current-lap
times show held/resampled source observations. The dataset card describes 50 Hz
telemetry generally; **native sampling and export interpolation/hold latency are
not certified here**. Canonical session time is the declared LD grid checked
against the simulator countdown. ML prefixes use the source lap timer, not a
synthetic final-distance fraction. Causality is guaranteed against the published
export's future samples, not against undocumented pre-export resampling internals.

## Lap validation

Every accepted segment requires all of:

1. Integral source lap count and a witnessed consecutive counter increment.
2. Monotonic current-lap timer, allowing repeated held samples; maximum forward
   source-clock step 200 ms, boundary coverage within 50 ms.
3. A plausible 20–600 s next-counter `Last Lap Time` target, agreeing with both
   export-grid duration and consecutive LDX beacon times within 50 ms.
4. Countdown consistency without resets or steps over 200 ms; whole-segment
   countdown duration agrees with the declared export grid within 100 ms.
5. No source lap-invalid flag and source progress starting within 1% of the line
   and reaching at least 99%, with bounded normalized values.

The next-counter timing packet supplies a **target only**. It is removed from
`ReplayLap.frame` and never becomes a model feature. A leading segment is accepted
only if timer, progress and the first beacon support a complete start. Final
unwitnessed segments are rejected. Summary `laps_info.csv` is preserved but not
used to infer boundaries: its `steps` totals do not reliably describe LD coverage.

## Measured exclusions and independence

Of 19 LD exports, 18 pass recording metadata checks, covering 690,856 export rows.
They contain **106 timing-validated laps and 25 rejected boundary segments**.
The per-lap decision and reasons are in
[ACGYM_LAP_AUDIT_V06.csv](ACGYM_LAP_AUDIT_V06.csv).

- `20240408_WL` is quarantined entirely: its header date is 6 April, whereas its
  recording folder indicates 8 April. No session identity or target is fabricated.
- Six A-coded stint exports contain 51 timing-valid laps. Their order-coded series
  identity is not established as independent physical sessions. They are grouped
  conservatively into one unresolved unit, inspected but excluded from robust ML.
- Multiple stints within `20240423_IN` remain **one** physical session.
- Date/participant folders with consistent header dates identify the remaining
  physical recording units. Generic driver header strings such as `adrianremonda`
  are not treated as participant identity. Participant codes come from the source
  catalogue and are not verified real-world identities.
- Full raw SHA-256 deduplication and clock-relative one-second signatures of
  speed, pedals and RPM detect repeated captures and exact derived lap exports.
  No duplicate signatures were found. These checks cannot prove the absence of
  every near-duplicate or undocumented export; the A-series exclusion is deliberate.

| Physical session | Participant | Accepted laps | Evaluation partition |
|---|---|---:|---|
| 20240229_HC | HC | 3 | train |
| 20240304_AB | AB | 4 | train |
| 20240313_OP | OP | 6 | train |
| 20240329_HC | HC | 6 | train |
| 20240329_ST | ST | 5 | train |
| 20240405_NH | NH | 5 | train |
| 20240417_HC | HC | 5 | validation |
| 20240423_IN | IN | 6 | validation |
| 20240424_KW | KW | 5 | test |
| 20240425_RRK | RRK | 5 | test |
| 20240426_AB | AB | 5 | test |

Accepted targets span **109.200–169.156667 s**. All 275 configured elapsed-time
snapshots pass coverage checks. The unusually broad skill/lap-time distribution
remains in the data; no test-error-driven outlier removal was performed.

## Limits

Only one car/track is evaluated; shifts in skill, automatic/manual gear settings,
feedback and recording conditions remain. Some participants recur across sessions.
This is a future-session holdout, not a guarantee for unseen drivers, cars or tracks.
No verified common distance reference is introduced. GT7's eight validated laps
remain a separate experimental case study; the original attachment still has no
validated lap targets. Both v0.5 raw datasets and their manifests are unchanged.
