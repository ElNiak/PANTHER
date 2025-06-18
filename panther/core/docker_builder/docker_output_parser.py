# panther/core/docker_builder/output_parser.py
import re
from datetime import datetime
from typing import Optional, Tuple


class DockerOutputParser:
    """Parse Docker build output for progress tracking."""

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

    def __init__(self):
        self.total_steps = 0
        self.current_step = 0
        self.last_message = ""
        self.last_progress_update = datetime.now()
        self.build_stage = None
        self.last_significant_message = None

    def parse_line(self, line: str) -> Optional[Tuple[str, float, str]]:
        """
        Parse a Docker output line and return (message, progress%, level).

        Returns:
            Tuple of (message, progress percentage, log level) or None if line should be skipped
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
            self.current_step = int(step_match.group(1))
            self.total_steps = int(step_match.group(2))
            step_desc = step_match.group(3)
            progress = (self.current_step / self.total_steps) * 100

            # Extract key information from step description
            if "FROM" in step_desc:
                self.build_stage = "Base image"
                return (
                    f"Step {self.current_step}/{self.total_steps}: Setting base image",
                    progress,
                    "INFO",
                )
            elif "RUN" in step_desc:
                # Truncate long RUN commands
                if len(step_desc) > 80:
                    step_desc = step_desc[:77] + "..."
                return (
                    f"Step {self.current_step}/{self.total_steps}: {step_desc}",
                    progress,
                    "INFO",
                )
            elif "COPY" in step_desc or "ADD" in step_desc:
                return (
                    f"Step {self.current_step}/{self.total_steps}: Adding files",
                    progress,
                    "INFO",
                )
            else:
                return (
                    f"Step {self.current_step}/{self.total_steps}: {step_desc}",
                    progress,
                    "INFO",
                )

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

        # Check for download progress
        download_match = self.DOWNLOAD_PATTERN.search(line)
        if download_match:
            # Only report significant download progress (every 10%)
            progress_bar = download_match.group(1)
            progress_pct = (
                len([c for c in progress_bar if c == "="]) / len(progress_bar) * 100
                if progress_bar
                else 0
            )
            if progress_pct % 10 < 1:  # Report at 10% intervals
                size_current = download_match.group(2)
                unit_current = download_match.group(3) or ""
                size_total = download_match.group(4) or ""
                unit_total = download_match.group(5) or ""
                if size_total:
                    return (
                        f"Downloading: {size_current}{unit_current}/{size_total}{unit_total} ({progress_pct:.0f}%)",
                        progress_pct,
                        "DEBUG",
                    )
                else:
                    return (f"Downloading: {progress_pct:.0f}%", progress_pct, "DEBUG")
            return None

        # Check for extract progress
        extract_match = self.EXTRACT_PATTERN.search(line)
        if extract_match:
            # Only report significant extract progress
            progress_bar = extract_match.group(1)
            progress_pct = (
                len([c for c in progress_bar if c == "="]) / len(progress_bar) * 100
                if progress_bar
                else 0
            )
            if progress_pct % 20 < 1:  # Report at 20% intervals for extraction
                return (f"Extracting: {progress_pct:.0f}%", progress_pct, "DEBUG")
            return None

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
