# Motorsport Telemetry Analyzer

A local application for exploring recorded motorsport telemetry, inspecting
driver inputs and vehicle dynamics, and comparing verified laps or session
windows. Built with Python, Streamlit, Plotly, NumPy, Pandas and PyArrow.
Optional AI coaching uses LM Studio and a locally loaded Qwen3-1.7B model;
automated tests use pytest and Streamlit AppTest.

## Setup and launch

Python 3.11 is the tested environment. Clone this repository (or download and
extract its ZIP), then create an environment. On Windows:

```powershell
git clone https://github.com/stiv-eng/EPICODE-Capstone-Project.git
cd EPICODE-Capstone-Project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. If activation
is unavailable, use the environment's Python with `-m pip` and `-m streamlit`.
The included VS Code **Motorsport Telemetry Analyzer** launch configuration also
supports F5 when the project environment is selected.

The application starts without a simulator, external timing service, trained
model or LM Studio. Recordings are loaded locally; startup never downloads data.

## Main workflows

| Page | Features |
| --- | --- |
| Session Overview | Source metadata, measured-time statistics and signal availability |
| Data Explorer | Signals, driver inputs, vehicle dynamics, G-G, tyres, recorded cockpit and track map |
| Telemetry Comparison | Verified laps or time windows, stable selection colors and synchronized cursors |
| Telemetry Lap Analysis | Spatial alignment, geometric corners, section deltas, engineering KPIs, JSON export and optional AI coaching |

Calculations use full-resolution observations; charts limit displayed points.
Missing channels and uncertain units remain explicitly unavailable.

## Telemetry data

A new clone contains source manifests, not the large recordings or private
original attachment. In **Data Explorer**, select **Carica file** to upload CSV
or Parquet, or place files in `data/raw/` or `data/demo/` and select **Dataset
locale**. Column/unit mapping is available for generic imports. Canonical names
include `elapsed_s`, `speed_kmh`, `throttle_pct`, `brake_pct`, `pos_x` and `pos_y`;
only declare units and source channels that are actually known.

Session exploration and time-window comparisons work without verified lap
boundaries. Complete-lap and corner comparisons require independently validated
timing and compatible metric coordinates; a lap-number column alone is insufficient.

The supported recorded examples can be acquired explicitly with pinned,
hash-checked download commands:

```powershell
python -m scripts.download_gt7
python -m scripts.download_acgym
python -m scripts.download_barcelona all
```

These install GT7 Trial Mountain / Porsche 962 C, ACGym Monza / Dallara F317,
and Barcelona GP / Dallara F317, respectively. Barcelona exposes 205 validated
complete laps when the complete recording bundle is installed. Downloads are
optional and can be large; existing recordings are verified before reuse.
See [data sources and attribution](data/raw/README.md). Original recordings,
download ledgers and local model files remain excluded from Git.

In **Telemetry Lap Analysis**, choose reference and analyzed recordings/laps.
The default geometric corner-radius threshold is 150 m. Sections are defined
on the reference trajectory; the weighted apex is an operational geometric
proxy. Partial alignments retain reliable regions and one combined unallocated
accounting residual. Measurements establish differences, not their causes.
Use **Esporta fatti JSON** to export the deterministic report.

See [architecture](docs/ARCHITECTURE_V090.md),
[corner detection](docs/CORNER_DETECTION_V090.md),
[alignment limits](docs/LAP_ALIGNMENT_V090.md) and
[KPI definitions](docs/DETERMINISTIC_KPI_DEFINITIONS_V090.md).

## Optional AI Driving Coach

1. Start LM Studio separately, manually load a local model such as Qwen3-1.7B,
   and start its local server. An 8192-token context was used in local smoke tests.
2. Open **Telemetry Lap Analysis > AI Driving Coach**. The default API URL is
   `http://127.0.0.1:1234/v1`. Press **Connect / Refresh**, then select a loaded
   model and Italian or English. The server must expose both `/v1/models` and
   `/api/v1/models`; only loopback hosts are accepted.
3. Press **Generate Lap Coaching**, or select a corner in the existing analyzer
   and press **Generate Corner Coaching**. Each mode works independently.

If server authentication is enabled, set `LM_STUDIO_API_KEY` in the environment
before launching Streamlit. Never commit credentials or local model weights.

Coaching is ordinary text, requested as **Summary / Recommended Actions**
(**Riepilogo / Azioni consigliate** in Italian). Python prepares evidence using
consistent units and at most three decimal places; no JSON response schema or
semantic output filter is used. Successful responses are cached in the session.
Changing inputs or settings requires an explicit generation click; reruns never
trigger inference, automatic model downloads or model loading.

AI recommendations are experiments requiring driver judgment. Local Qwen 1.7B
smoke tests returned text but also confused measurements and produced unreliable
advice. Prompt instructions do not validate the generated content; compare it
with the deterministic KPI table. If LM Studio is unavailable, deterministic
analysis remains usable.

## Tests and repository scope

```powershell
python -m pytest -q tests
```

Tests use pytest and Streamlit AppTest. Synthetic fixtures run without downloaded
recordings; real-source checks skip when their optional inputs are absent. The
frozen full-corpus regression additionally needs the original local attachment
and all three recording bundles. No live LLM inference is required by the tests.

The active project contains telemetry analysis and optional local coaching.
FastF1 and experimental SVR/GRU/progressive lap-time prediction are retired.
Historical code remains in Git history; existing local data, archived models and
keys are not publication assets. Generated reports, caches, environments and raw
recordings are excluded by `.gitignore`.
