# Quickstart: One-Click Character Switch

This guide validates Phase 1 locally without authorizing a paid provider call.

## Install

```bash
uv sync --extra dev --extra ui
```

Existing CLI-only users may continue with `uv sync --extra dev`; Streamlit remains optional.

## Start the local screen

```bash
uv run --extra ui streamlit run src/lala_workflow/ui/app.py
```

The one-page screen asks for:

1. 正面清晰照片 / front-facing photo
2. 全身照片 / full-body photo
3. 3/4 角度照片 / three-quarter photo

Choose **Create Character**. The default offline mode validates and builds the profile, records
hash/provenance automatically, leaves the current character active, and reports that live previews
are unavailable until an operator supplies existing authorization. It does not produce fake media.

When an operator has separately configured and explicitly authorized the existing bounded live
gates, the same screen can complete static and motion previews. The user then makes exactly one
final choice: **Reject** or **Approve & Activate**.

## Validate the backend without UI

```bash
uv run python -m lala_workflow character list
uv run python -m lala_workflow character show lala-v1
uv run python -m lala_workflow character import \
  --face /path/to/front.png \
  --full-body /path/to/full-body.png \
  --three-quarter /path/to/three-quarter.png \
  --name "Candidate 07"
uv run python -m lala_workflow character build CHARACTER_ID
uv run python -m lala_workflow character preview CHARACTER_ID --dry-run
```

Expected offline outcome: profile/source hashes exist, `lala-v1` remains active, provider call count
is zero, and the candidate is `READY_FOR_GENERATION`, not activation-ready.

## Mocked end-to-end verification

```bash
uv run pytest tests/characters tests/integration/test_character_static.py \
  tests/test_character_video_preview.py -q
```

The mocked lifecycle writes real local fixture image/video files, reaches `READY_FOR_APPROVAL`, and
tests activation/rejection without any network access.

## Activate and roll back

After both real or mocked review artifacts are present and valid:

```bash
uv run python -m lala_workflow character activate CHARACTER_ID
uv run python -m lala_workflow character activate lala-v1
```

Each command uses the same atomic registry switch. No character or historical output is deleted.

## Regression validation

```bash
uv run pytest -q
uv run python -m compileall -q src tests
uv run python -m lala_workflow validate
uv run python -m lala_workflow generate --preset baseline_identity --count 10 --dry-run
uv run python -m lala_workflow generate --preset home_decor --count 5 --dry-run
uv run python -m lala_workflow generate --preset product_page_clean --count 5 --dry-run
git diff --check
```

Goal 2 preview/validation commands retain their existing input and review gates. No live command is
part of this quickstart.

## Live safety

Character UI and CLI do not create new bypass flags. Real static/motion preview remains disabled
unless every existing exact permission, credential, smoke, budget, count, retry, timeout, and staged
review prerequisite is satisfied. Never place secrets in YAML, command output, logs, or screenshots.

## Phase 1 limitations

Phase 1 does not generate a three-quarter view, side view, expressions, product pose, face
embeddings, or automatic identity score. It does not add multi-user approval, authentication, a
database, cloud deployment, or automatic production keyframe/video approval.
