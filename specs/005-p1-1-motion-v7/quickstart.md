# Quickstart: P1-1 Motion V7 Targeted Fix

Run from the repository root after installing the development environment:

```bash
uv run pytest tests/test_motion_v7.py -q
uv run pytest tests/test_subject_lock.py tests/test_subject_lock_review_package.py tests/test_video_motion_variations.py -q
uv run python -m lala_workflow video motion-v7-dry-run --keyframe hero --project-root .
python -m compileall .
uv run pytest -q
git diff --check
```

Expected dry-run evidence:

- one unique run under `runs/`;
- three ordered candidates with 3 planned calls and estimator-derived 75 credits under current configuration;
- zero submissions, task IDs, provider instances, and paid calls;
- three blank review rows;
- V6 baseline values and V7/delta `PENDING` comparison values;
- no V7 Subject Lock/package artifact because no video exists;
- P1-2 Live remains blocked pending an explicit later P1-1 human pass.
