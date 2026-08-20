# CLI Contract: Character Management

All commands use `python -m lala_workflow` or the installed `lala-workflow` entry point. They accept
`--project-root` and return 0 on success, 2 on validation/state errors, 3 on provider execution
failure, and 4 on external/live authorization blockers, consistent with the existing CLI.

## Existing static command extension

```text
lala-workflow generate ... [--character CHARACTER_ID]
```

Resolution order is explicit character, active registry character, then legacy manifest fallback.
Production generation rejects staging/failed/rejected profiles; the character preview service uses
an internal explicit staging allowance.

## `character list`

```text
lala-workflow character list [--project-root PATH]
```

Outputs JSON with registry revision, active/previous IDs, and ordered character summaries. No
technical path is required from the user.

## `character show`

```text
lala-workflow character show CHARACTER_ID [--project-root PATH]
```

Outputs the redacted current profile, build/preview status, and integrity result. Unknown IDs fail
without creating files.

## `character import`

```text
lala-workflow character import \
  --face PATH --full-body PATH --three-quarter PATH \
  [--name DISPLAY_NAME] [--project-root PATH]
```

Copies exact bytes into controlled storage, generates the technical ID, creates the first profile
and registry entry, and returns character ID/status/profile hash. Input paths never become output
paths. No provider call occurs.

## `character build`

```text
lala-workflow character build CHARACTER_ID [--project-root PATH]
```

Revalidates sources, creates deterministic reference/preflight evidence, and transitions to
`READY_FOR_GENERATION`. It makes no provider call.

## `character preview`

```text
lala-workflow character preview CHARACTER_ID \
  [--dry-run | --live] [--max-runway-credits N] [--project-root PATH]
```

`--dry-run` is the default behavior and records a zero-call plan/status only. `--live` uses all
existing static and video live guards and budgets. It never modifies the active character. Success
with both verified media transitions to `READY_FOR_APPROVAL`; authorization absence returns exit 4
and leaves `READY_FOR_GENERATION`.

## `character activate`

```text
lala-workflow character activate CHARACTER_ID [--project-root PATH]
```

Requires complete approved-source-ready profile and both preview artifacts. It records an explicit
local-user approval/activation event and performs a revision-checked atomic switch. It is also the
rollback command for `lala-v1`.

## `character reject`

```text
lala-workflow character reject CHARACTER_ID [--project-root PATH]
```

Writes a rejected snapshot and registry revision while leaving active unchanged. Evidence is not
deleted.

## Output safety

JSON output may include IDs, statuses, hashes, relative paths, timestamps, and diagnostic status.
It never includes credential values, authorization headers, signed query strings, data URIs, or
provider SDK objects.
