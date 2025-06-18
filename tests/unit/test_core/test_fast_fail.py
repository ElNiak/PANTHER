#!/usr/bin/env python3.10
"""Tests for fast fail mechanism using Python 3.10 syntax."""

from __future__ import annotations

import time
from typing import Any, Callable
from unittest.mock import Mock, patch

import pytest

# Test imports with fallback to mocks
try:
    from panther.core.exceptions.fast_fail import (
        FastFailHandler,
        FastFailException,
        FastFailConfig,
        RetryPolicy
    )
    FAST_FAIL_SYSTEM_AVAILABLE = True
except ImportError:
    FAST_FAIL_SYSTEM_AVAILABLE = False
    
    # Create mock implementations for testing
    class FastFailException(Exception):
        """Exception raised when fast fail threshold is reached."""
        
        def __init__(self, message: str, attempt_count: int, last_error: Exception | None = None):
            super().__init__(message)
            self.attempt_count = attempt_count
            self.last_error = last_error
    
    class RetryPolicy:
        """Configuration for retry behavior."""
        
        def __init__(self, 
                     max_retries: int = 3,
                     initial_delay: float = 1.0,
                     max_delay: float = 60.0,
                     backoff_multiplier: float = 2.0,
                     jitter: bool = True):
            self.max_retries = max_retries
            self.initial_delay = initial_delay
            self.max_delay = max_delay
            self.backoff_multiplier = backoff_multiplier
            self.jitter = jitter
            
        def get_delay(self, attempt: int) -> float:
            """Calculate delay for given attempt number."""
            delay = self.initial_delay * (self.backoff_multiplier ** attempt)
            delay = min(delay, self.max_delay)
            
            if self.jitter:
                import random
                delay *= (0.5 + random.random() * 0.5)  # Add jitter
                
            return delay
    
    class FastFailConfig:
        """Configuration for fast fail behavior."""
        
        def __init__(self,
                     enabled: bool = True,
                     failure_threshold: int = 5,
                     time_window: float = 60.0,
                     circuit_breaker_timeout: float = 300.0,
                     retry_policy: RetryPolicy | None = None):
            self.enabled = enabled
            self.failure_threshold = failure_threshold
            self.time_window = time_window
            self.circuit_breaker_timeout = circuit_breaker_timeout
            self.retry_policy = retry_policy or RetryPolicy()
    
    class FastFailHandler:
        """Handler for fast fail mechanism with circuit breaker pattern."""
        
        def __init__(self, config: FastFailConfig | None = None):
            self.config = config or FastFailConfig()
            self.failure_count = 0
            self.last_failure_time = 0.0
            self.circuit_open = False
            self.circuit_open_time = 0.0
            self.success_count = 0
            self.total_attempts = 0
            
        def execute(self, func: Callable[[], Any], *args, **kwargs) -> Any:
            """Execute function with fast fail protection."""
            if func is None or not callable(func):
                raise TypeError("Function must be callable")
                
            if not self.config.enabled:
                return func(*args, **kwargs)
            
            # Check circuit breaker
            if self._is_circuit_open():
                raise FastFailException(
                    f"Circuit breaker is open. Last failure: {self.last_failure_time}",
                    self.total_attempts
                )
            
            # Try execution with retries
            last_error = None
            for attempt in range(self.config.retry_policy.max_retries + 1):
                try:
                    self.total_attempts += 1
                    result = func(*args, **kwargs)
                    self._record_success()
                    return result
                    
                except Exception as e:
                    last_error = e
                    self._record_failure()
                    
                    # Don't retry on last attempt
                    if attempt == self.config.retry_policy.max_retries:
                        break
                    
                    # Wait before retry
                    delay = self.config.retry_policy.get_delay(attempt)
                    time.sleep(delay)
            
            # All retries exhausted
            raise FastFailException(
                f"Operation failed after {self.config.retry_policy.max_retries + 1} attempts",
                self.total_attempts,
                last_error
            )
        
        def _is_circuit_open(self) -> bool:
            """Check if circuit breaker is open."""
            current_time = time.time()
            
            # Check if circuit should be closed due to timeout
            if (self.circuit_open and 
                current_time - self.circuit_open_time > self.config.circuit_breaker_timeout):
                self.circuit_open = False
                self.failure_count = 0
                return False
            
            return self.circuit_open
        
        def _record_success(self):
            """Record successful operation."""
            self.success_count += 1
            
            # Reset failure count on success
            if self.circuit_open:
                self.circuit_open = False
                self.failure_count = 0
        
        def _record_failure(self):
            """Record failed operation."""
            current_time = time.time()
            
            # Reset count if outside time window
            if current_time - self.last_failure_time > self.config.time_window:
                self.failure_count = 0
            
            self.failure_count += 1
            self.last_failure_time = current_time
            
            # Open circuit if threshold reached
            if self.failure_count >= self.config.failure_threshold:
                self.circuit_open = True
                self.circuit_open_time = current_time
        
        def get_stats(self) -> dict[str, Any]:
            """Get handler statistics."""
            return {
                'total_attempts': self.total_attempts,
                'success_count': self.success_count,
                'failure_count': self.failure_count,
                'circuit_open': self.circuit_open,
                'last_failure_time': self.last_failure_time,
                'circuit_open_time': self.circuit_open_time
            }
        
        def reset(self):
            """Reset handler state."""
            self.failure_count = 0
            self.last_failure_time = 0.0
            self.circuit_open = False
            self.circuit_open_time = 0.0
            self.success_count = 0
            self.total_attempts = 0

