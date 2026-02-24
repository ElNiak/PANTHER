import os
import subprocess

env = os.environ.copy()
env["COVERAGE_PROCESS_START"] = ".coveragerc"


def test_cli_create_experiment_docker_compose_quic():
    result = subprocess.run(
        [
            "panther",
            "run",
            "--config",
            "tests/tests_ressources/quic_e2e_config_docker_compose.yaml",
            "--experiment-name",
            "test_experiment_quic_e2e_config_docker_compose",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    # Should test in the logs -> check with and without the flag
    # assert "All experiment tests completed." in result.stdout


def test_cli_create_experiment_shadow_ns_quic():
    result = subprocess.run(
        [
            "panther",
            "run",
            "--config",
            "tests/tests_ressources/quic_e2e_config_shadow_ns.yaml",
            "--experiment-name",
            "test_experiment_quic_e2e_config_shadow_ns",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0


def test_cli_create_experiment_shadow_ns_quic_invalid_impl():
    result = subprocess.run(
        [
            "panther",
            "run",
            "--config",
            "tests/tests_ressources/quic_e2e_config_shadow_ns_invalid_impl.yaml",
            "--experiment-name",
            "test_experiment_quic_e2e_config_shadow_ns_invalid_impl",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0

    # assert "All experiment tests completed." in result.stdout


# def test_cli_create_experiment_shadow_ns_quic_determinism():
#     result = subprocess.run(
#         ["panther","--experiment-name", "test_experiment_quic_e2e_config_shadow_ns",
#          "--experiment-config", "tests/e2e/quic_e2e_config_shadow_ns.yaml",],
#         capture_output=True,
#         text=True
#     )
#     assert result.returncode == 0
#     assert "All experiment tests completed." in result.stdout


def test_cli_create_experiment_not_existing():
    result = subprocess.run(
        [
            "panther",
            "run",
            "--config",
            "tests/tests_ressources/e2e_config_not_existing.yaml",
            "--experiment-name",
            "test_experiment_not_existing",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    # assert "Experiment created" in result.stdout


def test_cli_create_experiment_invalid():
    result = subprocess.run(
        [
            "panther",
            "run",
            "--config",
            "tests/tests_ressources/e2e_config_invalid.yaml",
            "--experiment-name",
            "test_experiment_invalid",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    # assert "Experiment created" in result.stdout


def test_cli_invalid_command():
    result = subprocess.run(
        ["panther", "invalid-command"], capture_output=True, text=True, env=env
    )
    assert result.returncode != 0
    # assert "unrecognized arguments" in result.stderr
