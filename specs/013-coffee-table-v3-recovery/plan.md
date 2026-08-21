# Implementation Plan: Coffee Table V3 Semantic Recovery

**Spec**: [spec.md](spec.md)

## Technical Context

Python 3.11, Pillow, FFmpeg/FFprobe, existing hash/media helpers, and local filesystem only. New evidence is append-only under `outputs/`; all existing media, review packages, provider task IDs, and accounting are read-only SHA-gated inputs.

## Constitution Check

- **Immutable sources**: PASS — verifies the existing 35-file aggregate without writing approved paths.
- **Provider-neutral core**: PASS — the V3 module imports no provider adapter or SDK.
- **Paid calls bounded**: PASS — there is no Live code path; manifest authorization is false and maximum current credits are zero.
- **Offline validation**: PASS — deterministic FFmpeg frame extraction, hashes, mocked/local tests, and full offline regression are required.
- **Human approval**: PASS — Owner's explicit rejection is copied into new evidence; source-frame selection remains blank.

## Design

`coffee_table_v3_recovery.py` validates historical sources, creates three collision-safe output directories, copies the explicit Owner decision to a reviewed CSV/JSON pair, extracts frames 92/96/100/104/108/112/116 from TASK-02, and writes the V3 manifest. It does not construct a provider. A versioned V4 prompt fixes sofa support and the Coffee Table negative contract. The existing campaign CLI exposes a separate `--prepare-v3-recovery` mode.

## Verification

Run V3 focused tests, Coffee Table regression tests, complete offline pytest, video validation, compileall, `git diff --check`, credential/signed-URL scan, and protected SHA verification. Stop at the V3 Owner-review state.
