"""GraphSAGE implementation for task relationship embeddings."""

import logging
import numpy as np
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch_geometric.nn import SAGEConv
    from torch_geometric.data import Data
    import sentence_transformers
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
    # Create dummy classes for when PyTorch is not available
    class DummyTensor:
        pass
    
    class DummyModule:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return DummyTensor()
        def eval(self):
            pass
        def parameters(self):
            return []
        def buffers(self):
            return []
    
    class DummyNN:
        Module = DummyModule
        class Dropout:
            def __init__(self, *args, **kwargs):
                pass
        class BatchNorm1d:
            def __init__(self, *args, **kwargs):
                pass
    
    class DummyTorch:
        Tensor = DummyTensor
        def tensor(self, *args, **kwargs):
            return DummyTensor()
        def randn(self, *args, **kwargs):
            return DummyTensor()
        def no_grad(self):
            class DummyContextManager:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return DummyContextManager()
    
    class DummyData:
        def __init__(self, *args, **kwargs):
            self.x = DummyTensor()
            self.edge_index = DummyTensor()
            self.edge_attr = DummyTensor()
    
    torch = DummyTorch()
    nn = DummyNN()
    F = None
    Data = DummyData

logger = logging.getLogger(__name__)


@dataclass
class TaskNode:
    """Task node representation for graph neural network."""
    task_id: str
    description: str
    task_type: str
    domain: str
    complexity_score: float
    duration_normalized: float
    success_rate: float
    metadata: Dict[str, Any]
    
    def to_feature_vector(self, text_embedder) -> np.ndarray:
        """Convert task to feature vector."""
        # Text embedding (384 dimensions from sentence transformer)
        description_emb = text_embedder.encode(self.description)
        
        # Categorical features (one-hot encoded)
        task_type_features = self._encode_categorical(self.task_type, ['task', 'subtask', 'subsubtask'])
        domain_features = self._encode_categorical(self.domain, ['infrastructure', 'ml', 'networking', 'debugging'])
        
        # Numerical features (normalized)
        numerical_features = np.array([
            self.complexity_score,
            self.duration_normalized,
            self.success_rate
        ])
        
        # Combine all features
        return np.concatenate([
            description_emb,
            task_type_features,
            domain_features,
            numerical_features
        ])
    
    def _encode_categorical(self, value: str, categories: List[str]) -> np.ndarray:
        """One-hot encode categorical value."""
        encoding = np.zeros(len(categories))
        if value in categories:
            encoding[categories.index(value)] = 1.0
        return encoding


@dataclass
class TaskRelationship:
    """Task relationship representation."""
    source_id: str
    target_id: str
    relationship_type: str
    strength: float
    temporal_weight: float
    success_correlation: float
    semantic_similarity: float
    
    def to_edge_features(self) -> np.ndarray:
        """Convert relationship to edge features."""
        # Categorical encoding for relationship type
        rel_types = ['dependency', 'similarity', 'hierarchy', 'sequence']
        rel_encoding = np.zeros(len(rel_types))
        if self.relationship_type in rel_types:
            rel_encoding[rel_types.index(self.relationship_type)] = 1.0
        
        # Numerical features
        numerical_features = np.array([
            self.strength,
            self.temporal_weight,
            self.success_correlation,
            self.semantic_similarity
        ])
        
        return np.concatenate([rel_encoding, numerical_features])


class TaskGraphSAGE(nn.Module):
    """GraphSAGE model for task embeddings."""
    
    def __init__(self, input_dim: int = 256, hidden_dim: int = 128, output_dim: int = 64):
        """Initialize GraphSAGE model.
        
        Args:
            input_dim: Input feature dimension
            hidden_dim: Hidden layer dimension  
            output_dim: Output embedding dimension
        """
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available - GraphSAGE will use fallback embeddings")
            return
        
        # GraphSAGE layers
        self.sage_conv1 = SAGEConv(input_dim, hidden_dim)
        self.sage_conv2 = SAGEConv(hidden_dim, output_dim)
        self.dropout = nn.Dropout(0.2)
        
        # Batch normalization
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(output_dim)
    
    def forward(self, x: Any, edge_index: Any) -> Any:
        """Forward pass through GraphSAGE."""
        if not TORCH_AVAILABLE:
            # Fallback: return random normalized embeddings
            batch_size = x.shape[0] if hasattr(x, 'shape') else 1
            return torch.randn(batch_size, self.output_dim)
        
        # First SAGE layer
        x = self.sage_conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        # Second SAGE layer
        x = self.sage_conv2(x, edge_index)
        x = self.bn2(x)
        
        # L2 normalization
        return F.normalize(x, p=2, dim=1)
    
    def encode_graph(self, graph_data: Any) -> Any:
        """Encode entire graph to embeddings."""
        self.eval()
        with torch.no_grad():
            embeddings = self.forward(graph_data.x, graph_data.edge_index)
        return embeddings


