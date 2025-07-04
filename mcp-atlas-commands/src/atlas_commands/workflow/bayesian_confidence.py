"""
Bayesian Confidence Engine for Adaptive Learning

Replaces static confidence calculation with dynamic Bayesian confidence
based on Beta distributions and evidence accumulation.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import json

try:
    import numpy as np
except ImportError:
    # Fallback for environments without numpy
    import random
    np = None


class ContextType(Enum):
    """Types of project context for confidence modeling"""
    GREENFIELD = "greenfield"
    MAINTENANCE = "maintenance"
    REFACTORING = "refactoring"
    INTEGRATION = "integration"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    DOCUMENTATION = "documentation"


@dataclass
class ConfidenceDistribution:
    """Represents a Beta distribution for command confidence"""
    alpha: float  # Success count + prior
    beta: float   # Failure count + prior
    last_updated: datetime
    total_observations: int
    
    def get_expected_confidence(self) -> float:
        """Calculate expected value of Beta distribution"""
        return self.alpha / (self.alpha + self.beta)
    
    def sample_confidence(self) -> float:
        """Sample confidence value for Thompson Sampling"""
        if np is not None:
            return np.random.beta(self.alpha, self.beta)
        else:
            # Simple fallback using uniform distribution
            return random.uniform(0.3, 0.9)
    
    def get_confidence_interval(self, confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for uncertainty quantification"""
        if np is not None:
            # Approximate confidence interval using normal approximation
            mean = self.get_expected_confidence()
            var = (self.alpha * self.beta) / ((self.alpha + self.beta)**2 * (self.alpha + self.beta + 1))
            std = math.sqrt(var)
            
            # Normal approximation Z-score for confidence level
            z_score = 1.96 if confidence_level == 0.95 else 1.64  # 90% CI
            margin = z_score * std
            
            return (max(0.0, mean - margin), min(1.0, mean + margin))
        else:
            # Simple fallback
            mean = self.get_expected_confidence()
            return (max(0.0, mean - 0.1), min(1.0, mean + 0.1))


class BayesianConfidenceCalculator:
    """
    Dynamic confidence calculation using Bayesian inference.
    
    Replaces static confidence caps with evidence-based confidence
    that grows with successful outcomes and decreases with failures.
    """
    
    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        """
        Initialize Bayesian confidence calculator.
        
        Args:
            prior_alpha: Prior successful outcomes (optimistic: >1, pessimistic: <1)
            prior_beta: Prior failed outcomes (optimistic: <1, pessimistic: >1)
        """
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.distributions: Dict[str, ConfidenceDistribution] = {}
        
    def calculate_confidence(self, command: str, context: str, 
                           learning_data: Dict[str, Any]) -> float:
        """
        Calculate expected confidence for a command in given context.
        
        Args:
            command: Command name
            context: Context identifier
            learning_data: Historical learning data
            
        Returns:
            Dynamic confidence value (0.0 to 1.0)
        """
        key = f"{command}_{context}"
        
        if key not in self.distributions:
            self._initialize_distribution(key, learning_data)
        
        distribution = self.distributions[key]
        return distribution.get_expected_confidence()
    
    def sample_confidence(self, command: str, context: str,
                         learning_data: Dict[str, Any]) -> float:
        """
        Sample confidence value for Thompson Sampling exploration.
        
        Args:
            command: Command name
            context: Context identifier
            learning_data: Historical learning data
            
        Returns:
            Sampled confidence value for exploration
        """
        key = f"{command}_{context}"
        
        if key not in self.distributions:
            self._initialize_distribution(key, learning_data)
        
        distribution = self.distributions[key]
        return distribution.sample_confidence()
    
    def update_from_outcome(self, command: str, context: str,
                           outcome: str, timestamp: Optional[datetime] = None) -> None:
        """
        Update confidence distribution based on execution outcome.
        
        Args:
            command: Command name
            context: Context identifier
            outcome: 'success' or 'failure'
            timestamp: When outcome occurred (defaults to now)
        """
        key = f"{command}_{context}"
        timestamp = timestamp or datetime.now()
        
        if key not in self.distributions:
            # Initialize with minimal prior
            self.distributions[key] = ConfidenceDistribution(
                alpha=self.prior_alpha,
                beta=self.prior_beta,
                last_updated=timestamp,
                total_observations=0
            )
        
        distribution = self.distributions[key]
        
        # Update distribution based on outcome
        if outcome == "success":
            distribution.alpha += 1
        else:
            distribution.beta += 1
            
        distribution.last_updated = timestamp
        distribution.total_observations += 1
    
    def get_confidence_uncertainty(self, command: str, context: str) -> float:
        """
        Calculate uncertainty in confidence estimate.
        
        Higher uncertainty indicates need for more exploration.
        
        Args:
            command: Command name
            context: Context identifier
            
        Returns:
            Uncertainty measure (0.0 = certain, 1.0 = very uncertain)
        """
        key = f"{command}_{context}"
        
        if key not in self.distributions:
            return 1.0  # Maximum uncertainty for unknown commands
        
        distribution = self.distributions[key]
        
        # Uncertainty decreases with more observations
        # Use variance of Beta distribution as uncertainty measure
        total = distribution.alpha + distribution.beta
        variance = (distribution.alpha * distribution.beta) / (total**2 * (total + 1))
        
        # Normalize variance to 0-1 scale
        return min(1.0, variance * 4.0)  # Scale factor for reasonable range
    
    def _initialize_distribution(self, key: str, learning_data: Dict[str, Any]) -> None:
        """Initialize distribution from historical learning data"""
        successes = len(learning_data.get('successful_patterns', []))
        failures = len(learning_data.get('failed_patterns', []))
        
        # Get timestamp of most recent pattern
        last_updated = datetime.now()
        all_patterns = (learning_data.get('successful_patterns', []) + 
                       learning_data.get('failed_patterns', []))
        
        if all_patterns:
            timestamps = []
            for pattern in all_patterns:
                if isinstance(pattern, dict) and 'timestamp' in pattern:
                    try:
                        ts = datetime.fromisoformat(pattern['timestamp'])
                        timestamps.append(ts)
                    except (ValueError, TypeError):
                        pass
            
            if timestamps:
                last_updated = max(timestamps)
        
        self.distributions[key] = ConfidenceDistribution(
            alpha=successes + self.prior_alpha,
            beta=failures + self.prior_beta,
            last_updated=last_updated,
            total_observations=successes + failures
        )


