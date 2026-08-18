import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from lala_workflow.domain import (
    GenerationResult,
    OutputArtifact,
    ResolvedRunConfig,
    RunStatus,
)
from lala_workflow.reporting import REVIEW_FIELDS, review_csv_text, summary_markdown


def make_result() -> GenerationResult:
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    return GenerationResult(
        run_id="RUN-1",
        provider="runway",
        model="gen4_image",
        status=RunStatus.SUCCEEDED,
        started_at=now,
        completed_at=now,
        duration_seconds=0,
        outputs=(
            OutputArtifact("output-001", "task-1", Path("outputs/run/output-001.png"), "a" * 64, 1),
            OutputArtifact("output-002", "task-2", Path("outputs/run/output-002.png"), "b" * 64, 1),
        ),
    )


def test_review_csv_has_exact_schema_one_row_per_output_and_blank_human_fields() -> None:
    result = make_result()
    text = review_csv_text(
        result,
        {"output-001": {"seed": 42}, "output-002": {"seed": None}},
    )

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert tuple(reader.fieldnames or ()) == REVIEW_FIELDS
    assert len(rows) == 2
    assert rows[0]["seed"] == "42"
    assert rows[1]["seed"] == ""
    human_fields = REVIEW_FIELDS[7:]
    assert all(rows[0][field] == "" for field in human_fields)
    assert all(rows[1][field] == "" for field in human_fields)


def test_summary_reports_mode_counts_and_paid_calls() -> None:
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    config = ResolvedRunConfig(
        run_id="RUN-1",
        preset="baseline_identity",
        provider="runway",
        model="gen4_image",
        ratio="1080:1440",
        resolution="1080:1440",
        count=2,
        concurrency=2,
        max_retries=3,
        poll_timeout_seconds=900,
        overall_timeout_seconds=1800,
        network_timeout_seconds=60,
        download_timeout_seconds=60,
        live=True,
        allow_live_calls=True,
        estimated_credits_per_output=None,
        max_estimated_credits=None,
        api_version="2024-11-06",
        sdk_version="5.14.0",
        anchor_set_version="1.0",
    )

    text = summary_markdown(config, make_result(), paid_calls=2)

    assert "Mode: `live`" in text
    assert "Requested candidates: 2" in text
    assert "Downloaded outputs: 2" in text
    assert "Paid calls made: 2" in text
