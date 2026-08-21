# Quickstart: Review Coffee Table Four-Task Dry Run

1. Open the package `REVIEW.md` and confirm Henry's wine-glass and sofa requirements.
2. Review TASK-01 through TASK-04 in order, especially each terminal/start state pair.
3. Confirm TASK-03 remains in the same living room and TASK-04 places body weight on the sofa only.
4. Inspect `manifest.json`; verify four five-second tasks, `16:9`, blank Owner decisions, all zero current accounting, and false Live authorization.
5. Compare `approved-sources-before.sha256` and `approved-sources-after.sha256`; they must be byte-identical.
6. Record decisions only in a later copied review artifact. Do not authorize or run Live from this package.

Expected terminal state: `READY_FOR_OWNER_4TASK_DRYRUN_REVIEW`.
