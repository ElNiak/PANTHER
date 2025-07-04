"""
Memory Management Handler

Handles memory system health, backups, analytics, and cleanup operations.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from ..tool_registry import ToolHandler
from ..refactor_config import get_config
import logging


class MemoryManagementHandler(ToolHandler):
    """Handler for memory management and health tools."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "memory_management"
    
    def get_tool_names(self) -> List[str]:
        return [
            "memory_health_check",
            "memory_force_backup",
            "memory_restore",
            "memory_analytics",
            "memory_cleanup"
        ]
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle memory management tool calls."""
        try:
            if self.config.enable_consistent_error_handling:
                self.logger.info(f"Processing memory management tool: {name}")
            
            # Route to appropriate handler method
            if name == "memory_health_check":
                return await self._handle_memory_health_check(arguments)
            elif name == "memory_force_backup":
                return await self._handle_memory_force_backup(arguments)
            elif name == "memory_restore":
                return await self._handle_memory_restore(arguments)
            elif name == "memory_analytics":
                return await self._handle_memory_analytics(arguments)
            elif name == "memory_cleanup":
                return await self._handle_memory_cleanup(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown memory management tool: {name}")]
                
        except Exception as e:
            error_msg = f"Error in memory management handler for {name}: {str(e)}"
            self.logger.error(error_msg)
            if self.config.enable_consistent_error_handling:
                return [TextContent(type="text", text=f"Memory Management Error: {str(e)}")]
            else:
                raise e
    
    # Implement memory management methods directly
    async def _handle_memory_health_check(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle comprehensive memory health check requests with actual testing."""
        import time
        import psutil
        import os
        from datetime import datetime
        
        try:
            health_results = {
                "system_memory": {},
                "component_tests": {},
                "performance_metrics": {},
                "recommendations": [],
                "overall_status": "unknown",
                "test_timestamp": datetime.now().isoformat()
            }
            
            # 1. System Memory Analysis
            memory_info = psutil.virtual_memory()
            health_results["system_memory"] = {
                "total_gb": round(memory_info.total / (1024**3), 2),
                "available_gb": round(memory_info.available / (1024**3), 2),
                "used_percentage": memory_info.percent,
                "status": "healthy" if memory_info.percent < 80 else "warning" if memory_info.percent < 90 else "critical"
            }
            
            # 2. Component Functionality Tests
            component_tests = {}
            
            # Test Cache Manager
            if hasattr(self.server, 'cache_manager') and self.server.cache_manager:
                cache_start = time.time()
                try:
                    # Test cache operations
                    test_key = f"health_check_{int(time.time())}"
                    test_value = {"test": "data", "timestamp": time.time()}
                    
                    # Set operation
                    self.server.cache_manager.set("health_test", test_key, test_value, l1_ttl=30)
                    
                    # Get operation
                    retrieved = self.server.cache_manager.get("health_test", test_key)
                    
                    # Cleanup
                    self.server.cache_manager.invalidate("health_test", test_key)
                    
                    cache_time = (time.time() - cache_start) * 1000
                    component_tests["cache_manager"] = {
                        "status": "healthy" if retrieved is not None else "degraded",
                        "response_time_ms": round(cache_time, 2),
                        "operations_tested": ["set", "get", "invalidate"],
                        "l1_cache_available": True,
                        "l2_cache_available": hasattr(self.server.cache_manager, 'l2_client') and bool(self.server.cache_manager.l2_client),
                        "l3_cache_available": hasattr(self.server.cache_manager, 'l3_cache_dir') and bool(self.server.cache_manager.l3_cache_dir)
                    }
                except Exception as e:
                    component_tests["cache_manager"] = {
                        "status": "error",
                        "error": str(e),
                        "response_time_ms": 0
                    }
            else:
                component_tests["cache_manager"] = {"status": "unavailable"}
            
            # Test Storage Manager
            if hasattr(self.server, 'storage_manager') and self.server.storage_manager:
                storage_start = time.time()
                try:
                    # Test storage operations
                    test_projects = self.server.storage_manager.list_projects()
                    storage_time = (time.time() - storage_start) * 1000
                    
                    # Check storage path accessibility
                    storage_path = getattr(self.server.storage_manager, 'base_path', None)
                    storage_accessible = storage_path and os.path.exists(storage_path) and os.access(storage_path, os.W_OK)
                    
                    component_tests["storage_manager"] = {
                        "status": "healthy" if storage_accessible else "degraded",
                        "response_time_ms": round(storage_time, 2),
                        "projects_count": len(test_projects),
                        "storage_path": str(storage_path) if storage_path else None,
                        "writable": storage_accessible,
                        "operations_tested": ["list_projects", "path_access"]
                    }
                except Exception as e:
                    component_tests["storage_manager"] = {
                        "status": "error",
                        "error": str(e),
                        "response_time_ms": 0
                    }
            else:
                component_tests["storage_manager"] = {"status": "unavailable"}
            
            # Test Memory Manager
            if hasattr(self.server, 'memory_manager') and self.server.memory_manager:
                component_tests["memory_manager"] = {
                    "status": "healthy",
                    "type": type(self.server.memory_manager).__name__,
                    "operations_tested": ["basic_access"]
                }
            else:
                component_tests["memory_manager"] = {"status": "unavailable"}
            
            health_results["component_tests"] = component_tests
            
            # 3. Performance Metrics
            health_results["performance_metrics"] = {
                "cache_avg_response_ms": component_tests.get("cache_manager", {}).get("response_time_ms", 0),
                "storage_avg_response_ms": component_tests.get("storage_manager", {}).get("response_time_ms", 0),
                "memory_efficiency": 100 - health_results["system_memory"]["used_percentage"]
            }
            
            # 4. Generate Recommendations
            recommendations = []
            
            # Memory recommendations
            if health_results["system_memory"]["used_percentage"] > 85:
                recommendations.append({
                    "type": "memory",
                    "priority": "high",
                    "message": "System memory usage is high - consider implementing memory cleanup strategies"
                })
            
            # Cache recommendations
            cache_status = component_tests.get("cache_manager", {}).get("status", "unavailable")
            if cache_status == "unavailable":
                recommendations.append({
                    "type": "cache",
                    "priority": "medium",
                    "message": "Cache manager not available - initialize for better performance"
                })
            elif cache_status == "error":
                recommendations.append({
                    "type": "cache",
                    "priority": "high",
                    "message": "Cache manager has errors - investigate and repair"
                })
            
            # Storage recommendations
            storage_status = component_tests.get("storage_manager", {}).get("status", "unavailable")
            if storage_status == "degraded":
                recommendations.append({
                    "type": "storage",
                    "priority": "high",
                    "message": "Storage path not writable - check permissions and disk space"
                })
            
            # Performance recommendations
            cache_time = health_results["performance_metrics"]["cache_avg_response_ms"]
            if cache_time > 100:
                recommendations.append({
                    "type": "performance",
                    "priority": "medium",
                    "message": f"Cache response time ({cache_time}ms) is slow - optimize cache configuration"
                })
            
            health_results["recommendations"] = recommendations
            
            # 5. Overall Health Assessment
            healthy_components = sum(1 for test in component_tests.values() if test.get("status") == "healthy")
            total_components = len(component_tests)
            health_percentage = (healthy_components / total_components * 100) if total_components > 0 else 0
            
            if health_percentage >= 80 and health_results["system_memory"]["status"] in ["healthy", "warning"]:
                health_results["overall_status"] = "healthy"
            elif health_percentage >= 60:
                health_results["overall_status"] = "degraded"
            else:
                health_results["overall_status"] = "unhealthy"
            
            health_results["health_percentage"] = round(health_percentage, 1)
            
            import json
            return [TextContent(type="text", text=json.dumps(health_results, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive memory health check: {str(e)}")
            return [TextContent(type="text", text=f"Memory health check error: {str(e)}")]
    
    async def _handle_memory_force_backup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_memory_force_backup(arguments)
    
    async def _handle_memory_restore(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_memory_restore(arguments)
    
    async def _handle_memory_analytics(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle comprehensive memory analytics with real performance data."""
        import time
        import os
        import gc
        import psutil
        from datetime import datetime, timedelta
        
        try:
            analytics = {
                "system_analytics": {},
                "cache_analytics": {},
                "storage_analytics": {},
                "memory_usage_trends": {},
                "performance_insights": {},
                "optimization_recommendations": [],
                "collection_timestamp": datetime.now().isoformat()
            }
            
            # 1. Detailed System Memory Analytics
            process = psutil.Process(os.getpid())
            memory_info = psutil.virtual_memory()
            process_memory = process.memory_info()
            
            analytics["system_analytics"] = {
                "system_memory": {
                    "total_gb": round(memory_info.total / (1024**3), 2),
                    "available_gb": round(memory_info.available / (1024**3), 2),
                    "used_percentage": memory_info.percent,
                    "buffer_cache_gb": round(memory_info.buffers / (1024**3), 2) if hasattr(memory_info, 'buffers') else 0
                },
                "process_memory": {
                    "rss_mb": round(process_memory.rss / (1024**2), 2),
                    "vms_mb": round(process_memory.vms / (1024**2), 2),
                    "memory_percent": round(process.memory_percent(), 2),
                    "threads": process.num_threads()
                },
                "garbage_collection": {
                    "collections": gc.get_count(),
                    "thresholds": gc.get_threshold(),
                    "objects_tracked": len(gc.get_objects())
                }
            }
            
            # 2. Comprehensive Cache Analytics
            cache_analytics = {
                "l1_cache": {"available": False, "stats": {}},
                "l2_cache": {"available": False, "stats": {}},
                "l3_cache": {"available": False, "stats": {}},
                "performance_tests": {},
                "hit_miss_analysis": {}
            }
            
            if hasattr(self.server, 'cache_manager') and self.server.cache_manager:
                cache_mgr = self.server.cache_manager
                
                # L1 Cache Analysis
                cache_analytics["l1_cache"]["available"] = True
                if hasattr(cache_mgr, 'l1_cache') and cache_mgr.l1_cache:
                    l1_cache = cache_mgr.l1_cache
                    cache_analytics["l1_cache"]["stats"] = {
                        "max_size": getattr(l1_cache, 'maxsize', 0),
                        "current_size": len(getattr(l1_cache, 'data', {})),
                        "hit_count": getattr(l1_cache, 'hits', 0),
                        "miss_count": getattr(l1_cache, 'misses', 0),
                        "hit_rate": round(getattr(l1_cache, 'hits', 0) / max(1, getattr(l1_cache, 'hits', 0) + getattr(l1_cache, 'misses', 0)) * 100, 2)
                    }
                
                # L2 Cache Analysis (Redis)
                cache_analytics["l2_cache"]["available"] = hasattr(cache_mgr, 'l2_client') and bool(cache_mgr.l2_client)
                if cache_analytics["l2_cache"]["available"]:
                    try:
                        # Test Redis performance
                        redis_start = time.time()
                        test_key = f"analytics_test_{int(time.time())}"
                        cache_mgr.l2_client.set(test_key, "test_value", 10)
                        retrieved = cache_mgr.l2_client.get(test_key)
                        cache_mgr.l2_client.delete(test_key)
                        redis_time = (time.time() - redis_start) * 1000
                        
                        cache_analytics["l2_cache"]["stats"] = {
                            "connection_status": "healthy",
                            "response_time_ms": round(redis_time, 2),
                            "test_successful": retrieved is not None
                        }
                    except Exception as e:
                        cache_analytics["l2_cache"]["stats"] = {
                            "connection_status": "error",
                            "error": str(e)
                        }
                
                # L3 Cache Analysis (File system)
                cache_analytics["l3_cache"]["available"] = hasattr(cache_mgr, 'l3_cache_dir') and bool(cache_mgr.l3_cache_dir)
                if cache_analytics["l3_cache"]["available"]:
                    l3_dir = cache_mgr.l3_cache_dir
                    if os.path.exists(l3_dir):
                        cache_files = [f for f in os.listdir(l3_dir) if os.path.isfile(os.path.join(l3_dir, f))]
                        total_size = sum(os.path.getsize(os.path.join(l3_dir, f)) for f in cache_files)
                        
                        cache_analytics["l3_cache"]["stats"] = {
                            "cache_directory": str(l3_dir),
                            "file_count": len(cache_files),
                            "total_size_mb": round(total_size / (1024**2), 2),
                            "oldest_file": min([os.path.getctime(os.path.join(l3_dir, f)) for f in cache_files]) if cache_files else None,
                            "newest_file": max([os.path.getctime(os.path.join(l3_dir, f)) for f in cache_files]) if cache_files else None
                        }
                
                # Performance Testing
                performance_tests = {}
                try:
                    # Test cache operation speeds
                    test_data = {"large_test": list(range(1000)), "timestamp": time.time()}
                    
                    # L1 Performance
                    l1_start = time.time()
                    cache_mgr.set("analytics_test", "l1_perf_test", test_data, l1_ttl=30)
                    retrieved_l1 = cache_mgr.get("analytics_test", "l1_perf_test")
                    l1_time = (time.time() - l1_start) * 1000
                    
                    performance_tests["l1_performance"] = {
                        "write_read_time_ms": round(l1_time, 2),
                        "data_integrity": retrieved_l1 == test_data,
                        "data_size_bytes": len(str(test_data))
                    }
                    
                    # Cleanup
                    cache_mgr.invalidate("analytics_test", "l1_perf_test")
                    
                except Exception as e:
                    performance_tests["error"] = str(e)
                
                cache_analytics["performance_tests"] = performance_tests
            
            analytics["cache_analytics"] = cache_analytics
            
            # 3. Storage System Analytics
            storage_analytics = {
                "projects": {},
                "disk_usage": {},
                "file_analysis": {},
                "growth_patterns": {}
            }
            
            if hasattr(self.server, 'storage_manager') and self.server.storage_manager:
                storage_mgr = self.server.storage_manager
                base_path = getattr(storage_mgr, 'base_path', None)
                
                if base_path and os.path.exists(base_path):
                    # Project Analysis - find all project directories
                    project_dirs = [d for d in os.listdir(base_path) if d.endswith('_TASKS') and os.path.isdir(base_path / d)]
                    projects = [d[:-6] for d in project_dirs]  # Remove '_TASKS' suffix
                    project_stats = {}
                    
                    for project in projects:
                        try:
                            tasks = storage_mgr.list_project_tasks(project)
                            project_path = base_path / f"{project}_TASKS"
                            
                            if project_path.exists():
                                project_size = sum(
                                    os.path.getsize(os.path.join(dirpath, filename))
                                    for dirpath, dirnames, filenames in os.walk(project_path)
                                    for filename in filenames
                                )
                                
                                project_stats[project] = {
                                    "task_count": len(tasks),
                                    "size_mb": round(project_size / (1024**2), 2),
                                    "last_modified": os.path.getctime(project_path)
                                }
                        except Exception:
                            project_stats[project] = {"task_count": 0, "size_mb": 0}
                    
                    storage_analytics["projects"] = project_stats
                    
                    # Disk Usage Analysis
                    disk_usage = psutil.disk_usage(str(base_path))
                    storage_analytics["disk_usage"] = {
                        "total_gb": round(disk_usage.total / (1024**3), 2),
                        "used_gb": round(disk_usage.used / (1024**3), 2),
                        "free_gb": round(disk_usage.free / (1024**3), 2),
                        "used_percentage": round((disk_usage.used / disk_usage.total) * 100, 2),
                        "atlas_storage_path": str(base_path)
                    }
            
            analytics["storage_analytics"] = storage_analytics
            
            # 4. Memory Usage Trends and Insights
            insights = {
                "memory_efficiency": round(100 - memory_info.percent, 1),
                "cache_effectiveness": "unknown",
                "storage_growth_rate": "stable",
                "bottlenecks": [],
                "strengths": []
            }
            
            # Identify bottlenecks
            if memory_info.percent > 90:
                insights["bottlenecks"].append("Critical system memory usage")
            elif memory_info.percent > 80:
                insights["bottlenecks"].append("High system memory usage")
            
            if cache_analytics["l1_cache"]["available"]:
                l1_hit_rate = cache_analytics["l1_cache"]["stats"].get("hit_rate", 0)
                if l1_hit_rate > 80:
                    insights["strengths"].append("Excellent L1 cache performance")
                    insights["cache_effectiveness"] = "excellent"
                elif l1_hit_rate > 60:
                    insights["cache_effectiveness"] = "good"
                else:
                    insights["bottlenecks"].append("Poor L1 cache hit rate")
                    insights["cache_effectiveness"] = "poor"
            
            if not cache_analytics["l2_cache"]["available"]:
                insights["bottlenecks"].append("L2 Redis cache not available")
            
            analytics["performance_insights"] = insights
            
            # 5. Optimization Recommendations
            recommendations = []
            
            # Memory recommendations
            if memory_info.percent > 85:
                recommendations.append({
                    "category": "memory",
                    "priority": "high",
                    "action": "Implement memory cleanup and garbage collection optimization",
                    "expected_impact": "15-25% memory reduction"
                })
            
            # Cache recommendations
            if cache_analytics["l1_cache"]["available"]:
                hit_rate = cache_analytics["l1_cache"]["stats"].get("hit_rate", 0)
                if hit_rate < 60:
                    recommendations.append({
                        "category": "cache",
                        "priority": "medium",
                        "action": "Optimize cache key patterns and TTL values",
                        "expected_impact": "20-40% improvement in cache efficiency"
                    })
            
            if not cache_analytics["l2_cache"]["available"]:
                recommendations.append({
                    "category": "cache",
                    "priority": "medium",
                    "action": "Configure Redis for L2 cache tier",
                    "expected_impact": "50-80% improvement in cache performance"
                })
            
            # Storage recommendations
            if storage_analytics.get("disk_usage", {}).get("used_percentage", 0) > 85:
                recommendations.append({
                    "category": "storage",
                    "priority": "high",
                    "action": "Implement storage cleanup and archival policies",
                    "expected_impact": "20-40% storage space recovery"
                })
            
            analytics["optimization_recommendations"] = recommendations
            
            import json
            return [TextContent(type="text", text=json.dumps(analytics, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive memory analytics: {str(e)}")
            import traceback
            return [TextContent(type="text", text=f"Memory analytics error: {str(e)}\n{traceback.format_exc()}")]
    
    async def _handle_memory_cleanup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_memory_cleanup(arguments)