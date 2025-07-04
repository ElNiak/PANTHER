"""TodoWrite manager for ATLAS command integration."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ..checklist.manager import ChecklistManager


class TodoWriteManager:
    """Manages integration between checklists and TodoWrite system."""
    
    def __init__(self):
        self.checklist_manager = ChecklistManager()
        self.todo_mappings: Dict[str, str] = {}  # checklist_id -> todo_task_id
    
    def create_checklist_todowrite_integration(
        self,
        checklist_items: List[Dict[str, Any]],
        title: str,
        command_name: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Create integrated checklist and TodoWrite tasks."""
        
        # Create checklist
        checklist_id = f"{command_name}_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        checklist_markdown = self.checklist_manager.create_unified_checklist(
            checklist_items, title, checklist_id
        )
        
        # Create TodoWrite tasks from checklist items
        todos = self._convert_checklist_to_todos(checklist_items, command_name, task_id)
        
        # Store mapping
        todo_task_id = f"todo_{checklist_id}"
        self.todo_mappings[checklist_id] = todo_task_id
        
        return {
            "checklist_id": checklist_id,
            "checklist_markdown": checklist_markdown,
            "todo_task_id": todo_task_id,
            "todos": todos,
            "integration_status": "created"
        }
    
    def _convert_checklist_to_todos(
        self,
        checklist_items: List[Dict[str, Any]],
        command_name: str,
        task_id: str
    ) -> List[Dict[str, Any]]:
        """Convert checklist items to TodoWrite format."""
        
        todos = []
        
        # Create main todo task
        main_todo = {
            "content": f"{command_name.capitalize()} command for {task_id}",
            "status": "in_progress",
            "priority": "high",
            "id": f"{command_name}_{task_id}_main"
        }
        todos.append(main_todo)
        
        # Create todos for each checklist item
        for item in checklist_items:
            todo = {
                "content": item['description'],
                "status": self._map_checklist_status_to_todo(item.get('status', 'PENDING')),
                "priority": item.get('priority', 'MEDIUM').lower(),
                "id": f"{command_name}_{task_id}_{item['id']}"
            }
            todos.append(todo)
        
        return todos
    
    def _map_checklist_status_to_todo(self, checklist_status: str) -> str:
        """Map checklist status to TodoWrite status."""
        
        status_map = {
            'PENDING': 'pending',
            'IN_PROGRESS': 'in_progress',
            'COMPLETED': 'completed',
            'BLOCKED': 'pending'  # Map blocked to pending in TodoWrite
        }
        
        return status_map.get(checklist_status, 'pending')
    
    def sync_checklist_progress_to_todowrite(
        self,
        checklist_id: str,
        item_id: str,
        status: str
    ) -> bool:
        """Sync checklist item progress to TodoWrite."""
        
        # Update checklist
        success = self.checklist_manager.update_item_status(checklist_id, item_id, status)
        
        if success and checklist_id in self.todo_mappings:
            # Update corresponding TodoWrite task
            todo_status = self._map_checklist_status_to_todo(status)
            # In a real implementation, this would call the actual TodoWrite API
            return True
        
        return success
    
    def get_integrated_progress(self, checklist_id: str) -> Dict[str, Any]:
        """Get progress that combines checklist and TodoWrite data."""
        
        checklist_progress = self.checklist_manager.get_checklist_progress(checklist_id)
        
        if not checklist_progress:
            return {}
        
        # Add TodoWrite integration status
        integration_data = {
            "checklist_progress": checklist_progress,
            "todowrite_integrated": checklist_id in self.todo_mappings,
            "todo_task_id": self.todo_mappings.get(checklist_id),
            "sync_status": "active" if checklist_id in self.todo_mappings else "none"
        }
        
        return integration_data
    
    def finalize_checklist_todowrite(
        self,
        checklist_id: str,
        completion_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finalize both checklist and TodoWrite tasks."""
        
        # Get final progress
        progress = self.checklist_manager.get_checklist_progress(checklist_id)
        
        if not progress:
            return {"status": "error", "message": "Checklist not found"}
        
        # Mark all items as completed if not already
        incomplete_items = [
            item for item in progress['items'] 
            if item['status'] != 'COMPLETED'
        ]
        
        for item in incomplete_items:
            self.checklist_manager.update_item_status(
                checklist_id, item['id'], 'COMPLETED'
            )
        
        # Finalize TodoWrite tasks
        if checklist_id in self.todo_mappings:
            todo_task_id = self.todo_mappings[checklist_id]
            # In real implementation, would mark TodoWrite tasks as completed
        
        return {
            "status": "completed",
            "checklist_id": checklist_id,
            "todo_task_id": self.todo_mappings.get(checklist_id),
            "completion_note": completion_note,
            "final_progress": self.checklist_manager.get_checklist_progress(checklist_id)
        }
    
    def create_command_workflow_integration(
        self,
        command_name: str,
        task_id: str,
        workflow_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create integrated workflow for a command with both checklist and TodoWrite."""
        
        # Create main checklist for the command
        checklist_integration = self.create_checklist_todowrite_integration(
            workflow_steps,
            f"{command_name.capitalize()} Workflow: {task_id}",
            command_name,
            task_id
        )
        
        # Create workflow milestones
        milestones = []
        for step in workflow_steps:
            milestone = {
                "desc": step['description'],
                "est": step.get('estimate', '15m'),
                "priority": step.get('priority', 'medium'),
                "dependencies": step.get('dependencies', [])
            }
            milestones.append(milestone)
        
        return {
            "workflow_id": f"workflow_{command_name}_{task_id}",
            "checklist_integration": checklist_integration,
            "milestones": milestones,
            "command": command_name,
            "task_id": task_id,
            "created_at": datetime.now().isoformat()
        }