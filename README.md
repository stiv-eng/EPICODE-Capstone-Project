# Motorsport Telemetry Analyzer - v0.4 Dataset Foundation

Explore local racing telemetry without a running simulator or FastF1 downloads.
The real supplied dataset is available locally at `data/raw/telemetry.parquet`.
Raw telemetry is excluded from Git; a fresh clone must obtain the file separately.

## Start from VS Code (Windows)

1. Open this project folder in VS Code.
2. In **Run and Debug**, select **Motorsport Telemetry Analyzer**.
3. Press **F5**. The profile runs Streamlit with the selected project interpreter.
4. Open **Data Explorer** in the sidebar. Select `data/raw/telemetry.parquet`.

The existing `.venv` uses Python 3.11.9 and already contains all core packages.
`.vscode/settings.json` points Python at `.venv/Scripts/python.exe`.
The Python and Python Debugger extensions are installed in this workspace's user profile.
If VS Code previously selected a different interpreter, select the project `.venv`
with **Python: Select Interpreter** once; VS Code preserves explicit interpreter selections.
The older launch profile remains available.

## Data Explorer

- **Dataset e qualita**: metadata, original/canonical previews, missing/infinite values,
  duplicate records/timestamps, sampling gaps, constants and exploratory outliers.
- **Segnali**: select up to eight numeric signals and a sample interval. Speed,
  pedals, steering, RPM and gear are available in the real attachment.
- **Posizione**: a source-coordinate trace colored by speed where available.
- **Giri**: complete laps only when counters and progress validate boundaries.

For another file, choose **Carica file** and upload CSV or Parquet. Uploads remain
in memory. Alternatively place a local file in `data/raw/` or `data/demo/`.
Canonical names work directly; expand **Mappatura colonne e unita** to declare
source columns and units and press **Applica mappatura**. Supported time units:
seconds, milliseconds, microseconds, nanoseconds or datetime; speed: km/h or m/s;
pedals: percent or fraction. Units are never guessed from a signal's maximum.
CSV delimiters comma, semicolon, tab and pipe are detected; single-channel CSV
is supported. Nonstandard encodings/layouts should be exported as ordinary UTF-8 CSV.
The audited profile is automatically selected only for a local file whose SHA-256
matches the supplied attachment, not merely its filename.

Calculations use complete data. Plotly views use at most 5,000 rows selected by
bucket extrema. Source rows, timestamps and extra channels are preserved;
no missing telemetry is replaced with synthetic measurements. Canonical invalid
values become missing, with their original values still available in the raw frame.

## Findings from the real dataset

**116,987 samples, 86 source channels, 1,827.078 seconds, about 64.03 Hz.**
No null/infinite cells or exact duplicate rows; 14 constant channels; 1,245 repeated
simulator timestamps and one 2.36-second acquisition gap. Speed reaches 260.589 km/h.
`lap_progress` and `completed_laps` are both always zero. Coordinates are consistent
with integrated velocities, so proximity returns are not certified lap boundaries.
Lap analysis and lap-time model targets are unavailable for this attachment.
Assetto Corsa / Imola provenance cannot be established from its embedded metadata.

See the measured [dataset audit](docs/DATASET_AUDIT_V04.md),
[architecture](docs/ARCHITECTURE_V04.md) and [release report](docs/RELEASE_V04_REPORT.md).

## Environment and validation

For a new installation only (the current environment is already prepared):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Core dependencies: NumPy, Pandas, PyArrow, Plotly, Streamlit, scikit-learn and pytest.
FastF1, Keras, PyTorch and artifact support are optional in `requirements-extension.txt`.
Existing deep learning packages were reused; none were reinstalled.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.audit_dataset
.\.venv\Scripts\python.exe -m scripts.smoke_app
```

On a core-only installation, run tests with
`--ignore=tests/test_model.py --ignore=tests/test_evaluation.py`.
Those two historical training tests require the optional extension dependencies.
Real-data tests skip when the ignored local attachment is absent. CI separates core
and legacy training checks. Small synthetic fixtures are used only in tests.
Optional browser captures can be regenerated with
`python -m scripts.smoke_app --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"`;
this optional path uses the installed `websockets` package. Screenshots and logs are
ignored under `artifacts/`. The temporary server/browser are stopped after checking.

## Legacy and roadmap

Enable **Mostra pagine legacy Formula 1** to expose historical dashboards.
They require optional FastF1 resources and may need network access. Their models
and feature functions are preserved separately from the local ingestion pipeline.
Historical setup and model explanations are archived in
[README_LEGACY_V03.md](docs/README_LEGACY_V03.md).

v0.5 should obtain reliable finish crossings, lap/session identifiers, source units,
provenance and car/track metadata before lap comparisons or supervised lap-time
training. v0.6/v0.7 can migrate SVR and Keras using validated canonical data.
No v0.5 features or model migration are implemented in v0.4.
