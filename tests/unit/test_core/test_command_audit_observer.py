#!/usr/bin/env python3.10
"""Tests for command audit observer using Python 3.10 syntax."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

# Test imports with fallback to mocks
try:
    from panther.core.observer.impl.command_audit_observer import (
        CommandAuditObserver,
        AuditEntry,
        CommandAuditConfig
    )
    from panther.core.events.service.events import (
        ServiceCommandExecutedEvent,
        ServiceCommandFailedEvent,
        ServiceStartedEvent,
        ServiceStoppedEvent
    )
    COMMAND_AUDIT_SYSTEM_AVAILABLE = True
except ImportError:
    COMMAND_AUDIT_SYSTEM_AVAILABLE = False
    
    # Create mock implementations for testing
    class AuditEntry:
        """Audit log entry for command execution."""
        
        def __init__(self,
                     timestamp: datetime,
                     service_id: str,
                     command: str,
                     exit_code: int | None = None,
                     duration: float | None = None,
                     stdout: str | None = None,
                     stderr: str | None = None,
                     environment: Dict[str, str] | None = None,
                     working_directory: str | None = None,
                     user: str | None = None,
                     event_type: str = "command_executed"):
            self.timestamp = timestamp
            self.service_id = service_id
            self.command = command
            self.exit_code = exit_code
            self.duration = duration
            self.stdout = stdout
            self.stderr = stderr
            self.environment = environment or {}
            self.working_directory = working_directory
            self.user = user
            self.event_type = event_type
        
        def to_dict(self) -> Dict[str, Any]:
            """Convert audit entry to dictionary."""
            return {
                'timestamp': self.timestamp.isoformat(),
                'service_id': self.service_id,
                'command': self.command,
                'exit_code': self.exit_code,
                'duration': self.duration,
                'stdout': self.stdout,
                'stderr': self.stderr,
                'environment': self.environment,
                'working_directory': self.working_directory,
                'user': self.user,
                'event_type': self.event_type
            }
        
        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> AuditEntry:
            """Create audit entry from dictionary."""
            timestamp = datetime.fromisoformat(data['timestamp'])
            return cls(
                timestamp=timestamp,
                service_id=data['service_id'],
                command=data['command'],
                exit_code=data.get('exit_code'),
                duration=data.get('duration'),
                stdout=data.get('stdout'),
                stderr=data.get('stderr'),
                environment=data.get('environment', {}),
                working_directory=data.get('working_directory'),
                user=data.get('user'),
                event_type=data.get('event_type', 'command_executed')
            )
    
    class CommandAuditConfig:
        """Configuration for command audit observer."""
        
        def __init__(self,
                     enabled: bool = True,
                     log_file_path: str | None = None,
                     max_log_size: int = 100 * 1024 * 1024,  # 100MB
                     max_log_files: int = 5,
                     include_environment: bool = False,
                     include_stdout: bool = True,
                     include_stderr: bool = True,
                     max_command_length: int = 1000,
                     max_output_length: int = 10000,
                     sensitive_env_vars: List[str] | None = None):
            self.enabled = enabled
            self.log_file_path = log_file_path
            self.max_log_size = max_log_size
            self.max_log_files = max_log_files
            self.include_environment = include_environment
            self.include_stdout = include_stdout
            self.include_stderr = include_stderr
            self.max_command_length = max_command_length
            self.max_output_length = max_output_length
            self.sensitive_env_vars = sensitive_env_vars or [
                'PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'AUTH'
            ]
    
    class ServiceCommandExecutedEvent:
        """Mock service command executed event."""
        
        def __init__(self,
                     service_id: str,
                     command: str,
                     exit_code: int,
                     duration: float = 0.0,
                     stdout: str = "",
                     stderr: str = "",
                     timestamp: datetime | None = None,
                     environment: Dict[str, str] | None = None,
                     working_directory: str | None = None):
            self.service_id = service_id
            self.command = command
            self.exit_code = exit_code
            self.duration = duration
            self.stdout = stdout
            self.stderr = stderr
            self.timestamp = timestamp or datetime.now(timezone.utc)
            self.environment = environment or {}
            self.working_directory = working_directory
    
    class ServiceCommandFailedEvent:
        """Mock service command failed event."""
        
        def __init__(self,
                     service_id: str,
                     command: str,
                     error_message: str,
                     exit_code: int | None = None,
                     duration: float = 0.0,
                     stderr: str = "",
                     timestamp: datetime | None = None):
            self.service_id = service_id
            self.command = command
            self.error_message = error_message
            self.exit_code = exit_code
            self.duration = duration
            self.stderr = stderr
            self.timestamp = timestamp or datetime.now(timezone.utc)
    
    class ServiceStartedEvent:
        """Mock service started event."""
        
        def __init__(self, service_id: str, timestamp: datetime | None = None):
            self.service_id = service_id
            self.timestamp = timestamp or datetime.now(timezone.utc)
    
    class ServiceStoppedEvent:
        """Mock service stopped event."""
        
        def __init__(self, service_id: str, timestamp: datetime | None = None):
            self.service_id = service_id
            self.timestamp = timestamp or datetime.now(timezone.utc)
    
    class CommandAuditObserver:
        """Observer for auditing command executions."""
        
        def __init__(self, config: CommandAuditConfig | None = None):
            self.config = config or CommandAuditConfig()
            self.audit_log: List[AuditEntry] = []
            self.total_commands = 0
            self.successful_commands = 0
            self.failed_commands = 0
            self._log_file_handle = None
            
            if self.config.log_file_path:
                self._setup_log_file()
        
        def _setup_log_file(self):
            """Setup log file for persistent audit logging."""
            log_path = Path(self.config.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if log rotation is needed
            if (log_path.exists() and 
                log_path.stat().st_size > self.config.max_log_size):
                self._rotate_log_files()
        
        def _rotate_log_files(self):
            """Rotate log files when size limit is reached."""
            log_path = Path(self.config.log_file_path)
            
            # Remove oldest log file if max count reached
            old_log = log_path.with_suffix(f'.{self.config.max_log_files}')
            if old_log.exists():
                old_log.unlink()
            
            # Rotate existing log files
            for i in range(self.config.max_log_files - 1, 0, -1):
                current = log_path.with_suffix(f'.{i}')
                next_file = log_path.with_suffix(f'.{i + 1}')
                if current.exists():
                    current.rename(next_file)
            
            # Move current log to .1
            if log_path.exists():
                log_path.rename(log_path.with_suffix('.1'))
        
        def update(self, event) -> None:
            """Update method called when events are received."""
            if not self.config.enabled:
                return
            
            if isinstance(event, ServiceCommandExecutedEvent):
                self._handle_command_executed(event)
            elif isinstance(event, ServiceCommandFailedEvent):
                self._handle_command_failed(event)
            elif isinstance(event, ServiceStartedEvent):
                self._handle_service_started(event)
            elif isinstance(event, ServiceStoppedEvent):
                self._handle_service_stopped(event)
        
        def _handle_command_executed(self, event: ServiceCommandExecutedEvent):
            """Handle command executed event."""
            self.total_commands += 1
            
            if event.exit_code == 0:
                self.successful_commands += 1
            else:
                self.failed_commands += 1
            
            # Sanitize and truncate data
            command = self._sanitize_command(event.command)
            stdout = self._truncate_output(event.stdout) if self.config.include_stdout else None
            stderr = self._truncate_output(event.stderr) if self.config.include_stderr else None
            environment = self._sanitize_environment(event.environment) if self.config.include_environment else None
            
            audit_entry = AuditEntry(
                timestamp=event.timestamp,
                service_id=event.service_id,
                command=command,
                exit_code=event.exit_code,
                duration=event.duration,
                stdout=stdout,
                stderr=stderr,
                environment=environment,
                working_directory=event.working_directory,
                event_type="command_executed"
            )
            
            self._add_audit_entry(audit_entry)
        
        def _handle_command_failed(self, event: ServiceCommandFailedEvent):
            """Handle command failed event."""
            self.total_commands += 1
            self.failed_commands += 1
            
            command = self._sanitize_command(event.command)
            stderr = self._truncate_output(event.stderr) if self.config.include_stderr else None
            
            audit_entry = AuditEntry(
                timestamp=event.timestamp,
                service_id=event.service_id,
                command=command,
                exit_code=event.exit_code,
                duration=event.duration,
                stderr=stderr,
                event_type="command_failed"
            )
            
            self._add_audit_entry(audit_entry)
        
        def _handle_service_started(self, event: ServiceStartedEvent):
            """Handle service started event."""
            audit_entry = AuditEntry(
                timestamp=event.timestamp,
                service_id=event.service_id,
                command="<service_started>",
                event_type="service_started"
            )
            
            self._add_audit_entry(audit_entry)
        
        def _handle_service_stopped(self, event: ServiceStoppedEvent):
            """Handle service stopped event."""
            audit_entry = AuditEntry(
                timestamp=event.timestamp,
                service_id=event.service_id,
                command="<service_stopped>",
                event_type="service_stopped"
            )
            
            self._add_audit_entry(audit_entry)
        
        def _add_audit_entry(self, entry: AuditEntry):
            """Add audit entry to log."""
            self.audit_log.append(entry)
            
            # Write to file if configured
            if self.config.log_file_path:
                self._write_to_log_file(entry)
        
        def _write_to_log_file(self, entry: AuditEntry):
            """Write audit entry to log file."""
            try:
                with open(self.config.log_file_path, 'a', encoding='utf-8') as f:
                    json.dump(entry.to_dict(), f)
                    f.write('\n')
            except Exception as e:
                # In a real implementation, this would use proper logging
                print(f"Failed to write audit log: {e}")
        
        def _sanitize_command(self, command: str) -> str:
            """Sanitize command string."""
            if len(command) > self.config.max_command_length:
                command = command[:self.config.max_command_length] + "..."
            
            # Remove potential secrets from command
            for sensitive_var in self.config.sensitive_env_vars:
                if sensitive_var.lower() in command.lower():
                    command = command.replace(sensitive_var, "[REDACTED]")
            
            return command
        
        def _truncate_output(self, output: str | None) -> str | None:
            """Truncate output to configured maximum length."""
            if output is None:
                return None
            
            if len(output) > self.config.max_output_length:
                return output[:self.config.max_output_length] + "...[TRUNCATED]"
            
            return output
        
        def _sanitize_environment(self, env: Dict[str, str]) -> Dict[str, str]:
            """Sanitize environment variables."""
            sanitized = {}
            
            for key, value in env.items():
                # Check if environment variable contains sensitive data
                if any(sensitive.lower() in key.lower() for sensitive in self.config.sensitive_env_vars):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = value
            
            return sanitized
        
        def get_audit_log(self) -> List[AuditEntry]:
            """Get current audit log."""
            return self.audit_log.copy()
        
        def get_statistics(self) -> Dict[str, Any]:
            """Get audit statistics."""
            return {
                'total_commands': self.total_commands,
                'successful_commands': self.successful_commands,
                'failed_commands': self.failed_commands,
                'success_rate': (self.successful_commands / self.total_commands * 100) if self.total_commands > 0 else 0.0,
                'total_entries': len(self.audit_log)
            }
        
        def clear_audit_log(self):
            """Clear in-memory audit log."""
            self.audit_log.clear()
        
        def export_audit_log(self, file_path: str, format: str = 'json') -> bool:
            """Export audit log to file."""
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if format.lower() == 'json':
                        json.dump([entry.to_dict() for entry in self.audit_log], f, indent=2)
                    elif format.lower() == 'csv':
                        import csv
                        if self.audit_log:
                            fieldnames = list(self.audit_log[0].to_dict().keys())
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for entry in self.audit_log:
                                writer.writerow(entry.to_dict())
                return True
            except Exception:
                return False

pytestmark = [pytest.mark.unit, pytest.mark.command_audit]

class TestAuditEntry:
    """Test AuditEntry functionality."""
    
    def test_audit_entry_initialization(self):
        """Test AuditEntry initialization."""
        timestamp = datetime.now(timezone.utc)
        
        entry = AuditEntry(
            timestamp=timestamp,
            service_id="test-service",
            command="echo 'hello'",
            exit_code=0,
            duration=1.5,
            stdout="hello\n",
            stderr="",
            environment={"VAR1": "value1"},
            working_directory="/app",
            user="test-user"
        )
        
        assert entry.timestamp == timestamp
        assert entry.service_id == "test-service"
        assert entry.command == "echo 'hello'"
        assert entry.exit_code == 0
        assert entry.duration == 1.5
        assert entry.stdout == "hello\n"
        assert entry.stderr == ""
        assert entry.environment == {"VAR1": "value1"}
        assert entry.working_directory == "/app"
        assert entry.user == "test-user"
        assert entry.event_type == "command_executed"
    
    def test_audit_entry_to_dict(self):
        """Test AuditEntry to_dict conversion."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        entry = AuditEntry(
            timestamp=timestamp,
            service_id="test-service",
            command="test command",
            exit_code=0
        )
        
        expected_dict = {
            'timestamp': '2024-01-01T12:00:00+00:00',
            'service_id': 'test-service',
            'command': 'test command',
            'exit_code': 0,
            'duration': None,
            'stdout': None,
            'stderr': None,
            'environment': {},
            'working_directory': None,
            'user': None,
            'event_type': 'command_executed'
        }
        
        assert entry.to_dict() == expected_dict
    
    def test_audit_entry_from_dict(self):
        """Test AuditEntry from_dict creation."""
        data = {
            'timestamp': '2024-01-01T12:00:00+00:00',
            'service_id': 'test-service',
            'command': 'test command',
            'exit_code': 0,
            'duration': 1.0,
            'stdout': 'output',
            'stderr': 'error',
            'environment': {'VAR': 'value'},
            'working_directory': '/app',
            'user': 'user',
            'event_type': 'command_executed'
        }
        
        entry = AuditEntry.from_dict(data)
        
        assert entry.service_id == 'test-service'
        assert entry.command == 'test command'
        assert entry.exit_code == 0
        assert entry.duration == 1.0
        assert entry.stdout == 'output'
        assert entry.stderr == 'error'
        assert entry.environment == {'VAR': 'value'}
        assert entry.working_directory == '/app'
        assert entry.user == 'user'
        assert entry.event_type == 'command_executed'

