"""Declarative failure pattern library for root cause analysis.

Defines a catalog of known failure patterns derived from PANTHER's
ErrorCategory taxonomy. Each pattern associates event signatures and
message regexes with an actionable suggestion so that the RCA engine
can explain *why* an experiment failed and what the user should try next.

Typical usage::

    from panther.core.reporting.failure_patterns import BUILTIN_PATTERNS

    for pattern in BUILTIN_PATTERNS:
        if pattern.matches(record):
            print(pattern.suggestion)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FailurePattern:
    """A declarative description of a known failure mode.

    Attributes:
        name: Machine-readable identifier (e.g. ``"docker_build_failure"``).
        description: Human-readable explanation of the failure.
        event_types: Event type strings that this pattern matches
            (e.g. ``["service.error", "environment.error"]``).
        message_patterns: Regex patterns applied to the ``message`` field.
            A match on *any* pattern is sufficient.
        category: Error category value from ``ErrorCategory`` enum.
        suggestion: Actionable fix text shown to the user.
        severity: One of ``"critical"``, ``"high"``, ``"medium"``, ``"low"``.
    """

    name: str
    description: str
    event_types: tuple  # frozen requires hashable
    message_patterns: tuple  # frozen requires hashable
    category: str
    suggestion: str
    severity: str

    def matches_message(self, message: str) -> bool:
        """Check whether *message* matches any of the declared patterns.

        Args:
            message: The log/event message to test.

        Returns:
            True if at least one ``message_patterns`` regex matches.
        """
        if not message:
            return False
        for raw_pattern in self.message_patterns:
            try:
                if re.search(raw_pattern, message, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

    def matches_event_type(self, event_type: str) -> bool:
        """Check whether *event_type* is one of the declared types.

        Args:
            event_type: The event type string from the log record.

        Returns:
            True if the event type appears in ``event_types``.
        """
        return event_type in self.event_types

    def matches(self, record: Dict) -> float:
        """Score how well a log record matches this pattern.

        Returns a confidence score between 0.0 (no match) and 1.0
        (strong match).  The score is determined by:

        * 0.0 -- neither event type nor message matched
        * 0.4 -- message pattern matched only
        * 0.5 -- event type matched only
        * 0.8 -- both event type and message matched
        * +0.2 bonus if the record's category field equals this pattern's category

        Args:
            record: Parsed structured.jsonl record dict.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        score = 0.0

        message = record.get("message", "")
        event_type = record.get("event_type", "")

        msg_match = self.matches_message(message)
        evt_match = bool(event_type) and self.matches_event_type(event_type)

        if msg_match and evt_match:
            score = 0.8
        elif evt_match:
            score = 0.5
        elif msg_match:
            score = 0.4
        else:
            return 0.0

        # Bonus for category agreement
        record_category = record.get("category", "")
        if record_category and record_category == self.category:
            score = min(1.0, score + 0.2)

        return score


# ---------------------------------------------------------------------------
# Built-in pattern catalog
# ---------------------------------------------------------------------------
# Derived from ErrorCategory values in panther/core/exceptions/fast_fail.py.

