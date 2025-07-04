"""
Adaptive Preloading System
Phase 4 implementation for intelligent cache preloading with dynamic strategy adjustment
Learns from usage patterns and adapts preloading strategies automatically
"""

import json
import time
import numpy as np
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter, deque
import threading
import hashlib
import math

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard
from .ml_powered_analytics import MLPatternRecognition
from .predictive_analytics import PredictiveAnalyticsOrchestrator


@dataclass
class PreloadingStrategy:
    """Represents a cache preloading strategy"""
    strategy_id: str
    strategy_name: str
    strategy_type: str  # 'pattern_based', 'time_based', 'usage_based', 'predictive'
    target_cache_types: List[str]
    priority: str  # 'critical', 'high', 'medium', 'low'
    trigger_conditions: List[str]
    preload_rules: Dict[str, Any]
    effectiveness_score: float
    resource_cost: float
    adaptation_parameters: Dict[str, Any]
    created_at: float
    last_updated: float
    success_metrics: Dict[str, float]


@dataclass
class PreloadingDecision:
    """Decision to preload specific cache entries"""
    decision_id: str
    strategy_id: str
    target_files: List[str]
    cache_types: List[str]
    priority_score: float
    confidence: float
    estimated_benefit: Dict[str, float]
    resource_requirements: Dict[str, Any]
    trigger_context: Dict[str, Any]
    decision_timestamp: float
    execution_window: Tuple[float, float]  # Start and end times


@dataclass
class PreloadingExecution:
    """Execution of a preloading decision"""
    execution_id: str
    decision_id: str
    started_at: float
    completed_at: Optional[float]
    status: str  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    files_preloaded: List[str]
    cache_entries_created: int
    actual_benefit: Optional[Dict[str, float]]
    execution_logs: List[str]
    performance_impact: Dict[str, float]


