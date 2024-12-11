import subprocess

def test_cli_create_experiment():
    result = subprocess.run(
        ["panther_cli", "create-experiment", "--name", "test_experiment"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Experiment created" in result.stdout

def test_cli_invalid_command():
    result = subprocess.run(
        ["panther", "invalid-command"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert "Unknown command" in result.stderr
