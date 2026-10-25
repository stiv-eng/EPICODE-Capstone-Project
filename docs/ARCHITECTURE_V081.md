# Architecture v0.8.1

The existing v071 operational and v080 SVR/GRU paths are unchanged. New code is isolated in `replay_v081.py`, `cadence_v081.py` and `progressive_v081.py`; reports/artifacts use V081 names.

```mermaid
flowchart TD
    Source[Timestamped source observations] --> Index[Prefix sufficient statistics / original 13 features]
    Index --> Schedule[Elapsed-time scheduler: 5 / 1 / 0.5 s]
    Schedule --> Signed[Cached signed v080 held-out-fold SVR-DENSE]
    Signed --> Raw[Preserved raw final time]
    Raw --> Bound[max raw / observed elapsed]
    Source --> Detector[Causal sample-level stop / resume detector]
    Bound --> Heuristic[Frozen causal remaining time / resume transition]
    Detector --> Heuristic
    Heuristic --> Fragment[Per-session cached recorded replay / Streamlit fragment]
    Fragment --> Hover[Existing browser-only shared cursor]
    Labels[Verified final labels] --> Reveal[Separate explicit retrospective reveal]
    Labels --> Offline[Offline development-only metrics]
    Dev[Original 169 laps / frozen five folds] --> Training[One optional 1 s SVR / matched per-lap penalty]
```

`PrefixIndex` precomputes causal cumulative interval statistics and validates source-clock continuity. Predictions retain nominal and observed seconds. `ReplayEngine` advances a detector once per arriving sample, independent of display cadence. Stop onset and resume model queries are cached at actual sample timestamps, giving identical corrections at shared cutoffs. Rewind initializes isolated state when needed. No wall clock or target enters that engine.

The UI authenticates and caches existing fold models, validates full corpus identity once per ordinary rerun and retains a mutable engine in session state, never shared across user sessions. Fragment timer reruns avoid reloading datasets, recalculating full corpus identity or loading models per checkpoint. Charts contain only observed prefix signals and selected predictions. Targets are read only by the explicit reveal block and offline scorer. Changing replay context resets reveal.

One-second training is an explicitly invoked offline function with training-only preprocessing. It stores signed fold bundles separately and never replaces Model A or the operational reference. Separate fresh-process workers measure each inference cadence. Frozen evidence has SHA-256 bindings; the baseline inventory includes raw recordings, previous reports, signed model bytes and F5 files. Existing signing keys remain private local files.
