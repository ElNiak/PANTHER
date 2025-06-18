"""
Quick verification test for the logging system.

This test verifies that the logging system works correctly
with the recent changes.
"""

import tempfile
import logging
from pathlib import Path

from panther.core.utils.logger_factory import LoggerFactory
from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.observer.base.observer_interface import IObserver
from panther.core.events.base.event_base import BaseEvent


class TestComponent(LoggerMixin):
    """Test component using LoggerMixin."""
    
    def work(self):
        self.log_operation_start("test_work")
        self.logger.info("Doing work...")
        self.log_operation_complete("test_work", status="success")


class TestObserver(IObserver):
    """Test observer using _setup_logging."""
    
    def __init__(self):
        super().__init__()
        self.logger = self._setup_logging(
            logger_name="TestObserver",
            log_level=logging.INFO
        )
        
    def on_event(self, event: BaseEvent):
        self.logger.info(f"Received event: {event}")


def test_logging_system_works():
    """Verify the logging system works correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        
        # Reset LoggerFactory
        LoggerFactory._initialized = False
        LoggerFactory._config = {}
        
        # Initialize LoggerFactory
        LoggerFactory.initialize({
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] - %(name)s - %(message)s',
            'output_file': str(log_file)
        })
        
        # Create and use components
        component = TestComponent()
        observer = TestObserver()
        
        # Do work
        component.work()
        observer.logger.info("Observer is ready")
        
        # Direct logger
        direct_logger = LoggerFactory.get_logger("DirectLogger")
        direct_logger.info("Direct logger message")
        
        # Force flush
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        # Verify log file
        assert log_file.exists()
        content = log_file.read_text()
        
        # Check all components logged with consistent format
        assert "[INFO]" in content
        assert "TestComponent" in content
        assert "Starting test_work" in content
        assert "Doing work..." in content
        assert "Completed test_work" in content
        assert "TestObserver" in content
        assert "Observer is ready" in content
        assert "DirectLogger" in content
        assert "Direct logger message" in content
        
        # Check format consistency
        lines = [l for l in content.strip().split('\n') if l]
        for line in lines:
            # Each line should follow the format
            assert " [INFO] - " in line
            assert " - " in line
            
        print(f"✅ Logging system verified! {len(lines)} log entries created.")
        print(f"📄 Log file: {log_file}")
        print("📝 Sample log entries:")
        for line in lines[:3]:
            print(f"   {line}")
            

if __name__ == "__main__":
    test_logging_system_works()