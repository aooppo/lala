# Data Model: Coffee Table Four-Task Dry Run

## DryRunPackage

Fields: package ID, status, format/duration, Henry requirement, global locks, task list, transition notes, risks, staged strategy, historical/current accounting, authorization, protected-source facts, and Owner decisions. State is created directly as `READY_FOR_OWNER_4TASK_DRYRUN_REVIEW`; it has no executable/live transition.

## TaskPlan

Fields: task ID, interval, summary, prompt path/hash, source-reference plan, start/end continuity states, hard negatives, acceptance gates, composition, checklist, risks, and blank Owner decision.

## ContinuityState

Fields: room identity, character position/orientation, wine-glass custody/location/count, table geometry/scale, sofa/fireplace relationship, and frame-presence constraint. Adjacent end/start states must be semantically compatible.

## Accounting

Historical values remain 75 credits/USD 0.75. This dry run records zero HTTP requests, Provider constructions/submissions/task IDs, paid calls, retries, replacements, credits, and USD cost.
