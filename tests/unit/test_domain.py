from datetime import UTC, datetime
from pathlib import Path

from lala_workflow.domain import (
    GenerationRequest,
    GenerationResult,
    OutputArtifact,
    PromptTemplate,
    ReferenceImage,
    RunStatus,
    make_run_id,
    to_primitive,
)


def test_make_run_id_is_human_readable_and_stable() -> None:
    now = datetime(2026, 8, 18, 21, 0, 0, tzinfo=UTC)

    assert make_run_id("runway", "baseline_identity", now, 1) == (
        "LALA-RUNWAY-20260818-210000-BASELINE-IDENTITY-001"
    )


def test_generation_request_serializes_paths_without_provider_objects() -> None:
    prompt = PromptTemplate(
        path=Path("prompts/example-v1.txt"),
        filename="example-v1.txt",
        version="v1",
        text="Use @lala_face",
        sha256="a" * 64,
        referenced_tags=("lala_face",),
    )
    request = GenerationRequest(
        run_id="RUN-1",
        output_id="output-001",
        preset="baseline_identity",
        provider="runway",
        model="gen4_image",
        ratio="1080:1440",
        resolution="1080:1440",
        prompt=prompt,
        references=(
            ReferenceImage(
                name="face",
                path=Path("assets/approved_anchors/face/example.png"),
                role="facial_identity",
                tag="lala_face",
                sha256="b" * 64,
                mime_type="image/png",
            ),
        ),
        seed=42,
        output_count=1,
    )

    payload = to_primitive(request)

    assert payload["prompt"]["path"] == "prompts/example-v1.txt"
    assert payload["references"][0]["path"].endswith("example.png")
    assert payload["seed"] == 42
    assert payload["output_count"] == 1


def test_generation_result_serializes_status_timestamps_outputs_and_errors() -> None:
    started = datetime(2026, 8, 18, 21, 0, 0, tzinfo=UTC)
    completed = datetime(2026, 8, 18, 21, 0, 5, tzinfo=UTC)
    result = GenerationResult(
        run_id="LALA-RUNWAY-20260818-210000-BASELINE-IDENTITY-001",
        provider="runway",
        model="gen4_image",
        status=RunStatus.PARTIAL,
        started_at=started,
        completed_at=completed,
        duration_seconds=5.0,
        outputs=(
            OutputArtifact(
                output_id="output-001",
                provider_task_id="task-1",
                file=Path("outputs/run/output-001.png"),
                sha256="c" * 64,
                size_bytes=123,
            ),
        ),
        errors=({"output_id": "output-002", "code": "provider_failure"},),
    )

    payload = to_primitive(result)

    assert payload["status"] == "PARTIAL"
    assert payload["started_at"] == "2026-08-18T21:00:00+00:00"
    assert payload["completed_at"] == "2026-08-18T21:00:05+00:00"
    assert payload["outputs"][0]["file"] == "outputs/run/output-001.png"
    assert payload["errors"][0]["code"] == "provider_failure"
