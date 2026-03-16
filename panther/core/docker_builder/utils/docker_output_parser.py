# panther/core/docker_builder/utils/docker_output_parser.py
"""Docker build output parser with verbose-aware formatting.

Parses Docker build output line by line, extracting step progress,
download/extraction status, errors, and warnings. Output verbosity adapts
to the current console log level via ``LoggerFactory._verbose``.

When **not** verbose (default):
    - Step progress is shown as a concise one-liner with step number and
      a brief description of the Docker instruction.
    - Layer download and extraction details are suppressed entirely.

When **verbose** (console level <= DEBUG):
    - Full Docker output is shown without RUN-command truncation.
    - Download and extraction progress lines are forwarded at DEBUG level.
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from panther.core.exceptions.fast_fail import DockerBuildException
from panther.core.utils.logging_mixin import LoggerMixin


class DockerOutputParser(LoggerMixin):
    """Parse Docker build output for progress tracking.

    Args:
        verbose: If ``None`` (the default), verbose mode is read from
            ``LoggerFactory._verbose`` on each call. Pass an explicit
            ``bool`` to override.
    """

    STEP_PATTERN = re.compile(r"Step (\d+)/(\d+) : (.+)")
    DOWNLOAD_PATTERN = re.compile(
        r"Downloading.*\[([=>-]+)\]\s+(\d+\.?\d*)([KMG]?B)?\s*/?(\d+\.?\d*)?([KMG]?B)?"
    )
    EXTRACT_PATTERN = re.compile(
        r"Extracting.*\[([=>-]+)\]\s+(\d+\.?\d*)([KMG]?B)?\s*/?(\d+\.?\d*)?([KMG]?B)?"
    )
    PULL_PATTERN = re.compile(r"Pulling from (.+)")
    ALREADY_EXISTS_PATTERN = re.compile(r"Already exists")
    ERROR_PATTERN = re.compile(
        r'(?<!echo\s["\'])(?<!echo\s")(?<!Failed to add )(?<!Failed to build )(ERROR|error|Error):|(?<!echo\s["\'])(?<!echo\s")failed|Failed(?!\s*to\s*(add|build))|FAILED'
    )
    WARNING_PATTERN = re.compile(r"(WARNING|warning|Warning):")
    BUILD_CONTEXT_PATTERN = re.compile(r"Sending build context.*\s(\d+\.?\d*)([KMG]?B)")

    # Brief labels for Docker instructions used in concise mode
    _INSTRUCTION_LABELS = {
        "FROM": "Base image",
        "RUN": "Run",
        "COPY": "Copy files",
        "ADD": "Add files",
        "ENV": "Set env",
        "WORKDIR": "Set workdir",
        "EXPOSE": "Expose port",
        "CMD": "Set command",
        "ENTRYPOINT": "Set entrypoint",
        "ARG": "Build arg",
        "LABEL": "Set label",
        "VOLUME": "Declare volume",
        "USER": "Set user",
        "SHELL": "Set shell",
    }

    def __init__(self, verbose: Optional[bool] = None):
        """Initialize the parser.

        Args:
            verbose: Explicit verbose override. ``None`` means read from
                ``LoggerFactory._verbose`` dynamically.
        """
        self.total_steps = 0
        self.current_step = 0
        self.last_message = ""
        self.last_progress_update = datetime.now()
        self.build_stage = None
        self.last_significant_message = None
        self._verbose_override = verbose

    @property
    def verbose(self) -> bool:
        """Whether verbose output is active.

        Returns:
            True when the console is in DEBUG/TRACE mode or when an
            explicit ``verbose=True`` was passed to the constructor.
        """
        if self._verbose_override is not None:
            return self._verbose_override
        from panther.core.utils.logger_factory import LoggerFactory

        return LoggerFactory._verbose

    def _concise_step_label(self, step_desc: str) -> str:
        """Derive a short human-readable label from a Dockerfile instruction.

        Args:
            step_desc: The raw instruction text (e.g. ``RUN apt-get install ...``).

        Returns:
            A short label such as ``"Run"`` or ``"Copy files"``.
        """
        first_word = step_desc.split()[0].upper() if step_desc.split() else ""
        return self._INSTRUCTION_LABELS.get(first_word, first_word.capitalize())

    def parse_line(self, line: str) -> Optional[Tuple[str, float, str]]:
        """Parse a Docker output line and return (message, progress%, level).

        The output varies depending on :pyattr:`verbose`:

        * **Concise** (default): step lines produce a short one-liner like
          ``Step 5/12: Run``; download/extract lines are suppressed.
        * **Verbose**: the full instruction text is shown without
          truncation and download/extract lines are forwarded.

        Args:
            line: Raw Docker build output line.

        Returns:
            Tuple of (message, progress_percentage, log_level) or ``None``
            if the line should be skipped.
        """
        line = line.strip()
        if not line:
            return None

        # Check for errors first
        if self.ERROR_PATTERN.search(line):
            return (line, self.current_step / max(self.total_steps, 1) * 100, "ERROR")

        # Check for warnings
        if self.WARNING_PATTERN.search(line):
            return (line, self.current_step / max(self.total_steps, 1) * 100, "WARNING")

        # Check for build context
        context_match = self.BUILD_CONTEXT_PATTERN.search(line)
        if context_match:
            size = context_match.group(1)
            unit = context_match.group(2)
            return (f"Sending build context: {size}{unit}", 0, "INFO")

        # Check for step progress
        step_match = self.STEP_PATTERN.match(line)
        if step_match:
            return self._parse_step(step_match)

        # Check for pull operations
        pull_match = self.PULL_PATTERN.search(line)
        if pull_match:
            image = pull_match.group(1)
            return (
                f"Pulling image: {image}",
                self.current_step / max(self.total_steps, 1) * 100,
                "INFO",
            )

        # Skip "Already exists" messages
        if self.ALREADY_EXISTS_PATTERN.search(line):
            return None

        # Download / extract progress -- suppressed in concise mode
        matched, result = self._parse_download_extract(line)
        if matched:
            return result  # result is None when suppressed, tuple when verbose

        # Skip redundant messages
        if line == self.last_message:
            return None

        self.last_message = line

        # Skip common verbose messages
        skip_patterns = [
            r"^\s*-+>\s*[a-f0-9]{12}$",  # Docker layer IDs
            r"^Pulling fs layer",
            r"^Waiting",
            r"^Verifying Checksum",
            r"^Download complete",
            r"^Pull complete",
            r"^\s*$",  # Empty lines
        ]

        for pattern in skip_patterns:
            if re.match(pattern, line):
                return None

        # Only return other messages if they seem significant
        if any(
            keyword in line.lower()
            for keyword in ["complete", "success", "built", "tagged", "running"]
        ):
            return (line, self.current_step / max(self.total_steps, 1) * 100, "INFO")

        # Log everything else at TRACE level
        return (line, self.current_step / max(self.total_steps, 1) * 100, "TRACE")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_step(
        self,
        step_match: re.Match,
    ) -> Tuple[str, float, str]:
        """Format a Step line according to current verbosity.

        Args:
            step_match: Regex match from ``STEP_PATTERN``.

        Returns:
            Tuple of (message, progress, level).
        """
        self.current_step = int(step_match.group(1))
        self.total_steps = int(step_match.group(2))
        step_desc = step_match.group(3)
        progress = (self.current_step / self.total_steps) * 100

        if self.verbose:
            # Verbose: show full instruction without truncation
            if "FROM" in step_desc:
                self.build_stage = "Base image"
            return (
                f"Step {self.current_step}/{self.total_steps}: {step_desc}",
                progress,
                "INFO",
            )

        # Concise: one-liner with brief label
        if "FROM" in step_desc:
            self.build_stage = "Base image"
        label = self._concise_step_label(step_desc)
        return (
            f"Step {self.current_step}/{self.total_steps}: {label}",
            progress,
            "INFO",
        )

    def _parse_download_extract(
        self,
        line: str,
    ) -> Tuple[bool, Optional[Tuple[str, float, str]]]:
        """Parse download/extraction lines, suppressing them in concise mode.

        Args:
            line: Raw Docker build output line.

        Returns:
            A two-element tuple ``(matched, result)``.  ``matched`` is
            ``True`` when the line *is* a download or extract line (even
            if suppressed).  ``result`` is the parsed ``(message,
            progress, level)`` tuple when the line should be emitted, or
            ``None`` when it should be suppressed.
        """
        download_match = self.DOWNLOAD_PATTERN.search(line)
        if download_match:
            if not self.verbose:
                return True, None  # matched but suppress in concise mode
            progress_bar = download_match.group(1)
            progress_pct = (
                len([c for c in progress_bar if c == "="]) / len(progress_bar) * 100
                if progress_bar
                else 0
            )
            size_current = download_match.group(2)
            unit_current = download_match.group(3) or ""
            size_total = download_match.group(4) or ""
            unit_total = download_match.group(5) or ""
            if size_total:
                return True, (
                    f"Downloading: {size_current}{unit_current}/{size_total}{unit_total} ({progress_pct:.0f}%)",
                    progress_pct,
                    "DEBUG",
                )
            return True, (f"Downloading: {progress_pct:.0f}%", progress_pct, "DEBUG")

        extract_match = self.EXTRACT_PATTERN.search(line)
        if extract_match:
            if not self.verbose:
                return True, None  # matched but suppress in concise mode
            progress_bar = extract_match.group(1)
            progress_pct = (
                len([c for c in progress_bar if c == "="]) / len(progress_bar) * 100
                if progress_bar
                else 0
            )
            return True, (f"Extracting: {progress_pct:.0f}%", progress_pct, "DEBUG")

        return False, None  # not a download/extract line

    def get_summary(self) -> str:
        """Get a summary of the build process."""
        if self.total_steps > 0:
            return (
                f"Docker build completed: {self.current_step}/{self.total_steps} steps"
            )
        else:
            return "Docker build completed"

    def format_progress_bar(self, progress: float, width: int = 20) -> str:
        """Format a simple progress bar."""
        filled = int(width * progress / 100)
        bar = "=" * filled + "-" * (width - filled)
        return f"[{bar}] {progress:.0f}%"

    def log_docker_output(
        self, generator, task_name: str = "docker command execution", log_f=None
    ) -> None:
        """Log the output of a Docker command execution with smart progress tracking.

        Processes the output from a generator that yields Docker command
        execution results. Logs to the specified log file and to the logger.

        Args:
            generator: A generator (or list) that yields Docker command
                execution results (dicts with ``stream``/``error`` keys,
                or raw strings/bytes).
            task_name: Human-readable name of the task being executed.
            log_f: Optional file object to write raw log output to.

        Raises:
            ValueError: If an error is encountered in the Docker command
                execution output.
        """
        output = None

        while True:
            try:
                if isinstance(generator, list):
                    # If generator is a list, iterate through it
                    output = generator.pop(0) if generator else None
                    if output is None:
                        raise StopIteration
                else:
                    # Otherwise, get the next output from the generator
                    output = generator.__next__()
                # Handle both dictionary and string output
                if isinstance(output, dict):
                    if "stream" in output:
                        output_str = output["stream"].strip("\r\n").strip("\n")
                        if log_f:
                            log_f.write(f"{task_name}:{output_str}\n")

                        if parsed := self.parse_line(output_str):
                            message, progress, level = parsed

                            # Log based on parsed level
                            self.log_message_with_level(
                                task_name, message, progress, level
                            )

                    elif "error" in output:
                        if log_f:
                            log_f.write(f"{task_name}:{output['error']}\n")
                        self.logger.error(
                            "Error from %s: %s", task_name, output["error"]
                        )
                else:
                    # Handle raw output (bytes or string)
                    output_str = str(output).strip("\r\n").strip("\n")
                    if log_f:
                        log_f.write(f"{task_name}:{output_str}\n")

                    if parsed := self.parse_line(output_str):
                        message, progress, level = parsed
                        self.log_message_by_level(task_name, message, level)

            except StopIteration:
                # Get final summary from parser
                summary = self.get_summary()
                self.logger.info("%s complete. %s", task_name, summary)
                break
            except ValueError:
                self.logger.error("Error parsing output from %s: %s", task_name, output)

    def log_message_by_level(self, task_name, message, level):
        """Route a parsed message to the appropriate logger level.

        Args:
            task_name: Human-readable task name for context.
            message: Parsed message text.
            level: String log level (``ERROR``, ``WARNING``, ``INFO``,
                ``DEBUG``, or ``TRACE``).
        """
        if level == "ERROR":
            self.logger.error("%s: %s", task_name, message)
        elif level == "WARNING":
            self.logger.warning("%s: %s", task_name, message)
        elif level == "INFO":
            self.logger.info("%s: %s", task_name, message)
        elif level == "DEBUG":
            self.logger.debug("%s: %s", task_name, message)
        elif level == "TRACE" and hasattr(self.logger, "trace"):
            self.logger.trace("%s: %s", task_name, message)

    def log_message_with_level(self, task_name, message, progress, level):
        """Route a parsed message with progress to the appropriate logger level.

        Args:
            task_name: Human-readable task name for context.
            message: Parsed message text.
            progress: Build progress percentage (0-100).
            level: String log level.
        """
        if level == "ERROR":
            self.logger.error("%s: %s", task_name, message)
        elif level == "WARNING":
            self.logger.warning("%s: %s", task_name, message)
        elif level == "INFO":
            self.logger.info("%s [%.0f%%]: %s", task_name, progress, message)
        elif level == "DEBUG":
            self.logger.debug("%s: %s", task_name, message)
        elif level == "TRACE" and hasattr(self.logger, "trace"):
            self.logger.trace("%s: %s", task_name, message)

    def log_and_raise_build_exception(
        self, impl_name, dockerfile_path, image_tag, e, log_f
    ):
        """Log remaining build output and raise a ``DockerBuildException``.

        Args:
            impl_name: Implementation name (for the exception).
            dockerfile_path: Path to the Dockerfile.
            image_tag: Docker image tag that was being built.
            e: Original exception (must have a ``build_log`` attribute).
            log_f: Optional open file handle for writing raw logs.

        Raises:
            DockerBuildException: Always raised.
        """
        if log_f:
            self.log_docker_output(
                e.build_log, f"Building Docker image '{image_tag}'", log_f
            )
            log_f.write(f"ERROR: {e}\n")
            log_f.close()
        raise DockerBuildException(
            message=f"Failed to build Docker image '{image_tag}': {e}",
            image_name=impl_name,
            dockerfile=str(dockerfile_path),
            build_error=str(e),
        ) from e
