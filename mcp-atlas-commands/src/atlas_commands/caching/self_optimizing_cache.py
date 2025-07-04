"""
Self-Optimizing Cache System
Phase 4 implementation for automatic cache optimization using ML insights
Automatically applies optimization strategies based on real-time analysis
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

from .hierarchical_cache_manager import HierarchicalCacheManager
from .content_hash_validator import ContentHashValidator
from .language_aware_cache import LanguageAwareSymbolCache, LanguageType
from .performance_analytics import CachePerformanceDashboard
from .anomaly_detection import AnomalyDetectionOrchestrator, AnomalyDetectionConfig
from .predictive_analytics import PredictiveAnalyticsOrchestrator
from .global_optimization import GlobalCacheOptimizer, OptimizationStrategy, OptimizationResult


@dataclass
class AutoOptimizationConfig:
    """Configuration for automatic optimization"""
    enabled: bool = True
    optimization_interval_minutes: int = 60
    min_performance_threshold: float = 0.7
    max_optimization_frequency: int = 3  # Per day
    confidence_threshold: float = 0.8
    enable_predictive_optimization: bool = True
    enable_anomaly_triggered_optimization: bool = True
    enable_performance_monitoring: bool = True
    auto_apply_low_risk_strategies: bool = True
    require_approval_for_high_risk: bool = True
    rollback_on_performance_degradation: bool = True


@dataclass
class OptimizationDecision:
    """Decision made by the self-optimizing system"""
    decision_id: str
    trigger_type: str  # 'scheduled', 'anomaly', 'prediction', 'manual'
    trigger_data: Dict[str, Any]
    strategy_selected: str
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    auto_applied: bool
    approval_required: bool
    decision_timestamp: float
    reasoning: List[str]
    expected_benefits: Dict[str, float]


@dataclass
class OptimizationExecution:
    """Execution of an optimization decision"""
    execution_id: str
    decision_id: str
    strategy_id: str
    started_at: float
    completed_at: Optional[float]
    status: str  # 'pending', 'running', 'completed', 'failed', 'rolled_back'
    performance_before: Dict[str, float]
    performance_after: Optional[Dict[str, float]]
    actual_benefits: Optional[Dict[str, float]]
    execution_logs: List[str]
    rollback_reason: Optional[str]


class AutoOptimizationDecisionEngine:
    """Makes intelligent decisions about when and how to optimize"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 anomaly_detector: AnomalyDetectionOrchestrator,
                 predictive_analytics: PredictiveAnalyticsOrchestrator,
                 global_optimizer: GlobalCacheOptimizer,
                 config: AutoOptimizationConfig):
        
        self.cache_manager = cache_manager
        self.anomaly_detector = anomaly_detector
        self.predictive_analytics = predictive_analytics
        self.global_optimizer = global_optimizer
        self.config = config
        
        self.decisions_cache_type = "optimization_decisions"
        self.executions_cache_type = "optimization_executions"
        self._lock = threading.Lock()
        
        # Decision history
        self.recent_decisions = deque(maxlen=100)
        self.execution_history = deque(maxlen=100)
    
    def evaluate_optimization_need(self, trigger_type: str = "scheduled",
                                  trigger_data: Dict[str, Any] = None) -> Optional[OptimizationDecision]:
        """Evaluate whether optimization is needed"""
        
        # Check if optimization is enabled
        if not self.config.enabled:
            return None
        
        # Check optimization frequency limits
        if not self._check_optimization_frequency():
            return None
        
        # Analyze current system state
        system_state = self._analyze_system_state()
        
        # Determine optimization need based on trigger type
        if trigger_type == "scheduled":
            decision = self._evaluate_scheduled_optimization(system_state)
        elif trigger_type == "anomaly":
            decision = self._evaluate_anomaly_triggered_optimization(system_state, trigger_data)
        elif trigger_type == "prediction":
            decision = self._evaluate_prediction_triggered_optimization(system_state, trigger_data)
        else:
            decision = None
        
        if decision:
            self.recent_decisions.append(decision)
            self._store_decision(decision)
        
        return decision
    
    def select_optimization_strategy(self, system_state: Dict[str, Any],
                                   trigger_data: Dict[str, Any] = None) -> Optional[OptimizationStrategy]:
        """Select the best optimization strategy"""
        
        # Get available strategies
        available_strategies = self.global_optimizer.generate_optimization_strategies()
        
        if not available_strategies:
            return None
        
        # Score strategies based on current context
        scored_strategies = []
        for strategy in available_strategies:
            score = self._score_strategy(strategy, system_state, trigger_data)
            scored_strategies.append((strategy, score))
        
        # Sort by score and select best
        scored_strategies.sort(key=lambda x: x[1], reverse=True)
        
        # Check if best strategy meets confidence threshold
        best_strategy, best_score = scored_strategies[0]
        
        if best_score >= self.config.confidence_threshold:
            return best_strategy
        
        return None
    
    def _analyze_system_state(self) -> Dict[str, Any]:
        """Analyze current system state for optimization decisions"""
        
        # Get performance metrics
        performance_stats = self.cache_manager.get_performance_stats()
        
        # Get cache size info
        cache_size_info = self.cache_manager.get_cache_size_info()
        
        # Run anomaly detection
        anomaly_results = self.anomaly_detector.run_comprehensive_anomaly_detection()
        
        # Get predictive insights
        prediction_results = self.predictive_analytics.run_comprehensive_prediction_analysis()
        
        # Analyze global cache state
        global_state = self.global_optimizer.analyze_global_cache_state()
        
        return {
            "performance_stats": performance_stats,
            "cache_size_info": cache_size_info,
            "anomaly_results": anomaly_results,
            "prediction_results": prediction_results,
            "global_state": global_state,
            "timestamp": time.time()
        }
    
    def _evaluate_scheduled_optimization(self, system_state: Dict[str, Any]) -> Optional[OptimizationDecision]:
        """Evaluate need for scheduled optimization"""
        
        performance_stats = system_state["performance_stats"]
        global_state = system_state["global_state"]
        
        # Check performance thresholds
        hit_rate = performance_stats.get("hit_rate_percent", 0)
        optimization_score = global_state.get("optimization_score", 100)
        
        reasons = []
        confidence = 0.0
        
        # Performance-based triggers
        if hit_rate < 60:
            reasons.append(f"Low cache hit rate: {hit_rate:.1f}%")
            confidence += 0.3
        
        if optimization_score < 70:
            reasons.append(f"Low optimization score: {optimization_score:.1f}")
            confidence += 0.4
        
        # Resource utilization triggers
        cache_size = system_state["cache_size_info"].get("total_cache_mb", 0)
        if cache_size > 800:  # High cache usage
            reasons.append(f"High cache usage: {cache_size:.1f}MB")
            confidence += 0.2
        
        # Check if optimization is warranted
        if confidence >= self.config.confidence_threshold and reasons:
            strategy = self.select_optimization_strategy(system_state)
            
            if strategy:
                return OptimizationDecision(
                    decision_id=f"scheduled_{int(time.time())}",
                    trigger_type="scheduled",
                    trigger_data=system_state,
                    strategy_selected=strategy.strategy_id,
                    confidence=confidence,
                    risk_level=self._assess_strategy_risk(strategy),
                    auto_applied=self._should_auto_apply(strategy),
                    approval_required=self._requires_approval(strategy),
                    decision_timestamp=time.time(),
                    reasoning=reasons,
                    expected_benefits=strategy.estimated_improvement
                )
        
        return None
    
    def _evaluate_anomaly_triggered_optimization(self, system_state: Dict[str, Any],
                                               trigger_data: Dict[str, Any]) -> Optional[OptimizationDecision]:
        """Evaluate need for anomaly-triggered optimization"""
        
        if not self.config.enable_anomaly_triggered_optimization:
            return None
        
        anomaly_results = system_state["anomaly_results"]
        
        # Check for critical anomalies
        critical_anomalies = [
            a for a in anomaly_results.get("performance_anomalies", [])
            if a.get("severity") in ["critical", "high"]
        ]
        
        if not critical_anomalies:
            return None
        
        # Analyze anomaly patterns
        anomaly_types = Counter(a.get("anomaly_type") for a in critical_anomalies)
        primary_issue = anomaly_types.most_common(1)[0][0]
        
        reasons = [f"Critical {primary_issue} anomaly detected"]
        confidence = 0.8  # High confidence for anomaly response
        
        # Select strategy based on anomaly type
        strategy = self._select_anomaly_response_strategy(primary_issue, critical_anomalies)
        
        if strategy:
            return OptimizationDecision(
                decision_id=f"anomaly_{int(time.time())}",
                trigger_type="anomaly",
                trigger_data={"anomalies": critical_anomalies},
                strategy_selected=strategy.strategy_id,
                confidence=confidence,
                risk_level="high",  # Anomaly responses are typically higher risk
                auto_applied=False,  # Always require approval for anomaly responses
                approval_required=True,
                decision_timestamp=time.time(),
                reasoning=reasons,
                expected_benefits=strategy.estimated_improvement
            )
        
        return None
    
    def _evaluate_prediction_triggered_optimization(self, system_state: Dict[str, Any],
                                                  trigger_data: Dict[str, Any]) -> Optional[OptimizationDecision]:
        """Evaluate need for prediction-triggered optimization"""
        
        if not self.config.enable_predictive_optimization:
            return None
        
        prediction_results = system_state["prediction_results"]
        insights = prediction_results.get("predictive_insights", [])
        
        # Look for high-confidence negative predictions
        concerning_insights = [
            insight for insight in insights
            if insight.get("confidence", 0) > 0.7 and
               insight.get("insight_type") in ["performance_degradation", "cache_overflow"]
        ]
        
        if not concerning_insights:
            return None
        
        # Select most critical insight
        primary_insight = max(concerning_insights, key=lambda x: x.get("confidence", 0))
        
        reasons = [f"Predictive insight: {primary_insight.get('insight_type')}"]
        confidence = primary_insight.get("confidence", 0)
        
        # Select preventive strategy
        strategy = self._select_preventive_strategy(primary_insight)
        
        if strategy:
            return OptimizationDecision(
                decision_id=f"prediction_{int(time.time())}",
                trigger_type="prediction",
                trigger_data={"insight": primary_insight},
                strategy_selected=strategy.strategy_id,
                confidence=confidence,
                risk_level="medium",  # Preventive measures are medium risk
                auto_applied=self._should_auto_apply(strategy),
                approval_required=self._requires_approval(strategy),
                decision_timestamp=time.time(),
                reasoning=reasons,
                expected_benefits=strategy.estimated_improvement
            )
        
        return None
    
    def _score_strategy(self, strategy: OptimizationStrategy, system_state: Dict[str, Any],
                       trigger_data: Dict[str, Any] = None) -> float:
        """Score an optimization strategy for current context"""
        
        score = 0.0
        
        # Base score from estimated improvement
        improvement_score = sum(strategy.estimated_improvement.values()) / 100.0
        score += improvement_score * 0.4
        
        # Priority score
        priority_scores = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
        score += priority_scores.get(strategy.priority, 0.5) * 0.3
        
        # Complexity penalty
        complexity_penalties = {"simple": 0.0, "moderate": 0.1, "complex": 0.2}
        score -= complexity_penalties.get(strategy.complexity, 0.1) * 0.2
        
        # Context relevance
        context_score = self._calculate_context_relevance(strategy, system_state)
        score += context_score * 0.1
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_context_relevance(self, strategy: OptimizationStrategy,
                                   system_state: Dict[str, Any]) -> float:
        """Calculate how relevant a strategy is to current context"""
        
        relevance = 0.5  # Base relevance
        
        # Match strategy type to current issues
        performance_stats = system_state["performance_stats"]
        
        if strategy.strategy_type == "performance":
            hit_rate = performance_stats.get("hit_rate_percent", 80)
            if hit_rate < 60:
                relevance += 0.3
        
        elif strategy.strategy_type == "storage":
            cache_size = system_state["cache_size_info"].get("total_cache_mb", 0)
            if cache_size > 500:
                relevance += 0.3
        
        return min(relevance, 1.0)
    
    def _assess_strategy_risk(self, strategy: OptimizationStrategy) -> str:
        """Assess risk level of applying a strategy"""
        
        # Base risk from complexity
        complexity_risk = {
            "simple": "low",
            "moderate": "medium", 
            "complex": "high"
        }
        
        base_risk = complexity_risk.get(strategy.complexity, "medium")
        
        # Adjust based on strategy type
        if strategy.strategy_type in ["storage", "preload"]:
            # Generally lower risk
            if base_risk == "high":
                return "medium"
        elif strategy.strategy_type in ["performance", "distribution"]:
            # Potentially higher risk
            if base_risk == "low":
                return "medium"
        
        return base_risk
    
    def _should_auto_apply(self, strategy: OptimizationStrategy) -> bool:
        """Determine if strategy should be auto-applied"""
        
        if not self.config.auto_apply_low_risk_strategies:
            return False
        
        risk_level = self._assess_strategy_risk(strategy)
        
        # Only auto-apply low-risk strategies
        return risk_level == "low"
    
    def _requires_approval(self, strategy: OptimizationStrategy) -> bool:
        """Determine if strategy requires approval"""
        
        if not self.config.require_approval_for_high_risk:
            return False
        
        risk_level = self._assess_strategy_risk(strategy)
        
        # Require approval for medium and high risk
        return risk_level in ["medium", "high"]
    
    def _check_optimization_frequency(self) -> bool:
        """Check if optimization frequency limits are respected"""
        
        current_time = time.time()
        day_start = current_time - (current_time % 86400)
        
        # Count optimizations today
        today_optimizations = [
            d for d in self.recent_decisions
            if d.decision_timestamp >= day_start
        ]
        
        return len(today_optimizations) < self.config.max_optimization_frequency
    
    def _select_anomaly_response_strategy(self, anomaly_type: str,
                                        anomalies: List[Dict]) -> Optional[OptimizationStrategy]:
        """Select strategy to respond to specific anomaly type"""
        
        # Generate strategies and filter for anomaly type
        strategies = self.global_optimizer.generate_optimization_strategies()
        
        # Map anomaly types to strategy types
        anomaly_strategy_map = {
            "response_time": "performance",
            "memory": "storage",
            "hit_rate": "performance",
            "throughput": "performance"
        }
        
        target_strategy_type = anomaly_strategy_map.get(anomaly_type)
        
        if target_strategy_type:
            matching_strategies = [
                s for s in strategies
                if s.strategy_type == target_strategy_type
            ]
            
            if matching_strategies:
                # Return highest priority strategy
                return max(matching_strategies, 
                          key=lambda s: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s.priority, 1))
        
        return None
    
    def _select_preventive_strategy(self, insight: Dict[str, Any]) -> Optional[OptimizationStrategy]:
        """Select preventive strategy based on predictive insight"""
        
        insight_type = insight.get("insight_type")
        strategies = self.global_optimizer.generate_optimization_strategies()
        
        # Map insight types to strategy types
        insight_strategy_map = {
            "performance_degradation": "performance",
            "cache_overflow": "storage",
            "pattern_emergence": "preload"
        }
        
        target_strategy_type = insight_strategy_map.get(insight_type)
        
        if target_strategy_type:
            matching_strategies = [
                s for s in strategies
                if s.strategy_type == target_strategy_type
            ]
            
            if matching_strategies:
                return matching_strategies[0]  # Return first matching strategy
        
        return None
    
    def _store_decision(self, decision: OptimizationDecision):
        """Store optimization decision"""
        self.cache_manager.set_cache(
            self.decisions_cache_type,
            decision.decision_id,
            asdict(decision),
            cache_level="global"
        )


