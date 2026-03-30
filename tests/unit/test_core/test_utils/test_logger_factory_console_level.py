"""Unit tests for LoggerFactory.set_console_level().

Verifies that the classmethod correctly updates StreamHandler levels
on the root logger and all configured named loggers, while leaving
JsonlLogHandler instances untouched at DEBUG.
"""

import logging
import sys

import pytest

from panther.core.utils.jsonl_writer import JsonlLogHandler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_logger_factory():
    """Reset LoggerFactory singleton state so each test starts fresh."""
    from panther.core.utils.logger_factory import LoggerFactory

    LoggerFactory._initialized = False
    LoggerFactory._root_logger_configured = False
    LoggerFactory._config = {}
    LoggerFactory._handler_cache = {}
    LoggerFactory._feature_levels = {}
    LoggerFactory._structured_log_file = None

    # Remove any patched getLogger
    if hasattr(logging, "_original_getLogger"):
        logging.getLogger = logging._original_getLogger
        del logging._original_getLogger

    # Clean up root logger handlers
    root = logging.getLogger()
    root.handlers.clear()


@pytest.fixture(autouse=True)
def _clean_factory():
    """Ensure LoggerFactory is reset before and after every test."""
    _reset_logger_factory()
    yield
    _reset_logger_factory()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

TRACE = 5


@pytest.mark.unit
class TestSetConsoleLevel:
    """Tests for LoggerFactory.set_console_level()."""

    def test_noop_when_not_initialized(self):
        """set_console_level should silently return when factory is not initialized."""
        from panther.core.utils.logger_factory import LoggerFactory

        # Factory is not initialized (reset in fixture)
        assert not LoggerFactory._initialized
        # Should not raise
        LoggerFactory.set_console_level(logging.DEBUG)

    def test_updates_root_console_handler(self):
        """Console handler on root logger should be updated to the given level."""
        from panther.core.utils.logger_factory import LoggerFactory

        LoggerFactory.initialize({"level": "WARNING", "enable_colors": False})

        # Root logger should have a console handler at WARNING
        root = logging.getLogger()
        console_handlers = [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) >= 1
        assert console_handlers[0].level == logging.WARNING

        # After set_console_level, it should change
        LoggerFactory.set_console_level(logging.DEBUG)
        assert console_handlers[0].level == logging.DEBUG

    def test_updates_named_logger_console_handler(self):
        """Console handlers on named loggers created via get_logger should be updated."""
        from panther.core.utils.logger_factory import LoggerFactory

        LoggerFactory.initialize({"level": "INFO", "enable_colors": False})
        logger = LoggerFactory.get_logger("test.named.logger")

        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) >= 1
        for h in console_handlers:
            assert h.level == logging.INFO

        LoggerFactory.set_console_level(TRACE)

        for h in console_handlers:
            assert h.level == TRACE

    def test_preserves_file_handler_level(self, tmp_path):
        """FileHandler instances must remain at DEBUG regardless of set_console_level."""
        from panther.core.utils.logger_factory import LoggerFactory

        log_file = tmp_path / "test.jsonl"
        LoggerFactory.initialize(
            {
                "level": "INFO",
                "enable_colors": False,
                "output_file": str(log_file),
            }
        )

        logger = LoggerFactory.get_logger("test.file.handler")

        jsonl_handlers = [h for h in logger.handlers if isinstance(h, JsonlLogHandler)]
        assert len(jsonl_handlers) >= 1
        for jh in jsonl_handlers:
            assert jh.level == logging.DEBUG

        # Now change console level to ERROR
        LoggerFactory.set_console_level(logging.ERROR)

        # JSONL handlers should still be at DEBUG
        for jh in jsonl_handlers:
            assert jh.level == logging.DEBUG

        # Console handlers should be at ERROR
        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, JsonlLogHandler)
        ]
        for ch in console_handlers:
            assert ch.level == logging.ERROR

    def test_root_file_handler_preserved(self, tmp_path):
        """JsonlLogHandler on root logger must stay at DEBUG after set_console_level."""
        from panther.core.utils.logger_factory import LoggerFactory

        log_file = tmp_path / "root.jsonl"
        LoggerFactory.initialize(
            {
                "level": "INFO",
                "enable_colors": False,
                "output_file": str(log_file),
            }
        )

        root = logging.getLogger()
        jsonl_handlers = [h for h in root.handlers if isinstance(h, JsonlLogHandler)]
        assert len(jsonl_handlers) >= 1

        LoggerFactory.set_console_level(logging.CRITICAL)

        for jh in jsonl_handlers:
            assert jh.level == logging.DEBUG

    def test_updates_multiple_named_loggers(self):
        """All named loggers should have their console handlers updated."""
        from panther.core.utils.logger_factory import LoggerFactory

        LoggerFactory.initialize({"level": "WARNING", "enable_colors": False})
        loggers = [LoggerFactory.get_logger(f"test.multi.{i}") for i in range(5)]

        LoggerFactory.set_console_level(logging.DEBUG)

        for lgr in loggers:
            for h in lgr.handlers:
                if isinstance(h, logging.StreamHandler) and not isinstance(
                    h, logging.FileHandler
                ):
                    assert h.level == logging.DEBUG

    def test_set_trace_level(self):
        """Setting TRACE level (5) should work correctly."""
        from panther.core.utils.logger_factory import LoggerFactory

        LoggerFactory.initialize({"level": "INFO", "enable_colors": False})
        logger = LoggerFactory.get_logger("test.trace")

        LoggerFactory.set_console_level(TRACE)

        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        for ch in console_handlers:
            assert ch.level == TRACE

    def test_idempotent_calls(self):
        """Calling set_console_level multiple times should be safe."""
        from panther.core.utils.logger_factory import LoggerFactory

        LoggerFactory.initialize({"level": "INFO", "enable_colors": False})
        logger = LoggerFactory.get_logger("test.idempotent")

        LoggerFactory.set_console_level(logging.DEBUG)
        LoggerFactory.set_console_level(logging.WARNING)
        LoggerFactory.set_console_level(logging.ERROR)

        console_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        # Last call wins
        for ch in console_handlers:
            assert ch.level == logging.ERROR
