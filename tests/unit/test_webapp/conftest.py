"""Fixtures for webapp tests."""

import pytest


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory with mock experiment data."""
    # Create a fake experiment structure
    date_dir = tmp_path / "2026-01-15_10-00-00_test"
    exp_dir = date_dir / "0_test_experiment"
    exp_dir.mkdir(parents=True)

    # experiment.log
    (exp_dir / "experiment.log").write_text(
        "INFO: Experiment started\nINFO: Test passed\n"
    )

    # experiment_summary.json
    import json

    summary = {
        "experiment_id": "0_test_experiment",
        "status": "completed",
        "tests": {"total": 2, "passed": 1, "failed": 1},
    }
    (exp_dir / "experiment_summary.json").write_text(json.dumps(summary))

    # A test subdirectory
    test_dir = exp_dir / "test_basic"
    test_dir.mkdir()
    (test_dir / "test.log").write_text("Test log content")

    return tmp_path


@pytest.fixture
def sample_yaml():
    """Return a minimal valid PANTHER experiment YAML string."""
    return """\
logging:
  level: INFO
tests:
  - name: "Basic Test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
"""
