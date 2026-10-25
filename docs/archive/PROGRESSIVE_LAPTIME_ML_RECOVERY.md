# Progressive lap-time ML/DL archive and recovery

## Exact recovery point

- Verified code: **v0.8.1**.
- Local archival reference: `archive/progressive-laptime-ml-v081`.
- Commit: **`3b96553a10881ea654f5fe2a505cb7b3169d4d1d`**.
- Original development branch: `feat/sim-telemetry-v081`, retained.
- Active scope-reset branch: `feat/scope-reset-v082`.

The incoming v0.8.1 tree contained six modified tracked files and 33 untracked
release files. It was verified again: **287 tests passed**, zero failed/skipped,
217 existing Keras/Torch deprecation warnings, 222.14 s. Those changes were
committed locally before any removal. No push, merge, history rewrite, reset or
branch deletion was performed.

The archive includes original SVR, dense and remaining SVR, stop-aware correction,
training/evaluation/feature workflows, ordered Ridge, Keras GRU, prediction UI,
dedicated tests, reports and historical requirements. The old source and reports
were deliberately removed from the active tree; [the reviewed file ledger](RETIRED_FILES_V082.json)
lists every removed path. Shared analysis infrastructure is preserved.

## Restore into a separate worktree

From this repository, use an unused sibling directory and branch name:

```powershell
git show --no-patch archive/progressive-laptime-ml-v081
git -c core.autocrlf=false worktree add -b restore/progressive-laptime-v081 "../Motorsport-ML-v081" archive/progressive-laptime-ml-v081
```

This creates a separate checkout; the active application remains on its current
branch. The per-command line-ending setting preserves LF bytes needed by frozen
CSV/JSON evidence hashes. Do not switch/reset the active checkout to recover the
research version.

After restoring its ignored local dependencies below, use a separate Python 3.11
environment in the recovered worktree, install the archived requirements and
follow its archived README:

```powershell
Set-Location "../Motorsport-ML-v081"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-sequence.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

These are manual recovery instructions, not actions performed by v0.8.2.
The current project environment has not been uninstalled or modified.

## Git is not a backup of ignored dependencies

No ignored file was moved or deleted. The
[local artifact inventory](LOCAL_ARTIFACT_INVENTORY_V082.json) records existing
locations, byte counts and SHA-256 digests for **244 protected files**
(912,978,399 bytes including raw data, model binaries and F5 files).
It also lists five private signing-key locations, without their contents.

Manually back up and restore the required directory layout into the recovered
worktree before expecting old experimental tests/results to reproduce:

| Existing local path | Recovery purpose |
| --- | --- |
| `data/raw/acgym_barcelona_dallara/` | Original Barcelona LD/LDX and source tables; all 205 validated laps |
| `data/raw/acgym_monza_dallara/` | Historical ACGym/Monza source records |
| `data/raw/gt7_trial_mountain_962c/` | Historical GT7 Parquet bundle |
| `data/raw/telemetry.parquet` | Original inspected attachment for analysis regression |
| `artifacts/barcelona_v071/models/` | Operational reference binary, metadata and paired local signing key |
| `artifacts/barcelona_v072/models/` | Feature/weighting research artifacts and key |
| `artifacts/barcelona_v080/models/` | Dense SVR, ordered Ridge and Keras GRU fold/research artifacts and key |
| `artifacts/barcelona_v081/` | Focused cadence models, measured observations, runtime/stop evidence and key |
| `artifacts/models/` | Earlier signed Monza/GT7 artifacts and key |
| `artifacts/v081/`, `artifacts/barcelona_v081/pytest-final.xml` | Historical browser/JUnit evidence referenced by the old release |

Copy whole artifact directories, including metadata sidecars and hidden
`.local-signing-key` files, using trusted private storage. Keys authenticate their
paired model bytes; generating a replacement key does not authenticate old models.
Never commit/upload keys, secrets, large model files or raw recordings to Git.
Do not load untrusted replacement pickle/joblib files to bypass verification.

The archival reference is local because remote actions were prohibited.
A manual repository backup or Git bundle can preserve the tracked history:

```powershell
git bundle create "../motorsport-progressive-v081.bundle" archive/progressive-laptime-ml-v081
```

A bundle still excludes ignored dependencies. Preserve those separately with the
same relative paths and verify their digests against the inventory. No such
backup/copy is automatically executed by the cleanup.

## Reproducibility limits

Exact old experimental reproduction needs compatible Python/package versions,
source files, signed models and private keys. Original pinned sequence versions
and model-rebuild commands live in the archived README/requirements. Retraining
can produce new signed artifacts; it does not guarantee identical binary bytes.
The old historical test remains historical evidence.

The active v0.8.2 app has no model package/artifact requirement. Its automated and
browser tests explicitly forbid prediction imports and model-file access without
moving the original files. The archive is recoverable history, not an active
feature or a recommendation to resume this research.
