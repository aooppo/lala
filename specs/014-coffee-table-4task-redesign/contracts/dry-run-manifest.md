# Contract: Coffee Table Four-Task Dry-Run Manifest

The manifest is one JSON object with schema `coffee-table-4task-dryrun/v1`, exactly four ordered tasks (`TASK-01`…`TASK-04`), intervals `[0,5)`, `[5,10)`, `[10,15)`, `[15,20)`, ratio `16:9`, and exact terminal status `READY_FOR_OWNER_4TASK_DRYRUN_REVIEW`.

Every task includes the nine requested planning fields and a blank Owner decision. Global fields include all hard locks/negatives, adjacent transition contracts, risks, recommended staged Live order, historical/current accounting, source integrity, and explicit false/zero authorization.

This contract has no command that can submit a Provider task. Any future Live implementation requires a separately reviewed, hash-bound execution manifest and explicit task-by-task Owner authorization.