class ContextConfidenceModeler:
    """
    Maintains separate confidence models for different context types.
    
    Different contexts have different risk profiles and success patterns.
    """
    
    def __init__(self):
        # Context-specific priors based on typical risk/success patterns
        self.context_priors = {
            ContextType.DEBUGGING: (0.5, 1.5),      # Conservative: debugging is risky
            ContextType.GREENFIELD: (1.0, 1.0),     # Neutral: new projects vary
            ContextType.REFACTORING: (0.8, 1.2),    # Slightly conservative
            ContextType.MAINTENANCE: (1.2, 0.8),    # Slightly optimistic: fixes usually work
            ContextType.OPTIMIZATION: (0.7, 1.3),   # Conservative: optimization can break things
            ContextType.INTEGRATION: (0.6, 1.4),    # Very conservative: integration is complex
            ContextType.DOCUMENTATION: (1.5, 0.5)   # Optimistic: documentation rarely "fails"
        }
        
        self.calculators: Dict[ContextType, BayesianConfidenceCalculator] = {}
    
    def get_context_calculator(self, context_type: ContextType) -> BayesianConfidenceCalculator:
        """Get context-specific confidence calculator"""
        if context_type not in self.calculators:
            prior_alpha, prior_beta = self.context_priors.get(
                context_type, (1.0, 1.0)  # Default neutral priors
            )
            
            self.calculators[context_type] = BayesianConfidenceCalculator(
                prior_alpha=prior_alpha,
                prior_beta=prior_beta
            )
        
        return self.calculators[context_type]
    
    def classify_context_type(self, context_description: str) -> ContextType:
        """
        Classify context type from description.
        
        Args:
            context_description: Description of current context
            
        Returns:
            Most appropriate context type
        """
        description_lower = context_description.lower()
        
        # Priority-ordered keyword matching
        debug_keywords = [
            'debug', 'troubleshoot', 'diagnose', 'investigate',
            'error', 'failure', 'timeout', 'not working', 'broken',
            'issue', 'problem', 'bug', 'trace'
        ]
        if any(keyword in description_lower for keyword in debug_keywords):
            return ContextType.DEBUGGING
        
        refactor_keywords = [
            'refactor', 'restructure', 'reorganize', 'clean up',
            'extract', 'consolidate', 'simplify', 'modernize',
            'technical debt', 'redesign'
        ]
        if any(keyword in description_lower for keyword in refactor_keywords):
            return ContextType.REFACTORING
        
        optimize_keywords = [
            'optimize', 'performance', 'speed up', 'faster',
            'efficiency', 'reduce latency', 'improve response',
            'scale', 'bottleneck', 'tune'
        ]
        if any(keyword in description_lower for keyword in optimize_keywords):
            return ContextType.OPTIMIZATION
        
        maintenance_keywords = [
            'fix', 'repair', 'patch', 'update', 'maintain',
            'resolve', 'correct', 'address', 'handle'
        ]
        if any(keyword in description_lower for keyword in maintenance_keywords):
            return ContextType.MAINTENANCE
        
        integration_keywords = [
            'integrate', 'connect', 'link', 'interface',
            'api integration', 'webhook', 'sync', 'bridge'
        ]
        if any(keyword in description_lower for keyword in integration_keywords):
            return ContextType.INTEGRATION
        
        doc_keywords = [
            'document', 'documentation', 'readme', 'guide',
            'tutorial', 'api doc', 'write doc', 'update doc'
        ]
        if any(keyword in description_lower for keyword in doc_keywords):
            return ContextType.DOCUMENTATION
        
        # Default to GREENFIELD for unclear/new tasks
        return ContextType.GREENFIELD