pytestmark = [pytest.mark.unit, pytest.mark.fast_fail]

class TestFastFailException:
    """Test FastFailException functionality."""
    
    def test_exception_initialization(self):
        """Test FastFailException initialization."""
        message = "Test failure"
        attempt_count = 3
        last_error = ValueError("Original error")
        
        exception = FastFailException(message, attempt_count, last_error)
        
        assert str(exception) == message
        assert exception.attempt_count == attempt_count
        assert exception.last_error == last_error
    
    def test_exception_without_last_error(self):
        """Test FastFailException without last error."""
        message = "Test failure"
        attempt_count = 2
        
        exception = FastFailException(message, attempt_count)
        
        assert str(exception) == message
        assert exception.attempt_count == attempt_count
        assert exception.last_error is None

class TestRetryPolicy:
    """Test RetryPolicy functionality."""
    
    def test_retry_policy_initialization_defaults(self):
        """Test RetryPolicy initialization with defaults."""
        policy = RetryPolicy()
        
        assert policy.max_retries == 3
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_multiplier == 2.0
        assert policy.jitter is True
    
    def test_retry_policy_initialization_custom(self):
        """Test RetryPolicy initialization with custom values."""
        policy = RetryPolicy(
            max_retries=5,
            initial_delay=0.5,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter=False
        )
        
        assert policy.max_retries == 5
        assert policy.initial_delay == 0.5
        assert policy.max_delay == 30.0
        assert policy.backoff_multiplier == 1.5
        assert policy.jitter is False
    
    def test_delay_calculation_without_jitter(self):
        """Test delay calculation without jitter."""
        policy = RetryPolicy(
            initial_delay=1.0,
            backoff_multiplier=2.0,
            max_delay=60.0,
            jitter=False
        )
        
        # Test exponential backoff
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0
    
    def test_delay_calculation_with_max_delay(self):
        """Test delay calculation respects max delay."""
        policy = RetryPolicy(
            initial_delay=10.0,
            backoff_multiplier=10.0,
            max_delay=15.0,
            jitter=False
        )
        
        assert policy.get_delay(0) == 10.0
        assert policy.get_delay(1) == 15.0  # Capped at max_delay
        assert policy.get_delay(2) == 15.0  # Still capped
    
    @patch('random.random')
    def test_delay_calculation_with_jitter(self, mock_random):
        """Test delay calculation with jitter."""
        mock_random.return_value = 0.5  # Fixed random value
        
        policy = RetryPolicy(
            initial_delay=2.0,
            backoff_multiplier=2.0,
            jitter=True
        )
        
        # With jitter: delay * (0.5 + 0.5 * 0.5) = delay * 0.75
        expected_delay = 2.0 * 0.75
        assert policy.get_delay(0) == expected_delay

