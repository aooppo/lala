from dataclasses import replace

import pytest

from lala_workflow.providers.base import ProviderValidationError
from lala_workflow.providers.runway import RunwayImageProvider


def provider(runway_capabilities) -> RunwayImageProvider:
    return RunwayImageProvider(runway_capabilities, api_key="test-key", client=object())


def test_valid_request_passes(generation_request, runway_capabilities) -> None:
    provider(runway_capabilities).validate_request(generation_request)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("model", "unverified_model", "unsupported model"),
        ("ratio", "1:1", "ratio and resolution"),
        ("output_count", 2, "output_count=1"),
        ("seed", -1, "seed must be between"),
    ],
)
def test_invalid_capability_fields_are_rejected(
    generation_request, runway_capabilities, field, value, message
) -> None:
    request = replace(generation_request, **{field: value})

    with pytest.raises(ProviderValidationError, match=message):
        provider(runway_capabilities).validate_request(request)


def test_too_many_references_are_rejected(generation_request, runway_capabilities) -> None:
    request = replace(
        generation_request,
        references=generation_request.references + generation_request.references,
    )

    with pytest.raises(ProviderValidationError, match="0..3 references"):
        provider(runway_capabilities).validate_request(request)


def test_invalid_or_duplicate_tags_are_rejected(generation_request, runway_capabilities) -> None:
    first, second = generation_request.references
    duplicate = replace(second, tag=first.tag)

    with pytest.raises(ProviderValidationError, match="duplicate reference tag"):
        provider(runway_capabilities).validate_request(
            replace(generation_request, references=(first, duplicate))
        )

    invalid = replace(second, tag="Bad-Tag")
    with pytest.raises(ProviderValidationError, match="invalid reference tag"):
        provider(runway_capabilities).validate_request(
            replace(generation_request, references=(first, invalid))
        )