class EmbeddingGenerator:
    """Generates embeddings for tasks and relationships."""
    
    def __init__(self, model_dim: int = 64):
        """Initialize embedding generator.
        
        Args:
            model_dim: Dimension of output embeddings
        """
        self.model_dim = model_dim
        self.model = None
        self.text_embedder = None
        self.task_cache = {}
        self.relation_cache = {}
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize GraphSAGE model and text embedder."""
        try:
            if TORCH_AVAILABLE:
                # Initialize sentence transformer for text embeddings
                self.text_embedder = sentence_transformers.SentenceTransformer(
                    'all-MiniLM-L6-v2'  # 384-dimensional embeddings
                )
                
                # Calculate input dimension: text(384) + categorical(7) + numerical(3) = 394
                input_dim = 394
                self.model = TaskGraphSAGE(input_dim=input_dim, output_dim=self.model_dim)
                
                logger.info("GraphSAGE and SentenceTransformer initialized successfully")
            else:
                logger.warning("PyTorch/SentenceTransformers not available - using fallback embeddings")
                
        except Exception as e:
            logger.error(f"Failed to initialize embedding components: {e}")
            self.text_embedder = None
            self.model = None
    
    def generate_task_embedding(self, task_node: TaskNode) -> np.ndarray:
        """Generate embedding for a single task.
        
        Args:
            task_node: Task node to embed
            
        Returns:
            Embedding vector
        """
        # Check cache first
        task_hash = self._hash_task(task_node)
        if task_hash in self.task_cache:
            return self.task_cache[task_hash]
        
        if self.text_embedder is None or self.model is None:
            # Fallback: generate deterministic embedding from task content
            embedding = self._generate_fallback_embedding(task_node)
        else:
            try:
                # Generate features
                features = task_node.to_feature_vector(self.text_embedder)
                
                # Create simple graph with self-loop for single node embedding
                x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                edge_index = torch.tensor([[0], [0]], dtype=torch.long)  # Self-loop
                
                # Generate embedding
                self.model.eval()
                with torch.no_grad():
                    embedding = self.model(x, edge_index).numpy().flatten()
                    
            except Exception as e:
                logger.warning(f"Failed to generate GraphSAGE embedding: {e}")
                embedding = self._generate_fallback_embedding(task_node)
        
        # Cache result
        self.task_cache[task_hash] = embedding
        return embedding
    
    def generate_graph_embeddings(self, tasks: List[TaskNode], 
                                 relationships: List[TaskRelationship]) -> Dict[str, np.ndarray]:
        """Generate embeddings for multiple tasks using graph structure.
        
        Args:
            tasks: List of task nodes
            relationships: List of task relationships
            
        Returns:
            Dictionary mapping task_id to embedding vector
        """
        if not tasks:
            return {}
        
        if self.text_embedder is None or self.model is None:
            # Fallback: generate individual embeddings
            return {task.task_id: self._generate_fallback_embedding(task) for task in tasks}
        
        try:
            # Build graph data
            graph_data = self._build_graph_data(tasks, relationships)
            
            # Generate embeddings
            embeddings = self.model.encode_graph(graph_data)
            
            # Map embeddings to task IDs
            task_embeddings = {}
            for i, task in enumerate(tasks):
                task_embeddings[task.task_id] = embeddings[i].numpy()
            
            return task_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate graph embeddings: {e}")
            # Fallback to individual embeddings
            return {task.task_id: self._generate_fallback_embedding(task) for task in tasks}
    
    def _build_graph_data(self, tasks: List[TaskNode], 
                         relationships: List[TaskRelationship]) -> Data:
        """Build PyTorch Geometric graph data."""
        # Create node features
        node_features = []
        task_id_to_idx = {task.task_id: i for i, task in enumerate(tasks)}
        
        for task in tasks:
            features = task.to_feature_vector(self.text_embedder)
            node_features.append(features)
        
        x = torch.tensor(np.array(node_features), dtype=torch.float32)
        
        # Create edge indices
        edge_indices = []
        edge_features = []
        
        for rel in relationships:
            if rel.source_id in task_id_to_idx and rel.target_id in task_id_to_idx:
                src_idx = task_id_to_idx[rel.source_id]
                tgt_idx = task_id_to_idx[rel.target_id]
                
                # Add both directions for undirected relationships
                edge_indices.extend([[src_idx, tgt_idx], [tgt_idx, src_idx]])
                edge_attr = rel.to_edge_features()
                edge_features.extend([edge_attr, edge_attr])
        
        # Add self-loops for isolated nodes
        for i in range(len(tasks)):
            edge_indices.append([i, i])
            # Self-loop features (identity relationship)
            self_edge = np.zeros(8)  # 4 rel types + 4 numerical features
            self_edge[0] = 1.0  # Mark as identity
            self_edge[4] = 1.0  # Full strength
            edge_features.append(self_edge)
        
        edge_index = torch.tensor(np.array(edge_indices).T, dtype=torch.long)
        edge_attr = torch.tensor(np.array(edge_features), dtype=torch.float32)
        
        return Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
    
    def _generate_fallback_embedding(self, task_node: TaskNode) -> np.ndarray:
        """Generate deterministic fallback embedding."""
        # Create deterministic features from task content
        text_hash = hashlib.md5(task_node.description.encode()).hexdigest()
        
        # Convert hex to numerical features
        hex_features = np.array([int(text_hash[i:i+2], 16) for i in range(0, min(32, len(text_hash)), 2)])
        hex_features = hex_features / 255.0  # Normalize to [0, 1]
        
        # Add categorical and numerical features
        categorical_features = np.array([
            hash(task_node.task_type) % 100 / 100.0,
            hash(task_node.domain) % 100 / 100.0,
        ])
        
        numerical_features = np.array([
            task_node.complexity_score,
            task_node.duration_normalized,
            task_node.success_rate
        ])
        
        # Combine and pad/truncate to target dimension
        all_features = np.concatenate([hex_features, categorical_features, numerical_features])
        
        if len(all_features) > self.model_dim:
            embedding = all_features[:self.model_dim]
        else:
            embedding = np.pad(all_features, (0, self.model_dim - len(all_features)), 'constant')
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _hash_task(self, task_node: TaskNode) -> str:
        """Generate hash for task caching."""
        content = f"{task_node.task_id}_{task_node.description}_{task_node.task_type}_{task_node.domain}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_available": self.model is not None,
            "torch_available": TORCH_AVAILABLE,
            "text_embedder_available": self.text_embedder is not None,
            "model_dimension": self.model_dim,
            "cache_size": len(self.task_cache),
            "initialized": datetime.utcnow().isoformat()
        }