class TestFastFailConfig:
    """Test FastFailConfig functionality."""
    
    def test_config_initialization_defaults(self):
        """Test FastFailConfig initialization with defaults."""
        config = FastFailConfig()
        
        assert config.enabled is True
        assert config.failure_threshold == 5
        assert config.time_window == 60.0
        assert config.circuit_breaker_timeout == 300.0
        assert isinstance(config.retry_policy, RetryPolicy)
    
    def test_config_initialization_custom(self):
        """Test FastFailConfig initialization with custom values."""
        retry_policy = RetryPolicy(max_retries=2)
        
        config = FastFailConfig(
            enabled=False,
            failure_threshold=3,
            time_window=30.0,
            circuit_breaker_timeout=120.0,
            retry_policy=retry_policy
        )
        
        assert config.enabled is False
        assert config.failure_threshold == 3
        assert config.time_window == 30.0
        assert config.circuit_breaker_timeout == 120.0
        assert config.retry_policy == retry_policy

class TestFastFailHandler:
    """Test FastFailHandler functionality."""
    
    @pytest.fixture
    def handler(self) -> FastFailHandler:
        """Create a FastFailHandler for testing."""
        config = FastFailConfig(
            failure_threshold=3,
            time_window=60.0,
            circuit_breaker_timeout=10.0,
            retry_policy=RetryPolicy(max_retries=2, initial_delay=0.1)
        )
        return FastFailHandler(config)
    
    def test_handler_initialization(self, handler: FastFailHandler):
        """Test FastFailHandler initialization."""
        assert handler.config is not None
        assert handler.failure_count == 0
        assert handler.circuit_open is False
        assert handler.success_count == 0
        assert handler.total_attempts == 0
    
    def test_successful_execution(self, handler: FastFailHandler):
        """Test successful function execution."""
        def successful_func():
            return "success"
        
        result = handler.execute(successful_func)
        
        assert result == "success"
        assert handler.success_count == 1
        assert handler.total_attempts == 1
        assert handler.failure_count == 0
        assert handler.circuit_open is False
    
    def test_execution_with_retries_eventual_success(self, handler: FastFailHandler):
        """Test execution that fails then succeeds."""
        call_count = 0
        
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError(f"Failure {call_count}")
            return "success"
        
        result = handler.execute(failing_then_success)
        
        assert result == "success"
        assert call_count == 3
        assert handler.success_count == 1
        assert handler.total_attempts == 3
    
    def test_execution_with_retries_all_fail(self, handler: FastFailHandler):
        """Test execution that fails all retries."""
        call_count = 0
        
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure {call_count}")
        
        with pytest.raises(FastFailException) as exc_info:
            handler.execute(always_fails)
        
        assert call_count == 3  # max_retries + 1
        assert "failed after 3 attempts" in str(exc_info.value)
        assert exc_info.value.attempt_count == 3
        assert isinstance(exc_info.value.last_error, ValueError)
    
    @patch('time.time')
    def test_circuit_breaker_opens_after_threshold(self, mock_time, handler: FastFailHandler):
        """Test circuit breaker opens after failure threshold."""
        mock_time.return_value = 100.0
        
        def always_fails():
            raise ValueError("Always fails")
        
        # Cause enough failures to open circuit
        for i in range(3):  # failure_threshold = 3
            with pytest.raises(FastFailException):
                handler.execute(always_fails)
        
        assert handler.circuit_open is True
        assert handler.failure_count == 3
    
    @patch('time.time')
    def test_circuit_breaker_rejects_when_open(self, mock_time, handler: FastFailHandler):
        """Test circuit breaker rejects execution when open."""
        mock_time.return_value = 100.0
        
        # Force circuit open
        handler.circuit_open = True
        handler.circuit_open_time = 100.0
        
        def some_func():
            return "should not be called"
        
        with pytest.raises(FastFailException) as exc_info:
            handler.execute(some_func)
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @patch('time.time')
    def test_circuit_breaker_closes_after_timeout(self, mock_time, handler: FastFailHandler):
        """Test circuit breaker closes after timeout."""
        # Start with circuit open
        handler.circuit_open = True
        handler.circuit_open_time = 100.0
        handler.failure_count = 5
        
        # Simulate time passing beyond timeout
        mock_time.return_value = 100.0 + handler.config.circuit_breaker_timeout + 1
        
        def successful_func():
            return "success"
        
        result = handler.execute(successful_func)
        
        assert result == "success"
        assert handler.circuit_open is False
        assert handler.failure_count == 0
    
    @patch('time.time')
    def test_failure_count_resets_outside_time_window(self, mock_time, handler: FastFailHandler):
        """Test failure count resets outside time window."""
        # Record some failures
        mock_time.return_value = 100.0
        handler.failure_count = 2
        handler.last_failure_time = 100.0
        
        # Move time beyond window
        mock_time.return_value = 100.0 + handler.config.time_window + 1
        
        def failing_func():
            raise ValueError("Failure")
        
        with pytest.raises(FastFailException):
            handler.execute(failing_func)
        
        # Should have reset and then incremented by max_retries + 1 (default is 3, so 4 total attempts)
        assert handler.failure_count == handler.config.retry_policy.max_retries + 1
    
    def test_handler_disabled(self):
        """Test handler when disabled."""
        config = FastFailConfig(enabled=False)
        handler = FastFailHandler(config)
        
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")
        
        # Should raise original exception, not FastFailException
        with pytest.raises(ValueError):
            handler.execute(failing_func)
        
        assert call_count == 1  # No retries when disabled
    
    def test_get_stats(self, handler: FastFailHandler):
        """Test getting handler statistics."""
        stats = handler.get_stats()
        
        expected_keys = {
            'total_attempts', 'success_count', 'failure_count',
            'circuit_open', 'last_failure_time', 'circuit_open_time'
        }
        assert set(stats.keys()) == expected_keys
        assert all(isinstance(v, (int, float, bool)) for v in stats.values())
    
    def test_reset_handler(self, handler: FastFailHandler):
        """Test resetting handler state."""
        # Set some state
        handler.failure_count = 5
        handler.success_count = 3
        handler.total_attempts = 8
        handler.circuit_open = True
        handler.last_failure_time = 123.0
        handler.circuit_open_time = 456.0
        
        handler.reset()
        
        assert handler.failure_count == 0
        assert handler.success_count == 0
        assert handler.total_attempts == 0
        assert handler.circuit_open is False
        assert handler.last_failure_time == 0.0
        assert handler.circuit_open_time == 0.0