class UsagePatternAnalyzer:
    """Analyzes usage patterns to inform preloading strategies"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.patterns_cache_type = "usage_patterns"
        self._lock = threading.Lock()
        
        # Pattern storage
        self.access_patterns = defaultdict(lambda: deque(maxlen=1000))
        self.temporal_patterns = defaultdict(list)
        self.sequence_patterns = defaultdict(list)
        
        # ML components
        self.ml_available = SKLEARN_AVAILABLE
        if self.ml_available:
            self.pattern_clusterer = KMeans(n_clusters=5, random_state=42)
            self.scaler = StandardScaler()
    
    def analyze_access_patterns(self, lookback_hours: int = 24) -> Dict[str, Any]:
        """Analyze file access patterns"""
        current_time = time.time()
        start_time = current_time - (lookback_hours * 3600)
        
        # Get recent operations
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            lookback_hours * 60
        )
        
        # Group by file and analyze patterns
        file_access_patterns = defaultdict(list)
        for op in operations:
            if op.file_path and op.timestamp >= start_time:
                file_access_patterns[op.file_path].append({
                    "timestamp": op.timestamp,
                    "operation_type": op.operation_type,
                    "duration_ms": op.duration_ms,
                    "cache_type": op.cache_type
                })
        
        patterns = {}
        for file_path, accesses in file_access_patterns.items():
            if len(accesses) >= 3:  # Minimum for pattern analysis
                patterns[file_path] = self._analyze_file_access_pattern(accesses)
        
        return patterns
    
    def detect_temporal_patterns(self, lookback_hours: int = 168) -> Dict[str, Any]:
        """Detect temporal patterns (hourly, daily, weekly)"""
        current_time = time.time()
        start_time = current_time - (lookback_hours * 3600)
        
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            lookback_hours * 60
        )
        
        # Group by time buckets
        hourly_patterns = defaultdict(list)
        daily_patterns = defaultdict(list)
        
        for op in operations:
            if op.timestamp >= start_time:
                hour_bucket = int((op.timestamp % 86400) / 3600)  # Hour of day
                day_bucket = int((op.timestamp / 86400) % 7)      # Day of week
                
                hourly_patterns[hour_bucket].append(op)
                daily_patterns[day_bucket].append(op)
        
        return {
            "hourly_patterns": self._analyze_temporal_bucket_patterns(hourly_patterns, "hourly"),
            "daily_patterns": self._analyze_temporal_bucket_patterns(daily_patterns, "daily"),
            "peak_hours": self._identify_peak_hours(hourly_patterns),
            "usage_trends": self._identify_usage_trends(operations)
        }
    
    def discover_sequence_patterns(self, min_support: float = 0.1) -> List[Dict[str, Any]]:
        """Discover sequential access patterns"""
        # Get recent operations
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            24 * 60  # Last 24 hours
        )
        
        # Group by user session (simplified as time windows)
        session_duration = 3600  # 1 hour sessions
        sessions = self._group_operations_into_sessions(operations, session_duration)
        
        # Find frequent sequences
        sequence_patterns = []
        for session in sessions:
            if len(session) >= 2:
                sequences = self._extract_sequences_from_session(session)
                sequence_patterns.extend(sequences)
        
        # Count sequence frequency
        sequence_counts = Counter(sequence_patterns)
        total_sessions = len(sessions)
        
        # Filter by minimum support
        frequent_patterns = []
        for sequence, count in sequence_counts.items():
            support = count / total_sessions
            if support >= min_support:
                frequent_patterns.append({
                    "sequence": sequence,
                    "support": support,
                    "frequency": count,
                    "confidence": self._calculate_sequence_confidence(sequence, sequence_counts)
                })
        
        return sorted(frequent_patterns, key=lambda x: x["support"], reverse=True)
    
    def predict_next_accesses(self, current_file: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Predict next likely file accesses based on patterns"""
        predictions = []
        
        # Get sequence patterns involving current file
        sequence_patterns = self.discover_sequence_patterns()
        
        for pattern in sequence_patterns:
            sequence = pattern["sequence"]
            if current_file in sequence:
                # Find files that commonly follow current file
                current_index = sequence.index(current_file)
                if current_index < len(sequence) - 1:
                    next_file = sequence[current_index + 1]
                    predictions.append({
                        "file_path": next_file,
                        "probability": pattern["confidence"],
                        "pattern_support": pattern["support"],
                        "prediction_type": "sequence_based"
                    })
        
        # Add temporal predictions
        temporal_patterns = self.detect_temporal_patterns(24)
        current_hour = int((time.time() % 86400) / 3600)
        
        if current_hour in temporal_patterns["peak_hours"]:
            # During peak hours, predict commonly accessed files
            common_files = self._get_commonly_accessed_files_in_hour(current_hour)
            for file_info in common_files[:5]:  # Top 5
                predictions.append({
                    "file_path": file_info["file_path"],
                    "probability": file_info["access_probability"],
                    "prediction_type": "temporal_based"
                })
        
        # Remove duplicates and sort by probability
        unique_predictions = {}
        for pred in predictions:
            file_path = pred["file_path"]
            if file_path not in unique_predictions or pred["probability"] > unique_predictions[file_path]["probability"]:
                unique_predictions[file_path] = pred
        
        return sorted(unique_predictions.values(), key=lambda x: x["probability"], reverse=True)
    
    def _analyze_file_access_pattern(self, accesses: List[Dict]) -> Dict[str, Any]:
        """Analyze access pattern for a single file"""
        if len(accesses) < 2:
            return {"pattern_type": "insufficient_data"}
        
        # Calculate time intervals
        intervals = []
        for i in range(1, len(accesses)):
            interval = accesses[i]["timestamp"] - accesses[i-1]["timestamp"]
            intervals.append(interval)
        
        # Analyze pattern characteristics
        avg_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        # Classify pattern
        if std_interval / avg_interval < 0.3:  # Low variance
            pattern_type = "regular"
        elif avg_interval < 300:  # Less than 5 minutes
            pattern_type = "burst"
        elif avg_interval > 3600:  # More than 1 hour
            pattern_type = "occasional"
        else:
            pattern_type = "irregular"
        
        return {
            "pattern_type": pattern_type,
            "access_frequency": len(accesses),
            "average_interval_seconds": avg_interval,
            "interval_variance": std_interval,
            "total_duration_ms": sum(acc["duration_ms"] for acc in accesses),
            "cache_types_used": list(set(acc["cache_type"] for acc in accesses))
        }
    
    def _analyze_temporal_bucket_patterns(self, bucket_patterns: Dict, pattern_type: str) -> Dict[str, Any]:
        """Analyze patterns within temporal buckets"""
        bucket_stats = {}
        
        for bucket, operations in bucket_patterns.items():
            if operations:
                bucket_stats[str(bucket)] = {
                    "operation_count": len(operations),
                    "average_duration_ms": statistics.mean([op.duration_ms for op in operations]),
                    "hit_rate": len([op for op in operations if op.operation_type == "hit"]) / len(operations),
                    "unique_files": len(set(op.file_path for op in operations if op.file_path)),
                    "cache_types": list(set(op.cache_type for op in operations))
                }
        
        return bucket_stats
    
    def _identify_peak_hours(self, hourly_patterns: Dict) -> List[int]:
        """Identify peak usage hours"""
        if not hourly_patterns:
            return []
        
        operation_counts = {hour: len(ops) for hour, ops in hourly_patterns.items()}
        avg_operations = statistics.mean(operation_counts.values())
        
        peak_hours = [hour for hour, count in operation_counts.items() 
                     if count > avg_operations * 1.5]
        
        return sorted(peak_hours)
    
    def _identify_usage_trends(self, operations: List) -> Dict[str, Any]:
        """Identify usage trends over time"""
        if len(operations) < 10:
            return {"trend": "insufficient_data"}
        
        # Group operations by time buckets (hourly)
        time_buckets = defaultdict(int)
        for op in operations:
            bucket = int(op.timestamp / 3600) * 3600
            time_buckets[bucket] += 1
        
        # Calculate trend
        times = sorted(time_buckets.keys())
        counts = [time_buckets[t] for t in times]
        
        if len(counts) >= 3:
            # Simple linear trend calculation
            x = list(range(len(counts)))
            if self.ml_available:
                model = LinearRegression()
                X = np.array(x).reshape(-1, 1)
                model.fit(X, counts)
                slope = model.coef_[0]
            else:
                # Manual slope calculation
                n = len(counts)
                sum_x = sum(x)
                sum_y = sum(counts)
                sum_xy = sum(x[i] * counts[i] for i in range(n))
                sum_x2 = sum(xi ** 2 for xi in x)
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            
            if slope > 0.1:
                trend = "increasing"
            elif slope < -0.1:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "unknown"
            slope = 0
        
        return {
            "trend": trend,
            "slope": slope,
            "recent_average": statistics.mean(counts[-5:]) if len(counts) >= 5 else statistics.mean(counts),
            "volatility": statistics.stdev(counts) / statistics.mean(counts) if statistics.mean(counts) > 0 else 0
        }
    
    def _group_operations_into_sessions(self, operations: List, session_duration: int) -> List[List]:
        """Group operations into user sessions"""
        sessions = []
        current_session = []
        last_timestamp = 0
        
        sorted_operations = sorted(operations, key=lambda x: x.timestamp)
        
        for op in sorted_operations:
            if op.timestamp - last_timestamp > session_duration:
                if current_session:
                    sessions.append(current_session)
                current_session = [op]
            else:
                current_session.append(op)
            last_timestamp = op.timestamp
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _extract_sequences_from_session(self, session: List) -> List[Tuple]:
        """Extract file access sequences from a session"""
        sequences = []
        file_sequence = [op.file_path for op in session if op.file_path]
        
        # Generate sequences of length 2 and 3
        for length in [2, 3]:
            for i in range(len(file_sequence) - length + 1):
                sequence = tuple(file_sequence[i:i + length])
                sequences.append(sequence)
        
        return sequences
    
    def _calculate_sequence_confidence(self, sequence: Tuple, sequence_counts: Counter) -> float:
        """Calculate confidence for a sequence pattern"""
        if len(sequence) < 2:
            return 0.0
        
        # Confidence = P(B|A) for sequence A -> B
        prefix = sequence[:-1]
        prefix_count = sum(count for seq, count in sequence_counts.items() 
                          if seq[:len(prefix)] == prefix)
        
        if prefix_count == 0:
            return 0.0
        
        return sequence_counts[sequence] / prefix_count
    
    def _get_commonly_accessed_files_in_hour(self, hour: int) -> List[Dict[str, Any]]:
        """Get commonly accessed files during a specific hour"""
        # This would query historical data for the specific hour
        # For now, return a mock response
        return [
            {"file_path": "/common/file1.py", "access_probability": 0.8},
            {"file_path": "/common/file2.py", "access_probability": 0.6},
            {"file_path": "/common/file3.py", "access_probability": 0.4}
        ]


