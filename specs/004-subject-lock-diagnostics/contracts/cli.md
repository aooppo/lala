# CLI Contract: Subject Lock Diagnostics

## Local package diagnostics

```text
uv run python -m lala_workflow video subject-lock --run-id <motion-smoke-run-id> --package-dir outputs/review-packages/<package-name>
```

- Requires an existing successful local motion-smoke run and package-local `video.mp4`/blank `review.csv` matching run provenance.
- Uses `configs/video-qa.yaml` thresholds.
- Creates or safely refreshes only diagnostic artifacts, checksum manifest, and adjacent ZIP.
- Makes no provider client, HTTP request, download, or paid call.
- Returns subject summary and package integrity/secret-scan status.

## Report

```text
uv run python -m lala_workflow video report --run-id <motion-smoke-run-id>
```

When exactly one matching package has subject evidence, adds scope, tracking success, drift/scale, diagnostic status, and `human_qa_status`. It never converts diagnostic status into human PASS/FAIL.

## P1-2

The existing `video motion-generate` command remains. With an immutable failed review, `--dry-run --variations 3` resolves three calls and submits zero; `--live` rejects before provider construction. No command in this feature authorizes a real live call.
