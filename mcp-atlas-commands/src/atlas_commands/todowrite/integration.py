"""TodoWrite integration for ATLAS command system."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class TodoTask:
    """Represents a TodoWrite task."""
    
    def __init__(
        self,
        id: str,
        content: str,
        status: str = "pending",
        priority: str = "medium",
        estimate: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.content = content
        self.status = status
        self.priority = priority
        self.estimate = estimate
        self.dependencies = dependencies or []
        self.created_at = created_at or datetime.now()
        self.updated_at = self.created_at
        self.completed_at: Optional[datetime] = None


class TodoWriteIntegration:
    """Integrates ATLAS commands with TodoWrite system."""
    
    def __init__(self):
        self.tasks: Dict[str, TodoTask] = {}
        self.command_task_mapping: Dict[str, List[str]] = {}
    
    def create_command_task(
        self,
        command_name: str,
        task_id: str,
        priority: str = "medium",
        phase: Optional[str] = None,
        estimate: Optional[str] = None
    ) -> str:
        """Create a main TodoWrite task for a command execution."""
        
        content = f"{command_name.capitalize()} command for {task_id}"
        if phase:
            content += f" - {phase} phase"
        
        todo_task_id = f"{command_name}_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = TodoTask(
            id=todo_task_id,
            content=content,
            priority=priority,
            estimate=estimate
        )
        
        self.tasks[todo_task_id] = task
        
        # Track command-task mapping
        if command_name not in self.command_task_mapping:
            self.command_task_mapping[command_name] = []
        self.command_task_mapping[command_name].append(todo_task_id)
        
        return todo_task_id
    
    def create_subtask(
        self,
        parent_task_id: str,
        description: str,
        estimate: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        priority: str = "medium"
    ) -> str:
        """Create a subtask under a parent task."""
        
        subtask_id = f"{parent_task_id}_sub_{len([t for t in self.tasks.values() if t.id.startswith(parent_task_id + '_sub')])}"
        
        task = TodoTask(
            id=subtask_id,
            content=description,
            priority=priority,
            estimate=estimate,
            dependencies=dependencies or []
        )
        
        self.tasks[subtask_id] = task
        return subtask_id
    
    def create_milestone_tasks(
        self,
        parent_task_id: str,
        milestones: List[Dict[str, Any]]
    ) -> List[str]:
        """Create milestone tasks for a parent task."""
        
        milestone_ids = []
        for i, milestone in enumerate(milestones):
            dependencies = [milestone_ids[-1]] if i > 0 and milestone_ids else []
            if milestone.get('dependencies'):
                dependencies.extend(milestone['dependencies'])
            
            milestone_id = self.create_subtask(
                parent_task_id,
                milestone['desc'],
                estimate=milestone.get('est'),
                dependencies=dependencies,
                priority=milestone.get('priority', 'medium')
            )
            milestone_ids.append(milestone_id)
        
        return milestone_ids
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update the status of a task."""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        
        if status == "in_progress" and old_status == "pending":
            # Task started
            pass
        elif status == "completed":
            task.completed_at = datetime.now()
        
        return True
    
    def update_task_progress(
        self,
        task_id: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """Update task progress with detailed data."""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.updated_at = datetime.now()
        
        # Store progress data as task metadata (would extend TodoTask class in full implementation)
        if not hasattr(task, 'progress_data'):
            task.progress_data = {}
        task.progress_data.update(progress_data)
        
        return True
    
    def complete_task(
        self,
        task_id: str,
        completion_note: Optional[str] = None
    ) -> bool:
        """Mark a task as completed."""
        
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = "completed"
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        
        if completion_note and not hasattr(task, 'notes'):
            task.notes = []
        if completion_note:
            task.notes.append({
                'timestamp': datetime.now().isoformat(),
                'note': completion_note
            })
        
        return True
    
    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """Get progress information for a task."""
        
        if task_id not in self.tasks:
            return {}
        
        task = self.tasks[task_id]
        
        # Find all subtasks
        subtasks = [t for t in self.tasks.values() if t.id.startswith(task_id + '_sub')]
        completed_subtasks = len([t for t in subtasks if t.status == "completed"])
        total_subtasks = len(subtasks)
        
        progress_percentage = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0
        
        return {
            "task_id": task_id,
            "status": task.status,
            "priority": task.priority,
            "progress_percentage": progress_percentage,
            "completed_subtasks": completed_subtasks,
            "total_subtasks": total_subtasks,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "estimate": task.estimate,
            "dependencies": task.dependencies
        }
    
    def find_all_related_todowrite_tasks(self, task_id: str) -> List[str]:
        """Find all TodoWrite tasks related to a given task ID."""
        
        related_tasks = []
        for todo_id, task in self.tasks.items():
            if task_id in todo_id or task_id in task.content:
                related_tasks.append(todo_id)
        
        return related_tasks
    
    def sync_checklist_to_todowrite(
        self,
        checklist_items: List[Dict[str, Any]],
        parent_task_id: str
    ) -> List[str]:
        """Sync checklist items to TodoWrite tasks."""
        
        todo_ids = []
        for item in checklist_items:
            todo_id = self.create_subtask(
                parent_task_id,
                item['description'],
                estimate=item.get('estimate'),
                dependencies=item.get('dependencies', []),
                priority=item.get('priority', 'medium').lower()
            )
            
            # Update status if not pending
            if item.get('status') != 'PENDING':
                status_map = {
                    'IN_PROGRESS': 'in_progress',
                    'COMPLETED': 'completed',
                    'BLOCKED': 'blocked'
                }
                if item['status'] in status_map:
                    self.update_task_status(todo_id, status_map[item['status']])
            
            todo_ids.append(todo_id)
        
        return todo_ids
    
    def get_command_summary(self, command_name: str) -> Dict[str, Any]:
        """Get summary of all tasks for a command."""
        
        if command_name not in self.command_task_mapping:
            return {}
        
        task_ids = self.command_task_mapping[command_name]
        tasks = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        
        completed = len([t for t in tasks if t.status == "completed"])
        in_progress = len([t for t in tasks if t.status == "in_progress"])
        pending = len([t for t in tasks if t.status == "pending"])
        
        return {
            "command": command_name,
            "total_tasks": len(tasks),
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": (completed / len(tasks) * 100) if tasks else 0,
            "task_ids": task_ids
        }
    
    def export_todowrite_format(self) -> List[Dict[str, Any]]:
        """Export tasks in TodoWrite compatible format."""
        
        todos = []
        for task in self.tasks.values():
            todos.append({
                "content": task.content,
                "status": task.status,
                "priority": task.priority,
                "id": task.id
            })
        
        return todos