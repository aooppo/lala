# Quickstart: Offline Subject Lock Verification

No live permission variables or provider credentials are required or allowed.

```bash
uv sync --extra dev
uv run python -m compileall -q src tests
uv run pytest -q tests/test_subject_lock.py tests/test_subject_lock_review_package.py
uv run pytest -q tests/test_video_motion_smoke.py
uv run pytest -q tests/test_video_motion_variations.py
```

Analyze V6 locally:

```bash
uv run python -m lala_workflow video subject-lock \
  --run-id LALA-VIDEO-20260820-052930-MOTION-SMOKE-001 \
  --package-dir outputs/review-packages/P1-1-MOTION-SMOKE-V6-20260820
```

Expected: `OUTSIDE_THRESHOLD` with material non-zero drift/scale, or `INSUFFICIENT_EVIDENCE`; never false within-threshold after tracking failure. Output states it is diagnostic evidence, not automatic human QA.

Run the canonical three-candidate P1-2 dry-run with the archived V6 reviewed copy and confirm three planned calls, zero submissions/task IDs/provider construction/paid calls. Then run:

```bash
uv run pytest -q
git diff --check
```

Verify approved-source hashes pre/post and scan tracked/runtime text evidence for secrets, Bearer/authorization headers, and signed queries. Do not invoke a real `--live` command.