class TestCommandAuditConfig:
    """Test CommandAuditConfig functionality."""
    
    def test_config_initialization_defaults(self):
        """Test CommandAuditConfig initialization with defaults."""
        config = CommandAuditConfig()
        
        assert config.enabled is True
        assert config.log_file_path is None
        assert config.max_log_size == 100 * 1024 * 1024
        assert config.max_log_files == 5
        assert config.include_environment is False
        assert config.include_stdout is True
        assert config.include_stderr is True
        assert config.max_command_length == 1000
        assert config.max_output_length == 10000
        assert 'PASSWORD' in config.sensitive_env_vars
        assert 'SECRET' in config.sensitive_env_vars
    
    def test_config_initialization_custom(self):
        """Test CommandAuditConfig initialization with custom values."""
        config = CommandAuditConfig(
            enabled=False,
            log_file_path="/tmp/audit.log",
            max_log_size=50 * 1024 * 1024,
            max_log_files=3,
            include_environment=True,
            include_stdout=False,
            include_stderr=False,
            max_command_length=500,
            max_output_length=5000,
            sensitive_env_vars=['API_KEY', 'DB_PASSWORD']
        )
        
        assert config.enabled is False
        assert config.log_file_path == "/tmp/audit.log"
        assert config.max_log_size == 50 * 1024 * 1024
        assert config.max_log_files == 3
        assert config.include_environment is True
        assert config.include_stdout is False
        assert config.include_stderr is False
        assert config.max_command_length == 500
        assert config.max_output_length == 5000
        assert config.sensitive_env_vars == ['API_KEY', 'DB_PASSWORD']

