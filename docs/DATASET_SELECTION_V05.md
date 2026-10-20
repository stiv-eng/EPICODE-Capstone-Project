# Dataset selection v0.5

Research and byte inspection performed on 20 October 2026. **Selected for local
integration: Ricardo Queiroz's GT7 Trial Mountain / Porsche 962 C collection**.
Its advantage is inspectable raw sequences, explicit packet units, a small download
and verifiable next-lap timing targets. Its size and single-session provenance
remain insufficient for robust supervised evaluation. ACGym is the stronger
expansion target once a representative human subset has been independently audited.

## Candidate comparison

“Validated laps” below always means validated locally in this release, not the
number advertised by a publisher. Publisher counts are explicitly marked.

| Dataset / verified source URL | Format and size | Local validated laps / independent coverage | Channels | License / access | Data Analysis | ML | Progressive lap-time DL | Limitations |
|---|---|---|---|---|---|---|---|---|
| [GT7 Trial Mountain / Porsche 962 C](https://huggingface.co/datasets/rpqueiroz/gt7-trial-mountain-962c) | 16 raw lap Parquets plus grid/sectors/track/card; **29,122,896 downloaded bytes** | **8 accepted laps**, one session/driver/car/track; 95,796 raw rows, **114 columns measured** | Speed, byte pedals, RPM, gear, derived wheel steering, world coordinates, tyres, suspension and packet body-motion signals | Publisher declares **CC-BY-4.0** for their contribution; anonymous pinned download succeeded | Integrated; rich raw sequence analysis | Candidate target/feature plumbing and small case study; release eligibility false | Prefix experiments possible later; eligibility false for robust evaluation | Rejects 8 source groups; no common surveyed distance reference; only one session; body-motion calibration unknown |
| [AssettoCorsaGym](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym), [capture project](https://github.com/dasGringuen/assetto_corsa_gym) | Pickle, MoTeC LD/LDX, CSV summaries; project describes roughly **120 GB** full download | **Not validated locally**; publisher reports 15 human drivers and 64 million total steps, including 2.3 million human steps | Publisher describes speed, controls, position, acceleration at 50 Hz; exact per-export schemas vary | Card **CC-BY-4.0**; API/file listing and one small human-session summary downloaded | Promising multi-car/track analysis | Preferred expansion candidate after raw validation and human/policy separation | Best researched expansion lead, conditional on causal time/progress and target audit | Heterogeneous exports; most listed raw files are pickle; no raw sequence or completeness certification here |
| [ESRL SimRacing KPI repository](https://github.com/ESRLAccount/SimRacing_KPITelemetryDataAnalysis), [associated paper](https://doi.org/10.1016/j.chbr.2024.100414) | Current `Lap dataset.csv`: **328,055 bytes, 476 × 98 measured** | **No raw lap boundaries validated**; actual table has 124 PID values, one Laguna Seca track string and one car; 476 positive LapTime fields | Whole-lap speed/pedal/steering statistics, engineered features, labels and metadata | Public repository has no LICENSE file in inspected root; redistribution permission not established | Useful existing aggregates | Potential retrospective tabular baseline after permission, preprocessing and leakage audit | Current CSV cannot supply causal raw prefixes | Repository description references a different 1,327-lap Brands Hatch study; current table is not that advertised population |
| [Forza Rio de Janeiro, Kaggle](https://www.kaggle.com/datasets/alexhexan/fm7-rio-de-janeiro-race-telemetry), [HF mirror](https://huggingface.co/datasets/Nasim435/RaceTelemetry-Rio-de-Janeiro) | CSV; HF preview reports 94,519 rows / 63.8 MB | **Not validated locally**; preview lap counter reaches 4 | Preview includes controls, speed, RPM, lap timers, coordinates and wheel channels | Kaggle page yielded no readable body; HF API has no license declaration; no raw download attempted | Potential small session example | Too little verified independent evidence | Unverified targets, units and license | Mirror attribution does not establish permission; preview is not an audit |
| [Zenodo curated 2024 F1 season](https://zenodo.org/records/20061496) | Versioned ZIP **19,060,593 bytes** in record API; publisher describes Parquet/CSV/warehouse layers | **Not validated locally**; publisher describes 24 rounds / 120 sessions | Lap/sector times, compounds, results, weather and identities described; high-frequency driver inputs not established | API declares **CC-BY-4.0**; requests citation of curation and underlying timing source | Potential timing/session analysis | Promising tabular targets and grouping, pending archive audit | Raw progressive inputs not verified | Record/file metadata checked; archive bytes not downloaded and telemetry completeness not assumed |

## Evidence and reproducibility

The GT7 revision is pinned to
`a2e0709efc751904552890bf8398f3090763c8da`. Every downloaded file's URL, size and
SHA-256 appears in [GT7_MANIFEST_V05.json](GT7_MANIFEST_V05.json). The original
Parquets remain unchanged under `data/raw/gt7_trial_mountain_962c/`, excluded from
Git. Run `python -m scripts.download_gt7` explicitly to reproduce the download;
the app never downloads data at startup. Existing differing files are preserved
and produce an integrity error. Normal loading verifies the raw lap-file hashes.

Actual metrics and capabilities for both integrated datasets are reproducible with
`python -m scripts.audit_v05`; see
[DATASET_MEASUREMENTS_V05.json](DATASET_MEASUREMENTS_V05.json). Public API snapshots,
the small research CSVs and temporary inspection outputs remain local under
`artifacts/research_v05/` and are not included in Git.

ACGym's inspected revision is `ad1df12c49cce10f159ba31967744750bb9edd8b`.
Its API lists **17,131 files**, including 15,882 pickle files, 242 CSVs, 202 LDs
and 204 LDXs. The 328-byte
[Monza/Dallara human-session summary](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym/resolve/ad1df12c49cce10f159ba31967744750bb9edd8b/data_sets/monza/dallara_f317/20240329_HC/laps/laps_info.csv)
was parsed as **6 rows × 7 columns** with LapCount, LapTime, speed and steps.
These six summary rows are not six independently validated complete raw laps.
The dataset viewer itself reports heterogeneous-schema errors, so a blind
`load_dataset` across every CSV is unsuitable. No pickle was deserialized and no
third-party repository code was executed.

The [actual ESRL CSV](https://raw.githubusercontent.com/ESRLAccount/SimRacing_KPITelemetryDataAnalysis/master/Lap%20dataset.csv)
was downloaded and parsed, rather than inferring its contents from the repository
description. Its publisher `validlap` column is 1 for all 476 rows; that label
does not replace a raw timing/coverage audit. Whole-lap engineered features and
cluster/performance labels also warrant a future target-leakage review.

## GT7 validation result

The source contains an out-lap group 0 and timed groups 1–15. A source lap label
alone is not accepted. The adapter checks:

1. Agreement between file lap field and packet `lap_count`.
2. At most one witnessed start reset; the counter-leading stale timer packet is
   excluded from canonical lap labels.
3. Finite, strictly increasing in-lap `current_lap_ms`, with no repeated values,
   no additional reset and no step exceeding 100 ms.
4. Start timer within 100 ms of zero; last observed timer within 100 ms before
   the next group's stable `last_lap_ms` target, with a plausible 20–600 s duration.
5. Finite monotonic driven-distance coverage from near zero to over 1 km.

Accepted source IDs: **2, 3, 4, 5, 6, 11, 13, 14**. Packet-reported target durations
span **103.712–108.650 s**. Groups 1, 7, 8, 9 and 12 have repeated timer values;
10 has extra resets; 0 is an out-lap; 15 has no subsequent finish target and extra
resets. The excluded boundary packets remain in raw/session analysis.
“Validated” means these recorded-data consistency rules pass; it does not imply
official race validity, transponder precision or verified track limits.

Session elapsed time uses capture `wall_time`; **2,038.917117 s** of host span
contains six gaps over the observed-time threshold, the largest **137.955674 s**.
The effective host recording rate is **46.983273 Hz** versus a median positive
interval corresponding to **60.011217 Hz**. Lap analysis uses the simulator's
own lap timer and the independent next-lap target, not host duration or publisher
`dt` reconstruction. No official time is estimated from the integrated distance.

GT7 speed/pedals/temperature/position units follow the source card's explicit
packet definitions. Pedals convert byte 0–255 to percentage. Planar coordinates
use world x/z; y is preserved as elevation. Body-motion and derived steering
calibration remain unverified. Quaternions are not treated as heading angles.
Driven distance is not a verified common spatial reference, so cumulative lap
delta stays unavailable; normalized driven-distance plots are labelled approximate.

## Attribution and redistribution

Attribution for the integrated source: **Ricardo Queiroz (2026), GT7 Telemetry:
Porsche 962 C '88 at Trial Mountain**, linked above, under the publisher-declared
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Our changes are separate
canonical normalization, validation, analytical summaries and visualization.
The source card limits its license statement to the author's contribution; this
is not a grant over third-party game assets or trademarks. No game assets or raw
telemetry are committed. CC BY attribution includes author/source, license link
and identification of changes; the license does not imply endorsement.

No raw data from candidates with uncertain permission was added to the repository.
Public accessibility and platform mirroring are not treated as redistribution
authorization. ACGym use should retain its published attribution; the ESRL table
requires permission clarification before any redistribution.

## Recommendation for v0.6 and v0.7

Use the integrated **GT7 eight-lap subset in v0.6** to test feature contracts,
target joins, whole-lap grouping and simple case-study baselines. Preserve its
single-session limitation and false robust-training flags. It is an integration
fixture and a small observational case study, not a population benchmark.

For **v0.7**, acquire and audit a bounded **ACGym human subset spanning several
sessions/drivers**, using a documented conversion from trusted exports to Parquet.
Keep human and policy trajectories distinct, validate units and targets against
raw clocks, and reserve whole sessions chronologically before generating prefix
examples. Do not begin full Keras training merely because sample rows are numerous.
No candidate currently inspected satisfies the release's robust ML/DL gate.
