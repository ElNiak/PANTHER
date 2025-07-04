"""
Task Analysis Algorithm - Core Implementation
Provides comprehensive task analysis capabilities for ATLAS MCP coordination optimization.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict, Counter
import hashlib


class ComplexityLevel(Enum):
    """Task complexity levels."""
    TRIVIAL = "trivial"          # < 20 points
    SIMPLE = "simple"            # 20-40 points  
    MODERATE = "moderate"        # 40-60 points
    COMPLEX = "complex"          # 60-80 points
    VERY_COMPLEX = "very_complex" # > 80 points


class DependencyType(Enum):
    """Types of task dependencies."""
    SEQUENTIAL = "sequential"     # Must complete before next
    PARALLEL = "parallel"         # Can run concurrently
    CONDITIONAL = "conditional"   # Depends on outcome
    RESOURCE = "resource"         # Shared resource constraint
    DATA = "data"                # Data dependency


class PatternType(Enum):
    """Types of task patterns."""
    CRUD_OPERATIONS = "crud_operations"
    ANALYSIS_RESEARCH = "analysis_research"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    INTEGRATION = "integration"


@dataclass
class ComplexityFactors:
    """Factors contributing to task complexity."""
    computational_complexity: float
    cognitive_complexity: float
    integration_complexity: float
    risk_factor: float
    uncertainty_factor: float
    dependency_count: int
    estimated_duration: float


@dataclass 
class TaskDependency:
    """Represents a dependency between tasks."""
    from_task: str
    to_task: str
    dependency_type: DependencyType
    strength: float  # 0.0 to 1.0
    description: str


@dataclass
class DetectedPattern:
    """Represents a detected task pattern."""
    pattern_type: PatternType
    confidence: float
    indicators: List[str]
    optimization_suggestions: List[str]


class TaskComplexityAnalyzer:
    """
    Analyzes task complexity using multiple factors and heuristics.
    
    Provides comprehensive complexity scoring for ATLAS coordination optimization.
    """
    
    def __init__(self):
        """Initialize the task complexity analyzer."""
        
        self.logger = logging.getLogger(__name__)
        
        # Complexity indicators
        self.complexity_keywords = {
            "high": ["refactor", "migrate", "integrate", "complex", "advanced", "comprehensive"],
            "medium": ["implement", "develop", "analyze", "optimize", "enhance", "improve"],
            "low": ["fix", "update", "add", "remove", "simple", "basic", "quick"]
        }
        
        # Domain-specific complexity multipliers
        self.domain_multipliers = {
            "architecture": 1.5,
            "security": 1.4,
            "performance": 1.3,
            "integration": 1.4,
            "testing": 1.1,
            "documentation": 0.8,
            "bugfix": 0.9
        }
        
        self.logger.info("TaskComplexityAnalyzer initialized")
    
    def analyze_task_complexity(self, 
                               task_description: str,
                               context: Dict[str, Any] = None) -> ComplexityFactors:
        """
        Analyze the complexity of a given task.
        
        Args:
            task_description: Description of the task to analyze
            context: Additional context information
            
        Returns:
            ComplexityFactors containing detailed complexity analysis
        """
        
        # Input validation
        if task_description is None:
            raise ValueError("Task description cannot be None")
        if task_description == "":
            raise ValueError("Task description cannot be empty")
            
        context = context or {}
        
        # Base complexity analysis
        computational = self._analyze_computational_complexity(task_description, context)
        cognitive = self._analyze_cognitive_complexity(task_description, context)
        integration = self._analyze_integration_complexity(task_description, context)
        risk = self._assess_risk_factor(task_description, context)
        uncertainty = self._assess_uncertainty_factor(task_description, context)
        
        # Dependency analysis
        dependency_count = self._estimate_dependency_count(task_description, context)
        
        # Duration estimation
        estimated_duration = self._estimate_duration(
            computational, cognitive, integration, dependency_count
        )
        
        return ComplexityFactors(
            computational_complexity=computational,
            cognitive_complexity=cognitive,
            integration_complexity=integration,
            risk_factor=risk,
            uncertainty_factor=uncertainty,
            dependency_count=dependency_count,
            estimated_duration=estimated_duration
        )
    
    def get_complexity_level(self, factors: ComplexityFactors) -> ComplexityLevel:
        """
        Determine overall complexity level from factors.
        
        Args:
            factors: ComplexityFactors from analysis
            
        Returns:
            ComplexityLevel enum value
        """
        
        # Weighted scoring
        score = (
            factors.computational_complexity * 0.25 +
            factors.cognitive_complexity * 0.30 +
            factors.integration_complexity * 0.20 +
            factors.risk_factor * 0.15 +
            factors.uncertainty_factor * 0.10
        ) * 100
        
        # Adjust for dependencies
        score += min(factors.dependency_count * 2, 20)
        
        if score < 20:
            return ComplexityLevel.TRIVIAL
        elif score < 40:
            return ComplexityLevel.SIMPLE
        elif score < 60:
            return ComplexityLevel.MODERATE
        elif score < 80:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def _analyze_computational_complexity(self, 
                                        description: str, 
                                        context: Dict) -> float:
        """Analyze computational complexity indicators."""
        
        score = 0.0
        description_lower = description.lower()
        
        # Algorithm complexity indicators
        if any(term in description_lower for term in ["algorithm", "optimization", "search", "sort"]):
            score += 0.3
        
        # Data processing indicators
        if any(term in description_lower for term in ["process", "transform", "parse", "analyze"]):
            score += 0.2
        
        # Scale indicators
        if any(term in description_lower for term in ["large", "massive", "bulk", "batch"]):
            score += 0.3
        
        # Performance indicators
        if any(term in description_lower for term in ["performance", "optimize", "speed", "efficiency"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _analyze_cognitive_complexity(self, 
                                    description: str, 
                                    context: Dict) -> float:
        """Analyze cognitive complexity indicators."""
        
        score = 0.0
        description_lower = description.lower()
        
        # Decision complexity
        decision_words = ["if", "when", "decide", "choose", "determine", "evaluate"]
        score += min(len([w for w in decision_words if w in description_lower]) * 0.1, 0.4)
        
        # Domain complexity
        for domain, multiplier in self.domain_multipliers.items():
            if domain in description_lower:
                score += (multiplier - 1.0) * 0.5
        
        # Keyword complexity scoring
        for level, keywords in self.complexity_keywords.items():
            keyword_count = len([k for k in keywords if k in description_lower])
            if level == "high":
                score += keyword_count * 0.15
            elif level == "medium":
                score += keyword_count * 0.10
            elif level == "low":
                score += keyword_count * 0.05
        
        return min(score, 1.0)
    
    def _analyze_integration_complexity(self, 
                                      description: str, 
                                      context: Dict) -> float:
        """Analyze integration complexity indicators."""
        
        score = 0.0
        description_lower = description.lower()
        
        # Integration indicators
        integration_terms = ["integrate", "connect", "interface", "api", "service", "external"]
        score += min(len([t for t in integration_terms if t in description_lower]) * 0.15, 0.6)
        
        # System interaction indicators
        if any(term in description_lower for term in ["database", "network", "file", "system"]):
            score += 0.2
        
        # Multi-component indicators
        if any(term in description_lower for term in ["multiple", "several", "various", "different"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_risk_factor(self, description: str, context: Dict) -> float:
        """Assess risk factors in the task."""
        
        score = 0.0
        description_lower = description.lower()
        
        # High-risk operations
        risky_operations = ["migrate", "deploy", "delete", "remove", "change", "modify"]
        score += min(len([op for op in risky_operations if op in description_lower]) * 0.2, 0.6)
        
        # Production/critical indicators
        if any(term in description_lower for term in ["production", "critical", "live", "important"]):
            score += 0.3
        
        # Legacy/compatibility indicators
        if any(term in description_lower for term in ["legacy", "compatibility", "backward", "old"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_uncertainty_factor(self, description: str, context: Dict) -> float:
        """Assess uncertainty factors in the task."""
        
        score = 0.0
        description_lower = description.lower()
        
        # Uncertainty indicators
        uncertainty_terms = ["investigate", "explore", "research", "unknown", "unclear", "maybe"]
        score += min(len([t for t in uncertainty_terms if t in description_lower]) * 0.15, 0.6)
        
        # Experimental indicators
        if any(term in description_lower for term in ["experimental", "prototype", "trial", "test"]):
            score += 0.3
        
        # Requirement clarity
        if any(term in description_lower for term in ["requirements", "specification", "unclear"]):
            score += 0.2
        
        return min(score, 1.0)
    
    def _estimate_dependency_count(self, description: str, context: Dict) -> int:
        """Estimate the number of dependencies."""
        
        count = 0
        description_lower = description.lower()
        
        # Multi-step indicators
        if any(term in description_lower for term in ["first", "then", "after", "before", "next"]):
            count += 2
        
        # Integration dependencies
        if any(term in description_lower for term in ["integrate", "connect", "combine"]):
            count += 3
        
        # Testing dependencies
        if any(term in description_lower for term in ["test", "validate", "verify"]):
            count += 1
        
        # Documentation dependencies
        if any(term in description_lower for term in ["document", "write", "update"]):
            count += 1
        
        return max(count, 1)  # Minimum 1 dependency
    
    def _estimate_duration(self, 
                          computational: float,
                          cognitive: float, 
                          integration: float,
                          dependency_count: int) -> float:
        """Estimate task duration in hours."""
        
        # Base duration calculation
        base_duration = (
            computational * 4 +      # Up to 4 hours for computational complexity
            cognitive * 6 +          # Up to 6 hours for cognitive complexity
            integration * 3 +        # Up to 3 hours for integration complexity
            dependency_count * 0.5   # 30 minutes per dependency
        )
        
        return max(base_duration, 0.5)  # Minimum 30 minutes


class DependencyAnalyzer:
    """
    Analyzes dependencies between tasks and components.
    
    Provides dependency mapping and optimization for ATLAS coordination.
    """
    
    def __init__(self, task_graph: Dict[str, Any]):
        """Initialize the dependency analyzer."""
        
        self.logger = logging.getLogger(__name__)
        self.task_graph = task_graph
        self.dependencies: List[TaskDependency] = []
        
        self.logger.info("DependencyAnalyzer initialized")
    
    def analyze_dependencies(self, 
                           tasks: List[Dict[str, Any]]) -> List[TaskDependency]:
        """
        Analyze dependencies between a list of tasks.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            List of TaskDependency objects
        """
        
        dependencies = []
        
        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks):
                if i != j:
                    dependency = self._detect_dependency(task1, task2)
                    if dependency:
                        dependencies.append(dependency)
        
        self.dependencies = dependencies
        return dependencies
    
    def get_execution_order(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        Determine optimal execution order based on dependencies.
        
        Args:
            tasks: List of tasks to order
            
        Returns:
            List of task IDs in execution order
        """
        
        # Create dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        task_ids = [task.get("id", f"task_{i}") for i, task in enumerate(tasks)]
        
        for task_id in task_ids:
            in_degree[task_id] = 0
        
        for dep in self.dependencies:
            if dep.from_task in task_ids and dep.to_task in task_ids:
                graph[dep.from_task].append(dep.to_task)
                in_degree[dep.to_task] += 1
        
        # Topological sort
        queue = [task_id for task_id in task_ids if in_degree[task_id] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _detect_dependency(self, task1: Dict, task2: Dict) -> Optional[TaskDependency]:
        """Detect dependency between two tasks."""
        
        desc1 = task1.get("description", "").lower()
        desc2 = task2.get("description", "").lower()
        
        # Sequential dependencies
        if self._is_sequential_dependency(desc1, desc2):
            return TaskDependency(
                from_task=task1.get("id", "task1"),
                to_task=task2.get("id", "task2"),
                dependency_type=DependencyType.SEQUENTIAL,
                strength=0.8,
                description="Sequential execution required"
            )
        
        # Data dependencies
        if self._is_data_dependency(desc1, desc2):
            return TaskDependency(
                from_task=task1.get("id", "task1"),
                to_task=task2.get("id", "task2"),
                dependency_type=DependencyType.DATA,
                strength=0.7,
                description="Data output required as input"
            )
        
        # Resource dependencies
        if self._is_resource_dependency(desc1, desc2):
            return TaskDependency(
                from_task=task1.get("id", "task1"),
                to_task=task2.get("id", "task2"),
                dependency_type=DependencyType.RESOURCE,
                strength=0.6,
                description="Shared resource constraint"
            )
        
        return None
    
    def _is_sequential_dependency(self, desc1: str, desc2: str) -> bool:
        """Check if tasks have sequential dependency."""
        
        # Pattern: testing depends on implementation
        if "implement" in desc1 and "test" in desc2:
            return True
        
        # Pattern: deployment depends on testing
        if "test" in desc1 and "deploy" in desc2:
            return True
        
        # Pattern: documentation depends on implementation
        if "implement" in desc1 and "document" in desc2:
            return True
        
        return False
    
    def _is_data_dependency(self, desc1: str, desc2: str) -> bool:
        """Check if tasks have data dependency."""
        
        # Pattern: analysis depends on data collection
        if "collect" in desc1 and "analyze" in desc2:
            return True
        
        # Pattern: processing depends on generation
        if "generate" in desc1 and "process" in desc2:
            return True
        
        return False
    
    def _is_resource_dependency(self, desc1: str, desc2: str) -> bool:
        """Check if tasks have resource dependency."""
        
        # Pattern: both tasks access same resource
        resources = ["database", "file", "service", "api"]
        
        for resource in resources:
            if resource in desc1 and resource in desc2:
                return True
        
        return False


class PatternDetector:
    """
    Detects patterns in task descriptions and context.
    
    Provides pattern recognition for ATLAS optimization strategies.
    """
    
    def __init__(self, context: str, task_history: Dict[str, Any]):
        """Initialize the pattern detector."""
        
        self.logger = logging.getLogger(__name__)
        self.context = context
        self.task_history = task_history
        
        # Pattern definitions
        self.pattern_indicators = {
            PatternType.CRUD_OPERATIONS: ["create", "read", "update", "delete", "add", "remove", "modify"],
            PatternType.ANALYSIS_RESEARCH: ["analyze", "research", "investigate", "study", "examine"],
            PatternType.REFACTORING: ["refactor", "restructure", "reorganize", "improve", "optimize"],
            PatternType.DEBUGGING: ["debug", "fix", "resolve", "troubleshoot", "issue", "bug"],
            PatternType.TESTING: ["test", "validate", "verify", "check", "ensure"],
            PatternType.DEPLOYMENT: ["deploy", "release", "publish", "install", "configure"],
            PatternType.DOCUMENTATION: ["document", "write", "update", "readme", "guide"],
            PatternType.INTEGRATION: ["integrate", "connect", "interface", "api", "service"]
        }
        
        self.logger.info("PatternDetector initialized")
    
    def detect_patterns(self, 
                       task_description: str,
                       context: Dict[str, Any] = None) -> List[DetectedPattern]:
        """
        Detect patterns in the given task description.
        
        Args:
            task_description: Description to analyze
            context: Additional context
            
        Returns:
            List of DetectedPattern objects
        """
        
        context = context or {}
        patterns = []
        description_lower = task_description.lower()
        
        for pattern_type, indicators in self.pattern_indicators.items():
            confidence = self._calculate_pattern_confidence(description_lower, indicators)
            
            if confidence > 0.3:  # Threshold for pattern detection
                pattern = DetectedPattern(
                    pattern_type=pattern_type,
                    confidence=confidence,
                    indicators=[ind for ind in indicators if ind in description_lower],
                    optimization_suggestions=self._get_optimization_suggestions(pattern_type)
                )
                patterns.append(pattern)
        
        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return patterns
    
    def _calculate_pattern_confidence(self, 
                                    description: str, 
                                    indicators: List[str]) -> float:
        """Calculate confidence for pattern detection."""
        
        matched_indicators = [ind for ind in indicators if ind in description]
        
        if not matched_indicators:
            return 0.0
        
        # Base confidence from indicator matches
        base_confidence = len(matched_indicators) / len(indicators)
        
        # Boost confidence for multiple matches
        if len(matched_indicators) > 1:
            base_confidence *= 1.2
        
        # Context relevance boost
        if self.context and any(ind in self.context.lower() for ind in matched_indicators):
            base_confidence *= 1.1
        
        return min(base_confidence, 1.0)
    
    def _extract_technical_keywords(self, description: str) -> List[str]:
        """Extract technical keywords from task description."""
        import re
        
        # Common technical keywords
        technical_terms = [
            'api', 'database', 'authentication', 'microservices', 'docker',
            'kubernetes', 'rest', 'graphql', 'frontend', 'backend',
            'testing', 'deployment', 'monitoring', 'logging', 'security',
            'performance', 'optimization', 'refactor', 'migration',
            'integration', 'automation', 'ci/cd', 'devops'
        ]
        
        description_lower = description.lower()
        keywords = []
        
        for term in technical_terms:
            if re.search(r'\b' + term + r'\b', description_lower):
                keywords.append(term)
                
        return keywords
    
    def _get_optimization_suggestions(self, pattern_type: PatternType) -> List[str]:
        """Get optimization suggestions for detected pattern."""
        
        suggestions = {
            PatternType.CRUD_OPERATIONS: [
                "Consider batch operations for multiple items",
                "Use database transactions for consistency",
                "Implement caching for read operations"
            ],
            PatternType.ANALYSIS_RESEARCH: [
                "Use parallel processing for data analysis",
                "Implement incremental analysis for large datasets",
                "Cache intermediate results"
            ],
            PatternType.REFACTORING: [
                "Use semantic analysis tools before changes",
                "Implement comprehensive testing",
                "Plan for rollback mechanisms"
            ],
            PatternType.DEBUGGING: [
                "Use systematic debugging approach",
                "Implement comprehensive logging",
                "Consider automated testing"
            ],
            PatternType.TESTING: [
                "Implement test automation",
                "Use parallel test execution",
                "Consider property-based testing"
            ],
            PatternType.DEPLOYMENT: [
                "Use blue-green deployment",
                "Implement health checks",
                "Plan rollback strategy"
            ],
            PatternType.DOCUMENTATION: [
                "Use automated documentation generation",
                "Implement documentation testing",
                "Consider interactive examples"
            ],
            PatternType.INTEGRATION: [
                "Use async communication patterns",
                "Implement circuit breakers",
                "Plan for failure scenarios"
            ]
        }
        
        return suggestions.get(pattern_type, ["Consider pattern-specific optimizations"])


class ExecutionOptimizer:
    """
    Optimizes task execution strategies based on analysis results.
    
    Provides optimization recommendations for ATLAS coordination.
    """
    
    def __init__(self):
        """Initialize the execution optimizer."""
        
        self.logger = logging.getLogger(__name__)
        self.optimization_strategies = {}
        
        self.logger.info("ExecutionOptimizer initialized")
    
    def optimize_execution(self, 
                         task_description: str,
                         complexity_factors: ComplexityFactors,
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize task execution based on complexity and context.
        
        Args:
            task_description: Task description
            complexity_factors: Task complexity analysis
            context: Additional context
            
        Returns:
            Optimization strategy dictionary
        """
        return {
            "execution_mode": self._determine_execution_mode(complexity_factors),
            "parallelization": self._assess_parallelization([]),
            "resource_allocation": self._optimize_resources(complexity_factors),
            "caching_strategy": self._determine_caching([]),
            "monitoring_level": self._determine_monitoring(complexity_factors),
            "optimization_score": self._calculate_optimization_score(
                complexity_factors, [], []
            )
        }
    
    def optimize_execution_strategy(self,
                                  complexity_factors: ComplexityFactors,
                                  dependencies: List[TaskDependency],
                                  patterns: List[DetectedPattern]) -> Dict[str, Any]:
        """
        Generate optimized execution strategy.
        
        Args:
            complexity_factors: Task complexity analysis
            dependencies: Task dependencies
            patterns: Detected patterns
            
        Returns:
            Optimization strategy dictionary
        """
        
        strategy = {
            "execution_mode": self._determine_execution_mode(complexity_factors),
            "parallelization": self._assess_parallelization(dependencies),
            "resource_allocation": self._optimize_resources(complexity_factors),
            "caching_strategy": self._determine_caching(patterns),
            "monitoring_level": self._determine_monitoring(complexity_factors),
            "fallback_strategy": self._plan_fallback(complexity_factors),
            "optimization_score": self._calculate_optimization_score(
                complexity_factors, dependencies, patterns
            )
        }
        
        return strategy
    
    def _determine_execution_mode(self, factors: ComplexityFactors) -> str:
        """Determine optimal execution mode."""
        
        if factors.computational_complexity > 0.7:
            return "distributed"
        elif factors.integration_complexity > 0.6:
            return "staged"
        elif factors.risk_factor > 0.7:
            return "cautious"
        else:
            return "standard"
    
    def _assess_parallelization(self, dependencies: List[TaskDependency]) -> Dict[str, Any]:
        """Assess parallelization opportunities."""
        
        parallel_deps = [d for d in dependencies if d.dependency_type == DependencyType.PARALLEL]
        sequential_deps = [d for d in dependencies if d.dependency_type == DependencyType.SEQUENTIAL]
        
        return {
            "parallel_potential": len(parallel_deps) / max(len(dependencies), 1),
            "sequential_constraints": len(sequential_deps),
            "recommended_concurrency": min(len(parallel_deps) + 1, 4)
        }
    
    def _optimize_resources(self, factors: ComplexityFactors) -> Dict[str, Any]:
        """Optimize resource allocation."""
        
        return {
            "cpu_priority": "high" if factors.computational_complexity > 0.6 else "normal",
            "memory_allocation": "large" if factors.integration_complexity > 0.7 else "normal",
            "timeout_multiplier": 1.5 if factors.uncertainty_factor > 0.6 else 1.0,
            "retry_strategy": "exponential" if factors.risk_factor > 0.5 else "linear"
        }
    
    def _determine_caching(self, patterns: List[DetectedPattern]) -> Dict[str, Any]:
        """Determine caching strategy."""
        
        cache_beneficial_patterns = [
            PatternType.CRUD_OPERATIONS,
            PatternType.ANALYSIS_RESEARCH
        ]
        
        should_cache = any(
            p.pattern_type in cache_beneficial_patterns and p.confidence > 0.5
            for p in patterns
        )
        
        return {
            "enable_caching": should_cache,
            "cache_duration": "1h" if should_cache else "none",
            "cache_invalidation": "time_based" if should_cache else "none"
        }
    
    def _determine_monitoring(self, factors: ComplexityFactors) -> str:
        """Determine monitoring level."""
        
        risk_score = (factors.risk_factor + factors.uncertainty_factor) / 2
        
        if risk_score > 0.7:
            return "detailed"
        elif risk_score > 0.4:
            return "standard"
        else:
            return "minimal"
    
    def _plan_fallback(self, factors: ComplexityFactors) -> Dict[str, Any]:
        """Plan fallback strategy."""
        
        return {
            "checkpoint_frequency": "high" if factors.risk_factor > 0.6 else "normal",
            "rollback_capability": factors.risk_factor > 0.5,
            "alternative_approach": factors.uncertainty_factor > 0.7,
            "manual_intervention": factors.cognitive_complexity > 0.8
        }
    
    def _calculate_optimization_score(self,
                                    factors: ComplexityFactors,
                                    dependencies: List[TaskDependency],
                                    patterns: List[DetectedPattern]) -> float:
        """Calculate overall optimization score."""
        
        # Base score from complexity reduction
        complexity_score = 1.0 - (
            factors.computational_complexity * 0.3 +
            factors.cognitive_complexity * 0.3 +
            factors.integration_complexity * 0.2 +
            factors.risk_factor * 0.2
        )
        
        # Boost from parallelization
        parallel_boost = len([d for d in dependencies if d.dependency_type == DependencyType.PARALLEL]) * 0.1
        
        # Boost from pattern optimization
        pattern_boost = sum(p.confidence for p in patterns) * 0.1
        
        return min(complexity_score + parallel_boost + pattern_boost, 1.0)


def analyze_task_for_atlas_framework(task_description: str, 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Comprehensive task analysis for ATLAS framework integration.
    
    Args:
        task_description: Description of the task to analyze
        context: Additional context information
        
    Returns:
        Complete analysis results for ATLAS coordination
    """
    
    context = context or {}
    
    # Initialize analyzers
    complexity_analyzer = TaskComplexityAnalyzer()
    dependency_analyzer = DependencyAnalyzer(context.get("task_graph", {}))
    pattern_detector = PatternDetector(
        context.get("context", ""),
        context.get("task_history", {})
    )
    execution_optimizer = ExecutionOptimizer()
    
    # Perform analysis
    complexity_factors = complexity_analyzer.analyze_task_complexity(task_description, context)
    complexity_level = complexity_analyzer.get_complexity_level(complexity_factors)
    
    # Create dummy tasks for dependency analysis if not provided
    tasks = context.get("tasks", [{"id": "main_task", "description": task_description}])
    dependencies = dependency_analyzer.analyze_dependencies(tasks)
    execution_order = dependency_analyzer.get_execution_order(tasks)
    
    patterns = pattern_detector.detect_patterns(task_description, context)
    optimization_strategy = execution_optimizer.optimize_execution_strategy(
        complexity_factors, dependencies, patterns
    )
    
    # Generate comprehensive analysis
    analysis = {
        "task_description": task_description,
        "complexity": {
            "factors": asdict(complexity_factors),
            "level": complexity_level.value,
            "overall_score": (
                complexity_factors.computational_complexity * 0.25 +
                complexity_factors.cognitive_complexity * 0.30 +
                complexity_factors.integration_complexity * 0.20 +
                complexity_factors.risk_factor * 0.15 +
                complexity_factors.uncertainty_factor * 0.10
            ) * 100
        },
        "dependencies": {
            "count": len(dependencies),
            "types": [d.dependency_type.value for d in dependencies],
            "execution_order": execution_order,
            "details": [asdict(d) for d in dependencies]
        },
        "patterns": {
            "detected": [asdict(p) for p in patterns],
            "primary_pattern": patterns[0].pattern_type.value if patterns else "unknown",
            "confidence": patterns[0].confidence if patterns else 0.0
        },
        "optimization": optimization_strategy,
        "recommendations": {
            "coordination_strategy": _generate_coordination_recommendations(
                complexity_level, patterns, dependencies
            ),
            "atlas_tools": _recommend_atlas_tools(patterns, complexity_factors),
            "execution_priority": _determine_execution_priority(complexity_factors)
        },
        "metadata": {
            "analysis_timestamp": datetime.now().isoformat(),
            "analyzer_version": "1.0.0",
            "task_signature": _generate_task_signature(task_description)
        }
    }
    
    return analysis


def _generate_coordination_recommendations(complexity_level: ComplexityLevel,
                                         patterns: List[DetectedPattern],
                                         dependencies: List[TaskDependency]) -> List[str]:
    """Generate coordination strategy recommendations."""
    
    recommendations = []
    
    # Complexity-based recommendations
    if complexity_level in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
        recommendations.append("Use stateful workflow orchestration for complex coordination")
        recommendations.append("Implement comprehensive monitoring and checkpointing")
    
    # Pattern-based recommendations
    if patterns:
        primary_pattern = patterns[0].pattern_type
        if primary_pattern == PatternType.INTEGRATION:
            recommendations.append("Use saga pattern for distributed transactions")
        elif primary_pattern == PatternType.ANALYSIS_RESEARCH:
            recommendations.append("Implement parallel processing with result aggregation")
    
    # Dependency-based recommendations
    parallel_deps = [d for d in dependencies if d.dependency_type == DependencyType.PARALLEL]
    if len(parallel_deps) > 2:
        recommendations.append("Enable concurrent execution with dependency management")
    
    return recommendations


def _recommend_atlas_tools(patterns: List[DetectedPattern], 
                          factors: ComplexityFactors) -> List[str]:
    """Recommend specific ATLAS tools based on analysis."""
    
    tools = []
    
    # Pattern-based tool recommendations
    for pattern in patterns:
        if pattern.pattern_type == PatternType.ANALYSIS_RESEARCH:
            tools.extend(["semantic_search_activation", "memory_graph_analysis"])
        elif pattern.pattern_type == PatternType.REFACTORING:
            tools.extend(["code_standards_validation", "dependency_analysis"])
        elif pattern.pattern_type == PatternType.TESTING:
            tools.extend(["test_automation", "validation_pipeline"])
    
    # Complexity-based tool recommendations
    if factors.integration_complexity > 0.6:
        tools.append("integration_monitoring")
    
    if factors.risk_factor > 0.7:
        tools.append("risk_mitigation_pipeline")
    
    return list(set(tools))  # Remove duplicates


def _determine_execution_priority(factors: ComplexityFactors) -> str:
    """Determine execution priority based on complexity factors."""
    
    urgency_score = factors.risk_factor * 0.4 + factors.uncertainty_factor * 0.3 + factors.integration_complexity * 0.3
    
    if urgency_score > 0.7:
        return "high"
    elif urgency_score > 0.4:
        return "medium"
    else:
        return "low"


def _generate_task_signature(task_description: str) -> str:
    """Generate a unique signature for the task."""
    
    # Create normalized representation
    normalized = re.sub(r'[^\w\s]', '', task_description.lower())
    normalized = ' '.join(normalized.split())
    
    # Generate hash
    return hashlib.md5(normalized.encode()).hexdigest()[:16]