"""ML-based adaptive governance engine for ATLAS MCP tools."""

import json
import pickle
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import hashlib

try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Create dummy classes to prevent import errors
    class StandardScaler:
        def fit_transform(self, X): return X
        def transform(self, X): return X
    class RandomForestClassifier:
        def __init__(self, **kwargs): pass
        def fit(self, X, y): pass
        def predict(self, X): return [0]
        def predict_proba(self, X): return [[0.5, 0.5]]
    class IsolationForest:
        def __init__(self, **kwargs): pass
        def fit(self, X): pass
        def predict(self, X): return [1]
        def decision_function(self, X): return [0.0]

from .metrics import get_metrics_collector
from .policies import TOOL_POLICIES, TOOL_CATEGORIES

@dataclass
class GovernanceRecommendation:
    """Recommendation from adaptive governance engine."""
    type: str
    suggestion: str
    confidence: float
    reasoning: str
    priority: str  # HIGH, MEDIUM, LOW
    tool_specific: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

@dataclass
class UsagePattern:
    """Represents a tool usage pattern."""
    tool_name: str
    category: str
    frequency: float
    success_rate: float
    avg_execution_time: float
    complexity_score: float
    context_richness: float
    pattern_hash: str

class FeatureExtractor:
    """Extract features from tool usage data for ML models."""
    
    def __init__(self):
        """Initialize feature extractor."""
        self.feature_names = [
            "tool_frequency_per_hour",
            "argument_complexity_score", 
            "context_richness_score",
            "time_since_last_use_minutes",
            "recent_error_rate",
            "entropy_score",
            "execution_time_ms",
            "category_encoding",
            "session_position_normalized",
            "workflow_completion_rate"
        ]
        
    def extract_features(self, tool_name: str, arguments: Dict[str, Any],
                        context: Dict[str, Any]) -> np.ndarray:
        """Extract feature vector from tool usage data."""
        features = []
        
        # Tool frequency (calls per hour)
        features.append(context.get("recent_usage_count", 0) / max(1, context.get("session_hours", 1)))
        
        # Argument complexity (length and nesting depth)
        arg_str = json.dumps(arguments, default=str)
        complexity = len(arg_str) / 1000.0  # Normalize to [0, ~1]
        features.append(min(complexity, 1.0))
        
        # Context richness (amount of available context)
        context_richness = len(str(context)) / 1000.0
        features.append(min(context_richness, 1.0))
        
        # Time since last use (minutes)
        time_since_last = context.get("time_since_last_use_minutes", 0)
        features.append(min(time_since_last / 60.0, 10.0))  # Normalize to hours, cap at 10
        
        # Recent error rate
        features.append(context.get("recent_error_rate", 0.0))
        
        # Entropy score 
        features.append(context.get("entropy_score", 0.5))
        
        # Execution time (ms)
        exec_time = context.get("avg_execution_time_ms", 100)
        features.append(min(exec_time / 10000.0, 1.0))  # Normalize, cap at 10 seconds
        
        # Category encoding (simple ordinal)
        category = TOOL_CATEGORIES.get(tool_name, "general")
        category_map = {
            "memory_management": 0.1,
            "task_management": 0.2,
            "observability": 0.3,
            "workflow_intelligence": 0.4,
            "validation": 0.5,
            "version_control": 0.6,
            "general": 0.7
        }
        features.append(category_map.get(category, 0.7))
        
        # Session position (how far into session)
        session_position = context.get("session_position", 0.5)
        features.append(session_position)
        
        # Workflow completion rate
        features.append(context.get("workflow_completion_rate", 1.0))
        
        return np.array(features)

