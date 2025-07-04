"""Tests for Resource Management modules."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import psutil

from atlas_commands.resources import (
    ResourceUsage, ResourceLimits, ResourceMonitor, ResourcePool
)


class TestResourceMonitor:
    """Test suite for ResourceMonitor."""
    
    def test_get_current_usage(self):
        """Test getting current resource usage snapshot."""
        monitor = ResourceMonitor()
        
        usage = monitor.get_current_usage()
        
        assert isinstance(usage, ResourceUsage)
        assert isinstance(usage.timestamp, datetime)
        assert usage.cpu_percent >= 0
        assert usage.memory_mb > 0
        assert usage.memory_percent >= 0
        assert usage.disk_usage_percent >= 0
        assert usage.active_threads > 0
        assert usage.open_files >= 0
    
    def test_check_resource_availability(self):
        """Test checking if resources are available for operation."""
        monitor = ResourceMonitor()
        
        result = monitor.check_resource_availability(
            operation="test_operation",
            estimated_memory_mb=50.0,
            estimated_cpu_seconds=2.0
        )
        
        assert "available" in result
        assert "current_usage" in result
        assert "limits" in result
        assert "constraints" in result
        assert "recommendations" in result
        
        # Check structure
        assert "memory_mb" in result["current_usage"]
        assert "cpu_percent" in result["current_usage"]
    
    def test_resource_limits_enforcement(self):
        """Test resource limit enforcement."""
        limits = ResourceLimits(
            max_memory_mb=100.0,  # Very low for testing
            max_cpu_percent=5.0,   # Very low for testing
            max_active_operations=2
        )
        
        monitor = ResourceMonitor(limits)
        
        # Check with high requirements
        result = monitor.check_resource_availability(
            operation="heavy_operation",
            estimated_memory_mb=200.0  # Exceeds limit
        )
        
        assert result["available"] is False
        assert result["constraints"]["memory"] is True
    
    def test_operation_tracking(self):
        """Test tracking active operations."""
        monitor = ResourceMonitor()
        
        # Start operations
        success1 = monitor.start_operation(
            operation_id="op-1",
            operation_type="checklist_create",
            metadata={"task_id": "test-123"}
        )
        
        success2 = monitor.start_operation(
            operation_id="op-2",
            operation_type="memory_compact"
        )
        
        assert success1 is True
        assert success2 is True
        assert len(monitor.active_operations) == 2
        
        # End operation
        usage_summary = monitor.end_operation("op-1")
        
        assert usage_summary is not None
        assert usage_summary["operation_id"] == "op-1"
        assert usage_summary["operation_type"] == "checklist_create"
        assert "duration_seconds" in usage_summary
        assert "memory_delta_mb" in usage_summary
        assert len(monitor.active_operations) == 1
    
    def test_operation_limit_enforcement(self):
        """Test enforcing maximum active operations."""
        limits = ResourceLimits(max_active_operations=2)
        monitor = ResourceMonitor(limits)
        
        # Start max operations
        monitor.start_operation("op-1", "type1")
        monitor.start_operation("op-2", "type2")
        
        # Try to start one more
        success = monitor.start_operation("op-3", "type3")
        
        assert success is False
        assert len(monitor.active_operations) == 2
    
    def test_usage_statistics(self):
        """Test getting resource usage statistics."""
        monitor = ResourceMonitor()
        
        # Generate some usage history
        for i in range(5):
            monitor.get_current_usage()
        
        stats = monitor.get_usage_statistics(time_window_seconds=300)
        
        assert "time_window_seconds" in stats
        assert "sample_count" in stats
        assert stats["sample_count"] >= 5
        
        assert "cpu" in stats
        assert "average" in stats["cpu"]
        assert "peak" in stats["cpu"]
        assert "current" in stats["cpu"]
        
        assert "memory" in stats
        assert "average_mb" in stats["memory"]
        assert "peak_mb" in stats["memory"]
    
    def test_resource_recommendations(self):
        """Test getting resource recommendations."""
        monitor = ResourceMonitor()
        
        # Mock high usage
        with patch.object(monitor, 'get_current_usage') as mock_usage:
            mock_usage.return_value = ResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=75.0,
                memory_mb=450.0,
                memory_percent=88.0,
                disk_usage_percent=87.0,
                active_threads=10,
                open_files=85
            )
            
            result = monitor.check_resource_availability("test_op")
            
            recommendations = result["recommendations"]
            assert len(recommendations) > 0
            assert any("memory" in r.lower() for r in recommendations)
            assert any("cpu" in r.lower() for r in recommendations)
            assert any("disk" in r.lower() for r in recommendations)
    
    def test_resource_callbacks(self):
        """Test resource event callbacks."""
        monitor = ResourceMonitor()
        
        callback_events = []
        
        def test_callback(event_type, usage):
            callback_events.append({
                "type": event_type,
                "memory_mb": usage.memory_mb
            })
        
        monitor.register_callback(test_callback)
        
        # Trigger high memory event
        with patch.object(monitor, 'get_current_usage') as mock_usage:
            mock_usage.return_value = ResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=50.0,
                memory_mb=480.0,  # > 90% of default 512MB
                memory_percent=94.0,
                disk_usage_percent=70.0,
                active_threads=5,
                open_files=20
            )
            
            monitor._check_resource_triggers(mock_usage.return_value)
            
            assert len(callback_events) == 1
            assert callback_events[0]["type"] == "high_memory"
    
    def test_cleanup_resources(self):
        """Test resource cleanup operations."""
        monitor = ResourceMonitor()
        
        # Start some operations
        monitor.start_operation("op-1", "test")
        monitor.start_operation("op-2", "test")
        
        # Perform cleanup
        cleanup_result = monitor.cleanup_resources()
        
        assert "memory_freed_mb" in cleanup_result
        assert "files_closed" in cleanup_result
        assert "operations_cleared" in cleanup_result
        assert cleanup_result["operations_cleared"] == 2
        assert len(monitor.active_operations) == 0
    
    def test_peak_cpu_tracking(self):
        """Test tracking peak CPU during operations."""
        monitor = ResourceMonitor()
        
        # Start operation
        monitor.start_operation("cpu-test", "intensive")
        
        # Simulate CPU usage spikes
        for i in range(3):
            monitor.get_current_usage()
        
        # End operation
        summary = monitor.end_operation("cpu-test")
        
        assert "peak_cpu_percent" in summary
        assert summary["peak_cpu_percent"] >= 0


class TestResourcePool:
    """Test suite for ResourcePool."""
    
    def test_acquire_resource(self):
        """Test acquiring resource from pool."""
        pool = ResourcePool()
        
        # Define factory
        def create_validator():
            return {"type": "validator", "id": "new"}
        
        # Acquire resource (should create new)
        resource = pool.acquire("validators", factory=create_validator)
        
        assert resource is not None
        assert resource["type"] == "validator"
        assert pool.usage_counts.get("validators", 0) == 1
    
    def test_release_and_reuse_resource(self):
        """Test releasing and reusing resources."""
        pool = ResourcePool()
        
        # Create and release resource
        resource1 = {"type": "manager", "id": "1", "data": "test"}
        released = pool.release("managers", resource1)
        
        assert released is True
        assert len(pool.pools["managers"]) == 1
        
        # Acquire should reuse
        resource2 = pool.acquire("managers")
        
        assert resource2 is resource1
        assert pool.usage_counts["managers"] == 1
    
    def test_pool_limits(self):
        """Test pool size limits."""
        pool = ResourcePool()
        pool.pool_limits["test_pool"] = 2
        
        # Fill pool to limit
        pool.release("test_pool", {"id": 1})
        pool.release("test_pool", {"id": 2})
        
        # Try to add beyond limit
        released = pool.release("test_pool", {"id": 3})
        
        assert released is False
        assert len(pool.pools["test_pool"]) == 2
    
    def test_resource_reset(self):
        """Test resource reset on release."""
        pool = ResourcePool()
        
        # Resource with reset method
        class ResettableResource:
            def __init__(self):
                self.state = "dirty"
            
            def reset(self):
                self.state = "clean"
        
        resource = ResettableResource()
        assert resource.state == "dirty"
        
        # Release should reset
        pool.release("resettable", resource)
        
        # Acquire and check state
        reused = pool.acquire("resettable")
        assert reused.state == "clean"
    
    def test_pool_statistics(self):
        """Test getting pool statistics."""
        pool = ResourcePool()
        
        # Create various pools
        pool.release("checklist_managers", {"id": 1})
        pool.release("checklist_managers", {"id": 2})
        pool.release("memory_managers", {"id": 1})
        
        # Acquire some
        pool.acquire("checklist_managers")
        pool.acquire("checklist_managers")
        pool.acquire("memory_managers")
        
        stats = pool.get_pool_statistics()
        
        assert "pools" in stats
        assert "checklist_managers" in stats["pools"]
        assert stats["pools"]["checklist_managers"]["available"] == 2
        assert stats["pools"]["checklist_managers"]["total_usage"] == 2
        assert stats["pools"]["memory_managers"]["available"] == 1
        assert stats["pools"]["memory_managers"]["total_usage"] == 1
    
    def test_concurrent_pool_access(self):
        """Test concurrent access to resource pool."""
        pool = ResourcePool()
        
        # Pre-populate pool
        for i in range(5):
            pool.release("workers", {"id": i})
        
        # Simulate concurrent acquisitions
        acquired = []
        for i in range(5):
            resource = pool.acquire("workers")
            assert resource is not None
            acquired.append(resource)
        
        # Pool should be empty
        assert len(pool.pools["workers"]) == 0
        
        # All resources should be unique
        ids = [r["id"] for r in acquired]
        assert len(set(ids)) == 5
        
        # Release all back
        for resource in acquired:
            pool.release("workers", resource)
        
        assert len(pool.pools["workers"]) == 5