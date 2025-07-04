"""
Thompson Sampling Selector for Exploration-Exploitation Balance

Implements Thompson Sampling algorithm to balance between exploiting
high-confidence commands and exploring potentially better alternatives.
"""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .bayesian_confidence import (
    BayesianConfidenceCalculator, 
    ContextConfidenceModeler,
    ContextType
)


class ExplorationStrategy(Enum):
    """Different exploration strategies for Thompson Sampling"""
    PURE_THOMPSON = "pure_thompson"  # Pure Thompson sampling
    EPSILON_GREEDY = "epsilon_greedy"  # Epsilon-greedy with Thompson sampling
    UCB_THOMPSON = "ucb_thompson"  # Upper confidence bound with Thompson sampling
    ADAPTIVE_EXPLORATION = "adaptive"  # Adaptive exploration rate


@dataclass
class SamplingRecommendation:
    """Recommendation from Thompson Sampling with exploration metadata"""
    command: str
    sampled_confidence: float
    expected_confidence: float
    exploration_bonus: float
    is_exploration: bool  # True if this was an exploration choice
    uncertainty: float
    reasoning: str


class ThompsonSamplingSelector:
    """
    Thompson Sampling-based command selector that balances exploration and exploitation.
    
    Addresses the critical gap in ATLAS: the need to explore alternatives rather than
    always selecting the highest expected confidence command.
    """
    
    def __init__(self, 
                 confidence_engine: BayesianConfidenceCalculator,
                 context_modeler: Optional[ContextConfidenceModeler] = None,
                 exploration_strategy: ExplorationStrategy = ExplorationStrategy.PURE_THOMPSON,
                 exploration_rate: float = 0.1):
        """
        Initialize Thompson Sampling selector.
        
        Args:
            confidence_engine: Bayesian confidence calculator
            context_modeler: Context-specific confidence modeling
            exploration_strategy: Strategy for exploration-exploitation balance
            exploration_rate: Base exploration rate (for epsilon-greedy)
        """
        self.confidence_engine = confidence_engine
        self.context_modeler = context_modeler or ContextConfidenceModeler()
        self.exploration_strategy = exploration_strategy
        self.exploration_rate = exploration_rate
        
        # Tracking for adaptive exploration
        self.selection_history: List[Dict[str, Any]] = []
        self.exploration_count = 0
        self.exploitation_count = 0
        
        # Performance metrics
        self.metrics = {
            "total_selections": 0,
            "exploration_selections": 0,
            "exploitation_selections": 0,
            "average_confidence_improvement": 0.0,
            "discovery_rate": 0.0  # Rate of finding better alternatives
        }
    
    def select_command(self, 
                      candidates: List[str],
                      context: str,
                      learning_data: Dict[str, Any],
                      top_k: int = 3) -> List[SamplingRecommendation]:
        """
        Select commands using Thompson Sampling to balance exploration and exploitation.
        
        Args:
            candidates: List of candidate commands
            context: Context identifier
            learning_data: Historical learning data
            top_k: Number of recommendations to return
            
        Returns:
            List of Thompson sampling recommendations
        """
        recommendations = []
        
        # Get context type for appropriate confidence modeling
        context_type = self.context_modeler.classify_context_type(context)
        calculator = self.context_modeler.get_context_calculator(context_type)
        
        # Calculate expected and sampled confidence for each candidate
        candidate_scores = []
        for command in candidates:
            expected_conf = calculator.calculate_confidence(command, context, learning_data)
            uncertainty = calculator.get_confidence_uncertainty(command, context)
            
            # Sample confidence based on strategy
            sampled_conf, exploration_bonus, is_exploration = self._sample_confidence(
                command, context, expected_conf, uncertainty, calculator
            )
            
            candidate_scores.append({
                "command": command,
                "expected_confidence": expected_conf,
                "sampled_confidence": sampled_conf,
                "uncertainty": uncertainty,
                "exploration_bonus": exploration_bonus,
                "is_exploration": is_exploration
            })
        
        # Sort by sampled confidence (Thompson Sampling selection)
        candidate_scores.sort(key=lambda x: x["sampled_confidence"], reverse=True)
        
        # Create recommendations
        for i, score_data in enumerate(candidate_scores[:top_k]):
            reasoning = self._generate_selection_reasoning(
                score_data, i == 0, context_type
            )
            
            recommendation = SamplingRecommendation(
                command=score_data["command"],
                sampled_confidence=score_data["sampled_confidence"],
                expected_confidence=score_data["expected_confidence"],
                exploration_bonus=score_data["exploration_bonus"],
                is_exploration=score_data["is_exploration"],
                uncertainty=score_data["uncertainty"],
                reasoning=reasoning
            )
            
            recommendations.append(recommendation)
        
        # Track selection for adaptive exploration
        if recommendations:
            self._track_selection(recommendations[0], context, learning_data)
        
        return recommendations
    
    def update_exploration_rate(self, 
                               recent_success_rate: float,
                               discovery_evidence: Optional[Dict[str, Any]] = None) -> None:
        """
        Adaptively update exploration rate based on recent performance.
        
        Args:
            recent_success_rate: Success rate of recent selections
            discovery_evidence: Evidence of discovering better alternatives
        """
        if self.exploration_strategy != ExplorationStrategy.ADAPTIVE_EXPLORATION:
            return
        
        # Increase exploration if success rate is low (might be missing better options)
        if recent_success_rate < 0.6:
            self.exploration_rate = min(0.3, self.exploration_rate * 1.2)
        # Decrease exploration if success rate is high (current strategy working)
        elif recent_success_rate > 0.8:
            self.exploration_rate = max(0.05, self.exploration_rate * 0.9)
        
        # Increase exploration if we've discovered better alternatives recently
        if discovery_evidence and discovery_evidence.get("better_alternative_found"):
            self.exploration_rate = min(0.25, self.exploration_rate * 1.1)
    
    def get_exploration_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about exploration vs exploitation balance.
        
        Returns:
            Detailed analytics about selection patterns
        """
        total_selections = self.metrics["total_selections"]
        if total_selections == 0:
            return {"status": "no_selections"}
        
        exploration_rate = self.metrics["exploration_selections"] / total_selections
        exploitation_rate = self.metrics["exploitation_selections"] / total_selections
        
        # Calculate recent trends (last 20 selections)
        recent_selections = self.selection_history[-20:] if len(self.selection_history) >= 20 else self.selection_history
        recent_exploration_rate = (
            sum(1 for s in recent_selections if s["is_exploration"]) / len(recent_selections)
            if recent_selections else 0.0
        )
        
        # Calculate discovery effectiveness
        discoveries = sum(1 for s in self.selection_history if s.get("led_to_discovery", False))
        discovery_rate = discoveries / total_selections if total_selections > 0 else 0.0
        
        return {
            "status": "active",
            "total_selections": total_selections,
            "exploration_rate": exploration_rate,
            "exploitation_rate": exploitation_rate,
            "recent_exploration_rate": recent_exploration_rate,
            "discovery_rate": discovery_rate,
            "current_strategy": self.exploration_strategy.value,
            "adaptive_exploration_rate": self.exploration_rate,
            "balance_quality": self._assess_balance_quality(exploration_rate, discovery_rate),
            "recommendations": self._generate_balance_recommendations(exploration_rate, discovery_rate)
        }
    
    def _sample_confidence(self, 
                          command: str, 
                          context: str,
                          expected_confidence: float,
                          uncertainty: float,
                          calculator: BayesianConfidenceCalculator) -> Tuple[float, float, bool]:
        """
        Sample confidence value based on exploration strategy.
        
        Returns:
            (sampled_confidence, exploration_bonus, is_exploration)
        """
        if self.exploration_strategy == ExplorationStrategy.PURE_THOMPSON:
            # Pure Thompson sampling - sample from posterior distribution
            sampled_conf = calculator.sample_confidence(command, context, {})
            exploration_bonus = abs(sampled_conf - expected_confidence)
            is_exploration = sampled_conf > expected_confidence + 0.1
            
        elif self.exploration_strategy == ExplorationStrategy.EPSILON_GREEDY:
            # Epsilon-greedy with Thompson sampling for exploration
            if random.random() < self.exploration_rate:
                # Explore: sample from distribution
                sampled_conf = calculator.sample_confidence(command, context, {})
                exploration_bonus = 0.2  # Fixed exploration bonus
                is_exploration = True
            else:
                # Exploit: use expected value
                sampled_conf = expected_confidence
                exploration_bonus = 0.0
                is_exploration = False
                
        elif self.exploration_strategy == ExplorationStrategy.UCB_THOMPSON:
            # Upper confidence bound with Thompson sampling
            ucb_bonus = uncertainty * 1.96  # 95% confidence interval
            sampled_conf = calculator.sample_confidence(command, context, {})
            sampled_conf = max(sampled_conf, expected_confidence + ucb_bonus)
            exploration_bonus = ucb_bonus
            is_exploration = sampled_conf > expected_confidence + 0.05
            
        elif self.exploration_strategy == ExplorationStrategy.ADAPTIVE_EXPLORATION:
            # Adaptive exploration based on context and uncertainty
            adaptive_rate = self.exploration_rate * (1 + uncertainty)
            if random.random() < adaptive_rate:
                sampled_conf = calculator.sample_confidence(command, context, {})
                exploration_bonus = uncertainty * 0.3
                is_exploration = True
            else:
                sampled_conf = expected_confidence
                exploration_bonus = 0.0
                is_exploration = False
        
        else:
            # Fallback to expected confidence
            sampled_conf = expected_confidence
            exploration_bonus = 0.0
            is_exploration = False
        
        return sampled_conf, exploration_bonus, is_exploration
    
    def _generate_selection_reasoning(self, 
                                    score_data: Dict[str, Any],
                                    is_top_choice: bool,
                                    context_type: ContextType) -> str:
        """Generate explanation for why command was selected"""
        command = score_data["command"]
        expected = score_data["expected_confidence"]
        sampled = score_data["sampled_confidence"]
        uncertainty = score_data["uncertainty"]
        is_exploration = score_data["is_exploration"]
        
        reasoning_parts = []
        
        if is_top_choice:
            reasoning_parts.append("Selected as top choice by Thompson Sampling")
        
        if is_exploration:
            reasoning_parts.append(f"Exploration selection (uncertainty: {uncertainty:.2f})")
            if sampled > expected + 0.1:
                reasoning_parts.append("High sampling variance suggests potential for better performance")
        else:
            reasoning_parts.append(f"Exploitation selection (expected confidence: {expected:.2f})")
        
        # Add context-specific reasoning
        risk_tolerance = {
            ContextType.DEBUGGING: "low",
            ContextType.REFACTORING: "low", 
            ContextType.OPTIMIZATION: "medium",
            ContextType.GREENFIELD: "medium",
            ContextType.MAINTENANCE: "low"
        }.get(context_type, "medium")
        
        if is_exploration and risk_tolerance == "low":
            reasoning_parts.append("Careful exploration due to low-risk context")
        elif is_exploration and risk_tolerance == "medium":
            reasoning_parts.append("Moderate exploration appropriate for context")
        
        return "; ".join(reasoning_parts)
    
    def _track_selection(self, 
                        recommendation: SamplingRecommendation,
                        context: str,
                        learning_data: Dict[str, Any]) -> None:
        """Track selection for analytics and adaptive exploration"""
        selection_record = {
            "command": recommendation.command,
            "context": context,
            "sampled_confidence": recommendation.sampled_confidence,
            "expected_confidence": recommendation.expected_confidence,
            "is_exploration": recommendation.is_exploration,
            "uncertainty": recommendation.uncertainty,
            "timestamp": datetime.now().isoformat(),
            "strategy": self.exploration_strategy.value
        }
        
        self.selection_history.append(selection_record)
        
        # Update metrics
        self.metrics["total_selections"] += 1
        if recommendation.is_exploration:
            self.metrics["exploration_selections"] += 1
        else:
            self.metrics["exploitation_selections"] += 1
    
    def _assess_balance_quality(self, exploration_rate: float, discovery_rate: float) -> str:
        """Assess quality of exploration-exploitation balance"""
        if exploration_rate < 0.05:
            return "too_little_exploration"
        elif exploration_rate > 0.4:
            return "too_much_exploration"
        elif discovery_rate > 0.1:
            return "effective_exploration"
        elif discovery_rate < 0.02 and exploration_rate > 0.15:
            return "ineffective_exploration"
        else:
            return "balanced"
    
    def _generate_balance_recommendations(self, 
                                        exploration_rate: float, 
                                        discovery_rate: float) -> List[str]:
        """Generate recommendations for improving exploration-exploitation balance"""
        recommendations = []
        
        if exploration_rate < 0.05:
            recommendations.append("Increase exploration rate - may be missing better alternatives")
        elif exploration_rate > 0.4:
            recommendations.append("Decrease exploration rate - too much random selection")
        
        if discovery_rate < 0.02 and exploration_rate > 0.15:
            recommendations.append("Exploration not finding improvements - consider different strategy")
        
        if discovery_rate > 0.15:
            recommendations.append("High discovery rate - continue current exploration strategy")
        
        return recommendations


class MultiArmedBanditSelector:
    """
    Alternative selector using classic multi-armed bandit algorithms.
    
    Provides different approach to exploration-exploitation that can be
    compared with Thompson Sampling for effectiveness.
    """
    
    def __init__(self, 
                 confidence_engine: BayesianConfidenceCalculator,
                 algorithm: str = "ucb1",
                 exploration_parameter: float = 2.0):
        """
        Initialize multi-armed bandit selector.
        
        Args:
            confidence_engine: Bayesian confidence calculator
            algorithm: 'ucb1', 'epsilon_greedy', or 'exp3'
            exploration_parameter: Algorithm-specific exploration parameter
        """
        self.confidence_engine = confidence_engine
        self.algorithm = algorithm
        self.exploration_parameter = exploration_parameter
        
        # Track arm (command) statistics
        self.arm_counts: Dict[str, int] = {}
        self.arm_rewards: Dict[str, float] = {}
        self.total_selections = 0
    
    def select_command(self, 
                      candidates: List[str],
                      context: str) -> str:
        """
        Select command using multi-armed bandit algorithm.
        
        Args:
            candidates: Available command candidates
            context: Current context
            
        Returns:
            Selected command
        """
        if self.algorithm == "ucb1":
            return self._select_ucb1(candidates, context)
        elif self.algorithm == "epsilon_greedy":
            return self._select_epsilon_greedy(candidates, context)
        elif self.algorithm == "exp3":
            return self._select_exp3(candidates, context)
        else:
            # Fallback to highest confidence
            confidences = {
                cmd: self.confidence_engine.calculate_confidence(cmd, context, {})
                for cmd in candidates
            }
            return max(confidences, key=confidences.get)
    
    def update_reward(self, command: str, reward: float) -> None:
        """Update reward for selected command"""
        if command not in self.arm_rewards:
            self.arm_rewards[command] = 0.0
            self.arm_counts[command] = 0
        
        # Update using incremental average
        self.arm_counts[command] += 1
        n = self.arm_counts[command]
        self.arm_rewards[command] += (reward - self.arm_rewards[command]) / n
    
    def _select_ucb1(self, candidates: List[str], context: str) -> str:
        """Upper Confidence Bound selection"""
        if self.total_selections == 0:
            return random.choice(candidates)
        
        ucb_values = {}
        for cmd in candidates:
            if cmd not in self.arm_counts or self.arm_counts[cmd] == 0:
                # Select unselected arms first
                return cmd
            
            avg_reward = self.arm_rewards[cmd]
            confidence_bonus = self.exploration_parameter * (
                (2 * random.random()) / self.arm_counts[cmd]  # Simplified UCB
            ) ** 0.5
            
            ucb_values[cmd] = avg_reward + confidence_bonus
        
        return max(ucb_values, key=ucb_values.get)
    
    def _select_epsilon_greedy(self, candidates: List[str], context: str) -> str:
        """Epsilon-greedy selection"""
        if random.random() < self.exploration_parameter:
            # Explore: random selection
            return random.choice(candidates)
        else:
            # Exploit: best known arm
            if not self.arm_rewards:
                return random.choice(candidates)
            
            available_rewards = {
                cmd: self.arm_rewards.get(cmd, 0.0) 
                for cmd in candidates
            }
            return max(available_rewards, key=available_rewards.get)
    
    def _select_exp3(self, candidates: List[str], context: str) -> str:
        """EXP3 (Exponential-weight algorithm) selection"""
        # Simplified EXP3 implementation
        if not self.arm_rewards:
            return random.choice(candidates)
        
        # Calculate weights
        weights = {}
        for cmd in candidates:
            reward = self.arm_rewards.get(cmd, 0.0)
            weights[cmd] = (1 + self.exploration_parameter * reward) ** self.exploration_parameter
        
        # Probability distribution
        total_weight = sum(weights.values())
        if total_weight == 0:
            return random.choice(candidates)
        
        probabilities = {cmd: w / total_weight for cmd, w in weights.items()}
        
        # Sample from distribution
        rand_val = random.random()
        cumulative = 0.0
        for cmd, prob in probabilities.items():
            cumulative += prob
            if rand_val <= cumulative:
                return cmd
        
        return candidates[-1]  # Fallback