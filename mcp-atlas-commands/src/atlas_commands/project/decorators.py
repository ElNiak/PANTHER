"""
Project-Aware Decorators for ATLAS MCP Components

This module provides decorator classes that wrap existing ATLAS managers
with project-scoped functionality while preserving all existing behavior.

Design Principles:
- Composition over inheritance (SOLID)
- Decorator pattern for non-intrusive extension
- Delegate to existing managers (DRY)
- Minimal code changes (KISS)
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .context_manager import ProjectContextManager, ProjectContextValidator, ProjectMismatchError
from ..storage.task_storage_manager import TaskStorageManager
from ..memory.graph_manager import MemoryGraphManager


class ProjectAwareTaskManager:
    """
    Project-aware wrapper for existing task management functionality.
    
    Design: Decorator pattern - wraps existing TaskStorageManager and other
    task-related managers with project scoping while delegating all core
    functionality to preserve existing behavior.
    """
    
    def __init__(self, context_manager: ProjectContextManager):
        self.context_manager = context_manager
        self.validator = ProjectContextValidator(context_manager)
        self.project_id = context_manager.project_id
        
        # Initialize existing storage manager with project-scoped base path
        storage_base_path = context_manager.get_project_scoped_path('tasks')
        
        # REUSE: Existing TaskStorageManager with project-scoped storage
        self.storage_manager = TaskStorageManager(base_path=str(storage_base_path))
        
        # Override project name detection in storage manager
        self.storage_manager.project_name = self.project_id
    
    def create_task_metadata(self, project_name: str, task_id: str, task_type: str, 
                           description: str, **kwargs) -> str:
        """
        Create task metadata with project scoping.
        
        Validates project match and delegates to existing storage manager.
        """
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Project mismatch: {project_name} != {self.project_id}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # Add project scope to task ID
        scoped_task_id = self.context_manager.scope_task_id(task_id)
        
        # Add project context to metadata
        kwargs.update({
            'project_context': self.context_manager.get_project_context_dict(),
            'original_task_id': task_id,
            'scoped_task_id': scoped_task_id
        })
        
        # DELEGATE: Use existing storage manager logic (DRY)
        return self.storage_manager.create_task_metadata(
            project_name=project_name,
            task_id=scoped_task_id,
            task_type=task_type,
            description=description,
            **kwargs
        )
    
    def update_task_status(self, project_name: str, task_id: str, status: str, 
                          phase: Optional[str] = None) -> Dict[str, Any]:
        """Update task status with project validation."""
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Project mismatch: {project_name} != {self.project_id}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # Ensure task is project-scoped
        scoped_task_id = self.context_manager.scope_task_id(task_id)
        
        # Validate task belongs to project
        if not self.context_manager.validate_task_belongs_to_project(scoped_task_id):
            raise ProjectMismatchError(
                f"Task {scoped_task_id} does not belong to project {self.project_id}",
                expected_project=self.project_id,
                actual_project=scoped_task_id.split(':')[0] if ':' in scoped_task_id else 'unknown'
            )
        
        # DELEGATE: Use existing storage manager logic
        return self.storage_manager.update_task_status(
            project_name=project_name,
            task_id=scoped_task_id,
            status=status,
            phase=phase
        )
    
    def add_task_artifact(self, project_name: str, task_id: str, artifact_type: str,
                         content: str, filename: str) -> str:
        """Add task artifact with project validation."""
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Project mismatch: {project_name} != {self.project_id}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # Ensure task is project-scoped
        scoped_task_id = self.context_manager.scope_task_id(task_id)
        
        # Validate task belongs to project
        if not self.context_manager.validate_task_belongs_to_project(scoped_task_id):
            raise ProjectMismatchError(
                f"Task {scoped_task_id} does not belong to project {self.project_id}",
                expected_project=self.project_id,
                actual_project=scoped_task_id.split(':')[0] if ':' in scoped_task_id else 'unknown'
            )
        
        # DELEGATE: Use existing storage manager logic
        return self.storage_manager.add_task_artifact(
            project_name=project_name,
            task_id=scoped_task_id,
            artifact_type=artifact_type,
            content=content,
            filename=filename
        )
    
    def get_task_context(self, project_name: str, task_id: str) -> Dict[str, Any]:
        """Get task context with project validation."""
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Project mismatch: {project_name} != {self.project_id}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # Ensure task is project-scoped
        scoped_task_id = self.context_manager.scope_task_id(task_id)
        
        # DELEGATE: Use existing storage manager logic
        return self.storage_manager.get_task_context(project_name, scoped_task_id)
    
    def list_project_tasks(self, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks for current project only."""
        # Default to current project
        if project_name is None:
            project_name = self.project_id
        
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Cannot access tasks for project: {project_name}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # DELEGATE: Use existing storage manager logic
        all_tasks = self.storage_manager.list_project_tasks(project_name)
        
        # Filter tasks to ensure they belong to current project
        project_tasks = []
        for task in all_tasks:
            task_id = task.get('task_id', '')
            if self.context_manager.validate_task_belongs_to_project(task_id):
                project_tasks.append(task)
        
        return project_tasks
    
    def create_hierarchical_task(self, project_name: str, task_id: str, task_name: str,
                               task_type: str, description: str, 
                               parent_task_id: Optional[str] = None) -> str:
        """Create hierarchical task with project scoping."""
        # Validate project match
        if project_name != self.project_id:
            raise ProjectMismatchError(
                f"Project mismatch: {project_name} != {self.project_id}",
                expected_project=self.project_id,
                actual_project=project_name
            )
        
        # Scope task ID and parent task ID
        scoped_task_id = self.context_manager.scope_task_id(task_id)
        scoped_parent_id = None
        if parent_task_id:
            scoped_parent_id = self.context_manager.scope_task_id(parent_task_id)
            # Validate parent task belongs to project
            if not self.context_manager.validate_task_belongs_to_project(scoped_parent_id):
                raise ProjectMismatchError(
                    f"Parent task {scoped_parent_id} does not belong to project {self.project_id}",
                    expected_project=self.project_id,
                    actual_project=scoped_parent_id.split(':')[0] if ':' in scoped_parent_id else 'unknown'
                )
        
        # DELEGATE: Use existing hierarchical management logic
        # Note: This would delegate to the existing HierarchicalManagementHandler
        # For now, we create a basic implementation that follows the same pattern
        return self._create_hierarchical_task_impl(
            project_name, scoped_task_id, task_name, task_type, description, scoped_parent_id
        )
    
    def _create_hierarchical_task_impl(self, project_name: str, task_id: str, task_name: str,
                                     task_type: str, description: str, 
                                     parent_task_id: Optional[str] = None) -> str:
        """Implementation of hierarchical task creation."""
        # Create the basic task first
        task_metadata = {
            'task_name': task_name,
            'task_type': task_type,
            'description': description,
            'parent_task_id': parent_task_id,
            'hierarchical': True,
            'project_context': self.context_manager.get_project_context_dict()
        }
        
        # Use existing task creation logic
        return self.storage_manager.create_task_metadata(
            project_name=project_name,
            task_id=task_id,
            task_type=task_type,
            description=description,
            **task_metadata
        )


