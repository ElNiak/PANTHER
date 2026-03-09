"""Tests for observer config enums and constraints."""

import pytest

from panther.config.core.models.observer import (
    BaseObserverConfig,
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    ReportFormat,
    StorageFormat,
    StorageObserverConfig,
)


class TestStorageFormatEnum:
    def test_valid_values(self):
        for val in ["json", "sqlite", "csv"]:
            assert StorageFormat(val).value == val

    def test_storage_config_accepts_string(self):
        sc = StorageObserverConfig(storage_format="sqlite")
        assert sc.storage_format == StorageFormat.SQLITE


class TestReportFormatEnum:
    def test_valid_values(self):
        for val in ["markdown", "html", "json"]:
            assert ReportFormat(val).value == val

    def test_experiment_config_accepts_string(self):
        ec = ExperimentObserverConfig(report_format="html")
        assert ec.report_format == ReportFormat.HTML


class TestObserverConstraints:
    def test_priority_negative(self):
        with pytest.raises(Exception):
            BaseObserverConfig(priority=-1)

    def test_priority_too_high(self):
        with pytest.raises(Exception):
            BaseObserverConfig(priority=1001)

    def test_backup_count_negative(self):
        with pytest.raises(Exception):
            LoggerObserverConfig(backup_count=-1)

    def test_buffer_size_zero(self):
        with pytest.raises(Exception):
            StorageObserverConfig(buffer_size=0)

    def test_flush_interval_zero(self):
        with pytest.raises(Exception):
            StorageObserverConfig(flush_interval=0)

    def test_batch_size_zero(self):
        with pytest.raises(Exception):
            StorageObserverConfig(batch_size=0)

    def test_publish_interval_zero(self):
        with pytest.raises(Exception):
            MetricsObserverConfig(publish_interval=0)
