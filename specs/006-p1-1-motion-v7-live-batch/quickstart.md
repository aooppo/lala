# Quickstart: P1-1 Motion V7 Controlled Live Batch

All implementation validation is offline. Never export a real provider credential for these commands.

```bash
uv run pytest tests/test_motion_v7_live.py tests/test_motion_v7.py -q
uv run pytest tests/test_video_motion_smoke.py tests/test_video_motion_variations.py -q
uv run pytest tests/test_subject_lock.py tests/test_subject_lock_review_package.py -q
python -m compileall .
uv run pytest -q
git diff --check
```

Guard-only CLI validation may invoke `motion-v7-live` without authorization and must fail before provider construction. Authorized orchestration is tested only by injecting a fake provider directly into the same runner used by the future command.

Expected fake success evidence:

- one parent run and exactly thirteen artifacts;
- three prevalidated requests and exactly three submissions in A/B/C order;
- prompt SHA-256 values match the immutable V7 prompts;
- known estimates of 25/25/25 and 75 total under current config;
- three correctly associated task IDs/results and no fourth task;
- three blank Human QA rows and pending V7 Subject Lock diagnostics;
- P1-2 Live remains blocked.

Expected partial fake evidence for A success/B submission error:

- two submission attempts, zero automatic retries/replacements;
- A task ID retained, B failed, C not submitted;
- append-only parent evidence remains complete and sanitized.

No command in this quickstart performs a real Runway call or generates real V7 video.
