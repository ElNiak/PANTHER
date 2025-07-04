"""Resource management and monitoring for ATLAS Commands MCP Server."""

import psutil
import os
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass
from collections import deque
import logging


@dataclass
class ResourceUsage:
    """Resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    active_threads: int
    open_files: int


@dataclass
class ResourceLimits:
    """Resource limits for the MCP server."""
    max_memory_mb: float = 512.0  # 512MB
    max_cpu_percent: float = 80.0  # 80%
    max_disk_usage_percent: float = 90.0  # 90%
    max_open_files: int = 100
    max_active_operations: int = 10


class ResourceMonitor:
    """Monitors resource usage and enforces limits."""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self.usage_history: deque = deque(maxlen=100)  # Keep last 100 snapshots
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.resource_callbacks: List[Callable] = []
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process(os.getpid())
    
    def get_current_usage(self) -> ResourceUsage:
        """Get current resource usage snapshot."""
        
        # CPU usage (over 1 second interval)
        cpu_percent = self.process.cpu_percent(interval=0.1)
        
        # Memory usage
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        memory_percent = self.process.memory_percent()
        
        # Disk usage
        disk_usage = psutil.disk_usage('/')
        disk_usage_percent = disk_usage.percent
        
        # Thread and file counts
        active_threads = self.process.num_threads()
        try:
            open_files = len(self.process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            open_files = 0
        
        usage = ResourceUsage(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_usage_percent=disk_usage_percent,
            active_threads=active_threads,
            open_files=open_files
        )
        
        # Add to history
        self.usage_history.append(usage)
        
        return usage
    
    def check_resource_availability(
        self,
        operation: str,
        estimated_memory_mb: float = 10.0,
        estimated_cpu_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """Check if resources are available for an operation."""
        
        current_usage = self.get_current_usage()
        
        # Check memory
        projected_memory = current_usage.memory_mb + estimated_memory_mb
        memory_available = projected_memory < self.limits.max_memory_mb
        
        # Check CPU
        cpu_available = current_usage.cpu_percent < self.limits.max_cpu_percent
        
        # Check disk
        disk_available = current_usage.disk_usage_percent < self.limits.max_disk_usage_percent
        
        # Check file handles
        files_available = current_usage.open_files < self.limits.max_open_files
        
        # Check concurrent operations
        operations_available = len(self.active_operations) < self.limits.max_active_operations
        
        available = all([
            memory_available,
            cpu_available,
            disk_available,
            files_available,
            operations_available
        ])
        
        return {
            "available": available,
            "current_usage": {
                "memory_mb": current_usage.memory_mb,
                "memory_percent": current_usage.memory_percent,
                "cpu_percent": current_usage.cpu_percent,
                "disk_percent": current_usage.disk_usage_percent,
                "open_files": current_usage.open_files,
                "active_operations": len(self.active_operations)
            },
            "limits": {
                "memory_mb": self.limits.max_memory_mb,
                "cpu_percent": self.limits.max_cpu_percent,
                "disk_percent": self.limits.max_disk_usage_percent,
                "open_files": self.limits.max_open_files,
                "active_operations": self.limits.max_active_operations
            },
            "constraints": {
                "memory": not memory_available,
                "cpu": not cpu_available,
                "disk": not disk_available,
                "files": not files_available,
                "operations": not operations_available
            },
            "recommendations": self._get_resource_recommendations(current_usage)
        }
    
    def start_operation(
        self,
        operation_id: str,
        operation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register an operation as started."""
        
        if len(self.active_operations) >= self.limits.max_active_operations:
            self.logger.warning(
                f"Operation limit reached: {len(self.active_operations)}/{self.limits.max_active_operations}"
            )
            return False
        
        self.active_operations[operation_id] = {
            "type": operation_type,
            "start_time": datetime.now(),
            "metadata": metadata or {},
            "initial_usage": self.get_current_usage()
        }
        
        return True
    
    def end_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Mark an operation as completed and return resource usage."""
        
        if operation_id not in self.active_operations:
            return None
        
        operation = self.active_operations[operation_id]
        end_time = datetime.now()
        final_usage = self.get_current_usage()
        
        # Calculate resource consumption
        duration = (end_time - operation["start_time"]).total_seconds()
        memory_delta = final_usage.memory_mb - operation["initial_usage"].memory_mb
        
        usage_summary = {
            "operation_id": operation_id,
            "operation_type": operation["type"],
            "duration_seconds": duration,
            "memory_delta_mb": memory_delta,
            "peak_cpu_percent": self._get_peak_cpu_during_operation(operation["start_time"], end_time),
            "start_time": operation["start_time"].isoformat(),
            "end_time": end_time.isoformat()
        }
        
        # Remove from active operations
        del self.active_operations[operation_id]
        
        # Trigger callbacks if needed
        self._check_resource_triggers(final_usage)
        
        return usage_summary
    
    def _get_peak_cpu_during_operation(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> float:
        """Get peak CPU usage during an operation."""
        
        relevant_snapshots = [
            usage for usage in self.usage_history
            if start_time <= usage.timestamp <= end_time
        ]
        
        if not relevant_snapshots:
            return 0.0
        
        return max(usage.cpu_percent for usage in relevant_snapshots)
    
    def _get_resource_recommendations(
        self,
        current_usage: ResourceUsage
    ) -> List[str]:
        """Get recommendations based on current resource usage."""
        
        recommendations = []
        
        # Memory recommendations
        memory_percent_used = (current_usage.memory_mb / self.limits.max_memory_mb) * 100
        if memory_percent_used > 80:
            recommendations.append("Consider compacting memory graph to free memory")
        elif memory_percent_used > 60:
            recommendations.append("Memory usage is moderate, monitor for increases")
        
        # CPU recommendations
        if current_usage.cpu_percent > 70:
            recommendations.append("High CPU usage detected, consider deferring intensive operations")
        
        # Disk recommendations
        if current_usage.disk_usage_percent > 85:
            recommendations.append("Disk space running low, consider archiving old tasks")
        
        # File handle recommendations
        if current_usage.open_files > self.limits.max_open_files * 0.8:
            recommendations.append("Many open files detected, close unused file handles")
        
        return recommendations
    
    def _check_resource_triggers(self, usage: ResourceUsage):
        """Check if any resource triggers should fire."""
        
        # Check for high memory usage
        if usage.memory_mb > self.limits.max_memory_mb * 0.9:
            self._trigger_callbacks("high_memory", usage)
        
        # Check for high CPU usage
        if usage.cpu_percent > self.limits.max_cpu_percent * 0.9:
            self._trigger_callbacks("high_cpu", usage)
        
        # Check for high disk usage
        if usage.disk_usage_percent > self.limits.max_disk_usage_percent * 0.95:
            self._trigger_callbacks("high_disk", usage)
    
    def _trigger_callbacks(self, event_type: str, usage: ResourceUsage):
        """Trigger registered callbacks."""
        
        for callback in self.resource_callbacks:
            try:
                callback(event_type, usage)
            except Exception as e:
                self.logger.error(f"Resource callback failed: {e}")
    
    def register_callback(self, callback: Callable):
        """Register a callback for resource events."""
        
        self.resource_callbacks.append(callback)
    
    def get_usage_statistics(
        self,
        time_window_seconds: int = 300
    ) -> Dict[str, Any]:
        """Get resource usage statistics over a time window."""
        
        cutoff_time = datetime.now().timestamp() - time_window_seconds
        recent_usage = [
            usage for usage in self.usage_history
            if usage.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_usage:
            return {
                "time_window_seconds": time_window_seconds,
                "sample_count": 0,
                "no_data": True
            }
        
        return {
            "time_window_seconds": time_window_seconds,
            "sample_count": len(recent_usage),
            "cpu": {
                "average": sum(u.cpu_percent for u in recent_usage) / len(recent_usage),
                "peak": max(u.cpu_percent for u in recent_usage),
                "current": recent_usage[-1].cpu_percent
            },
            "memory": {
                "average_mb": sum(u.memory_mb for u in recent_usage) / len(recent_usage),
                "peak_mb": max(u.memory_mb for u in recent_usage),
                "current_mb": recent_usage[-1].memory_mb,
                "average_percent": sum(u.memory_percent for u in recent_usage) / len(recent_usage)
            },
            "disk": {
                "average_percent": sum(u.disk_usage_percent for u in recent_usage) / len(recent_usage),
                "current_percent": recent_usage[-1].disk_usage_percent
            },
            "operations": {
                "currently_active": len(self.active_operations),
                "active_types": list(set(op["type"] for op in self.active_operations.values()))
            }
        }
    
    def cleanup_resources(self) -> Dict[str, Any]:
        """Perform resource cleanup operations."""
        
        cleanup_results = {
            "memory_freed_mb": 0,
            "files_closed": 0,
            "operations_cleared": 0
        }
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        
        # Estimate memory freed (rough estimate)
        current_usage = self.get_current_usage()
        gc.collect()
        after_usage = self.get_current_usage()
        cleanup_results["memory_freed_mb"] = max(0, current_usage.memory_mb - after_usage.memory_mb)
        
        # Clear completed operations
        cleanup_results["operations_cleared"] = len(self.active_operations)
        self.active_operations.clear()
        
        return cleanup_results


class ResourcePool:
    """Manages pooled resources for efficient reuse."""
    
    def __init__(self):
        self.pools: Dict[str, List[Any]] = {}
        self.pool_limits: Dict[str, int] = {
            "checklist_managers": 5,
            "memory_managers": 3,
            "validators": 10
        }
        self.usage_counts: Dict[str, int] = {}
    
    def acquire(self, resource_type: str, factory: Optional[Callable] = None) -> Any:
        """Acquire a resource from the pool."""
        
        if resource_type not in self.pools:
            self.pools[resource_type] = []
        
        # Try to get from pool
        if self.pools[resource_type]:
            resource = self.pools[resource_type].pop()
            self.usage_counts[resource_type] = self.usage_counts.get(resource_type, 0) + 1
            return resource
        
        # Create new resource if factory provided
        if factory:
            resource = factory()
            self.usage_counts[resource_type] = self.usage_counts.get(resource_type, 0) + 1
            return resource
        
        return None
    
    def release(self, resource_type: str, resource: Any) -> bool:
        """Release a resource back to the pool."""
        
        if resource_type not in self.pools:
            self.pools[resource_type] = []
        
        # Check pool limit
        limit = self.pool_limits.get(resource_type, 10)
        if len(self.pools[resource_type]) < limit:
            # Reset resource if it has a reset method
            if hasattr(resource, 'reset'):
                resource.reset()
            
            self.pools[resource_type].append(resource)
            return True
        
        return False
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get statistics about resource pools."""
        
        return {
            "pools": {
                pool_name: {
                    "available": len(resources),
                    "limit": self.pool_limits.get(pool_name, 10),
                    "total_usage": self.usage_counts.get(pool_name, 0)
                }
                for pool_name, resources in self.pools.items()
            }
        }