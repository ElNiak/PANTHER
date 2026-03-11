"""Tests for panther.core.utils.format_utils."""

import pytest

from panther.core.utils.format_utils import compute_duration, format_json


class TestFormatJson:
    def test_dict_input(self):
        result = format_json({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_non_serializable_fallback(self):
        obj = object()
        result = format_json(obj)
        assert isinstance(result, str)

    def test_nested_data(self):
        data = {"a": [1, 2, {"b": 3}]}
        result = format_json(data)
        assert '"a"' in result
        assert "3" in result


class TestComputeDuration:
    def test_subsecond(self):
        assert compute_duration("2024-01-01T00:00:00", "2024-01-01T00:00:00") == "<1s"

    def test_seconds(self):
        result = compute_duration("2024-01-01T00:00:00", "2024-01-01T00:00:30")
        assert result == "30s"

    def test_minutes(self):
        result = compute_duration("2024-01-01T00:00:00", "2024-01-01T00:05:00")
        assert result == "5.0m"

    def test_hours(self):
        result = compute_duration("2024-01-01T00:00:00", "2024-01-01T02:00:00")
        assert result == "2.0h"

    def test_parse_failure(self):
        assert compute_duration("not-a-date", "also-not") == ""

    def test_absolute_difference(self):
        result = compute_duration("2024-01-01T00:01:00", "2024-01-01T00:00:00")
        assert result == "1.0m"
