# UI architecture v0.6.2

This refinement extends [v0.6.1](ARCHITECTURE_V061.md). Its six Explorer sections,
source/selection state, canonical model, ingestion/normalization, analytical APIs
and ML/replay contracts remain available. Production ML files/pages are unchanged.

## Catalog and availability

`telemetry.source_catalog` prefers GT7, then per-recording ACGym, then other local
sources/uploads. It removes the specific `data/raw/telemetry.parquet` entry only
when its bytes match the pinned original SHA-256. Hashing is cached with file
mtime/size in the key. A different future file with that name remains discoverable.
`include_original=True` is an explicit developer/testing catalog option; the normal
application does not use it. Explicit upload registrations remain selectable.

Generic CSV/Parquet ingestion and pyarrow are intact. `explorer_source.upload_session`
recognizes the exact original bytes and uses the already audited source profile;
other uploads use the existing canonical/manual-unit workflow. No download occurs.

`analytics.channels.usable_channels` is the common pure availability check. It
requires an actual finite real numeric value in the selected frame; complex/text,
entirely nonfinite and internal UI columns are excluded. Constants remain usable.
Boolean flags are permitted only where meaningful, such as color mapping. Numeric
strings can be explicitly mapped through normalization, rather than treated as
arithmetic channels solely because their labels resemble signals.

`available_corners` and `paired_channels` build on that predicate. Tyre/dynamics
families with no usable channels are removed. Scatter plots require simultaneous
finite pairs. `motorsport_ui.widgets` prunes stale select/multiselect choices before
widget creation; no empty selectors are created. Shared source/lap/time state lives
in the existing durable keys and is not changed by these channel controls.

## Equal G-G data geometry

`motorsport_ui.gg.gg_figure` requires usable acceleration pairs with equal declared
unit labels (case-insensitive). Unknown matching source units remain explicitly
uncalibrated. Different declared units disable the diagram rather than silently
converting or claiming a physical envelope.

Full finite values determine a common symmetric padded range. Downsampling only
affects displayed points; it does not set narrower limits or discard measured
extremes. X/Y use identical ranges and constrained domains; Y anchors to X with
`scaleratio=1`. A bounded 660px Streamlit container can shrink with the viewport.
Plotly then adjusts the data domain so one source unit has the same pixel length
on both axes and the actual plotting area stays square. Figure width/height alone
are not used as evidence. Chrome checks read actual `_length`/range geometry at
1600, 960 and 480px viewport widths; measured results are in the UI test report.

## Full-resolution position adjacency and direction

`analytics.position.position_adjacency` now owns the existing edge validity rules:
finite XY/time, positive time steps, temporal-gap threshold, same validated lap,
consecutive source rows and the 20x-median spatial discontinuity guard. Both the
polyline simplifier and the direction estimate call this same function, before
any display downsampling. Source axes are unchanged.

`analytics.orientation.vehicle_orientation(frame, row_offset, metadata, adjacency)`
returns radians and a truthful provenance label. Measured heading is accepted only
with a complete verified `metadata['planar_heading']` declaration:

```python
{
    'verified': True,
    'channel': 'heading',
    'unit': 'deg',                 # must also match channel_units['heading']
    'zero_vector': [1, 0],         # in canonical source XY
    'positive_rotation': 'ccw',    # or 'cw', physical convention
    'handedness': 'right',         # or 'left', source planar basis
    'coordinate_columns': ['pos_x', 'pos_y'],
    'provenance': 'verified source convention'
}
```

`transform_heading` handles degrees/radians, zero axis, physical rotation sign,
handedness and an explicit optional display transform for axis swaps/reflections.
The current map preserves canonical source XY and uses the identity transform.
Neither current source adapter declares a trustworthy planar heading, so real
examples use the labelled estimate; GT7 quaternion components are never assumed
to be heading. Synthetic tests cover the measured-heading contract.

The estimate uses `atan2(dy,dx)` on the next full-resolution valid adjacent packet.
At a fragment end it may use a valid backward difference, labelled accordingly.
Missing positions, invalid boundaries, stationary/near-zero motion and spatial
jumps cannot create a direction. The small movement threshold combines floating
point coordinate precision and a tiny fraction of the valid median spatial step.
No heading/source values are written. Retrospective use of the next packet is
isolated from the untouched ML feature/inference modules.

`motorsport_ui.vehicle.add_vehicle` draws a six-piece top-down car as Plotly vector
paths (body, windshield and four wheels). Artwork points along mathematical +X;
vertices are rotated before rendering. Plotly converts mathematical Y into SVG
screen Y. Shapes use pixel sizing with actual-data XY anchors, so zooming changes
the map, not car size. Chrome compares the rendered windshield direction with the
expected screen vector and verifies stable artwork dimensions after zoom.

Undefined direction uses a neutral circular marker. Even stationary finite XY can
be displayed without a connected path; absent XY displays only the capability
explanation. No world coordinates are inferred from rank or normalized progress.

`trajectory_base` caches the full-resolution adjacency, bounded colored line figure
and stats. Slider changes add the actual current marker to a cached copy, rather
than recalculating trajectory segmentation. A regression test counts one segment
preparation across a slider change. UI revision includes source/selection identity
so zoom is stable within a selection and resets for incompatible datasets.

## Comparison readouts outside the data area

The native `x unified` hover used in v0.6.1 still floats near signals, and Plotly
does not expose a fixed external native-label placement through that configuration.
`comparison_hover.py` therefore renders the existing shared-legend SVG figure in a
small `components.html` iframe with a reserved side column. The installed Plotly
JavaScript bundle is inlined; no CDN or frontend package is introduced.

Traces retain the same source/window identity, deterministic color, numeric data
and channel/unit metadata. `hoverinfo='none'` suppresses floating labels while
retaining hover events. The public `plotly_hover` event fills the separate panel
using safe `textContent`, measured X/Y and trace identity/color. Its position tracks
the inspected subplot vertically but remains outside the chart's bounding rectangle.
Values persist on unhover for reading; actual relative timestamps can differ slightly
between sources and are shown independently. No interpolation is fabricated.

JSON embedded in HTML escapes `<`, and uploaded labels never become executable HTML.
The single Plotly legend remains shared across subplots, with an explicit bottom
anchor and reserved top margin to avoid title overlap when it wraps. CSV exports
and unit/track/delta guards remain in the Streamlit page.

Tradeoffs: the iframe repeats the already installed Plotly runtime in its payload,
reserves horizontal room and does not send hover events back into Python. Narrow
screens have a smaller readout column; mobile touch/accessibility interaction has
not been certified by the desktop Chrome workflow. Streamlit's generic iframe allow
list produces browser policy warnings; the report distinguishes those from errors.

## ML audit boundary

`scripts.assess_ml_v062` is an offline audit, not an application import. It verifies
original source targets, splits, metrics and allowed baselines, describes frozen
residuals at proper grouping levels, and fits exactly three unchanged configurations
on the training/validation development pool to inspect in-sample/validation gaps.
It never fits on the test population, selects variants or saves a model artifact.

Its only document outputs are allowlisted `ML_HEALTH_EVIDENCE_V062.json` and
`ML_HEALTH_GROUPS_V062.csv`; an ignored standalone figure is written under
`artifacts/v062/`. Original frozen evidence/model-store files are hash-checked
before/after. Existing `verify_ml_v061` independently verifies preservation of all
450 frozen model-prediction rows. Production ML, source adapters, prediction packages,
training/replay pages and `.vscode` have no diff from `c47fd4a`.
