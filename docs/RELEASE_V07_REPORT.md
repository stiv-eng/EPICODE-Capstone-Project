# v0.7 preserved checkpoint — Barcelona acquisition and audit

This checkpoint preserves work completed before the user's v0.7.1 instruction
explicitly replaced the restrictive eligibility policy. It is not a claim that
the planned Barcelona ML evaluation was executed.

- Baseline: v0.6.3 `7e304cc`; clean initial tree; 193 baseline tests passed.
- Source: AssettoCorsaGym, pinned `ad1df12c49cce10f159ba31967744750bb9edd8b`,
  authors' human catalogue pinned `9e79864e4c5cf9971dc9cc260d20113b54198d9d`.
- 151 LD/LDX/CSV files acquired, 574,612,274 payload bytes against a 750,000,000-byte
  cap. All 70 numerical recordings retained unchanged; no pickle/policy download.
- 62 recordings imported for validated targets; 204 complete targets cross-checked;
  88 admitted under the original metadata policy, 116 excluded; 11 identified
  groups/eight participant codes. Eight recordings lack usable beacon evidence.
- The original preregistered 12-group/6–3–3 gate failed. No Barcelona model was
  fitted, no model ranking or MAE was reported, and no final split/test was forced.
- The configured adapter, acquisition/resume command, audit, gated future runner,
  domain/serialization checks and Barcelona UI paths are preserved here.
- Full checkpoint suite: **193 passed, 92 warnings in 125.11 s**. Focused regression:
  63 passed. Historical frozen check: all 390 Monza and 60 GT7 predictions match
  within 1e-9 s. This checkpoint has no newly completed Chrome acceptance claim.

See `BARCELONA_AUDIT_V07.json`, `BARCELONA_LAPS_V07.csv`,
`BARCELONA_RECORDINGS_V07.csv`, `BARCELONA_MANIFEST_V07.json`,
`BARCELONA_PROTOCOL_V07.json` and `ML_STATUS_V07.json` for actual evidence.
The v0.7.1 policy and results will be separate files; these audit/protocol records
are retained for comparison. Original datasets, historical models and frozen
prediction files remain intact. No push, merge or history rewrite occurred.
