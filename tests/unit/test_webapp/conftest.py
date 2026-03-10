"""Fixtures for webapp tests."""

import json

import pytest


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory with mock experiment data.

    Mimics the actual output structure: outputs/<timestamp>/
    Each directory under outputs/ is an experiment (single-level).
    """
    # Experiment directory directly under tmp_path (single-level)
    exp_dir = tmp_path / "2026-01-15_10-00-00"
    exp_dir.mkdir()

    # experiment.log
    (exp_dir / "experiment.log").write_text(
        "INFO: Experiment started\nINFO: Test passed\n"
    )

    # experiment_summary.json
    summary = {
        "experiment_id": "2026-01-15_10-00-00",
        "status": "completed",
        "tests": {
            "total": 2,
            "passed": 1,
            "failed": 1,
            "results": [
                {
                    "name": "0_test_basic",
                    "status": "passed",
                    "duration": 10.5,
                    "start_time": "2026-01-15T10:00:00",
                    "end_time": "2026-01-15T10:00:10",
                },
                {
                    "name": "1_test_advanced",
                    "status": "failed",
                    "duration": 25.0,
                    "start_time": "2026-01-15T10:00:11",
                    "end_time": "2026-01-15T10:00:36",
                    "error_message": "Tester failed",
                },
            ],
        },
    }
    (exp_dir / "experiment_summary.json").write_text(json.dumps(summary))

    # EXPERIMENT_REPORT.md
    (exp_dir / "EXPERIMENT_REPORT.md").write_text("# Experiment Report\nAll done.\n")

    # Test subdirectory with test.log and events
    test_dir = exp_dir / "0_test_basic"
    test_dir.mkdir()
    (test_dir / "test.log").write_text("Test log content")
    (test_dir / "test_config.yaml").write_text("name: test_basic\n")
    (test_dir / "events.jsonl").write_text(
        '{"event_type": "test.started", "timestamp": "2026-01-15T10:00:00"}\n'
        '{"event_type": "test.completed", "timestamp": "2026-01-15T10:00:10"}\n'
    )

    # Logs directory with service subdirectories
    logs_dir = test_dir / "logs"
    logs_dir.mkdir()
    svc_dir = logs_dir / "picoquic_server"
    svc_dir.mkdir()
    compile_dir = svc_dir / "compile"
    compile_dir.mkdir()
    (compile_dir / "stdout.log").write_text("Compiling...\nDone.")
    (compile_dir / "stderr.log").write_text("")

    # Analysis directory
    analysis_dir = test_dir / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "analysis_results.json").write_text(
        json.dumps({"results": {"passed": True, "analysis_summary": "All good"}})
    )

    # Second test directory (failed)
    test_dir2 = exp_dir / "1_test_advanced"
    test_dir2.mkdir()
    (test_dir2 / "test.log").write_text("Test advanced log")
    (test_dir2 / "test_config.yaml").write_text("name: test_advanced\n")

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
      client:
        implementation:
          name: ivy
          type: testers
        protocol:
          name: quic
          version: rfc9000
          role: client
          target: server
"""
