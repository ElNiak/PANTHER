"""
Performance Analytics Dashboard for ATLAS Hierarchical Cache
Phase 2 implementation providing comprehensive cache performance insights
"""

import json
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache


@dataclass
class CacheOperation:
    """Represents a single cache operation for analytics"""
    timestamp: float
    operation_type: str  # 'hit', 'miss', 'set', 'invalidate'
    cache_type: str
    cache_level: str  # 'global', 'project'
    key: str
    duration_ms: float = 0.0
    size_bytes: int = 0
    content_hash: str = ""


@dataclass
class PerformanceMetrics:
    """Performance metrics for a time period"""
    start_time: float
    end_time: float
    total_operations: int
    hit_count: int
    miss_count: int
    hit_rate_percent: float
    average_response_time_ms: float
    total_cache_size_mb: float
    cache_efficiency_score: float  # 0-100 composite score


@dataclass
class CacheRecommendation:
    """Cache optimization recommendation"""
    recommendation_type: str
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    estimated_improvement: str
    action_items: List[str]


class PerformanceTracker:
    """Tracks cache operations for performance analysis"""
    
    def __init__(self, max_operations: int = 10000):
        self.operations: deque = deque(maxlen=max_operations)
        self.hourly_stats: Dict[str, Dict] = {}  # hour -> stats
        self.daily_stats: Dict[str, Dict] = {}   # date -> stats
        self._lock = threading.Lock()
    
    def record_operation(self, operation: CacheOperation):
        """Record a cache operation"""
        with self._lock:
            self.operations.append(operation)
            self._update_time_based_stats(operation)
    
    def get_recent_operations(self, minutes: int = 60) -> List[CacheOperation]:
        """Get operations from the last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        with self._lock:
            return [op for op in self.operations if op.timestamp >= cutoff_time]
    
    def get_operations_by_cache_type(self, cache_type: str, hours: int = 24) -> List[CacheOperation]:
        """Get operations for specific cache type"""
        cutoff_time = time.time() - (hours * 3600)
        with self._lock:
            return [op for op in self.operations 
                   if op.cache_type == cache_type and op.timestamp >= cutoff_time]
    
    def calculate_metrics(self, start_time: float, end_time: float) -> PerformanceMetrics:
        """Calculate performance metrics for time period"""
        with self._lock:
            relevant_ops = [op for op in self.operations 
                          if start_time <= op.timestamp <= end_time]
        
        if not relevant_ops:
            return PerformanceMetrics(
                start_time=start_time,
                end_time=end_time,
                total_operations=0,
                hit_count=0,
                miss_count=0,
                hit_rate_percent=0.0,
                average_response_time_ms=0.0,
                total_cache_size_mb=0.0,
                cache_efficiency_score=0.0
            )
        
        hit_count = sum(1 for op in relevant_ops if op.operation_type == 'hit')
        miss_count = sum(1 for op in relevant_ops if op.operation_type == 'miss')
        total_operations = len(relevant_ops)
        
        hit_rate = (hit_count / max(hit_count + miss_count, 1)) * 100
        avg_response_time = statistics.mean([op.duration_ms for op in relevant_ops]) if relevant_ops else 0
        total_size = sum(op.size_bytes for op in relevant_ops) / (1024 * 1024)  # MB
        
        # Calculate efficiency score (composite of hit rate, response time, size efficiency)
        efficiency_score = self._calculate_efficiency_score(hit_rate, avg_response_time, total_size)
        
        return PerformanceMetrics(
            start_time=start_time,
            end_time=end_time,
            total_operations=total_operations,
            hit_count=hit_count,
            miss_count=miss_count,
            hit_rate_percent=hit_rate,
            average_response_time_ms=avg_response_time,
            total_cache_size_mb=total_size,
            cache_efficiency_score=efficiency_score
        )
    
    def _update_time_based_stats(self, operation: CacheOperation):
        """Update hourly and daily statistics"""
        dt = datetime.fromtimestamp(operation.timestamp)
        hour_key = dt.strftime('%Y-%m-%d-%H')
        day_key = dt.strftime('%Y-%m-%d')
        
        # Update hourly stats
        if hour_key not in self.hourly_stats:
            self.hourly_stats[hour_key] = {'hits': 0, 'misses': 0, 'operations': 0}
        
        self.hourly_stats[hour_key]['operations'] += 1
        if operation.operation_type == 'hit':
            self.hourly_stats[hour_key]['hits'] += 1
        elif operation.operation_type == 'miss':
            self.hourly_stats[hour_key]['misses'] += 1
        
        # Update daily stats
        if day_key not in self.daily_stats:
            self.daily_stats[day_key] = {'hits': 0, 'misses': 0, 'operations': 0}
        
        self.daily_stats[day_key]['operations'] += 1
        if operation.operation_type == 'hit':
            self.daily_stats[day_key]['hits'] += 1
        elif operation.operation_type == 'miss':
            self.daily_stats[day_key]['misses'] += 1
    
    def _calculate_efficiency_score(self, hit_rate: float, avg_response_ms: float, size_mb: float) -> float:
        """Calculate composite efficiency score (0-100)"""
        # Hit rate component (40% weight)
        hit_rate_score = min(hit_rate, 100) * 0.4
        
        # Response time component (30% weight) - lower is better
        response_time_score = max(0, 100 - (avg_response_ms / 10)) * 0.3
        
        # Size efficiency component (30% weight) - reasonable cache size
        ideal_size_mb = 100  # Assume 100MB is ideal cache size
        size_efficiency = max(0, 100 - abs(size_mb - ideal_size_mb)) * 0.3
        
        return hit_rate_score + response_time_score + size_efficiency


class CacheAnalyzer:
    """Analyzes cache performance patterns and generates recommendations"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager, 
                 performance_tracker: PerformanceTracker):
        self.cache_manager = cache_manager
        self.performance_tracker = performance_tracker
    
    def analyze_cache_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze cache usage patterns"""
        cutoff_time = time.time() - (hours * 3600)
        recent_ops = [op for op in self.performance_tracker.operations 
                     if op.timestamp >= cutoff_time]
        
        if not recent_ops:
            return {"error": "No operations in the specified time period"}
        
        # Analyze by cache type
        cache_type_stats = defaultdict(lambda: {'hits': 0, 'misses': 0, 'total_size': 0})
        for op in recent_ops:
            stats = cache_type_stats[op.cache_type]
            if op.operation_type == 'hit':
                stats['hits'] += 1
            elif op.operation_type == 'miss':
                stats['misses'] += 1
            stats['total_size'] += op.size_bytes
        
        # Analyze by time of day
        hourly_patterns = defaultdict(lambda: {'operations': 0, 'hit_rate': 0})
        for op in recent_ops:
            hour = datetime.fromtimestamp(op.timestamp).hour
            hourly_patterns[hour]['operations'] += 1
        
        # Calculate hit rates
        for cache_type, stats in cache_type_stats.items():
            total_requests = stats['hits'] + stats['misses']
            stats['hit_rate'] = (stats['hits'] / max(total_requests, 1)) * 100
            stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
        
        return {
            "analysis_period_hours": hours,
            "total_operations": len(recent_ops),
            "cache_type_performance": dict(cache_type_stats),
            "hourly_patterns": dict(hourly_patterns),
            "most_active_cache_types": self._get_most_active_cache_types(cache_type_stats),
            "performance_trends": self._analyze_performance_trends(recent_ops)
        }
    
    def generate_recommendations(self) -> List[CacheRecommendation]:
        """Generate cache optimization recommendations"""
        recommendations = []
        
        # Analyze recent performance
        metrics_24h = self.performance_tracker.calculate_metrics(
            time.time() - 86400, time.time()
        )
        
        # Low hit rate recommendation
        if metrics_24h.hit_rate_percent < 60:
            recommendations.append(CacheRecommendation(
                recommendation_type="hit_rate_optimization",
                priority="high",
                title="Improve Cache Hit Rate",
                description=f"Current hit rate is {metrics_24h.hit_rate_percent:.1f}%, which is below optimal threshold of 80%",
                estimated_improvement="20-40% performance boost",
                action_items=[
                    "Analyze frequently accessed data patterns",
                    "Increase cache size for hot data",
                    "Implement predictive cache preloading",
                    "Review cache invalidation strategy"
                ]
            ))
        
        # High response time recommendation
        if metrics_24h.average_response_time_ms > 50:
            recommendations.append(CacheRecommendation(
                recommendation_type="response_time_optimization",
                priority="medium",
                title="Reduce Cache Response Time",
                description=f"Average response time is {metrics_24h.average_response_time_ms:.1f}ms, target is <20ms",
                estimated_improvement="50-70% faster responses",
                action_items=[
                    "Optimize cache data structures",
                    "Implement cache compression",
                    "Use memory-based caching for hot data",
                    "Review serialization performance"
                ]
            ))
        
        # Cache size optimization
        cache_size_info = self.cache_manager.get_cache_size_info()
        total_size = cache_size_info.get("total_cache_mb", 0)
        
        if total_size > 500:  # Large cache
            recommendations.append(CacheRecommendation(
                recommendation_type="storage_optimization",
                priority="medium",
                title="Optimize Cache Storage",
                description=f"Cache size is {total_size:.1f}MB, consider optimization",
                estimated_improvement="20-50% storage reduction",
                action_items=[
                    "Remove stale cache entries",
                    "Implement cache compression",
                    "Review cache retention policies",
                    "Archive rarely accessed data"
                ]
            ))
        
        elif total_size < 10:  # Very small cache
            recommendations.append(CacheRecommendation(
                recommendation_type="cache_utilization",
                priority="low",
                title="Increase Cache Utilization",
                description=f"Cache size is only {total_size:.1f}MB, may be underutilized",
                estimated_improvement="Better performance through caching",
                action_items=[
                    "Cache more frequently accessed data",
                    "Implement proactive caching",
                    "Review what data should be cached",
                    "Increase cache retention periods"
                ]
            ))
        
        # ML model sharing optimization
        global_cache_size = cache_size_info.get("global_cache_mb", 0)
        if global_cache_size > 0:
            recommendations.append(CacheRecommendation(
                recommendation_type="ml_model_optimization",
                priority="low",
                title="ML Model Sharing Efficiency",
                description=f"Global cache contains {global_cache_size:.1f}MB of shared ML models",
                estimated_improvement="Storage savings across projects",
                action_items=[
                    "Verify model sharing across projects",
                    "Clean up unused models",
                    "Monitor model usage patterns",
                    "Consider model quantization"
                ]
            ))
        
        return recommendations
    
    def _get_most_active_cache_types(self, cache_type_stats: Dict) -> List[Dict[str, Any]]:
        """Get most active cache types by operation count"""
        cache_types = []
        for cache_type, stats in cache_type_stats.items():
            total_ops = stats['hits'] + stats['misses']
            cache_types.append({
                "cache_type": cache_type,
                "operations": total_ops,
                "hit_rate": stats['hit_rate'],
                "size_mb": stats['total_size_mb']
            })
        
        return sorted(cache_types, key=lambda x: x['operations'], reverse=True)[:5]
    
    def _analyze_performance_trends(self, operations: List[CacheOperation]) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(operations) < 10:
            return {"error": "Insufficient data for trend analysis"}
        
        # Split operations into time buckets
        bucket_size = max(1, len(operations) // 10)  # 10 buckets
        buckets = []
        
        for i in range(0, len(operations), bucket_size):
            bucket_ops = operations[i:i + bucket_size]
            hit_count = sum(1 for op in bucket_ops if op.operation_type == 'hit')
            miss_count = sum(1 for op in bucket_ops if op.operation_type == 'miss')
            hit_rate = (hit_count / max(hit_count + miss_count, 1)) * 100
            
            avg_response = statistics.mean([op.duration_ms for op in bucket_ops]) if bucket_ops else 0
            
            buckets.append({
                "hit_rate": hit_rate,
                "avg_response_ms": avg_response,
                "operations": len(bucket_ops)
            })
        
        # Calculate trends
        hit_rates = [b['hit_rate'] for b in buckets]
        response_times = [b['avg_response_ms'] for b in buckets]
        
        hit_rate_trend = "improving" if hit_rates[-1] > hit_rates[0] else "declining"
        response_trend = "improving" if response_times[-1] < response_times[0] else "declining"
        
        return {
            "hit_rate_trend": hit_rate_trend,
            "response_time_trend": response_trend,
            "trend_buckets": buckets,
            "avg_hit_rate": statistics.mean(hit_rates),
            "avg_response_time": statistics.mean(response_times)
        }


class CachePerformanceDashboard:
    """Comprehensive cache performance dashboard"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 content_validator: ContentHashValidator = None,
                 symbol_cache: LanguageAwareSymbolCache = None):
        self.cache_manager = cache_manager
        self.content_validator = content_validator
        self.symbol_cache = symbol_cache
        self.performance_tracker = PerformanceTracker()
        self.analyzer = CacheAnalyzer(cache_manager, self.performance_tracker)
        
        # Initialize analytics storage
        self.analytics_path = cache_manager.project_cache_root / "analytics"
        self.analytics_path.mkdir(parents=True, exist_ok=True)
    
    def record_cache_operation(self, operation_type: str, cache_type: str, 
                              cache_level: str, key: str, duration_ms: float = 0.0,
                              size_bytes: int = 0, content_hash: str = ""):
        """Record a cache operation for analytics"""
        operation = CacheOperation(
            timestamp=time.time(),
            operation_type=operation_type,
            cache_type=cache_type,
            cache_level=cache_level,
            key=key,
            duration_ms=duration_ms,
            size_bytes=size_bytes,
            content_hash=content_hash
        )
        self.performance_tracker.record_operation(operation)
    
    def generate_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate performance report"""
        base_report = {
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "cache_manager_stats": self.cache_manager.get_performance_stats(),
            "cache_size_info": self.cache_manager.get_cache_size_info()
        }
        
        if report_type in ["comprehensive", "performance"]:
            # Performance metrics
            metrics_1h = self.performance_tracker.calculate_metrics(
                time.time() - 3600, time.time()
            )
            metrics_24h = self.performance_tracker.calculate_metrics(
                time.time() - 86400, time.time()
            )
            
            base_report.update({
                "performance_metrics": {
                    "last_hour": asdict(metrics_1h),
                    "last_24_hours": asdict(metrics_24h)
                },
                "cache_patterns": self.analyzer.analyze_cache_patterns(24),
                "recommendations": [asdict(rec) for rec in self.analyzer.generate_recommendations()]
            })
        
        if report_type in ["comprehensive", "dependencies"] and self.content_validator:
            base_report["dependency_tracking"] = self.content_validator.get_dependency_stats()
        
        if report_type in ["comprehensive", "symbols"] and self.symbol_cache:
            base_report["symbol_cache_stats"] = self.symbol_cache.get_cache_statistics()
        
        if report_type == "comprehensive":
            base_report["ml_model_savings"] = self._calculate_ml_model_savings()
            base_report["storage_optimization"] = self._analyze_storage_optimization()
        
        return base_report
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time performance statistics"""
        recent_ops = self.performance_tracker.get_recent_operations(5)  # Last 5 minutes
        
        if not recent_ops:
            return {
                "status": "no_recent_activity",
                "last_5_minutes": {
                    "operations": 0,
                    "hit_rate": 0,
                    "avg_response_ms": 0
                }
            }
        
        hit_count = sum(1 for op in recent_ops if op.operation_type == 'hit')
        miss_count = sum(1 for op in recent_ops if op.operation_type == 'miss')
        hit_rate = (hit_count / max(hit_count + miss_count, 1)) * 100
        avg_response = statistics.mean([op.duration_ms for op in recent_ops]) if recent_ops else 0
        
        return {
            "status": "active",
            "last_5_minutes": {
                "operations": len(recent_ops),
                "hit_rate": hit_rate,
                "avg_response_ms": avg_response,
                "cache_levels": {
                    "global": sum(1 for op in recent_ops if op.cache_level == 'global'),
                    "project": sum(1 for op in recent_ops if op.cache_level == 'project')
                }
            },
            "cache_health": self._assess_cache_health()
        }
    
    def save_analytics_snapshot(self) -> str:
        """Save current analytics state to disk"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_file = self.analytics_path / f"snapshot_{timestamp}.json"
        
        snapshot = {
            "timestamp": timestamp,
            "performance_report": self.generate_report("comprehensive"),
            "recent_operations": [asdict(op) for op in self.performance_tracker.get_recent_operations(60)],
            "hourly_stats": dict(self.performance_tracker.hourly_stats),
            "daily_stats": dict(self.performance_tracker.daily_stats)
        }
        
        try:
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)
            return str(snapshot_file)
        except Exception:
            return ""
    
    def _calculate_ml_model_savings(self) -> Dict[str, Any]:
        """Calculate savings from ML model sharing"""
        cache_size_info = self.cache_manager.get_cache_size_info()
        global_cache_mb = cache_size_info.get("global_cache_mb", 0)
        
        # Estimate savings based on typical ML model sizes
        typical_model_size_mb = 178  # Based on architecture document
        estimated_projects = 3  # Conservative estimate
        
        if global_cache_mb > 0:
            savings_mb = max(0, (estimated_projects - 1) * typical_model_size_mb)
            savings_percent = (savings_mb / (global_cache_mb + savings_mb)) * 100 if global_cache_mb > 0 else 0
            
            return {
                "shared_models_mb": global_cache_mb,
                "estimated_savings_mb": savings_mb,
                "savings_percent": savings_percent,
                "estimated_projects": estimated_projects
            }
        
        return {"shared_models_mb": 0, "estimated_savings_mb": 0, "savings_percent": 0}
    
    def _analyze_storage_optimization(self) -> Dict[str, Any]:
        """Analyze storage optimization opportunities"""
        # This would analyze cache contents for optimization opportunities
        return {
            "optimization_opportunities": [
                "Compress large cache entries",
                "Remove duplicate data",
                "Archive old cache entries"
            ],
            "estimated_reduction_mb": 50,  # Placeholder
            "priority": "medium"
        }
    
    def _assess_cache_health(self) -> str:
        """Assess overall cache health"""
        metrics = self.performance_tracker.calculate_metrics(
            time.time() - 3600, time.time()
        )
        
        if metrics.total_operations == 0:
            return "idle"
        elif metrics.hit_rate_percent > 80 and metrics.average_response_time_ms < 20:
            return "excellent"
        elif metrics.hit_rate_percent > 60 and metrics.average_response_time_ms < 50:
            return "good"
        elif metrics.hit_rate_percent > 40:
            return "fair"
        else:
            return "poor"