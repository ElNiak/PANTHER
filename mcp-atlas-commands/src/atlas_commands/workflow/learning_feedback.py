"""
Learning Feedback Loop for Adaptive Command Selection

Connects learning outcomes to confidence updates, closing the gap
between pattern storage and recommendation improvement.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict
import json

from .bayesian_confidence import (
    BayesianConfidenceCalculator, 
    ContextConfidenceModeler,
    TemporalConfidenceDecay,
    ConfidenceCalibrator,
    ContextType
)


@dataclass
class LearningOutcome:
    """Represents a learning outcome from command execution"""
    commands_used: List[str]
    context: str
    outcome: str  # 'success', 'failure', 'partial'
    execution_time: Optional[float]
    timestamp: datetime
    notes: Optional[str]
    confidence_before: Optional[float] = None
    confidence_after: Optional[float] = None


class LearningFeedbackLoop:
    """
    Connects learn_from_outcome() to confidence updates.
    
    This class closes the critical gap identified in the root cause analysis:
    learning data was stored but never applied to confidence calculation.
    """
    
    def __init__(self, confidence_engine: BayesianConfidenceCalculator,
                 context_modeler: Optional[ContextConfidenceModeler] = None,
                 temporal_decay: Optional[TemporalConfidenceDecay] = None,
                 calibrator: Optional[ConfidenceCalibrator] = None):
        """
        Initialize learning feedback loop.
        
        Args:
            confidence_engine: Bayesian confidence calculator
            context_modeler: Context-specific confidence modeling
            temporal_decay: Time-based confidence decay
            calibrator: Confidence calibration system
        """
        self.confidence_engine = confidence_engine
        self.context_modeler = context_modeler or ContextConfidenceModeler()
        self.temporal_decay = temporal_decay or TemporalConfidenceDecay()
        self.calibrator = calibrator or ConfidenceCalibrator()
        
        # Learning tracking
        self.learning_history: List[LearningOutcome] = []
        self.learning_buffer: List[LearningOutcome] = []
        self.batch_size = 5  # Process updates in batches
        
        # Performance metrics
        self.metrics = {
            "total_outcomes_processed": 0,
            "successful_outcomes": 0,
            "failed_outcomes": 0,
            "average_confidence_improvement": 0.0,
            "learning_velocity": 0.0
        }
    
    def process_outcome(self, commands_used: List[str], context_dict: Dict[str, Any],
                       outcome: str, execution_time: Optional[float] = None,
                       notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Process execution outcome and update confidence immediately.
        
        This is the main entry point that replaces the static learning storage
        with dynamic confidence updates.
        
        Args:
            commands_used: Commands that were executed
            context_dict: Context information (domain, complexity, phase, etc.)
            outcome: 'success', 'failure', or 'partial'
            execution_time: Time taken for execution
            notes: Additional notes about the outcome
            
        Returns:
            Learning impact summary with confidence changes
        """
        timestamp = datetime.now()
        
        # Create context identifier
        context = self._create_context_identifier(context_dict)
        
        # Classify context type first to get the right calculator
        context_type = self.context_modeler.classify_context_type(context)
        context_calculator = self.context_modeler.get_context_calculator(context_type)
        
        # Get confidence before update for comparison using the SAME calculator
        confidence_before = {}
        for command in commands_used:
            try:
                confidence_before[command] = context_calculator.calculate_confidence(
                    command, context, {}
                )
            except Exception:
                confidence_before[command] = 0.5  # Default if calculation fails
        
        # Create learning outcome record
        learning_outcome = LearningOutcome(
            commands_used=commands_used,
            context=context,
            outcome=outcome,
            execution_time=execution_time,
            timestamp=timestamp,
            notes=notes,
            confidence_before=confidence_before
        )
        
        # Update confidence distributions immediately using the same calculator
        impact_summary = self._update_confidence_distributions(learning_outcome, context_calculator)
        
        # Store for batch processing and analytics
        self.learning_history.append(learning_outcome)
        self.learning_buffer.append(learning_outcome)
        
        # Process batch updates if buffer is full
        if len(self.learning_buffer) >= self.batch_size:
            self._process_batch_updates()
        
        # Update metrics
        self._update_metrics(learning_outcome, impact_summary)
        
        return impact_summary
    
    def _update_confidence_distributions(self, outcome: LearningOutcome, context_calculator=None) -> Dict[str, Any]:
        """
        Update Bayesian confidence distributions based on outcome.
        
        This is where the actual learning → application happens.
        """
        impact_summary = {
            "commands_affected": len(outcome.commands_used),
            "confidence_changes": {},
            "learning_impact": outcome.outcome,
            "timestamp": outcome.timestamp.isoformat()
        }
        
        # Use provided calculator or get context-specific one
        if context_calculator is None:
            context_type = self.context_modeler.classify_context_type(outcome.context)
            context_calculator = self.context_modeler.get_context_calculator(context_type)
        
        for command in outcome.commands_used:
            # Get confidence before update
            confidence_before = outcome.confidence_before.get(command, 0.5)
            
            # Update distribution based on outcome
            context_calculator.update_from_outcome(
                command=command,
                context=outcome.context,
                outcome=outcome.outcome,
                timestamp=outcome.timestamp
            )
            
            # Calculate confidence after update
            confidence_after = context_calculator.calculate_confidence(
                command, outcome.context, {}
            )
            
            # Track confidence change
            confidence_change = confidence_after - confidence_before
            impact_summary["confidence_changes"][command] = {
                "before": confidence_before,
                "after": confidence_after,
                "change": confidence_change,
                "relative_change": confidence_change / confidence_before if confidence_before > 0 else 0
            }
            
            # Update calibration data
            predicted_success = confidence_before > 0.5
            actual_success = outcome.outcome == "success"
            self.calibrator.update_calibration_data(
                context=outcome.context,
                predicted_confidence=confidence_before,
                actual_outcome=actual_success
            )
        
        return impact_summary
    
    def _process_batch_updates(self) -> None:
        """Process batched updates for performance optimization"""
        if not self.learning_buffer:
            return
        
        # Group outcomes by context for batch processing
        context_groups = defaultdict(list)
        for outcome in self.learning_buffer:
            context_groups[outcome.context].append(outcome)
        
        # Process context-specific optimizations
        for context, outcomes in context_groups.items():
            self._optimize_context_confidence(context, outcomes)
        
        # Clear buffer
        self.learning_buffer.clear()
    
    def _optimize_context_confidence(self, context: str, outcomes: List[LearningOutcome]) -> None:
        """Optimize confidence models for specific context based on recent outcomes"""
        # Analyze patterns in recent outcomes
        success_rate = sum(1 for o in outcomes if o.outcome == "success") / len(outcomes)
        
        # Adjust confidence modeling based on observed patterns
        if success_rate > 0.8:
            # High success rate: slightly increase prior optimism
            pass  # Could implement adaptive prior adjustment
        elif success_rate < 0.3:
            # Low success rate: increase prior pessimism
            pass  # Could implement adaptive prior adjustment
    
    def get_learning_effectiveness_metrics(self) -> Dict[str, Any]:
        """
        Calculate metrics about learning effectiveness.
        
        This addresses the key requirement: measure actual improvement
        rather than just pattern storage.
        """
        if len(self.learning_history) < 5:
            return {
                "status": "insufficient_data",
                "total_outcomes": len(self.learning_history)
            }
        
        recent_outcomes = self.learning_history[-20:]  # Last 20 outcomes
        
        # Calculate confidence improvement trends
        confidence_improvements = []
        for outcome in recent_outcomes:
            if outcome.confidence_before and outcome.confidence_after:
                for command, changes in outcome.confidence_after.items():
                    if command in outcome.confidence_before:
                        improvement = changes - outcome.confidence_before[command]
                        confidence_improvements.append(improvement)
        
        avg_improvement = (sum(confidence_improvements) / len(confidence_improvements) 
                          if confidence_improvements else 0.0)
        
        # Calculate learning velocity
        recent_successes = sum(1 for o in recent_outcomes if o.outcome == "success")
        success_rate = recent_successes / len(recent_outcomes)
        
        # Calculate exploration vs exploitation balance
        high_confidence_decisions = sum(
            1 for o in recent_outcomes 
            if any(conf > 0.8 for conf in (o.confidence_before or {}).values())
        )
        exploration_rate = 1.0 - (high_confidence_decisions / len(recent_outcomes))
        
        return {
            "status": "active_learning",
            "total_outcomes": len(self.learning_history),
            "recent_outcomes": len(recent_outcomes),
            "average_confidence_improvement": avg_improvement,
            "success_rate": success_rate,
            "exploration_rate": exploration_rate,
            "learning_velocity": avg_improvement * success_rate,  # Combined metric
            "improvement_trend": "positive" if avg_improvement > 0.05 else "stable" if avg_improvement > -0.05 else "negative"
        }
    
    def get_command_learning_analysis(self, command: str, context: str) -> Dict[str, Any]:
        """
        Analyze learning patterns for specific command in context.
        
        Args:
            command: Command to analyze
            context: Context to analyze
            
        Returns:
            Detailed learning analysis
        """
        # Filter outcomes for this command/context
        relevant_outcomes = [
            o for o in self.learning_history 
            if command in o.commands_used and o.context == context
        ]
        
        if not relevant_outcomes:
            return {
                "status": "no_data",
                "command": command,
                "context": context
            }
        
        # Calculate statistics
        total_uses = len(relevant_outcomes)
        successes = sum(1 for o in relevant_outcomes if o.outcome == "success")
        success_rate = successes / total_uses
        
        # Get current confidence
        context_type = self.context_modeler.classify_context_type(context)
        calculator = self.context_modeler.get_context_calculator(context_type)
        current_confidence = calculator.calculate_confidence(command, context, {})
        
        # Calculate confidence trend
        confidence_trend = []
        for outcome in relevant_outcomes[-10:]:  # Last 10 uses
            if outcome.confidence_after and command in outcome.confidence_after:
                confidence_trend.append(outcome.confidence_after[command])
        
        trend_direction = "stable"
        if len(confidence_trend) >= 3:
            recent_avg = sum(confidence_trend[-3:]) / 3
            older_avg = sum(confidence_trend[:3]) / 3
            if recent_avg > older_avg + 0.05:
                trend_direction = "improving"
            elif recent_avg < older_avg - 0.05:
                trend_direction = "declining"
        
        # Get uncertainty level
        uncertainty = calculator.get_confidence_uncertainty(command, context)
        
        return {
            "status": "analyzed",
            "command": command,
            "context": context,
            "total_uses": total_uses,
            "success_rate": success_rate,
            "current_confidence": current_confidence,
            "uncertainty": uncertainty,
            "trend_direction": trend_direction,
            "needs_exploration": uncertainty > 0.7,
            "confidence_stable": trend_direction == "stable" and uncertainty < 0.3,
            "last_used": relevant_outcomes[-1].timestamp.isoformat() if relevant_outcomes else None
        }
    
    def _create_context_identifier(self, context_dict: Dict[str, Any]) -> str:
        """Create standardized context identifier from context dictionary"""
        domain = context_dict.get('domain', 'unknown')
        complexity = context_dict.get('complexity', 'unknown') 
        phase = context_dict.get('current_phase', 'unknown')
        
        return f"{domain}_{complexity}_{phase}"
    
    def _update_metrics(self, outcome: LearningOutcome, impact_summary: Dict[str, Any]) -> None:
        """Update internal metrics tracking"""
        self.metrics["total_outcomes_processed"] += 1
        
        if outcome.outcome == "success":
            self.metrics["successful_outcomes"] += 1
        else:
            self.metrics["failed_outcomes"] += 1
        
        # Update average confidence improvement
        confidence_changes = impact_summary.get("confidence_changes", {})
        if confidence_changes:
            total_change = sum(change["change"] for change in confidence_changes.values())
            avg_change = total_change / len(confidence_changes)
            
            # Exponential moving average
            alpha = 0.1
            current_avg = self.metrics["average_confidence_improvement"]
            self.metrics["average_confidence_improvement"] = (
                (1 - alpha) * current_avg + alpha * avg_change
            )
        
        # Update learning velocity
        success_rate = (self.metrics["successful_outcomes"] / 
                       self.metrics["total_outcomes_processed"])
        self.metrics["learning_velocity"] = (
            self.metrics["average_confidence_improvement"] * success_rate
        )


