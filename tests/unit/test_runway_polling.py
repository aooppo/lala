from types import SimpleNamespace

import pytest

from lala_workflow.domain import TaskStatus
from lala_workflow.providers.runway import RunwayImageProvider


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class FakeTasks:
    def __init__(self, states) -> None:
        self.states = list(states)
        self.calls = 0

    def retrieve(self, task_id: str, **kwargs):
        index = min(self.calls, len(self.states) - 1)
        self.calls += 1
        return self.states[index]


class ErrorThenSuccessTasks:
    def __init__(self, errors: int) -> None:
        self.errors = errors
        self.calls = 0

    def retrieve(self, task_id: str, **kwargs):
        self.calls += 1
        if self.calls <= self.errors:
            raise OSError("temporary poll failure")
        return SimpleNamespace(status="SUCCEEDED", output=["https://example.test/output.png"])


def make_provider(runway_capabilities, states, clock: FakeClock) -> RunwayImageProvider:
    client = SimpleNamespace(tasks=FakeTasks(states))
    return RunwayImageProvider(
        runway_capabilities,
        api_key="test-key",
        client=client,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def test_wait_polls_at_documented_interval_until_success(runway_capabilities) -> None:
    clock = FakeClock()
    provider = make_provider(
        runway_capabilities,
        [
            SimpleNamespace(status="PENDING"),
            SimpleNamespace(status="RUNNING", progress=0.5),
            SimpleNamespace(status="SUCCEEDED", output=["https://example.test/output.png"]),
        ],
        clock,
    )

    result = provider.wait("task-1", timeout_seconds=20)

    assert result.status is TaskStatus.SUCCEEDED
    assert result.output_urls == ("https://example.test/output.png",)
    assert clock.sleeps == [5.0, 5.0]


@pytest.mark.parametrize(
    ("state", "expected"),
    [("FAILED", TaskStatus.FAILED), ("CANCELLED", TaskStatus.CANCELLED)],
)
def test_wait_normalizes_terminal_failure_states(runway_capabilities, state, expected) -> None:
    clock = FakeClock()
    details = SimpleNamespace(status=state, failure="nope", failure_code="provider_code")

    result = make_provider(runway_capabilities, [details], clock).wait("task-1", 20)

    assert result.status is expected
    assert result.error_code == "provider_code"


def test_wait_terminates_at_timeout(runway_capabilities) -> None:
    clock = FakeClock()
    provider = make_provider(
        runway_capabilities,
        [SimpleNamespace(status="PENDING")],
        clock,
    )

    result = provider.wait("task-1", timeout_seconds=10)

    assert result.status is TaskStatus.TIMED_OUT
    assert clock.value == 10
    assert len(clock.sleeps) == 2


def test_poll_read_retries_are_bounded_without_resubmission(runway_capabilities) -> None:
    clock = FakeClock()
    tasks = ErrorThenSuccessTasks(errors=2)
    provider = RunwayImageProvider(
        runway_capabilities,
        api_key="test-key",
        client=SimpleNamespace(tasks=tasks),
        max_poll_retries=2,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    result = provider.wait("task-1", timeout_seconds=20)

    assert result.status is TaskStatus.SUCCEEDED
    assert tasks.calls == 3
    assert clock.sleeps == [5.0, 5.0]


def test_poll_read_stops_after_retry_limit(runway_capabilities) -> None:
    clock = FakeClock()
    tasks = ErrorThenSuccessTasks(errors=99)
    provider = RunwayImageProvider(
        runway_capabilities,
        api_key="test-key",
        client=SimpleNamespace(tasks=tasks),
        max_poll_retries=2,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    result = provider.wait("task-1", timeout_seconds=30)

    assert result.status is TaskStatus.FAILED
    assert result.error_code == "poll_error"
    assert tasks.calls == 3
