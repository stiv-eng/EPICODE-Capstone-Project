# Recommendation after deterministic Telemetry Lap Analysis v0.9.0

Keep this release deterministic. The next step is a **small manual technical
validation**, not another model or an automatic coaching layer.

| Decision item | Focused proposal |
| --- | --- |
| User problem | Determine whether displayed corner and pedal differences are useful and correctly associated with the selected driving phase |
| Simplest viable alternative | Use the existing raw telemetry comparison and the new fact table side by side, without new algorithms |
| Expected practical benefit | Identify misleading phase associations or unstable geometric proxies before users interpret them as driving advice |
| Evidence needed | Human annotations for a few corners on two fixed accepted Barcelona lap pairs, plus visible raw brake/throttle/speed traces |
| Small feasibility check | Review three corners, compare weighted/maximum-curvature landmarks, explain null/uncertain KPIs and repeat with one modest threshold change |
| Development gate | Add a narrowly justified refinement only when the manual review demonstrates a concrete measurement or usability problem |

Retain all valid timing laps and the explicit spatial rejection rules. Do not
relax quality thresholds merely to increase the successful alignment count. If
GT7 steering/acceleration measurements become important, obtain their source
calibration/unit contract first. If a later LLM demonstration is selected, limit
it initially to faithful summaries of these structured facts and validity flags;
evaluate it separately for unsupported causal statements. No ML, DL or LLM
development is justified merely by the future Capstone architecture.