class TemporalConfidenceDecay:
    """
    Applies time-based confidence decay for stale patterns.
    
    Confidence in old patterns should decrease over time as
    context and best practices evolve.
    """
    
    def __init__(self, decay_rate: float = 0.1, decay_threshold_days: int = 30):
        """
        Initialize temporal decay parameters.
        
        Args:
            decay_rate: Confidence decay rate per day
            decay_threshold_days: Days before decay starts
        """
        self.decay_rate = decay_rate
        self.decay_threshold_days = decay_threshold_days
    
    def apply_time_decay(self, base_confidence: float, last_used: datetime) -> float:
        """
        Apply temporal decay to confidence based on last usage.
        
        Args:
            base_confidence: Original confidence value
            last_used: When pattern was last used
            
        Returns:
            Time-adjusted confidence value
        """
        days_since_use = (datetime.now() - last_used).days
        
        if days_since_use <= self.decay_threshold_days:
            return base_confidence  # No decay within threshold
        
        # Exponential decay after threshold
        excess_days = days_since_use - self.decay_threshold_days
        decay_factor = math.exp(-self.decay_rate * excess_days)
        
        return base_confidence * decay_factor
    
    def should_refresh_pattern(self, last_used: datetime, 
                              refresh_threshold_days: int = 90) -> bool:
        """
        Determine if pattern needs refreshing due to age.
        
        Args:
            last_used: When pattern was last used
            refresh_threshold_days: Days before suggesting refresh
            
        Returns:
            True if pattern should be refreshed
        """
        days_since_use = (datetime.now() - last_used).days
        return days_since_use > refresh_threshold_days


class ConfidenceCalibrator:
    """
    Applies user/context-specific confidence calibration.
    
    Learns from prediction accuracy to adjust confidence values
    for better calibration with actual outcomes.
    """
    
    def __init__(self):
        self.calibration_history: Dict[str, List[Tuple[float, bool]]] = {}
        self.calibration_curves: Dict[str, callable] = {}
    
    def calibrate_confidence(self, raw_confidence: float, context: str,
                           user_feedback_history: Optional[List[Dict]] = None) -> float:
        """
        Apply calibration curve based on historical feedback.
        
        Args:
            raw_confidence: Uncalibrated confidence value
            context: Context for calibration
            user_feedback_history: Historical user feedback data
            
        Returns:
            Calibrated confidence value
        """
        if context not in self.calibration_curves:
            return raw_confidence  # No calibration available yet
        
        calibration_func = self.calibration_curves[context]
        return calibration_func(raw_confidence)
    
    def update_calibration_data(self, context: str, predicted_confidence: float,
                               actual_outcome: bool) -> None:
        """
        Update calibration data with prediction vs reality.
        
        Args:
            context: Context for calibration
            predicted_confidence: What we predicted
            actual_outcome: What actually happened
        """
        if context not in self.calibration_history:
            self.calibration_history[context] = []
        
        self.calibration_history[context].append((predicted_confidence, actual_outcome))
        
        # Update calibration curve if we have enough data
        if len(self.calibration_history[context]) >= 10:
            self._update_calibration_curve(context)
    
    def _update_calibration_curve(self, context: str) -> None:
        """Update calibration curve using isotonic regression approximation"""
        history = self.calibration_history[context]
        
        # Simple binning approach for calibration
        bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bin_accuracies = {}
        
        for bin_start, bin_end in zip(bins[:-1], bins[1:]):
            bin_predictions = [outcome for conf, outcome in history 
                             if bin_start <= conf < bin_end]
            
            if bin_predictions:
                bin_accuracies[(bin_start, bin_end)] = sum(bin_predictions) / len(bin_predictions)
            else:
                bin_accuracies[(bin_start, bin_end)] = (bin_start + bin_end) / 2  # Default to midpoint
        
        # Create calibration function
        def calibration_func(confidence: float) -> float:
            for (bin_start, bin_end), accuracy in bin_accuracies.items():
                if bin_start <= confidence < bin_end:
                    return accuracy
            return confidence  # Fallback to original
        
        self.calibration_curves[context] = calibration_func
    
    def get_calibration_diagnostics(self, context: str) -> Dict[str, Any]:
        """Get diagnostics about calibration quality"""
        if context not in self.calibration_history:
            return {"status": "no_data"}
        
        history = self.calibration_history[context]
        total_predictions = len(history)
        
        if total_predictions < 5:
            return {"status": "insufficient_data", "predictions": total_predictions}
        
        # Calculate calibration error (simplified)
        confidences = [conf for conf, _ in history]
        outcomes = [outcome for _, outcome in history]
        
        avg_confidence = sum(confidences) / len(confidences)
        avg_accuracy = sum(outcomes) / len(outcomes)
        calibration_error = abs(avg_confidence - avg_accuracy)
        
        return {
            "status": "calibrated",
            "predictions": total_predictions,
            "avg_confidence": avg_confidence,
            "avg_accuracy": avg_accuracy,
            "calibration_error": calibration_error,
            "well_calibrated": calibration_error < 0.1
        }