class IncrementalConfidenceUpdater:
    """
    Real-time confidence adjustment as new outcomes arrive.
    
    Optimizes performance by batching updates and using incremental
    algorithms for large-scale learning.
    """
    
    def __init__(self, update_interval: int = 5, max_buffer_size: int = 100):
        """
        Initialize incremental updater.
        
        Args:
            update_interval: Process updates every N outcomes
            max_buffer_size: Maximum buffer size before forced processing
        """
        self.update_interval = update_interval
        self.max_buffer_size = max_buffer_size
        self.pending_updates: Dict[str, List[str]] = defaultdict(list)
        self.update_count = 0
    
    def queue_confidence_update(self, command: str, context: str, outcome: str) -> None:
        """
        Queue confidence update for batch processing.
        
        Args:
            command: Command name
            context: Context identifier
            outcome: Outcome result
        """
        key = f"{command}_{context}"
        self.pending_updates[key].append(outcome)
        self.update_count += 1
        
        # Process if buffer is full or interval reached
        if (self.update_count >= self.update_interval or 
            len(self.pending_updates) >= self.max_buffer_size):
            self.process_pending_updates()
    
    def process_pending_updates(self) -> Dict[str, Any]:
        """
        Process all pending updates using incremental algorithms.
        
        Returns:
            Summary of processing results
        """
        if not self.pending_updates:
            return {"status": "no_updates"}
        
        processed_count = 0
        updates_summary = {}
        
        for key, outcomes in self.pending_updates.items():
            # Process incremental updates for this command-context pair
            successes = sum(1 for outcome in outcomes if outcome == "success")
            failures = len(outcomes) - successes
            
            updates_summary[key] = {
                "successes": successes,
                "failures": failures,
                "total": len(outcomes)
            }
            
            processed_count += len(outcomes)
        
        # Clear processed updates
        self.pending_updates.clear()
        self.update_count = 0
        
        return {
            "status": "processed",
            "total_updates": processed_count,
            "command_contexts_updated": len(updates_summary),
            "updates_summary": updates_summary
        }
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status for monitoring"""
        total_pending = sum(len(outcomes) for outcomes in self.pending_updates.values())
        
        return {
            "pending_updates": total_pending,
            "pending_contexts": len(self.pending_updates),
            "update_count": self.update_count,
            "buffer_utilization": total_pending / self.max_buffer_size,
            "next_processing_threshold": self.update_interval - self.update_count
        }