"""Tests for the _requires_emitter decorator in service_event_mixin."""

from unittest.mock import patch

import pytest

import panther.plugins.services.service_event_mixin as _sem_module
from panther.plugins.services.service_event_mixin import (
    ServiceManagerEventMixin,
    _requires_emitter,
)

pytestmark = pytest.mark.unit

# The module-level logger has propagate=False and an ERROR-level StreamHandler,
# so pytest caplog cannot capture its records.  We patch _logger.warning directly.


# ---------------------------------------------------------------------------
# Minimal stub classes
# ---------------------------------------------------------------------------


class _Stub(ServiceManagerEventMixin):
    """Minimal concrete subclass of ServiceManagerEventMixin for testing."""

    def __init__(self, emitter=None):
        self.event_emitter = emitter
        self.name = "stub_service"
        self.service_type = "iut"
        self.implementation_name = "stub"

    @_requires_emitter
    def do_something(self, value=None):
        """A decorated method that records calls."""
        self.called = True
        self.call_value = value
        return "result"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRequiresEmitter:
    """Test suite for the _requires_emitter decorator."""

    # --- 1. Skips cleanly when event_emitter is None ----------------------

    def test_skips_when_emitter_is_none(self):
        """Method returns None and body does not execute when emitter is None."""
        stub = _Stub(emitter=None)

        result = stub.do_something(value=42)

        assert result is None, "Expected None return when emitter is absent"
        assert not hasattr(stub, "called"), "Method body must not have been executed"

    # --- 2. Warning logged exactly once (circuit-breaker _emitter_warned) -

    def test_warning_logged_once(self):
        """A single warning is emitted for the first missing-emitter call.

        Subsequent calls are silent (circuit-breaker via _emitter_warned).
        The module logger has propagate=False, so we patch _logger.warning
        directly instead of using caplog.
        """
        stub = _Stub(emitter=None)

        with patch.object(_sem_module._logger, "warning") as mock_warn:
            stub.do_something()
            stub.do_something()
            stub.do_something()

        assert (
            mock_warn.call_count == 1
        ), f"Expected exactly 1 warning call, got {mock_warn.call_count}"
        # Verify the message mentions dropped events
        call_args = mock_warn.call_args
        assert "events will be dropped" in call_args[0][0]

    def test_emitter_warned_flag_set_after_first_call(self):
        """_emitter_warned attribute is set to True after the first skipped call."""
        stub = _Stub(emitter=None)

        assert not getattr(stub, "_emitter_warned", False)
        stub.do_something()
        assert stub._emitter_warned is True

    # --- 3. Executes normally when emitter is set -------------------------

    def test_executes_when_emitter_present(self):
        """Method body runs and returns its value when emitter is set."""
        emitter = object()  # any truthy object
        stub = _Stub(emitter=emitter)

        result = stub.do_something(value=99)

        assert result == "result", "Expected the decorated method's return value"
        assert stub.called is True
        assert stub.call_value == 99

    def test_no_warning_when_emitter_present(self):
        """No warning is logged when the emitter is properly set."""
        emitter = object()
        stub = _Stub(emitter=emitter)

        with patch.object(_sem_module._logger, "warning") as mock_warn:
            stub.do_something()

        mock_warn.assert_not_called()

    # --- 4. Edge cases: falsy emitter values (0, "") ----------------------

    @pytest.mark.parametrize("falsy_emitter", [0, "", [], {}, False])
    def test_skips_for_falsy_emitter(self, falsy_emitter):
        """Method skips for any falsy event_emitter value, not just None."""
        stub = _Stub(emitter=falsy_emitter)

        result = stub.do_something(value="test")

        assert (
            result is None
        ), f"Expected None return for falsy emitter {falsy_emitter!r}"
        assert not hasattr(stub, "called"), "Method body must not have executed"

    def test_no_attribute_event_emitter_skips(self):
        """Method skips if the instance has no event_emitter attribute at all."""

        class _NoEmitterStub(ServiceManagerEventMixin):
            name = "no_emitter"
            service_type = "iut"
            implementation_name = "stub"

            @_requires_emitter
            def do_something(self):
                self.called = True
                return "result"

        stub = _NoEmitterStub()

        result = stub.do_something()

        assert result is None
        assert not hasattr(stub, "called")

    def test_warning_circuit_breaker_per_instance(self):
        """The _emitter_warned flag is per-instance; two instances each warn once."""
        stub_a = _Stub(emitter=None)
        stub_b = _Stub(emitter=None)

        with patch.object(_sem_module._logger, "warning") as mock_warn:
            stub_a.do_something()
            stub_a.do_something()  # should be suppressed
            stub_b.do_something()
            stub_b.do_something()  # should be suppressed

        assert (
            mock_warn.call_count == 2
        ), f"Expected 2 warnings (one per instance), got {mock_warn.call_count}"
