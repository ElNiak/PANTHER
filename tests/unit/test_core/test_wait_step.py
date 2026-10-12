"""The wait step's overrun warning.

The wait step's ceiling is the sum of its sleeps, so a machine stall or host sleep
lengthens it by its whole length. When the measured duration passes the ceiling by
more than ``steps.wait_overrun_warning`` seconds, the step logs one warning.

These tests drive the real ``TestExecutor.execute_steps`` with a fake clock: each
sleep advances it, and a fake environment adds a one-off stall at its first
early-termination check.
"""

import logging
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from panther.config.core.models.experiment import StepsConfig
from panther.core.test_cases.execution import test_executor as executor_mod

pytestmark = [pytest.mark.unit]


class RecordList(logging.Handler):
    """A handler that keeps every record it receives."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class FakeClock:
    """A clock that only moves when the code under test sleeps or a stall is added."""

    def __init__(self) -> None:
        self.now = 1000.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class StallingEnvironment:
    """An environment whose first early-termination check stalls the clock."""

    def __init__(self, clock: FakeClock, stall: float, terminate: bool) -> None:
        self.clock = clock
        self.stall = stall
        self.terminate = terminate
        self.checks = 0

    def should_terminate_early(self) -> bool:
        self.checks += 1
        if self.checks == 1:
            self.clock.now += self.stall
        return self.terminate


def run_wait_step(monkeypatch, steps, stall, terminate=False):
    """Run the wait step under a fake clock and return the warnings it logged."""
    clock = FakeClock()
    monkeypatch.setattr(
        executor_mod, "time", SimpleNamespace(time=clock.time, sleep=clock.sleep)
    )
    # A standalone logger: PANTHER's logging setup turns off propagation on
    # loggers from logging.getLogger, so caplog's root handler would see nothing.
    logger = logging.Logger("test_wait_step", logging.DEBUG)
    handler = RecordList()
    logger.addHandler(handler)
    test_case = SimpleNamespace(
        logger=logger,
        test_config=SimpleNamespace(steps=steps),
        emitter_registry=None,
        environment_plugin_manager=[StallingEnvironment(clock, stall, terminate)],
        test_name="wait-step-test",
    )
    executor_mod.TestExecutor(test_case).execute_steps()
    return [r for r in handler.records if r.levelno == logging.WARNING]


def test_an_overrun_past_the_default_margin_warns(monkeypatch):
    warnings = run_wait_step(monkeypatch, StepsConfig(wait=5), stall=11.0)

    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "16.00s" in message
    assert "5s ceiling" in message
    assert "stall or host sleep" in message


@pytest.mark.parametrize("stall", [9.0, 10.0])
def test_an_overrun_within_the_default_margin_does_not_warn(monkeypatch, stall):
    warnings = run_wait_step(monkeypatch, StepsConfig(wait=5), stall=stall)

    assert warnings == []


def test_an_early_terminated_step_that_overran_warns(monkeypatch):
    # The first 0.5 s slice, then a 16 s stall, then the environment ends the wait:
    # 16.5 s measured against a 5 s ceiling.
    warnings = run_wait_step(
        monkeypatch, StepsConfig(wait=5), stall=16.0, terminate=True
    )

    assert len(warnings) == 1
    assert "16.50s" in warnings[0].getMessage()


def test_a_custom_margin_is_read_from_the_steps_config(monkeypatch):
    steps = StepsConfig(wait=5, wait_overrun_warning=3)

    assert len(run_wait_step(monkeypatch, steps, stall=4.0)) == 1


def test_an_overrun_within_a_custom_margin_does_not_warn(monkeypatch):
    steps = StepsConfig(wait=5, wait_overrun_warning=3)

    assert run_wait_step(monkeypatch, steps, stall=2.0) == []


def test_the_setting_defaults_to_ten_seconds_within_bounds():
    assert StepsConfig().wait_overrun_warning == 10
    with pytest.raises(ValidationError):
        StepsConfig(wait_overrun_warning=0)
    with pytest.raises(ValidationError):
        StepsConfig(wait_overrun_warning=86401)
    schema = StepsConfig.model_json_schema()["properties"]["wait_overrun_warning"]
    assert schema["unit"] == "seconds"
