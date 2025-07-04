"""
Semantic Search Capabilities Activator
Implements intelligent activation of semantic search tools based on governance analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .enforcement_pipeline import (
    GovernanceEnforcementPipeline,
    GovernanceLevel, 
    ViolationType,
    ActivationTrigger,
    ActivationResult
)
from .atlas_feature_activator import AtlasFeatureActivator, AtlasFeatureMapping


class SemanticSearchTrigger(Enum):
    """Triggers for semantic search activation."""
    KNOWLEDGE_BASE_SIZE = "knowledge_base_size"
    PATTERN_COMPLEXITY = "pattern_complexity"
    DISCOVERY_PATTERNS = "discovery_patterns"
    TASK_SIMILARITY = "task_similarity"
    CONCEPT_DENSITY = "concept_density"
    RESEARCH_WORKFLOW = "research_workflow"


class SearchCapability(Enum):
    """Types of semantic search capabilities."""
    SIMILAR_TASKS = "search_similar_tasks"
    RELATED_CONCEPTS = "discover_related_concepts"
    PATTERN_DISCOVERY = "discover_patterns"
    KNOWLEDGE_GRAPH = "search_knowledge_graph"
    CONTEXTUAL_SEARCH = "contextual_search"


@dataclass
class SearchActivationContext:
    """Context for semantic search activation decisions."""
    knowledge_base_size: int = 0
    concept_density: float = 0.0
    pattern_complexity: float = 0.0
    task_history_size: int = 0
    discovery_patterns: List[str] = None
    current_workflow: str = "unknown"
    user_experience_level: str = "intermediate"
    
    def __post_init__(self):
        if self.discovery_patterns is None:
            self.discovery_patterns = []


@dataclass
class SemanticSearchResult:
    """Result of semantic search activation."""
    capability: SearchCapability
    activation_successful: bool
    activation_reason: str
    confidence_score: float
    expected_value: float
    usage_patterns: List[str]
    integration_complexity: str
    performance_metrics: Dict[str, float]


class SemanticSearchActivator:
    """
    Activates semantic search capabilities based on governance triggers and context analysis.
    
    Implements intelligent activation for underutilized semantic search tools:
    - search_similar_tasks: 35% expected adoption increase
    - discover_related_concepts: 20% expected adoption increase
    - Pattern discovery capabilities: 40% expected adoption increase
    """
    
    def __init__(self, storage_path: str = None):
        """Initialize the semantic search activator."""
        
        self.governance_pipeline = GovernanceEnforcementPipeline(storage_path)
        self.atlas_activator = AtlasFeatureActivator(storage_path)
        self.logger = logging.getLogger(__name__)
        
        # Semantic search capability mappings
        self.search_capabilities = self._initialize_search_capabilities()
        
        # Activation history and performance tracking
        self.activation_history: List[Dict] = []
        self.performance_metrics: Dict[str, Dict] = {}
        
        # Configuration for semantic search activation
        self.config = {
            "knowledge_base_threshold": 50,      # Minimum knowledge base size
            "concept_density_threshold": 0.3,    # Minimum concept density
            "pattern_complexity_threshold": 0.6, # Minimum pattern complexity
            "task_history_threshold": 10,        # Minimum task history size
            "confidence_threshold": 0.7,         # Minimum confidence for activation
            "discovery_pattern_boost": 0.2,      # Boost for discovery patterns
            "research_workflow_boost": 0.3       # Boost for research workflows
        }
        
        self.logger.info("SemanticSearchActivator initialized with semantic search capabilities")
    
    async def activate_semantic_search_intelligently(self, 
                                                   context: Dict = None,
                                                   force_activation: bool = False) -> Dict[str, SemanticSearchResult]:
        """
        Intelligently activate semantic search capabilities based on context analysis.
        
        Args:
            context: Project and task context for activation decisions
            force_activation: Force activation of all applicable capabilities
            
        Returns:
            Dictionary of activation results by capability name
        """
        
        self.logger.info("Starting intelligent semantic search activation")
        
        try:
            # Step 1: Analyze activation context
            search_context = await self._analyze_search_activation_context(context)
            
            # Step 2: Identify activation candidates
            candidates = await self._identify_search_activation_candidates(
                search_context, force_activation
            )
            
            # Step 3: Execute capability activations
            activation_results = {}
            
            for capability, activation_data in candidates.items():
                try:
                    result = await self._activate_search_capability(
                        capability, activation_data, search_context
                    )
                    activation_results[capability.value] = result
                    
                    # Update performance metrics
                    await self._update_search_performance_metrics(capability, result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to activate search capability {capability.value}: {str(e)}")
                    activation_results[capability.value] = SemanticSearchResult(
                        capability=capability,
                        activation_successful=False,
                        activation_reason=f"Activation failed: {str(e)}",
                        confidence_score=0.0,
                        expected_value=0.0,
                        usage_patterns=[],
                        integration_complexity="unknown",
                        performance_metrics={}
                    )
            
            # Step 4: Calculate overall semantic search adoption improvement
            adoption_improvement = await self._calculate_search_adoption_metrics(activation_results)
            
            # Step 5: Store activation history
            activation_record = {
                "timestamp": datetime.now().isoformat(),
                "context": search_context.__dict__,
                "capabilities_activated": len([r for r in activation_results.values() if r.activation_successful]),
                "total_candidates": len(candidates),
                "adoption_improvement": adoption_improvement.get("adoption_improvement", 0.0),
                "average_confidence": adoption_improvement.get("average_confidence", 0.0)
            }
            self.activation_history.append(activation_record)
            
            self.logger.info(
                f"Semantic search activation complete: {len(activation_results)} capabilities processed, "
                f"{adoption_improvement.get('adoption_improvement', 0.0):.1%} adoption improvement"
            )
            
            return activation_results
            
        except Exception as e:
            self.logger.error(f"Semantic search activation failed: {str(e)}")
            return {}
    
    async def discover_semantic_search_opportunities(self, 
                                                   project_context: Dict = None) -> Dict[str, Dict]:
        """
        Discover opportunities for activating semantic search capabilities.
        
        Args:
            project_context: Project context for opportunity analysis
            
        Returns:
            Dictionary of search capabilities with activation opportunities
        """
        
        self.logger.info("Discovering semantic search activation opportunities")
        
        try:
            # Analyze current context
            search_context = await self._analyze_search_activation_context(project_context)
            
            # Evaluate each search capability
            opportunities = {}
            
            for capability, capability_config in self.search_capabilities.items():
                # Calculate activation potential
                potential_score = await self._calculate_search_activation_potential(
                    capability, capability_config, search_context
                )
                
                if potential_score["potential_score"] > 0.5:  # 50% potential threshold
                    opportunities[capability.value] = {
                        "activation_potential": potential_score,
                        "capability_config": capability_config,
                        "current_usage": await self._get_current_search_usage(capability),
                        "recommended_triggers": potential_score["recommended_triggers"],
                        "expected_adoption_increase": potential_score["expected_adoption"],
                        "integration_complexity": capability_config["integration_complexity"],
                        "value_proposition": potential_score["value_proposition"]
                    }
            
            # Sort by activation potential
            sorted_opportunities = dict(
                sorted(opportunities.items(), 
                      key=lambda x: x[1]["activation_potential"]["potential_score"], 
                      reverse=True)
            )
            
            self.logger.info(f"Discovered {len(sorted_opportunities)} semantic search opportunities")
            
            return sorted_opportunities
            
        except Exception as e:
            self.logger.error(f"Semantic search opportunity discovery failed: {str(e)}")
            return {}
    
    async def get_semantic_search_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive semantic search activation dashboard."""
        
        try:
            # Current capabilities status
            capabilities_status = {}
            for capability in SearchCapability:
                capabilities_status[capability.value] = {
                    "currently_active": capability.value in self.performance_metrics,
                    "performance_metrics": self.performance_metrics.get(capability.value, {}),
                    "activation_count": len([
                        h for h in self.activation_history 
                        if capability.value in h.get("capabilities_activated", [])
                    ])
                }
            
            # Calculate overall metrics
            total_capabilities = len(SearchCapability)
            active_capabilities = len([
                c for c in capabilities_status.values() 
                if c["currently_active"]
            ])
            
            # Recent activation trends
            recent_activations = self.activation_history[-10:] if self.activation_history else []
            
            dashboard = {
                "overview": {
                    "total_search_capabilities": total_capabilities,
                    "currently_active": active_capabilities,
                    "activation_rate": active_capabilities / total_capabilities if total_capabilities > 0 else 0.0,
                    "average_confidence": self._calculate_average_confidence(),
                    "total_activations": len(self.activation_history)
                },
                "capabilities_status": capabilities_status,
                "recent_activations": recent_activations,
                "performance_summary": await self._generate_performance_summary(),
                "activation_opportunities": await self.discover_semantic_search_opportunities(),
                "recommendations": await self._generate_search_activation_recommendations(),
                "success_metrics": {
                    "search_similar_tasks_adoption": self._get_capability_adoption("search_similar_tasks"),
                    "discover_related_concepts_adoption": self._get_capability_adoption("discover_related_concepts"),
                    "overall_search_effectiveness": self._calculate_search_effectiveness()
                }
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Failed to generate semantic search dashboard: {str(e)}")
            return {"error": str(e)}
    
    # Private helper methods
    
    def _initialize_search_capabilities(self) -> Dict[SearchCapability, Dict]:
        """Initialize semantic search capability configurations."""
        
        capabilities = {}
        
        # Similar Tasks Search
        capabilities[SearchCapability.SIMILAR_TASKS] = {
            "activation_conditions": {
                "min_task_history_size": 10,
                "min_pattern_complexity": 0.6,
                "required_patterns": ["analysis", "research", "troubleshooting"]
            },
            "expected_adoption_increase": 0.35,  # 35% increase
            "integration_complexity": "medium",
            "value_proposition": "Find similar past tasks to accelerate problem-solving",
            "trigger_weights": {
                SemanticSearchTrigger.TASK_SIMILARITY: 0.4,
                SemanticSearchTrigger.PATTERN_COMPLEXITY: 0.3,
                SemanticSearchTrigger.RESEARCH_WORKFLOW: 0.3
            }
        }
        
        # Related Concepts Discovery
        capabilities[SearchCapability.RELATED_CONCEPTS] = {
            "activation_conditions": {
                "min_knowledge_base_size": 50,
                "min_concept_density": 0.3,
                "required_patterns": ["research", "analysis", "exploration"]
            },
            "expected_adoption_increase": 0.20,  # 20% increase
            "integration_complexity": "high",
            "value_proposition": "Discover related concepts to enhance understanding",
            "trigger_weights": {
                SemanticSearchTrigger.KNOWLEDGE_BASE_SIZE: 0.4,
                SemanticSearchTrigger.CONCEPT_DENSITY: 0.3,
                SemanticSearchTrigger.DISCOVERY_PATTERNS: 0.3
            }
        }
        
        # Pattern Discovery
        capabilities[SearchCapability.PATTERN_DISCOVERY] = {
            "activation_conditions": {
                "min_pattern_complexity": 0.7,
                "min_task_history_size": 15,
                "required_workflows": ["research", "analysis", "debugging"]
            },
            "expected_adoption_increase": 0.40,  # 40% increase
            "integration_complexity": "high",
            "value_proposition": "Automatically discover patterns in complex tasks",
            "trigger_weights": {
                SemanticSearchTrigger.PATTERN_COMPLEXITY: 0.5,
                SemanticSearchTrigger.DISCOVERY_PATTERNS: 0.3,
                SemanticSearchTrigger.RESEARCH_WORKFLOW: 0.2
            }
        }
        
        # Knowledge Graph Search
        capabilities[SearchCapability.KNOWLEDGE_GRAPH] = {
            "activation_conditions": {
                "min_knowledge_base_size": 100,
                "min_concept_density": 0.4,
                "required_patterns": ["research", "knowledge_management"]
            },
            "expected_adoption_increase": 0.25,  # 25% increase
            "integration_complexity": "high",
            "value_proposition": "Search and traverse knowledge relationships",
            "trigger_weights": {
                SemanticSearchTrigger.KNOWLEDGE_BASE_SIZE: 0.5,
                SemanticSearchTrigger.CONCEPT_DENSITY: 0.3,
                SemanticSearchTrigger.RESEARCH_WORKFLOW: 0.2
            }
        }
        
        # Contextual Search
        capabilities[SearchCapability.CONTEXTUAL_SEARCH] = {
            "activation_conditions": {
                "min_pattern_complexity": 0.5,
                "min_task_history_size": 8,
                "user_experience_level": ["intermediate", "advanced"]
            },
            "expected_adoption_increase": 0.30,  # 30% increase
            "integration_complexity": "medium",
            "value_proposition": "Context-aware search across all project artifacts",
            "trigger_weights": {
                SemanticSearchTrigger.PATTERN_COMPLEXITY: 0.4,
                SemanticSearchTrigger.TASK_SIMILARITY: 0.3,
                SemanticSearchTrigger.DISCOVERY_PATTERNS: 0.3
            }
        }
        
        return capabilities
    
    async def _analyze_search_activation_context(self, context: Dict = None) -> SearchActivationContext:
        """Analyze context to determine appropriate search capability activations."""
        
        search_context = SearchActivationContext()
        
        if context:
            # Extract task analysis information
            if "task_analysis" in context:
                task_analysis = context["task_analysis"]
                if "complexity" in task_analysis:
                    search_context.pattern_complexity = task_analysis["complexity"].get("overall_score", 0) / 100.0
                
                if "patterns" in task_analysis:
                    search_context.discovery_patterns = [task_analysis["patterns"].get("primary_pattern", "")]
            
            # Extract project context
            if "project_context" in context:
                project_context = context["project_context"]
                search_context.current_workflow = project_context.get("workflow", "unknown")
                search_context.user_experience_level = project_context.get("user_experience_level", "intermediate")
            
            # Extract knowledge base information
            if "knowledge_base" in context:
                kb_info = context["knowledge_base"]
                search_context.knowledge_base_size = kb_info.get("total_concepts", 0)
                search_context.concept_density = kb_info.get("concept_density", 0.0)
            
            # Extract task history
            if "task_history" in context:
                search_context.task_history_size = len(context["task_history"])
        
        # Get additional context from memory manager
        try:
            memory_stats = await self._get_memory_statistics()
            search_context.knowledge_base_size = max(
                search_context.knowledge_base_size, 
                memory_stats.get("total_entities", 0)
            )
            if memory_stats.get("concept_density"):
                search_context.concept_density = memory_stats["concept_density"]
        except Exception as e:
            self.logger.debug(f"Could not get memory statistics: {str(e)}")
        
        return search_context
    
    async def _identify_search_activation_candidates(self, 
                                                   search_context: SearchActivationContext,
                                                   force_activation: bool = False) -> Dict[SearchCapability, Dict]:
        """Identify search capabilities that should be activated based on context."""
        
        candidates = {}
        
        for capability, config in self.search_capabilities.items():
            activation_score = await self._calculate_activation_score(
                capability, config, search_context
            )
            
            if activation_score > self.config["confidence_threshold"] or force_activation:
                candidates[capability] = {
                    "activation_score": activation_score,
                    "activation_reason": self._generate_activation_reason(
                        capability, config, search_context, activation_score
                    ),
                    "expected_value": config["expected_adoption_increase"] * activation_score,
                    "capability_config": config
                }
        
        return candidates
    
    async def _activate_search_capability(self, 
                                        capability: SearchCapability,
                                        activation_data: Dict,
                                        context: SearchActivationContext) -> SemanticSearchResult:
        """Activate a specific semantic search capability."""
        
        self.logger.info(f"Activating search capability: {capability.value}")
        
        try:
            config = activation_data["capability_config"]
            activation_score = activation_data["activation_score"]
            
            # Simulate capability activation (in real implementation, this would integrate with actual tools)
            activation_successful = True
            
            # Calculate performance metrics
            performance_metrics = {
                "activation_time": datetime.now().timestamp(),
                "activation_score": activation_score,
                "expected_usage_frequency": activation_score * 0.8,
                "integration_complexity_score": self._calculate_complexity_score(
                    config["integration_complexity"]
                ),
                "value_score": activation_data["expected_value"]
            }
            
            # Determine usage patterns
            usage_patterns = self._determine_usage_patterns(capability, context)
            
            result = SemanticSearchResult(
                capability=capability,
                activation_successful=activation_successful,
                activation_reason=activation_data["activation_reason"],
                confidence_score=activation_score,
                expected_value=activation_data["expected_value"],
                usage_patterns=usage_patterns,
                integration_complexity=config["integration_complexity"],
                performance_metrics=performance_metrics
            )
            
            self.logger.info(
                f"Search capability {capability.value} activation: "
                f"{'successful' if activation_successful else 'failed'} "
                f"(confidence: {activation_score:.2f})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Search capability activation failed for {capability.value}: {str(e)}")
            return SemanticSearchResult(
                capability=capability,
                activation_successful=False,
                activation_reason=f"Activation failed: {str(e)}",
                confidence_score=0.0,
                expected_value=0.0,
                usage_patterns=[],
                integration_complexity="unknown",
                performance_metrics={}
            )
    
    async def _calculate_activation_score(self, 
                                        capability: SearchCapability,
                                        config: Dict,
                                        context: SearchActivationContext) -> float:
        """Calculate activation score for a search capability."""
        
        score = 0.0
        conditions = config["activation_conditions"]
        trigger_weights = config["trigger_weights"]
        
        # Check knowledge base size
        if "min_knowledge_base_size" in conditions:
            if context.knowledge_base_size >= conditions["min_knowledge_base_size"]:
                weight = trigger_weights.get(SemanticSearchTrigger.KNOWLEDGE_BASE_SIZE, 0.0)
                score += weight * (context.knowledge_base_size / conditions["min_knowledge_base_size"])
        
        # Check concept density
        if "min_concept_density" in conditions:
            if context.concept_density >= conditions["min_concept_density"]:
                weight = trigger_weights.get(SemanticSearchTrigger.CONCEPT_DENSITY, 0.0)
                score += weight * (context.concept_density / conditions["min_concept_density"])
        
        # Check pattern complexity
        if "min_pattern_complexity" in conditions:
            if context.pattern_complexity >= conditions["min_pattern_complexity"]:
                weight = trigger_weights.get(SemanticSearchTrigger.PATTERN_COMPLEXITY, 0.0)
                score += weight * (context.pattern_complexity / conditions["min_pattern_complexity"])
        
        # Check task history size
        if "min_task_history_size" in conditions:
            if context.task_history_size >= conditions["min_task_history_size"]:
                weight = trigger_weights.get(SemanticSearchTrigger.TASK_SIMILARITY, 0.0)
                score += weight * (context.task_history_size / conditions["min_task_history_size"])
        
        # Check discovery patterns
        if "required_patterns" in conditions:
            matching_patterns = set(context.discovery_patterns) & set(conditions["required_patterns"])
            if matching_patterns:
                weight = trigger_weights.get(SemanticSearchTrigger.DISCOVERY_PATTERNS, 0.0)
                score += weight * (len(matching_patterns) / len(conditions["required_patterns"]))
        
        # Check workflow patterns
        if "required_workflows" in conditions:
            if context.current_workflow in conditions["required_workflows"]:
                weight = trigger_weights.get(SemanticSearchTrigger.RESEARCH_WORKFLOW, 0.0)
                score += weight
        
        # Apply boosts
        if "research" in context.discovery_patterns:
            score += self.config["research_workflow_boost"]
        
        if context.current_workflow in ["research", "analysis"]:
            score += self.config["discovery_pattern_boost"]
        
        return min(1.0, score)  # Cap at 1.0
    
    def _generate_activation_reason(self, 
                                   capability: SearchCapability,
                                   config: Dict,
                                   context: SearchActivationContext,
                                   score: float) -> str:
        """Generate human-readable activation reason."""
        
        reasons = []
        
        if context.knowledge_base_size > 50:
            reasons.append(f"knowledge base size ({context.knowledge_base_size})")
        
        if context.pattern_complexity > 0.6:
            reasons.append(f"pattern complexity ({context.pattern_complexity:.1%})")
        
        if context.task_history_size > 10:
            reasons.append(f"task history ({context.task_history_size} tasks)")
        
        if "research" in context.discovery_patterns:
            reasons.append("research workflow detected")
        
        if context.concept_density > 0.3:
            reasons.append(f"concept density ({context.concept_density:.1%})")
        
        reason_text = " + ".join(reasons) if reasons else "threshold conditions met"
        
        return f"{capability.value} activated: {reason_text} (confidence: {score:.1%})"
    
    def _determine_usage_patterns(self, 
                                 capability: SearchCapability,
                                 context: SearchActivationContext) -> List[str]:
        """Determine expected usage patterns for a capability."""
        
        patterns = []
        
        # Based on capability type
        if capability == SearchCapability.SIMILAR_TASKS:
            patterns.extend(["problem_solving", "troubleshooting", "pattern_matching"])
        elif capability == SearchCapability.RELATED_CONCEPTS:
            patterns.extend(["concept_exploration", "knowledge_discovery", "research"])
        elif capability == SearchCapability.PATTERN_DISCOVERY:
            patterns.extend(["pattern_analysis", "trend_identification", "automation"])
        elif capability == SearchCapability.KNOWLEDGE_GRAPH:
            patterns.extend(["relationship_mapping", "knowledge_navigation", "discovery"])
        elif capability == SearchCapability.CONTEXTUAL_SEARCH:
            patterns.extend(["contextual_retrieval", "smart_search", "adaptive_filtering"])
        
        # Based on context
        if "research" in context.discovery_patterns:
            patterns.append("research_workflow")
        
        if context.pattern_complexity > 0.7:
            patterns.append("complex_analysis")
        
        if context.user_experience_level == "advanced":
            patterns.append("power_user_features")
        
        return list(set(patterns))  # Remove duplicates
    
    def _calculate_complexity_score(self, complexity: str) -> float:
        """Calculate numerical complexity score."""
        complexity_map = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.9
        }
        return complexity_map.get(complexity, 0.5)
    
    async def _update_search_performance_metrics(self, 
                                               capability: SearchCapability,
                                               result: SemanticSearchResult):
        """Update performance metrics for a search capability."""
        
        if capability.value not in self.performance_metrics:
            self.performance_metrics[capability.value] = {
                "activation_count": 0,
                "success_count": 0,
                "total_confidence": 0.0,
                "total_expected_value": 0.0,
                "usage_patterns": []
            }
        
        metrics = self.performance_metrics[capability.value]
        metrics["activation_count"] += 1
        
        if result.activation_successful:
            metrics["success_count"] += 1
            metrics["total_confidence"] += result.confidence_score
            metrics["total_expected_value"] += result.expected_value
            
            # Update usage patterns
            for pattern in result.usage_patterns:
                if pattern not in metrics["usage_patterns"]:
                    metrics["usage_patterns"].append(pattern)
    
    async def _calculate_search_adoption_metrics(self, 
                                               activation_results: Dict[str, SemanticSearchResult]) -> Dict[str, float]:
        """Calculate comprehensive search adoption metrics."""
        
        total_capabilities = len(self.search_capabilities)
        successful_activations = len([r for r in activation_results.values() if r.activation_successful])
        
        # Calculate adoption improvement
        adoption_improvement = successful_activations / total_capabilities if total_capabilities > 0 else 0.0
        
        # Calculate average confidence
        confidences = [r.confidence_score for r in activation_results.values() if r.activation_successful]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Calculate expected value
        total_expected_value = sum(r.expected_value for r in activation_results.values())
        
        return {
            "adoption_improvement": adoption_improvement,
            "average_confidence": average_confidence,
            "total_expected_value": total_expected_value,
            "successful_activations": successful_activations,
            "total_capabilities": total_capabilities
        }
    
    # Additional helper methods
    
    async def _get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory statistics for context analysis."""
        # Simulate memory statistics
        return {
            "total_entities": 75,
            "concept_density": 0.4,
            "relationship_count": 150
        }
    
    async def _calculate_search_activation_potential(self, 
                                                   capability: SearchCapability,
                                                   config: Dict,
                                                   context: SearchActivationContext) -> Dict[str, Any]:
        """Calculate activation potential for a search capability."""
        
        potential_score = await self._calculate_activation_score(capability, config, context)
        
        return {
            "potential_score": potential_score,
            "expected_adoption": config["expected_adoption_increase"],
            "recommended_triggers": list(config["trigger_weights"].keys()),
            "value_proposition": config["value_proposition"]
        }
    
    async def _get_current_search_usage(self, capability: SearchCapability) -> Dict[str, Any]:
        """Get current usage statistics for a search capability."""
        
        metrics = self.performance_metrics.get(capability.value, {})
        
        return {
            "usage_rate": 0.2 if capability.value in self.performance_metrics else 0.0,
            "activation_count": metrics.get("activation_count", 0),
            "success_rate": (
                metrics["success_count"] / metrics["activation_count"] 
                if metrics.get("activation_count", 0) > 0 else 0.0
            ),
            "average_confidence": (
                metrics["total_confidence"] / metrics["success_count"] 
                if metrics.get("success_count", 0) > 0 else 0.0
            )
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all activations."""
        
        if not self.activation_history:
            return 0.0
        
        total_confidence = sum(h.get("average_confidence", 0.0) for h in self.activation_history)
        return total_confidence / len(self.activation_history)
    
    async def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary for all search capabilities."""
        
        summary = {}
        
        for capability in SearchCapability:
            metrics = self.performance_metrics.get(capability.value, {})
            
            summary[capability.value] = {
                "activation_count": metrics.get("activation_count", 0),
                "success_rate": (
                    metrics["success_count"] / metrics["activation_count"] 
                    if metrics.get("activation_count", 0) > 0 else 0.0
                ),
                "average_confidence": (
                    metrics["total_confidence"] / metrics["success_count"] 
                    if metrics.get("success_count", 0) > 0 else 0.0
                ),
                "expected_value": (
                    metrics["total_expected_value"] / metrics["success_count"] 
                    if metrics.get("success_count", 0) > 0 else 0.0
                ),
                "usage_patterns": metrics.get("usage_patterns", [])
            }
        
        return summary
    
    async def _generate_search_activation_recommendations(self) -> List[Dict]:
        """Generate recommendations for search capability activation."""
        
        opportunities = await self.discover_semantic_search_opportunities()
        
        recommendations = []
        for capability_name, opportunity in list(opportunities.items())[:3]:  # Top 3
            recommendations.append({
                "capability": capability_name,
                "potential_score": opportunity["activation_potential"]["potential_score"],
                "expected_impact": opportunity["expected_adoption_increase"],
                "complexity": opportunity["integration_complexity"],
                "value_proposition": opportunity["activation_potential"]["value_proposition"],
                "recommended_triggers": opportunity["recommended_triggers"]
            })
        
        return recommendations
    
    def _get_capability_adoption(self, capability_name: str) -> float:
        """Get adoption rate for a specific capability."""
        
        metrics = self.performance_metrics.get(capability_name, {})
        
        if metrics.get("activation_count", 0) > 0:
            return metrics["success_count"] / metrics["activation_count"]
        
        return 0.0
    
    def _calculate_search_effectiveness(self) -> float:
        """Calculate overall search effectiveness score."""
        
        if not self.performance_metrics:
            return 0.0
        
        total_success = sum(m.get("success_count", 0) for m in self.performance_metrics.values())
        total_activations = sum(m.get("activation_count", 0) for m in self.performance_metrics.values())
        
        if total_activations == 0:
            return 0.0
        
        return total_success / total_activations