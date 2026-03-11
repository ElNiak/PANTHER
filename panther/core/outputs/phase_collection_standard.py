"""Centralized phase collection pattern definitions for all PANTHER services.

Pattern tuples can be either 2-tuples ``(type, pattern)`` or 3-tuples
``(type, pattern, required)``.  When a 3-tuple is used and ``required``
is ``True``, the pattern counts toward the output-completeness metric
reported by ``ServiceHealthAnalyzer``.  2-tuples default to optional.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class ExecutionPhase(Enum):
    """Standard execution phases for all services."""

    PRE_COMPILE = "pre-compile"
    COMPILE = "compile"
    POST_COMPILE = "post-compile"
    PRE_RUN = "pre-run"
    RUNTIME = "runtime"
    POST_RUN = "post-run"
    TEST = "test"


class PhaseCollectionStandard:
    """Centralized definition of all phase collection patterns."""

    # Base patterns all services should have.
    # 3-tuples: (type, pattern, required) — required patterns count toward completeness.
    # 2-tuples: (type, pattern) — optional, backwards-compatible.
    BASE_PHASE_PATTERNS = [
        ("pre_compile_stdout", "pre-compile/stdout.log"),
        ("pre_compile_stderr", "pre-compile/stderr.log"),
        ("compile_stdout", "compile/stdout.log", True),
        ("compile_stderr", "compile/stderr.log", True),
        ("post_compile_stdout", "post-compile/stdout.log"),
        ("post_compile_stderr", "post-compile/stderr.log"),
        ("pre_run_stdout", "pre-run/stdout.log"),
        ("pre_run_stderr", "pre-run/stderr.log"),
        ("runtime_stdout", "runtime/stdout.log", True),
        ("runtime_stderr", "runtime/stderr.log", True),
        ("post_run_stdout", "post-run/stdout.log"),
        ("post_run_stderr", "post-run/stderr.log"),
        ("test_stdout", "test/stdout.log", True),
        ("test_stderr", "test/stderr.log", True),
        # Compilation status
        ("compilation_status", "compile/compilation_status.txt"),
        # Legacy compatibility
        ("compilation_status_legacy", "compilation_status.txt"),
        ("stdout", "stdout.log"),
        ("stderr", "stderr.log"),
        ("logs", "{service_name}.log"),
    ]

    # Protocol-specific patterns
    PROTOCOL_PATTERNS = {
        "quic": [
            ("qlog", "artifacts/*.qlog"),
            ("sslkeylog", "artifacts/sslkeylogfile.txt"),
            ("keys", "artifacts/*keys.log"),
            ("secrets", "artifacts/*secrets.log"),
            ("congestion", "artifacts/*congestion*.log"),
            ("connection_stats", "artifacts/connection_stats.json"),
            ("pcap", "artifacts/{service_name}.pcap"),
            ("http3_logs", "artifacts/*http3*.log"),
        ],
        "tcp": [
            ("tcpdump", "artifacts/*.pcap"),
            ("netstat", "artifacts/*netstat*.log"),
            ("ss_output", "artifacts/ss_*.log"),
            ("tcpdump_capture", "artifacts/tcp_capture.pcap"),
        ],
        "http": [
            ("access_log", "artifacts/access.log"),
            ("error_log", "artifacts/error.log"),
            ("har", "artifacts/*.har"),
            ("http_headers", "artifacts/headers_*.log"),
            ("response_time", "artifacts/response_time.log"),
        ],
        "minip": [
            ("ping_results", "artifacts/ping_results.log"),
            ("network_trace", "artifacts/network_trace.log"),
            ("ping_stats", "artifacts/ping_statistics.json"),
        ],
    }

    # Service type patterns
    SERVICE_TYPE_PATTERNS = {
        "tester": [
            ("compilation_status", "compile/compilation_status.txt"),
            ("test_results", "test/test_results.json"),
            ("test_summary", "test/test_summary.log"),
            ("analysis_report", "artifacts/analysis_report.json"),
            ("verification_log", "test/verification.log"),
            ("test_execution", "test/execution.log"),
        ],
        "iut": [
            ("performance_metrics", "artifacts/performance.json"),
            ("resource_usage", "artifacts/resource_usage.log"),
            ("service_metrics", "artifacts/metrics_{service_name}.log"),
            ("examples", "artifacts/examples/"),
            ("analysis", "artifacts/analysis_{service_name}.json"),
        ],
    }

    # Language-specific patterns for compilation-heavy services
    LANGUAGE_PATTERNS = {
        "python": [
            ("python_version", "pre-compile/python_version.log"),
            ("pip_install", "pre-compile/pip_install.log"),
            ("asyncio_debug", "runtime/asyncio_debug.log"),
            ("python_traceback", "runtime/traceback.log"),
            ("python_logs", "artifacts/*.log"),
        ],
        "rust": [
            ("cargo_version", "pre-compile/cargo_version.log"),
            ("cargo_build", "compile/cargo_build.log"),
            ("rust_backtrace", "runtime/rust_backtrace.log"),
            ("target_artifacts", "artifacts/target/release/*"),
        ],
        "c": [
            ("gcc_version", "pre-compile/gcc_version.log"),
            ("make_build", "compile/make_build.log"),
            ("gdb_backtrace", "runtime/gdb_backtrace.log"),
            ("core_dump", "artifacts/core.*"),
        ],
        "cpp": [
            ("cmake_config", "pre-compile/cmake_config.log"),
            ("cmake_build", "compile/cmake_build.log"),
            ("valgrind", "runtime/valgrind.log"),
            ("sanitizer", "runtime/sanitizer.log"),
        ],
        "go": [
            ("go_version", "pre-compile/go_version.log"),
            ("go_build", "compile/go_build.log"),
            ("go_trace", "runtime/go_trace.log"),
            ("pprof", "artifacts/pprof.*"),
        ],
    }

    @classmethod
    def get_patterns_for_service(
        cls,
        protocol: str,
        service_type: str,
        service_name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """Get complete pattern set for a service."""
        patterns = []

        # Add base patterns
        patterns.extend(cls.BASE_PHASE_PATTERNS)

        # Add protocol-specific patterns
        if protocol.lower() in cls.PROTOCOL_PATTERNS:
            patterns.extend(cls.PROTOCOL_PATTERNS[protocol.lower()])

        # Add service type patterns
        if service_type.lower() in cls.SERVICE_TYPE_PATTERNS:
            patterns.extend(cls.SERVICE_TYPE_PATTERNS[service_type.lower()])

        # Add language-specific patterns
        if language and language.lower() in cls.LANGUAGE_PATTERNS:
            patterns.extend(cls.LANGUAGE_PATTERNS[language.lower()])

        # Substitute service name placeholders
        if service_name:
            patterns = [
                (output_type, pattern.replace("{service_name}", service_name))
                for output_type, pattern in patterns
            ]

        return patterns

    @classmethod
    def validate_patterns(
        cls, patterns: List[Tuple[str, str]]
    ) -> Tuple[bool, List[str]]:
        """Validate patterns follow expected format."""
        errors = []

        if not patterns:
            errors.append("No patterns provided")
            return False, errors

        required_phases = {"pre-compile", "compile", "runtime", "test"}
        found_phases = set()

        for output_type, pattern in patterns:
            if not isinstance(output_type, str) or not isinstance(pattern, str):
                errors.append(f"Invalid pattern format: {output_type}, {pattern}")
                continue

            # Check for phase coverage
            for phase in required_phases:
                if phase in pattern:
                    found_phases.add(phase)

        missing_phases = required_phases - found_phases
        if missing_phases:
            errors.append(f"Missing required phases: {missing_phases}")

        return len(errors) == 0, errors

    @classmethod
    def detect_protocol_from_path(cls, module_path: str) -> str:
        """Detect protocol from service module path."""
        module_path = module_path.lower()
        if "quic" in module_path:
            return "quic"
        elif "tcp" in module_path:
            return "tcp"
        elif "http" in module_path:
            return "http"
        elif "minip" in module_path:
            return "minip"
        return "unknown"

    @classmethod
    def detect_service_type_from_path(cls, module_path: str) -> str:
        """Detect service type from module path."""
        module_path = module_path.lower()
        if "testers" in module_path:
            return "tester"
        elif "iut" in module_path:
            return "iut"
        return "unknown"

    @classmethod
    def detect_language_from_path(cls, module_path: str) -> str:
        """Detect programming language from service module path."""
        module_path = module_path.lower()

        # Language detection patterns based on common service names
        language_indicators = {
            "python": ["aioquic", "python"],
            "rust": ["quiche", "quinn", "rust"],
            "c": ["picoquic", "quant", "lsquic"],
            "cpp": ["mvfst", "cpp", "facebook"],
            "go": ["quic_go", "golang", "go"],
        }

        for language, indicators in language_indicators.items():
            if any(indicator in module_path for indicator in indicators):
                return language

        return "unknown"
