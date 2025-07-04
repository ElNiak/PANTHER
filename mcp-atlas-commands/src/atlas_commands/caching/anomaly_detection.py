"""
Anomaly Detection System
Phase 4 implementation for detecting performance and code quality anomalies
Uses ML techniques to identify unusual patterns and potential issues
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
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard
from .ml_powered_analytics import PerformanceAnomaly, CodeQualityAnomaly


@dataclass
class AnomalyDetectionConfig:
    """Configuration for anomaly detection"""
    sensitivity: float = 0.1  # 0.05 = very sensitive, 0.2 = less sensitive
    min_data_points: int = 20
    lookback_window_hours: int = 24
    anomaly_threshold: float = 2.0  # Standard deviations
    confidence_threshold: float = 0.7
    enabled_detectors: List[str] = None
    
    def __post_init__(self):
        if self.enabled_detectors is None:
            self.enabled_detectors = [
                "performance", "memory", "code_quality", "cache_behavior"
            ]


class PerformanceAnomalyDetector:
    """Detects performance anomalies using ML techniques"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 performance_dashboard: CachePerformanceDashboard,
                 config: AnomalyDetectionConfig):
        self.cache_manager = cache_manager
        self.performance_dashboard = performance_dashboard
        self.config = config
        self.anomalies_cache_type = "performance_anomalies"
        self._lock = threading.Lock()
        
        # Initialize ML models if available
        self.ml_available = SKLEARN_AVAILABLE
        if self.ml_available:
            self.isolation_forest = IsolationForest(
                contamination=config.sensitivity,
                random_state=42
            )
            self.scaler = StandardScaler()
        
        # Baseline metrics storage
        self.baseline_metrics = {}
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))
    
    def detect_anomalies(self, project_id: str = None) -> List[PerformanceAnomaly]:
        """Detect performance anomalies across the system"""
        anomalies = []
        
        # Get recent performance data
        performance_data = self._collect_performance_data(project_id)
        
        if len(performance_data) < self.config.min_data_points:
            return anomalies
        
        # Detect different types of anomalies
        if "performance" in self.config.enabled_detectors:
            response_time_anomalies = self._detect_response_time_anomalies(performance_data, project_id)
            anomalies.extend(response_time_anomalies)
        
        if "memory" in self.config.enabled_detectors:
            memory_anomalies = self._detect_memory_anomalies(performance_data, project_id)
            anomalies.extend(memory_anomalies)
        
        if "cache_behavior" in self.config.enabled_detectors:
            cache_anomalies = self._detect_cache_behavior_anomalies(performance_data, project_id)
            anomalies.extend(cache_anomalies)
        
        # Store detected anomalies
        self._store_anomalies(anomalies)
        
        return anomalies
    
    def update_baselines(self, project_id: str = None):
        """Update baseline metrics for anomaly detection"""
        current_time = time.time()
        cutoff_time = current_time - (self.config.lookback_window_hours * 3600)
        
        # Get historical performance data
        metrics = self.performance_dashboard.performance_tracker.calculate_metrics(
            cutoff_time, current_time
        )
        
        # Update baselines
        baseline_key = project_id or "global"
        self.baseline_metrics[baseline_key] = {
            "response_time_ms": {
                "mean": metrics.average_response_time_ms,
                "std": self._calculate_response_time_std(cutoff_time, current_time),
                "updated_at": current_time
            },
            "hit_rate": {
                "mean": metrics.hit_rate_percent,
                "std": self._calculate_hit_rate_std(cutoff_time, current_time),
                "updated_at": current_time
            },
            "cache_size": {
                "mean": metrics.total_cache_size_mb,
                "std": self._calculate_cache_size_std(),
                "updated_at": current_time
            }
        }
    
    def _collect_performance_data(self, project_id: str = None) -> List[Dict[str, Any]]:
        """Collect recent performance data for analysis"""
        current_time = time.time()
        start_time = current_time - (self.config.lookback_window_hours * 3600)
        
        # Get operations data
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            self.config.lookback_window_hours * 60  # Convert to minutes
        )
        
        # Convert to analysis format
        data_points = []
        for op in operations:
            data_point = {
                "timestamp": op.timestamp,
                "operation_type": op.operation_type,
                "duration_ms": op.duration_ms,
                "cache_type": op.cache_type,
                "cache_level": op.cache_level,
                "file_path": op.file_path,
                "project_context": project_id
            }
            data_points.append(data_point)
        
        return data_points
    
    def _detect_response_time_anomalies(self, performance_data: List[Dict], 
                                       project_id: str) -> List[PerformanceAnomaly]:
        """Detect response time anomalies"""
        anomalies = []
        
        # Extract response times
        response_times = [dp["duration_ms"] for dp in performance_data]
        
        if len(response_times) < self.config.min_data_points:
            return anomalies
        
        # Calculate statistical baseline
        mean_time = statistics.mean(response_times)
        std_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # Update metric history
        self.metric_history["response_time"].extend(response_times)
        
        # Detect anomalies using statistical method
        threshold = mean_time + (self.config.anomaly_threshold * std_time)
        
        for i, dp in enumerate(performance_data):
            if dp["duration_ms"] > threshold and std_time > 0:
                deviation_score = (dp["duration_ms"] - mean_time) / std_time
                
                if deviation_score > self.config.anomaly_threshold:
                    anomaly = PerformanceAnomaly(
                        anomaly_id=f"response_time_{int(dp['timestamp'])}",
                        anomaly_type="response_time",
                        severity=self._calculate_severity(deviation_score),
                        detected_at=time.time(),
                        affected_projects=[project_id] if project_id else ["global"],
                        metric_name="response_time_ms",
                        baseline_value=mean_time,
                        anomalous_value=dp["duration_ms"],
                        deviation_score=deviation_score,
                        confidence=min(deviation_score / 5.0, 1.0),
                        root_cause_analysis=self._analyze_response_time_root_cause(dp, performance_data),
                        suggested_actions=self._suggest_response_time_actions(deviation_score),
                        historical_context=self._get_historical_context("response_time", dp["duration_ms"])
                    )
                    anomalies.append(anomaly)
        
        # ML-based detection if available
        if self.ml_available and len(response_times) > 50:
            ml_anomalies = self._detect_ml_response_time_anomalies(performance_data, project_id)
            anomalies.extend(ml_anomalies)
        
        return anomalies
    
    def _detect_memory_anomalies(self, performance_data: List[Dict], 
                                project_id: str) -> List[PerformanceAnomaly]:
        """Detect memory usage anomalies"""
        anomalies = []
        
        # Get cache size information
        cache_info = self.cache_manager.get_cache_size_info()
        current_size = cache_info.get("total_cache_mb", 0)
        
        # Get baseline
        baseline_key = project_id or "global"
        baseline = self.baseline_metrics.get(baseline_key, {}).get("cache_size")
        
        if not baseline:
            return anomalies
        
        # Check for memory anomaly
        if baseline["std"] > 0:
            deviation_score = abs(current_size - baseline["mean"]) / baseline["std"]
            
            if deviation_score > self.config.anomaly_threshold:
                anomaly = PerformanceAnomaly(
                    anomaly_id=f"memory_{int(time.time())}",
                    anomaly_type="memory",
                    severity=self._calculate_severity(deviation_score),
                    detected_at=time.time(),
                    affected_projects=[project_id] if project_id else ["global"],
                    metric_name="cache_size_mb",
                    baseline_value=baseline["mean"],
                    anomalous_value=current_size,
                    deviation_score=deviation_score,
                    confidence=min(deviation_score / 3.0, 1.0),
                    root_cause_analysis=self._analyze_memory_root_cause(cache_info),
                    suggested_actions=self._suggest_memory_actions(current_size, baseline["mean"]),
                    historical_context=self._get_historical_context("memory", current_size)
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_cache_behavior_anomalies(self, performance_data: List[Dict], 
                                        project_id: str) -> List[PerformanceAnomaly]:
        """Detect cache behavior anomalies"""
        anomalies = []
        
        # Analyze hit rate patterns
        hit_operations = [dp for dp in performance_data if dp["operation_type"] == "hit"]
        total_operations = len(performance_data)
        
        if total_operations == 0:
            return anomalies
        
        current_hit_rate = (len(hit_operations) / total_operations) * 100
        
        # Get baseline
        baseline_key = project_id or "global"
        baseline = self.baseline_metrics.get(baseline_key, {}).get("hit_rate")
        
        if baseline and baseline["std"] > 0:
            deviation_score = abs(current_hit_rate - baseline["mean"]) / baseline["std"]
            
            if deviation_score > self.config.anomaly_threshold:
                anomaly = PerformanceAnomaly(
                    anomaly_id=f"hit_rate_{int(time.time())}",
                    anomaly_type="hit_rate",
                    severity=self._calculate_severity(deviation_score),
                    detected_at=time.time(),
                    affected_projects=[project_id] if project_id else ["global"],
                    metric_name="hit_rate_percent",
                    baseline_value=baseline["mean"],
                    anomalous_value=current_hit_rate,
                    deviation_score=deviation_score,
                    confidence=min(deviation_score / 3.0, 1.0),
                    root_cause_analysis=self._analyze_hit_rate_root_cause(performance_data),
                    suggested_actions=self._suggest_hit_rate_actions(current_hit_rate, baseline["mean"]),
                    historical_context=self._get_historical_context("hit_rate", current_hit_rate)
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_ml_response_time_anomalies(self, performance_data: List[Dict], 
                                          project_id: str) -> List[PerformanceAnomaly]:
        """Detect response time anomalies using ML"""
        if not self.ml_available:
            return []
        
        # Prepare feature matrix
        features = self._extract_performance_features(performance_data)
        
        if len(features) < 20:
            return []
        
        # Normalize features
        features_array = np.array(features)
        normalized_features = self.scaler.fit_transform(features_array)
        
        # Detect anomalies
        anomaly_scores = self.isolation_forest.fit_predict(normalized_features)
        
        anomalies = []
        for i, (score, dp) in enumerate(zip(anomaly_scores, performance_data)):
            if score == -1:  # Anomaly detected
                # Calculate confidence based on isolation score
                isolation_score = self.isolation_forest.decision_function(normalized_features[i:i+1])[0]
                confidence = min(abs(isolation_score) * 2, 1.0)
                
                if confidence > self.config.confidence_threshold:
                    anomaly = PerformanceAnomaly(
                        anomaly_id=f"ml_response_{int(dp['timestamp'])}",
                        anomaly_type="response_time",
                        severity="medium",
                        detected_at=time.time(),
                        affected_projects=[project_id] if project_id else ["global"],
                        metric_name="response_time_ml",
                        baseline_value=statistics.mean([d["duration_ms"] for d in performance_data]),
                        anomalous_value=dp["duration_ms"],
                        deviation_score=abs(isolation_score),
                        confidence=confidence,
                        root_cause_analysis={"method": "ml_isolation_forest", "features": features[i]},
                        suggested_actions=["Investigate ML-detected performance anomaly"],
                        historical_context={"detection_method": "machine_learning"}
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    def _extract_performance_features(self, performance_data: List[Dict]) -> List[List[float]]:
        """Extract features for ML anomaly detection"""
        features = []
        
        for dp in performance_data:
            feature_vector = [
                dp["duration_ms"],
                1.0 if dp["operation_type"] == "hit" else 0.0,
                1.0 if dp["operation_type"] == "miss" else 0.0,
                len(dp.get("file_path", "")),
                hash(dp.get("cache_type", "")) % 100,  # Simple hash feature
                hash(dp.get("cache_level", "")) % 10,
                dp["timestamp"] % 86400,  # Time of day
            ]
            features.append(feature_vector)
        
        return features
    
    def _calculate_severity(self, deviation_score: float) -> str:
        """Calculate severity based on deviation score"""
        if deviation_score > 4:
            return "critical"
        elif deviation_score > 3:
            return "high"
        elif deviation_score > 2:
            return "medium"
        else:
            return "low"
    
    def _analyze_response_time_root_cause(self, data_point: Dict, 
                                        all_data: List[Dict]) -> Dict[str, Any]:
        """Analyze root cause of response time anomaly"""
        analysis = {
            "cache_type": data_point.get("cache_type"),
            "cache_level": data_point.get("cache_level"),
            "operation_type": data_point.get("operation_type"),
            "file_path": data_point.get("file_path"),
        }
        
        # Analyze patterns
        same_type_ops = [dp for dp in all_data 
                        if dp.get("cache_type") == data_point.get("cache_type")]
        if same_type_ops:
            avg_time_same_type = statistics.mean([dp["duration_ms"] for dp in same_type_ops])
            analysis["avg_time_same_cache_type"] = avg_time_same_type
            analysis["deviation_from_cache_type_avg"] = data_point["duration_ms"] - avg_time_same_type
        
        return analysis
    
    def _suggest_response_time_actions(self, deviation_score: float) -> List[str]:
        """Suggest actions for response time anomalies"""
        actions = []
        
        if deviation_score > 4:
            actions.extend([
                "Immediately investigate system resources",
                "Check for memory pressure or disk I/O issues",
                "Review recent code changes"
            ])
        elif deviation_score > 3:
            actions.extend([
                "Monitor system performance closely",
                "Check cache hit rates",
                "Review file access patterns"
            ])
        else:
            actions.extend([
                "Log anomaly for trend analysis",
                "Monitor for recurring patterns"
            ])
        
        return actions
    
    def _analyze_memory_root_cause(self, cache_info: Dict) -> Dict[str, Any]:
        """Analyze root cause of memory anomaly"""
        return {
            "global_cache_mb": cache_info.get("global_cache_mb", 0),
            "project_cache_mb": cache_info.get("project_cache_mb", 0),
            "cache_distribution": cache_info.get("cache_distribution", {}),
            "largest_cache_types": cache_info.get("largest_cache_types", [])
        }
    
    def _suggest_memory_actions(self, current_size: float, baseline_size: float) -> List[str]:
        """Suggest actions for memory anomalies"""
        actions = []
        
        if current_size > baseline_size * 1.5:
            actions.extend([
                "Run cache cleanup operation",
                "Check for memory leaks",
                "Review cache retention policies"
            ])
        elif current_size < baseline_size * 0.5:
            actions.extend([
                "Investigate cache invalidation patterns",
                "Check if cache warming is needed",
                "Review cache configuration"
            ])
        
        return actions
    
    def _analyze_hit_rate_root_cause(self, performance_data: List[Dict]) -> Dict[str, Any]:
        """Analyze root cause of hit rate anomaly"""
        # Analyze cache types
        cache_type_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        
        for dp in performance_data:
            cache_type = dp.get("cache_type", "unknown")
            if dp["operation_type"] == "hit":
                cache_type_stats[cache_type]["hits"] += 1
            else:
                cache_type_stats[cache_type]["misses"] += 1
        
        # Calculate hit rates by cache type
        hit_rates_by_type = {}
        for cache_type, stats in cache_type_stats.items():
            total = stats["hits"] + stats["misses"]
            if total > 0:
                hit_rates_by_type[cache_type] = (stats["hits"] / total) * 100
        
        return {
            "cache_type_hit_rates": hit_rates_by_type,
            "total_operations": len(performance_data),
            "operation_distribution": dict(Counter(dp["operation_type"] for dp in performance_data))
        }
    
    def _suggest_hit_rate_actions(self, current_rate: float, baseline_rate: float) -> List[str]:
        """Suggest actions for hit rate anomalies"""
        actions = []
        
        if current_rate < baseline_rate - 10:
            actions.extend([
                "Investigate cache invalidation patterns",
                "Check if working set has changed",
                "Review cache size limits",
                "Consider cache warming strategies"
            ])
        elif current_rate > baseline_rate + 20:
            actions.extend([
                "Verify cache metrics are accurate",
                "Check for changes in usage patterns",
                "Monitor for potential cache thrashing"
            ])
        
        return actions
    
    def _get_historical_context(self, metric_type: str, current_value: float) -> Dict[str, Any]:
        """Get historical context for anomaly"""
        history = list(self.metric_history[metric_type])
        
        if len(history) < 10:
            return {"message": "Insufficient historical data"}
        
        recent_avg = statistics.mean(history[-10:])
        long_term_avg = statistics.mean(history)
        
        return {
            "recent_average": recent_avg,
            "long_term_average": long_term_avg,
            "trend": "increasing" if recent_avg > long_term_avg else "decreasing",
            "historical_min": min(history),
            "historical_max": max(history),
            "percentile_rank": self._calculate_percentile_rank(current_value, history)
        }
    
    def _calculate_percentile_rank(self, value: float, history: List[float]) -> float:
        """Calculate percentile rank of value in history"""
        if not history:
            return 50.0
        
        sorted_history = sorted(history)
        rank = sum(1 for v in sorted_history if v <= value)
        return (rank / len(sorted_history)) * 100
    
    def _calculate_response_time_std(self, start_time: float, end_time: float) -> float:
        """Calculate standard deviation of response times"""
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            int((end_time - start_time) / 60)
        )
        response_times = [op.duration_ms for op in operations]
        return statistics.stdev(response_times) if len(response_times) > 1 else 0
    
    def _calculate_hit_rate_std(self, start_time: float, end_time: float) -> float:
        """Calculate standard deviation of hit rates"""
        # This would require time-bucketed hit rate calculations
        # For now, return a reasonable default
        return 5.0
    
    def _calculate_cache_size_std(self) -> float:
        """Calculate standard deviation of cache sizes"""
        # This would require historical cache size data
        # For now, return a reasonable default
        return 50.0
    
    def _store_anomalies(self, anomalies: List[PerformanceAnomaly]):
        """Store detected anomalies"""
        for anomaly in anomalies:
            self.cache_manager.set_cache(
                self.anomalies_cache_type,
                anomaly.anomaly_id,
                asdict(anomaly),
                cache_level="global"
            )


class CodeQualityAnomalyDetector:
    """Detects code quality anomalies"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 config: AnomalyDetectionConfig):
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.config = config
        self.quality_anomalies_cache_type = "quality_anomalies"
        self._lock = threading.Lock()
    
    def detect_code_quality_anomalies(self, file_paths: List[str]) -> List[CodeQualityAnomaly]:
        """Detect code quality anomalies in files"""
        anomalies = []
        
        for file_path in file_paths:
            file_anomalies = self._analyze_file_quality(file_path)
            anomalies.extend(file_anomalies)
        
        # Store anomalies
        self._store_quality_anomalies(anomalies)
        
        return anomalies
    
    def _analyze_file_quality(self, file_path: str) -> List[CodeQualityAnomaly]:
        """Analyze quality anomalies in a single file"""
        anomalies = []
        
        symbol_map = self.symbol_cache.analyze_file(file_path)
        if not symbol_map:
            return anomalies
        
        # Detect complexity anomalies
        complexity_anomalies = self._detect_complexity_anomalies(file_path, symbol_map)
        anomalies.extend(complexity_anomalies)
        
        # Detect inconsistency anomalies
        inconsistency_anomalies = self._detect_inconsistency_anomalies(file_path, symbol_map)
        anomalies.extend(inconsistency_anomalies)
        
        return anomalies
    
    def _detect_complexity_anomalies(self, file_path: str, symbol_map) -> List[CodeQualityAnomaly]:
        """Detect complexity anomalies"""
        anomalies = []
        
        # Analyze function complexity
        functions = [s for s in symbol_map.symbols if s.symbol_type == "function"]
        
        if not functions:
            return anomalies
        
        param_counts = [len(s.parameters) for s in functions]
        if param_counts:
            mean_params = statistics.mean(param_counts)
            std_params = statistics.stdev(param_counts) if len(param_counts) > 1 else 0
            
            for func in functions:
                param_count = len(func.parameters)
                if std_params > 0:
                    deviation = abs(param_count - mean_params) / std_params
                    
                    if deviation > self.config.anomaly_threshold and param_count > 8:
                        anomaly = CodeQualityAnomaly(
                            anomaly_id=f"complexity_{hash(file_path + func.name)}",
                            file_path=file_path,
                            anomaly_type="complexity_spike",
                            severity=self._calculate_quality_severity(deviation),
                            description=f"Function '{func.name}' has unusually high parameter count ({param_count})",
                            affected_symbols=[func.name],
                            quality_metrics={
                                "parameter_count": param_count,
                                "deviation_score": deviation,
                                "file_average": mean_params
                            },
                            suggestions=[
                                "Consider breaking function into smaller parts",
                                "Use parameter objects or configuration classes",
                                "Review function responsibility"
                            ],
                            detected_at=time.time(),
                            confidence=min(deviation / 3.0, 1.0)
                        )
                        anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_inconsistency_anomalies(self, file_path: str, symbol_map) -> List[CodeQualityAnomaly]:
        """Detect naming and style inconsistencies"""
        anomalies = []
        
        # Analyze naming consistency
        symbols = symbol_map.symbols
        if not symbols:
            return anomalies
        
        # Check naming patterns
        snake_case_count = sum(1 for s in symbols if '_' in s.name and s.name.islower())
        camel_case_count = sum(1 for s in symbols if any(c.isupper() for c in s.name[1:]) and '_' not in s.name)
        
        total_symbols = len(symbols)
        snake_case_ratio = snake_case_count / total_symbols
        camel_case_ratio = camel_case_count / total_symbols
        
        # Detect mixed naming conventions
        if 0.2 < snake_case_ratio < 0.8 and 0.2 < camel_case_ratio < 0.8:
            anomaly = CodeQualityAnomaly(
                anomaly_id=f"naming_{hash(file_path)}",
                file_path=file_path,
                anomaly_type="inconsistency",
                severity="medium",
                description="Mixed naming conventions detected in file",
                affected_symbols=[s.name for s in symbols],
                quality_metrics={
                    "snake_case_ratio": snake_case_ratio,
                    "camel_case_ratio": camel_case_ratio,
                    "total_symbols": total_symbols
                },
                suggestions=[
                    "Standardize on one naming convention",
                    "Use automated formatting tools",
                    "Establish team coding standards"
                ],
                detected_at=time.time(),
                confidence=0.8
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _calculate_quality_severity(self, deviation_score: float) -> str:
        """Calculate severity for quality anomalies"""
        if deviation_score > 3:
            return "high"
        elif deviation_score > 2:
            return "medium"
        else:
            return "low"
    
    def _store_quality_anomalies(self, anomalies: List[CodeQualityAnomaly]):
        """Store quality anomalies"""
        for anomaly in anomalies:
            self.cache_manager.set_cache(
                self.quality_anomalies_cache_type,
                anomaly.anomaly_id,
                asdict(anomaly),
                cache_level="project"
            )


class AnomalyDetectionOrchestrator:
    """Orchestrates all anomaly detection activities"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard,
                 config: AnomalyDetectionConfig = None):
        
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.config = config or AnomalyDetectionConfig()
        
        # Initialize detectors
        self.performance_detector = PerformanceAnomalyDetector(
            cache_manager, performance_dashboard, self.config
        )
        self.quality_detector = CodeQualityAnomalyDetector(
            cache_manager, symbol_cache, self.config
        )
    
    def run_comprehensive_anomaly_detection(self, project_id: str = None, 
                                          file_paths: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive anomaly detection"""
        results = {
            "detection_timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "config": asdict(self.config),
            "performance_anomalies": [],
            "quality_anomalies": [],
            "summary": {}
        }
        
        # Update baselines first
        self.performance_detector.update_baselines(project_id)
        
        # Detect performance anomalies
        if "performance" in self.config.enabled_detectors:
            perf_anomalies = self.performance_detector.detect_anomalies(project_id)
            results["performance_anomalies"] = [asdict(a) for a in perf_anomalies]
        
        # Detect code quality anomalies
        if "code_quality" in self.config.enabled_detectors and file_paths:
            quality_anomalies = self.quality_detector.detect_code_quality_anomalies(file_paths)
            results["quality_anomalies"] = [asdict(a) for a in quality_anomalies]
        
        # Generate summary
        results["summary"] = self._generate_anomaly_summary(
            results["performance_anomalies"],
            results["quality_anomalies"]
        )
        
        return results
    
    def _generate_anomaly_summary(self, perf_anomalies: List[Dict], 
                                 quality_anomalies: List[Dict]) -> Dict[str, Any]:
        """Generate summary of detected anomalies"""
        total_anomalies = len(perf_anomalies) + len(quality_anomalies)
        
        # Count by severity
        severity_counts = defaultdict(int)
        for anomaly in perf_anomalies + quality_anomalies:
            severity_counts[anomaly.get("severity", "unknown")] += 1
        
        # Count by type
        type_counts = defaultdict(int)
        for anomaly in perf_anomalies:
            type_counts[anomaly.get("anomaly_type", "unknown")] += 1
        for anomaly in quality_anomalies:
            type_counts[anomaly.get("anomaly_type", "unknown")] += 1
        
        return {
            "total_anomalies": total_anomalies,
            "performance_anomalies_count": len(perf_anomalies),
            "quality_anomalies_count": len(quality_anomalies),
            "severity_distribution": dict(severity_counts),
            "type_distribution": dict(type_counts),
            "critical_issues": len([a for a in perf_anomalies + quality_anomalies 
                                  if a.get("severity") == "critical"]),
            "recommendations": self._generate_summary_recommendations(
                perf_anomalies, quality_anomalies
            )
        }
    
    def _generate_summary_recommendations(self, perf_anomalies: List[Dict], 
                                        quality_anomalies: List[Dict]) -> List[str]:
        """Generate high-level recommendations"""
        recommendations = []
        
        critical_count = len([a for a in perf_anomalies + quality_anomalies 
                            if a.get("severity") == "critical"])
        
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical anomalies immediately")
        
        perf_count = len(perf_anomalies)
        quality_count = len(quality_anomalies)
        
        if perf_count > quality_count * 2:
            recommendations.append("Focus on performance optimization")
        elif quality_count > perf_count * 2:
            recommendations.append("Focus on code quality improvements")
        
        if perf_count + quality_count > 10:
            recommendations.append("Consider systematic review of development practices")
        
        return recommendations