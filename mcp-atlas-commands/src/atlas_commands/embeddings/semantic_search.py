"""Semantic search engine for task discovery and relationship analysis."""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .graph_sage import TaskNode, EmbeddingGenerator
from .vector_store import EmbeddingStorage, TaskEmbedding

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search modes for different use cases."""
    SIMILAR_TASKS = "similar_tasks"
    RELATED_CONCEPTS = "related_concepts"
    SOLUTION_PATTERNS = "solution_patterns"
    DEPENDENCY_CHAINS = "dependency_chains"


@dataclass
class SearchResult:
    """Search result with relevance metadata."""
    task_id: str
    similarity_score: float
    relevance_rank: int
    result_type: str
    metadata: Dict[str, Any]
    explanation: str


@dataclass
class SearchContext:
    """Search context for contextual ranking."""
    current_task_id: Optional[str] = None
    project_name: Optional[str] = None
    domain: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None
    search_history: Optional[List[str]] = None


class SemanticSearchEngine:
    """Advanced semantic search engine for task discovery."""
    
    def __init__(self, embedding_generator: EmbeddingGenerator, 
                 embedding_storage: EmbeddingStorage):
        """Initialize semantic search engine.
        
        Args:
            embedding_generator: Embedding generator instance
            embedding_storage: Embedding storage instance
        """
        self.embedding_generator = embedding_generator
        self.embedding_storage = embedding_storage
        self.search_cache = {}
        self.max_cache_size = 1000
        
        logger.info("Initialized semantic search engine")
    
    def search_similar_tasks(self, query: str, context: Optional[SearchContext] = None,
                           max_results: int = 10, threshold: float = 0.7) -> List[SearchResult]:
        """Search for tasks similar to the query.
        
        Args:
            query: Search query (natural language)
            context: Search context for ranking
            max_results: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_query_embedding(query)
            
            # Search similar embeddings
            similar_embeddings = self.embedding_storage.search_similar_tasks(
                query_embedding, k=max_results * 2, threshold=threshold
            )
            
            # Convert to search results
            results = []
            for i, (task_id, similarity) in enumerate(similar_embeddings):
                result = SearchResult(
                    task_id=task_id,
                    similarity_score=similarity,
                    relevance_rank=i + 1,
                    result_type="similar_task",
                    metadata={"search_mode": SearchMode.SIMILAR_TASKS.value},
                    explanation=f"Task semantically similar to query (similarity: {similarity:.3f})"
                )
                results.append(result)
            
            # Apply contextual ranking
            if context:
                results = self._apply_contextual_ranking(results, context)
            
            # Limit results
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to search similar tasks: {e}")
            return []
    
    def find_related_concepts(self, task_id: str, relation_types: List[str] = None,
                            max_distance: int = 3) -> List[SearchResult]:
        """Find concepts related to a specific task.
        
        Args:
            task_id: Source task ID
            relation_types: Types of relationships to explore
            max_distance: Maximum relationship distance
            
        Returns:
            List of related concepts
        """
        try:
            # Get task embedding
            task_embedding_obj = self.embedding_storage.get_embedding(task_id)
            if not task_embedding_obj:
                logger.warning(f"No embedding found for task {task_id}")
                return []
            
            query_embedding = task_embedding_obj.to_numpy()
            
            # Search for similar tasks (potential relationships)
            similar_tasks = self.embedding_storage.search_similar_tasks(
                query_embedding, k=50, threshold=0.5
            )
            
            # Filter and rank based on relationship types
            results = []
            for i, (related_task_id, similarity) in enumerate(similar_tasks):
                if related_task_id == task_id:
                    continue
                
                # Determine relationship type based on similarity and metadata
                relationship_type = self._infer_relationship_type(
                    task_id, related_task_id, similarity
                )
                
                if relation_types and relationship_type not in relation_types:
                    continue
                
                result = SearchResult(
                    task_id=related_task_id,
                    similarity_score=similarity,
                    relevance_rank=i + 1,
                    result_type=relationship_type,
                    metadata={
                        "source_task": task_id,
                        "relationship_type": relationship_type,
                        "distance": 1  # Direct relationship
                    },
                    explanation=f"{relationship_type.title()} relationship with source task"
                )
                results.append(result)
            
            return results[:20]  # Limit related concepts
            
        except Exception as e:
            logger.error(f"Failed to find related concepts for {task_id}: {e}")
            return []
    
    def discover_solution_patterns(self, problem_description: str, 
                                 domain: Optional[str] = None) -> List[SearchResult]:
        """Discover solution patterns for a problem.
        
        Args:
            problem_description: Description of the problem
            domain: Optional domain filter
            
        Returns:
            List of solution patterns
        """
        try:
            # Generate problem embedding
            problem_embedding = self._generate_query_embedding(problem_description)
            
            # Search for similar tasks that might contain solutions
            similar_tasks = self.embedding_storage.search_similar_tasks(
                problem_embedding, k=30, threshold=0.6
            )
            
            # Filter for tasks that likely contain solutions
            solution_results = []
            for i, (task_id, similarity) in enumerate(similar_tasks):
                task_embedding = self.embedding_storage.get_embedding(task_id)
                if not task_embedding:
                    continue
                
                # Check if task metadata suggests it contains solutions
                metadata = task_embedding.metadata
                is_solution = self._is_solution_task(metadata, domain)
                
                if is_solution:
                    result = SearchResult(
                        task_id=task_id,
                        similarity_score=similarity,
                        relevance_rank=len(solution_results) + 1,
                        result_type="solution_pattern",
                        metadata={
                            "problem_domain": domain,
                            "solution_confidence": self._calculate_solution_confidence(metadata),
                            "task_metadata": metadata
                        },
                        explanation=f"Solution pattern for similar problem (confidence: {similarity:.3f})"
                    )
                    solution_results.append(result)
            
            # Sort by solution confidence
            solution_results.sort(
                key=lambda x: x.metadata["solution_confidence"], 
                reverse=True
            )
            
            return solution_results[:15]
            
        except Exception as e:
            logger.error(f"Failed to discover solution patterns: {e}")
            return []
    
    def find_dependency_chains(self, task_id: str, direction: str = "both") -> List[SearchResult]:
        """Find dependency chains for a task.
        
        Args:
            task_id: Source task ID
            direction: Search direction ("upstream", "downstream", "both")
            
        Returns:
            List of dependency chain results
        """
        try:
            # This would typically use the memory graph for actual dependencies
            # For now, we'll use embedding similarity as a proxy
            
            task_embedding_obj = self.embedding_storage.get_embedding(task_id)
            if not task_embedding_obj:
                return []
            
            query_embedding = task_embedding_obj.to_numpy()
            
            # Search for similar tasks
            similar_tasks = self.embedding_storage.search_similar_tasks(
                query_embedding, k=30, threshold=0.6
            )
            
            # Filter for tasks that could be dependencies
            dependency_results = []
            for i, (dep_task_id, similarity) in enumerate(similar_tasks):
                if dep_task_id == task_id:
                    continue
                
                dep_embedding = self.embedding_storage.get_embedding(dep_task_id)
                if not dep_embedding:
                    continue
                
                # Infer dependency relationship
                dep_type = self._infer_dependency_type(
                    task_id, dep_task_id, dep_embedding.metadata
                )
                
                if dep_type and (direction == "both" or 
                              (direction == "upstream" and dep_type == "prerequisite") or
                              (direction == "downstream" and dep_type == "dependent")):
                    
                    result = SearchResult(
                        task_id=dep_task_id,
                        similarity_score=similarity,
                        relevance_rank=len(dependency_results) + 1,
                        result_type=dep_type,
                        metadata={
                            "dependency_type": dep_type,
                            "chain_position": 1,  # Direct dependency
                            "source_task": task_id
                        },
                        explanation=f"{dep_type.title()} dependency relationship"
                    )
                    dependency_results.append(result)
            
            return dependency_results[:10]
            
        except Exception as e:
            logger.error(f"Failed to find dependency chains for {task_id}: {e}")
            return []
    
    def multi_modal_search(self, query: str, search_modes: List[SearchMode],
                          context: Optional[SearchContext] = None) -> Dict[str, List[SearchResult]]:
        """Perform multi-modal search across different search types.
        
        Args:
            query: Search query
            search_modes: List of search modes to use
            context: Search context
            
        Returns:
            Dictionary mapping search mode to results
        """
        results = {}
        
        for mode in search_modes:
            try:
                if mode == SearchMode.SIMILAR_TASKS:
                    results[mode.value] = self.search_similar_tasks(query, context)
                elif mode == SearchMode.RELATED_CONCEPTS:
                    # For related concepts, we need a task ID
                    if context and context.current_task_id:
                        results[mode.value] = self.find_related_concepts(context.current_task_id)
                    else:
                        results[mode.value] = []
                elif mode == SearchMode.SOLUTION_PATTERNS:
                    domain = context.domain if context else None
                    results[mode.value] = self.discover_solution_patterns(query, domain)
                elif mode == SearchMode.DEPENDENCY_CHAINS:
                    if context and context.current_task_id:
                        results[mode.value] = self.find_dependency_chains(context.current_task_id)
                    else:
                        results[mode.value] = []
            except Exception as e:
                logger.error(f"Failed multi-modal search for mode {mode}: {e}")
                results[mode.value] = []
        
        return results
    
    def _generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for search query."""
        # Create a temporary task node for the query
        query_task = TaskNode(
            task_id="query",
            description=query,
            task_type="query",
            domain="unknown",
            complexity_score=0.5,
            duration_normalized=0.5,
            success_rate=1.0,
            metadata={"is_query": True}
        )
        
        return self.embedding_generator.generate_task_embedding(query_task)
    
    def _apply_contextual_ranking(self, results: List[SearchResult], 
                                context: SearchContext) -> List[SearchResult]:
        """Apply contextual ranking to search results."""
        # Boost results from same project
        if context.project_name:
            for result in results:
                task_embedding = self.embedding_storage.get_embedding(result.task_id)
                if task_embedding and task_embedding.metadata.get("project") == context.project_name:
                    result.similarity_score *= 1.2
        
        # Boost results from same domain
        if context.domain:
            for result in results:
                task_embedding = self.embedding_storage.get_embedding(result.task_id)
                if task_embedding and task_embedding.metadata.get("domain") == context.domain:
                    result.similarity_score *= 1.1
        
        # Apply user preferences
        if context.user_preferences:
            preferred_types = context.user_preferences.get("preferred_task_types", [])
            for result in results:
                task_embedding = self.embedding_storage.get_embedding(result.task_id)
                if task_embedding and task_embedding.metadata.get("task_type") in preferred_types:
                    result.similarity_score *= 1.15
        
        # Re-sort and update ranks
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        for i, result in enumerate(results):
            result.relevance_rank = i + 1
        
        return results
    
    def _infer_relationship_type(self, task_id: str, related_task_id: str, 
                               similarity: float) -> str:
        """Infer relationship type between tasks."""
        # Get task metadata
        task_embedding = self.embedding_storage.get_embedding(task_id)
        related_embedding = self.embedding_storage.get_embedding(related_task_id)
        
        if not task_embedding or not related_embedding:
            return "similar"
        
        task_meta = task_embedding.metadata
        related_meta = related_embedding.metadata
        
        # Check for hierarchical relationships
        if (task_meta.get("parent_task_id") == related_task_id or
            related_meta.get("parent_task_id") == task_id):
            return "hierarchical"
        
        # Check for sequential relationships
        if (task_meta.get("sequence_id", 0) == related_meta.get("sequence_id", 0) - 1 or
            related_meta.get("sequence_id", 0) == task_meta.get("sequence_id", 0) - 1):
            return "sequential"
        
        # Check for domain similarity
        if task_meta.get("domain") == related_meta.get("domain"):
            return "domain_related"
        
        # High similarity suggests direct relationship
        if similarity > 0.85:
            return "similar"
        elif similarity > 0.7:
            return "related"
        else:
            return "tangential"
    
    def _is_solution_task(self, metadata: Dict[str, Any], domain: Optional[str]) -> bool:
        """Check if task metadata suggests it contains solutions."""
        # Check task status
        if metadata.get("status") == "completed":
            # Completed tasks are more likely to contain solutions
            if domain:
                return metadata.get("domain") == domain
            return True
        
        # Check for solution indicators in description or metadata
        solution_indicators = ["fix", "solve", "implement", "complete", "resolve"]
        description = metadata.get("description", "").lower()
        
        for indicator in solution_indicators:
            if indicator in description:
                return True
        
        return False
    
    def _calculate_solution_confidence(self, metadata: Dict[str, Any]) -> float:
        """Calculate confidence that task contains a good solution."""
        confidence = 0.5  # Base confidence
        
        # Boost for completed tasks
        if metadata.get("status") == "completed":
            confidence += 0.3
        
        # Boost for high success rate
        success_rate = metadata.get("success_rate", 0.5)
        confidence += success_rate * 0.2
        
        # Boost for recent tasks
        last_updated = metadata.get("last_updated")
        if last_updated:
            try:
                update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                days_old = (datetime.utcnow() - update_time.replace(tzinfo=None)).days
                if days_old < 30:
                    confidence += 0.1
            except:
                pass
        
        return min(1.0, confidence)
    
    def _infer_dependency_type(self, task_id: str, dep_task_id: str, 
                              dep_metadata: Dict[str, Any]) -> Optional[str]:
        """Infer dependency type between tasks."""
        # Check explicit dependencies in metadata
        dependencies = dep_metadata.get("dependencies", [])
        if task_id in dependencies:
            return "prerequisite"
        
        # Check if current task depends on dep_task
        task_embedding = self.embedding_storage.get_embedding(task_id)
        if task_embedding:
            task_dependencies = task_embedding.metadata.get("dependencies", [])
            if dep_task_id in task_dependencies:
                return "dependent"
        
        # Infer from creation times
        task_created = dep_metadata.get("created_at")
        if task_embedding and task_created:
            current_created = task_embedding.metadata.get("created_at")
            if current_created and task_created < current_created:
                return "prerequisite"
            elif current_created and task_created > current_created:
                return "dependent"
        
        return None
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "cache_size": len(self.search_cache),
            "max_cache_size": self.max_cache_size,
            "embedding_generator_available": self.embedding_generator is not None,
            "embedding_storage_available": self.embedding_storage is not None,
            "supported_search_modes": [mode.value for mode in SearchMode],
            "storage_stats": self.embedding_storage.get_storage_stats() if self.embedding_storage else {}
        }