class ProjectAwareMemoryManager:
    """
    Project-aware wrapper for existing memory management functionality.
    
    Design: Decorator pattern - wraps existing MemoryGraphManager with
    project scoping while preserving all existing memory operations.
    """
    
    def __init__(self, context_manager: ProjectContextManager):
        self.context_manager = context_manager
        self.validator = ProjectContextValidator(context_manager)
        self.project_id = context_manager.project_id
        
        # Initialize existing memory manager with project-scoped storage
        memory_base_path = context_manager.get_project_scoped_path('memory')
        
        # REUSE: Existing MemoryGraphManager with project-scoped storage
        self.memory_manager = MemoryGraphManager(storage_path=str(memory_base_path))
    
    def create_entities(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Create memory entities with project scoping."""
        scoped_entities = []
        entity_ids = []
        
        for entity in entities:
            # Generate project-scoped entity ID
            entity_name = entity.get('name', f'entity_{uuid.uuid4().hex[:8]}')
            scoped_entity_id = self.context_manager.scope_entity_id(entity_name)
            
            # Add project context to entity
            scoped_entity = {
                **entity,  # Preserve all existing fields (DRY)
                'id': scoped_entity_id,
                'project_id': self.project_id,
                'project_context': self.context_manager.get_project_context_dict(),
                'original_name': entity_name,
                'created_at': datetime.utcnow().isoformat()
            }
            
            scoped_entities.append(scoped_entity)
            entity_ids.append(scoped_entity_id)
        
        # DELEGATE: Use existing memory manager logic
        result_ids = self.memory_manager.create_entities(scoped_entities)
        
        # Return the scoped entity IDs
        return entity_ids
    
    def search_nodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory nodes within project scope only."""
        # DELEGATE: Use existing search logic
        all_results = self.memory_manager.search_nodes(query, limit * 2)  # Get more to account for filtering
        
        # Filter results to current project only
        project_results = []
        for result in all_results:
            entity_id = result.get('id', result.get('entity_id', ''))
            if self.context_manager.validate_entity_belongs_to_project(entity_id):
                project_results.append(result)
                
            if len(project_results) >= limit:
                break
        
        return project_results
    
    def create_relations(self, relations: List[Dict[str, Any]]) -> List[str]:
        """Create relations between entities within project scope."""
        scoped_relations = []
        relation_ids = []
        
        for relation in relations:
            # Scope entity IDs
            from_entity = relation.get('from', '')
            to_entity = relation.get('to', '')
            
            scoped_from = self.context_manager.scope_entity_id(from_entity)
            scoped_to = self.context_manager.scope_entity_id(to_entity)
            
            # Validate both entities belong to project
            if not (self.context_manager.validate_entity_belongs_to_project(scoped_from) and
                    self.context_manager.validate_entity_belongs_to_project(scoped_to)):
                continue  # Skip cross-project relations
            
            relation_id = f"{self.project_id}:rel_{uuid.uuid4().hex[:8]}"
            
            scoped_relation = {
                **relation,  # Preserve existing fields
                'id': relation_id,
                'from': scoped_from,
                'to': scoped_to,
                'project_id': self.project_id,
                'project_context': self.context_manager.get_project_context_dict(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            scoped_relations.append(scoped_relation)
            relation_ids.append(relation_id)
        
        # DELEGATE: Use existing memory manager logic
        result_ids = self.memory_manager.create_relations(scoped_relations)
        
        return relation_ids
    
    def read_graph(self, entity_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Read memory graph for current project only."""
        # Scope entity names if provided
        scoped_entity_names = None
        if entity_names:
            scoped_entity_names = [
                self.context_manager.scope_entity_id(name) for name in entity_names
            ]
        
        # DELEGATE: Use existing memory manager logic
        graph_data = self.memory_manager.read_graph(scoped_entity_names)
        
        # Filter results to current project
        if isinstance(graph_data, dict):
            # Filter entities and relations by project
            entities = graph_data.get('entities', [])
            relations = graph_data.get('relations', [])
            
            project_entities = [
                entity for entity in entities
                if self.context_manager.validate_entity_belongs_to_project(
                    entity.get('id', entity.get('entity_id', ''))
                )
            ]
            
            project_relations = [
                relation for relation in relations
                if relation.get('project_id') == self.project_id
            ]
            
            # Update graph data with filtered results
            graph_data.update({
                'entities': project_entities,
                'relations': project_relations,
                'project_id': self.project_id,
                'entity_count': len(project_entities),
                'relation_count': len(project_relations)
            })
        
        return graph_data
    
    def add_observations(self, entity_name: str, observations: List[str]) -> bool:
        """Add observations to entity with project scoping."""
        # Scope entity name
        scoped_entity_name = self.context_manager.scope_entity_id(entity_name)
        
        # Validate entity belongs to project
        if not self.context_manager.validate_entity_belongs_to_project(scoped_entity_name):
            raise ProjectMismatchError(
                f"Entity {scoped_entity_name} does not belong to project {self.project_id}",
                expected_project=self.project_id,
                actual_project=scoped_entity_name.split(':')[0] if ':' in scoped_entity_name else 'unknown'
            )
        
        # DELEGATE: Use existing memory manager logic
        return self.memory_manager.add_observations(scoped_entity_name, observations)


class ProjectAwareStorageManager:
    """
    Project-aware wrapper for storage operations.
    
    Design: Lightweight wrapper that adds project context validation
    and scoped paths to existing storage operations.
    """
    
    def __init__(self, context_manager: ProjectContextManager):
        self.context_manager = context_manager
        self.validator = ProjectContextValidator(context_manager)
        self.project_id = context_manager.project_id
    
    def get_project_storage_path(self, resource_type: str, filename: str = None) -> str:
        """Get project-scoped storage path."""
        return str(self.context_manager.get_project_scoped_path(resource_type, filename))
    
    def validate_storage_operation(self, operation: str, **kwargs) -> bool:
        """Validate storage operation against project context."""
        return self.validator.validate_operation(operation, kwargs)
    
    def ensure_project_directory(self, resource_type: str) -> str:
        """Ensure project-specific directory exists."""
        directory_path = self.context_manager.get_project_scoped_path(resource_type)
        directory_path.mkdir(parents=True, exist_ok=True)
        return str(directory_path)