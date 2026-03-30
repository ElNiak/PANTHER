"""Unit tests for StringRepresentationMixin."""

import pytest

from panther.core.utils.string_representation_mixin import StringRepresentationMixin


class MockProtocol:
    """Mock protocol object for testing."""

    def __init__(self, name):
        self.name = name


class SimpleTestClass(StringRepresentationMixin):
    """Simple test class using the mixin."""

    pass


class ServiceTestClass(StringRepresentationMixin):
    """Test class simulating a service manager."""

    def __init__(self, protocol, service_type, implementation_name):
        self.protocol = protocol
        self.service_type = service_type
        self.implementation_name = implementation_name


class EnvironmentTestClass(StringRepresentationMixin):
    """Test class simulating an environment."""

    def __init__(self, env_type, env_sub_type):
        self.env_type = env_type
        self.env_sub_type = env_sub_type


class CustomAttributesTestClass(StringRepresentationMixin):
    """Test class with custom _get_key_attributes implementation."""

    def __init__(self, custom_field):
        self.custom_field = custom_field
        self.protocol = MockProtocol("test_protocol")

    def _get_key_attributes(self):
        attrs = super()._get_key_attributes()
        attrs["custom"] = self.custom_field
        return attrs


class TestStringRepresentationMixin:
    """Test cases for StringRepresentationMixin."""

    def test_simple_class_no_attributes(self):
        """Test string representation of class with no relevant attributes."""
        obj = SimpleTestClass()
        assert str(obj) == "SimpleTestClass()"
        assert repr(obj) == "SimpleTestClass()"

    def test_service_class_with_protocol(self):
        """Test string representation of service-like class."""
        protocol = MockProtocol("quic")
        obj = ServiceTestClass(protocol, "testers", "panther_ivy")

        expected = "ServiceTestClass(protocol=quic, impl=panther_ivy, type=testers)"
        assert str(obj) == expected
        assert repr(obj) == expected

    def test_service_class_no_protocol(self):
        """Test service class with None protocol."""
        obj = ServiceTestClass(None, "testers", "panther_ivy")

        expected = "ServiceTestClass(protocol=none, impl=panther_ivy, type=testers)"
        assert str(obj) == expected

    def test_environment_class(self):
        """Test string representation of environment-like class."""
        obj = EnvironmentTestClass("network", "docker_compose")

        expected = "EnvironmentTestClass(type=network, subtype=docker_compose)"
        assert str(obj) == expected
        assert repr(obj) == expected

    def test_custom_attributes(self):
        """Test class with custom _get_key_attributes implementation."""
        obj = CustomAttributesTestClass("my_value")

        # Should include both base attributes and custom ones
        result = str(obj)
        assert "protocol=test_protocol" in result
        assert "custom=my_value" in result
        assert "CustomAttributesTestClass" in result

    def test_get_verbose_string(self):
        """Test verbose string output."""
        protocol = MockProtocol("quic")
        obj = ServiceTestClass(protocol, "testers", "panther_ivy")
        obj.service_config_to_test = {"test": "config"}
        obj.output_dir = "/tmp/output"

        verbose = obj.get_verbose_string()

        # Should include all attributes
        assert "ServiceTestClass" in verbose
        assert "protocol=quic" in verbose
        assert "service_config_to_test=<dict[1]>" in verbose
        assert "output_dir=/tmp/output" in verbose
        # Should be multi-line
        assert "\n" in verbose

    def test_get_verbose_string_with_lists(self):
        """Test verbose string with list attributes."""
        obj = SimpleTestClass()
        obj.services_managers = ["manager1", "manager2", "manager3"]

        verbose = obj.get_verbose_string()
        assert "services_managers=<list[3]>" in verbose

    def test_get_verbose_string_with_complex_objects(self):
        """Test verbose string with complex object attributes."""
        obj = SimpleTestClass()
        obj.event_manager = MockProtocol("event_mgr")  # Complex object

        verbose = obj.get_verbose_string()
        assert "event_manager=<MockProtocol>" in verbose

    def test_inheritance_multiple_classes(self):
        """Test that mixin works correctly with multiple inheritance."""

        class MultipleInheritanceTest(ServiceTestClass, EnvironmentTestClass):
            def __init__(self):
                # Service attributes take precedence
                self.protocol = MockProtocol("http")
                self.service_type = "iut"
                self.implementation_name = "test_impl"
                # These should be ignored due to attribute precedence
                self.env_type = "execution"
                self.env_sub_type = "gperf"

        obj = MultipleInheritanceTest()
        result = str(obj)

        # Should show service attributes (first in MRO)
        assert "protocol=http" in result
        assert "impl=test_impl" in result
        # env_type overwrites service_type since both map to "type" key
        assert "type=execution" in result
        # env_sub_type is also present since it maps to "subtype"
        assert "subtype=gperf" in result

    def test_none_protocol_object(self):
        """Test handling of protocol object without name attribute."""

        class BadProtocol:
            pass

        obj = ServiceTestClass(BadProtocol(), "testers", "test")
        assert "protocol=unknown" in str(obj)
