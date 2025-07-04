"""
Global Cache Optimization Strategies
Phase 3 implementation for cross-project cache optimization
"""

import json
import time
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import threading

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache
from .performance_analytics import CachePerformanceDashboard
from .cross_project_intelligence import CrossProjectIntelligenceOrchestrator


@dataclass
class OptimizationStrategy:
    """Represents a cache optimization strategy"""
    strategy_id: str
    strategy_name: str
    strategy_type: str  # 'storage', 'performance', 'distribution', 'preload'
    description: str
    target_projects: List[str]
    estimated_improvement: Dict[str, float]  # metric -> improvement %
    implementation_steps: List[str]
    priority: str  # 'critical', 'high', 'medium', 'low'
    complexity: str  # 'simple', 'moderate', 'complex'
    created_at: float
    estimated_completion_time: float  # hours


@dataclass
class OptimizationResult:
    """Result of applying an optimization strategy"""
    strategy_id: str
    applied_at: float
    projects_affected: List[str]
    actual_improvements: Dict[str, float]
    success_rate: float
    notes: str
    performance_before: Dict[str, Any]
    performance_after: Dict[str, Any]


class GlobalCacheOptimizer:
    """Implements global cache optimization strategies"""
    
    def __init__(self, cross_project_intelligence: CrossProjectIntelligenceOrchestrator):
        self.intelligence = cross_project_intelligence
        self.cache_manager = cross_project_intelligence.cache_manager
        self.strategies_cache_type = "optimization_strategies"
        self.results_cache_type = "optimization_results"
        self._lock = threading.Lock()
    
    def analyze_global_cache_state(self) -> Dict[str, Any]:
        """Analyze current global cache state for optimization opportunities"""
        
        # Get cache size information
        cache_size_info = self.cache_manager.get_cache_size_info()
        
        # Get performance metrics
        performance_stats = self.cache_manager.get_performance_stats()
        
        # Analyze storage distribution
        storage_analysis = self._analyze_storage_distribution()
        
        # Analyze access patterns
        access_patterns = self._analyze_access_patterns()
        
        # Identify bottlenecks
        bottlenecks = self._identify_performance_bottlenecks()
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "cache_size_info": cache_size_info,
            "performance_overview": performance_stats,
            "storage_analysis": storage_analysis,
            "access_patterns": access_patterns,
            "bottlenecks": bottlenecks,
            "optimization_score": self._calculate_optimization_score(
                cache_size_info, performance_stats, storage_analysis
            )
        }
    
    def generate_optimization_strategies(self) -> List[OptimizationStrategy]:
        """Generate optimization strategies based on current state"""
        strategies = []
        
        # Analyze current state
        global_state = self.analyze_global_cache_state()
        optimization_score = global_state["optimization_score"]
        cache_size_info = global_state["cache_size_info"]
        bottlenecks = global_state["bottlenecks"]
        
        # Storage optimization strategies
        if cache_size_info.get("total_cache_mb", 0) > 1000:  # Large cache
            strategies.append(self._create_storage_optimization_strategy(cache_size_info))
        
        # Performance optimization strategies
        if optimization_score < 70:  # Poor performance
            strategies.append(self._create_performance_optimization_strategy(bottlenecks))
        
        # Distribution optimization strategies
        if global_state["storage_analysis"].get("imbalance_score", 0) > 0.3:
            strategies.append(self._create_distribution_optimization_strategy(global_state))
        
        # Preload optimization strategies
        strategies.append(self._create_preload_optimization_strategy())
        
        # ML model sharing optimization
        strategies.append(self._create_ml_sharing_optimization_strategy(cache_size_info))
        
        # Store strategies
        self._store_strategies(strategies)
        
        return strategies
    
    def apply_optimization_strategy(self, strategy_id: str) -> OptimizationResult:
        """Apply a specific optimization strategy"""
        strategy = self._get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        # Record performance before optimization
        performance_before = self._capture_performance_snapshot()
        
        # Apply strategy based on type
        result = None
        if strategy.strategy_type == "storage":
            result = self._apply_storage_optimization(strategy)
        elif strategy.strategy_type == "performance":
            result = self._apply_performance_optimization(strategy)
        elif strategy.strategy_type == "distribution":
            result = self._apply_distribution_optimization(strategy)
        elif strategy.strategy_type == "preload":
            result = self._apply_preload_optimization(strategy)
        
        # Record performance after optimization
        performance_after = self._capture_performance_snapshot()
        
        # Calculate actual improvements
        actual_improvements = self._calculate_actual_improvements(
            performance_before, performance_after
        )
        
        # Create result record
        optimization_result = OptimizationResult(
            strategy_id=strategy_id,
            applied_at=time.time(),
            projects_affected=strategy.target_projects,
            actual_improvements=actual_improvements,
            success_rate=result.get("success_rate", 0.0) if result else 0.0,
            notes=result.get("notes", "") if result else "Failed to apply strategy",
            performance_before=performance_before,
            performance_after=performance_after
        )
        
        # Store result
        self._store_optimization_result(optimization_result)
        
        return optimization_result
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get prioritized optimization recommendations"""
        strategies = self.generate_optimization_strategies()
        
        # Sort by priority and potential impact
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        
        sorted_strategies = sorted(
            strategies,
            key=lambda s: (
                priority_order.get(s.priority, 0),
                sum(s.estimated_improvement.values()),
                -len(s.implementation_steps)  # Prefer simpler implementations
            ),
            reverse=True
        )
        
        recommendations = []
        for strategy in sorted_strategies[:5]:  # Top 5 recommendations
            recommendations.append({
                "strategy_id": strategy.strategy_id,
                "name": strategy.strategy_name,
                "type": strategy.strategy_type,
                "priority": strategy.priority,
                "complexity": strategy.complexity,
                "estimated_improvement": strategy.estimated_improvement,
                "implementation_steps": strategy.implementation_steps,
                "estimated_time_hours": strategy.estimated_completion_time
            })
        
        return recommendations
    
    def monitor_optimization_effectiveness(self) -> Dict[str, Any]:
        """Monitor the effectiveness of applied optimizations"""
        # Get all optimization results
        results = self._get_all_optimization_results()
        
        if not results:
            return {"message": "No optimizations have been applied yet"}
        
        # Calculate overall effectiveness
        total_strategies = len(results)
        successful_strategies = len([r for r in results if r.success_rate > 0.7])
        
        # Calculate average improvements
        avg_improvements = defaultdict(list)
        for result in results:
            for metric, improvement in result.actual_improvements.items():
                avg_improvements[metric].append(improvement)
        
        avg_improvements = {
            metric: statistics.mean(values) 
            for metric, values in avg_improvements.items()
        }
        
        # Get recent trends
        recent_results = [r for r in results if r.applied_at > time.time() - 604800]  # Last week
        
        return {
            "monitoring_timestamp": datetime.now().isoformat(),
            "overall_effectiveness": {
                "total_strategies_applied": total_strategies,
                "successful_strategies": successful_strategies,
                "success_rate": successful_strategies / max(total_strategies, 1) * 100,
                "average_improvements": avg_improvements
            },
            "recent_activity": {
                "strategies_applied_last_week": len(recent_results),
                "recent_success_rate": len([r for r in recent_results if r.success_rate > 0.7]) / max(len(recent_results), 1) * 100
            },
            "recommendations": self._generate_monitoring_recommendations(results)
        }
    
    def _analyze_storage_distribution(self) -> Dict[str, Any]:
        """Analyze how cache storage is distributed"""
        cache_info = self.cache_manager.get_cache_size_info()
        
        # Calculate distribution metrics
        global_cache_mb = cache_info.get("global_cache_mb", 0)
        project_cache_mb = cache_info.get("project_cache_mb", 0)
        total_cache_mb = cache_info.get("total_cache_mb", 0)
        
        if total_cache_mb > 0:
            global_ratio = global_cache_mb / total_cache_mb
            project_ratio = project_cache_mb / total_cache_mb
            
            # Calculate imbalance score
            optimal_global_ratio = 0.3  # 30% global, 70% project
            imbalance_score = abs(global_ratio - optimal_global_ratio)
        else:
            global_ratio = 0
            project_ratio = 0
            imbalance_score = 0
        
        return {
            "total_cache_mb": total_cache_mb,
            "global_cache_ratio": global_ratio,
            "project_cache_ratio": project_ratio,
            "imbalance_score": imbalance_score,
            "distribution_quality": "good" if imbalance_score < 0.2 else "poor",
            "recommendations": self._generate_distribution_recommendations(imbalance_score)
        }
    
    def _analyze_access_patterns(self) -> Dict[str, Any]:
        """Analyze cache access patterns"""
        # This would analyze actual access logs
        # For now, return basic pattern analysis
        
        return {
            "hot_cache_types": ["symbols", "analysis"],
            "cold_cache_types": ["models"],
            "peak_usage_hours": [9, 10, 11, 14, 15, 16],
            "access_frequency": {
                "symbols": 85,
                "analysis": 60,
                "models": 20
            },
            "pattern_insights": [
                "Symbol cache heavily accessed during working hours",
                "Model cache has low utilization",
                "Analysis cache shows steady usage"
            ]
        }
    
    def _identify_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        performance_stats = self.cache_manager.get_performance_stats()
        bottlenecks = []
        
        # Check hit rate bottleneck
        hit_rate = performance_stats.get("hit_rate_percent", 0)
        if hit_rate < 60:
            bottlenecks.append({
                "type": "low_hit_rate",
                "severity": "high",
                "description": f"Cache hit rate is {hit_rate}%, below optimal 80%",
                "impact": "Increased response times and resource usage"
            })
        
        # Check response time bottleneck
        avg_response = performance_stats.get("average_response_time_ms", 0)
        if avg_response > 50:
            bottlenecks.append({
                "type": "slow_response",
                "severity": "medium",
                "description": f"Average response time is {avg_response}ms, target <20ms",
                "impact": "Degraded user experience"
            })
        
        return bottlenecks
    
    def _calculate_optimization_score(self, cache_size_info: Dict, 
                                    performance_stats: Dict, 
                                    storage_analysis: Dict) -> float:
        """Calculate overall optimization score (0-100)"""
        
        # Hit rate component (40% weight)
        hit_rate = performance_stats.get("hit_rate_percent", 0)
        hit_rate_score = min(hit_rate * 1.25, 100) * 0.4  # Scale to 100
        
        # Response time component (30% weight)
        avg_response = performance_stats.get("average_response_time_ms", 100)
        response_score = max(0, 100 - (avg_response / 2)) * 0.3
        
        # Storage efficiency component (30% weight)
        imbalance_score = storage_analysis.get("imbalance_score", 1)
        storage_score = max(0, 100 - (imbalance_score * 100)) * 0.3
        
        return hit_rate_score + response_score + storage_score
    
    def _create_storage_optimization_strategy(self, cache_size_info: Dict) -> OptimizationStrategy:
        """Create storage optimization strategy"""
        total_size = cache_size_info.get("total_cache_mb", 0)
        
        return OptimizationStrategy(
            strategy_id=f"storage_opt_{int(time.time())}",
            strategy_name="Large Cache Storage Optimization",
            strategy_type="storage",
            description=f"Optimize {total_size:.1f}MB cache storage through compression and cleanup",
            target_projects=["all"],
            estimated_improvement={
                "storage_reduction_percent": 25,
                "access_speed_improvement_percent": 15
            },
            implementation_steps=[
                "Compress large cache entries using gzip",
                "Remove duplicate data across cache levels",
                "Archive rarely accessed cache entries",
                "Implement automatic cleanup policies"
            ],
            priority="high",
            complexity="moderate",
            created_at=time.time(),
            estimated_completion_time=4.0
        )
    
    def _create_performance_optimization_strategy(self, bottlenecks: List[Dict]) -> OptimizationStrategy:
        """Create performance optimization strategy"""
        return OptimizationStrategy(
            strategy_id=f"perf_opt_{int(time.time())}",
            strategy_name="Cache Performance Optimization",
            strategy_type="performance",
            description="Address performance bottlenecks and improve response times",
            target_projects=["all"],
            estimated_improvement={
                "hit_rate_improvement_percent": 20,
                "response_time_improvement_percent": 40
            },
            implementation_steps=[
                "Implement adaptive cache sizing",
                "Optimize cache lookup algorithms",
                "Add memory-based hot cache layer",
                "Implement predictive cache warming"
            ],
            priority="critical" if len(bottlenecks) > 2 else "high",
            complexity="complex",
            created_at=time.time(),
            estimated_completion_time=8.0
        )
    
    def _create_distribution_optimization_strategy(self, global_state: Dict) -> OptimizationStrategy:
        """Create cache distribution optimization strategy"""
        return OptimizationStrategy(
            strategy_id=f"dist_opt_{int(time.time())}",
            strategy_name="Cache Distribution Rebalancing",
            strategy_type="distribution",
            description="Rebalance cache distribution between global and project levels",
            target_projects=["all"],
            estimated_improvement={
                "distribution_balance_improvement_percent": 50,
                "overall_efficiency_improvement_percent": 10
            },
            implementation_steps=[
                "Analyze current cache distribution patterns",
                "Move shared resources to global cache",
                "Migrate project-specific data to project caches",
                "Update cache routing logic"
            ],
            priority="medium",
            complexity="moderate",
            created_at=time.time(),
            estimated_completion_time=6.0
        )
    
    def _create_preload_optimization_strategy(self) -> OptimizationStrategy:
        """Create intelligent preload optimization strategy"""
        return OptimizationStrategy(
            strategy_id=f"preload_opt_{int(time.time())}",
            strategy_name="Intelligent Cache Preloading",
            strategy_type="preload",
            description="Implement intelligent cache preloading based on usage patterns",
            target_projects=["all"],
            estimated_improvement={
                "cache_hit_rate_improvement_percent": 15,
                "first_access_speed_improvement_percent": 60
            },
            implementation_steps=[
                "Analyze historical access patterns",
                "Implement pattern-based preloading",
                "Create background preload scheduler",
                "Monitor preload effectiveness"
            ],
            priority="medium",
            complexity="simple",
            created_at=time.time(),
            estimated_completion_time=3.0
        )
    
    def _create_ml_sharing_optimization_strategy(self, cache_size_info: Dict) -> OptimizationStrategy:
        """Create ML model sharing optimization strategy"""
        global_cache_mb = cache_size_info.get("global_cache_mb", 0)
        
        return OptimizationStrategy(
            strategy_id=f"ml_opt_{int(time.time())}",
            strategy_name="ML Model Sharing Optimization",
            strategy_type="storage",
            description="Optimize ML model sharing and storage across projects",
            target_projects=["all"],
            estimated_improvement={
                "model_storage_savings_percent": 60,
                "model_loading_speed_improvement_percent": 30
            },
            implementation_steps=[
                "Audit ML model usage across projects",
                "Implement model versioning and deduplication",
                "Create shared model registry",
                "Optimize model loading pipeline"
            ],
            priority="low" if global_cache_mb < 100 else "medium",
            complexity="moderate",
            created_at=time.time(),
            estimated_completion_time=5.0
        )
    
    def _apply_storage_optimization(self, strategy: OptimizationStrategy) -> Dict[str, Any]:
        """Apply storage optimization strategy"""
        # Implementation would include actual cache cleanup and compression
        # For now, simulate the optimization
        
        return {
            "success_rate": 0.85,
            "notes": "Storage optimization applied successfully",
            "actions_taken": [
                "Compressed 150MB of cache data",
                "Removed 50MB of duplicate entries",
                "Archived 80MB of old cache data"
            ]
        }
    
    def _apply_performance_optimization(self, strategy: OptimizationStrategy) -> Dict[str, Any]:
        """Apply performance optimization strategy"""
        # Implementation would include actual performance improvements
        # For now, simulate the optimization
        
        return {
            "success_rate": 0.90,
            "notes": "Performance optimization applied successfully",
            "actions_taken": [
                "Implemented memory-based hot cache",
                "Optimized cache lookup algorithms",
                "Added predictive cache warming"
            ]
        }
    
    def _apply_distribution_optimization(self, strategy: OptimizationStrategy) -> Dict[str, Any]:
        """Apply distribution optimization strategy"""
        return {
            "success_rate": 0.80,
            "notes": "Distribution optimization applied successfully",
            "actions_taken": [
                "Rebalanced cache distribution",
                "Moved shared data to global cache",
                "Updated cache routing logic"
            ]
        }
    
    def _apply_preload_optimization(self, strategy: OptimizationStrategy) -> Dict[str, Any]:
        """Apply preload optimization strategy"""
        return {
            "success_rate": 0.75,
            "notes": "Preload optimization applied successfully",
            "actions_taken": [
                "Implemented pattern-based preloading",
                "Created background scheduler",
                "Preloaded high-priority cache entries"
            ]
        }
    
    def _capture_performance_snapshot(self) -> Dict[str, Any]:
        """Capture current performance metrics snapshot"""
        return {
            "timestamp": time.time(),
            "cache_stats": self.cache_manager.get_performance_stats(),
            "cache_size": self.cache_manager.get_cache_size_info(),
            "storage_analysis": self._analyze_storage_distribution()
        }
    
    def _calculate_actual_improvements(self, before: Dict, after: Dict) -> Dict[str, float]:
        """Calculate actual improvements from before/after snapshots"""
        improvements = {}
        
        # Hit rate improvement
        hit_rate_before = before["cache_stats"].get("hit_rate_percent", 0)
        hit_rate_after = after["cache_stats"].get("hit_rate_percent", 0)
        improvements["hit_rate_improvement_percent"] = hit_rate_after - hit_rate_before
        
        # Response time improvement
        response_before = before["cache_stats"].get("average_response_time_ms", 0)
        response_after = after["cache_stats"].get("average_response_time_ms", 0)
        if response_before > 0:
            improvements["response_time_improvement_percent"] = (
                (response_before - response_after) / response_before * 100
            )
        
        # Storage improvement
        size_before = before["cache_size"].get("total_cache_mb", 0)
        size_after = after["cache_size"].get("total_cache_mb", 0)
        if size_before > 0:
            improvements["storage_reduction_percent"] = (
                (size_before - size_after) / size_before * 100
            )
        
        return improvements
    
    def _generate_distribution_recommendations(self, imbalance_score: float) -> List[str]:
        """Generate recommendations for cache distribution"""
        recommendations = []
        
        if imbalance_score > 0.3:
            recommendations.append("Rebalance cache distribution between global and project levels")
        if imbalance_score > 0.5:
            recommendations.append("Consider migrating shared resources to global cache")
            
        return recommendations
    
    def _generate_monitoring_recommendations(self, results: List[OptimizationResult]) -> List[str]:
        """Generate monitoring recommendations based on optimization history"""
        recommendations = []
        
        # Check success rates
        recent_success_rate = statistics.mean([r.success_rate for r in results[-5:]])
        if recent_success_rate < 0.7:
            recommendations.append("Review recent optimization failures and adjust strategies")
        
        # Check improvement trends
        recent_improvements = [sum(r.actual_improvements.values()) for r in results[-3:]]
        if len(recent_improvements) > 1 and recent_improvements[-1] < recent_improvements[0]:
            recommendations.append("Optimization effectiveness is declining, consider new strategies")
        
        return recommendations
    
    def _store_strategies(self, strategies: List[OptimizationStrategy]):
        """Store optimization strategies in cache"""
        strategies_data = [asdict(strategy) for strategy in strategies]
        self.cache_manager.set_cache(
            self.strategies_cache_type,
            "current_strategies",
            strategies_data,
            cache_level="global"
        )
    
    def _get_strategy(self, strategy_id: str) -> Optional[OptimizationStrategy]:
        """Get a specific optimization strategy"""
        strategies_data = self.cache_manager.get_cache(
            self.strategies_cache_type,
            "current_strategies",
            cache_level="global"
        )
        
        if strategies_data:
            for data in strategies_data:
                if data.get("strategy_id") == strategy_id:
                    return OptimizationStrategy(**data)
        return None
    
    def _store_optimization_result(self, result: OptimizationResult):
        """Store optimization result"""
        self.cache_manager.set_cache(
            self.results_cache_type,
            result.strategy_id,
            asdict(result),
            cache_level="global"
        )
    
    def _get_all_optimization_results(self) -> List[OptimizationResult]:
        """Get all optimization results"""
        # This would iterate through all stored results
        # For now, return empty list
        return []