class StrategyAdaptationEngine:
    """Adapts preloading strategies based on effectiveness feedback"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.performance_dashboard = performance_dashboard
        self.strategies_cache_type = "preloading_strategies"
        self.executions_cache_type = "preloading_executions"
        self._lock = threading.Lock()
        
        # Strategy storage
        self.active_strategies = {}
        self.strategy_metrics = defaultdict(lambda: {
            "executions": 0,
            "successes": 0,
            "total_benefit": 0.0,
            "total_cost": 0.0,
            "last_updated": time.time()
        })
    
    def create_initial_strategies(self, usage_patterns: Dict[str, Any]) -> List[PreloadingStrategy]:
        """Create initial preloading strategies based on usage patterns"""
        strategies = []
        
        # Pattern-based strategy
        if "sequence_patterns" in usage_patterns:
            pattern_strategy = PreloadingStrategy(
                strategy_id="pattern_based_v1",
                strategy_name="Sequential Pattern Preloading",
                strategy_type="pattern_based",
                target_cache_types=["symbols", "analysis"],
                priority="high",
                trigger_conditions=["file_access_detected", "sequence_pattern_match"],
                preload_rules={
                    "min_sequence_confidence": 0.6,
                    "max_preload_files": 5,
                    "preload_depth": 2
                },
                effectiveness_score=0.7,  # Initial estimate
                resource_cost=0.3,
                adaptation_parameters={
                    "confidence_threshold_min": 0.3,
                    "confidence_threshold_max": 0.9,
                    "adjustment_step": 0.1
                },
                created_at=time.time(),
                last_updated=time.time(),
                success_metrics={}
            )
            strategies.append(pattern_strategy)
        
        # Time-based strategy
        if "temporal_patterns" in usage_patterns:
            temporal_strategy = PreloadingStrategy(
                strategy_id="temporal_based_v1",
                strategy_name="Peak Hour Preloading",
                strategy_type="time_based",
                target_cache_types=["symbols", "performance"],
                priority="medium",
                trigger_conditions=["peak_hour_approaching", "usage_trend_positive"],
                preload_rules={
                    "peak_hour_offset_minutes": 15,
                    "preload_top_files_count": 10,
                    "minimum_historical_access_count": 5
                },
                effectiveness_score=0.6,
                resource_cost=0.4,
                adaptation_parameters={
                    "offset_minutes_min": 5,
                    "offset_minutes_max": 30,
                    "files_count_min": 5,
                    "files_count_max": 20
                },
                created_at=time.time(),
                last_updated=time.time(),
                success_metrics={}
            )
            strategies.append(temporal_strategy)
        
        # Usage-based strategy
        usage_strategy = PreloadingStrategy(
            strategy_id="usage_based_v1",
            strategy_name="Frequency-Based Preloading",
            strategy_type="usage_based",
            target_cache_types=["symbols", "analysis", "performance"],
            priority="medium",
            trigger_conditions=["file_access_frequency_high", "cache_miss_rate_high"],
            preload_rules={
                "min_access_frequency": 3,
                "frequency_window_hours": 24,
                "max_preload_size_mb": 50
            },
            effectiveness_score=0.5,
            resource_cost=0.2,
            adaptation_parameters={
                "frequency_threshold_min": 1,
                "frequency_threshold_max": 10,
                "window_hours_min": 6,
                "window_hours_max": 72
            },
            created_at=time.time(),
            last_updated=time.time(),
            success_metrics={}
        )
        strategies.append(usage_strategy)
        
        # Store strategies
        self._store_strategies(strategies)
        
        return strategies
    
    def adapt_strategy(self, strategy_id: str, execution_results: List[PreloadingExecution]) -> PreloadingStrategy:
        """Adapt a strategy based on execution results"""
        strategy = self._load_strategy(strategy_id)
        if not strategy:
            return None
        
        # Analyze execution performance
        performance_metrics = self._analyze_execution_performance(execution_results)
        
        # Update strategy metrics
        self.strategy_metrics[strategy_id]["executions"] += len(execution_results)
        self.strategy_metrics[strategy_id]["successes"] += len([e for e in execution_results if e.status == "completed"])
        
        # Calculate effectiveness
        total_benefit = sum(
            sum(e.actual_benefit.values()) if e.actual_benefit else 0
            for e in execution_results
        )
        self.strategy_metrics[strategy_id]["total_benefit"] += total_benefit
        
        # Adapt strategy parameters
        adapted_strategy = self._adapt_strategy_parameters(strategy, performance_metrics)
        
        # Store updated strategy
        self._store_strategy(adapted_strategy)
        
        return adapted_strategy
    
    def evaluate_strategy_effectiveness(self, strategy_id: str, 
                                      evaluation_window_hours: int = 24) -> Dict[str, float]:
        """Evaluate strategy effectiveness"""
        metrics = self.strategy_metrics[strategy_id]
        
        # Basic effectiveness metrics
        success_rate = metrics["successes"] / max(metrics["executions"], 1)
        avg_benefit = metrics["total_benefit"] / max(metrics["executions"], 1)
        avg_cost = metrics["total_cost"] / max(metrics["executions"], 1)
        
        # Calculate ROI
        roi = (avg_benefit - avg_cost) / max(avg_cost, 0.1)
        
        # Get recent performance
        recent_executions = self._get_recent_executions(strategy_id, evaluation_window_hours)
        recent_success_rate = len([e for e in recent_executions if e.status == "completed"]) / max(len(recent_executions), 1)
        
        return {
            "overall_success_rate": success_rate,
            "recent_success_rate": recent_success_rate,
            "average_benefit": avg_benefit,
            "average_cost": avg_cost,
            "roi": roi,
            "total_executions": metrics["executions"],
            "effectiveness_trend": "improving" if recent_success_rate > success_rate else "declining"
        }
    
    def recommend_strategy_adjustments(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Recommend adjustments to improve strategy effectiveness"""
        effectiveness = self.evaluate_strategy_effectiveness(strategy_id)
        recommendations = []
        
        if effectiveness["recent_success_rate"] < 0.5:
            recommendations.append({
                "type": "parameter_adjustment",
                "description": "Low success rate - consider relaxing trigger conditions",
                "suggested_changes": {"confidence_threshold": "decrease by 0.1"},
                "priority": "high"
            })
        
        if effectiveness["roi"] < 0.5:
            recommendations.append({
                "type": "cost_optimization",
                "description": "Low ROI - optimize resource usage",
                "suggested_changes": {"max_preload_files": "reduce by 20%"},
                "priority": "medium"
            })
        
        if effectiveness["effectiveness_trend"] == "declining":
            recommendations.append({
                "type": "strategy_refresh",
                "description": "Declining effectiveness - update pattern recognition",
                "suggested_changes": {"retrain_models": True},
                "priority": "medium"
            })
        
        return recommendations
    
    def _analyze_execution_performance(self, executions: List[PreloadingExecution]) -> Dict[str, Any]:
        """Analyze performance of strategy executions"""
        if not executions:
            return {"success_rate": 0, "avg_benefit": 0, "avg_duration": 0}
        
        successful = [e for e in executions if e.status == "completed"]
        success_rate = len(successful) / len(executions)
        
        benefits = []
        durations = []
        
        for execution in successful:
            if execution.actual_benefit:
                benefits.extend(execution.actual_benefit.values())
            
            if execution.completed_at and execution.started_at:
                durations.append(execution.completed_at - execution.started_at)
        
        return {
            "success_rate": success_rate,
            "avg_benefit": statistics.mean(benefits) if benefits else 0,
            "avg_duration": statistics.mean(durations) if durations else 0,
            "total_executions": len(executions)
        }
    
    def _adapt_strategy_parameters(self, strategy: PreloadingStrategy, 
                                 performance_metrics: Dict[str, Any]) -> PreloadingStrategy:
        """Adapt strategy parameters based on performance"""
        adapted_rules = strategy.preload_rules.copy()
        adaptation_params = strategy.adaptation_parameters
        
        # Adjust based on success rate
        success_rate = performance_metrics["success_rate"]
        
        if success_rate < 0.4:
            # Low success rate - relax constraints
            if "min_sequence_confidence" in adapted_rules:
                current_val = adapted_rules["min_sequence_confidence"]
                min_val = adaptation_params.get("confidence_threshold_min", 0.3)
                step = adaptation_params.get("adjustment_step", 0.1)
                adapted_rules["min_sequence_confidence"] = max(min_val, current_val - step)
            
            if "min_access_frequency" in adapted_rules:
                current_val = adapted_rules["min_access_frequency"]
                min_val = adaptation_params.get("frequency_threshold_min", 1)
                adapted_rules["min_access_frequency"] = max(min_val, current_val - 1)
        
        elif success_rate > 0.8:
            # High success rate - tighten constraints for better precision
            if "min_sequence_confidence" in adapted_rules:
                current_val = adapted_rules["min_sequence_confidence"]
                max_val = adaptation_params.get("confidence_threshold_max", 0.9)
                step = adaptation_params.get("adjustment_step", 0.1)
                adapted_rules["min_sequence_confidence"] = min(max_val, current_val + step)
        
        # Update effectiveness score
        new_effectiveness = (strategy.effectiveness_score * 0.7) + (success_rate * 0.3)
        
        # Create adapted strategy
        return PreloadingStrategy(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.strategy_name,
            strategy_type=strategy.strategy_type,
            target_cache_types=strategy.target_cache_types,
            priority=strategy.priority,
            trigger_conditions=strategy.trigger_conditions,
            preload_rules=adapted_rules,
            effectiveness_score=new_effectiveness,
            resource_cost=strategy.resource_cost,
            adaptation_parameters=strategy.adaptation_parameters,
            created_at=strategy.created_at,
            last_updated=time.time(),
            success_metrics=performance_metrics
        )
    
    def _load_strategy(self, strategy_id: str) -> Optional[PreloadingStrategy]:
        """Load strategy from cache"""
        strategy_data = self.cache_manager.get_cache(
            self.strategies_cache_type,
            strategy_id,
            cache_level="global"
        )
        
        if strategy_data:
            return PreloadingStrategy(**strategy_data)
        return None
    
    def _store_strategy(self, strategy: PreloadingStrategy):
        """Store strategy to cache"""
        self.cache_manager.set_cache(
            self.strategies_cache_type,
            strategy.strategy_id,
            asdict(strategy),
            cache_level="global"
        )
    
    def _store_strategies(self, strategies: List[PreloadingStrategy]):
        """Store multiple strategies"""
        for strategy in strategies:
            self._store_strategy(strategy)
    
    def _get_recent_executions(self, strategy_id: str, hours: int) -> List[PreloadingExecution]:
        """Get recent executions for a strategy"""
        # This would load from cache and filter by time
        # For now, return empty list
        return []


