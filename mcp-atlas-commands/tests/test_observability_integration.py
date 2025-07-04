#!/usr/bin/env python3
"""
Comprehensive integration tests for ATLAS MCP Observability System.

This test suite validates the complete observability stack:
- OpenTelemetry distributed tracing
- Metrics collection (with fallback)
- Structured logging with trace correlation
- Error handling and health monitoring
- Graceful degradation when OpenTelemetry unavailable
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from atlas_commands.observability.manager import ObservabilityManager
from atlas_commands.observability.metrics import Metrics, MetricsCollector
from atlas_commands.observability.logging import get_logger, setup_structured_logging
from atlas_commands.observability.tracing import trace_mcp_tool, trace_cache_operation, trace_task_operation


def test_basic_initialization():
    """Test basic component initialization."""
    print("🔧 Testing basic initialization...")
    
    # Initialize components
    obs_manager = ObservabilityManager('atlas-mcp-test', '1.0.0')
    metrics = Metrics('atlas-mcp-test')
    logger = get_logger('atlas_commands.test')
    
    assert obs_manager is not None
    assert metrics is not None
    assert logger is not None
    
    print("  ✓ All components initialized successfully")
    return obs_manager, metrics, logger


def test_metrics_collection(metrics):
    """Test comprehensive metrics collection."""
    print("📊 Testing metrics collection...")
    
    # Test all metric types
    metrics.record_tool_call('create_task', 0.15, True, {'project': 'TEST'})
    metrics.record_tool_call('list_tasks', 0.05, True)
    metrics.record_tool_call('invalid_tool', 0.02, False)  # Failed call
    
    metrics.record_cache_operation('get', 'tasks', 0.001, hit=True, size=256)
    metrics.record_cache_operation('get', 'tasks', 0.001, hit=False)
    metrics.record_cache_operation('set', 'tasks', 0.002, size=512)
    metrics.record_cache_operation('invalidate', 'tasks', 0.001)
    
    metrics.record_task_operation('create', 'TEST', 0.1, 'task_01', 'active')
    metrics.record_task_operation('update', 'TEST', 0.05, 'task_01', 'completed')
    metrics.record_task_operation('list', 'TEST', 0.03)
    
    metrics.update_active_tasks('TEST', 1)
    metrics.update_active_tasks('PROD', 2)
    metrics.update_cache_size('tasks', 15)
    metrics.update_cache_size('artifacts', 8)
    
    metrics.record_error('ValidationError', 'task_storage', 'Invalid task ID')
    metrics.record_error('NetworkError', 'cache', 'Redis connection failed')
    
    fallback_metrics = metrics.get_fallback_metrics()
    assert len(fallback_metrics) > 0
    
    print(f"  ✓ Recorded {len(fallback_metrics)} metrics successfully")
    return fallback_metrics


def test_structured_logging(logger):
    """Test structured logging with trace correlation."""
    print("📝 Testing structured logging...")
    
    # Test different log levels
    logger.debug("Debug message", component='test', operation='debug_test')
    logger.info("Info message", component='test', user_id='test_user')
    logger.warning("Warning message", component='test', error_code='WARN_001')
    logger.error("Error message", component='test', error_type='TestError')
    
    # Test domain-specific logging methods
    logger.log_tool_call('test_tool', {'param1': 'value1', 'param2': 42}, 0.123)
    logger.log_cache_operation('get', 'test_cache', 'key_123', hit=True)
    logger.log_task_operation('create', 'TEST_PROJECT', 'task_456', status='active')
    
    # Test error logging with context
    try:
        raise ValueError("Test exception for logging")
    except Exception as e:
        logger.log_error_with_context(e, {'operation': 'test', 'user': 'test_user'})
    
    print("  ✓ All logging methods functional")


def test_tracing_decorators():
    """Test distributed tracing decorators."""
    print("🔍 Testing tracing decorators...")
    
    @trace_mcp_tool('test_mcp_operation', record_args=True, record_result=True)
    def mcp_tool_simulation(project: str, task_id: str, action: str = 'create'):
        """Simulate an MCP tool call."""
        time.sleep(0.01)  # Simulate work
        return {'status': 'success', 'project': project, 'task_id': task_id, 'action': action}
    
    @trace_cache_operation('get')
    def cache_get_simulation(namespace: str, key: str):
        """Simulate cache get operation."""
        time.sleep(0.001)
        return f"cached_value_for_{key}" if key != 'missing' else None
    
    @trace_task_operation('create')
    def task_create_simulation(project: str, task_data: dict):
        """Simulate task creation."""
        time.sleep(0.05)
        return {'task_id': 'task_789', 'status': 'created', **task_data}
    
    # Test sync decorators
    result1 = mcp_tool_simulation('TEST', 'task_123', action='update')
    result2 = cache_get_simulation('tasks', 'key_456')
    result3 = cache_get_simulation('tasks', 'missing')  # Cache miss
    result4 = task_create_simulation('TEST', {'name': 'Test Task'})
    
    assert result1['status'] == 'success'
    assert result2 == 'cached_value_for_key_456'
    assert result3 is None
    assert result4['task_id'] == 'task_789'
    
    print("  ✓ All tracing decorators functional")


async def test_async_tracing():
    """Test async function tracing."""
    print("🔄 Testing async tracing...")
    
    @trace_mcp_tool('async_tool_operation')
    async def async_tool_simulation(delay: float = 0.01):
        """Simulate async MCP tool call."""
        await asyncio.sleep(delay)
        return {'async_result': 'success', 'delay': delay}
    
    result = await async_tool_simulation(0.02)
    assert result['async_result'] == 'success'
    assert result['delay'] == 0.02
    
    print("  ✓ Async tracing functional")


def test_metrics_context_managers(metrics):
    """Test MetricsCollector context managers."""
    print("🎯 Testing metrics context managers...")
    
    # Test successful operation
    with MetricsCollector(metrics, 'tool_call', tool='context_test_tool') as collector:
        time.sleep(0.01)
        collector.add_attributes(operation_type='test', result_size=100)
    
    # Test failed operation
    try:
        with MetricsCollector(metrics, 'cache', operation='get', namespace='test') as collector:
            time.sleep(0.005)
            raise RuntimeError("Simulated cache error")
    except RuntimeError:
        pass  # Expected
    
    # Test task operation
    with MetricsCollector(metrics, 'task', operation='create', project='TEST') as collector:
        time.sleep(0.02)
        collector.add_attributes(task_id='task_context_test', status='active')
    
    print("  ✓ All context managers functional")


def test_health_and_fallback(metrics):
    """Test health monitoring and fallback behavior."""
    print("🏥 Testing health monitoring and fallback...")
    
    health = metrics.get_health_metrics()
    assert 'metrics_enabled' in health
    assert 'otel_available' in health
    assert 'timestamp' in health
    
    # Test fallback metrics when OTel unavailable
    if not health['metrics_enabled']:
        assert 'fallback_metrics' in health
        fallback = health['fallback_metrics']
        
        # Verify we have timing statistics
        timing_keys = [k for k in fallback.keys() if '_avg' in k or '_min' in k or '_max' in k]
        assert len(timing_keys) > 0
        
        print(f"  ✓ Fallback mode active with {len(fallback)} metrics")
    else:
        print("  ✓ OpenTelemetry mode active")
    
    print(f"  ✓ Health status: OTel={health['otel_available']}, Metrics={health['metrics_enabled']}")


def run_comprehensive_test():
    """Run the complete observability integration test suite."""
    print("🚀 Starting ATLAS MCP Observability Integration Tests")
    print("=" * 60)
    
    try:
        # Setup structured logging for test output
        setup_structured_logging(
            level='INFO',
            enable_trace_correlation=True,
            enable_console_output=False,  # Disable to avoid cluttering test output
            extra_fields={'test_run': 'observability_integration'}
        )
        
        # Run test suite
        obs_manager, metrics, logger = test_basic_initialization()
        
        fallback_metrics = test_metrics_collection(metrics)
        test_structured_logging(logger)
        test_tracing_decorators()
        
        # Run async test
        asyncio.run(test_async_tracing())
        
        test_metrics_context_managers(metrics)
        test_health_and_fallback(metrics)
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED - Observability System Fully Integrated!")
        print("\n📋 Integration Summary:")
        print(f"  • Metrics collected: {len(fallback_metrics)} types")
        print(f"  • OpenTelemetry available: {obs_manager.enabled}")
        print(f"  • Fallback mode functional: {not metrics.enabled}")
        print(f"  • Structured logging: ✓")
        print(f"  • Distributed tracing: ✓")
        print(f"  • Error handling: ✓")
        print(f"  • Health monitoring: ✓")
        print(f"  • Async support: ✓")
        print(f"  • Context managers: ✓")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)