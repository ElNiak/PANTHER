"""Generic service health analysis for all PANTHER services.

Analyzes outputs from IUT and tester services to determine execution health
without requiring per-service implementation. Works with the standard phase
directory structure (pre-compile/, compile/, runtime/, test/).
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

STANDARD_PHASES = ["pre-compile", "compile", "runtime", "test"]

# Generic error patterns (not protocol-specific)
ERROR_PATTERNS = [
    re.compile(r"Segmentation fault", re.IGNORECASE),
    re.compile(r"SIGSEGV"),
    re.compile(r"SIGABRT"),
    re.compile(r"core dumped", re.IGNORECASE),
    re.compile(r"No such file or directory"),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"^ERROR:", re.MULTILINE),
    re.compile(r"^FATAL:", re.MULTILINE),
    re.compile(r"Failed:", re.IGNORECASE),
    re.compile(r"Connection refused"),
    re.compile(r"Permission denied"),
    re.compile(r"killed", re.IGNORECASE),
    re.compile(r"OOM|Out of memory", re.IGNORECASE),
]

EXIT_CODE_PATTERNS = [
    re.compile(r"exit(?:\s+|_)code[:\s]+(\d+)", re.IGNORECASE),
    re.compile(r"return(?:\s+|_)code[:\s]+(\d+)", re.IGNORECASE),
    re.compile(r"exited\s+with\s+(?:code\s+)?(\d+)", re.IGNORECASE),
    re.compile(r"status[:\s]+(\d+)", re.IGNORECASE),
]


@dataclass
class ServiceHealth:
    """Health assessment for a single service."""

    service_name: str
    service_type: str  # "iut" or "tester"
    phases_completed: Dict[str, bool] = field(default_factory=dict)
    exit_code: Optional[int] = None
    crashed: bool = False
    error_summary: Optional[str] = None
    stderr_errors: List[str] = field(default_factory=list)
    compilation_succeeded: bool = True
    has_output_artifacts: bool = False
    log_size_bytes: int = 0
    output_files_found: int = 0
    output_files_expected: int = 0

    @property
    def status(self) -> str:
        """Derive overall status from health indicators."""
        if self.crashed or self.exit_code not in (None, 0):
            return "failed"
        if not self.compilation_succeeded:
            return "failed"
        if self.stderr_errors:
            return "degraded"
        if not any(self.phases_completed.values()):
            return "unknown"
        return "healthy"

    @property
    def output_completeness(self) -> float:
        """Ratio of found vs expected output files (0.0 - 1.0)."""
        if self.output_files_expected == 0:
            return 1.0 if self.output_files_found > 0 else 0.0
        return min(self.output_files_found / self.output_files_expected, 1.0)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status
        d["output_completeness"] = self.output_completeness
        return d


class ServiceHealthAnalyzer:
    """Analyzes service outputs for health status.

    Works with any service by reading from the standard phase directory
    structure. No service-specific code needed.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze_service(
        self,
        service_name: str,
        service_type: str,
        log_dir: Path,
        output_patterns: Optional[List[Tuple[str, str]]] = None,
    ) -> ServiceHealth:
        """Analyze a single service's outputs.

        Args:
            service_name: Name of the service.
            service_type: "iut" or "tester".
            log_dir: Root log directory for this service.
            output_patterns: Optional list of (type, glob_pattern) tuples.

        Returns:
            ServiceHealth with analysis results.
        """
        health = ServiceHealth(
            service_name=service_name,
            service_type=service_type,
        )

        if not log_dir or not log_dir.exists():
            self.logger.debug(
                "Log directory not found for %s: %s", service_name, log_dir
            )
            return health

        health.phases_completed = self._check_phase_completeness(log_dir)
        health.log_size_bytes = self._compute_log_size(log_dir)

        # Parse compilation status from compile phase
        health.compilation_succeeded = self._check_compilation(log_dir)

        # Parse exit code and crash status from runtime/test phases
        exit_code, crashed = self._extract_exit_info(log_dir)
        health.exit_code = exit_code
        health.crashed = crashed

        # Collect stderr errors
        health.stderr_errors = self._collect_stderr_errors(log_dir)
        if health.stderr_errors:
            health.error_summary = health.stderr_errors[0][:200]

        # Check output artifacts
        if output_patterns:
            found, expected = self._check_output_patterns(log_dir, output_patterns)
            health.output_files_found = found
            health.output_files_expected = expected
            health.has_output_artifacts = found > 0
        else:
            # Fallback: check if any non-log files exist
            non_log = [
                f
                for f in log_dir.rglob("*")
                if f.is_file() and f.suffix not in (".log", ".err")
            ]
            health.has_output_artifacts = len(non_log) > 0
            health.output_files_found = len(non_log)

        return health

    def analyze_all_services(
        self,
        services_managers,
        get_log_dir_func,
    ) -> List[ServiceHealth]:
        """Analyze all services provided by environment managers.

        Args:
            services_managers: Iterable of service manager objects with
                service_name, get_output_patterns(), and service type info.
            get_log_dir_func: Callable(service_name) -> Path returning
                the log directory for a given service.

        Returns:
            List of ServiceHealth results.
        """
        results = []
        for sm in services_managers:
            service_name = getattr(sm, "service_name", str(sm))
            service_type = self._detect_service_type(sm)

            log_dir = get_log_dir_func(service_name)

            patterns = None
            if hasattr(sm, "get_output_patterns"):
                try:
                    patterns = sm.get_output_patterns()
                except Exception as e:
                    self.logger.warning(
                        "Failed to get output patterns for %s: %s. "
                        "Health analysis will skip output completeness checking.",
                        service_name,
                        e,
                    )

            health = self.analyze_service(service_name, service_type, log_dir, patterns)
            results.append(health)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_phase_completeness(self, log_dir: Path) -> Dict[str, bool]:
        completed = {}
        for phase in STANDARD_PHASES:
            phase_dir = log_dir / phase
            if phase_dir.exists() and phase_dir.is_dir():
                completed[phase] = any(phase_dir.iterdir())
            else:
                completed[phase] = False
        return completed

    def _compute_log_size(self, log_dir: Path) -> int:
        total = 0
        for f in log_dir.rglob("*.log"):
            try:
                total += f.stat().st_size
            except OSError:
                pass
        return total

    def _check_compilation(self, log_dir: Path) -> bool:
        compile_stderr = log_dir / "compile" / "stderr.log"
        if not compile_stderr.exists():
            # No compile phase = no compilation needed or didn't run
            return True
        try:
            content = compile_stderr.read_text(errors="replace")
            fail_indicators = [
                "error:",
                "fatal error",
                "compilation failed",
                "make: ***",
            ]
            return not any(ind in content.lower() for ind in fail_indicators)
        except OSError:
            return True

    def _extract_exit_info(self, log_dir: Path) -> Tuple[Optional[int], bool]:
        """Extract exit code and crash status from runtime/test logs."""
        exit_code = None
        crashed = False

        for phase in ("test", "runtime"):
            for log_name in ("stdout.log", "stderr.log"):
                log_path = log_dir / phase / log_name
                if not log_path.exists():
                    continue
                try:
                    content = log_path.read_text(errors="replace")[-4096:]
                except OSError:
                    continue

                # Check for crash signals
                if any(
                    p.search(content)
                    for p in ERROR_PATTERNS[
                        :4
                    ]  # SIGSEGV, SIGABRT, core dumped, segfault
                ):
                    crashed = True

                # Extract exit code
                if exit_code is None:
                    for pattern in EXIT_CODE_PATTERNS:
                        m = pattern.search(content)
                        if m:
                            exit_code = int(m.group(1))
                            break

        return exit_code, crashed

    def _collect_stderr_errors(self, log_dir: Path, max_errors: int = 10) -> List[str]:
        errors = []
        for phase in STANDARD_PHASES:
            stderr_log = log_dir / phase / "stderr.log"
            if not stderr_log.exists():
                continue
            try:
                content = stderr_log.read_text(errors="replace")
            except OSError:
                continue

            for pattern in ERROR_PATTERNS:
                for match in pattern.finditer(content):
                    # Get the full line containing the match
                    start = content.rfind("\n", 0, match.start()) + 1
                    end = content.find("\n", match.end())
                    if end == -1:
                        end = len(content)
                    line = content[start:end].strip()
                    if line and line not in errors:
                        errors.append(line[:500])
                        if len(errors) >= max_errors:
                            return errors
        return errors

    def _check_output_patterns(
        self, log_dir: Path, patterns: List[Tuple[str, str]]
    ) -> Tuple[int, int]:
        expected = len(patterns)
        found = 0
        for _output_type, glob_pattern in patterns:
            if list(log_dir.rglob(glob_pattern)):
                found += 1
        return found, expected

    def _detect_service_type(self, sm) -> str:
        # Check for tester interface
        try:
            from panther.plugins.services.testers.tester_interface import ITesterManager

            if isinstance(sm, ITesterManager):
                return "tester"
        except ImportError:
            pass

        # Check for service config type attribute
        if hasattr(sm, "service_config_to_test"):
            impl = getattr(sm.service_config_to_test, "implementation", None)
            if impl:
                impl_type = getattr(impl, "type", None)
                if impl_type:
                    type_str = getattr(impl_type, "value", str(impl_type)).lower()
                    if type_str == "tester":
                        return "tester"

        return "iut"
