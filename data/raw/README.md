# Local telemetry recordings

Place original CSV/Parquet recordings here, or upload them in Data Explorer.
Raw files stay local and are excluded from Git. `telemetry.parquet`, when present,
is the original privately supplied attachment; it is not distributed or needed
to run the application.

Supported optional public bundles:

| Directory | Source and attribution | Reproduce |
| --- | --- | --- |
| `gt7_trial_mountain_962c/` | [Ricardo Queiroz: GT7 Trial Mountain / Porsche 962 C](https://huggingface.co/datasets/rpqueiroz/gt7-trial-mountain-962c), publisher-declared CC BY 4.0 for their contribution; about 29 MB | `python -m scripts.download_gt7` |
| `acgym_monza_dallara/` | [AssettoCorsaGym / dasGringuen research team](https://huggingface.co/datasets/dasgringuen/assettoCorsaGym), publisher-declared CC BY 4.0; about 242 MB | `python -m scripts.download_acgym` |
| `acgym_barcelona_dallara/` | Same AssettoCorsaGym source, Barcelona GP / Dallara F317 human MoTeC recordings; about 575 MB | `python -m scripts.download_barcelona all` |

ACGym capture project: [Assetto Corsa Gym](https://github.com/dasGringuen/assetto_corsa_gym).
Pinned revisions, original URLs, byte sizes and hashes are recorded in
`docs/GT7_MANIFEST_V05.json`, `docs/ACGYM_MANIFEST_V06.json` and
`docs/BARCELONA_MANIFEST_V07.json`. The app relies on these manifests for loading
and source integrity; their versioned names are intentional.

Original exports are preserved unchanged. Decoding, filtering, unit conversion
and canonical mappings are application derivations, not publisher annotations.
No simulator/game assets, raw recordings or model weights are distributed here.
Acquisition is explicit; application startup never downloads data. Existing
differing files are preserved and reported rather than silently overwritten.
Keep local acquisition ledgers under `artifacts/` when resuming downloads.