class AdaptivePreloadingOrchestrator:
    """Main orchestrator for adaptive preloading system"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard,
                 ml_pattern_recognition: MLPatternRecognition = None,
                 predictive_analytics: PredictiveAnalyticsOrchestrator = None):
        
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.ml_pattern_recognition = ml_pattern_recognition
        self.predictive_analytics = predictive_analytics
        
        # Initialize components
        self.usage_analyzer = UsagePatternAnalyzer(
            cache_manager, symbol_cache, performance_dashboard
        )
        self.strategy_engine = StrategyAdaptationEngine(
            cache_manager, performance_dashboard
        )
        
        # State management
        self.is_running = False
        self.preloading_thread = None
        self._stop_event = threading.Event()
        
        # Decision and execution tracking
        self.pending_decisions = deque(maxlen=100)
        self.execution_history = deque(maxlen=200)
    
    def start_adaptive_preloading(self):
        """Start the adaptive preloading system"""
        if self.is_running:
            return
        
        # Initialize strategies
        usage_patterns = self.analyze_current_usage_patterns()
        initial_strategies = self.strategy_engine.create_initial_strategies(usage_patterns)
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start preloading thread
        self.preloading_thread = threading.Thread(target=self._preloading_loop)
        self.preloading_thread.daemon = True
        self.preloading_thread.start()
    
    def stop_adaptive_preloading(self):
        """Stop the adaptive preloading system"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        if self.preloading_thread:
            self.preloading_thread.join(timeout=30)
    
    def analyze_current_usage_patterns(self) -> Dict[str, Any]:
        """Analyze current usage patterns"""
        access_patterns = self.usage_analyzer.analyze_access_patterns()
        temporal_patterns = self.usage_analyzer.detect_temporal_patterns()
        sequence_patterns = self.usage_analyzer.discover_sequence_patterns()
        
        return {
            "access_patterns": access_patterns,
            "temporal_patterns": temporal_patterns,
            "sequence_patterns": sequence_patterns,
            "analysis_timestamp": time.time()
        }
    
    def make_preloading_decision(self, trigger_context: Dict[str, Any]) -> Optional[PreloadingDecision]:
        """Make an intelligent preloading decision"""
        current_file = trigger_context.get("current_file")
        if not current_file:
            return None
        
        # Get predictions for next accesses
        next_accesses = self.usage_analyzer.predict_next_accesses(current_file, trigger_context)
        
        if not next_accesses:
            return None
        
        # Select files to preload based on probability and resource constraints
        files_to_preload = []
        total_priority = 0
        
        for prediction in next_accesses[:5]:  # Top 5 predictions
            if prediction["probability"] > 0.4:  # Minimum confidence threshold
                files_to_preload.append(prediction["file_path"])
                total_priority += prediction["probability"]
        
        if not files_to_preload:
            return None
        
        # Create preloading decision
        decision = PreloadingDecision(
            decision_id=f"preload_{int(time.time())}",
            strategy_id="adaptive_v1",
            target_files=files_to_preload,
            cache_types=["symbols", "analysis"],
            priority_score=total_priority / len(files_to_preload),
            confidence=max(p["probability"] for p in next_accesses[:len(files_to_preload)]),
            estimated_benefit={
                "hit_rate_improvement": len(files_to_preload) * 10,  # Estimated %
                "response_time_reduction_ms": len(files_to_preload) * 50
            },
            resource_requirements={
                "estimated_memory_mb": len(files_to_preload) * 2,
                "estimated_cpu_ms": len(files_to_preload) * 100
            },
            trigger_context=trigger_context,
            decision_timestamp=time.time(),
            execution_window=(time.time(), time.time() + 300)  # 5-minute window
        )
        
        self.pending_decisions.append(decision)
        return decision
    
    def execute_preloading_decision(self, decision: PreloadingDecision) -> PreloadingExecution:
        """Execute a preloading decision"""
        execution = PreloadingExecution(
            execution_id=f"exec_{decision.decision_id}",
            decision_id=decision.decision_id,
            started_at=time.time(),
            completed_at=None,
            status="running",
            files_preloaded=[],
            cache_entries_created=0,
            actual_benefit=None,
            execution_logs=[],
            performance_impact={}
        )
        
        try:
            execution.execution_logs.append(f"Starting preload of {len(decision.target_files)} files")
            
            # Capture performance before
            performance_before = self._capture_performance_snapshot()
            
            # Execute preloading
            for file_path in decision.target_files:
                try:
                    # Preload symbols
                    if "symbols" in decision.cache_types:
                        symbol_map = self.symbol_cache.analyze_file(file_path, force_refresh=False)
                        if symbol_map:
                            execution.files_preloaded.append(file_path)
                            execution.cache_entries_created += len(symbol_map.symbols)
                    
                    # Preload analysis if ML patterns available
                    if "analysis" in decision.cache_types and self.ml_pattern_recognition:
                        patterns = self.ml_pattern_recognition.discover_ml_patterns("current", [file_path])
                        if patterns:
                            execution.cache_entries_created += len(patterns)
                    
                except Exception as e:
                    execution.execution_logs.append(f"Failed to preload {file_path}: {str(e)}")
            
            # Capture performance after
            performance_after = self._capture_performance_snapshot()
            
            # Calculate actual benefit
            execution.actual_benefit = self._calculate_preloading_benefit(
                performance_before, performance_after, len(execution.files_preloaded)
            )
            
            execution.status = "completed"
            execution.completed_at = time.time()
            execution.execution_logs.append(f"Preloaded {len(execution.files_preloaded)} files successfully")
            
        except Exception as e:
            execution.status = "failed"
            execution.execution_logs.append(f"Execution failed: {str(e)}")
        
        # Store execution
        self.execution_history.append(execution)
        self._store_execution(execution)
        
        return execution
    
    def get_preloading_status(self) -> Dict[str, Any]:
        """Get current preloading system status"""
        recent_executions = list(self.execution_history)[-10:]  # Last 10
        
        return {
            "system_running": self.is_running,
            "pending_decisions": len(self.pending_decisions),
            "recent_executions": len(recent_executions),
            "success_rate": len([e for e in recent_executions if e.status == "completed"]) / max(len(recent_executions), 1),
            "average_files_preloaded": statistics.mean([len(e.files_preloaded) for e in recent_executions]) if recent_executions else 0,
            "total_cache_entries_created": sum(e.cache_entries_created for e in recent_executions),
            "system_effectiveness": self._calculate_system_effectiveness()
        }
    
    def _preloading_loop(self):
        """Main preloading loop"""
        while self.is_running and not self._stop_event.is_set():
            try:
                # Process pending decisions
                current_time = time.time()
                
                for decision in list(self.pending_decisions):
                    # Check if decision is within execution window
                    if decision.execution_window[0] <= current_time <= decision.execution_window[1]:
                        self.execute_preloading_decision(decision)
                        self.pending_decisions.remove(decision)
                    elif current_time > decision.execution_window[1]:
                        # Decision expired
                        self.pending_decisions.remove(decision)
                
                # Adapt strategies based on recent performance
                if len(self.execution_history) >= 10:
                    recent_executions = list(self.execution_history)[-10:]
                    # Group by strategy and adapt
                    strategy_executions = defaultdict(list)
                    for execution in recent_executions:
                        # Extract strategy from decision
                        strategy_executions["adaptive_v1"].append(execution)
                    
                    for strategy_id, executions in strategy_executions.items():
                        self.strategy_engine.adapt_strategy(strategy_id, executions)
                
                # Wait before next iteration
                self._stop_event.wait(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in preloading loop: {e}")
                self._stop_event.wait(60)
    
    def _capture_performance_snapshot(self) -> Dict[str, float]:
        """Capture performance metrics snapshot"""
        stats = self.cache_manager.get_performance_stats()
        return {
            "timestamp": time.time(),
            "hit_rate_percent": stats.get("hit_rate_percent", 0),
            "average_response_time_ms": stats.get("average_response_time_ms", 0),
            "cache_size_mb": stats.get("total_cache_size_mb", 0)
        }
    
    def _calculate_preloading_benefit(self, before: Dict, after: Dict, files_preloaded: int) -> Dict[str, float]:
        """Calculate actual benefit from preloading"""
        if files_preloaded == 0:
            return {"hit_rate_improvement": 0, "response_time_improvement": 0}
        
        hit_rate_improvement = after.get("hit_rate_percent", 0) - before.get("hit_rate_percent", 0)
        response_time_improvement = before.get("average_response_time_ms", 0) - after.get("average_response_time_ms", 0)
        
        return {
            "hit_rate_improvement": hit_rate_improvement,
            "response_time_improvement": response_time_improvement,
            "cache_size_increase_mb": after.get("cache_size_mb", 0) - before.get("cache_size_mb", 0)
        }
    
    def _calculate_system_effectiveness(self) -> float:
        """Calculate overall system effectiveness"""
        if not self.execution_history:
            return 0.0
        
        recent_executions = list(self.execution_history)[-20:]  # Last 20
        successful = [e for e in recent_executions if e.status == "completed"]
        
        if not successful:
            return 0.0
        
        # Average benefit score
        benefits = []
        for execution in successful:
            if execution.actual_benefit:
                benefit_score = (
                    execution.actual_benefit.get("hit_rate_improvement", 0) +
                    execution.actual_benefit.get("response_time_improvement", 0) / 10  # Normalize
                )
                benefits.append(max(0, benefit_score))
        
        return statistics.mean(benefits) if benefits else 0.0
    
    def _store_execution(self, execution: PreloadingExecution):
        """Store execution record"""
        self.cache_manager.set_cache(
            "preloading_executions",
            execution.execution_id,
            asdict(execution),
            cache_level="global"
        )