BUILTIN_PATTERNS: List[FailurePattern] = [
    FailurePattern(
        name="docker_build_failure",
        description="Docker image build failed during environment setup.",
        event_types=(
            "service.error",
            "environment.error",
            "docker.build.failed",
        ),
        message_patterns=(
            r"docker\s+build\s+fail",
            r"(?:Dockerfile|docker-compose).*(?:error|fail)",
            r"build.*image.*fail",
            r"COPY\s+failed",
            r"returned a non-zero code",
        ),
        category="docker_build",
        suggestion=(
            "Check the Dockerfile and build logs for syntax errors or "
            "missing dependencies. Run 'docker build' manually to reproduce."
        ),
        severity="critical",
    ),
    FailurePattern(
        name="certificate_error",
        description="TLS certificate generation or validation failed.",
        event_types=(
            "service.error",
            "security.error",
        ),
        message_patterns=(
            r"certific",
            r"tls.*(?:error|fail)",
            r"ssl.*(?:error|fail)",
            r"x509",
            r"handshake.*fail",
            r"cert.*(?:expired|invalid|missing)",
        ),
        category="security",
        suggestion=(
            "Regenerate TLS certificates. Check certificate paths and "
            "expiration dates. Ensure the CA chain is complete."
        ),
        severity="critical",
    ),
    FailurePattern(
        name="ivy_compilation_timeout",
        description="Ivy test compilation took too long or failed.",
        event_types=(
            "service.error",
            "tester.error",
            "test.error",
        ),
        message_patterns=(
            r"ivy.*compil.*(?:fail|timeout|error)",
            r"ivy.*timed?\s*out",
            r"compilation.*(?:timeout|exceeded)",
            r"ivy_compile.*fail",
        ),
        category="test_framework",
        suggestion=(
            "Increase Ivy compilation timeout. Consider using the Ivy build "
            "cache (first build takes ~30 minutes). Check ivy compilation logs."
        ),
        severity="critical",
    ),
    FailurePattern(
        name="port_conflict",
        description="A required network port is already in use.",
        event_types=(
            "service.error",
            "environment.error",
            "network.error",
        ),
        message_patterns=(
            r"port.*(?:in\s+use|conflict|occupied|bind)",
            r"address\s+already\s+in\s+use",
            r"EADDRINUSE",
            r"bind.*fail",
        ),
        category="network_setup",
        suggestion=(
            "Check for stale Docker containers or lingering processes. "
            "Run 'docker ps' and 'docker compose down' to free ports."
        ),
        severity="high",
    ),
    FailurePattern(
        name="segfault",
        description="A service crashed with a segmentation fault.",
        event_types=(
            "service.error",
            "service.crashed",
        ),
        message_patterns=(
            r"SIGSEGV",
            r"segmentation\s+fault",
            r"signal\s+11",
            r"core\s+dump",
            r"segfault",
        ),
        category="command_execution",
        suggestion=(
            "Check core dump files in the service output directory. "
            "Run with GDB/valgrind for detailed crash analysis. "
            "This may indicate a bug in the IUT implementation."
        ),
        severity="critical",
    ),
    FailurePattern(
        name="oom_killed",
        description="A process was killed due to memory exhaustion.",
        event_types=(
            "service.error",
            "service.crashed",
            "environment.error",
        ),
        message_patterns=(
            r"OOM",
            r"out\s+of\s+memory",
            r"oom.?kill",
            r"memory.*exhaust",
            r"Cannot\s+allocate\s+memory",
            r"killed.*memory",
        ),
        category="resource",
        suggestion=(
            "Increase Docker memory limits in the experiment config. "
            "Check 'docker stats' during execution. Consider reducing "
            "parallel test count."
        ),
        severity="critical",
    ),
    FailurePattern(
        name="timeout_cascade",
        description="Multiple timeout errors occurred in succession.",
        event_types=(
            "service.error",
            "test.error",
            "service.timeout",
        ),
        message_patterns=(
            r"timeout",
            r"timed?\s*out",
            r"deadline\s+exceeded",
            r"connection.*timeout",
            r"read.*timeout",
        ),
        category="cascade",
        suggestion=(
            "Check network connectivity between containers. Increase "
            "timeout values in the experiment config. Verify services "
            "are starting and accepting connections."
        ),
        severity="high",
    ),
    FailurePattern(
        name="compilation_failure",
        description="Source compilation failed for a service or test.",
        event_types=(
            "service.error",
            "tester.error",
        ),
        message_patterns=(
            r"compil.*(?:error|fail)",
            r"make.*(?:error|fail)",
            r"cmake.*(?:error|fail)",
            r"undefined\s+reference",
            r"cannot\s+find\s+-l",
            r"fatal\s+error:.*\.h",
            r"error:.*expected",
        ),
        category="command_execution",
        suggestion=(
            "Check stderr logs for the failing service. Verify build "
            "dependencies are installed in the Docker image. Try "
            "rebuilding the image with '--no-cache'."
        ),
        severity="high",
    ),
]


def get_pattern_by_name(name: str) -> Optional[FailurePattern]:
    """Look up a built-in pattern by its name.

    Args:
        name: Pattern name (e.g. ``"docker_build_failure"``).

    Returns:
        The matching ``FailurePattern``, or ``None`` if not found.
    """
    for pattern in BUILTIN_PATTERNS:
        if pattern.name == name:
            return pattern
    return None
