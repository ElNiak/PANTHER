import os
import tempfile
from unittest import mock
from panther.plugins.services.testers.panther_ivy.config_schema import AvailableTests


def test_load_tests_from_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a nested directory structure with test files
        os.makedirs(os.path.join(temp_dir, "protocol1"))
        os.makedirs(os.path.join(temp_dir, "protocol2"))
        test_file1 = os.path.join(temp_dir, "protocol1", "test1_test.ivy")
        test_file2 = os.path.join(temp_dir, "protocol2", "test2_test.ivy")
        with open(test_file1, "w") as f:
            f.write("test content")
        with open(test_file2, "w") as f:
            f.write("test content")

        # Call the function to test
        available_tests = AvailableTests.load_tests_from_directory(temp_dir)

        # Check if the tests are loaded correctly
        assert len(available_tests.tests) == 2
        assert available_tests.tests[0]["name"] == "test1_test.ivy"
        assert available_tests.tests[0]["type"] == "protocol1"
        assert available_tests.tests[1]["name"] == "test2_test.ivy"
        assert available_tests.tests[1]["type"] == "protocol2"


def test_load_tests_from_directory_no_tests():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Call the function to test
        available_tests = AvailableTests.load_tests_from_directory(temp_dir)

        # Check if no tests are loaded
        assert len(available_tests.tests) == 0


@mock.patch("os.walk")
def test_load_tests_from_directory_mocked(os_walk_mock):
    os_walk_mock.return_value = [
        ("/some/dir/protocol1", ("subdir",), ("test1_test.ivy",)),
        ("/some/dir/protocol2", ("subdir",), ("test2_test.ivy",)),
    ]

    available_tests = AvailableTests.load_tests_from_directory("/some/dir")

    assert len(available_tests.tests) == 2
    assert available_tests.tests[0]["name"] == "test1_test.ivy"
    assert available_tests.tests[0]["type"] == "protocol1"
    assert available_tests.tests[1]["name"] == "test2_test.ivy"
    assert available_tests.tests[1]["type"] == "protocol2"