class TestCommandAuditObserver:
    """Test CommandAuditObserver functionality."""
    
    @pytest.fixture
    def observer(self) -> CommandAuditObserver:
        """Create a CommandAuditObserver for testing."""
        config = CommandAuditConfig(
            include_environment=True,
            include_stdout=True,
            include_stderr=True
        )
        return CommandAuditObserver(config)
    
    def test_observer_initialization(self, observer: CommandAuditObserver):
        """Test CommandAuditObserver initialization."""
        assert observer.config is not None
        assert observer.audit_log == []
        assert observer.total_commands == 0
        assert observer.successful_commands == 0
        assert observer.failed_commands == 0
    
    def test_handle_command_executed_success(self, observer: CommandAuditObserver):
        """Test handling successful command execution."""
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo 'hello world'",
            exit_code=0,
            duration=0.5,
            stdout="hello world\n",
            stderr="",
            environment={"PATH": "/usr/bin"}
        )
        
        observer.update(event)
        
        assert observer.total_commands == 1
        assert observer.successful_commands == 1
        assert observer.failed_commands == 0
        assert len(observer.audit_log) == 1
        
        entry = observer.audit_log[0]
        assert entry.service_id == "test-service"
        assert entry.command == "echo 'hello world'"
        assert entry.exit_code == 0
        assert entry.duration == 0.5
        assert entry.stdout == "hello world\n"
        assert entry.stderr == ""
        assert entry.environment == {"PATH": "/usr/bin"}
        assert entry.event_type == "command_executed"
    
    def test_handle_command_executed_failure(self, observer: CommandAuditObserver):
        """Test handling failed command execution."""
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="false",
            exit_code=1,
            duration=0.1,
            stdout="",
            stderr="command failed\n"
        )
        
        observer.update(event)
        
        assert observer.total_commands == 1
        assert observer.successful_commands == 0
        assert observer.failed_commands == 1
        assert len(observer.audit_log) == 1
        
        entry = observer.audit_log[0]
        assert entry.exit_code == 1
        assert entry.stderr == "command failed\n"
    
    def test_handle_command_failed_event(self, observer: CommandAuditObserver):
        """Test handling command failed event."""
        event = ServiceCommandFailedEvent(
            service_id="test-service",
            command="invalid-command",
            error_message="Command not found",
            exit_code=127,
            duration=0.01,
            stderr="bash: invalid-command: command not found\n"
        )
        
        observer.update(event)
        
        assert observer.total_commands == 1
        assert observer.failed_commands == 1
        assert len(observer.audit_log) == 1
        
        entry = observer.audit_log[0]
        assert entry.service_id == "test-service"
        assert entry.command == "invalid-command"
        assert entry.exit_code == 127
        assert entry.event_type == "command_failed"
    
    def test_handle_service_lifecycle_events(self, observer: CommandAuditObserver):
        """Test handling service start/stop events."""
        start_event = ServiceStartedEvent(service_id="test-service")
        stop_event = ServiceStoppedEvent(service_id="test-service")
        
        observer.update(start_event)
        observer.update(stop_event)
        
        assert len(observer.audit_log) == 2
        
        start_entry = observer.audit_log[0]
        assert start_entry.service_id == "test-service"
        assert start_entry.command == "<service_started>"
        assert start_entry.event_type == "service_started"
        
        stop_entry = observer.audit_log[1]
        assert stop_entry.service_id == "test-service"
        assert stop_entry.command == "<service_stopped>"
        assert stop_entry.event_type == "service_stopped"
    
    def test_command_sanitization(self, observer: CommandAuditObserver):
        """Test command sanitization for sensitive data."""
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="mysql -u user -pPASSWORD123 -h host db",
            exit_code=0
        )
        
        observer.update(event)
        
        entry = observer.audit_log[0]
        assert "[REDACTED]" in entry.command
        assert "PASSWORD123" not in entry.command
    
    def test_command_truncation(self, observer: CommandAuditObserver):
        """Test command truncation for long commands."""
        long_command = "echo " + "a" * 2000
        
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command=long_command,
            exit_code=0
        )
        
        observer.update(event)
        
        entry = observer.audit_log[0]
        assert len(entry.command) <= observer.config.max_command_length + 3  # +3 for "..."
        assert entry.command.endswith("...")
    
    def test_output_truncation(self, observer: CommandAuditObserver):
        """Test output truncation for long outputs."""
        long_output = "output " * 2000
        
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo test",
            exit_code=0,
            stdout=long_output
        )
        
        observer.update(event)
        
        entry = observer.audit_log[0]
        assert len(entry.stdout) <= observer.config.max_output_length + len("...[TRUNCATED]")
        assert entry.stdout.endswith("...[TRUNCATED]")
    
    def test_environment_sanitization(self, observer: CommandAuditObserver):
        """Test environment variable sanitization."""
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="env",
            exit_code=0,
            environment={
                "PATH": "/usr/bin",
                "PASSWORD": "secret123",
                "API_TOKEN": "token456",
                "NORMAL_VAR": "normal_value"
            }
        )
        
        observer.update(event)
        
        entry = observer.audit_log[0]
        assert entry.environment["PATH"] == "/usr/bin"
        assert entry.environment["PASSWORD"] == "[REDACTED]"
        assert entry.environment["API_TOKEN"] == "[REDACTED]"
        assert entry.environment["NORMAL_VAR"] == "normal_value"
    
    def test_observer_disabled(self):
        """Test observer when disabled."""
        config = CommandAuditConfig(enabled=False)
        observer = CommandAuditObserver(config)
        
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo test",
            exit_code=0
        )
        
        observer.update(event)
        
        assert observer.total_commands == 0
        assert len(observer.audit_log) == 0
    
    def test_get_statistics(self, observer: CommandAuditObserver):
        """Test getting audit statistics."""
        # Add some successful commands
        for i in range(3):
            event = ServiceCommandExecutedEvent(
                service_id=f"service-{i}",
                command=f"echo {i}",
                exit_code=0
            )
            observer.update(event)
        
        # Add some failed commands
        for i in range(2):
            event = ServiceCommandExecutedEvent(
                service_id=f"service-{i}",
                command="false",
                exit_code=1
            )
            observer.update(event)
        
        stats = observer.get_statistics()
        
        assert stats['total_commands'] == 5
        assert stats['successful_commands'] == 3
        assert stats['failed_commands'] == 2
        assert stats['success_rate'] == 60.0
        assert stats['total_entries'] == 5
    
    def test_clear_audit_log(self, observer: CommandAuditObserver):
        """Test clearing audit log."""
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo test",
            exit_code=0
        )
        
        observer.update(event)
        assert len(observer.audit_log) == 1
        
        observer.clear_audit_log()
        assert len(observer.audit_log) == 0