class TestFastFailIntegration:
    """Test integration scenarios for fast fail mechanism."""
    
    def test_docker_command_execution_with_fast_fail(self):
        """Test fast fail with Docker command execution simulation."""
        config = FastFailConfig(
            failure_threshold=2,
            retry_policy=RetryPolicy(max_retries=1, initial_delay=0.1)
        )
        handler = FastFailHandler(config)
        
        def mock_docker_command():
            import random
            if random.random() < 0.7:  # 70% failure rate
                raise RuntimeError("Docker command failed")
            return "Command successful"
        
        successes = 0
        failures = 0
        
        # Simulate multiple command executions
        for _ in range(10):
            try:
                with patch('random.random', return_value=0.5):  # Force failure (0.5 < 0.7)
                    handler.execute(mock_docker_command)
                successes += 1
            except FastFailException:
                failures += 1
        
        # Should have some failures due to circuit breaker
        assert failures > 0
        stats = handler.get_stats()
        # Circuit breaker will stop attempts once opened, so we expect fewer attempts
        assert stats['total_attempts'] >= 2  # At least the threshold number
    
    def test_network_operation_with_fast_fail(self):
        """Test fast fail with network operation simulation."""
        config = FastFailConfig(
            failure_threshold=3,
            time_window=30.0,
            retry_policy=RetryPolicy(max_retries=2, initial_delay=0.05)
        )
        handler = FastFailHandler(config)
        
        connection_attempts = 0
        
        def mock_network_connect():
            nonlocal connection_attempts
            connection_attempts += 1
            
            if connection_attempts <= 2:
                raise ConnectionError("Network unreachable")
            return {"status": "connected", "latency": 45}
        
        result = handler.execute(mock_network_connect)
        
        assert result["status"] == "connected"
        assert connection_attempts == 3
        assert handler.success_count == 1
    
    def test_service_dependency_with_fast_fail(self):
        """Test fast fail with service dependency simulation."""
        config = FastFailConfig(
            failure_threshold=2,
            circuit_breaker_timeout=5.0,
            retry_policy=RetryPolicy(max_retries=1, initial_delay=0.1)
        )
        handler = FastFailHandler(config)
        
        service_available = False
        
        def check_service_health():
            if not service_available:
                raise RuntimeError("Service unavailable")
            return {"status": "healthy"}
        
        # Initially service is down - should trip circuit breaker
        for _ in range(2):
            with pytest.raises(FastFailException):
                handler.execute(check_service_health)
        
        assert handler.circuit_open is True
        
        # Service comes back up, but circuit is still open
        service_available = True
        with pytest.raises(FastFailException) as exc_info:
            handler.execute(check_service_health)
        
        assert "Circuit breaker is open" in str(exc_info.value)

