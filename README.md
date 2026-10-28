# Motorsport Telemetry Analyzer — v0.9.3

A local Motorsport **Data Analysis** application built with Python, Streamlit,
Plotly, NumPy and Pandas. Explore recorded sessions, inspect driver inputs and
vehicle dynamics, and compare verified laps or time windows.

## Start on Windows / VS Code

The existing project interpreter and F5 configuration are preserved:

1. Open this project folder in VS Code.
2. Select **Motorsport Telemetry Analyzer** in Run and Debug.
3. Press **F5**, then open **Data Explorer**.

For a new Python 3.11 environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The local application needs no simulator connection, trained models or model
artifacts. Simulator telemetry support is independent of external timing services.

## Use the application

| Page | Active functionality |
| --- | --- |
| Home | Entry to the analysis workflows |
| Session Overview | Source information, measured-time signal statistics and data availability |
| Data Explorer | Signals, Driver Inputs, Vehicle Dynamics, G-G, Tyre Analysis, recorded Cockpit inspection and Position / Track Map |
| Telemetry Comparison | Verified laps or session windows, stable lap ordering/colors and synchronized hover/cursors |
| Telemetry Lap Analysis | Deterministic spatial lap comparison, inferred corners/apex proxies, section deltas, engineering KPIs and JSON facts |

In Data Explorer choose an installed local recording or upload CSV/Parquet.
Explicit column/unit mapping supports other telemetry sources. Complete laps are
available only when timing boundaries are verified; otherwise use session windows.
Track maps and channels appear only when supported by the actual source.
Calculations use full-resolution observations while chart point counts are bounded.

Supported installed examples are **Barcelona GP / Dallara F317 (205 validated
complete laps)**, ACGym Monza / Dallara and GT7 Trial Mountain / Porsche 962 C.
Raw recordings remain under ignored `data/raw/`. No data is downloaded on startup.
Generic CSV/Parquet imports work without these example datasets.

## Compare completed laps

Open **Telemetry Lap Analysis**, choose the reference recording/lap and analyzed
recording/lap, then inspect the measured total delta, section contributions and
selected-corner signals/KPIs. The default corner radius threshold is **150 m**;
expand the geometry parameters to change it. The curvature-weighted centre is an
operational apex proxy. Reference and analysis laps have independent session/lap
selectors in two columns. Rejected spatial comparisons show reasons and observed
problem regions while preserving the verified recorded laps. Partial comparisons
recover supported sections and show one combined unallocated accounting residual.
The checkered flag marks a recorded position near the verified finish boundary.
Export the full comparison with **Esporta fatti JSON**.

The raw Barcelona LD files contain actual metre world coordinates omitted by the
older analysis adapter. This page reads those channels explicitly; GT7 also has
metric world coordinates. No coordinates are reconstructed from normalized lap
progress. Generic imports require verified coordinate units/frame and complete
timing; unsupported sources retain explicit availability messages.

All sections come from one reference trajectory. Sequential geometric projection
checks offsets, reverse motion, crossings and coverage before producing section
deltas. An unverified seam is marked as an unclassified boundary section, with
its time retained. A rejected alignment does not produce corner losses. Unknown
units, missing events and uncertain braking associations remain unavailable or
uncertain KPIs. Measurements do not establish causes or physical racing apexes.
See [alignment limits](docs/LAP_ALIGNMENT_V090.md) and
[KPI definitions](docs/DETERMINISTIC_KPI_DEFINITIONS_V090.md).

## Scope and verification

Progressive final-lap-time prediction has been discontinued. Its implementation,
experiments, dedicated tests and dependency manifests are archived in the local
Git reference `archive/progressive-laptime-ml-v081`. See the
[recovery guide](docs/archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md) for the exact commit
and the ignored datasets/models/private signing keys required for historical recovery.
The active app contains telemetry analysis; this release adds no replacement predictor.

```powershell
python -m pytest -q
```

The optional real-source integration checks require the installed local recordings.
Browser verification forbids prediction-package imports and model-file access
without moving or deleting those files. Existing environments may still contain
historical libraries; they are not required by the active app.

Read the [v0.9.3 release report](docs/RELEASE_V093_REPORT.md),
[feasibility audit](docs/TELEMETRY_DATA_FEASIBILITY_V090.md),
[architecture](docs/ARCHITECTURE_V090.md),
[verification](docs/VERIFICATION_V090.json) and
[future-direction criteria](docs/NEXT_RELEASE_RECOMMENDATION.md).
Earlier numbered analysis reports are historical records. v0.9.0 introduces no
ML, DL, LLM, trained model or API requirement.
