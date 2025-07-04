"""Training pipeline for GraphSAGE embeddings."""

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch_geometric.data import Data, DataLoader
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    
    # Create dummy classes for when PyTorch is not available
    class DummyTensor:
        def __init__(self, *args, **kwargs):
            self.shape = [1]
            
        def reshape(self, *args):
            return self
            
        def astype(self, *args):
            return self
    
    class DummyTorch:
        Tensor = DummyTensor
        def tensor(self, *args, **kwargs):
            return DummyTensor()
        def zeros(self, *args, **kwargs):
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
            self.train_mask = DummyTensor()
            self.val_mask = DummyTensor()
    
    def train_test_split(*args, **kwargs):
        return [0], [1]
    
    torch = DummyTorch()
    Data = DummyData

from .graph_sage import TaskNode, TaskRelationship, TaskGraphSAGE, EmbeddingGenerator
from .vector_store import EmbeddingStorage, TaskEmbedding

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for embedding training."""
    batch_size: int = 32
    learning_rate: float = 0.001
    num_epochs: int = 100
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    min_improvement: float = 0.001
    l2_regularization: float = 0.0001
    dropout_rate: float = 0.2
    graph_sampling_size: int = 1000
    negative_sampling_ratio: float = 2.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrainingResult:
    """Results from training session."""
    success: bool
    final_loss: float
    validation_accuracy: float
    num_epochs_trained: int
    training_time_seconds: float
    model_size_mb: float
    embeddings_generated: int
    config_used: TrainingConfig
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['config_used'] = self.config_used.to_dict()
        return result


class EmbeddingTrainer:
    """Trainer for GraphSAGE embeddings on task relationships."""
    
    def __init__(self, embedding_generator: EmbeddingGenerator,
                 embedding_storage: EmbeddingStorage,
                 task_storage_manager=None):
        """Initialize embedding trainer.
        
        Args:
            embedding_generator: Embedding generator instance
            embedding_storage: Embedding storage instance
            task_storage_manager: Task storage manager for data access
        """
        self.embedding_generator = embedding_generator
        self.embedding_storage = embedding_storage
        self.task_storage_manager = task_storage_manager
        
        self.training_history = []
        self.current_model = None
        self.last_training_time = None
        
        logger.info("Initialized embedding trainer")
    
    def train_embeddings(self, config: Optional[TrainingConfig] = None,
                        incremental: bool = True) -> TrainingResult:
        """Train GraphSAGE embeddings on task data.
        
        Args:
            config: Training configuration
            incremental: Whether to perform incremental training
            
        Returns:
            Training results
        """
        if not TORCH_AVAILABLE:
            return TrainingResult(
                success=False,
                final_loss=0.0,
                validation_accuracy=0.0,
                num_epochs_trained=0,
                training_time_seconds=0.0,
                model_size_mb=0.0,
                embeddings_generated=0,
                config_used=config or TrainingConfig(),
                error_message="PyTorch not available for training"
            )
        
        start_time = datetime.utcnow()
        config = config or TrainingConfig()
        
        try:
            # Load training data
            logger.info("Loading training data...")
            tasks, relationships = self._load_training_data(incremental)
            
            if len(tasks) < 10:
                return TrainingResult(
                    success=False,
                    final_loss=0.0,
                    validation_accuracy=0.0,
                    num_epochs_trained=0,
                    training_time_seconds=0.0,
                    model_size_mb=0.0,
                    embeddings_generated=0,
                    config_used=config,
                    error_message=f"Insufficient training data: {len(tasks)} tasks"
                )
            
            # Prepare data
            logger.info(f"Preparing training data: {len(tasks)} tasks, {len(relationships)} relationships")
            train_data, val_data = self._prepare_training_data(tasks, relationships, config)
            
            # Initialize or load model
            if incremental and self.current_model is not None:
                model = self.current_model
                logger.info("Using existing model for incremental training")
            else:
                model = self._initialize_model(train_data)
                logger.info("Initialized new model for training")
            
            # Train model
            logger.info("Starting training...")
            final_loss, val_accuracy, epochs_trained = self._train_model(
                model, train_data, val_data, config
            )
            
            # Generate embeddings for all tasks
            logger.info("Generating embeddings for all tasks...")
            embeddings_count = self._generate_and_store_embeddings(model, tasks)
            
            # Calculate model size
            model_size_mb = self._calculate_model_size(model)
            
            # Update current model
            self.current_model = model
            self.last_training_time = datetime.utcnow()
            
            training_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = TrainingResult(
                success=True,
                final_loss=final_loss,
                validation_accuracy=val_accuracy,
                num_epochs_trained=epochs_trained,
                training_time_seconds=training_time,
                model_size_mb=model_size_mb,
                embeddings_generated=embeddings_count,
                config_used=config
            )
            
            # Store training history
            self.training_history.append(result)
            
            logger.info(f"Training completed successfully in {training_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Training failed: {str(e)}"
            logger.error(error_msg)
            
            training_time = (datetime.utcnow() - start_time).total_seconds()
            return TrainingResult(
                success=False,
                final_loss=0.0,
                validation_accuracy=0.0,
                num_epochs_trained=0,
                training_time_seconds=training_time,
                model_size_mb=0.0,
                embeddings_generated=0,
                config_used=config,
                error_message=error_msg
            )
    
    def _load_training_data(self, incremental: bool) -> Tuple[List[TaskNode], List[TaskRelationship]]:
        """Load training data from task storage."""
        tasks = []
        relationships = []
        
        try:
            if self.task_storage_manager:
                # Load tasks from all projects
                projects = ["ATLAS", "PANTHER"]  # Known projects
                
                for project in projects:
                    try:
                        project_tasks = self.task_storage_manager.list_project_tasks(project)
                        
                        for task_data in project_tasks:
                            # Convert task data to TaskNode
                            task_node = self._convert_task_to_node(task_data)
                            if task_node:
                                tasks.append(task_node)
                                
                                # Extract relationships from task metadata
                                task_relationships = self._extract_relationships(task_data)
                                relationships.extend(task_relationships)
                                
                    except Exception as e:
                        logger.warning(f"Failed to load tasks for project {project}: {e}")
            
            # If no tasks loaded from storage, create synthetic data for demonstration
            if not tasks:
                logger.warning("No tasks loaded from storage, creating synthetic training data")
                tasks, relationships = self._create_synthetic_training_data()
            
        except Exception as e:
            logger.error(f"Failed to load training data: {e}")
            # Create minimal synthetic data
            tasks, relationships = self._create_synthetic_training_data()
        
        logger.info(f"Loaded {len(tasks)} tasks and {len(relationships)} relationships")
        return tasks, relationships
    
    def _convert_task_to_node(self, task_data: Dict[str, Any]) -> Optional[TaskNode]:
        """Convert task data to TaskNode."""
        try:
            # Calculate normalized metrics
            duration_hours = task_data.get("estimated_hours", 1.0)
            duration_normalized = min(1.0, duration_hours / 40.0)  # Normalize to [0, 1]
            
            # Calculate complexity from description length and metadata
            description = task_data.get("description", "")
            complexity_score = min(1.0, len(description) / 500.0)  # Normalize by description length
            
            # Success rate based on status
            status = task_data.get("status", "planning")
            success_rate = 1.0 if status == "completed" else 0.5
            
            return TaskNode(
                task_id=task_data["task_id"],
                description=description,
                task_type=task_data.get("task_type", "task"),
                domain=task_data.get("domain", "unknown"),
                complexity_score=complexity_score,
                duration_normalized=duration_normalized,
                success_rate=success_rate,
                metadata=task_data
            )
        except Exception as e:
            logger.warning(f"Failed to convert task {task_data.get('task_id', 'unknown')}: {e}")
            return None
    
    def _extract_relationships(self, task_data: Dict[str, Any]) -> List[TaskRelationship]:
        """Extract relationships from task metadata."""
        relationships = []
        task_id = task_data["task_id"]
        
        try:
            # Parent-child relationships
            parent_id = task_data.get("parent_task_id")
            if parent_id:
                relationship = TaskRelationship(
                    source_id=parent_id,
                    target_id=task_id,
                    relationship_type="hierarchy",
                    strength=0.9,
                    temporal_weight=1.0,
                    success_correlation=0.8,
                    semantic_similarity=0.7
                )
                relationships.append(relationship)
            
            # Dependencies
            dependencies = task_data.get("dependencies", [])
            for dep_id in dependencies:
                relationship = TaskRelationship(
                    source_id=dep_id,
                    target_id=task_id,
                    relationship_type="dependency",
                    strength=0.8,
                    temporal_weight=1.0,
                    success_correlation=0.9,
                    semantic_similarity=0.6
                )
                relationships.append(relationship)
            
            # Sequential relationships (if sequence metadata exists)
            sequence_id = task_data.get("sequence_id")
            if sequence_id is not None and sequence_id > 0:
                # Create relationship to previous task in sequence
                prev_task_id = f"{task_id}_prev"  # Simplified for demo
                relationship = TaskRelationship(
                    source_id=prev_task_id,
                    target_id=task_id,
                    relationship_type="sequence",
                    strength=0.7,
                    temporal_weight=1.0,
                    success_correlation=0.7,
                    semantic_similarity=0.8
                )
                relationships.append(relationship)
        
        except Exception as e:
            logger.warning(f"Failed to extract relationships for {task_id}: {e}")
        
        return relationships
    
    def _create_synthetic_training_data(self) -> Tuple[List[TaskNode], List[TaskRelationship]]:
        """Create synthetic training data for demonstration."""
        tasks = []
        relationships = []
        
        # Create sample tasks
        task_templates = [
            ("Implement Redis caching", "infrastructure", "task", 0.7, 0.4, 1.0),
            ("Setup OpenTelemetry", "infrastructure", "task", 0.6, 0.3, 1.0),
            ("Knowledge graph embeddings", "ml", "task", 0.9, 0.8, 0.8),
            ("Fix network binding issue", "debugging", "task", 0.4, 0.2, 1.0),
            ("Create test suite", "testing", "subtask", 0.3, 0.1, 0.9),
            ("Document API endpoints", "documentation", "subtask", 0.2, 0.1, 1.0),
            ("Optimize database queries", "performance", "task", 0.6, 0.5, 0.7),
            ("Implement user authentication", "security", "task", 0.5, 0.3, 0.9),
        ]
        
        for i, (description, domain, task_type, complexity, duration, success) in enumerate(task_templates):
            task = TaskNode(
                task_id=f"synthetic_task_{i}",
                description=description,
                task_type=task_type,
                domain=domain,
                complexity_score=complexity,
                duration_normalized=duration,
                success_rate=success,
                metadata={
                    "created_at": datetime.utcnow().isoformat(),
                    "synthetic": True
                }
            )
            tasks.append(task)
        
        # Create relationships
        for i in range(len(tasks) - 1):
            # Sequential relationship
            relationship = TaskRelationship(
                source_id=tasks[i].task_id,
                target_id=tasks[i + 1].task_id,
                relationship_type="sequence",
                strength=0.6,
                temporal_weight=1.0,
                success_correlation=0.7,
                semantic_similarity=0.5
            )
            relationships.append(relationship)
        
        # Add some hierarchical relationships
        for i in range(0, len(tasks), 3):
            if i + 1 < len(tasks):
                relationship = TaskRelationship(
                    source_id=tasks[i].task_id,
                    target_id=tasks[i + 1].task_id,
                    relationship_type="hierarchy",
                    strength=0.8,
                    temporal_weight=1.0,
                    success_correlation=0.8,
                    semantic_similarity=0.7
                )
                relationships.append(relationship)
        
        return tasks, relationships
    
    def _prepare_training_data(self, tasks: List[TaskNode], relationships: List[TaskRelationship],
                             config: TrainingConfig) -> Tuple[Any, Any]:
        """Prepare training and validation data."""
        # Build graph data
        graph_data = self.embedding_generator._build_graph_data(tasks, relationships)
        
        # Split into train/validation
        num_nodes = graph_data.x.shape[0]
        train_indices, val_indices = train_test_split(
            list(range(num_nodes)), 
            test_size=config.validation_split,
            random_state=42
        )
        
        # Create train/val masks
        train_mask = torch.zeros(num_nodes, dtype=torch.bool)
        val_mask = torch.zeros(num_nodes, dtype=torch.bool)
        train_mask[train_indices] = True
        val_mask[val_indices] = True
        
        # Add masks to graph data
        graph_data.train_mask = train_mask
        graph_data.val_mask = val_mask
        
        return graph_data, graph_data  # Same data with different masks
    
    def _initialize_model(self, train_data: Any) -> TaskGraphSAGE:
        """Initialize GraphSAGE model."""
        input_dim = train_data.x.shape[1]
        model = TaskGraphSAGE(
            input_dim=input_dim,
            hidden_dim=128,
            output_dim=64
        )
        return model
    
    def _train_model(self, model: TaskGraphSAGE, train_data: Any, val_data: Any,
                    config: TrainingConfig) -> Tuple[float, float, int]:
        """Train the GraphSAGE model."""
        optimizer = optim.Adam(model.parameters(), lr=config.learning_rate, 
                              weight_decay=config.l2_regularization)
        criterion = nn.MSELoss()  # Self-supervised learning
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(config.num_epochs):
            # Training phase
            model.train()
            optimizer.zero_grad()
            
            # Forward pass
            embeddings = model(train_data.x, train_data.edge_index)
            
            # Self-supervised loss: predict node features from embeddings
            reconstructed = torch.nn.functional.linear(embeddings, model.sage_conv2.lin_l.weight.T)
            loss = criterion(reconstructed[train_data.train_mask], 
                           train_data.x[train_data.train_mask])
            
            loss.backward()
            optimizer.step()
            
            # Validation phase
            model.eval()
            with torch.no_grad():
                val_embeddings = model(val_data.x, val_data.edge_index)
                val_reconstructed = torch.nn.functional.linear(val_embeddings, model.sage_conv2.lin_l.weight.T)
                val_loss = criterion(val_reconstructed[val_data.val_mask], 
                                   val_data.x[val_data.val_mask])
            
            # Early stopping
            if val_loss < best_val_loss - config.min_improvement:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
            
            if (epoch + 1) % 10 == 0:
                logger.debug(f"Epoch {epoch + 1}: Loss={loss:.4f}, Val Loss={val_loss:.4f}")
        
        # Calculate validation accuracy (similarity to original features)
        val_accuracy = 1.0 - (val_loss.item() / train_data.x[val_data.val_mask].norm().item())
        val_accuracy = max(0.0, min(1.0, val_accuracy))  # Clamp to [0, 1]
        
        return loss.item(), val_accuracy, epoch + 1
    
    def _generate_and_store_embeddings(self, model: TaskGraphSAGE, tasks: List[TaskNode]) -> int:
        """Generate and store embeddings for all tasks."""
        count = 0
        
        try:
            # Generate embeddings
            embeddings_dict = self.embedding_generator.generate_graph_embeddings(tasks, [])
            
            # Store embeddings
            for task in tasks:
                if task.task_id in embeddings_dict:
                    embedding_vector = embeddings_dict[task.task_id]
                    
                    task_embedding = TaskEmbedding(
                        task_id=task.task_id,
                        embedding_vector=embedding_vector.tolist(),
                        confidence_score=0.9,  # High confidence for trained embeddings
                        last_updated=datetime.utcnow().isoformat(),
                        version=1,
                        metadata=task.metadata
                    )
                    
                    if self.embedding_storage.store_embedding(task_embedding):
                        count += 1
        
        except Exception as e:
            logger.error(f"Failed to generate/store embeddings: {e}")
        
        return count
    
    def _calculate_model_size(self, model: TaskGraphSAGE) -> float:
        """Calculate model size in MB."""
        try:
            param_size = 0
            buffer_size = 0
            
            for param in model.parameters():
                param_size += param.nelement() * param.element_size()
            
            for buffer in model.buffers():
                buffer_size += buffer.nelement() * buffer.element_size()
            
            size_mb = (param_size + buffer_size) / 1024 / 1024
            return round(size_mb, 2)
        except:
            return 0.0
    
    def should_retrain(self, force_retrain: bool = False) -> bool:
        """Check if model should be retrained."""
        if force_retrain:
            return True
        
        # Check if model exists
        if self.current_model is None:
            return True
        
        # Check time since last training
        if self.last_training_time is None:
            return True
        
        # Retrain weekly
        days_since_training = (datetime.utcnow() - self.last_training_time).days
        if days_since_training >= 7:
            return True
        
        # Check if significant new data is available
        # (Would implement based on task storage statistics)
        
        return False
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        stats = {
            "model_available": self.current_model is not None,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "training_sessions": len(self.training_history),
            "torch_available": TORCH_AVAILABLE
        }
        
        if self.training_history:
            latest_result = self.training_history[-1]
            stats.update({
                "latest_training_success": latest_result.success,
                "latest_training_accuracy": latest_result.validation_accuracy,
                "latest_embeddings_generated": latest_result.embeddings_generated,
                "latest_training_time_seconds": latest_result.training_time_seconds
            })
        
        return stats