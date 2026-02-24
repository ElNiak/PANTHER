import pytest

from panther.plugins.services.service_manager_mixin import (
    RUN_CMD_SCHEMA,
    validate_cmd,
    validate_structure,
)

pytestmark = [pytest.mark.unit, pytest.mark.command_generation]


# Test data factories to eliminate duplication
class CommandTestDataFactory:
    @staticmethod
    def create_base_command_structure():
        """Create the common command structure used in tests."""
        return {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "post_run_cmds": [],
        }

    @staticmethod
    def create_valid_run_cmd():
        """Create a valid run command configuration."""
        return {
            "working_dir": "/path/to/dir",
            "command_binary": "binary",
            "command_args": "args",
            "timeout": 60,
            "environment": {},
        }

    @staticmethod
    def create_valid_command():
        """Create a complete valid command structure."""
        command = CommandTestDataFactory.create_base_command_structure()
        command["run_cmd"] = CommandTestDataFactory.create_valid_run_cmd()
        return command

    @staticmethod
    def create_invalid_command(invalid_field="timeout", invalid_value="sixty"):
        """Create an invalid command structure for testing error cases."""
        command = CommandTestDataFactory.create_valid_command()
        command["run_cmd"][invalid_field] = invalid_value
        return command


@pytest.fixture
def valid_command_data():
    """Fixture providing valid command data."""
    return CommandTestDataFactory.create_valid_command()


@pytest.fixture
def invalid_command_data():
    """Fixture providing invalid command data."""
    return CommandTestDataFactory.create_invalid_command()


def test_validate_cmd_decorator_valid_command(valid_command_data):
    """Test that validate_cmd decorator accepts valid command structures."""

    @validate_cmd
    def valid_command():
        return valid_command_data

    try:
        valid_command()
    except Exception as e:
        pytest.fail(f"validate_cmd raised an exception unexpectedly: {e}")


def test_validate_cmd_decorator_invalid_command(invalid_command_data):
    """Test that validate_cmd decorator rejects invalid command structures."""

    @validate_cmd
    def invalid_command():
        return invalid_command_data

    with pytest.raises(TypeError):
        invalid_command()


def test_validate_structure_valid_data(valid_command_data):
    """Test that validate_structure accepts valid data structures."""
    try:
        validate_structure(valid_command_data, RUN_CMD_SCHEMA)
    except Exception as e:
        pytest.fail(f"validate_structure raised an exception unexpectedly: {e}")


def test_validate_structure_invalid_data(invalid_command_data):
    """Test that validate_structure rejects invalid data structures."""
    with pytest.raises(TypeError):
        validate_structure(invalid_command_data, RUN_CMD_SCHEMA)


@pytest.mark.parametrize(
    "invalid_field,invalid_value",
    [
        ("timeout", "sixty"),
        ("working_dir", 123),
        ("command_binary", None),
        (
            "command_args",
            123,
        ),  # command_args accepts list or string, so use invalid type
    ],
)
def test_validate_structure_various_invalid_fields(invalid_field, invalid_value):
    """Test validation with different types of invalid fields."""
    invalid_data = CommandTestDataFactory.create_invalid_command(
        invalid_field, invalid_value
    )
    with pytest.raises(TypeError):
        validate_structure(invalid_data, RUN_CMD_SCHEMA)
