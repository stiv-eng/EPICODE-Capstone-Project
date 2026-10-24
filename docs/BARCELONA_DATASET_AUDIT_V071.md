# Barcelona dataset recovery v0.7.1

All **205 technically valid complete laps** are eligible. The 116 laps previously
excluded solely for uncertain participant/capture metadata or date conflicts are
recovered, plus one objectively supported timer-rounding case. No valid lap was
removed for being slow, atypical or difficult to predict.

## Source, integrity and scope

The preserved acquisition contains **70 LD recordings, 70 paired LDX files and
11 laps_info CSV files**, totaling **574,612,274 bytes** in
17 author folders. No additional download was needed in v0.7.1. All LD/LDX hashes
are rechecked against [the pinned manifest](BARCELONA_MANIFEST_V07.json), revision
`ad1df12c49cce10f159ba31967744750bb9edd8b`. Human provenance follows the author's pinned catalogue;
SAC/MPC/AI policies, pickle payloads and other car/track domains are excluded.
Attribution: Remonda et al., *A Simulation Benchmark for Autonomous Racing with
Large-Scale Human Data*, NeurIPS 2024 / AssettoCorsaGym / dasGringuen. Source-declared
license: CC BY 4.0; the original files stay unchanged and ignored by Git.

The publication's 247 laps / 70 stints / 612,557 human steps are source-level
counts, not an assertion that 247 independently verified complete targets can be
reconstructed from these exports. Our measured counts are:

| Measure | v0.7 | v0.7.1 |
|---|---:|---:|
| Downloaded recordings | 70 | 70 |
| Recordings imported for validated targets | 62 | 62 |
| Complete cross-checked targets | 204 | 205 |
| Eligible complete laps | 88 | 205 |
| Validated laps excluded only for metadata | 116 | 0 |
| Remaining rejected candidate spans in imported recordings | 82 | 81 |
| Exact raw/lap duplicates found | 0 / 0 | 0 / 0 |

117 admitted laps retain metadata uncertainty flags, including the additional WL
lap. A, XX and WL are included; unknown codes are not invented driver identities.
Core speed/pedals/RPM coverage is **100%** for every admitted lap. Every lap supports
all five causal checkpoints: **1,025 snapshots**. Optional steering/gear absence
is supported by existing training-only imputation, rather than requiring every
telemetry channel. All currently admitted exports supply those channels.

## Objective extra recovery and retained target checks

WL `20240325_WL/...stint_2.ld`, source lap 12: source final timer **98.8475 s**,
witnessed next-counter Last Lap Time **98.847 s**, export-grid duration **98.860 s**.
The old nonnegative final-timer difference rejected 0.5 ms of field rounding.
v0.7.1 allows at most **1 ms** negative difference, with all other checks intact:
consecutive witnessed counter, valid next-packet target, increasing lap timer,
<=200 ms timer steps, initial timer <=50 ms, LDX start/end and export/target
agreement <=50 ms, countdown agreement, source invalidation and progress coverage.
The historical Monza default remains zero negative tolerance. An unwitnessed
tail, absent beacon or contradictory target is never reconstructed as a lap.

## Every remaining unusable source/span

Eight recordings lack usable increasing paired beacon evidence:

| source | reason |
|---|---|
| 20240426_NiM/laps/ks_barcelona_&_dallara_f317_&_NiM_&_stint_8.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_26.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_29.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_32.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_33.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_37.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_39.ld | Missing/nonmonotonic source beacons |
| 20240426_XX/laps/ks_barcelona_&_dallara_f317_&_adrianremonda_&_stint_43.ld | Missing/nonmonotonic source beacons |

Their unverified internal spans are not added to the denominator of 81 rejected
candidates from the 62 timing-importable recordings. NiM has a 965-byte LDX with
Details and no Beacons, TotalLaps=1 while LD counters run 15..22; metadata leniency
cannot supply a missing independent boundary. Such recordings remain available
for signal exploration through the analysis-only adapter.

Reasons across the 81 rejected candidate spans overlap:

| reason | spans |
|---|---|
| no witnessed consecutive finish/next-packet target | 62 |
| invalid target | 63 |
| incomplete lap timer boundary coverage | 81 |
| beacons/export grid/source target disagree by over 50 ms | 81 |
| incomplete source progress coverage | 81 |
| countdown clock gap/reset or export clock disagreement | 3 |
| lap timer reset/missing/gap over 200 ms | 2 |

[BARCELONA_LAPS_V071.csv](BARCELONA_LAPS_V071.csv) records every accepted/rejected
candidate with source, source lap/start sample and all reasons. The
[recording ledger](BARCELONA_RECORDINGS_V071.csv) covers all 70 recordings.
No remaining candidate fails only a participant/date criterion.

## Actual duplicate checks and split assumptions

Raw SHA-256 detects exact repeated captures. A second hash covers every canonical
feature-safe lap sample and verified target, excluding source identity from the
hash. It found **0 exact lap duplicates**. Matching 1-second rounded trajectory
signatures with consistent targets would link recording groups while retaining
nonidentical laps; **0 such cross-capture links** were found. These checks do not
prove every near-duplicate or unknown session link absent.

Explicit recording-folder stints stay together. XX is a mixed-date collection;
each actual LD capture forms a block, with no assumed common participant. A-series
folders remain distinct recording blocks, without claimed physical independence.
Same/missing driver labels alone never merge groups. The resulting **51 blocks**
are export/recording units, not 51 certified independent physical sessions.

Seed-42 permutation of sorted blocks freezes approximately 60/20/20 membership
before fitting or filtering. Unequal block sizes give:

| partition | recording_blocks | laps | snapshots |
|---|---|---|---|
| test | 11 | 36 | 180 |
| train | 30 | 103 | 515 |
| validation | 10 | 66 | 330 |

All prefixes and laps of a block remain together. See exact
[memberships](BARCELONA_SPLIT_V071.csv), [freeze](BARCELONA_SPLIT_V071.json) and
[preregistered protocol](BARCELONA_PROTOCOL_V071.json). Unknown capture links,
recurring participants and inconsistent absolute chronology limit independence.
This is an **offline retrospective recording-block holdout**, not evidence of
unseen-session, unseen-driver or prospective chronological generalization.

Corpus identity: `46884dc894e1b0a1dd0c76baa5beaf2fff79d02e24bebccdae9701c326da1523`. The v0.7 audit/protocol and downloaded raw
files remain preserved; only dedicated V071 evidence is produced.
