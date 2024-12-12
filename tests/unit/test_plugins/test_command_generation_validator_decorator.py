import pytest
from panther.plugins.services.services_interface import (
    RUN_CMD_SCHEMA,
    validate_cmd,
    validate_structure,
)


def test_validate_cmd_decorator_valid_command():
    @validate_cmd
    def valid_command():
        return {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmd": {
                "working_dir": "/path/to/dir",
                "command_binary": "binary",
                "command_args": "args",
                "timeout": 60,
                "command_env": {},
            },
            "post_run_cmds": [],
        }

    try:
        valid_command()
    except Exception as e:
        pytest.fail(f"validate_cmd raised an exception unexpectedly: {e}")


def test_validate_cmd_decorator_invalid_command():
    @validate_cmd
    def invalid_command():
        return {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmd": {
                "working_dir": "/path/to/dir",
                "command_binary": "binary",
                "command_args": "args",
                "timeout": "sixty",  # Invalid type
                "command_env": {},
            },
            "post_run_cmds": [],
        }

    with pytest.raises(TypeError):
        invalid_command()


def test_validate_structure_valid_data():
    data = {
        "pre_compile_cmds": [],
        "compile_cmds": [],
        "post_compile_cmds": [],
        "pre_run_cmds": [],
        "run_cmd": {
            "working_dir": "/path/to/dir",
            "command_binary": "binary",
            "command_args": "args",
            "timeout": 60,
            "command_env": {},
        },
        "post_run_cmds": [],
    }
    try:
        validate_structure(data, RUN_CMD_SCHEMA)
    except Exception as e:
        pytest.fail(f"validate_structure raised an exception unexpectedly: {e}")


def test_validate_structure_invalid_data():
    data = {
        "pre_compile_cmds": [],
        "compile_cmds": [],
        "post_compile_cmds": [],
        "pre_run_cmds": [],
        "run_cmd": {
            "working_dir": "/path/to/dir",
            "command_binary": "binary",
            "command_args": "args",
            "timeout": "sixty",  # Invalid type
            "command_env": {},
        },
        "post_run_cmds": [],
    }
    with pytest.raises(TypeError):
        validate_structure(data, RUN_CMD_SCHEMA)