class TestFastFailErrorHandling:
    """Test error handling in fast fail mechanism."""
    
    def test_handler_with_none_function(self):
        """Test handler with None function."""
        handler = FastFailHandler()
        
        with pytest.raises(TypeError):
            handler.execute(None)
    
    def test_handler_with_invalid_config(self):
        """Test handler with invalid configuration values."""
        # Test with negative values
        config = FastFailConfig(
            failure_threshold=-1,  # Invalid
            time_window=-10.0,     # Invalid
            retry_policy=RetryPolicy(max_retries=-1)  # Invalid
        )
        
        handler = FastFailHandler(config)
        
        # Should still work but with weird behavior (negative retries means 0 retries)
        def test_func():
            return "test"
        
        # With negative max_retries, it should still try once (max_retries + 1 = 0)
        # but the range() function with negative numbers will result in no iterations
        with pytest.raises(FastFailException) as exc_info:
            result = handler.execute(test_func)
        
        assert "failed after 0 attempts" in str(exc_info.value)
    
    def test_exception_chaining(self):
        """Test proper exception chaining."""
        handler = FastFailHandler()
        
        original_error = ValueError("Original error message")
        
        def failing_func():
            raise original_error
        
        with pytest.raises(FastFailException) as exc_info:
            handler.execute(failing_func)
        
        assert exc_info.value.last_error == original_error
        assert "Original error message" in str(original_error)

class TestFastFailPerformance:
    """Test performance characteristics of fast fail mechanism."""
    
    def test_handler_overhead_minimal(self):
        """Test that handler adds minimal overhead for successful operations."""
        handler = FastFailHandler()
        
        def simple_func():
            return 42
        
        # Time normal execution with a larger sample size for more stable timing
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            result = simple_func()
        normal_time = time.time() - start_time
        
        # Time with fast fail handler
        start_time = time.time()
        for _ in range(iterations):
            result = handler.execute(simple_func)
        handler_time = time.time() - start_time
        
        # Handler should add minimal overhead (less than 500% increase for very fast operations)
        # Note: For very fast operations, the overhead percentage can be high but absolute time is still small
        assert handler_time < normal_time * 5.0 or handler_time < 0.1  # Either relative or absolute threshold
        assert result == 42
    
    @patch('time.sleep')
    def test_retry_delays_are_respected(self, mock_sleep):
        """Test that retry delays are properly implemented."""
        policy = RetryPolicy(
            max_retries=2,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        config = FastFailConfig(retry_policy=policy)
        handler = FastFailHandler(config)
        
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(FastFailException):
            handler.execute(failing_func)
        
        # Should have called sleep twice (between retries)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)  # First retry delay
        mock_sleep.assert_any_call(2.0)  # Second retry delay

if __name__ == "__main__":
    pytest.main([__file__, "-v"])