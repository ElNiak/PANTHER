"""Console formatter with phase/service context and phase banners.

Extends colorlog.ColoredFormatter (with graceful fallback to
logging.Formatter) to produce short, context-rich console output:

    12:30:01 [INFO] (initialization) Loading plugins...
    12:30:05 [INFO] (test_execution|picoquic) Starting service
    12:30:10 [WARNING] Connection timeout

The formatter reads the current LogContext (phase, service_id) from
``get_log_context()`` on every record so call-sites don't need to pass
extra arguments.

See Also:
    ``panther.core.utils.log_context`` -- context propagation
    ``panther.core.utils.logger_factory`` -- where this formatter is wired in
"""

import logging
from typing import Any, Dict, Optional

import click

from .log_context import get_log_context

# Prefix stripped from module names to keep output concise
_MODULE_PREFIX = "panther.core."


def _short_module(name: str) -> str:
    """Strip common prefixes from a module name for compact display.

    Args:
        name: Full dotted module name (e.g. ``panther.core.experiment_manager``).

    Returns:
        Shortened name with ``panther.core.`` prefix removed when present.
    """
    if name.startswith(_MODULE_PREFIX):
        return name[len(_MODULE_PREFIX) :]
    return name


def _build_context_tag() -> str:
    """Build the ``(phase|service)`` tag from the current LogContext.

    Returns:
        A string like ``"(initialization|picoquic) "`` when both fields
        are set, ``"(initialization) "`` when only phase is set, or
        ``""`` when no context is available.
    """
    ctx = get_log_context()
    parts: list[str] = []
    if ctx.phase:
        parts.append(ctx.phase)
    if ctx.service_id:
        parts.append(ctx.service_id)
    if parts:
        return f"({' | '.join(parts)}) "  # note trailing space
    return ""


class ConsoleFormatter(logging.Formatter):
    """Human-friendly console formatter with phase/service context.

    Features:
        - Short ``HH:MM:SS`` timestamps (date is redundant for live runs)
        - Phase and service context injected from LogContext
        - Shortened module names (strips ``panther.core.`` prefix)
        - Optional color support via ``colorlog`` (auto-detected)

    The ``banner()`` static method prints a prominent phase separator
    directly to the terminal via ``click.echo()`` so it is not affected
    by log-level filtering.

    Args:
        log_colors: Color mapping passed to ``colorlog.ColoredFormatter``.
            Ignored when colorlog is not available.
        **kwargs: Forwarded to the underlying Formatter constructor.
    """

    # Base format -- caller injects %(log_color)s when colors are enabled
    _BASE_FMT = (
        "%(asctime)s [%(levelname)s] %(context_tag)s%(short_module)s - %(message)s"
    )

    def __init__(
        self,
        log_colors: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the console formatter.

        Args:
            log_colors: Mapping of level names to colorlog color strings.
                Pass ``None`` to disable color output entirely.
            **kwargs: Extra keyword arguments forwarded to ``logging.Formatter``.
        """
        self._use_color = False
        self._color_formatter: Optional[logging.Formatter] = None

        if log_colors is not None:
            try:
                import colorlog  # type: ignore[import-untyped]

                color_fmt = self._BASE_FMT.replace(
                    "%(levelname)s", "%(log_color)s%(levelname)s"
                )
                self._color_formatter = colorlog.ColoredFormatter(
                    color_fmt,
                    datefmt="%H:%M:%S",
                    log_colors=log_colors,
                    reset=True,
                )
                self._use_color = True
            except ImportError:
                pass

        # Plain-text fallback (always built, used when colorlog unavailable)
        super().__init__(fmt=self._BASE_FMT, datefmt="%H:%M:%S", **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with context tag and shortened module name.

        Args:
            record: The log record to format.

        Returns:
            Formatted string ready for console output.
        """
        # Inject extra fields that the format string references
        record.context_tag = _build_context_tag()  # type: ignore[attr-defined]
        record.short_module = _short_module(record.module)  # type: ignore[attr-defined]

        if self._use_color and self._color_formatter is not None:
            return self._color_formatter.format(record)
        return super().format(record)

    # ------------------------------------------------------------------
    # Phase banners
    # ------------------------------------------------------------------

    @staticmethod
    def banner(text: str, width: int = 50) -> None:
        """Print a prominent phase-transition banner to the terminal.

        Uses ``click.echo()`` to bypass log formatting and level filtering,
        ensuring the banner is always visible.

        Args:
            text: Banner text (e.g. ``"Initialization"``).
            width: Total character width of the separator lines.
        """
        separator = "\u2550" * width  # BOX DRAWINGS DOUBLE HORIZONTAL
        click.echo("")
        click.echo(separator)
        click.echo(f" {text}")
        click.echo(separator)
