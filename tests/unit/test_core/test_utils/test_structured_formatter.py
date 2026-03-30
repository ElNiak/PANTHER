"""Tests for StructuredJsonFormatter."""

import json
import logging

import pytest

pytestmark = pytest.mark.unit

from panther.core.utils.log_context import log_context
from panther.core.utils.structured_formatter import StructuredJsonFormatter


@pytest.fixture
def formatter():
    return StructuredJsonFormatter()


@pytest.fixture
def make_record():
    """Create a log record with given parameters."""

    def _make(
        msg="test message",
        level=logging.INFO,
        name="test.logger",
        exc_info=None,
    ):
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname="test.py",
            lineno=42,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )
        return record

    return _make


class TestStructuredJsonFormatter:
    """Tests for StructuredJsonFormatter output."""

    def test_basic_format(self, formatter, make_record):
        record = make_record()
        line = formatter.format(record)
        data = json.loads(line)

        assert data["level"] == "INFO"
        assert data["level_num"] == 20
        assert data["message"] == "test message"
        assert data["source"] == "logging"
        assert data["lineno"] == 42
        assert "ts" in data

    def test_context_fields_included(self, formatter, make_record):
        with log_context(experiment_id="exp-1", test_id="test-1"):
            record = make_record()
            line = formatter.format(record)
            data = json.loads(line)

        assert data["experiment_id"] == "exp-1"
        assert data["test_id"] == "test-1"

    def test_null_values_omitted(self, formatter, make_record):
        record = make_record()
        line = formatter.format(record)
        data = json.loads(line)

        assert "experiment_id" not in data
        assert "test_id" not in data
        assert "service_id" not in data
        assert "error" not in data

    def test_error_info_included(self, formatter, make_record):
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = make_record(level=logging.ERROR, exc_info=exc_info)
        line = formatter.format(record)
        data = json.loads(line)

        assert "error" in data
        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "test error"
        assert "traceback" in data["error"]

    def test_feature_from_record(self, formatter, make_record):
        record = make_record()
        record._panther_feature = "quic_services"  # type: ignore[attr-defined]
        line = formatter.format(record)
        data = json.loads(line)

        assert data["feature"] == "quic_services"

    def test_valid_json_output(self, formatter, make_record):
        """Every formatted line should be valid JSON."""
        record = make_record(msg='special chars: {"key": 42} \n\ttab')
        line = formatter.format(record)
        data = json.loads(line)  # Should not raise
        assert data["message"] == 'special chars: {"key": 42} \n\ttab'

    def test_iso_timestamp(self, formatter, make_record):
        record = make_record()
        line = formatter.format(record)
        data = json.loads(line)

        # Should be ISO-8601 format with timezone
        ts = data["ts"]
        assert "T" in ts
        assert "+" in ts or "Z" in ts