class UsageClassifier:
    """Classifies tool usage patterns as optimal/suboptimal."""
    
    def __init__(self):
        """Initialize usage classifier."""
        self.model = None
        self.scaler = StandardScaler()
        self.feature_extractor = FeatureExtractor()
        self.is_trained = False
        
    def prepare_training_data(self, usage_logs: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from usage logs."""
        features = []
        labels = []
        
        for log_entry in usage_logs:
            # Extract features
            feature_vector = self.feature_extractor.extract_features(
                tool_name=log_entry.get("tool_name", ""),
                arguments=log_entry.get("arguments", {}),
                context=log_entry.get("context", {})
            )
            features.append(feature_vector)
            
            # Create label (1 = optimal, 0 = suboptimal)
            # Based on compliance score and governance flags
            compliance_score = log_entry.get("compliance_score", 0.5)
            has_violations = len(log_entry.get("governance_flags", [])) > 0
            
            # Optimal if high compliance and no violations
            label = 1 if compliance_score > 0.8 and not has_violations else 0
            labels.append(label)
            
        return np.array(features), np.array(labels)
        
    def train(self, usage_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the usage classifier."""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available for ML training"}
            
        if len(usage_logs) < 10:
            return {"error": f"Insufficient training data: {len(usage_logs)} samples (need at least 10)"}
            
        # Prepare training data
        X, y = self.prepare_training_data(usage_logs)
        
        if len(np.unique(y)) < 2:
            return {"error": "Training data lacks diversity (all samples have same label)"}
            
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train random forest classifier
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        self.is_trained = True
        
        return {
            "training_samples": len(usage_logs),
            "test_accuracy": accuracy,
            "feature_importance": dict(zip(
                self.feature_extractor.feature_names,
                self.model.feature_importances_
            ))
        }
        
    def predict_usage_quality(self, tool_name: str, arguments: Dict[str, Any],
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict usage quality and provide recommendations."""
        if not self.is_trained or self.model is None:
            return {
                "prediction": "unknown",
                "confidence": 0.0,
                "reason": "Model not trained"
            }
            
        # Extract features
        features = self.feature_extractor.extract_features(tool_name, arguments, context)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        confidence = max(probabilities)
        
        return {
            "prediction": "optimal" if prediction == 1 else "suboptimal",
            "confidence": confidence,
            "probabilities": {
                "optimal": probabilities[1] if len(probabilities) > 1 else 0,
                "suboptimal": probabilities[0]
            }
        }

class AnomalyDetector:
    """Detects anomalous tool usage patterns."""
    
    def __init__(self):
        """Initialize anomaly detector."""
        self.model = None
        self.feature_extractor = FeatureExtractor()
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def train(self, usage_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the anomaly detector."""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available for anomaly detection"}
            
        if len(usage_logs) < 20:
            return {"error": f"Insufficient training data: {len(usage_logs)} samples (need at least 20)"}
            
        # Prepare features
        features = []
        for log_entry in usage_logs:
            feature_vector = self.feature_extractor.extract_features(
                tool_name=log_entry.get("tool_name", ""),
                arguments=log_entry.get("arguments", {}),
                context=log_entry.get("context", {})
            )
            features.append(feature_vector)
            
        X = np.array(features)
        X_scaled = self.scaler.fit_transform(X)
        
        # Train isolation forest
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        
        self.model.fit(X_scaled)
        self.is_trained = True
        
        return {
            "training_samples": len(usage_logs),
            "contamination_rate": 0.1,
            "model_type": "IsolationForest"
        }
        
    def detect_anomaly(self, tool_name: str, arguments: Dict[str, Any],
                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if tool usage is anomalous."""
        if not self.is_trained or self.model is None:
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "reason": "Model not trained"
            }
            
        # Extract features
        features = self.feature_extractor.extract_features(tool_name, arguments, context)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Detect anomaly
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.decision_function(features_scaled)[0]
        
        return {
            "is_anomaly": prediction == -1,
            "anomaly_score": float(anomaly_score),
            "confidence": abs(anomaly_score)
        }

class AdaptiveGovernanceEngine:
    """Main adaptive governance engine with ML capabilities."""
    
    def __init__(self, models_dir: str = "~/.atlas/models"):
        """Initialize adaptive governance engine."""
        self.models_dir = Path(models_dir).expanduser()
        self.models_dir.mkdir(exist_ok=True)
        
        self.usage_classifier = UsageClassifier()
        self.anomaly_detector = AnomalyDetector()
        
        # Load existing models if available
        self._load_models()
        
        # Usage history for pattern learning
        self.usage_history = deque(maxlen=1000)
        
    def _load_models(self) -> None:
        """Load trained models from disk."""
        try:
            classifier_path = self.models_dir / "usage_classifier.pkl"
            anomaly_path = self.models_dir / "anomaly_detector.pkl"
            
            if classifier_path.exists():
                with open(classifier_path, 'rb') as f:
                    self.usage_classifier = pickle.load(f)
                    
            if anomaly_path.exists():
                with open(anomaly_path, 'rb') as f:
                    self.anomaly_detector = pickle.load(f)
                    
        except Exception as e:
            print(f"Warning: Could not load models: {e}")
            
    def _save_models(self) -> None:
        """Save trained models to disk."""
        try:
            classifier_path = self.models_dir / "usage_classifier.pkl"
            anomaly_path = self.models_dir / "anomaly_detector.pkl"
            
            with open(classifier_path, 'wb') as f:
                pickle.dump(self.usage_classifier, f)
                
            with open(anomaly_path, 'wb') as f:
                pickle.dump(self.anomaly_detector, f)
                
        except Exception as e:
            print(f"Warning: Could not save models: {e}")
            
    def train_models(self, usage_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train ML models on usage data."""
        results = {}
        
        # Train usage classifier
        classifier_result = self.usage_classifier.train(usage_logs)
        results["classifier"] = classifier_result
        
        # Train anomaly detector  
        anomaly_result = self.anomaly_detector.train(usage_logs)
        results["anomaly_detector"] = anomaly_result
        
        # Save models
        self._save_models()
        
        return results
        
    def analyze_tool_usage_pattern(self, tool_name: str, arguments: Dict[str, Any],
                                 context: Dict[str, Any]) -> GovernanceRecommendation:
        """Analyze tool usage and provide recommendations."""
        recommendations = []
        
        # Usage quality prediction
        quality_result = self.usage_classifier.predict_usage_quality(
            tool_name, arguments, context
        )
        
        if quality_result["prediction"] == "suboptimal" and quality_result["confidence"] > 0.7:
            recommendations.append(GovernanceRecommendation(
                type="USAGE_OPTIMIZATION",
                suggestion=f"Tool usage pattern appears suboptimal. Review arguments and context.",
                confidence=quality_result["confidence"],
                reasoning=f"ML classifier predicted suboptimal usage with {quality_result['confidence']:.2f} confidence",
                priority="MEDIUM"
            ))
            
        # Anomaly detection
        anomaly_result = self.anomaly_detector.detect_anomaly(
            tool_name, arguments, context
        )
        
        if anomaly_result["is_anomaly"] and anomaly_result["confidence"] > 0.5:
            recommendations.append(GovernanceRecommendation(
                type="ANOMALY_DETECTED",
                suggestion=f"Unusual usage pattern detected. Verify this is intentional.",
                confidence=anomaly_result["confidence"],
                reasoning=f"Anomaly detector flagged usage with score {anomaly_result['anomaly_score']:.3f}",
                priority="HIGH" if anomaly_result["confidence"] > 0.8 else "MEDIUM"
            ))
            
        # Policy-based recommendations
        category = TOOL_CATEGORIES.get(tool_name, "general")
        policy = TOOL_POLICIES.get(category, {})
        
        # Check frequency limits
        recent_frequency = context.get("recent_usage_count", 0)
        max_frequency = policy.get("max_frequency_per_session", 50)
        
        if recent_frequency > max_frequency * 0.8:  # 80% of limit
            recommendations.append(GovernanceRecommendation(
                type="FREQUENCY_WARNING",
                suggestion=f"Approaching frequency limit for {category} tools ({recent_frequency}/{max_frequency})",
                confidence=1.0,
                reasoning="Based on governance policy frequency limits",
                priority="LOW"
            ))
            
        # Return highest priority recommendation or default
        if recommendations:
            return max(recommendations, key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[r.priority])
        else:
            return GovernanceRecommendation(
                type="NO_ISSUES",
                suggestion="Tool usage appears optimal",
                confidence=0.8,
                reasoning="No issues detected by adaptive governance",
                priority="LOW"
            )
            
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about trained models."""
        return {
            "usage_classifier_trained": self.usage_classifier.is_trained,
            "anomaly_detector_trained": self.anomaly_detector.is_trained,
            "usage_history_size": len(self.usage_history),
            "models_dir": str(self.models_dir),
            "sklearn_available": SKLEARN_AVAILABLE
        }

# Global instance
_adaptive_engine = None

def get_adaptive_engine() -> AdaptiveGovernanceEngine:
    """Get or create global adaptive governance engine."""
    global _adaptive_engine
    if _adaptive_engine is None:
        _adaptive_engine = AdaptiveGovernanceEngine()
    return _adaptive_engine