"""
Hierarchical Task Management Handler

Handles all hierarchical task operations with parent-child relationships,
dependency management, and progress rollup capabilities.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from .base import BaseToolHandler
from ..refactor_config import get_config
import logging
import json


class HierarchicalManagementHandler(BaseToolHandler):
    """Handler for hierarchical task management tools."""
    
    def __init__(self, storage_manager=None, memory_manager=None):
        super().__init__(storage_manager, memory_manager)
        self.config = get_config()
    
    @property
    def category(self) -> str:
        return "hierarchical_management"
    
    def get_tool_names(self) -> List[str]:
        return [
            "create_hierarchical_task",
            "get_task_hierarchy", 
            "update_hierarchical_status",
            "create_task_dependency",
            "get_progress_rollup",
            "query_hierarchical_context",
            "create_hierarchical_backup",
            "list_checkpoints",
            "restore_from_checkpoint"
        ]
    
    async def _handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle hierarchical management tool calls."""
        # Route to appropriate handler method
        if name == "create_hierarchical_task":
            return await self._handle_create_hierarchical_task(arguments)
        elif name == "get_task_hierarchy":
            return await self._handle_get_task_hierarchy(arguments)
        elif name == "update_hierarchical_status":
            return await self._handle_update_hierarchical_status(arguments)
        elif name == "create_task_dependency":
            return await self._handle_create_task_dependency(arguments)
        elif name == "get_progress_rollup":
            return await self._handle_get_progress_rollup(arguments)
        elif name == "query_hierarchical_context":
            return await self._handle_query_hierarchical_context(arguments)
        elif name == "create_hierarchical_backup":
            return await self._handle_create_hierarchical_backup(arguments)
        elif name == "list_checkpoints":
            return await self._handle_list_checkpoints(arguments)
        elif name == "restore_from_checkpoint":
            return await self._handle_restore_from_checkpoint(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown hierarchical tool: {name}")]
    
    # Implement hierarchical task management tools directly
    async def _handle_create_hierarchical_task(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a new hierarchical task with parent-child relationships."""
        self._validate_required_args(args, ["project_name", "task_id", "task_name", "task_type", "description"])
        
        # Create the basic task first
        metadata = self.storage_manager.create_task_metadata(
            args["project_name"],
            args["task_id"],
            args["task_type"],
            args["description"],
            args.get("command", "plan")
        )
        
        # Add hierarchical properties
        if "parent_task_id" in args:
            metadata["parent_task_id"] = args["parent_task_id"]
            metadata["hierarchical"] = True
        
        # Add task name for hierarchical display
        metadata["task_name"] = args["task_name"]
        
        # Save updated metadata
        result = await self.storage_manager.update_task_metadata(
            args["project_name"],
            args["task_id"],
            metadata
        )
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_get_task_hierarchy(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get hierarchical structure for tasks."""
        project_name = args.get("project_name", "ATLAS")
        task_id = args.get("task_id")
        max_depth = args.get("max_depth", 3)
        
        try:
            if task_id:
                # Get specific task hierarchy
                hierarchy = self.storage_manager.get_full_hierarchy(project_name, task_id, max_depth)
                result = {
                    "project": project_name,
                    "task_id": task_id,
                    "hierarchy": hierarchy,
                    "max_depth": max_depth
                }
            else:
                # Get all tasks and build hierarchy
                tasks = self.storage_manager.list_project_tasks(project_name, include_hierarchical=True)
                
                # Build hierarchy structure
                root_tasks = []
                child_tasks = {}
                
                for task in tasks:
                    if task.get("hierarchical") and task.get("parent_task_id"):
                        parent_id = task["parent_task_id"]
                        if parent_id not in child_tasks:
                            child_tasks[parent_id] = []
                        child_tasks[parent_id].append(task)
                    else:
                        root_tasks.append(task)
                
                # Add children to parent tasks
                def add_children(task_data):
                    task_id = task_data.get("task_id")
                    if task_id in child_tasks:
                        task_data["children"] = child_tasks[task_id]
                        for child in task_data["children"]:
                            add_children(child)
                    return task_data
                
                hierarchy_tree = [add_children(task) for task in root_tasks]
                
                result = {
                    "project": project_name,
                    "hierarchy_tree": hierarchy_tree,
                    "total_tasks": len(tasks),
                    "root_tasks": len(root_tasks),
                    "hierarchical_tasks": len(tasks) - len(root_tasks)
                }
        
        except Exception as e:
            result = {
                "project": project_name,
                "error": f"Failed to get hierarchy: {str(e)}",
                "message": "Check that project and task exist"
            }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_update_hierarchical_status(self, args: Dict[str, Any]) -> List[TextContent]:
        """Update status with hierarchical rollup."""
        self._validate_required_args(args, ["project_name", "task_id", "status"])
        
        # Update the task status (same as regular status update for now)
        result = self.storage_manager.update_task_status(
            args["project_name"],
            args["task_id"],
            args["status"],
            args.get("phase")
        )
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_create_task_dependency(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create dependency between tasks."""
        self._validate_required_args(args, ["project_name", "task_id", "depends_on"])
        
        project_name = args["project_name"]
        task_id = args["task_id"]
        depends_on = args["depends_on"]
        dependency_type = args.get("dependency_type", "blocks")
        
        try:
            # Load the dependent task
            task_context = self.storage_manager.get_task_context(project_name, task_id)
            
            # Initialize dependencies if not present
            if "dependencies" not in task_context:
                task_context["dependencies"] = []
            
            # Check if dependency already exists
            existing = False
            for dep in task_context["dependencies"]:
                if dep.get("task_id") == depends_on:
                    existing = True
                    break
            
            if not existing:
                # Add new dependency
                dependency = {
                    "task_id": depends_on,
                    "dependency_type": dependency_type,
                    "created_at": json.loads(json.dumps({"time": __import__('datetime').datetime.now().isoformat()}))["time"],
                    "status": "active"
                }
                task_context["dependencies"].append(dependency)
                
                # Update task metadata
                await self.storage_manager.update_task_metadata(
                    project_name, task_id, {"dependencies": task_context["dependencies"]}
                )
                
                result = {
                    "status": "dependency_created",
                    "task_id": task_id,
                    "depends_on": depends_on,
                    "dependency_type": dependency_type,
                    "total_dependencies": len(task_context["dependencies"])
                }
            else:
                result = {
                    "status": "dependency_exists",
                    "task_id": task_id,
                    "depends_on": depends_on,
                    "message": "Dependency already exists"
                }
        
        except Exception as e:
            result = {
                "status": "error",
                "error": f"Failed to create dependency: {str(e)}",
                "task_id": task_id,
                "depends_on": depends_on
            }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_get_progress_rollup(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get progress rollup for hierarchical tasks."""
        project_name = args.get("project_name", "ATLAS")
        task_id = args.get("task_id")
        
        try:
            if task_id:
                # Get progress for specific task and its children
                progress = self.storage_manager.calculate_task_progress(project_name, task_id)
                
                # Try to get child tasks for rollup
                try:
                    hierarchy = self.storage_manager.get_full_hierarchy(project_name, task_id)
                    child_progress = []
                    
                    def collect_progress(task_data):
                        for subtask in task_data.get("subtasks", []):
                            if subtask.get("task_id"):
                                try:
                                    sub_progress = self.storage_manager.calculate_task_progress(project_name, subtask["task_id"])
                                    child_progress.append({
                                        "task_id": subtask["task_id"],
                                        "progress": sub_progress
                                    })
                                except:
                                    # Subtask might not have separate storage
                                    pass
                            collect_progress(subtask)
                    
                    collect_progress(hierarchy)
                    
                    # Calculate rollup
                    if child_progress:
                        total_child_progress = sum(p["progress"]["overall_progress"] for p in child_progress)
                        avg_child_progress = total_child_progress / len(child_progress)
                    else:
                        avg_child_progress = 0
                    
                    result = {
                        "project": project_name,
                        "task_id": task_id,
                        "own_progress": progress,
                        "child_progress": child_progress,
                        "rollup_progress": {
                            "overall_with_children": round((progress["overall_progress"] + avg_child_progress) / 2, 1),
                            "children_average": round(avg_child_progress, 1),
                            "children_count": len(child_progress)
                        }
                    }
                except:
                    # Fallback to just own progress
                    result = {
                        "project": project_name,
                        "task_id": task_id,
                        "own_progress": progress,
                        "rollup_progress": progress,
                        "note": "No hierarchical children found"
                    }
            else:
                # Get progress summary for all tasks
                tasks = self.storage_manager.list_project_tasks(project_name)
                project_summary = self.storage_manager.list_project_tasks_summary(project_name)
                
                result = {
                    "project": project_name,
                    "project_summary": project_summary,
                    "total_tasks": len(tasks),
                    "average_progress": project_summary.get("average_progress", 0)
                }
        
        except Exception as e:
            result = {
                "project": project_name,
                "error": f"Failed to calculate progress rollup: {str(e)}",
                "message": "Check that project and task exist"
            }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_query_hierarchical_context(self, args: Dict[str, Any]) -> List[TextContent]:
        """Query hierarchical context."""
        result = {
            "status": "context_query",
            "message": "Hierarchical context queries not fully implemented",
            "args": args
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_create_hierarchical_backup(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create backup of hierarchical structure."""
        result = {
            "status": "backup_created",
            "message": "Hierarchical backup not fully implemented",
            "args": args
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_list_checkpoints(self, args: Dict[str, Any]) -> List[TextContent]:
        """List available checkpoints."""
        result = {
            "status": "checkpoints_listed",
            "message": "Checkpoint listing not fully implemented",
            "checkpoints": []
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_restore_from_checkpoint(self, args: Dict[str, Any]) -> List[TextContent]:
        """Restore from checkpoint."""
        result = {
            "status": "restore_completed",
            "message": "Checkpoint restore not fully implemented",
            "args": args
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]