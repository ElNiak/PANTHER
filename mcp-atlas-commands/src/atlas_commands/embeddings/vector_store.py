"""Vector storage and retrieval for task embeddings."""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

logger = logging.getLogger(__name__)


@dataclass
class TaskEmbedding:
    """Task embedding with metadata."""
    task_id: str
    embedding_vector: List[float]
    confidence_score: float
    last_updated: str
    version: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskEmbedding':
        """Create from dictionary."""
        return cls(**data)
    
    def to_numpy(self) -> np.ndarray:
        """Convert embedding to numpy array."""
        return np.array(self.embedding_vector, dtype=np.float32)


class VectorIndex:
    """FAISS-based vector index for fast similarity search."""
    
    def __init__(self, dimension: int, index_type: str = "flat"):
        """Initialize vector index.
        
        Args:
            dimension: Embedding dimension
            index_type: Type of FAISS index ('flat', 'ivf', 'hnsw')
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.task_ids = []  # Maps index positions to task IDs
        self.enabled = FAISS_AVAILABLE
        
        if self.enabled:
            self._create_index()
        else:
            logger.warning("FAISS not available - using fallback linear search")
            self.vectors = {}  # Fallback storage
    
    def _create_index(self):
        """Create FAISS index."""
        try:
            if self.index_type == "flat":
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine similarity)
            elif self.index_type == "ivf":
                # IVF index for larger datasets
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)  # 100 clusters
            elif self.index_type == "hnsw":
                # HNSW index for high-dimensional data
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
                self.index.hnsw.efConstruction = 40
                self.index.hnsw.efSearch = 16
            else:
                raise ValueError(f"Unknown index type: {self.index_type}")
            
            logger.info(f"Created FAISS {self.index_type} index with dimension {self.dimension}")
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            self.enabled = False
            self.vectors = {}
    
    def add_embedding(self, task_id: str, embedding: np.ndarray) -> bool:
        """Add embedding to index.
        
        Args:
            task_id: Task identifier
            embedding: Embedding vector
            
        Returns:
            Success status
        """
        try:
            embedding = embedding.astype(np.float32)
            
            if self.enabled:
                # Normalize for cosine similarity
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                
                self.index.add(embedding.reshape(1, -1))
                self.task_ids.append(task_id)
            else:
                # Fallback storage
                self.vectors[task_id] = embedding
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add embedding for {task_id}: {e}")
            return False
    
    def search_similar(self, query_embedding: np.ndarray, k: int = 10, 
                      threshold: float = 0.0) -> List[Tuple[str, float]]:
        """Search for similar embeddings.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (task_id, similarity_score) tuples
        """
        try:
            query_embedding = query_embedding.astype(np.float32)
            
            if self.enabled and self.index.ntotal > 0:
                # Normalize query
                norm = np.linalg.norm(query_embedding)
                if norm > 0:
                    query_embedding = query_embedding / norm
                
                # Search FAISS index
                scores, indices = self.index.search(query_embedding.reshape(1, -1), k)
                
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx >= 0 and idx < len(self.task_ids) and score >= threshold:
                        task_id = self.task_ids[idx]
                        results.append((task_id, float(score)))
                
                return results
            else:
                # Fallback linear search
                return self._linear_search(query_embedding, k, threshold)
            
        except Exception as e:
            logger.error(f"Failed to search similar embeddings: {e}")
            return []
    
    def _linear_search(self, query_embedding: np.ndarray, k: int, 
                      threshold: float) -> List[Tuple[str, float]]:
        """Fallback linear search implementation."""
        if not self.vectors:
            return []
        
        # Normalize query
        query_norm = np.linalg.norm(query_embedding)
        if query_norm > 0:
            query_embedding = query_embedding / query_norm
        
        similarities = []
        for task_id, embedding in self.vectors.items():
            # Normalize stored embedding
            emb_norm = np.linalg.norm(embedding)
            if emb_norm > 0:
                normalized_emb = embedding / emb_norm
                # Cosine similarity
                similarity = np.dot(query_embedding, normalized_emb)
                if similarity >= threshold:
                    similarities.append((task_id, float(similarity)))
        
        # Sort by similarity (descending) and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]
    
    def remove_embedding(self, task_id: str) -> bool:
        """Remove embedding from index.
        
        Note: FAISS doesn't support efficient removal, so we mark as deleted.
        """
        try:
            if self.enabled:
                # Find index position
                if task_id in self.task_ids:
                    idx = self.task_ids.index(task_id)
                    self.task_ids[idx] = None  # Mark as deleted
            else:
                # Remove from fallback storage
                self.vectors.pop(task_id, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove embedding for {task_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if self.enabled:
            return {
                "index_type": self.index_type,
                "dimension": self.dimension,
                "total_vectors": self.index.ntotal if self.index else 0,
                "task_count": len([tid for tid in self.task_ids if tid is not None]),
                "faiss_available": True
            }
        else:
            return {
                "index_type": "linear_fallback",
                "dimension": self.dimension,
                "total_vectors": len(self.vectors),
                "task_count": len(self.vectors),
                "faiss_available": False
            }


class EmbeddingStorage:
    """Storage manager for task embeddings with Redis backend."""
    
    def __init__(self, redis_client=None, embedding_dim: int = 64):
        """Initialize embedding storage.
        
        Args:
            redis_client: Redis client instance
            embedding_dim: Dimension of embeddings
        """
        self.redis_client = redis_client
        self.embedding_dim = embedding_dim
        self.vector_index = VectorIndex(embedding_dim)
        self.cache = {}  # Local cache for frequently accessed embeddings
        self.max_cache_size = 1000
        
        # Storage prefixes
        self.embedding_prefix = "embedding:"
        self.metadata_prefix = "embedding_meta:"
        self.version_prefix = "embedding_version:"
        
        logger.info(f"Initialized embedding storage with dimension {embedding_dim}")
    
    def store_embedding(self, task_embedding: TaskEmbedding) -> bool:
        """Store task embedding.
        
        Args:
            task_embedding: Task embedding to store
            
        Returns:
            Success status
        """
        try:
            task_id = task_embedding.task_id
            
            # Store in Redis if available
            if self.redis_client:
                embedding_key = f"{self.embedding_prefix}{task_id}"
                metadata_key = f"{self.metadata_prefix}{task_id}"
                version_key = f"{self.version_prefix}{task_id}"
                
                # Store embedding vector
                embedding_bytes = np.array(task_embedding.embedding_vector, dtype=np.float32).tobytes()
                self.redis_client.set(embedding_key, embedding_bytes)
                
                # Store metadata
                metadata = {
                    "confidence_score": task_embedding.confidence_score,
                    "last_updated": task_embedding.last_updated,
                    "metadata": task_embedding.metadata
                }
                self.redis_client.set(metadata_key, json.dumps(metadata))
                
                # Store version
                self.redis_client.set(version_key, str(task_embedding.version))
                
                # Set expiration (7 days)
                expiration = 7 * 24 * 3600
                self.redis_client.expire(embedding_key, expiration)
                self.redis_client.expire(metadata_key, expiration)
                self.redis_client.expire(version_key, expiration)
            
            # Add to vector index
            embedding_vector = task_embedding.to_numpy()
            self.vector_index.add_embedding(task_id, embedding_vector)
            
            # Update local cache
            self._update_cache(task_id, task_embedding)
            
            logger.debug(f"Stored embedding for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding for {task_embedding.task_id}: {e}")
            return False
    
    def get_embedding(self, task_id: str) -> Optional[TaskEmbedding]:
        """Retrieve task embedding.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task embedding or None if not found
        """
        try:
            # Check cache first
            if task_id in self.cache:
                return self.cache[task_id]
            
            # Try Redis
            if self.redis_client:
                embedding_key = f"{self.embedding_prefix}{task_id}"
                metadata_key = f"{self.metadata_prefix}{task_id}"
                version_key = f"{self.version_prefix}{task_id}"
                
                embedding_bytes = self.redis_client.get(embedding_key)
                metadata_json = self.redis_client.get(metadata_key)
                version_str = self.redis_client.get(version_key)
                
                if embedding_bytes and metadata_json and version_str:
                    # Reconstruct embedding
                    embedding_vector = np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
                    metadata = json.loads(metadata_json)
                    version = int(version_str)
                    
                    task_embedding = TaskEmbedding(
                        task_id=task_id,
                        embedding_vector=embedding_vector,
                        confidence_score=metadata["confidence_score"],
                        last_updated=metadata["last_updated"],
                        version=version,
                        metadata=metadata["metadata"]
                    )
                    
                    # Update cache
                    self._update_cache(task_id, task_embedding)
                    return task_embedding
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get embedding for {task_id}: {e}")
            return None
    
    def search_similar_tasks(self, query_embedding: np.ndarray, k: int = 10,
                           threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Search for similar tasks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (task_id, similarity_score) tuples
        """
        return self.vector_index.search_similar(query_embedding, k, threshold)
    
    def batch_store_embeddings(self, embeddings: List[TaskEmbedding]) -> int:
        """Store multiple embeddings efficiently.
        
        Args:
            embeddings: List of task embeddings
            
        Returns:
            Number of successfully stored embeddings
        """
        success_count = 0
        
        for embedding in embeddings:
            if self.store_embedding(embedding):
                success_count += 1
        
        logger.info(f"Batch stored {success_count}/{len(embeddings)} embeddings")
        return success_count
    
    def get_embeddings_by_pattern(self, pattern: str) -> List[TaskEmbedding]:
        """Get embeddings matching a pattern.
        
        Args:
            pattern: Task ID pattern (supports wildcards if Redis available)
            
        Returns:
            List of matching embeddings
        """
        embeddings = []
        
        try:
            if self.redis_client:
                # Use Redis pattern matching
                embedding_keys = self.redis_client.keys(f"{self.embedding_prefix}{pattern}")
                
                for key in embedding_keys:
                    task_id = key.decode('utf-8').replace(self.embedding_prefix, '')
                    embedding = self.get_embedding(task_id)
                    if embedding:
                        embeddings.append(embedding)
            else:
                # Search local cache
                for task_id in self.cache:
                    if pattern in task_id:  # Simple substring match
                        embeddings.append(self.cache[task_id])
        
        except Exception as e:
            logger.error(f"Failed to get embeddings by pattern {pattern}: {e}")
        
        return embeddings
    
    def cleanup_old_embeddings(self, max_age_days: int = 30) -> int:
        """Clean up old embeddings.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of embeddings cleaned up
        """
        cleanup_count = 0
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        try:
            if self.redis_client:
                # Get all embedding metadata keys
                metadata_keys = self.redis_client.keys(f"{self.metadata_prefix}*")
                
                for key in metadata_keys:
                    metadata_json = self.redis_client.get(key)
                    if metadata_json:
                        metadata = json.loads(metadata_json)
                        last_updated = datetime.fromisoformat(metadata["last_updated"].replace('Z', '+00:00'))
                        
                        if last_updated < cutoff_date:
                            task_id = key.decode('utf-8').replace(self.metadata_prefix, '')
                            self._delete_embedding(task_id)
                            cleanup_count += 1
            
            # Clean local cache
            cache_to_remove = []
            for task_id, embedding in self.cache.items():
                last_updated = datetime.fromisoformat(embedding.last_updated.replace('Z', '+00:00'))
                if last_updated < cutoff_date:
                    cache_to_remove.append(task_id)
            
            for task_id in cache_to_remove:
                del self.cache[task_id]
                cleanup_count += 1
        
        except Exception as e:
            logger.error(f"Failed to cleanup old embeddings: {e}")
        
        logger.info(f"Cleaned up {cleanup_count} old embeddings")
        return cleanup_count
    
    def _update_cache(self, task_id: str, embedding: TaskEmbedding):
        """Update local cache with LRU eviction."""
        # Remove if already exists
        if task_id in self.cache:
            del self.cache[task_id]
        
        # Add to end (most recently used)
        self.cache[task_id] = embedding
        
        # Evict oldest if cache is full
        while len(self.cache) > self.max_cache_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
    
    def _delete_embedding(self, task_id: str):
        """Delete embedding from all storage layers."""
        try:
            if self.redis_client:
                # Delete from Redis
                self.redis_client.delete(f"{self.embedding_prefix}{task_id}")
                self.redis_client.delete(f"{self.metadata_prefix}{task_id}")
                self.redis_client.delete(f"{self.version_prefix}{task_id}")
            
            # Remove from vector index
            self.vector_index.remove_embedding(task_id)
            
            # Remove from cache
            self.cache.pop(task_id, None)
            
        except Exception as e:
            logger.error(f"Failed to delete embedding for {task_id}: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "redis_available": self.redis_client is not None,
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "embedding_dimension": self.embedding_dim
        }
        
        # Add vector index stats
        stats.update(self.vector_index.get_stats())
        
        # Add Redis stats if available
        if self.redis_client:
            try:
                embedding_count = len(self.redis_client.keys(f"{self.embedding_prefix}*"))
                stats["redis_embedding_count"] = embedding_count
            except:
                stats["redis_embedding_count"] = "unknown"
        
        return stats