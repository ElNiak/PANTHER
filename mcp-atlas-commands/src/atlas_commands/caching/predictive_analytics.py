"""
Predictive Analytics System
Phase 4 implementation for predicting cache performance and system behavior
Uses ML models and time series analysis for forecasting
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
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard
from .ml_powered_analytics import PredictiveInsight


@dataclass
class PredictionModel:
    """Represents a trained prediction model"""
    model_id: str
    model_type: str  # 'linear', 'random_forest', 'time_series'
    target_metric: str  # 'hit_rate', 'response_time', 'cache_size'
    prediction_horizon: str  # 'hourly', 'daily', 'weekly'
    accuracy_score: float  # R² or similar
    trained_at: float
    last_updated: float
    feature_importance: Dict[str, float]
    model_parameters: Dict[str, Any]
    validation_metrics: Dict[str, float]


@dataclass
class PredictionResult:
    """Result of a prediction"""
    prediction_id: str
    model_id: str
    target_metric: str
    predicted_value: float
    confidence_interval: Tuple[float, float]
    prediction_horizon: str
    predicted_at: float
    valid_until: float
    context: Dict[str, Any]
    features_used: Dict[str, float]


@dataclass
class TrendAnalysis:
    """Analysis of trends in metrics"""
    metric_name: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable', 'volatile'
    trend_strength: float  # 0-1
    seasonal_patterns: Dict[str, Any]
    volatility_score: float
    anomaly_indicators: List[str]
    forecast_reliability: float


class CachePerformancePredictor:
    """Predicts cache performance metrics using ML"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.performance_dashboard = performance_dashboard
        self.models_cache_type = "prediction_models"
        self.predictions_cache_type = "predictions"
        self._lock = threading.Lock()
        
        # ML components
        self.ml_available = SKLEARN_AVAILABLE
        self.models = {}
        self.scalers = {}
        
        if self.ml_available:
            self.model_types = {
                'linear': LinearRegression(),
                'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
            }
        
        # Data storage
        self.historical_data = defaultdict(lambda: deque(maxlen=10000))
        self.feature_history = defaultdict(lambda: deque(maxlen=10000))
    
    def train_prediction_models(self, lookback_days: int = 7) -> Dict[str, PredictionModel]:
        """Train prediction models on historical data"""
        if not self.ml_available:
            return {}
        
        models = {}
        
        # Collect training data
        training_data = self._collect_training_data(lookback_days)
        
        if not training_data or len(training_data) < 50:
            return models
        
        # Train models for different metrics
        target_metrics = ['hit_rate', 'response_time', 'cache_size']
        
        for metric in target_metrics:
            # Prepare data
            features, targets = self._prepare_training_data(training_data, metric)
            
            if len(features) < 20:
                continue
            
            # Train different model types
            for model_name, model_class in self.model_types.items():
                model = self._train_model(
                    features, targets, model_class, f"{metric}_{model_name}"
                )
                
                if model:
                    models[f"{metric}_{model_name}"] = model
        
        # Store models
        self._store_models(models)
        
        return models
    
    def predict_metric(self, metric_name: str, horizon: str = "hourly", 
                      context: Dict[str, Any] = None) -> Optional[PredictionResult]:
        """Predict a specific metric"""
        # Find best model for metric
        model = self._find_best_model(metric_name)
        
        if not model:
            return None
        
        # Prepare current features
        current_features = self._extract_current_features(context)
        
        if not current_features:
            return None
        
        # Make prediction
        prediction = self._make_prediction(model, current_features)
        
        if prediction is None:
            return None
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(
            model, current_features, prediction
        )
        
        # Create prediction result
        return PredictionResult(
            prediction_id=f"pred_{metric_name}_{int(time.time())}",
            model_id=model.model_id,
            target_metric=metric_name,
            predicted_value=prediction,
            confidence_interval=confidence_interval,
            prediction_horizon=horizon,
            predicted_at=time.time(),
            valid_until=time.time() + self._get_horizon_seconds(horizon),
            context=context or {},
            features_used=current_features
        )
    
    def analyze_trends(self, metric_name: str, lookback_days: int = 30) -> TrendAnalysis:
        """Analyze trends in a metric"""
        # Get historical data
        end_time = time.time()
        start_time = end_time - (lookback_days * 24 * 3600)
        
        historical_values = self._get_metric_history(metric_name, start_time, end_time)
        
        if len(historical_values) < 10:
            return TrendAnalysis(
                metric_name=metric_name,
                trend_direction="unknown",
                trend_strength=0.0,
                seasonal_patterns={},
                volatility_score=0.0,
                anomaly_indicators=[],
                forecast_reliability=0.0
            )
        
        # Analyze trend direction and strength
        trend_direction, trend_strength = self._analyze_trend_direction(historical_values)
        
        # Detect seasonal patterns
        seasonal_patterns = self._detect_seasonal_patterns(historical_values)
        
        # Calculate volatility
        volatility_score = self._calculate_volatility(historical_values)
        
        # Identify anomaly indicators
        anomaly_indicators = self._identify_anomaly_indicators(historical_values)
        
        # Calculate forecast reliability
        forecast_reliability = self._calculate_forecast_reliability(historical_values)
        
        return TrendAnalysis(
            metric_name=metric_name,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            seasonal_patterns=seasonal_patterns,
            volatility_score=volatility_score,
            anomaly_indicators=anomaly_indicators,
            forecast_reliability=forecast_reliability
        )
    
    def generate_predictive_insights(self, project_id: str = None) -> List[PredictiveInsight]:
        """Generate predictive insights for the system"""
        insights = []
        
        # Predict performance degradation
        degradation_insights = self._predict_performance_degradation(project_id)
        insights.extend(degradation_insights)
        
        # Predict cache overflow
        overflow_insights = self._predict_cache_overflow(project_id)
        insights.extend(overflow_insights)
        
        # Predict pattern emergence
        pattern_insights = self._predict_pattern_emergence(project_id)
        insights.extend(pattern_insights)
        
        return insights
    
    def _collect_training_data(self, lookback_days: int) -> List[Dict[str, Any]]:
        """Collect training data from historical performance"""
        end_time = time.time()
        start_time = end_time - (lookback_days * 24 * 3600)
        
        # Get operations data
        operations = self.performance_dashboard.performance_tracker.get_recent_operations(
            lookback_days * 24 * 60  # Convert to minutes
        )
        
        # Aggregate data by time buckets (hourly)
        bucket_size = 3600  # 1 hour
        buckets = defaultdict(list)
        
        for op in operations:
            bucket_key = int(op.timestamp // bucket_size) * bucket_size
            buckets[bucket_key].append(op)
        
        # Convert to training samples
        training_data = []
        for bucket_time, bucket_ops in buckets.items():
            if len(bucket_ops) >= 5:  # Minimum operations per bucket
                sample = self._create_training_sample(bucket_time, bucket_ops)
                training_data.append(sample)
        
        return training_data
    
    def _create_training_sample(self, timestamp: float, operations: List) -> Dict[str, Any]:
        """Create a training sample from operations"""
        # Calculate metrics
        hit_count = sum(1 for op in operations if op.operation_type == "hit")
        total_count = len(operations)
        hit_rate = (hit_count / total_count) * 100 if total_count > 0 else 0
        
        response_times = [op.duration_ms for op in operations]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Get cache size at this time
        cache_info = self.cache_manager.get_cache_size_info()
        cache_size = cache_info.get("total_cache_mb", 0)
        
        # Extract features
        hour_of_day = int((timestamp % 86400) / 3600)
        day_of_week = int((timestamp / 86400) % 7)
        
        cache_types = Counter(op.cache_type for op in operations)
        most_common_cache_type = cache_types.most_common(1)[0][0] if cache_types else "unknown"
        
        return {
            "timestamp": timestamp,
            "hit_rate": hit_rate,
            "response_time": avg_response_time,
            "cache_size": cache_size,
            "operation_count": total_count,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "dominant_cache_type": hash(most_common_cache_type) % 100,
            "response_time_variance": statistics.variance(response_times) if len(response_times) > 1 else 0
        }
    
    def _prepare_training_data(self, training_data: List[Dict], target_metric: str) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data for ML model"""
        features = []
        targets = []
        
        feature_names = [
            "operation_count", "hour_of_day", "day_of_week", 
            "dominant_cache_type", "response_time_variance"
        ]
        
        # Add lagged features for time series
        if len(training_data) > 5:
            sorted_data = sorted(training_data, key=lambda x: x["timestamp"])
            
            for i in range(2, len(sorted_data)):
                current = sorted_data[i]
                prev1 = sorted_data[i-1]
                prev2 = sorted_data[i-2]
                
                # Current features
                feature_vector = [current[name] for name in feature_names]
                
                # Lagged features
                feature_vector.extend([
                    prev1.get(target_metric, 0),
                    prev2.get(target_metric, 0),
                    current["timestamp"] - prev1["timestamp"],  # Time delta
                ])
                
                features.append(feature_vector)
                targets.append(current.get(target_metric, 0))
        
        return features, targets
    
    def _train_model(self, features: List[List[float]], targets: List[float], 
                    model_class, model_id: str) -> Optional[PredictionModel]:
        """Train a prediction model"""
        if len(features) < 10:
            return None
        
        try:
            # Prepare data
            X = np.array(features)
            y = np.array(targets)
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train model
            model = model_class.fit(X_scaled, y)
            
            # Calculate accuracy
            predictions = model.predict(X_scaled)
            r2 = r2_score(y, predictions)
            
            # Get feature importance (if available)
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                importance_values = model.feature_importances_
                feature_names = [f"feature_{i}" for i in range(len(importance_values))]
                feature_importance = dict(zip(feature_names, importance_values))
            
            # Store model and scaler
            self.models[model_id] = model
            self.scalers[model_id] = scaler
            
            return PredictionModel(
                model_id=model_id,
                model_type=type(model_class).__name__,
                target_metric=model_id.split('_')[0],
                prediction_horizon="hourly",
                accuracy_score=r2,
                trained_at=time.time(),
                last_updated=time.time(),
                feature_importance=feature_importance,
                model_parameters={},
                validation_metrics={"r2_score": r2, "mse": mean_squared_error(y, predictions)}
            )
            
        except Exception as e:
            print(f"Error training model {model_id}: {e}")
            return None
    
    def _find_best_model(self, metric_name: str) -> Optional[PredictionModel]:
        """Find the best model for a metric"""
        # Load stored models
        stored_models = self._load_stored_models()
        
        # Find models for this metric
        metric_models = [m for m in stored_models.values() 
                        if m.target_metric == metric_name]
        
        if not metric_models:
            return None
        
        # Return model with highest accuracy
        return max(metric_models, key=lambda m: m.accuracy_score)
    
    def _extract_current_features(self, context: Dict[str, Any] = None) -> Dict[str, float]:
        """Extract current features for prediction"""
        # Get current performance metrics
        current_time = time.time()
        recent_ops = self.performance_dashboard.performance_tracker.get_recent_operations(60)  # Last hour
        
        if not recent_ops:
            return {}
        
        # Calculate current metrics
        hit_count = sum(1 for op in recent_ops if op.operation_type == "hit")
        total_count = len(recent_ops)
        operation_count = total_count
        
        response_times = [op.duration_ms for op in recent_ops]
        response_time_variance = statistics.variance(response_times) if len(response_times) > 1 else 0
        
        cache_types = Counter(op.cache_type for op in recent_ops)
        dominant_cache_type = hash(cache_types.most_common(1)[0][0]) % 100 if cache_types else 0
        
        hour_of_day = int((current_time % 86400) / 3600)
        day_of_week = int((current_time / 86400) % 7)
        
        return {
            "operation_count": operation_count,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "dominant_cache_type": dominant_cache_type,
            "response_time_variance": response_time_variance
        }
    
    def _make_prediction(self, model: PredictionModel, features: Dict[str, float]) -> Optional[float]:
        """Make a prediction using the model"""
        if model.model_id not in self.models:
            return None
        
        try:
            # Prepare feature vector
            feature_vector = [
                features.get("operation_count", 0),
                features.get("hour_of_day", 0),
                features.get("day_of_week", 0),
                features.get("dominant_cache_type", 0),
                features.get("response_time_variance", 0),
                0, 0, 3600  # Placeholder for lagged features
            ]
            
            # Scale features
            scaler = self.scalers.get(model.model_id)
            if not scaler:
                return None
            
            X = np.array([feature_vector])
            X_scaled = scaler.transform(X)
            
            # Make prediction
            ml_model = self.models[model.model_id]
            prediction = ml_model.predict(X_scaled)[0]
            
            return float(prediction)
            
        except Exception as e:
            print(f"Error making prediction: {e}")
            return None
    
    def _calculate_confidence_interval(self, model: PredictionModel, 
                                     features: Dict[str, float], 
                                     prediction: float) -> Tuple[float, float]:
        """Calculate confidence interval for prediction"""
        # Simple confidence interval based on model accuracy
        accuracy = model.accuracy_score
        uncertainty = (1 - accuracy) * abs(prediction) * 0.5
        
        return (prediction - uncertainty, prediction + uncertainty)
    
    def _get_horizon_seconds(self, horizon: str) -> int:
        """Get seconds for prediction horizon"""
        horizons = {
            "hourly": 3600,
            "daily": 86400,
            "weekly": 604800
        }
        return horizons.get(horizon, 3600)
    
    def _get_metric_history(self, metric_name: str, start_time: float, 
                           end_time: float) -> List[float]:
        """Get historical values for a metric"""
        # This would retrieve actual historical data
        # For now, simulate some data
        values = []
        current_time = start_time
        base_value = 50.0 if metric_name == "hit_rate" else 20.0
        
        while current_time < end_time:
            # Add some trend and noise
            trend = (current_time - start_time) / (end_time - start_time) * 10
            noise = np.random.normal(0, 5) if np else 0
            value = base_value + trend + noise
            values.append(max(0, value))
            current_time += 3600  # Hour intervals
        
        return values
    
    def _analyze_trend_direction(self, values: List[float]) -> Tuple[str, float]:
        """Analyze trend direction and strength"""
        if len(values) < 3:
            return "unknown", 0.0
        
        # Simple linear regression for trend
        x = list(range(len(values)))
        
        if not SKLEARN_AVAILABLE:
            # Simple slope calculation
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(xi ** 2 for xi in x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            
        else:
            model = LinearRegression()
            X = np.array(x).reshape(-1, 1)
            model.fit(X, values)
            slope = model.coef_[0]
        
        # Determine direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Strength is absolute slope normalized
        strength = min(abs(slope) / max(values), 1.0) if values else 0.0
        
        return direction, strength
    
    def _detect_seasonal_patterns(self, values: List[float]) -> Dict[str, Any]:
        """Detect seasonal patterns in data"""
        # Simple pattern detection
        if len(values) < 24:  # Need at least 24 hours
            return {}
        
        # Check for daily patterns (24-hour cycle)
        daily_pattern = []
        for hour in range(24):
            hour_values = [values[i] for i in range(hour, len(values), 24) if i < len(values)]
            if hour_values:
                daily_pattern.append(statistics.mean(hour_values))
        
        # Check for variation in daily pattern
        daily_variation = statistics.stdev(daily_pattern) if len(daily_pattern) > 1 else 0
        
        return {
            "daily_pattern_detected": daily_variation > 5.0,
            "daily_pattern_strength": min(daily_variation / 20.0, 1.0),
            "peak_hour": daily_pattern.index(max(daily_pattern)) if daily_pattern else 0,
            "low_hour": daily_pattern.index(min(daily_pattern)) if daily_pattern else 0
        }
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility score"""
        if len(values) < 2:
            return 0.0
        
        # Calculate coefficient of variation
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        if mean_val == 0:
            return 0.0
        
        cv = std_val / mean_val
        return min(cv, 2.0) / 2.0  # Normalize to 0-1
    
    def _identify_anomaly_indicators(self, values: List[float]) -> List[str]:
        """Identify indicators of anomalous behavior"""
        indicators = []
        
        if len(values) < 10:
            return indicators
        
        # Check for sudden spikes
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        spikes = [v for v in values if abs(v - mean_val) > 2 * std_val]
        if len(spikes) > len(values) * 0.1:
            indicators.append("frequent_spikes")
        
        # Check for trend reversal
        recent_trend = values[-5:]
        earlier_trend = values[-10:-5] if len(values) >= 10 else []
        
        if len(recent_trend) >= 3 and len(earlier_trend) >= 3:
            recent_slope = (recent_trend[-1] - recent_trend[0]) / len(recent_trend)
            earlier_slope = (earlier_trend[-1] - earlier_trend[0]) / len(earlier_trend)
            
            if recent_slope * earlier_slope < 0 and abs(recent_slope) > 1:
                indicators.append("trend_reversal")
        
        return indicators
    
    def _calculate_forecast_reliability(self, values: List[float]) -> float:
        """Calculate reliability of forecasts based on historical data"""
        if len(values) < 10:
            return 0.5
        
        # Calculate consistency of recent patterns
        volatility = self._calculate_volatility(values)
        trend_strength = self._analyze_trend_direction(values)[1]
        
        # Higher reliability for low volatility and clear trends
        reliability = (1 - volatility) * 0.6 + trend_strength * 0.4
        
        return min(max(reliability, 0.0), 1.0)
    
    def _predict_performance_degradation(self, project_id: str) -> List[PredictiveInsight]:
        """Predict potential performance degradation"""
        insights = []
        
        # Analyze response time trend
        response_time_trend = self.analyze_trends("response_time", 7)
        
        if (response_time_trend.trend_direction == "increasing" and 
            response_time_trend.trend_strength > 0.3):
            
            insight = PredictiveInsight(
                insight_id=f"perf_degradation_{int(time.time())}",
                insight_type="performance_degradation",
                prediction_horizon="days",
                confidence=response_time_trend.trend_strength,
                predicted_impact={
                    "response_time_increase_percent": response_time_trend.trend_strength * 50,
                    "user_experience_impact": "medium" if response_time_trend.trend_strength > 0.5 else "low"
                },
                trigger_conditions=[
                    f"Response time trending upward with strength {response_time_trend.trend_strength:.2f}",
                    f"Volatility score: {response_time_trend.volatility_score:.2f}"
                ],
                prevention_strategies=[
                    "Monitor cache hit rates",
                    "Review recent code changes",
                    "Check system resource utilization",
                    "Consider cache warming strategies"
                ],
                generated_at=time.time(),
                model_version="trend_analysis_v1"
            )
            insights.append(insight)
        
        return insights
    
    def _predict_cache_overflow(self, project_id: str) -> List[PredictiveInsight]:
        """Predict potential cache overflow"""
        insights = []
        
        # Analyze cache size trend
        cache_size_trend = self.analyze_trends("cache_size", 7)
        
        if (cache_size_trend.trend_direction == "increasing" and 
            cache_size_trend.trend_strength > 0.4):
            
            # Get current cache info
            cache_info = self.cache_manager.get_cache_size_info()
            current_size = cache_info.get("total_cache_mb", 0)
            
            # Estimate time to overflow (simple linear projection)
            days_to_overflow = self._estimate_days_to_overflow(current_size, cache_size_trend)
            
            if days_to_overflow and days_to_overflow < 30:
                insight = PredictiveInsight(
                    insight_id=f"cache_overflow_{int(time.time())}",
                    insight_type="cache_overflow",
                    prediction_horizon="days",
                    confidence=cache_size_trend.forecast_reliability,
                    predicted_impact={
                        "estimated_days_to_overflow": days_to_overflow,
                        "performance_impact": "high",
                        "system_stability_risk": "medium"
                    },
                    trigger_conditions=[
                        f"Cache size growing at {cache_size_trend.trend_strength:.2f} strength",
                        f"Current size: {current_size:.1f}MB"
                    ],
                    prevention_strategies=[
                        "Implement cache cleanup policies",
                        "Review cache retention settings",
                        "Consider cache compression",
                        "Archive old cache entries"
                    ],
                    generated_at=time.time(),
                    model_version="trend_analysis_v1"
                )
                insights.append(insight)
        
        return insights
    
    def _predict_pattern_emergence(self, project_id: str) -> List[PredictiveInsight]:
        """Predict emergence of new patterns"""
        # This would analyze code changes and predict new patterns
        # For now, return empty list
        return []
    
    def _estimate_days_to_overflow(self, current_size: float, trend: TrendAnalysis) -> Optional[float]:
        """Estimate days until cache overflow"""
        # Assume overflow at 1GB (1000MB)
        overflow_threshold = 1000.0
        
        if current_size >= overflow_threshold:
            return None
        
        # Simple linear projection
        if trend.trend_strength > 0:
            daily_growth = trend.trend_strength * 10  # Rough estimate
            days_remaining = (overflow_threshold - current_size) / daily_growth
            return max(1, days_remaining)
        
        return None
    
    def _store_models(self, models: Dict[str, PredictionModel]):
        """Store trained models"""
        models_data = {k: asdict(v) for k, v in models.items()}
        self.cache_manager.set_cache(
            self.models_cache_type,
            "trained_models",
            models_data,
            cache_level="global"
        )
    
    def _load_stored_models(self) -> Dict[str, PredictionModel]:
        """Load stored models"""
        models_data = self.cache_manager.get_cache(
            self.models_cache_type,
            "trained_models",
            cache_level="global"
        )
        
        if not models_data:
            return {}
        
        models = {}
        for k, v in models_data.items():
            models[k] = PredictionModel(**v)
        
        return models


class PredictiveAnalyticsOrchestrator:
    """Orchestrates predictive analytics across the system"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 performance_dashboard: CachePerformanceDashboard):
        self.cache_manager = cache_manager
        self.performance_dashboard = performance_dashboard
        
        # Initialize predictor
        self.performance_predictor = CachePerformancePredictor(
            cache_manager, performance_dashboard
        )
    
    def run_comprehensive_prediction_analysis(self, project_id: str = None) -> Dict[str, Any]:
        """Run comprehensive predictive analysis"""
        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_id": project_id,
            "model_training": {},
            "predictions": {},
            "trend_analysis": {},
            "predictive_insights": [],
            "recommendations": []
        }
        
        # Train models
        trained_models = self.performance_predictor.train_prediction_models()
        results["model_training"] = {
            "models_trained": len(trained_models),
            "model_details": {k: asdict(v) for k, v in trained_models.items()}
        }
        
        # Make predictions
        metrics_to_predict = ["hit_rate", "response_time", "cache_size"]
        for metric in metrics_to_predict:
            prediction = self.performance_predictor.predict_metric(metric)
            if prediction:
                results["predictions"][metric] = asdict(prediction)
        
        # Analyze trends
        for metric in metrics_to_predict:
            trend = self.performance_predictor.analyze_trends(metric)
            results["trend_analysis"][metric] = asdict(trend)
        
        # Generate insights
        insights = self.performance_predictor.generate_predictive_insights(project_id)
        results["predictive_insights"] = [asdict(insight) for insight in insights]
        
        # Generate recommendations
        results["recommendations"] = self._generate_predictive_recommendations(
            results["trend_analysis"], insights
        )
        
        return results
    
    def _generate_predictive_recommendations(self, trends: Dict[str, Any], 
                                           insights: List[PredictiveInsight]) -> List[str]:
        """Generate recommendations based on predictions"""
        recommendations = []
        
        # Check for concerning trends
        for metric, trend_data in trends.items():
            trend = TrendAnalysis(**trend_data)
            
            if trend.volatility_score > 0.7:
                recommendations.append(f"High volatility detected in {metric} - investigate causes")
            
            if trend.trend_direction == "decreasing" and metric == "hit_rate":
                recommendations.append("Cache hit rate declining - review caching strategies")
            
            if trend.trend_direction == "increasing" and metric == "response_time":
                recommendations.append("Response time increasing - optimize performance")
        
        # Add insight-based recommendations
        critical_insights = [i for i in insights if i.confidence > 0.7]
        if critical_insights:
            recommendations.append(f"Address {len(critical_insights)} high-confidence predictive insights")
        
        return recommendations