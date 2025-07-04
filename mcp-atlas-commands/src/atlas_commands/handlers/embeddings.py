"""
Embeddings Handler

Handles semantic search, similarity detection, concept discovery,
and embedding training operations.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from ..tool_registry import ToolHandler
from ..refactor_config import get_config
import logging


class EmbeddingsHandler(ToolHandler):
    """Handler for embeddings and semantic search tools."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "embeddings"
    
    def get_tool_names(self) -> List[str]:
        return [
            "search_similar_tasks",
            "discover_related_concepts",
            "find_solution_patterns",
            "train_task_embeddings",
            "get_embeddings_stats"
        ]
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle embeddings tool calls."""
        try:
            if self.config.enable_consistent_error_handling:
                self.logger.info(f"Processing embeddings tool: {name}")
            
            # Route to appropriate handler method
            if name == "search_similar_tasks":
                return await self._handle_search_similar_tasks(arguments)
            elif name == "discover_related_concepts":
                return await self._handle_discover_related_concepts(arguments)
            elif name == "find_solution_patterns":
                return await self._handle_find_solution_patterns(arguments)
            elif name == "train_task_embeddings":
                return await self._handle_train_task_embeddings(arguments)
            elif name == "get_embeddings_stats":
                return await self._handle_get_embeddings_stats(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown embeddings tool: {name}")]
                
        except Exception as e:
            error_msg = f"Error in embeddings handler for {name}: {str(e)}"
            self.logger.error(error_msg)
            if self.config.enable_consistent_error_handling:
                return [TextContent(type="text", text=f"Embeddings Error: {str(e)}")]
            else:
                raise e
    
    # Delegate to existing server methods with consistent error handling
    async def _handle_search_similar_tasks(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Search for tasks similar to the given query or task."""
        import json
        from datetime import datetime
        
        try:
            query = arguments.get("query", "")
            project_name = arguments.get("project_name", "")
            limit = arguments.get("limit", 10)
            similarity_threshold = arguments.get("similarity_threshold", 0.7)
            
            # Check for semantic search components first
            semantic_search = getattr(self.server, 'semantic_search', None)
            embedding_generator = getattr(self.server, 'embedding_generator', None)
            storage_manager = getattr(self.server, 'storage_manager', None)
            # Try semantic search first if components are available
            if semantic_search and embedding_generator:
                try:
                    # Use semantic search for better results
                    from ..embeddings.semantic_search import SearchContext
                    
                    context = SearchContext(
                        project_name=project_name if project_name else None,
                        domain=None,
                        user_preferences=None
                    )
                    
                    search_results = semantic_search.search_similar_tasks(
                        query=query,
                        context=context,
                        max_results=limit,
                        threshold=similarity_threshold
                    )
                    
                    # Convert semantic search results to expected format
                    similar_tasks = []
                    for result in search_results:
                        similar_tasks.append({
                            "task_id": result.task_id,
                            "task_name": result.metadata.get("task_name", result.task_id),
                            "task_type": result.metadata.get("task_type", "unknown"),
                            "status": result.metadata.get("status", "unknown"),
                            "similarity_score": round(result.similarity_score, 3),
                            "project_name": result.metadata.get("project_name", ""),
                            "explanation": result.explanation
                        })
                    
                    result = {
                        "query": query,
                        "similar_tasks": similar_tasks,
                        "total_found": len(similar_tasks),
                        "method": "semantic_search",
                        "similarity_threshold": similarity_threshold,
                        "timestamp": datetime.now().isoformat(),
                        "semantic_components_available": True
                    }
                    
                    if self.config.enable_consistent_error_handling:
                        self.logger.info(f"Semantic search found {len(similar_tasks)} similar tasks for query: {query}")
                    
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
                except Exception as semantic_error:
                    # Log semantic search failure but continue with fallback
                    self.logger.warning(f"Semantic search failed, falling back to keyword search: {semantic_error}")
            
            # Fallback to keyword-based search
            if not storage_manager:
                result = {
                    "query": query,
                    "similar_tasks": [],
                    "total_found": 0,
                    "method": "keyword_search_fallback",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Storage manager not available for search",
                    "semantic_components_available": semantic_search is not None and embedding_generator is not None
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            # Get all tasks from storage
            if project_name:
                all_tasks = storage_manager.list_project_tasks(project_name)
            else:
                # Search across all projects
                all_tasks = []
                # This would need implementation to search across all projects
                
            # Basic keyword matching for similar tasks (fallback)
            similar_tasks = []
            query_lower = query.lower()
            
            for task in all_tasks:
                # Calculate basic similarity score based on description and task type
                description = task.get("description", "").lower()
                task_type = task.get("task_type", "").lower()
                task_name = task.get("task_name", "").lower()
                
                score = 0.0
                if query_lower in description:
                    score += 0.6
                if query_lower in task_type:
                    score += 0.3
                if query_lower in task_name:
                    score += 0.4
                
                # Add partial word matches
                for word in query_lower.split():
                    if word in description:
                        score += 0.1
                    if word in task_type:
                        score += 0.1
                
                if score >= similarity_threshold:
                    similar_tasks.append({
                        "task_id": task.get("task_id"),
                        "task_name": task.get("task_name", task.get("description", "")[:50]),
                        "task_type": task.get("task_type"),
                        "status": task.get("status"),
                        "similarity_score": round(score, 3),
                        "project_name": task.get("project_name")
                    })
            
            # Sort by similarity score and limit results
            similar_tasks.sort(key=lambda x: x["similarity_score"], reverse=True)
            similar_tasks = similar_tasks[:limit]
            
            result = {
                "query": query,
                "similar_tasks": similar_tasks,
                "total_found": len(similar_tasks),
                "method": "keyword_search_fallback",
                "similarity_threshold": similarity_threshold,
                "timestamp": datetime.now().isoformat(),
                "semantic_components_available": semantic_search is not None and embedding_generator is not None
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error in search_similar_tasks: {str(e)}")
            return [TextContent(type="text", text=f"Error executing search_similar_tasks: {str(e)}")]
    
    async def _handle_discover_related_concepts(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_discover_related_concepts(arguments)
    
    async def _handle_find_solution_patterns(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_find_solution_patterns(arguments)
    
    async def _handle_train_task_embeddings(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_train_task_embeddings(arguments)
    
    async def _handle_get_embeddings_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get comprehensive embeddings system statistics."""
        try:
            # Access embeddings system from server
            embeddings_system = getattr(self.server, 'embeddings_system', None)
            semantic_search = getattr(self.server, 'semantic_search', None)
            
            stats = {
                "embeddings_system": {
                    "available": embeddings_system is not None,
                    "model_dimension": getattr(embeddings_system, 'dimension', 0) if embeddings_system else 0,
                    "vector_store_size": 0,
                    "training_status": "not_available"
                },
                "semantic_search": {
                    "available": semantic_search is not None,
                    "index_size": 0,
                    "last_trained": "never"
                },
                "performance": {
                    "total_searches": 0,
                    "average_search_time": 0.0,
                    "cache_hit_rate": 0.0
                },
                "timestamp": "2025-06-27T10:45:00Z"
            }
            
            # Get actual stats if embeddings system is available
            if embeddings_system:
                vector_store = getattr(embeddings_system, 'vector_store', None)
                if vector_store:
                    stats["embeddings_system"]["vector_store_size"] = getattr(vector_store, 'size', 0)
                    stats["embeddings_system"]["training_status"] = "ready"
                    
            if semantic_search:
                stats["semantic_search"]["index_size"] = getattr(semantic_search, 'index_size', 0)
            
            import json
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
            
        except Exception as e:
            error_msg = f"Error getting embeddings stats: {str(e)}"
            self.logger.error(error_msg)
            return [TextContent(type="text", text=f"Embeddings stats error: {str(e)}")]