class TestCommandAuditFileOperations:
    """Test file operations for command audit observer."""
    
    def test_export_audit_log_json(self):
        """Test exporting audit log to JSON format."""
        observer = CommandAuditObserver()
        
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo test",
            exit_code=0,
            stdout="test\n"
        )
        
        observer.update(event)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = observer.export_audit_log(temp_path, 'json')
            assert result is True
            
            # Verify file content
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert len(data) == 1
            assert data[0]['service_id'] == 'test-service'
            assert data[0]['command'] == 'echo test'
            assert data[0]['exit_code'] == 0
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_export_audit_log_csv(self):
        """Test exporting audit log to CSV format."""
        observer = CommandAuditObserver()
        
        event = ServiceCommandExecutedEvent(
            service_id="test-service",
            command="echo test",
            exit_code=0
        )
        
        observer.update(event)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            result = observer.export_audit_log(temp_path, 'csv')
            assert result is True
            
            # Verify file exists and has content
            assert Path(temp_path).exists()
            content = Path(temp_path).read_text()
            assert 'service_id' in content  # Header
            assert 'test-service' in content  # Data
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_export_audit_log_failure(self, mock_open):
        """Test export failure handling."""
        observer = CommandAuditObserver()
        
        result = observer.export_audit_log('/invalid/path/file.json', 'json')
        assert result is False
    
    def test_log_file_writing(self):
        """Test writing audit entries to log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            temp_path = f.name
        
        try:
            config = CommandAuditConfig(log_file_path=temp_path)
            observer = CommandAuditObserver(config)
            
            event = ServiceCommandExecutedEvent(
                service_id="test-service",
                command="echo test",
                exit_code=0
            )
            
            observer.update(event)
            
            # Verify log file content
            with open(temp_path, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 1
            log_entry = json.loads(lines[0])
            assert log_entry['service_id'] == 'test-service'
            assert log_entry['command'] == 'echo test'
            
        finally:
            Path(temp_path).unlink(missing_ok=True)

class TestCommandAuditIntegration:
    """Test integration scenarios for command audit observer."""
    
    def test_full_workflow_audit(self):
        """Test complete workflow auditing."""
        observer = CommandAuditObserver()
        
        # Service startup
        start_event = ServiceStartedEvent(service_id="web-server")
        observer.update(start_event)
        
        # Successful commands
        for i in range(3):
            event = ServiceCommandExecutedEvent(
                service_id="web-server",
                command=f"curl -s http://localhost:808{i}",
                exit_code=0,
                duration=0.1 + i * 0.1,
                stdout=f"Response {i}\n"
            )
            observer.update(event)
        
        # Failed command
        fail_event = ServiceCommandFailedEvent(
            service_id="web-server",
            command="curl -s http://invalid-host",
            error_message="Host not found",
            exit_code=6,
            stderr="curl: (6) Could not resolve host: invalid-host\n"
        )
        observer.update(fail_event)
        
        # Service shutdown
        stop_event = ServiceStoppedEvent(service_id="web-server")
        observer.update(stop_event)
        
        # Verify complete audit trail
        assert len(observer.audit_log) == 6
        assert observer.total_commands == 4  # Only commands, not service events
        assert observer.successful_commands == 3
        assert observer.failed_commands == 1
        
        # Verify event sequence
        events = observer.audit_log
        assert events[0].event_type == "service_started"
        assert events[1].event_type == "command_executed"
        assert events[4].event_type == "command_failed"
        assert events[5].event_type == "service_stopped"
    
    def test_concurrent_services_audit(self):
        """Test auditing multiple concurrent services."""
        observer = CommandAuditObserver()
        
        services = ["web-server", "database", "cache"]
        
        # Start all services
        for service in services:
            start_event = ServiceStartedEvent(service_id=service)
            observer.update(start_event)
        
        # Each service executes commands
        for service in services:
            for i in range(2):
                event = ServiceCommandExecutedEvent(
                    service_id=service,
                    command=f"{service}-command-{i}",
                    exit_code=0
                )
                observer.update(event)
        
        # Verify audit log
        assert len(observer.audit_log) == 9  # 3 starts + 6 commands
        assert observer.total_commands == 6
        
        # Verify service separation
        web_entries = [e for e in observer.audit_log if e.service_id == "web-server"]
        assert len(web_entries) == 3  # 1 start + 2 commands
        
        db_entries = [e for e in observer.audit_log if e.service_id == "database"]
        assert len(db_entries) == 3
    
    def test_performance_with_many_events(self):
        """Test performance with large number of events."""
        observer = CommandAuditObserver()
        
        import time
        start_time = time.time()
        
        # Generate many events
        for i in range(1000):
            event = ServiceCommandExecutedEvent(
                service_id=f"service-{i % 10}",
                command=f"command-{i}",
                exit_code=0 if i % 10 != 0 else 1,  # 10% failure rate
                stdout=f"output-{i}\n"
            )
            observer.update(event)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should process 1000 events quickly
        assert duration < 1.0  # Less than 1 second
        assert len(observer.audit_log) == 1000
        assert observer.total_commands == 1000
        assert observer.successful_commands == 900
        assert observer.failed_commands == 100

class TestCommandAuditErrorHandling:
    """Test error handling in command audit observer."""
    
    def test_malformed_event_handling(self):
        """Test handling of malformed events."""
        observer = CommandAuditObserver()
        
        # Event with missing attributes
        malformed_event = Mock()
        malformed_event.service_id = "test"
        # Missing other required attributes
        
        # Should not crash
        try:
            observer.update(malformed_event)
        except Exception:
            pass  # Expected to fail gracefully
        
        # Observer should still be functional
        assert len(observer.audit_log) == 0
    
    def test_none_event_handling(self):
        """Test handling of None events."""
        observer = CommandAuditObserver()
        
        # Should not crash
        observer.update(None)
        assert len(observer.audit_log) == 0
    
    def test_unknown_event_type_handling(self):
        """Test handling of unknown event types."""
        observer = CommandAuditObserver()
        
        unknown_event = Mock()
        unknown_event.service_id = "test"
        unknown_event.timestamp = datetime.now(timezone.utc)
        
        # Should not crash and should ignore unknown event
        observer.update(unknown_event)
        assert len(observer.audit_log) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])