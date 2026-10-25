# Next development after the v0.8.2 scope reset

The progressive lap-time prediction research direction is closed. Keep the
application focused on Motorsport telemetry Data Analysis. No new direction is
selected or started by this release.

Two small possibilities are reasonable only if the user confirms the need:

| Assessment | Find the right recording faster | Make unfamiliar CSV/Parquet imports easier |
| --- | --- | --- |
| User problem | Many similarly named recordings can slow source selection | A new source may use different channel names/units |
| Simplest viable alternative | Improve naming/documentation and use the existing selector | Supply one canonical example and a short mapping guide |
| Expected practical benefit | Fewer wrong-source selections and faster comparisons | Fewer mapping errors and quicker first useful chart |
| Evidence required | Observe the user's source-selection workflow and measure mistakes/time | Collect a few representative upload difficulties and supported unit declarations |
| Small feasibility check before coding | Compare existing labels against a small proposed label/filter sketch using three recording tasks | Manually map two representative files using the existing form and document ambiguities |
| Development gate | Implement a small selector improvement only if existing naming is insufficient | Improve documentation first; consider UI changes only if the existing mapping flow remains insufficient |

Existing analysis and comparison methods should be used before adding new
infrastructure. The user will choose a direction separately. This release
implements neither option.
