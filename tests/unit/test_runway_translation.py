from dataclasses import replace
from pathlib import Path

from PIL import Image

from lala_workflow.domain import ProviderTaskResult, TaskStatus
from lala_workflow.providers.runway import RunwayImageProvider


def test_translation_uses_only_official_sdk_fields(
    generation_request, runway_capabilities
) -> None:
    provider = RunwayImageProvider(runway_capabilities, api_key="test-key", client=object())

    payload = provider.translate_request(generation_request)

    assert set(payload) == {"model", "prompt_text", "ratio", "reference_images", "seed"}
    assert payload["model"] == "gen4_image"
    assert payload["ratio"] == "1080:1440"
    assert payload["prompt_text"] == generation_request.prompt.text
    assert [item["tag"] for item in payload["reference_images"]] == [
        "lala_face",
        "lala_look",
    ]
    assert all(item["uri"].startswith("data:image/png;base64,") for item in payload["reference_images"])
    assert "RUN-TEST" not in repr(payload)
    assert "output_count" not in repr(payload)


def test_translation_omits_unsupported_optional_seed(
    generation_request, runway_capabilities
) -> None:
    provider = RunwayImageProvider(runway_capabilities, api_key="test-key", client=object())

    payload = provider.translate_request(replace(generation_request, seed=None))

    assert "seed" not in payload


def test_download_retries_are_bounded_and_result_is_hashed(
    tmp_path: Path, runway_capabilities
) -> None:
    calls = []

    def downloader(url: str, destination: Path, timeout: float) -> None:
        calls.append((url, timeout))
        if len(calls) < 3:
            raise OSError("temporary download failure")
        Image.new("RGB", (10, 10), "red").save(destination)

    provider = RunwayImageProvider(
        runway_capabilities,
        api_key="test-key",
        client=object(),
        downloader=downloader,
    )
    result = ProviderTaskResult(
        "task-1",
        TaskStatus.SUCCEEDED,
        ("https://example.test/output.png?temporary=token",),
    )

    artifacts = provider.download_results(result, tmp_path, "output-001", 12, max_retries=2)

    assert len(calls) == 3
    assert len(artifacts[0].sha256) == 64
    assert artifacts[0].source_url_redacted == "https://example.test/output.png"
    assert artifacts[0].file.is_file()
