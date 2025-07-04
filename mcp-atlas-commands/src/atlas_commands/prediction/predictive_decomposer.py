"""
Predictive Task Decomposition with ML-Driven Insights
Implements advanced task decomposition using machine learning patterns and historical data.
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
import re

# Import existing ATLAS components
from ..task_analysis_algorithm import TaskComplexityAnalyzer, DependencyAnalyzer, PatternDetector
from ..memory.graph_manager import MemoryGraphManager
from ..storage.task_storage_manager import TaskStorageManager


class DecompositionStrategy(Enum):
    """Task decomposition strategies."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"
    ML_OPTIMIZED = "ml_optimized"


class TaskComplexityPattern(Enum):
    """Patterns for task complexity prediction."""
    LINEAR_GROWTH = "linear_growth"
    EXPONENTIAL_GROWTH = "exponential_growth"
    LOGARITHMIC_GROWTH = "logarithmic_growth"
    CONSTANT_COMPLEXITY = "constant_complexity"
    UNPREDICTABLE = "unpredictable"


class PredictionConfidence(Enum):
    """Confidence levels for ML predictions."""
    VERY_HIGH = "very_high"      # >90% confidence
    HIGH = "high"                # 80-90% confidence
    MEDIUM = "medium"            # 60-80% confidence
    LOW = "low"                  # 40-60% confidence
    VERY_LOW = "very_low"        # <40% confidence


@dataclass
class TaskDecompositionPrediction:
    """Prediction result for task decomposition."""
    predicted_subtasks: List[Dict[str, Any]]
    decomposition_strategy: DecompositionStrategy
    complexity_pattern: TaskComplexityPattern
    confidence_score: float
    confidence_level: PredictionConfidence
    execution_sequence: List[str]
    dependency_graph: Dict[str, List[str]]
    resource_requirements: Dict[str, Any]
    estimated_duration: float
    risk_factors: List[str]
    optimization_opportunities: List[str]
    ml_insights: Dict[str, Any]


@dataclass
class HistoricalTaskPattern:
    """Historical pattern for similar tasks."""
    task_signature: str
    decomposition_used: List[str]
    success_rate: float
    average_duration: float
    common_issues: List[str]
    optimization_points: List[str]
    frequency: int
    last_seen: datetime


