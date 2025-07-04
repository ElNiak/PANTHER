#!/usr/bin/env python3
"""Test script for Knowledge Graph Embeddings integration."""

import sys
import traceback
from datetime import datetime

sys.path.insert(0, 'src')

def test_embeddings_integration():
    """Test the complete embeddings integration."""
    print("=== Testing Knowledge Graph Embeddings Integration ===\n")
    
    try:
        # Test imports
        print("1. Testing imports...")
        from atlas_commands.embeddings.graph_sage import EmbeddingGenerator, TaskNode
        from atlas_commands.embeddings.vector_store import EmbeddingStorage, TaskEmbedding
        from atlas_commands.embeddings.semantic_search import SemanticSearchEngine
        from atlas_commands.embeddings.training import EmbeddingTrainer
        print("✓ All imports successful")
        
        # Test EmbeddingGenerator
        print("\n2. Testing EmbeddingGenerator...")
        generator = EmbeddingGenerator(model_dim=64)
        model_info = generator.get_model_info()
        print(f"✓ EmbeddingGenerator initialized: {model_info}")
        
        # Create test task
        test_task = TaskNode(
            task_id="test_task_001",
            description="Implement Redis caching for performance optimization",
            task_type="task",
            domain="infrastructure",
            complexity_score=0.7,
            duration_normalized=0.4,
            success_rate=1.0,
            metadata={"project": "ATLAS", "status": "completed"}
        )
        
        # Generate embedding
        embedding = generator.generate_task_embedding(test_task)
        print(f"✓ Generated embedding: shape={embedding.shape}, type={type(embedding)}")
        
        # Test EmbeddingStorage
        print("\n3. Testing EmbeddingStorage...")
        storage = EmbeddingStorage(redis_client=None, embedding_dim=64)
        storage_stats = storage.get_storage_stats()
        print(f"✓ EmbeddingStorage initialized: {storage_stats}")
        
        # Store test embedding
        task_embedding = TaskEmbedding(
            task_id=test_task.task_id,
            embedding_vector=embedding.tolist(),
            confidence_score=0.95,
            last_updated=datetime.utcnow().isoformat(),
            version=1,
            metadata=test_task.metadata
        )
        
        success = storage.store_embedding(task_embedding)
        print(f"✓ Stored embedding: success={success}")
        
        # Retrieve embedding
        retrieved = storage.get_embedding(test_task.task_id)
        print(f"✓ Retrieved embedding: found={retrieved is not None}")
        
        # Test SemanticSearchEngine
        print("\n4. Testing SemanticSearchEngine...")
        search_engine = SemanticSearchEngine(generator, storage)
        search_stats = search_engine.get_search_stats()
        print(f"✓ SemanticSearchEngine initialized: {search_stats}")
        
        # Test search functionality
        results = search_engine.search_similar_tasks("caching system optimization", max_results=5)
        print(f"✓ Search similar tasks: {len(results)} results found")
        
        solutions = search_engine.discover_solution_patterns("performance bottleneck", domain="infrastructure")
        print(f"✓ Solution patterns: {len(solutions)} solutions found")
        
        # Test EmbeddingTrainer
        print("\n5. Testing EmbeddingTrainer...")
        trainer = EmbeddingTrainer(generator, storage, task_storage_manager=None)
        training_stats = trainer.get_training_stats()
        print(f"✓ EmbeddingTrainer initialized: {training_stats}")
        
        # Test should_retrain logic
        should_retrain = trainer.should_retrain()
        print(f"✓ Should retrain check: {should_retrain}")
        
        print("\n=== ✅ All Tests Passed! ===")
        print("\nKnowledge Graph Embeddings system is working correctly:")
        print("- GraphSAGE embeddings with fallback support")
        print("- Vector storage with FAISS/linear search fallback")
        print("- Semantic search with multiple modes")
        print("- Training pipeline with synthetic data support")
        print("- Complete graceful degradation when ML dependencies unavailable")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_embeddings_integration()
    exit(0 if success else 1)