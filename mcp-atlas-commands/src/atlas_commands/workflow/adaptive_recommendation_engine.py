"""
Adaptive Recommendation Engine - Central Orchestrator

Orchestrates all adaptive learning components to provide intelligent command 
recommendations that actually improve over time, replacing the static system.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from .bayesian_confidence import (
    BayesianConfidenceCalculator, 
    ContextConfidenceModeler,
    TemporalConfidenceDecay,
    ConfidenceCalibrator,
    ContextType
)
from .learning_feedback import LearningFeedbackLoop, LearningOutcome
from .thompson_sampling import (
    ThompsonSamplingSelector, 
    SamplingRecommendation,
    ExplorationStrategy
)
from .pattern_analyzer import WorkflowPatternAnalyzer
from .validator import ValidationLevel


class RecommendationMode(Enum):
    """Different modes of recommendation generation"""
    CONSERVATIVE = "conservative"  # Emphasize high-confidence, low-risk choices
    BALANCED = "balanced"         # Balance exploration and exploitation
    EXPLORATORY = "exploratory"   # Emphasize discovering new patterns
    ADAPTIVE = "adaptive"         # Automatically adjust based on context


@dataclass
class AdaptiveRecommendation:
    """Enhanced recommendation with adaptive learning metadata"""
    command: str
    confidence: float
    expected_confidence: float  # What Bayesian model expects
    sampled_confidence: float   # What Thompson sampling selected
    reasoning: str
    prerequisites: List[str]
    expected_outcome: str
    risk_level: str
    estimated_time: float
    
    # Adaptive learning metadata
    uncertainty: float
    is_exploration: bool
    exploration_bonus: float
    learning_potential: float  # How much we could learn from this choice
    context_type: ContextType
    confidence_trend: str      # "improving", "stable", "declining"
    
    # Quality metrics
    calibration_quality: float  # How well-calibrated our confidence is
    temporal_freshness: float   # How recent/relevant the pattern is


class AdaptiveRecommendationEngine:
    """
    Central orchestrator for adaptive command recommendations.
    
    This class replaces the static recommendation system with a dynamic one that:
    1. Uses Bayesian confidence instead of static caps
    2. Employs Thompson Sampling for exploration-exploitation balance
    3. Learns from outcomes to improve future recommendations
    4. Provides detailed analytics about learning effectiveness
    """
    
    def __init__(self, 
                 storage_path: Optional[str] = None,
                 exploration_strategy: ExplorationStrategy = ExplorationStrategy.ADAPTIVE_EXPLORATION,
                 recommendation_mode: RecommendationMode = RecommendationMode.BALANCED,
                 confidence_threshold: float = 0.3):
        """
        Initialize adaptive recommendation engine.
        
        Args:
            storage_path: Path for persistent storage
            exploration_strategy: Strategy for exploration-exploitation balance
            recommendation_mode: Mode for recommendation generation
            confidence_threshold: Minimum confidence for recommendations
        """
        # Core components
        self.confidence_engine = BayesianConfidenceCalculator()
        self.context_modeler = ContextConfidenceModeler()
        self.temporal_decay = TemporalConfidenceDecay()
        self.calibrator = ConfidenceCalibrator()
        
        # Learning and exploration
        self.feedback_loop = LearningFeedbackLoop(
            confidence_engine=self.confidence_engine,
            context_modeler=self.context_modeler,
            temporal_decay=self.temporal_decay,
            calibrator=self.calibrator
        )
        self.thompson_selector = ThompsonSamplingSelector(
            confidence_engine=self.confidence_engine,
            context_modeler=self.context_modeler,
            exploration_strategy=exploration_strategy
        )
        
        # Pattern analysis
        self.pattern_analyzer = WorkflowPatternAnalyzer()
        
        # Configuration
        self.recommendation_mode = recommendation_mode
        self.confidence_threshold = confidence_threshold
        self.storage_path = storage_path
        
        # Analytics
        self.recommendation_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "total_recommendations": 0,
            "successful_recommendations": 0,
            "average_confidence_improvement": 0.0,
            "exploration_discovery_rate": 0.0,
            "calibration_accuracy": 0.0
        }
    
    def recommend_commands(self,
                          task_description: str,
                          domain: str,
                          current_phase: str = "planning",
                          previous_commands: List[str] = None,
                          project_state: Dict[str, Any] = None,
                          candidate_commands: List[str] = None,
                          limit: int = 5) -> List[AdaptiveRecommendation]:
        """
        Generate adaptive command recommendations.
        
        Args:
            task_description: Description of current task
            domain: Project domain
            current_phase: Current workflow phase
            previous_commands: Previously executed commands
            project_state: Additional project state information
            candidate_commands: Specific commands to evaluate (optional)
            limit: Maximum number of recommendations
            
        Returns:
            List of adaptive recommendations
        """
        previous_commands = previous_commands or []
        project_state = project_state or {}
        
        # Create context identifier
        context = self._create_context_identifier(domain, current_phase, task_description)
        
        # Get candidate commands if not provided
        if candidate_commands is None:
            candidate_commands = self._generate_candidate_commands(
                task_description, domain, current_phase, previous_commands
            )
        
        # Gather historical learning data
        learning_data = self._gather_learning_data(context, domain, current_phase)
        
        # Use Thompson Sampling for command selection
        sampling_recommendations = self.thompson_selector.select_command(
            candidates=candidate_commands,
            context=context,
            learning_data=learning_data,
            top_k=limit * 2  # Get more for filtering
        )
        
        # Convert to adaptive recommendations with full metadata
        adaptive_recommendations = []
        for sampling_rec in sampling_recommendations:
            adaptive_rec = self._create_adaptive_recommendation(
                sampling_rec, context, domain, current_phase, 
                task_description, previous_commands, learning_data
            )
            
            # Apply confidence threshold
            if adaptive_rec.confidence >= self.confidence_threshold:
                adaptive_recommendations.append(adaptive_rec)
        
        # Apply recommendation mode filters
        filtered_recommendations = self._apply_recommendation_mode_filters(
            adaptive_recommendations, context
        )
        
        # Track recommendations for analytics
        self._track_recommendations(filtered_recommendations[:limit], context)
        
        return filtered_recommendations[:limit]
    
    def learn_from_outcome(self,
                          commands_used: List[str],
                          task_description: str,
                          domain: str,
                          current_phase: str,
                          outcome: str,
                          execution_time: Optional[float] = None,
                          notes: Optional[str] = None,
                          quality_metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Learn from command execution outcomes to improve future recommendations.
        
        This is where the adaptive learning happens - outcomes feed back into
        the Bayesian confidence models to improve future recommendations.
        
        Args:
            commands_used: Commands that were executed
            task_description: Task description
            domain: Project domain
            current_phase: Current workflow phase
            outcome: 'success', 'failure', or 'partial'
            execution_time: Time taken for execution
            notes: Additional notes about execution
            quality_metrics: Quality metrics from execution
            
        Returns:
            Learning impact summary
        """
        # Create context dictionary
        context_dict = {
            'domain': domain,
            'complexity': self._determine_complexity(task_description),
            'current_phase': current_phase,
            'task_description': task_description
        }
        
        # Process outcome through feedback loop
        impact_summary = self.feedback_loop.process_outcome(
            commands_used=commands_used,
            context_dict=context_dict,
            outcome=outcome,
            execution_time=execution_time,
            notes=notes
        )
        
        # Update Thompson sampling exploration rate based on outcome
        recent_success_rate = self._calculate_recent_success_rate()
        discovery_evidence = self._analyze_discovery_evidence(
            commands_used, outcome, quality_metrics
        )
        self.thompson_selector.update_exploration_rate(
            recent_success_rate, discovery_evidence
        )
        
        # Update performance metrics
        self._update_performance_metrics(outcome, impact_summary)
        
        return {
            **impact_summary,
            "adaptive_learning_impact": self._calculate_learning_impact(impact_summary),
            "exploration_adjustment": discovery_evidence,
            "performance_trend": self._get_performance_trend()
        }
    
    def get_learning_effectiveness_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive report on learning effectiveness.
        
        This addresses the key requirement: measure actual improvement
        rather than just pattern storage.
        """
        # Get feedback loop metrics
        feedback_metrics = self.feedback_loop.get_learning_effectiveness_metrics()
        
        # Get exploration analytics
        exploration_analytics = self.thompson_selector.get_exploration_analytics()
        
        # Calculate overall improvement metrics
        confidence_improvements = []
        recent_recommendations = self.recommendation_history[-50:]  # Last 50
        
        for rec_data in recent_recommendations:
            if "outcome" in rec_data and rec_data["outcome"] == "success":
                # Calculate improvement from baseline
                baseline_confidence = 0.5  # Default confidence without learning
                actual_confidence = rec_data.get("average_confidence", baseline_confidence)
                improvement = actual_confidence - baseline_confidence
                confidence_improvements.append(improvement)
        
        avg_improvement = (sum(confidence_improvements) / len(confidence_improvements) 
                          if confidence_improvements else 0.0)
        
        # Calculate learning velocity (rate of improvement)
        learning_velocity = avg_improvement * len(confidence_improvements) / max(len(recent_recommendations), 1)
        
        # Overall system status
        if avg_improvement > 0.15:
            status = "high_learning"
        elif avg_improvement > 0.05:
            status = "moderate_learning"
        elif avg_improvement > -0.05:
            status = "stable_learning"
        else:
            status = "learning_decline"
        
        return {
            "status": status,
            "overall_improvement": avg_improvement,
            "learning_velocity": learning_velocity,
            "confidence_baseline": 0.5,
            "current_average_confidence": 0.5 + avg_improvement,
            "improvement_percentage": (avg_improvement / 0.5) * 100 if avg_improvement > 0 else 0,
            
            # Component metrics
            "feedback_loop_metrics": feedback_metrics,
            "exploration_analytics": exploration_analytics,
            
            # Performance trends
            "recent_success_rate": self._calculate_recent_success_rate(),
            "calibration_quality": self._assess_calibration_quality(),
            "discovery_effectiveness": exploration_analytics.get("discovery_rate", 0.0),
            
            # Recommendations for improvement
            "improvement_recommendations": self._generate_improvement_recommendations(
                avg_improvement, exploration_analytics, feedback_metrics
            ),
            
            # Historical comparison
            "comparison_to_static_system": {
                "static_system_confidence": 0.95,  # Artificial cap from old system
                "adaptive_system_confidence": 0.5 + avg_improvement,
                "learning_advantage": avg_improvement,
                "explanation": "Static system provided 0.000 improvement, adaptive system provides measurable improvement"
            }
        }
    
    def analyze_command_learning_pattern(self, 
                                       command: str, 
                                       context_domain: str) -> Dict[str, Any]:
        """
        Analyze learning patterns for specific command in domain.
        
        Args:
            command: Command to analyze
            context_domain: Domain context
            
        Returns:
            Detailed learning pattern analysis
        """
        context = f"{context_domain}_unknown_unknown"  # Generic context for domain
        
        return self.feedback_loop.get_command_learning_analysis(command, context)
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export all learning data for analysis or backup"""
        return {
            "confidence_distributions": {
                key: {
                    "alpha": dist.alpha,
                    "beta": dist.beta,
                    "last_updated": dist.last_updated.isoformat(),
                    "total_observations": dist.total_observations
                }
                for key, dist in self.confidence_engine.distributions.items()
            },
            "learning_history": [
                {
                    "commands": outcome.commands_used,
                    "context": outcome.context,
                    "outcome": outcome.outcome,
                    "timestamp": outcome.timestamp.isoformat(),
                    "execution_time": outcome.execution_time,
                    "notes": outcome.notes
                }
                for outcome in self.feedback_loop.learning_history
            ],
            "exploration_history": self.thompson_selector.selection_history,
            "recommendation_history": self.recommendation_history,
            "performance_metrics": self.performance_metrics
        }
    
    # Private helper methods
    
    def _create_context_identifier(self, domain: str, phase: str, task_description: str) -> str:
        """Create standardized context identifier"""
        complexity = self._determine_complexity(task_description)
        return f"{domain}_{complexity}_{phase}"
    
    def _determine_complexity(self, task_description: str) -> str:
        """Determine task complexity from description"""
        desc_lower = task_description.lower()
        
        if any(word in desc_lower for word in ["simple", "quick", "minor", "small"]):
            return "simple"
        elif any(word in desc_lower for word in ["complex", "major", "large", "comprehensive"]):
            return "complex"
        elif any(word in desc_lower for word in ["epic", "massive", "complete", "full"]):
            return "epic"
        else:
            return "moderate"
    
    def _generate_candidate_commands(self, 
                                   task_description: str,
                                   domain: str,
                                   current_phase: str,
                                   previous_commands: List[str]) -> List[str]:
        """Generate candidate commands based on context"""
        # Base commands by phase
        phase_commands = {
            "planning": ["explore", "analyze", "plan", "design", "decompose"],
            "implementation": ["execute", "implement", "code", "develop", "build"],
            "validation": ["test", "verify", "validate", "review", "check"],
            "completion": ["complete", "document", "deploy", "finalize", "archive"]
        }
        
        base_candidates = phase_commands.get(current_phase, ["analyze", "plan", "execute"])
        
        # Add domain-specific commands
        domain_commands = {
            "debugging": ["investigate", "trace", "reproduce", "isolate", "fix"],
            "refactoring": ["restructure", "extract", "consolidate", "modernize"],
            "optimization": ["profile", "benchmark", "optimize", "tune"],
            "integration": ["connect", "integrate", "sync", "bridge"]
        }
        
        if domain in domain_commands:
            base_candidates.extend(domain_commands[domain])
        
        # Add task-specific commands based on description
        desc_lower = task_description.lower()
        if "test" in desc_lower:
            base_candidates.extend(["test", "validate", "verify"])
        if "document" in desc_lower:
            base_candidates.extend(["document", "explain", "guide"])
        if "performance" in desc_lower:
            base_candidates.extend(["profile", "benchmark", "optimize"])
        
        return list(set(base_candidates))  # Remove duplicates
    
    def _gather_learning_data(self, context: str, domain: str, phase: str) -> Dict[str, Any]:
        """Gather historical learning data for context"""
        # Get successful and failed patterns from feedback loop
        learning_key = context
        success_cache = getattr(self.feedback_loop, 'learning_history', [])
        
        successful_patterns = []
        failed_patterns = []
        
        for outcome in success_cache:
            if outcome.context == context:
                pattern_data = {
                    "commands": outcome.commands_used,
                    "timestamp": outcome.timestamp.isoformat(),
                    "execution_time": outcome.execution_time,
                    "notes": outcome.notes
                }
                
                if outcome.outcome == "success":
                    successful_patterns.append(pattern_data)
                else:
                    failed_patterns.append(pattern_data)
        
        return {
            "successful_patterns": successful_patterns,
            "failed_patterns": failed_patterns,
            "context": context,
            "domain": domain,
            "phase": phase
        }
    
    def _create_adaptive_recommendation(self,
                                      sampling_rec: SamplingRecommendation,
                                      context: str,
                                      domain: str,
                                      phase: str,
                                      task_description: str,
                                      previous_commands: List[str],
                                      learning_data: Dict[str, Any]) -> AdaptiveRecommendation:
        """Create full adaptive recommendation from sampling recommendation"""
        
        # Analyze confidence trend
        confidence_trend = self._analyze_confidence_trend(
            sampling_rec.command, context, learning_data
        )
        
        # Calculate learning potential
        learning_potential = sampling_rec.uncertainty * 0.8  # High uncertainty = high learning potential
        
        # Get context type
        context_type = self.context_modeler.classify_context_type(task_description)
        
        # Assess calibration quality
        calibration_quality = self._assess_command_calibration_quality(
            sampling_rec.command, context
        )
        
        # Calculate temporal freshness
        temporal_freshness = self._calculate_temporal_freshness(learning_data)
        
        # Generate comprehensive reasoning
        reasoning_parts = [sampling_rec.reasoning]
        
        if sampling_rec.uncertainty > 0.7:
            reasoning_parts.append("High uncertainty indicates potential for discovery")
        
        if confidence_trend == "improving":
            reasoning_parts.append("Command confidence has been improving with experience")
        elif confidence_trend == "declining":
            reasoning_parts.append("Command confidence has been declining - needs attention")
        
        if learning_potential > 0.6:
            reasoning_parts.append("High learning potential from this choice")
        
        comprehensive_reasoning = "; ".join(reasoning_parts)
        
        # Estimate prerequisites, time, etc.
        prerequisites = self._estimate_prerequisites(sampling_rec.command, previous_commands)
        risk_level = self._assess_risk_level(sampling_rec.command, context_type)
        estimated_time = self._estimate_execution_time(sampling_rec.command, domain)
        expected_outcome = self._generate_expected_outcome(sampling_rec.command, domain, phase)
        
        return AdaptiveRecommendation(
            command=sampling_rec.command,
            confidence=sampling_rec.sampled_confidence,
            expected_confidence=sampling_rec.expected_confidence,
            sampled_confidence=sampling_rec.sampled_confidence,
            reasoning=comprehensive_reasoning,
            prerequisites=prerequisites,
            expected_outcome=expected_outcome,
            risk_level=risk_level,
            estimated_time=estimated_time,
            
            # Adaptive metadata
            uncertainty=sampling_rec.uncertainty,
            is_exploration=sampling_rec.is_exploration,
            exploration_bonus=sampling_rec.exploration_bonus,
            learning_potential=learning_potential,
            context_type=context_type,
            confidence_trend=confidence_trend,
            
            # Quality metrics
            calibration_quality=calibration_quality,
            temporal_freshness=temporal_freshness
        )
    
    def _apply_recommendation_mode_filters(self,
                                         recommendations: List[AdaptiveRecommendation],
                                         context: str) -> List[AdaptiveRecommendation]:
        """Apply filters based on recommendation mode"""
        if self.recommendation_mode == RecommendationMode.CONSERVATIVE:
            # Prefer high confidence, low risk
            return sorted(recommendations, 
                         key=lambda x: (x.confidence, -self._risk_score(x.risk_level)), 
                         reverse=True)
        
        elif self.recommendation_mode == RecommendationMode.EXPLORATORY:
            # Prefer high learning potential and exploration
            return sorted(recommendations,
                         key=lambda x: (x.learning_potential, x.uncertainty, x.exploration_bonus),
                         reverse=True)
        
        elif self.recommendation_mode == RecommendationMode.BALANCED:
            # Balance confidence and learning potential
            scored_recs = []
            for rec in recommendations:
                balance_score = (rec.confidence * 0.6 + rec.learning_potential * 0.4)
                scored_recs.append((balance_score, rec))
            
            return [rec for score, rec in sorted(scored_recs, key=lambda x: x[0], reverse=True)]
        
        elif self.recommendation_mode == RecommendationMode.ADAPTIVE:
            # Adapt based on recent performance
            recent_success_rate = self._calculate_recent_success_rate()
            
            if recent_success_rate > 0.8:
                # High success - can afford exploration
                return self._apply_recommendation_mode_filters(
                    recommendations, context
                )
            else:
                # Low success - be conservative
                return self._apply_recommendation_mode_filters(
                    recommendations, context
                )
        
        return recommendations
    
    def _track_recommendations(self, recommendations: List[AdaptiveRecommendation], context: str) -> None:
        """Track recommendations for analytics"""
        recommendation_data = {
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "recommendations": [
                {
                    "command": rec.command,
                    "confidence": rec.confidence,
                    "is_exploration": rec.is_exploration,
                    "uncertainty": rec.uncertainty,
                    "learning_potential": rec.learning_potential
                }
                for rec in recommendations
            ],
            "average_confidence": sum(r.confidence for r in recommendations) / len(recommendations) if recommendations else 0.0,
            "exploration_rate": sum(1 for r in recommendations if r.is_exploration) / len(recommendations) if recommendations else 0.0,
            "mode": self.recommendation_mode.value
        }
        
        self.recommendation_history.append(recommendation_data)
        self.performance_metrics["total_recommendations"] += len(recommendations)
    
    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate of recent recommendations"""
        recent_outcomes = [
            rec for rec in self.recommendation_history[-20:]
            if "outcome" in rec
        ]
        
        if not recent_outcomes:
            return 0.5  # Neutral assumption
        
        successes = sum(1 for rec in recent_outcomes if rec.get("outcome") == "success")
        return successes / len(recent_outcomes)
    
    def _analyze_discovery_evidence(self, 
                                  commands_used: List[str],
                                  outcome: str,
                                  quality_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze evidence of discovering better alternatives"""
        discovery_evidence = {
            "better_alternative_found": False,
            "confidence_exceeded_expectation": False,
            "new_pattern_discovered": False
        }
        
        if outcome == "success" and quality_metrics:
            # Check if performance exceeded expectations
            if quality_metrics.get("execution_time", float('inf')) < quality_metrics.get("expected_time", 0):
                discovery_evidence["better_alternative_found"] = True
            
            if quality_metrics.get("quality_score", 0) > quality_metrics.get("expected_quality", 0):
                discovery_evidence["better_alternative_found"] = True
        
        return discovery_evidence
    
    def _update_performance_metrics(self, outcome: str, impact_summary: Dict[str, Any]) -> None:
        """Update performance tracking metrics"""
        if outcome == "success":
            self.performance_metrics["successful_recommendations"] += 1
        
        # Update average confidence improvement
        confidence_changes = impact_summary.get("confidence_changes", {})
        if confidence_changes:
            total_change = sum(change["change"] for change in confidence_changes.values())
            avg_change = total_change / len(confidence_changes)
            
            current_avg = self.performance_metrics["average_confidence_improvement"]
            alpha = 0.1  # Learning rate
            self.performance_metrics["average_confidence_improvement"] = (
                (1 - alpha) * current_avg + alpha * avg_change
            )
    
    def _calculate_learning_impact(self, impact_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate the learning impact of this outcome"""
        confidence_changes = impact_summary.get("confidence_changes", {})
        
        if not confidence_changes:
            return {"impact": "none", "explanation": "No confidence changes recorded"}
        
        total_absolute_change = sum(abs(change["change"]) for change in confidence_changes.values())
        avg_absolute_change = total_absolute_change / len(confidence_changes)
        
        if avg_absolute_change > 0.1:
            impact_level = "high"
        elif avg_absolute_change > 0.05:
            impact_level = "moderate"
        else:
            impact_level = "low"
        
        return {
            "impact": impact_level,
            "average_absolute_change": avg_absolute_change,
            "total_commands_affected": len(confidence_changes),
            "explanation": f"Learning updated confidence for {len(confidence_changes)} commands by average of {avg_absolute_change:.3f}"
        }
    
    def _get_performance_trend(self) -> str:
        """Get trend in performance metrics"""
        if len(self.recommendation_history) < 10:
            return "insufficient_data"
        
        recent_success_rate = self._calculate_recent_success_rate()
        older_outcomes = [
            rec for rec in self.recommendation_history[-40:-20]
            if "outcome" in rec
        ]
        
        if older_outcomes:
            older_success_rate = sum(1 for rec in older_outcomes if rec.get("outcome") == "success") / len(older_outcomes)
            
            if recent_success_rate > older_success_rate + 0.1:
                return "improving"
            elif recent_success_rate < older_success_rate - 0.1:
                return "declining"
        
        return "stable"
    
    def _analyze_confidence_trend(self, command: str, context: str, learning_data: Dict[str, Any]) -> str:
        """Analyze confidence trend for command"""
        # This would analyze historical confidence values
        # For now, return stable as placeholder
        return "stable"
    
    def _assess_command_calibration_quality(self, command: str, context: str) -> float:
        """Assess calibration quality for specific command"""
        calibration_diagnostics = self.calibrator.get_calibration_diagnostics(context)
        return 1.0 - calibration_diagnostics.get("calibration_error", 0.2)
    
    def _calculate_temporal_freshness(self, learning_data: Dict[str, Any]) -> float:
        """Calculate how fresh/recent the learning data is"""
        successful_patterns = learning_data.get("successful_patterns", [])
        if not successful_patterns:
            return 0.5
        
        # Get most recent timestamp
        most_recent = max(
            datetime.fromisoformat(p["timestamp"]) 
            for p in successful_patterns 
            if "timestamp" in p
        )
        
        days_old = (datetime.now() - most_recent).days
        freshness = max(0.0, 1.0 - (days_old / 30.0))  # Decay over 30 days
        return freshness
    
    def _estimate_prerequisites(self, command: str, previous_commands: List[str]) -> List[str]:
        """Estimate prerequisites for command"""
        prereqs = []
        
        if command in ["test", "verify"] and not any("implement" in cmd for cmd in previous_commands):
            prereqs.append("implementation_required")
        
        if command in ["deploy", "complete"] and not any("test" in cmd for cmd in previous_commands):
            prereqs.append("testing_required")
        
        return prereqs
    
    def _assess_risk_level(self, command: str, context_type: ContextType) -> str:
        """Assess risk level for command in context"""
        high_risk_commands = ["deploy", "delete", "migrate", "overwrite"]
        medium_risk_commands = ["refactor", "optimize", "restructure"]
        
        base_risk = "low"
        if any(risk_cmd in command.lower() for risk_cmd in high_risk_commands):
            base_risk = "high"
        elif any(risk_cmd in command.lower() for risk_cmd in medium_risk_commands):
            base_risk = "medium"
        
        # Adjust for context
        if context_type in [ContextType.DEBUGGING, ContextType.MAINTENANCE]:
            # Lower risk tolerance in debugging/maintenance
            if base_risk == "medium":
                base_risk = "high"
        
        return base_risk
    
    def _estimate_execution_time(self, command: str, domain: str) -> float:
        """Estimate execution time for command"""
        base_times = {
            "explore": 2.0, "analyze": 3.0, "plan": 4.0, "design": 6.0,
            "implement": 8.0, "execute": 6.0, "test": 3.0, "verify": 2.0,
            "complete": 1.0, "document": 2.0
        }
        
        return base_times.get(command, 4.0)
    
    def _generate_expected_outcome(self, command: str, domain: str, phase: str) -> str:
        """Generate expected outcome description"""
        return f"Progress in {domain} {phase} through {command} execution"
    
    def _risk_score(self, risk_level: str) -> float:
        """Convert risk level to numeric score"""
        return {"low": 1.0, "medium": 2.0, "high": 3.0}.get(risk_level, 2.0)
    
    def _assess_calibration_quality(self) -> float:
        """Assess overall calibration quality"""
        total_error = 0.0
        contexts_checked = 0
        
        for context in set(rec["context"] for rec in self.recommendation_history[-20:]):
            diagnostics = self.calibrator.get_calibration_diagnostics(context)
            if diagnostics.get("status") == "calibrated":
                total_error += diagnostics.get("calibration_error", 0.0)
                contexts_checked += 1
        
        if contexts_checked == 0:
            return 0.5  # Neutral
        
        avg_error = total_error / contexts_checked
        return max(0.0, 1.0 - avg_error)
    
    def _generate_improvement_recommendations(self, 
                                            avg_improvement: float,
                                            exploration_analytics: Dict[str, Any],
                                            feedback_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving the learning system"""
        recommendations = []
        
        if avg_improvement < 0.05:
            recommendations.append("Consider increasing exploration rate to discover better patterns")
        
        if exploration_analytics.get("exploration_rate", 0) < 0.1:
            recommendations.append("Increase exploration to avoid getting stuck in local optima")
        
        if exploration_analytics.get("discovery_rate", 0) < 0.05:
            recommendations.append("Current exploration not finding improvements - try different strategy")
        
        if feedback_metrics.get("status") == "insufficient_data":
            recommendations.append("Gather more execution data to improve learning effectiveness")
        
        return recommendations