class PredictiveTaskDecomposer:
    """
    Advanced task decomposer using ML-driven insights and historical patterns.
    
    Implements predictive decomposition strategies:
    - Historical pattern recognition
    - ML-based complexity prediction
    - Adaptive decomposition optimization
    - Resource-aware task planning
    - Risk-based decomposition adjustment
    """
    
    def __init__(self, storage_path: str = None):
        """Initialize the predictive task decomposer."""
        
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.task_analyzer = TaskComplexityAnalyzer()
        self.memory_manager = MemoryGraphManager()
        self.storage_manager = TaskStorageManager(storage_path)
        
        # ML and pattern recognition
        self.historical_patterns: Dict[str, HistoricalTaskPattern] = {}
        self.pattern_database: Dict[str, List[Dict]] = defaultdict(list)
        self.decomposition_success_metrics: Dict[str, Dict] = {}
        
        # Prediction models (simplified ML simulation)
        self.complexity_predictor = ComplexityPredictor()
        self.decomposition_optimizer = DecompositionOptimizer()
        self.resource_predictor = ResourcePredictor()
        
        # Configuration
        self.config = {
            "min_historical_samples": 3,     # Minimum samples for pattern recognition
            "confidence_threshold": 0.6,     # Minimum confidence for predictions
            "max_decomposition_depth": 5,    # Maximum decomposition levels
            "parallel_task_threshold": 3,    # When to consider parallel execution
            "ml_prediction_weight": 0.7,     # Weight for ML vs rule-based predictions
            "pattern_similarity_threshold": 0.8,  # Threshold for pattern matching
            "adaptive_learning_rate": 0.1,   # Rate for updating patterns
            "resource_safety_margin": 0.2    # Safety margin for resource estimates
        }
        
        # Initialize with some default patterns
        self._initialize_default_patterns()
        
        self.logger.info("PredictiveTaskDecomposer initialized with ML-driven insights")
    
    async def predict_task_decomposition(self, 
                                       task_description: str,
                                       context: Dict = None,
                                       strategy_hint: DecompositionStrategy = None) -> TaskDecompositionPrediction:
        """
        Predict optimal task decomposition using ML-driven insights.
        
        Args:
            task_description: Description of the task to decompose
            context: Additional context including constraints, resources
            strategy_hint: Optional hint for decomposition strategy
            
        Returns:
            Comprehensive prediction with ML insights and recommendations
        """
        
        self.logger.info(f"Predicting task decomposition for: {task_description[:100]}...")
        
        try:
            # Step 1: Analyze task characteristics
            task_signature = await self._generate_task_signature(task_description, context)
            task_analysis = await self._analyze_task_characteristics(task_description, context)
            
            # Step 2: Search for historical patterns
            similar_patterns = await self._find_similar_historical_patterns(task_signature, task_analysis)
            
            # Step 3: Apply ML-based predictions
            ml_predictions = await self._apply_ml_predictions(task_analysis, similar_patterns)
            
            # Step 4: Generate optimal decomposition
            decomposition = await self._generate_optimal_decomposition(
                task_description, task_analysis, ml_predictions, strategy_hint
            )
            
            # Step 5: Validate and optimize
            validated_decomposition = await self._validate_and_optimize_decomposition(
                decomposition, task_analysis, context
            )
            
            # Step 6: Calculate confidence and risk assessment
            confidence_assessment = await self._assess_prediction_confidence(
                validated_decomposition, similar_patterns, ml_predictions
            )
            
            # Step 7: Generate comprehensive prediction result
            prediction = TaskDecompositionPrediction(
                predicted_subtasks=validated_decomposition["subtasks"],
                decomposition_strategy=validated_decomposition["strategy"],
                complexity_pattern=validated_decomposition["complexity_pattern"],
                confidence_score=confidence_assessment["confidence_score"],
                confidence_level=confidence_assessment["confidence_level"],
                execution_sequence=validated_decomposition["execution_sequence"],
                dependency_graph=validated_decomposition["dependency_graph"],
                resource_requirements=validated_decomposition["resource_requirements"],
                estimated_duration=validated_decomposition["estimated_duration"],
                risk_factors=confidence_assessment["risk_factors"],
                optimization_opportunities=validated_decomposition["optimization_opportunities"],
                ml_insights=ml_predictions
            )
            
            # Step 8: Store pattern for future learning
            await self._store_prediction_pattern(task_signature, prediction, task_analysis)
            
            self.logger.info(
                f"Predictive decomposition complete: {len(prediction.predicted_subtasks)} subtasks, "
                f"{prediction.confidence_level.value} confidence"
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Predictive task decomposition failed: {str(e)}")
            
            # Fallback to basic decomposition
            return await self._generate_fallback_decomposition(task_description, context)
    
    async def learn_from_execution_results(self, 
                                         task_signature: str,
                                         prediction: TaskDecompositionPrediction,
                                         execution_results: Dict) -> None:
        """
        Learn from execution results to improve future predictions.
        
        Args:
            task_signature: Signature of the executed task
            prediction: Original prediction made
            execution_results: Actual execution results and metrics
        """
        
        self.logger.info(f"Learning from execution results for task: {task_signature}")
        
        try:
            # Extract learning insights
            actual_duration = execution_results.get("actual_duration", 0.0)
            predicted_duration = prediction.estimated_duration
            success_rate = execution_results.get("success_rate", 0.0)
            issues_encountered = execution_results.get("issues", [])
            
            # Calculate prediction accuracy
            duration_accuracy = 1.0 - abs(actual_duration - predicted_duration) / max(predicted_duration, 0.1)
            overall_accuracy = (duration_accuracy + success_rate) / 2.0
            
            # Update historical patterns
            pattern_key = task_signature
            if pattern_key in self.historical_patterns:
                pattern = self.historical_patterns[pattern_key]
                
                # Update success rate with exponential moving average
                alpha = self.config["adaptive_learning_rate"]
                pattern.success_rate = alpha * success_rate + (1 - alpha) * pattern.success_rate
                pattern.average_duration = alpha * actual_duration + (1 - alpha) * pattern.average_duration
                pattern.frequency += 1
                pattern.last_seen = datetime.now()
                
                # Update common issues
                for issue in issues_encountered:
                    if issue not in pattern.common_issues:
                        pattern.common_issues.append(issue)
            else:
                # Create new pattern
                self.historical_patterns[pattern_key] = HistoricalTaskPattern(
                    task_signature=task_signature,
                    decomposition_used=[s["name"] for s in prediction.predicted_subtasks],
                    success_rate=success_rate,
                    average_duration=actual_duration,
                    common_issues=issues_encountered,
                    optimization_points=[],
                    frequency=1,
                    last_seen=datetime.now()
                )
            
            # Update ML models (simplified simulation)
            await self._update_ml_models(prediction, execution_results, overall_accuracy)
            
            self.logger.info(f"Learning complete: {overall_accuracy:.2%} prediction accuracy")
            
        except Exception as e:
            self.logger.error(f"Learning from execution results failed: {str(e)}")
    
    async def get_decomposition_insights(self, task_description: str) -> Dict[str, Any]:
        """Get insights about task decomposition patterns and recommendations."""
        
        try:
            task_signature = await self._generate_task_signature(task_description, {})
            similar_patterns = await self._find_similar_historical_patterns(task_signature, {})
            
            insights = {
                "historical_patterns_found": len(similar_patterns),
                "common_decomposition_strategies": self._analyze_common_strategies(similar_patterns),
                "success_rate_distribution": self._analyze_success_rates(similar_patterns),
                "common_risk_factors": self._analyze_common_risks(similar_patterns),
                "optimization_recommendations": await self._generate_optimization_recommendations(similar_patterns),
                "complexity_predictions": await self._predict_complexity_trends(task_signature),
                "resource_insights": await self._analyze_resource_patterns(similar_patterns)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get decomposition insights: {str(e)}")
            return {"error": str(e)}
    
    # Private implementation methods
    
    async def _generate_task_signature(self, task_description: str, context: Dict = None) -> str:
        """Generate a unique signature for the task type."""
        
        # Extract key features for signature
        keywords = self._extract_keywords(task_description)
        complexity_indicators = self._extract_complexity_indicators(task_description)
        domain_indicators = self._extract_domain_indicators(task_description)
        
        # Add context features
        context_features = []
        if context:
            if "project_type" in context:
                context_features.append(f"proj:{context['project_type']}")
            if "team_size" in context:
                context_features.append(f"team:{context['team_size']}")
        
        # Combine features into signature
        signature_parts = (
            sorted(keywords[:5]) +  # Top 5 keywords
            complexity_indicators +
            domain_indicators +
            context_features
        )
        
        signature = "|".join(signature_parts)
        return signature
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key keywords from task description."""
        
        # Simple keyword extraction (would use NLP in production)
        keywords = re.findall(r'\b\w+\b', text.lower())
        
        # Filter common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in keywords if len(word) > 3 and word not in stop_words]
        
        # Return most frequent keywords
        return [word for word, count in Counter(keywords).most_common(10)]
    
    def _extract_complexity_indicators(self, text: str) -> List[str]:
        """Extract complexity indicators from task description."""
        
        complexity_patterns = {
            "high_complexity": ["complex", "difficult", "challenging", "intricate", "sophisticated"],
            "integration": ["integrate", "connect", "combine", "merge", "link"],
            "analysis": ["analyze", "investigate", "research", "study", "examine"],
            "development": ["develop", "create", "build", "implement", "design"],
            "optimization": ["optimize", "improve", "enhance", "refactor", "performance"],
            "testing": ["test", "validate", "verify", "check", "qa"],
            "deployment": ["deploy", "release", "publish", "launch", "production"]
        }
        
        indicators = []
        text_lower = text.lower()
        
        for category, patterns in complexity_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                indicators.append(f"comp:{category}")
        
        return indicators
    
    def _extract_domain_indicators(self, text: str) -> List[str]:
        """Extract domain-specific indicators."""
        
        domain_patterns = {
            "backend": ["api", "server", "database", "backend", "service"],
            "frontend": ["ui", "interface", "frontend", "react", "vue", "angular"],
            "devops": ["docker", "kubernetes", "ci/cd", "deployment", "infrastructure"],
            "data": ["data", "analytics", "ml", "machine learning", "statistics"],
            "security": ["security", "auth", "authentication", "encryption", "ssl"]
        }
        
        indicators = []
        text_lower = text.lower()
        
        for domain, patterns in domain_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                indicators.append(f"domain:{domain}")
        
        return indicators
    
    async def _analyze_task_characteristics(self, task_description: str, context: Dict = None) -> Dict:
        """Analyze comprehensive task characteristics."""
        
        # Use existing task analyzer
        basic_analysis = await self.task_analyzer.analyze_task_complexity(task_description, context or {})
        
        # Add ML-enhanced characteristics
        enhanced_analysis = {
            **basic_analysis,
            "ml_features": {
                "text_length": len(task_description),
                "keyword_density": self._calculate_keyword_density(task_description),
                "complexity_score_ml": await self.complexity_predictor.predict_complexity(task_description),
                "decomposition_potential": self._assess_decomposition_potential(task_description),
                "parallelization_opportunity": self._assess_parallelization_opportunity(task_description)
            }
        }
        
        return enhanced_analysis
    
    def _calculate_keyword_density(self, text: str) -> float:
        """Calculate keyword density for ML features."""
        
        keywords = self._extract_keywords(text)
        total_words = len(text.split())
        
        return len(keywords) / max(total_words, 1)
    
    def _assess_decomposition_potential(self, text: str) -> float:
        """Assess how well a task can be decomposed."""
        
        decomposition_indicators = [
            "step", "phase", "part", "component", "module", "section",
            "first", "then", "next", "finally", "after", "before"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for indicator in decomposition_indicators if indicator in text_lower)
        
        return min(1.0, matches / 5.0)  # Normalize to 0-1
    
    def _assess_parallelization_opportunity(self, text: str) -> float:
        """Assess potential for parallel execution."""
        
        parallel_indicators = [
            "independent", "parallel", "concurrent", "simultaneously", 
            "separate", "isolated", "modular"
        ]
        
        sequential_indicators = [
            "sequential", "order", "depends", "after", "before", "prerequisite"
        ]
        
        text_lower = text.lower()
        
        parallel_score = sum(1 for indicator in parallel_indicators if indicator in text_lower)
        sequential_score = sum(1 for indicator in sequential_indicators if indicator in text_lower)
        
        # Calculate net parallelization potential
        net_score = parallel_score - sequential_score
        return max(0.0, min(1.0, (net_score + 3) / 6))  # Normalize to 0-1
    
    async def _find_similar_historical_patterns(self, task_signature: str, task_analysis: Dict) -> List[HistoricalTaskPattern]:
        """Find similar historical patterns for the task."""
        
        similar_patterns = []
        
        # Direct signature match
        if task_signature in self.historical_patterns:
            similar_patterns.append(self.historical_patterns[task_signature])
        
        # Fuzzy matching based on signature similarity
        for signature, pattern in self.historical_patterns.items():
            similarity = self._calculate_signature_similarity(task_signature, signature)
            
            if similarity >= self.config["pattern_similarity_threshold"]:
                # Add similarity score to pattern for ranking
                pattern_copy = HistoricalTaskPattern(**asdict(pattern))
                pattern_copy.task_signature = f"{signature} (similarity: {similarity:.2f})"
                similar_patterns.append(pattern_copy)
        
        # Sort by frequency and success rate
        similar_patterns.sort(key=lambda p: (p.frequency, p.success_rate), reverse=True)
        
        return similar_patterns[:10]  # Return top 10 similar patterns
    
    def _calculate_signature_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between two task signatures."""
        
        features1 = set(sig1.split("|"))
        features2 = set(sig2.split("|"))
        
        if not features1 or not features2:
            return 0.0
        
        intersection = features1 & features2
        union = features1 | features2
        
        # Jaccard similarity
        return len(intersection) / len(union)
    
    async def _apply_ml_predictions(self, task_analysis: Dict, similar_patterns: List[HistoricalTaskPattern]) -> Dict:
        """Apply ML-based predictions for task decomposition."""
        
        ml_predictions = {
            "complexity_prediction": await self.complexity_predictor.predict_comprehensive_complexity(task_analysis),
            "decomposition_recommendation": await self.decomposition_optimizer.recommend_strategy(task_analysis, similar_patterns),
            "resource_prediction": await self.resource_predictor.predict_requirements(task_analysis),
            "duration_prediction": await self._predict_duration_ml(task_analysis, similar_patterns),
            "risk_prediction": await self._predict_risks_ml(task_analysis, similar_patterns),
            "success_probability": await self._predict_success_probability(task_analysis, similar_patterns)
        }
        
        return ml_predictions
    
    async def _generate_optimal_decomposition(self, 
                                            task_description: str,
                                            task_analysis: Dict,
                                            ml_predictions: Dict,
                                            strategy_hint: DecompositionStrategy = None) -> Dict:
        """Generate optimal task decomposition using all available insights."""
        
        # Determine decomposition strategy
        if strategy_hint:
            strategy = strategy_hint
        else:
            strategy = ml_predictions["decomposition_recommendation"]["recommended_strategy"]
        
        # Generate subtasks based on strategy
        if strategy == DecompositionStrategy.ML_OPTIMIZED:
            subtasks = await self._generate_ml_optimized_subtasks(task_description, task_analysis, ml_predictions)
        else:
            subtasks = await self._generate_traditional_subtasks(task_description, task_analysis, strategy)
        
        # Create execution sequence
        execution_sequence = self._create_execution_sequence(subtasks, strategy)
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(subtasks)
        
        # Determine complexity pattern
        complexity_pattern = self._determine_complexity_pattern(task_analysis, ml_predictions)
        
        return {
            "subtasks": subtasks,
            "strategy": strategy,
            "complexity_pattern": complexity_pattern,
            "execution_sequence": execution_sequence,
            "dependency_graph": dependency_graph,
            "resource_requirements": ml_predictions["resource_prediction"],
            "estimated_duration": ml_predictions["duration_prediction"],
            "optimization_opportunities": self._identify_optimization_opportunities(subtasks, ml_predictions)
        }
    
    async def _generate_ml_optimized_subtasks(self, 
                                            task_description: str,
                                            task_analysis: Dict,
                                            ml_predictions: Dict) -> List[Dict]:
        """Generate subtasks using ML optimization."""
        
        # ML-driven subtask generation based on complexity and patterns
        complexity_score = task_analysis.get("complexity", {}).get("overall_score", 50)
        
        base_subtasks = [
            {
                "name": "analysis_and_planning",
                "description": "Analyze requirements and create detailed plan",
                "estimated_duration": ml_predictions["duration_prediction"] * 0.2,
                "complexity": min(complexity_score, 40),
                "dependencies": [],
                "parallelizable": False,
                "resources": {"cpu": "low", "memory": "low"},
                "ml_optimized": True
            },
            {
                "name": "core_implementation",
                "description": "Implement core functionality",
                "estimated_duration": ml_predictions["duration_prediction"] * 0.5,
                "complexity": complexity_score,
                "dependencies": ["analysis_and_planning"],
                "parallelizable": ml_predictions["decomposition_recommendation"]["parallelization_score"] > 0.6,
                "resources": ml_predictions["resource_prediction"],
                "ml_optimized": True
            },
            {
                "name": "validation_and_testing",
                "description": "Validate implementation and run tests",
                "estimated_duration": ml_predictions["duration_prediction"] * 0.2,
                "complexity": complexity_score * 0.7,
                "dependencies": ["core_implementation"],
                "parallelizable": True,
                "resources": {"cpu": "medium", "memory": "medium"},
                "ml_optimized": True
            },
            {
                "name": "optimization_and_finalization",
                "description": "Optimize and finalize implementation",
                "estimated_duration": ml_predictions["duration_prediction"] * 0.1,
                "complexity": complexity_score * 0.5,
                "dependencies": ["validation_and_testing"],
                "parallelizable": False,
                "resources": {"cpu": "low", "memory": "low"},
                "ml_optimized": True
            }
        ]
        
        # Add complexity-specific subtasks
        if complexity_score >= 70:
            base_subtasks.insert(2, {
                "name": "integration_and_compatibility",
                "description": "Handle integration and compatibility requirements",
                "estimated_duration": ml_predictions["duration_prediction"] * 0.15,
                "complexity": complexity_score * 0.8,
                "dependencies": ["core_implementation"],
                "parallelizable": True,
                "resources": {"cpu": "medium", "memory": "high"},
                "ml_optimized": True
            })
        
        return base_subtasks
    
    async def _generate_traditional_subtasks(self, 
                                           task_description: str,
                                           task_analysis: Dict,
                                           strategy: DecompositionStrategy) -> List[Dict]:
        """Generate subtasks using traditional decomposition methods."""
        
        # Simple rule-based decomposition
        return [
            {
                "name": "planning",
                "description": "Plan and design the solution",
                "estimated_duration": 30.0,
                "complexity": 30,
                "dependencies": [],
                "parallelizable": False,
                "resources": {"cpu": "low", "memory": "low"},
                "ml_optimized": False
            },
            {
                "name": "implementation",
                "description": "Implement the solution",
                "estimated_duration": 120.0,
                "complexity": 70,
                "dependencies": ["planning"],
                "parallelizable": strategy in [DecompositionStrategy.PARALLEL, DecompositionStrategy.HYBRID],
                "resources": {"cpu": "high", "memory": "medium"},
                "ml_optimized": False
            },
            {
                "name": "testing",
                "description": "Test the implementation",
                "estimated_duration": 60.0,
                "complexity": 40,
                "dependencies": ["implementation"],
                "parallelizable": True,
                "resources": {"cpu": "medium", "memory": "medium"},
                "ml_optimized": False
            }
        ]
    
    def _create_execution_sequence(self, subtasks: List[Dict], strategy: DecompositionStrategy) -> List[str]:
        """Create optimal execution sequence for subtasks."""
        
        if strategy == DecompositionStrategy.SEQUENTIAL:
            return [task["name"] for task in subtasks]
        
        elif strategy == DecompositionStrategy.PARALLEL:
            # Group parallelizable tasks
            sequence = []
            parallel_groups = []
            current_group = []
            
            for task in subtasks:
                if task["parallelizable"] and not task["dependencies"]:
                    current_group.append(task["name"])
                else:
                    if current_group:
                        parallel_groups.append(current_group)
                        current_group = []
                    sequence.append(task["name"])
            
            if current_group:
                parallel_groups.append(current_group)
            
            # Interleave parallel groups with sequence
            result = []
            for i, task in enumerate(sequence):
                result.append(task)
                if i < len(parallel_groups):
                    result.extend(parallel_groups[i])
            
            return result
        
        else:  # HYBRID, ADAPTIVE, ML_OPTIMIZED
            # Topological sort considering dependencies
            return self._topological_sort(subtasks)
    
    def _topological_sort(self, subtasks: List[Dict]) -> List[str]:
        """Perform topological sort on subtasks considering dependencies."""
        
        # Simple topological sort implementation
        in_degree = {task["name"]: 0 for task in subtasks}
        graph = {task["name"]: [] for task in subtasks}
        
        # Build graph
        for task in subtasks:
            for dep in task["dependencies"]:
                if dep in graph:
                    graph[dep].append(task["name"])
                    in_degree[task["name"]] += 1
        
        # Kahn's algorithm
        queue = [task for task, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _build_dependency_graph(self, subtasks: List[Dict]) -> Dict[str, List[str]]:
        """Build dependency graph for subtasks."""
        
        graph = {}
        for task in subtasks:
            graph[task["name"]] = task["dependencies"]
        
        return graph
    
    def _determine_complexity_pattern(self, task_analysis: Dict, ml_predictions: Dict) -> TaskComplexityPattern:
        """Determine the complexity pattern for the task."""
        
        complexity_score = task_analysis.get("complexity", {}).get("overall_score", 50)
        ml_complexity = ml_predictions.get("complexity_prediction", {})
        
        # Simple pattern determination logic
        if complexity_score < 30:
            return TaskComplexityPattern.CONSTANT_COMPLEXITY
        elif complexity_score < 60:
            return TaskComplexityPattern.LINEAR_GROWTH
        elif complexity_score < 80:
            return TaskComplexityPattern.LOGARITHMIC_GROWTH
        elif ml_complexity.get("predictability", 0.5) > 0.7:
            return TaskComplexityPattern.EXPONENTIAL_GROWTH
        else:
            return TaskComplexityPattern.UNPREDICTABLE
    
    def _identify_optimization_opportunities(self, subtasks: List[Dict], ml_predictions: Dict) -> List[str]:
        """Identify opportunities for optimization."""
        
        opportunities = []
        
        # Check for parallelization opportunities
        parallelizable_tasks = [task for task in subtasks if task.get("parallelizable", False)]
        if len(parallelizable_tasks) >= 2:
            opportunities.append("parallel_execution_optimization")
        
        # Check for resource optimization
        resource_intensive_tasks = [
            task for task in subtasks 
            if task.get("resources", {}).get("cpu") == "high"
        ]
        if len(resource_intensive_tasks) >= 2:
            opportunities.append("resource_pooling_optimization")
        
        # Check for caching opportunities
        if ml_predictions.get("success_probability", 0.5) > 0.8:
            opportunities.append("result_caching_optimization")
        
        # Check for early validation
        if any(task.get("complexity", 0) > 70 for task in subtasks):
            opportunities.append("early_validation_checkpoints")
        
        return opportunities
    
    # Additional helper methods for ML simulation and pattern analysis
    
    def _initialize_default_patterns(self):
        """Initialize with some default historical patterns."""
        
        default_patterns = {
            "comp:development|domain:backend": HistoricalTaskPattern(
                task_signature="comp:development|domain:backend",
                decomposition_used=["planning", "implementation", "testing", "deployment"],
                success_rate=0.85,
                average_duration=180.0,
                common_issues=["integration_complexity", "dependency_conflicts"],
                optimization_points=["early_testing", "modular_design"],
                frequency=25,
                last_seen=datetime.now() - timedelta(days=7)
            ),
            "comp:analysis|domain:data": HistoricalTaskPattern(
                task_signature="comp:analysis|domain:data",
                decomposition_used=["data_collection", "analysis", "visualization", "reporting"],
                success_rate=0.75,
                average_duration=120.0,
                common_issues=["data_quality", "analysis_complexity"],
                optimization_points=["data_preprocessing", "incremental_analysis"],
                frequency=15,
                last_seen=datetime.now() - timedelta(days=3)
            )
        }
        
        self.historical_patterns.update(default_patterns)
    
    async def _validate_and_optimize_decomposition(self, 
                                                 decomposition: Dict,
                                                 task_analysis: Dict,
                                                 context: Dict = None) -> Dict:
        """Validate and optimize the generated decomposition."""
        
        # Validation checks
        validated_decomposition = dict(decomposition)
        
        # Check for missing dependencies
        all_task_names = {task["name"] for task in decomposition["subtasks"]}
        for task in validated_decomposition["subtasks"]:
            # Remove invalid dependencies
            task["dependencies"] = [
                dep for dep in task["dependencies"] 
                if dep in all_task_names
            ]
        
        # Optimize resource allocation
        validated_decomposition["resource_requirements"] = self._optimize_resource_allocation(
            decomposition["subtasks"], decomposition["resource_requirements"]
        )
        
        # Adjust duration estimates based on complexity
        total_complexity = sum(task.get("complexity", 50) for task in decomposition["subtasks"])
        if total_complexity > 300:  # High complexity threshold
            validated_decomposition["estimated_duration"] *= 1.2  # Add complexity buffer
        
        return validated_decomposition
    
    def _optimize_resource_allocation(self, subtasks: List[Dict], base_requirements: Dict) -> Dict:
        """Optimize resource allocation for subtasks."""
        
        # Calculate peak resource usage
        max_cpu_tasks = len([task for task in subtasks if task.get("resources", {}).get("cpu") == "high"])
        max_memory_tasks = len([task for task in subtasks if task.get("resources", {}).get("memory") == "high"])
        
        optimized = dict(base_requirements)
        
        # Add peak resource adjustments
        if max_cpu_tasks > 2:
            optimized["cpu_cores"] = max(optimized.get("cpu_cores", 4), max_cpu_tasks * 2)
        
        if max_memory_tasks > 1:
            optimized["memory_gb"] = max(optimized.get("memory_gb", 8), max_memory_tasks * 4)
        
        return optimized
    
    async def _assess_prediction_confidence(self, 
                                          decomposition: Dict,
                                          similar_patterns: List[HistoricalTaskPattern],
                                          ml_predictions: Dict) -> Dict:
        """Assess confidence in the prediction and identify risk factors."""
        
        # Base confidence from ML predictions
        base_confidence = ml_predictions.get("success_probability", 0.5)
        
        # Adjust confidence based on historical patterns
        if similar_patterns:
            avg_historical_success = sum(p.success_rate for p in similar_patterns) / len(similar_patterns)
            historical_weight = min(len(similar_patterns) / 10.0, 0.4)  # Max 40% weight
            base_confidence = base_confidence * (1 - historical_weight) + avg_historical_success * historical_weight
        
        # Adjust confidence based on complexity
        complexity_penalty = 0.0
        for task in decomposition["subtasks"]:
            if task.get("complexity", 50) > 80:
                complexity_penalty += 0.05  # 5% penalty per high-complexity task
        
        final_confidence = max(0.1, base_confidence - complexity_penalty)
        
        # Determine confidence level
        if final_confidence >= 0.9:
            confidence_level = PredictionConfidence.VERY_HIGH
        elif final_confidence >= 0.8:
            confidence_level = PredictionConfidence.HIGH
        elif final_confidence >= 0.6:
            confidence_level = PredictionConfidence.MEDIUM
        elif final_confidence >= 0.4:
            confidence_level = PredictionConfidence.LOW
        else:
            confidence_level = PredictionConfidence.VERY_LOW
        
        # Identify risk factors
        risk_factors = []
        
        if not similar_patterns:
            risk_factors.append("no_historical_patterns")
        
        if any(task.get("complexity", 50) > 85 for task in decomposition["subtasks"]):
            risk_factors.append("high_complexity_components")
        
        if len(decomposition["subtasks"]) > 8:
            risk_factors.append("high_decomposition_depth")
        
        if decomposition["estimated_duration"] > 300:  # 5 hours
            risk_factors.append("long_execution_time")
        
        return {
            "confidence_score": final_confidence,
            "confidence_level": confidence_level,
            "risk_factors": risk_factors
        }
    
    async def _store_prediction_pattern(self, 
                                      task_signature: str,
                                      prediction: TaskDecompositionPrediction,
                                      task_analysis: Dict) -> None:
        """Store prediction pattern for future learning."""
        
        # Store in pattern database for analysis
        pattern_entry = {
            "task_signature": task_signature,
            "prediction": asdict(prediction),
            "task_analysis_summary": {
                "complexity": task_analysis.get("complexity", {}).get("overall_score", 50),
                "pattern": task_analysis.get("patterns", {}).get("primary_pattern", "unknown")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to pattern database
        signature_key = task_signature.split("|")[0] if "|" in task_signature else task_signature
        self.pattern_database[signature_key].append(pattern_entry)
        
        # Keep only recent patterns (last 100 per signature)
        if len(self.pattern_database[signature_key]) > 100:
            self.pattern_database[signature_key] = self.pattern_database[signature_key][-100:]
    
    async def _generate_fallback_decomposition(self, task_description: str, context: Dict = None) -> TaskDecompositionPrediction:
        """Generate fallback decomposition when ML prediction fails."""
        
        return TaskDecompositionPrediction(
            predicted_subtasks=[
                {
                    "name": "analyze_and_plan",
                    "description": "Analyze requirements and create plan",
                    "estimated_duration": 60.0,
                    "complexity": 40,
                    "dependencies": [],
                    "parallelizable": False,
                    "resources": {"cpu": "low", "memory": "low"},
                    "ml_optimized": False
                },
                {
                    "name": "implement_solution",
                    "description": "Implement the solution",
                    "estimated_duration": 120.0,
                    "complexity": 60,
                    "dependencies": ["analyze_and_plan"],
                    "parallelizable": False,
                    "resources": {"cpu": "medium", "memory": "medium"},
                    "ml_optimized": False
                },
                {
                    "name": "test_and_validate",
                    "description": "Test and validate the solution",
                    "estimated_duration": 30.0,
                    "complexity": 30,
                    "dependencies": ["implement_solution"],
                    "parallelizable": False,
                    "resources": {"cpu": "low", "memory": "low"},
                    "ml_optimized": False
                }
            ],
            decomposition_strategy=DecompositionStrategy.SEQUENTIAL,
            complexity_pattern=TaskComplexityPattern.LINEAR_GROWTH,
            confidence_score=0.3,
            confidence_level=PredictionConfidence.LOW,
            execution_sequence=["analyze_and_plan", "implement_solution", "test_and_validate"],
            dependency_graph={
                "analyze_and_plan": [],
                "implement_solution": ["analyze_and_plan"],
                "test_and_validate": ["implement_solution"]
            },
            resource_requirements={"cpu_cores": 2, "memory_gb": 4, "storage_gb": 10},
            estimated_duration=210.0,
            risk_factors=["ml_prediction_failed", "fallback_decomposition"],
            optimization_opportunities=["enable_ml_predictions"],
            ml_insights={"status": "fallback", "reason": "ml_prediction_failed"}
        )
    
    # ML Model Simulation Classes (simplified)
    
    async def _update_ml_models(self, prediction: TaskDecompositionPrediction, execution_results: Dict, accuracy: float):
        """Update ML models based on execution feedback."""
        # Simplified ML model updating
        await self.complexity_predictor.update_model(prediction, execution_results, accuracy)
        await self.decomposition_optimizer.update_model(prediction, execution_results, accuracy)
        await self.resource_predictor.update_model(prediction, execution_results, accuracy)
    
    async def _predict_duration_ml(self, task_analysis: Dict, similar_patterns: List[HistoricalTaskPattern]) -> float:
        """ML-based duration prediction."""
        if similar_patterns:
            return sum(p.average_duration for p in similar_patterns) / len(similar_patterns)
        return 120.0  # Default
    
    async def _predict_risks_ml(self, task_analysis: Dict, similar_patterns: List[HistoricalTaskPattern]) -> List[str]:
        """ML-based risk prediction."""
        risks = []
        if similar_patterns:
            for pattern in similar_patterns:
                risks.extend(pattern.common_issues)
        return list(set(risks))  # Remove duplicates
    
    async def _predict_success_probability(self, task_analysis: Dict, similar_patterns: List[HistoricalTaskPattern]) -> float:
        """ML-based success probability prediction."""
        if similar_patterns:
            return sum(p.success_rate for p in similar_patterns) / len(similar_patterns)
        return 0.7  # Default
    
    # Analysis methods for insights
    
    def _analyze_common_strategies(self, patterns: List[HistoricalTaskPattern]) -> Dict[str, int]:
        """Analyze common decomposition strategies."""
        strategy_counts = Counter()
        for pattern in patterns:
            # Infer strategy from decomposition structure
            if len(pattern.decomposition_used) <= 3:
                strategy_counts["simple"] += 1
            elif any("parallel" in step.lower() for step in pattern.decomposition_used):
                strategy_counts["parallel"] += 1
            else:
                strategy_counts["sequential"] += 1
        return dict(strategy_counts)
    
    def _analyze_success_rates(self, patterns: List[HistoricalTaskPattern]) -> Dict[str, float]:
        """Analyze success rate distribution."""
        if not patterns:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        
        success_rates = [p.success_rate for p in patterns]
        return {
            "min": min(success_rates),
            "max": max(success_rates),
            "avg": sum(success_rates) / len(success_rates)
        }
    
    def _analyze_common_risks(self, patterns: List[HistoricalTaskPattern]) -> List[str]:
        """Analyze common risk factors."""
        all_issues = []
        for pattern in patterns:
            all_issues.extend(pattern.common_issues)
        
        issue_counts = Counter(all_issues)
        return [issue for issue, count in issue_counts.most_common(5)]
    
    async def _generate_optimization_recommendations(self, patterns: List[HistoricalTaskPattern]) -> List[str]:
        """Generate optimization recommendations based on patterns."""
        recommendations = []
        
        if patterns:
            avg_success_rate = sum(p.success_rate for p in patterns) / len(patterns)
            if avg_success_rate < 0.8:
                recommendations.append("Consider adding more validation checkpoints")
            
            avg_duration = sum(p.average_duration for p in patterns) / len(patterns)
            if avg_duration > 180:  # 3 hours
                recommendations.append("Consider parallel execution strategies")
        
        recommendations.extend([
            "Use ML-optimized decomposition strategy",
            "Implement early risk detection",
            "Enable adaptive resource allocation"
        ])
        
        return recommendations
    
    async def _predict_complexity_trends(self, task_signature: str) -> Dict[str, Any]:
        """Predict complexity trends for similar tasks."""
        return {
            "trend": "increasing",
            "confidence": 0.6,
            "recommendation": "Monitor complexity growth and consider decomposition refinements"
        }
    
    async def _analyze_resource_patterns(self, patterns: List[HistoricalTaskPattern]) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        return {
            "typical_cpu_usage": "medium",
            "typical_memory_usage": "medium",
            "peak_resource_periods": ["implementation", "testing"],
            "optimization_opportunities": ["resource_pooling", "dynamic_scaling"]
        }


# Simplified ML Model Classes
class ComplexityPredictor:
    """Simplified ML model for complexity prediction."""
    
    async def predict_complexity(self, task_description: str) -> float:
        # Simple complexity scoring based on text features
        return min(100.0, len(task_description.split()) * 2 + len(task_description) / 10)
    
    async def predict_comprehensive_complexity(self, task_analysis: Dict) -> Dict:
        return {
            "computational_complexity": 60.0,
            "interface_complexity": 45.0,
            "algorithmic_complexity": 70.0,
            "predictability": 0.75
        }
    
    async def update_model(self, prediction, execution_results, accuracy):
        # Simplified model update
        pass


class DecompositionOptimizer:
    """Simplified ML model for decomposition optimization."""
    
    async def recommend_strategy(self, task_analysis: Dict, similar_patterns: List) -> Dict:
        complexity = task_analysis.get("complexity", {}).get("overall_score", 50)
        
        if complexity > 80:
            strategy = DecompositionStrategy.ML_OPTIMIZED
        elif complexity > 60:
            strategy = DecompositionStrategy.HYBRID
        else:
            strategy = DecompositionStrategy.SEQUENTIAL
        
        return {
            "recommended_strategy": strategy,
            "parallelization_score": min(1.0, complexity / 100.0),
            "confidence": 0.8
        }
    
    async def update_model(self, prediction, execution_results, accuracy):
        # Simplified model update
        pass


class ResourcePredictor:
    """Simplified ML model for resource prediction."""
    
    async def predict_requirements(self, task_analysis: Dict) -> Dict:
        complexity = task_analysis.get("complexity", {}).get("overall_score", 50)
        
        return {
            "cpu_cores": max(2, int(complexity / 25)),
            "memory_gb": max(4, int(complexity / 12.5)),
            "storage_gb": max(10, int(complexity / 5)),
            "network_bandwidth": "medium"
        }
    
    async def update_model(self, prediction, execution_results, accuracy):
        # Simplified model update
        pass