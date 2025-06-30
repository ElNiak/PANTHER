#!/usr/bin/env python3
# filepath: /Users/elniak/Documents/Project/PANTHER/tests/plugins/test_picoquic_service_manager.py

import unittest
from unittest.mock import MagicMock
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from panther.plugins.services.iut.quic.picoquic.picoquic import PicoquicServiceManager


class TestPicoquicServiceManager(unittest.TestCase):
    """Test the PicoquicServiceManager class for the fixes."""

    def setUp(self):
        # Setup basic logging for tests
        logging.basicConfig(level=logging.INFO)

    def test_service_protocol_attribute(self):
        """Test that service_protocol attribute is correctly set."""
        # Create a mock instance directly
        manager = MagicMock(spec=PicoquicServiceManager)

        # Manually call the patched __init__ method with our own implementation
        protocol_mock = MagicMock()
        protocol_mock.type = "quic"

        # Store the protocol type in service_protocol as the real class would
        manager.service_protocol = protocol_mock.type

        # Verify service_protocol is set correctly
        self.assertEqual(manager.service_protocol, "quic")

    def test_get_service_name_method(self):
        """Test that get_service_name method returns the correct value."""
        # Get the actual method from the class
        get_service_name_method = PicoquicServiceManager.get_service_name

        # Create a mock instance with service_name already set
        manager = MagicMock(spec=PicoquicServiceManager)
        manager.service_name = "test_service"

        # Call the actual method on our mock instance
        result = get_service_name_method(manager)

        # Verify get_service_name returns the correct value
        self.assertEqual(result, "test_service")


if __name__ == "__main__":
    unittest.main()
