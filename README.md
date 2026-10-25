# Motorsport Telemetry Analyzer — v0.8.2

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
artifacts. Existing optional Formula 1 analysis pages require
`requirements-extension.txt` (FastF1) and may access external timing services.

## Use the application

| Page | Active functionality |
| --- | --- |
| Home | Entry to the three analysis workflows |
| Session Overview | Source information, measured-time signal statistics and data availability |
| Data Explorer | Signals, Driver Inputs, Vehicle Dynamics, G-G, Tyre Analysis, recorded Cockpit inspection and Position / Track Map |
| Telemetry Comparison | Verified laps or session windows, stable lap ordering/colors and synchronized hover/cursors |

In Data Explorer choose an installed local recording or upload CSV/Parquet.
Explicit column/unit mapping supports other telemetry sources. Complete laps are
available only when timing boundaries are verified; otherwise use session windows.
Track maps and channels appear only when supported by the actual source.
Calculations use full-resolution observations while chart point counts are bounded.

Supported installed examples are **Barcelona GP / Dallara F317 (205 validated
complete laps)**, ACGym Monza / Dallara and GT7 Trial Mountain / Porsche 962 C.
Raw recordings remain under ignored `data/raw/`. No data is downloaded on startup.
Generic CSV/Parquet imports work without these example datasets.

## Scope and verification

Progressive final-lap-time prediction has been discontinued. Its implementation,
experiments, dedicated tests and dependency manifests are archived in the local
Git reference `archive/progressive-laptime-ml-v081`. See the
[recovery guide](docs/archive/PROGRESSIVE_LAPTIME_ML_RECOVERY.md) for the exact commit
and the ignored datasets/models/private signing keys required for historical recovery.
The active app contains telemetry analysis; this release adds no replacement predictor.

```powershell
python -m pytest -q
python -m scripts.verify_data_analysis_v082
python -m scripts.smoke_app --release v082 --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
python -m scripts.smoke_app --release uploads --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
python -m scripts.smoke_app --release fixtures --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

The optional real-source integration checks require the installed local recordings.
Browser verification forbids prediction-package imports and model-file access
without moving or deleting those files. Existing environments may still contain
historical libraries; they are not required by the active app.

Read the [release report](docs/RELEASE_V082_REPORT.md),
[active features](docs/ACTIVE_FEATURES_V082.md), [architecture](docs/ARCHITECTURE_V082.md),
[verification](docs/VERIFICATION_V082.json) and
[future-direction criteria](docs/NEXT_RELEASE_RECOMMENDATION.md).
Earlier numbered analysis reports are historical records; current scope is v0.8.2.
