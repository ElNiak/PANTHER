#!/usr/bin/env python3
"""
Test script to validate semantic search integration in Atlas MCP.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.handlers.embeddings import EmbeddingsHandler
from atlas_commands.embeddings.graph_sage import EmbeddingGenerator, TaskNode
from atlas_commands.embeddings.vector_store import EmbeddingStorage, TaskEmbedding
from atlas_commands.embeddings.semantic_search import SemanticSearchEngine
from atlas_commands.storage.task_storage_manager import TaskStorageManager


class MockServer:
    """Mock server for testing semantic search integration."""
    
    def __init__(self):
        # Initialize semantic components
        self.embedding_generator = EmbeddingGenerator(model_dim=64)
        self.embedding_storage = EmbeddingStorage(
            redis_client=None,  # No Redis for testing
            embedding_dim=64
        )
        self.semantic_search = SemanticSearchEngine(
            self.embedding_generator,
            self.embedding_storage
        )
        
        # Initialize storage manager
        storage_path = "/tmp/atlas_test"
        os.makedirs(storage_path, exist_ok=True)
        self.storage_manager = TaskStorageManager(storage_path)
        
        # Create some test tasks for embedding
        self._create_test_tasks()
    
    def _create_test_tasks(self):
        """Create test tasks and their embeddings."""
        test_tasks = [
            {
                "task_id": "task_001",
                "task_name": "Debug authentication issue",
                "description": "Fix OAuth login failures in production environment",
                "task_type": "debugging",
                "domain": "authentication",
                "project_name": "test_project",
                "status": "completed"
            },
            {
                "task_id": "task_002", 
                "task_name": "Implement user registration",
                "description": "Add new user registration flow with email verification",
                "task_type": "feature",
                "domain": "authentication",
                "project_name": "test_project",
                "status": "in_progress"
            },
            {
                "task_id": "task_003",
                "task_name": "Database performance optimization",
                "description": "Optimize slow database queries in user management system",
                "task_type": "optimization",
                "domain": "database",
                "project_name": "test_project", 
                "status": "completed"
            },
            {
                "task_id": "task_004",
                "task_name": "API rate limiting",
                "description": "Implement rate limiting for authentication endpoints",
                "task_type": "security",
                "domain": "api",
                "project_name": "test_project",
                "status": "pending"
            }
        ]
        
        # Store tasks in storage manager
        for task in test_tasks:
            try:
                self.storage_manager.create_task_metadata(
                    project_name=task["project_name"],
                    task_id=task["task_id"],
                    task_type=task["task_type"],
                    description=task["description"]
                )
            except Exception as e:
                print(f"Warning: Could not store task {task['task_id']}: {e}")
        
        # Create embeddings for semantic search
        self.test_tasks = test_tasks  # Store for fallback testing
        for task in test_tasks:
            try:
                # Create task node for embedding generation
                task_node = TaskNode(
                    task_id=task["task_id"],
                    description=task["description"],
                    task_type=task["task_type"],
                    domain=task["domain"],
                    complexity_score=0.7,
                    duration_normalized=0.5,
                    success_rate=0.9,
                    metadata=task
                )
                
                # Generate embedding
                embedding_vector = self.embedding_generator.generate_task_embedding(task_node)
                
                # Create task embedding object
                task_embedding = TaskEmbedding(
                    task_id=task["task_id"],
                    embedding_vector=embedding_vector.tolist(),
                    confidence_score=0.9,
                    last_updated="2025-06-28T00:00:00Z",
                    version=1,
                    metadata=task
                )
                
                # Store embedding
                self.embedding_storage.store_embedding(task_embedding)
                
            except Exception as e:
                print(f"Warning: Could not create embedding for task {task['task_id']}: {e}")
    
    def list_project_tasks(self, project_name):
        """Mock implementation for testing fallback."""
        return getattr(self, 'test_tasks', [])


async def test_semantic_search_integration():
    """Test the semantic search integration in embeddings handler."""
    
    print("🧪 Testing Semantic Search Integration")
    print("=" * 50)
    
    # Create mock server with test data
    mock_server = MockServer()
    
    # Create embeddings handler
    handler = EmbeddingsHandler(mock_server)
    
    # Test queries
    test_queries = [
        {
            "query": "authentication problems",
            "description": "Should find OAuth and registration tasks",
            "expected_semantic": True
        },
        {
            "query": "database slow queries",
            "description": "Should find database optimization task",
            "expected_semantic": True
        },
        {
            "query": "security implementation",
            "description": "Should find rate limiting task",
            "expected_semantic": True
        },
        {
            "query": "nonexistent xyz feature",
            "description": "Should return empty results",
            "expected_semantic": False
        }
    ]
    
    print(f"📊 Testing {len(test_queries)} search queries...\n")
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        
        # Prepare arguments for the handler
        arguments = {
            "query": test_case["query"],
            "project_name": "test_project",
            "limit": 5,
            "similarity_threshold": 0.3
        }
        
        try:
            # Call the search handler
            result = await handler._handle_search_similar_tasks(arguments)
            
            # Parse the JSON result
            result_text = result[0].text
            result_data = json.loads(result_text)
            
            # Check results
            method_used = result_data.get("method", "unknown")
            similar_tasks = result_data.get("similar_tasks", [])
            total_found = result_data.get("total_found", 0)
            semantic_available = result_data.get("semantic_components_available", False)
            
            print(f"  Method used: {method_used}")
            print(f"  Semantic components available: {semantic_available}")
            print(f"  Results found: {total_found}")
            
            if similar_tasks:
                print("  Top results:")
                for task in similar_tasks[:3]:
                    score = task.get("similarity_score", 0)
                    name = task.get("task_name", "Unknown")
                    print(f"    - {name} (score: {score})")
            
            # Verify semantic search was used when expected
            if test_case["expected_semantic"] and semantic_available:
                if method_used == "semantic_search":
                    print("  ✅ Semantic search was used as expected")
                else:
                    print(f"  ⚠️  Expected semantic search but got {method_used}")
            else:
                print(f"  ℹ️  Used {method_used} (semantic components: {semantic_available})")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Error during test: {str(e)}")
            print()
    
    # Test embedding stats
    print("📈 Testing embedding statistics...")
    try:
        stats_result = await handler._handle_get_embeddings_stats({})
        stats_text = stats_result[0].text
        stats_data = json.loads(stats_text)
        
        print("Embeddings system status:")
        embeddings_system = stats_data.get("embeddings_system", {})
        semantic_search = stats_data.get("semantic_search", {})
        
        print(f"  Embeddings available: {embeddings_system.get('available', False)}")
        print(f"  Model dimension: {embeddings_system.get('model_dimension', 0)}")
        print(f"  Semantic search available: {semantic_search.get('available', False)}")
        print(f"  Vector store size: {embeddings_system.get('vector_store_size', 0)}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")
    
    print("\n🎉 Semantic search integration test completed!")


async def test_fallback_behavior():
    """Test fallback behavior when semantic components are not available."""
    
    print("\n🔄 Testing Fallback Behavior")
    print("=" * 30)
    
    # Create server without semantic components
    class MockServerNoSemantic:
        def __init__(self):
            storage_path = "/tmp/atlas_test_fallback"
            os.makedirs(storage_path, exist_ok=True)
            self.storage_manager = TaskStorageManager(storage_path)
            # No semantic components initialized
            
    mock_server = MockServerNoSemantic()
    handler = EmbeddingsHandler(mock_server)
    
    arguments = {
        "query": "test query",
        "project_name": "",
        "limit": 5,
        "similarity_threshold": 0.7
    }
    
    try:
        result = await handler._handle_search_similar_tasks(arguments)
        result_text = result[0].text
        result_data = json.loads(result_text)
        
        method_used = result_data.get("method", "unknown")
        semantic_available = result_data.get("semantic_components_available", False)
        
        print(f"Method used: {method_used}")
        print(f"Semantic components available: {semantic_available}")
        
        if method_used.endswith("fallback") and not semantic_available:
            print("✅ Fallback behavior working correctly")
        else:
            print("⚠️  Unexpected fallback behavior")
            
    except Exception as e:
        print(f"❌ Error during fallback test: {str(e)}")


if __name__ == "__main__":
    async def main():
        await test_semantic_search_integration()
        await test_fallback_behavior()
    
    asyncio.run(main())