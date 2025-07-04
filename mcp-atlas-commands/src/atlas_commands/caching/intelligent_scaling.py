"""
Intelligent Scaling System
Phase 4 implementation for automatic cache scaling based on project growth patterns
Monitors project development velocity and scales cache resources intelligently
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
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard


@dataclass
class ProjectGrowthMetrics:
    """Metrics representing project growth"""
    project_id: str
    measurement_timestamp: float
    
    # Code metrics
    total_files: int
    total_lines_of_code: int
    total_functions: int
    total_classes: int
    
    # Activity metrics
    daily_file_changes: int
    weekly_commits: int
    active_developers: int
    
    # Cache metrics
    cache_size_mb: float
    symbol_count: int
    analysis_entries: int
    
    # Performance metrics
    hit_rate_percent: float
    average_response_time_ms: float
    peak_concurrent_operations: int
    
    # Growth indicators
    velocity_score: float  # Composite score of development velocity
    complexity_trend: str  # 'increasing', 'stable', 'decreasing'
    team_expansion_factor: float


@dataclass
class ScalingPrediction:
    """Prediction for required scaling"""
    prediction_id: str
    project_id: str
    prediction_horizon_days: int
    predicted_at: float
    
    # Predicted metrics
    predicted_files: int
    predicted_loc: int
    predicted_symbols: int
    predicted_cache_size_mb: float
    
    # Scaling requirements
    recommended_cache_limit_mb: int
    recommended_performance_tier: str  # 'basic', 'standard', 'premium', 'enterprise'
    scaling_trigger_threshold: float
    
    # Confidence and reasoning
    confidence_score: float
    growth_pattern: str  # 'linear', 'exponential', 'plateau', 'declining'
    key_growth_drivers: List[str]
    
    # Resource planning
    estimated_memory_requirement_mb: int
    estimated_cpu_requirement_percent: float
    estimated_network_bandwidth_mbps: float


@dataclass
class ScalingAction:
    """Action to scale cache resources"""
    action_id: str
    prediction_id: str
    action_type: str  # 'scale_up', 'scale_down', 'optimize', 'redistribute'
    target_resources: List[str]
    
    # Scaling parameters
    new_cache_limits: Dict[str, int]
    performance_adjustments: Dict[str, Any]
    resource_reallocation: Dict[str, Dict[str, Any]]
    
    # Execution details
    scheduled_at: float
    estimated_duration_minutes: int
    rollback_plan: Dict[str, Any]
    impact_assessment: Dict[str, str]


class ProjectGrowthAnalyzer:
    """Analyzes project growth patterns and trends"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.growth_metrics_cache_type = "growth_metrics"
        self._lock = threading.Lock()
        
        # Growth data storage
        self.metrics_history = defaultdict(lambda: deque(maxlen=365))  # 1 year of daily metrics
        self.growth_patterns = {}
        
        # ML components
        self.ml_available = SKLEARN_AVAILABLE
        if self.ml_available:
            self.growth_model = LinearRegression()
            self.polynomial_features = PolynomialFeatures(degree=2)
            self.pattern_clusterer = KMeans(n_clusters=4, random_state=42)
    
    def collect_current_metrics(self, project_id: str, file_paths: List[str] = None) -> ProjectGrowthMetrics:
        """Collect current project growth metrics"""
        current_time = time.time()
        
        # Analyze code metrics
        code_metrics = self._analyze_code_metrics(file_paths or [])
        
        # Get activity metrics
        activity_metrics = self._analyze_activity_metrics(project_id)
        
        # Get cache metrics
        cache_metrics = self._analyze_cache_metrics()
        
        # Get performance metrics
        performance_metrics = self._analyze_performance_metrics()
        
        # Calculate composite scores
        velocity_score = self._calculate_velocity_score(activity_metrics, code_metrics)
        complexity_trend = self._analyze_complexity_trend(code_metrics)
        team_expansion = self._calculate_team_expansion_factor(activity_metrics)
        
        metrics = ProjectGrowthMetrics(
            project_id=project_id,
            measurement_timestamp=current_time,
            
            # Code metrics
            total_files=code_metrics["total_files"],
            total_lines_of_code=code_metrics["total_loc"],
            total_functions=code_metrics["total_functions"],
            total_classes=code_metrics["total_classes"],
            
            # Activity metrics
            daily_file_changes=activity_metrics["daily_changes"],
            weekly_commits=activity_metrics["weekly_commits"],
            active_developers=activity_metrics["active_developers"],
            
            # Cache metrics
            cache_size_mb=cache_metrics["total_size_mb"],
            symbol_count=cache_metrics["symbol_count"],
            analysis_entries=cache_metrics["analysis_entries"],
            
            # Performance metrics
            hit_rate_percent=performance_metrics["hit_rate"],
            average_response_time_ms=performance_metrics["avg_response_time"],
            peak_concurrent_operations=performance_metrics["peak_operations"],
            
            # Growth indicators
            velocity_score=velocity_score,
            complexity_trend=complexity_trend,
            team_expansion_factor=team_expansion
        )
        
        # Store metrics
        self._store_metrics(metrics)
        self.metrics_history[project_id].append(metrics)
        
        return metrics
    
    def analyze_growth_patterns(self, project_id: str, analysis_window_days: int = 90) -> Dict[str, Any]:
        """Analyze growth patterns over time"""
        history = list(self.metrics_history[project_id])
        
        if len(history) < 7:  # Need at least a week of data
            return {"pattern": "insufficient_data", "confidence": 0.0}
        
        # Filter to analysis window
        cutoff_time = time.time() - (analysis_window_days * 24 * 3600)
        recent_history = [m for m in history if m.measurement_timestamp >= cutoff_time]
        
        if len(recent_history) < 3:
            return {"pattern": "insufficient_recent_data", "confidence": 0.0}
        
        # Analyze different growth dimensions
        patterns = {
            "file_growth": self._analyze_metric_growth([m.total_files for m in recent_history]),
            "loc_growth": self._analyze_metric_growth([m.total_lines_of_code for m in recent_history]),
            "symbol_growth": self._analyze_metric_growth([m.total_functions + m.total_classes for m in recent_history]),
            "cache_growth": self._analyze_metric_growth([m.cache_size_mb for m in recent_history]),
            "performance_trend": self._analyze_performance_trend(recent_history),
            "velocity_trend": self._analyze_metric_growth([m.velocity_score for m in recent_history]),
            "team_growth": self._analyze_metric_growth([m.active_developers for m in recent_history])
        }
        
        # Determine overall growth pattern
        overall_pattern = self._classify_overall_growth_pattern(patterns)
        
        # Calculate pattern confidence
        confidence = self._calculate_pattern_confidence(patterns, recent_history)
        
        return {
            "overall_pattern": overall_pattern,
            "confidence": confidence,
            "detailed_patterns": patterns,
            "growth_velocity": self._calculate_growth_velocity(recent_history),
            "sustainability_score": self._calculate_sustainability_score(patterns),
            "scaling_urgency": self._assess_scaling_urgency(patterns)
        }
    
    def predict_growth_trajectory(self, project_id: str, prediction_horizon_days: int = 30) -> Dict[str, Any]:
        """Predict project growth trajectory"""
        history = list(self.metrics_history[project_id])
        
        if len(history) < 10:
            return {"error": "Insufficient historical data for prediction"}
        
        # Prepare data for ML model
        X, y_metrics = self._prepare_growth_prediction_data(history)
        
        if not self.ml_available or len(X) < 5:
            # Fallback to simple trend extrapolation
            return self._simple_trend_prediction(history, prediction_horizon_days)
        
        # Train growth model
        predictions = {}
        
        for metric_name, y_values in y_metrics.items():
            try:
                # Fit polynomial features for non-linear growth
                X_poly = self.polynomial_features.fit_transform(X)
                model = LinearRegression()
                model.fit(X_poly, y_values)
                
                # Predict future values
                future_X = np.array([[len(history) + i] for i in range(1, prediction_horizon_days + 1)])
                future_X_poly = self.polynomial_features.transform(future_X)
                future_values = model.predict(future_X_poly)
                
                # Calculate prediction confidence
                train_score = model.score(X_poly, y_values)
                
                predictions[metric_name] = {
                    "predicted_values": future_values.tolist(),
                    "confidence": min(train_score, 1.0),
                    "trend": "increasing" if future_values[-1] > y_values[-1] else "decreasing"
                }
                
            except Exception as e:
                print(f"Error predicting {metric_name}: {e}")
                predictions[metric_name] = {"error": str(e)}
        
        return {
            "prediction_horizon_days": prediction_horizon_days,
            "predictions": predictions,
            "model_confidence": statistics.mean([
                p.get("confidence", 0) for p in predictions.values() if "confidence" in p
            ]),
            "growth_acceleration": self._calculate_growth_acceleration(predictions)
        }
    
    def identify_scaling_triggers(self, project_id: str) -> List[Dict[str, Any]]:
        """Identify conditions that should trigger scaling"""
        current_metrics = self.metrics_history[project_id][-1] if self.metrics_history[project_id] else None
        
        if not current_metrics:
            return []
        
        triggers = []
        
        # Cache size trigger
        if current_metrics.cache_size_mb > 500:  # 500MB threshold
            triggers.append({
                "trigger_type": "cache_size_threshold",
                "severity": "high" if current_metrics.cache_size_mb > 800 else "medium",
                "current_value": current_metrics.cache_size_mb,
                "threshold": 500,
                "recommended_action": "scale_up_cache_limits"
            })
        
        # Performance degradation trigger
        if current_metrics.hit_rate_percent < 70:
            triggers.append({
                "trigger_type": "performance_degradation",
                "severity": "high" if current_metrics.hit_rate_percent < 50 else "medium",
                "current_value": current_metrics.hit_rate_percent,
                "threshold": 70,
                "recommended_action": "optimize_cache_strategy"
            })
        
        # Growth velocity trigger
        if current_metrics.velocity_score > 0.8:
            triggers.append({
                "trigger_type": "high_growth_velocity",
                "severity": "medium",
                "current_value": current_metrics.velocity_score,
                "threshold": 0.8,
                "recommended_action": "proactive_scaling"
            })
        
        # Team expansion trigger
        if current_metrics.team_expansion_factor > 1.5:
            triggers.append({
                "trigger_type": "team_expansion",
                "severity": "medium",
                "current_value": current_metrics.team_expansion_factor,
                "threshold": 1.5,
                "recommended_action": "scale_collaborative_features"
            })
        
        return sorted(triggers, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["severity"]], reverse=True)
    
    def _analyze_code_metrics(self, file_paths: List[str]) -> Dict[str, int]:
        """Analyze code metrics from files"""
        total_files = len(file_paths)
        total_loc = 0
        total_functions = 0
        total_classes = 0
        
        for file_path in file_paths:
            try:
                symbol_map = self.symbol_cache.analyze_file(file_path)
                if symbol_map:
                    # Count symbols
                    functions = [s for s in symbol_map.symbols if s.symbol_type == "function"]
                    classes = [s for s in symbol_map.symbols if s.symbol_type == "class"]
                    
                    total_functions += len(functions)
                    total_classes += len(classes)
                    
                    # Estimate lines of code (simplified)
                    if symbol_map.symbols:
                        max_line = max(s.line_end for s in symbol_map.symbols if s.line_end)
                        total_loc += max_line
                
            except Exception:
                continue  # Skip files that can't be analyzed
        
        return {
            "total_files": total_files,
            "total_loc": total_loc,
            "total_functions": total_functions,
            "total_classes": total_classes
        }
    
    def _analyze_activity_metrics(self, project_id: str) -> Dict[str, int]:
        """Analyze development activity metrics"""
        # This would integrate with git or other VCS
        # For now, estimate based on cache activity
        
        recent_operations = self.performance_dashboard.performance_tracker.get_recent_operations(24 * 60)
        
        # Estimate activity from cache operations
        daily_changes = len(set(op.file_path for op in recent_operations if op.file_path))
        
        # Simplified estimates
        weekly_commits = daily_changes * 7  # Rough estimate
        active_developers = max(1, daily_changes // 10)  # Estimate developers
        
        return {
            "daily_changes": daily_changes,
            "weekly_commits": weekly_commits,
            "active_developers": active_developers
        }
    
    def _analyze_cache_metrics(self) -> Dict[str, Any]:
        """Analyze current cache metrics"""
        cache_info = self.cache_manager.get_cache_size_info()
        
        # Count symbols across all cache levels
        symbol_count = 0
        analysis_entries = 0
        
        # This would traverse cache to count entries
        # For now, estimate based on cache size
        total_size_mb = cache_info.get("total_cache_mb", 0)
        symbol_count = int(total_size_mb * 100)  # Rough estimate
        analysis_entries = int(total_size_mb * 50)
        
        return {
            "total_size_mb": total_size_mb,
            "symbol_count": symbol_count,
            "analysis_entries": analysis_entries
        }
    
    def _analyze_performance_metrics(self) -> Dict[str, float]:
        """Analyze current performance metrics"""
        stats = self.cache_manager.get_performance_stats()
        
        return {
            "hit_rate": stats.get("hit_rate_percent", 0),
            "avg_response_time": stats.get("average_response_time_ms", 0),
            "peak_operations": stats.get("operations_per_hour", 0)
        }
    
    def _calculate_velocity_score(self, activity: Dict, code: Dict) -> float:
        """Calculate development velocity score (0-1)"""
        # Normalize metrics
        file_velocity = min(activity["daily_changes"] / 20.0, 1.0)  # 20 files = max velocity
        commit_velocity = min(activity["weekly_commits"] / 50.0, 1.0)  # 50 commits = max
        code_velocity = min(code["total_functions"] / 1000.0, 1.0)  # 1000 functions = max
        
        # Weighted average
        return (file_velocity * 0.4 + commit_velocity * 0.4 + code_velocity * 0.2)
    
    def _analyze_complexity_trend(self, code_metrics: Dict) -> str:
        """Analyze code complexity trend"""
        # Simplified complexity analysis
        total_symbols = code_metrics["total_functions"] + code_metrics["total_classes"]
        
        if code_metrics["total_files"] == 0:
            return "stable"
        
        avg_symbols_per_file = total_symbols / code_metrics["total_files"]
        
        if avg_symbols_per_file > 15:
            return "increasing"
        elif avg_symbols_per_file < 5:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_team_expansion_factor(self, activity: Dict) -> float:
        """Calculate team expansion factor"""
        # Base factor of 1.0 for stable team
        base_developers = 3  # Assumed baseline team size
        current_developers = activity["active_developers"]
        
        return current_developers / base_developers
    
    def _analyze_metric_growth(self, values: List[float]) -> Dict[str, Any]:
        """Analyze growth pattern for a metric"""
        if len(values) < 3:
            return {"pattern": "insufficient_data", "growth_rate": 0}
        
        # Calculate growth rate
        if self.ml_available and len(values) >= 5:
            # Use linear regression for trend
            X = np.array(range(len(values))).reshape(-1, 1)
            model = LinearRegression()
            model.fit(X, values)
            growth_rate = model.coef_[0]
            r_squared = model.score(X, values)
        else:
            # Simple growth rate calculation
            growth_rate = (values[-1] - values[0]) / max(len(values) - 1, 1)
            r_squared = 0.5  # Default confidence
        
        # Classify pattern
        if abs(growth_rate) < 0.1:
            pattern = "stable"
        elif growth_rate > 0:
            if growth_rate > statistics.mean(values) * 0.1:  # >10% of mean per period
                pattern = "exponential"
            else:
                pattern = "linear"
        else:
            pattern = "declining"
        
        return {
            "pattern": pattern,
            "growth_rate": growth_rate,
            "confidence": r_squared,
            "recent_value": values[-1],
            "trend_strength": abs(growth_rate) / (statistics.stdev(values) + 0.1)
        }
    
    def _analyze_performance_trend(self, history: List[ProjectGrowthMetrics]) -> Dict[str, Any]:
        """Analyze performance trend over time"""
        hit_rates = [m.hit_rate_percent for m in history]
        response_times = [m.average_response_time_ms for m in history]
        
        hit_rate_trend = self._analyze_metric_growth(hit_rates)
        response_time_trend = self._analyze_metric_growth(response_times)
        
        # Overall performance trend
        if hit_rate_trend["pattern"] == "declining" or response_time_trend["pattern"] == "exponential":
            overall_trend = "degrading"
        elif hit_rate_trend["pattern"] == "linear" and response_time_trend["pattern"] == "stable":
            overall_trend = "improving"
        else:
            overall_trend = "stable"
        
        return {
            "overall_trend": overall_trend,
            "hit_rate_trend": hit_rate_trend,
            "response_time_trend": response_time_trend
        }
    
    def _classify_overall_growth_pattern(self, patterns: Dict[str, Any]) -> str:
        """Classify overall growth pattern"""
        # Count pattern types
        pattern_counts = Counter()
        for pattern_data in patterns.values():
            if isinstance(pattern_data, dict) and "pattern" in pattern_data:
                pattern_counts[pattern_data["pattern"]] += 1
        
        # Determine overall pattern
        if pattern_counts["exponential"] >= 2:
            return "rapid_growth"
        elif pattern_counts["linear"] >= 3:
            return "steady_growth"
        elif pattern_counts["declining"] >= 2:
            return "declining"
        elif pattern_counts["stable"] >= 3:
            return "mature_stable"
        else:
            return "mixed_growth"
    
    def _calculate_pattern_confidence(self, patterns: Dict, history: List) -> float:
        """Calculate confidence in pattern analysis"""
        confidences = []
        
        for pattern_data in patterns.values():
            if isinstance(pattern_data, dict) and "confidence" in pattern_data:
                confidences.append(pattern_data["confidence"])
        
        if not confidences:
            return 0.5
        
        # Factor in data volume
        data_volume_factor = min(len(history) / 30.0, 1.0)  # 30 days = full confidence
        
        return statistics.mean(confidences) * data_volume_factor
    
    def _calculate_growth_velocity(self, history: List[ProjectGrowthMetrics]) -> float:
        """Calculate current growth velocity"""
        if len(history) < 2:
            return 0.0
        
        recent = history[-1]
        previous = history[-2]
        
        # Compare key metrics
        file_growth = (recent.total_files - previous.total_files) / max(previous.total_files, 1)
        loc_growth = (recent.total_lines_of_code - previous.total_lines_of_code) / max(previous.total_lines_of_code, 1)
        velocity_change = recent.velocity_score - previous.velocity_score
        
        return (file_growth + loc_growth + velocity_change) / 3.0
    
    def _calculate_sustainability_score(self, patterns: Dict[str, Any]) -> float:
        """Calculate sustainability score of current growth"""
        performance_trend = patterns.get("performance_trend", {})
        velocity_trend = patterns.get("velocity_trend", {})
        
        # Penalize performance degradation
        perf_penalty = 0.0
        if performance_trend.get("overall_trend") == "degrading":
            perf_penalty = 0.3
        
        # Reward stable velocity
        velocity_bonus = 0.0
        if velocity_trend.get("pattern") in ["stable", "linear"]:
            velocity_bonus = 0.2
        
        base_score = 0.7
        return max(0.0, min(1.0, base_score - perf_penalty + velocity_bonus))
    
    def _assess_scaling_urgency(self, patterns: Dict[str, Any]) -> str:
        """Assess urgency of scaling needs"""
        cache_growth = patterns.get("cache_growth", {})
        performance_trend = patterns.get("performance_trend", {})
        
        if (cache_growth.get("pattern") == "exponential" or 
            performance_trend.get("overall_trend") == "degrading"):
            return "high"
        elif cache_growth.get("pattern") == "linear":
            return "medium"
        else:
            return "low"
    
    def _prepare_growth_prediction_data(self, history: List[ProjectGrowthMetrics]) -> Tuple[np.ndarray, Dict[str, List]]:
        """Prepare data for ML growth prediction"""
        if not self.ml_available:
            return np.array([]), {}
        
        X = np.array([[i] for i in range(len(history))])
        
        y_metrics = {
            "total_files": [m.total_files for m in history],
            "total_loc": [m.total_lines_of_code for m in history],
            "cache_size_mb": [m.cache_size_mb for m in history],
            "symbol_count": [m.symbol_count for m in history],
            "hit_rate": [m.hit_rate_percent for m in history]
        }
        
        return X, y_metrics
    
    def _simple_trend_prediction(self, history: List[ProjectGrowthMetrics], days: int) -> Dict[str, Any]:
        """Simple trend-based prediction fallback"""
        if len(history) < 3:
            return {"error": "Insufficient data for simple prediction"}
        
        recent = history[-3:]
        
        # Calculate simple growth rates
        files_rate = (recent[-1].total_files - recent[0].total_files) / 2
        loc_rate = (recent[-1].total_lines_of_code - recent[0].total_lines_of_code) / 2
        cache_rate = (recent[-1].cache_size_mb - recent[0].cache_size_mb) / 2
        
        return {
            "prediction_method": "simple_trend",
            "predictions": {
                "total_files": {
                    "predicted_values": [recent[-1].total_files + files_rate * i for i in range(1, days + 1)],
                    "confidence": 0.6
                },
                "total_loc": {
                    "predicted_values": [recent[-1].total_lines_of_code + loc_rate * i for i in range(1, days + 1)],
                    "confidence": 0.6
                },
                "cache_size_mb": {
                    "predicted_values": [recent[-1].cache_size_mb + cache_rate * i for i in range(1, days + 1)],
                    "confidence": 0.6
                }
            }
        }
    
    def _calculate_growth_acceleration(self, predictions: Dict[str, Any]) -> float:
        """Calculate growth acceleration from predictions"""
        accelerations = []
        
        for metric_data in predictions.values():
            if "predicted_values" in metric_data:
                values = metric_data["predicted_values"]
                if len(values) >= 3:
                    # Calculate second derivative (acceleration)
                    first_diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
                    if len(first_diffs) >= 2:
                        second_diffs = [first_diffs[i+1] - first_diffs[i] for i in range(len(first_diffs)-1)]
                        avg_acceleration = statistics.mean(second_diffs)
                        accelerations.append(avg_acceleration)
        
        return statistics.mean(accelerations) if accelerations else 0.0
    
    def _store_metrics(self, metrics: ProjectGrowthMetrics):
        """Store growth metrics"""
        self.cache_manager.set_cache(
            self.growth_metrics_cache_type,
            f"{metrics.project_id}_{int(metrics.measurement_timestamp)}",
            asdict(metrics),
            cache_level="global"
        )


class ScalingDecisionEngine:
    """Makes intelligent scaling decisions based on growth analysis"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager):
        self.cache_manager = cache_manager
        self.predictions_cache_type = "scaling_predictions"
        self.actions_cache_type = "scaling_actions"
        self._lock = threading.Lock()
        
        # Scaling thresholds
        self.scaling_thresholds = {
            "cache_size_mb": 500,
            "hit_rate_percent": 70,
            "response_time_ms": 100,
            "growth_velocity": 0.7,
            "prediction_confidence": 0.6
        }
    
    def generate_scaling_prediction(self, project_id: str, growth_analysis: Dict[str, Any],
                                  growth_trajectory: Dict[str, Any]) -> ScalingPrediction:
        """Generate scaling prediction based on growth analysis"""
        
        # Extract key predictions
        predictions = growth_trajectory.get("predictions", {})
        horizon_days = growth_trajectory.get("prediction_horizon_days", 30)
        
        # Get final predicted values
        predicted_files = self._extract_final_prediction(predictions, "total_files")
        predicted_loc = self._extract_final_prediction(predictions, "total_loc")
        predicted_cache_size = self._extract_final_prediction(predictions, "cache_size_mb")
        predicted_symbols = predicted_files * 10  # Estimate symbols
        
        # Determine performance tier
        performance_tier = self._determine_performance_tier(
            predicted_files, predicted_cache_size, growth_analysis
        )
        
        # Calculate recommended cache limit
        recommended_cache_limit = self._calculate_recommended_cache_limit(
            predicted_cache_size, performance_tier
        )
        
        # Assess growth pattern
        growth_pattern = growth_analysis.get("overall_pattern", "unknown")
        
        # Identify key growth drivers
        growth_drivers = self._identify_growth_drivers(growth_analysis)
        
        # Calculate confidence
        model_confidence = growth_trajectory.get("model_confidence", 0.5)
        pattern_confidence = growth_analysis.get("confidence", 0.5)
        confidence_score = (model_confidence + pattern_confidence) / 2.0
        
        # Calculate resource requirements
        memory_req = self._estimate_memory_requirement(predicted_cache_size, performance_tier)
        cpu_req = self._estimate_cpu_requirement(predicted_files, growth_pattern)
        bandwidth_req = self._estimate_bandwidth_requirement(predicted_symbols, performance_tier)
        
        prediction = ScalingPrediction(
            prediction_id=f"scale_pred_{int(time.time())}",
            project_id=project_id,
            prediction_horizon_days=horizon_days,
            predicted_at=time.time(),
            
            # Predicted metrics
            predicted_files=predicted_files,
            predicted_loc=predicted_loc,
            predicted_symbols=predicted_symbols,
            predicted_cache_size_mb=predicted_cache_size,
            
            # Scaling requirements
            recommended_cache_limit_mb=recommended_cache_limit,
            recommended_performance_tier=performance_tier,
            scaling_trigger_threshold=self._calculate_scaling_trigger_threshold(growth_pattern),
            
            # Confidence and reasoning
            confidence_score=confidence_score,
            growth_pattern=growth_pattern,
            key_growth_drivers=growth_drivers,
            
            # Resource planning
            estimated_memory_requirement_mb=memory_req,
            estimated_cpu_requirement_percent=cpu_req,
            estimated_network_bandwidth_mbps=bandwidth_req
        )
        
        # Store prediction
        self._store_prediction(prediction)
        
        return prediction
    
    def plan_scaling_actions(self, prediction: ScalingPrediction, 
                           current_metrics: ProjectGrowthMetrics) -> List[ScalingAction]:
        """Plan specific scaling actions based on prediction"""
        actions = []
        
        # Cache scaling action
        if prediction.predicted_cache_size_mb > current_metrics.cache_size_mb * 1.5:
            cache_action = self._create_cache_scaling_action(prediction, current_metrics)
            actions.append(cache_action)
        
        # Performance optimization action
        if prediction.recommended_performance_tier != "basic":
            perf_action = self._create_performance_optimization_action(prediction)
            actions.append(perf_action)
        
        # Resource reallocation action
        if prediction.growth_pattern in ["rapid_growth", "exponential"]:
            realloc_action = self._create_resource_reallocation_action(prediction)
            actions.append(realloc_action)
        
        return actions
    
    def evaluate_scaling_urgency(self, prediction: ScalingPrediction, 
                                triggers: List[Dict]) -> str:
        """Evaluate urgency of scaling actions"""
        # Check immediate triggers
        high_severity_triggers = [t for t in triggers if t.get("severity") == "high"]
        if high_severity_triggers:
            return "immediate"
        
        # Check prediction confidence and growth rate
        if prediction.confidence_score > 0.8 and prediction.growth_pattern == "exponential":
            return "urgent"
        
        # Check if we're approaching limits
        if prediction.predicted_cache_size_mb > prediction.recommended_cache_limit_mb * 0.8:
            return "planned"
        
        return "monitoring"
    
    def _extract_final_prediction(self, predictions: Dict, metric_name: str) -> float:
        """Extract final predicted value for a metric"""
        metric_data = predictions.get(metric_name, {})
        predicted_values = metric_data.get("predicted_values", [])
        
        if predicted_values:
            return max(0, predicted_values[-1])  # Ensure non-negative
        return 0.0
    
    def _determine_performance_tier(self, predicted_files: float, 
                                  predicted_cache_size: float, 
                                  growth_analysis: Dict) -> str:
        """Determine appropriate performance tier"""
        growth_pattern = growth_analysis.get("overall_pattern", "stable")
        
        if predicted_files > 5000 or predicted_cache_size > 1000 or growth_pattern == "rapid_growth":
            return "enterprise"
        elif predicted_files > 1000 or predicted_cache_size > 500:
            return "premium"
        elif predicted_files > 500 or predicted_cache_size > 200:
            return "standard"
        else:
            return "basic"
    
    def _calculate_recommended_cache_limit(self, predicted_cache_size: float, 
                                        performance_tier: str) -> int:
        """Calculate recommended cache limit"""
        # Add safety margin based on tier
        margin_multipliers = {
            "basic": 1.5,
            "standard": 2.0,
            "premium": 2.5,
            "enterprise": 3.0
        }
        
        margin = margin_multipliers.get(performance_tier, 2.0)
        return int(predicted_cache_size * margin)
    
    def _identify_growth_drivers(self, growth_analysis: Dict) -> List[str]:
        """Identify key factors driving growth"""
        patterns = growth_analysis.get("detailed_patterns", {})
        drivers = []
        
        for pattern_name, pattern_data in patterns.items():
            if isinstance(pattern_data, dict) and pattern_data.get("pattern") in ["linear", "exponential"]:
                drivers.append(pattern_name.replace("_", " ").title())
        
        if growth_analysis.get("scaling_urgency") == "high":
            drivers.append("Performance Pressure")
        
        return drivers[:5]  # Top 5 drivers
    
    def _calculate_scaling_trigger_threshold(self, growth_pattern: str) -> float:
        """Calculate threshold for triggering scaling"""
        thresholds = {
            "rapid_growth": 0.7,
            "steady_growth": 0.8,
            "exponential": 0.6,
            "stable": 0.9,
            "declining": 0.95
        }
        
        return thresholds.get(growth_pattern, 0.8)
    
    def _estimate_memory_requirement(self, predicted_cache_size: float, 
                                   performance_tier: str) -> int:
        """Estimate memory requirements"""
        base_memory = predicted_cache_size
        
        # Add overhead based on tier
        overhead_multipliers = {
            "basic": 1.2,
            "standard": 1.5,
            "premium": 2.0,
            "enterprise": 2.5
        }
        
        multiplier = overhead_multipliers.get(performance_tier, 1.5)
        return int(base_memory * multiplier)
    
    def _estimate_cpu_requirement(self, predicted_files: float, growth_pattern: str) -> float:
        """Estimate CPU requirements as percentage"""
        base_cpu = min(predicted_files / 100.0, 80.0)  # Max 80% CPU
        
        # Adjust based on growth pattern
        if growth_pattern in ["rapid_growth", "exponential"]:
            base_cpu *= 1.3
        elif growth_pattern == "declining":
            base_cpu *= 0.8
        
        return min(base_cpu, 90.0)
    
    def _estimate_bandwidth_requirement(self, predicted_symbols: float, 
                                      performance_tier: str) -> float:
        """Estimate network bandwidth requirements"""
        # Base bandwidth on symbol transfer needs
        base_bandwidth = predicted_symbols / 10000.0  # Symbols per Mbps
        
        # Adjust for tier
        tier_multipliers = {
            "basic": 1.0,
            "standard": 1.2,
            "premium": 1.5,
            "enterprise": 2.0
        }
        
        multiplier = tier_multipliers.get(performance_tier, 1.2)
        return base_bandwidth * multiplier
    
    def _create_cache_scaling_action(self, prediction: ScalingPrediction, 
                                   current_metrics: ProjectGrowthMetrics) -> ScalingAction:
        """Create cache scaling action"""
        return ScalingAction(
            action_id=f"cache_scale_{int(time.time())}",
            prediction_id=prediction.prediction_id,
            action_type="scale_up",
            target_resources=["cache_memory", "cache_storage"],
            
            new_cache_limits={
                "global_cache_mb": prediction.recommended_cache_limit_mb,
                "project_cache_mb": prediction.recommended_cache_limit_mb // 2,
                "symbol_cache_mb": prediction.recommended_cache_limit_mb // 4
            },
            
            performance_adjustments={
                "cache_eviction_policy": "adaptive_lru",
                "preload_threshold": 0.6,
                "compression_enabled": True
            },
            
            resource_reallocation={
                "memory": {
                    "old_allocation_mb": int(current_metrics.cache_size_mb),
                    "new_allocation_mb": prediction.recommended_cache_limit_mb,
                    "increase_percent": ((prediction.recommended_cache_limit_mb - current_metrics.cache_size_mb) / 
                                       max(current_metrics.cache_size_mb, 1)) * 100
                }
            },
            
            scheduled_at=time.time() + 3600,  # Schedule 1 hour from now
            estimated_duration_minutes=15,
            
            rollback_plan={
                "rollback_trigger": "performance_degradation",
                "original_limits": {
                    "global_cache_mb": int(current_metrics.cache_size_mb)
                }
            },
            
            impact_assessment={
                "user_impact": "minimal",
                "system_impact": "low",
                "downtime_required": "no"
            }
        )
    
    def _create_performance_optimization_action(self, prediction: ScalingPrediction) -> ScalingAction:
        """Create performance optimization action"""
        return ScalingAction(
            action_id=f"perf_opt_{int(time.time())}",
            prediction_id=prediction.prediction_id,
            action_type="optimize",
            target_resources=["cache_algorithms", "indexing", "compression"],
            
            new_cache_limits={},  # No limit changes
            
            performance_adjustments={
                "enable_intelligent_preloading": True,
                "adaptive_compression": True,
                "smart_invalidation": True,
                "performance_tier": prediction.recommended_performance_tier
            },
            
            resource_reallocation={},
            
            scheduled_at=time.time() + 1800,  # Schedule 30 minutes from now
            estimated_duration_minutes=10,
            
            rollback_plan={
                "rollback_trigger": "performance_regression",
                "fallback_settings": "conservative_defaults"
            },
            
            impact_assessment={
                "user_impact": "positive",
                "system_impact": "low",
                "downtime_required": "no"
            }
        )
    
    def _create_resource_reallocation_action(self, prediction: ScalingPrediction) -> ScalingAction:
        """Create resource reallocation action"""
        return ScalingAction(
            action_id=f"realloc_{int(time.time())}",
            prediction_id=prediction.prediction_id,
            action_type="redistribute",
            target_resources=["memory_pools", "cpu_allocation", "cache_distribution"],
            
            new_cache_limits={},
            
            performance_adjustments={
                "dynamic_resource_allocation": True,
                "load_balancing": "adaptive"
            },
            
            resource_reallocation={
                "cpu": {
                    "analysis_pool_percent": 40,
                    "cache_pool_percent": 35,
                    "preload_pool_percent": 25
                },
                "memory": {
                    "hot_cache_percent": 50,
                    "warm_cache_percent": 30,
                    "cold_cache_percent": 20
                }
            },
            
            scheduled_at=time.time() + 7200,  # Schedule 2 hours from now
            estimated_duration_minutes=20,
            
            rollback_plan={
                "rollback_trigger": "resource_contention",
                "original_allocation": "equal_distribution"
            },
            
            impact_assessment={
                "user_impact": "minimal",
                "system_impact": "medium",
                "downtime_required": "no"
            }
        )
    
    def _store_prediction(self, prediction: ScalingPrediction):
        """Store scaling prediction"""
        self.cache_manager.set_cache(
            self.predictions_cache_type,
            prediction.prediction_id,
            asdict(prediction),
            cache_level="global"
        )


class IntelligentScalingOrchestrator:
    """Main orchestrator for intelligent scaling system"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard):
        
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        
        # Initialize components
        self.growth_analyzer = ProjectGrowthAnalyzer(
            cache_manager, symbol_cache, performance_dashboard
        )
        self.decision_engine = ScalingDecisionEngine(cache_manager)
        
        # State management
        self.is_running = False
        self.scaling_thread = None
        self._stop_event = threading.Event()
        
        # Monitoring intervals
        self.metrics_collection_interval = 3600  # 1 hour
        self.analysis_interval = 24 * 3600  # 24 hours
        self.prediction_interval = 7 * 24 * 3600  # 7 days
    
    def start_intelligent_scaling(self):
        """Start the intelligent scaling system"""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start scaling thread
        self.scaling_thread = threading.Thread(target=self._scaling_loop)
        self.scaling_thread.daemon = True
        self.scaling_thread.start()
    
    def stop_intelligent_scaling(self):
        """Stop the intelligent scaling system"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        if self.scaling_thread:
            self.scaling_thread.join(timeout=30)
    
    def perform_growth_analysis(self, project_id: str, file_paths: List[str] = None) -> Dict[str, Any]:
        """Perform comprehensive growth analysis"""
        # Collect current metrics
        current_metrics = self.growth_analyzer.collect_current_metrics(project_id, file_paths)
        
        # Analyze growth patterns
        growth_patterns = self.growth_analyzer.analyze_growth_patterns(project_id)
        
        # Predict growth trajectory
        growth_trajectory = self.growth_analyzer.predict_growth_trajectory(project_id, 30)
        
        # Identify scaling triggers
        scaling_triggers = self.growth_analyzer.identify_scaling_triggers(project_id)
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "current_metrics": asdict(current_metrics),
            "growth_patterns": growth_patterns,
            "growth_trajectory": growth_trajectory,
            "scaling_triggers": scaling_triggers,
            "analysis_summary": self._generate_analysis_summary(
                growth_patterns, growth_trajectory, scaling_triggers
            )
        }
    
    def generate_scaling_plan(self, project_id: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive scaling plan"""
        # Generate prediction
        prediction = self.decision_engine.generate_scaling_prediction(
            project_id, analysis["growth_patterns"], analysis["growth_trajectory"]
        )
        
        # Plan scaling actions
        current_metrics = ProjectGrowthMetrics(**analysis["current_metrics"])
        scaling_actions = self.decision_engine.plan_scaling_actions(prediction, current_metrics)
        
        # Evaluate urgency
        urgency = self.decision_engine.evaluate_scaling_urgency(
            prediction, analysis["scaling_triggers"]
        )
        
        return {
            "plan_timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "prediction": asdict(prediction),
            "scaling_actions": [asdict(action) for action in scaling_actions],
            "urgency": urgency,
            "execution_timeline": self._create_execution_timeline(scaling_actions, urgency),
            "resource_requirements": self._summarize_resource_requirements(prediction),
            "risk_assessment": self._assess_scaling_risks(scaling_actions)
        }
    
    def get_scaling_status(self, project_id: str) -> Dict[str, Any]:
        """Get current scaling system status"""
        return {
            "system_running": self.is_running,
            "project_id": project_id,
            "last_analysis": self._get_last_analysis_time(project_id),
            "next_scheduled_analysis": self._get_next_analysis_time(),
            "monitoring_intervals": {
                "metrics_collection_hours": self.metrics_collection_interval / 3600,
                "analysis_interval_hours": self.analysis_interval / 3600,
                "prediction_interval_days": self.prediction_interval / (24 * 3600)
            },
            "system_health": self._assess_system_health()
        }
    
    def _scaling_loop(self):
        """Main scaling monitoring loop"""
        last_metrics_collection = 0
        last_analysis = 0
        last_prediction = 0
        
        while self.is_running and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # Collect metrics periodically
                if current_time - last_metrics_collection >= self.metrics_collection_interval:
                    self._collect_metrics_for_all_projects()
                    last_metrics_collection = current_time
                
                # Perform analysis periodically
                if current_time - last_analysis >= self.analysis_interval:
                    self._perform_scheduled_analysis()
                    last_analysis = current_time
                
                # Generate predictions periodically
                if current_time - last_prediction >= self.prediction_interval:
                    self._generate_scheduled_predictions()
                    last_prediction = current_time
                
                # Wait before next iteration
                self._stop_event.wait(min(3600, self.metrics_collection_interval))  # Max 1 hour wait
                
            except Exception as e:
                print(f"Error in scaling loop: {e}")
                self._stop_event.wait(3600)  # Wait 1 hour before retry
    
    def _collect_metrics_for_all_projects(self):
        """Collect metrics for all monitored projects"""
        # This would iterate through all projects
        # For now, just collect for a default project
        self.growth_analyzer.collect_current_metrics("default", [])
    
    def _perform_scheduled_analysis(self):
        """Perform scheduled growth analysis"""
        # This would analyze all projects
        try:
            analysis = self.perform_growth_analysis("default")
            # Store analysis results
            self.cache_manager.set_cache(
                "growth_analysis",
                f"scheduled_{int(time.time())}",
                analysis,
                cache_level="global"
            )
        except Exception as e:
            print(f"Error in scheduled analysis: {e}")
    
    def _generate_scheduled_predictions(self):
        """Generate scheduled scaling predictions"""
        # This would generate predictions for all projects
        try:
            analysis = self.perform_growth_analysis("default")
            plan = self.generate_scaling_plan("default", analysis)
            # Store plan
            self.cache_manager.set_cache(
                "scaling_plans",
                f"scheduled_{int(time.time())}",
                plan,
                cache_level="global"
            )
        except Exception as e:
            print(f"Error in scheduled predictions: {e}")
    
    def _generate_analysis_summary(self, growth_patterns: Dict, trajectory: Dict, 
                                 triggers: List) -> Dict[str, Any]:
        """Generate analysis summary"""
        return {
            "overall_growth_trend": growth_patterns.get("overall_pattern", "unknown"),
            "growth_confidence": growth_patterns.get("confidence", 0.0),
            "scaling_urgency": growth_patterns.get("scaling_urgency", "low"),
            "active_triggers": len(triggers),
            "high_priority_triggers": len([t for t in triggers if t.get("severity") == "high"]),
            "prediction_reliability": trajectory.get("model_confidence", 0.0)
        }
    
    def _create_execution_timeline(self, actions: List[ScalingAction], urgency: str) -> Dict[str, Any]:
        """Create execution timeline for scaling actions"""
        timeline = {
            "immediate": [],
            "short_term": [],  # 1-7 days
            "medium_term": [],  # 1-4 weeks
            "long_term": []  # 1+ months
        }
        
        current_time = time.time()
        
        for action in actions:
            time_diff = action.scheduled_at - current_time
            
            if urgency == "immediate" or time_diff < 3600:  # 1 hour
                timeline["immediate"].append(action.action_id)
            elif time_diff < 7 * 24 * 3600:  # 7 days
                timeline["short_term"].append(action.action_id)
            elif time_diff < 30 * 24 * 3600:  # 30 days
                timeline["medium_term"].append(action.action_id)
            else:
                timeline["long_term"].append(action.action_id)
        
        return timeline
    
    def _summarize_resource_requirements(self, prediction: ScalingPrediction) -> Dict[str, Any]:
        """Summarize resource requirements"""
        return {
            "memory_increase_mb": prediction.estimated_memory_requirement_mb,
            "cpu_increase_percent": prediction.estimated_cpu_requirement_percent,
            "bandwidth_requirement_mbps": prediction.estimated_network_bandwidth_mbps,
            "cache_limit_increase_mb": prediction.recommended_cache_limit_mb,
            "performance_tier": prediction.recommended_performance_tier
        }
    
    def _assess_scaling_risks(self, actions: List[ScalingAction]) -> Dict[str, str]:
        """Assess risks of scaling actions"""
        risks = {
            "overall_risk": "low",
            "performance_risk": "low",
            "resource_risk": "low",
            "operational_risk": "low"
        }
        
        # Assess based on action types and scope
        scale_up_actions = [a for a in actions if a.action_type == "scale_up"]
        if len(scale_up_actions) > 2:
            risks["resource_risk"] = "medium"
        
        complex_actions = [a for a in actions if a.estimated_duration_minutes > 30]
        if complex_actions:
            risks["operational_risk"] = "medium"
        
        # Set overall risk as max of individual risks
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        max_risk_level = max(risk_levels[risk] for risk in risks.values())
        risks["overall_risk"] = {1: "low", 2: "medium", 3: "high"}[max_risk_level]
        
        return risks
    
    def _get_last_analysis_time(self, project_id: str) -> Optional[str]:
        """Get timestamp of last analysis"""
        # This would query cache for last analysis
        return datetime.now().isoformat()  # Placeholder
    
    def _get_next_analysis_time(self) -> str:
        """Get timestamp of next scheduled analysis"""
        next_time = time.time() + self.analysis_interval
        return datetime.fromtimestamp(next_time).isoformat()
    
    def _assess_system_health(self) -> Dict[str, str]:
        """Assess overall system health"""
        cache_stats = self.cache_manager.get_performance_stats()
        
        health = {
            "cache_performance": "healthy" if cache_stats.get("hit_rate_percent", 0) > 70 else "degraded",
            "response_time": "healthy" if cache_stats.get("average_response_time_ms", 0) < 100 else "slow",
            "system_load": "normal",  # Would assess actual system load
            "scaling_readiness": "ready"
        }
        
        return health