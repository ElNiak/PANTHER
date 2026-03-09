"""Tests for field partitioning utility."""

import pytest
from pydantic import BaseModel, ConfigDict, Field


class SampleModel(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str = Field(...)
    type: str = Field(default="iut")
    version: str = Field(default="")


class TestPartitionFields:
    def test_all_declared(self):
        from panther.config.core.utils.field_partition import partition_fields

        data = {"name": "picoquic", "type": "iut", "version": "1.0"}
        declared, extra = partition_fields(data, SampleModel)
        assert declared == {"name": "picoquic", "type": "iut", "version": "1.0"}
        assert extra == {}

    def test_with_extras(self):
        from panther.config.core.utils.field_partition import partition_fields

        data = {
            "name": "picoquic",
            "type": "iut",
            "build_mode": "rel-lto",
            "test": "quic_test",
        }
        declared, extra = partition_fields(data, SampleModel)
        assert declared == {"name": "picoquic", "type": "iut"}
        assert extra == {"build_mode": "rel-lto", "test": "quic_test"}

    def test_empty_data(self):
        from panther.config.core.utils.field_partition import partition_fields

        declared, extra = partition_fields({}, SampleModel)
        assert declared == {}
        assert extra == {}

    def test_all_extra(self):
        from panther.config.core.utils.field_partition import partition_fields

        data = {"custom_a": 1, "custom_b": 2}
        declared, extra = partition_fields(data, SampleModel)
        assert declared == {}
        assert extra == {"custom_a": 1, "custom_b": 2}

    def test_with_real_implementation_config(self):
        """Test with the actual ImplementationConfig to verify field detection."""
        from panther.config.core.models.service import ImplementationConfig
        from panther.config.core.utils.field_partition import partition_fields

        data = {
            "name": "panther_ivy",
            "type": "testers",
            "version": "1.0",
            "version_config": {"commit": "abc123"},
            "shadow_compatible": False,
            "gperf_compatible": False,
            # These are plugin-specific:
            "test": "quic_client_test_max",
            "build_mode": "rel-lto",
            "iterations_per_test": 10,
        }
        declared, extra = partition_fields(data, ImplementationConfig)

        # All 6 declared fields should be in declared
        assert "name" in declared
        assert "type" in declared
        assert "version" in declared
        assert "version_config" in declared
        assert "shadow_compatible" in declared
        assert "gperf_compatible" in declared

        # Plugin-specific fields should be in extra
        assert "test" in extra
        assert "build_mode" in extra
        assert "iterations_per_test" in extra
