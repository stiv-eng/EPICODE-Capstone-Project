Place original Parquet/CSV telemetry files here. The v0.4 working copy is
`data/raw/telemetry.parquet` (ignored by Git). The source in Downloads is unchanged.
The application discovers files here and in `data/demo/` without external downloads.
Only this README is versioned; raw data must not enter Git.

Additional cached bundles: `gt7_trial_mountain_962c/` (v0.5) and
`acgym_monza_dallara/` (v0.6). The latter contains pinned human LD/LDX exports and
small summary CSVs, 241,902,674 bytes in total, publisher-declared CC BY 4.0.
See `docs/DATASET_EXPANSION_V06.md` for attribution, exclusions and clock limitations.
Only verified independent ACGym records enter the ML corpus. No pickle is read.

To reproduce acquisition deliberately, use `python -m scripts.download_acgym`.
It verifies/reuses cached files and enforces the 300 MB payload ledger cap.
There is no automatic download during application startup or page navigation.
