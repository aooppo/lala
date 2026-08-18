from lala_workflow.redaction import redact_text, sanitize


def test_recursive_sanitizer_redacts_secret_headers_and_data_uris() -> None:
    secret = "test-secret-sentinel"
    value = {
        "Authorization": f"Bearer {secret}",
        "nested": [secret, {"api_key": secret}],
        "uri": "data:image/png;base64,very-large-payload",
        "safe": "hello",
    }

    sanitized = sanitize(value, secrets=(secret,))

    assert sanitized["Authorization"] == "[REDACTED]"
    assert sanitized["nested"] == ["[REDACTED]", {"api_key": "[REDACTED]"}]
    assert sanitized["uri"] == "data:image/png;base64,[REDACTED]"
    assert sanitized["safe"] == "hello"


def test_redact_text_removes_bearer_and_explicit_secret() -> None:
    text = "Authorization: Bearer abc.def and token SECRET123"

    redacted = redact_text(text, secrets=("SECRET123",))

    assert "abc.def" not in redacted
    assert "SECRET123" not in redacted
    assert redacted.count("[REDACTED]") >= 2