class AutoOptimizationExecutor:
    """Executes optimization decisions automatically"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 global_optimizer: GlobalCacheOptimizer,
                 config: AutoOptimizationConfig):
        
        self.cache_manager = cache_manager
        self.global_optimizer = global_optimizer
        self.config = config
        
        self.executions_cache_type = "optimization_executions"
        self._lock = threading.Lock()
        
        # Execution tracking
        self.active_executions = {}
        self.execution_history = deque(maxlen=50)
    
    def execute_optimization(self, decision: OptimizationDecision) -> OptimizationExecution:
        """Execute an optimization decision"""
        
        execution = OptimizationExecution(
            execution_id=f"exec_{decision.decision_id}",
            decision_id=decision.decision_id,
            strategy_id=decision.strategy_selected,
            started_at=time.time(),
            completed_at=None,
            status="pending",
            performance_before=self._capture_performance_snapshot(),
            performance_after=None,
            actual_benefits=None,
            execution_logs=[],
            rollback_reason=None
        )
        
        # Store and track execution
        self.active_executions[execution.execution_id] = execution
        self._store_execution(execution)
        
        try:
            # Execute the strategy
            execution.status = "running"
            execution.execution_logs.append(f"Starting optimization at {datetime.now()}")
            
            # Apply the optimization strategy
            result = self.global_optimizer.apply_optimization_strategy(decision.strategy_selected)
            
            if result and result.success_rate > 0.5:
                execution.status = "completed"
                execution.completed_at = time.time()
                execution.performance_after = self._capture_performance_snapshot()
                execution.actual_benefits = self._calculate_actual_benefits(
                    execution.performance_before,
                    execution.performance_after
                )
                execution.execution_logs.append("Optimization completed successfully")
                
                # Check if performance improved
                if self.config.rollback_on_performance_degradation:
                    self._check_and_rollback_if_needed(execution)
                
            else:
                execution.status = "failed"
                execution.execution_logs.append("Optimization strategy failed to apply")
        
        except Exception as e:
            execution.status = "failed"
            execution.execution_logs.append(f"Execution failed: {str(e)}")
        
        finally:
            # Update tracking
            self.execution_history.append(execution)
            if execution.execution_id in self.active_executions:
                del self.active_executions[execution.execution_id]
            
            self._store_execution(execution)
        
        return execution
    
    def _capture_performance_snapshot(self) -> Dict[str, float]:
        """Capture current performance metrics"""
        stats = self.cache_manager.get_performance_stats()
        
        return {
            "hit_rate_percent": stats.get("hit_rate_percent", 0),
            "average_response_time_ms": stats.get("average_response_time_ms", 0),
            "total_cache_size_mb": stats.get("total_cache_size_mb", 0),
            "timestamp": time.time()
        }
    
    def _calculate_actual_benefits(self, before: Dict[str, float],
                                 after: Dict[str, float]) -> Dict[str, float]:
        """Calculate actual benefits from optimization"""
        benefits = {}
        
        # Hit rate improvement
        hit_rate_before = before.get("hit_rate_percent", 0)
        hit_rate_after = after.get("hit_rate_percent", 0)
        benefits["hit_rate_improvement"] = hit_rate_after - hit_rate_before
        
        # Response time improvement
        response_before = before.get("average_response_time_ms", 0)
        response_after = after.get("average_response_time_ms", 0)
        if response_before > 0:
            benefits["response_time_improvement_percent"] = (
                (response_before - response_after) / response_before * 100
            )
        
        # Cache size change
        size_before = before.get("total_cache_size_mb", 0)
        size_after = after.get("total_cache_size_mb", 0)
        benefits["cache_size_change_mb"] = size_after - size_before
        
        return benefits
    
    def _check_and_rollback_if_needed(self, execution: OptimizationExecution):
        """Check if rollback is needed due to performance degradation"""
        
        if not execution.actual_benefits:
            return
        
        # Check for significant performance degradation
        hit_rate_change = execution.actual_benefits.get("hit_rate_improvement", 0)
        response_time_change = execution.actual_benefits.get("response_time_improvement_percent", 0)
        
        should_rollback = False
        rollback_reasons = []
        
        if hit_rate_change < -10:  # 10% hit rate drop
            should_rollback = True
            rollback_reasons.append(f"Hit rate decreased by {abs(hit_rate_change):.1f}%")
        
        if response_time_change < -20:  # 20% response time increase
            should_rollback = True
            rollback_reasons.append(f"Response time worsened by {abs(response_time_change):.1f}%")
        
        if should_rollback:
            execution.status = "rolled_back"
            execution.rollback_reason = "; ".join(rollback_reasons)
            execution.execution_logs.append(f"Rolled back due to: {execution.rollback_reason}")
            
            # TODO: Implement actual rollback logic
            # This would involve undoing the optimization changes
    
    def _store_execution(self, execution: OptimizationExecution):
        """Store execution record"""
        self.cache_manager.set_cache(
            self.executions_cache_type,
            execution.execution_id,
            asdict(execution),
            cache_level="global"
        )


class SelfOptimizingCacheOrchestrator:
    """Main orchestrator for self-optimizing cache system"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager,
                 symbol_cache: LanguageAwareSymbolCache,
                 performance_dashboard: CachePerformanceDashboard,
                 config: AutoOptimizationConfig = None):
        
        self.cache_manager = cache_manager
        self.symbol_cache = symbol_cache
        self.performance_dashboard = performance_dashboard
        self.config = config or AutoOptimizationConfig()
        
        # Initialize components
        anomaly_config = AnomalyDetectionConfig()
        self.anomaly_detector = AnomalyDetectionOrchestrator(
            cache_manager, symbol_cache, performance_dashboard, anomaly_config
        )
        
        self.predictive_analytics = PredictiveAnalyticsOrchestrator(
            cache_manager, performance_dashboard
        )
        
        # Initialize global optimizer with lazy loading to avoid circular imports
        self.global_optimizer = None
        
        # Initialize decision engine and executor
        self.decision_engine = None
        self.executor = None
        
        # Control variables
        self.is_running = False
        self.optimization_thread = None
        self._stop_event = threading.Event()
    
    def start_auto_optimization(self):
        """Start automatic optimization process"""
        if self.is_running:
            return
        
        # Initialize components if not already done
        if not self.global_optimizer:
            from .cross_project_intelligence import CrossProjectIntelligenceOrchestrator
            cross_project_intelligence = CrossProjectIntelligenceOrchestrator(
                self.cache_manager, None, self.symbol_cache, self.performance_dashboard
            )
            from .global_optimization import GlobalCacheOptimizer
            self.global_optimizer = GlobalCacheOptimizer(cross_project_intelligence)
        
        if not self.decision_engine:
            self.decision_engine = AutoOptimizationDecisionEngine(
                self.cache_manager, self.anomaly_detector, self.predictive_analytics,
                self.global_optimizer, self.config
            )
        
        if not self.executor:
            self.executor = AutoOptimizationExecutor(
                self.cache_manager, self.global_optimizer, self.config
            )
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start optimization thread
        self.optimization_thread = threading.Thread(target=self._optimization_loop)
        self.optimization_thread.daemon = True
        self.optimization_thread.start()
    
    def stop_auto_optimization(self):
        """Stop automatic optimization process"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        if self.optimization_thread:
            self.optimization_thread.join(timeout=30)
    
    def force_optimization_check(self, trigger_type: str = "manual",
                                trigger_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Force an immediate optimization check"""
        
        if not self.decision_engine:
            return {"error": "Decision engine not initialized"}
        
        # Evaluate optimization need
        decision = self.decision_engine.evaluate_optimization_need(trigger_type, trigger_data)
        
        result = {
            "trigger_type": trigger_type,
            "evaluation_timestamp": time.time(),
            "decision_made": decision is not None,
            "decision": asdict(decision) if decision else None,
            "execution_result": None
        }
        
        # Execute if decision was made and should be auto-applied
        if decision and decision.auto_applied and not decision.approval_required:
            execution = self.executor.execute_optimization(decision)
            result["execution_result"] = asdict(execution)
        
        return result
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization system status"""
        
        status = {
            "system_enabled": self.config.enabled,
            "auto_optimization_running": self.is_running,
            "last_check_timestamp": time.time(),
            "configuration": asdict(self.config),
            "recent_decisions": [],
            "active_executions": [],
            "system_health": {}
        }
        
        # Add recent decisions if available
        if self.decision_engine:
            recent_decisions = list(self.decision_engine.recent_decisions)[-5:]  # Last 5
            status["recent_decisions"] = [asdict(d) for d in recent_decisions]
        
        # Add active executions if available
        if self.executor:
            status["active_executions"] = [
                asdict(e) for e in self.executor.active_executions.values()
            ]
        
        # Add system health metrics
        status["system_health"] = {
            "cache_performance": self.cache_manager.get_performance_stats(),
            "optimization_effectiveness": self._calculate_optimization_effectiveness()
        }
        
        return status
    
    def _optimization_loop(self):
        """Main optimization loop running in background thread"""
        
        while self.is_running and not self._stop_event.is_set():
            try:
                # Perform scheduled optimization check
                decision = self.decision_engine.evaluate_optimization_need("scheduled")
                
                if decision and decision.auto_applied and not decision.approval_required:
                    # Execute optimization automatically
                    self.executor.execute_optimization(decision)
                
                # Wait for next interval
                self._stop_event.wait(self.config.optimization_interval_minutes * 60)
                
            except Exception as e:
                print(f"Error in optimization loop: {e}")
                # Continue running despite errors
                self._stop_event.wait(60)  # Wait 1 minute before retry
    
    def _calculate_optimization_effectiveness(self) -> Dict[str, float]:
        """Calculate effectiveness of recent optimizations"""
        
        if not self.executor:
            return {"message": "No execution history available"}
        
        recent_executions = list(self.executor.execution_history)[-10:]  # Last 10
        
        if not recent_executions:
            return {"message": "No recent executions"}
        
        # Calculate success rate
        successful = len([e for e in recent_executions if e.status == "completed"])
        success_rate = successful / len(recent_executions) * 100
        
        # Calculate average benefits
        completed_executions = [e for e in recent_executions if e.status == "completed" and e.actual_benefits]
        
        if completed_executions:
            avg_hit_rate_improvement = statistics.mean([
                e.actual_benefits.get("hit_rate_improvement", 0)
                for e in completed_executions
            ])
            
            avg_response_improvement = statistics.mean([
                e.actual_benefits.get("response_time_improvement_percent", 0)
                for e in completed_executions
            ])
        else:
            avg_hit_rate_improvement = 0
            avg_response_improvement = 0
        
        return {
            "success_rate_percent": success_rate,
            "average_hit_rate_improvement": avg_hit_rate_improvement,
            "average_response_time_improvement_percent": avg_response_improvement,
            "total_optimizations": len(recent_executions),
            "rollback_rate_percent": len([e for e in recent_executions if e.status == "rolled_back"]) / max(len(recent_executions), 1) * 100
        }