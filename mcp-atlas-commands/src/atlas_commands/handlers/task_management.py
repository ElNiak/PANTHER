"""
Task management tool handlers.

Handles: create_task_metadata, update_task_status, add_task_artifact, 
get_task_context, list_project_tasks, create_task_backup, archive_task, 
filter_tasks, calculate_task_progress
"""

from typing import Dict, Any, List
from mcp.types import TextContent
import json
import logging
from datetime import datetime

from .base import BaseToolHandler
from ..refactor_config import get_config
from ..token_optimization import ContentType


class TaskManagementHandler(BaseToolHandler):
    """Handler for basic task management operations."""
    
    def __init__(self, storage_manager=None, memory_manager=None):
        super().__init__(storage_manager, memory_manager)
        self.config = get_config()
    
    @property
    def category(self) -> str:
        return "task_management"
    
    def get_tool_names(self) -> List[str]:
        return [
            "create_task_metadata",
            "update_task_status", 
            "add_task_artifact",
            "get_task_context",
            "list_project_tasks",
            "create_task_backup",
            "archive_task", 
            "filter_tasks",
            "calculate_task_progress",
            "test_simple_tool"  # Add test tool
        ]
    
    async def _handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle task management tool calls with improved error handling."""
        # Route to appropriate handler method
        if name == "create_task_metadata":
            return await self._handle_create_task_metadata(arguments)
        elif name == "update_task_status":
            return await self._handle_update_task_status(arguments)
        elif name == "add_task_artifact":
            return await self._handle_add_task_artifact(arguments)
        elif name == "get_task_context":
            return await self._handle_get_task_context(arguments)
        elif name == "list_project_tasks":
            return await self._handle_list_project_tasks(arguments)
        elif name == "create_task_backup":
            return await self._handle_create_task_backup(arguments)
        elif name == "archive_task":
            return await self._handle_archive_task(arguments)
        elif name == "filter_tasks":
            return await self._handle_filter_tasks(arguments)
        elif name == "calculate_task_progress":
            return await self._handle_calculate_task_progress(arguments)
        elif name == "test_simple_tool":
            return await self._handle_test_simple_tool(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown task management tool: {name}")]

    
    async def _handle_create_task_metadata(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle task metadata creation with persistence and memory integration."""
        self._validate_required_args(args, ["project_name", "task_id", "task_type", "description"])
        
        try:
            metadata = self.storage_manager.create_task_metadata(
                args["project_name"],
                args["task_id"],
                args["task_type"],
                args["description"],
                args.get("command", "plan")
            )
            
            return [TextContent(type="text", text=json.dumps(metadata, indent=2))]
        except Exception as e:
            self.logger.error(f"Error creating task metadata: {str(e)}")
            return [TextContent(type="text", text=f"Error creating task metadata: {str(e)}")]
    
    async def _handle_update_task_status(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle task status updates with persistence."""
        self._validate_required_args(args, ["project_name", "task_id", "status"])
        
        try:
            result = self.storage_manager.update_task_status(
                args["project_name"],
                args["task_id"], 
                args["status"],
                args.get("phase")
            )
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            self.logger.error(f"Error updating task status: {str(e)}")
            return [TextContent(type="text", text=f"Error updating task status: {str(e)}")]
    
    async def _handle_add_task_artifact(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle adding artifacts to tasks with JSON serialization support."""
        self._validate_required_args(args, ["project_name", "task_id", "artifact_type", "content", "filename"])
        
        try:
            content = args["content"]
            
            # Handle JSON serialization for dict/list content
            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)
            elif not isinstance(content, str):
                content = str(content)
            
            result = self.storage_manager.add_task_artifact(
                args["project_name"],
                args["task_id"],
                args["artifact_type"],
                content,
                args["filename"],
                args.get("description", "")
            )
            
            result_data = {"artifact_path": result, "status": "success"}
            return [TextContent(type="text", text=json.dumps(result_data, indent=2))]
        except Exception as e:
            self.logger.error(f"Error adding task artifact: {str(e)}")
            return [TextContent(type="text", text=f"Error adding task artifact: {str(e)}")]
    
    async def _handle_get_task_context(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle retrieving full task context - with comprehensive debugging."""
        self._validate_required_args(args, ["project_name", "task_id"])
        
        try:
            self.logger.info(f"Getting task context for {args}")
            
            project_name = args["project_name"]
            task_id = args["task_id"]
            
            # Direct implementation of get_task_context logic without cache
            root = self.storage_manager.get_task_root(project_name, task_id)
            metadata_path = root / "task.json"
            
            self.logger.info(f"Looking for task file at: {metadata_path}")
            
            if not metadata_path.exists():
                self.logger.warning(f"Task file not found at {metadata_path}")
                # Create a minimal task context for testing
                context = {
                    "task_id": task_id,
                    "project_name": project_name,
                    "status": "not_found",
                    "message": "Task metadata file not found",
                    "retrieved_at": datetime.now().isoformat()
                }
                result = [TextContent(type="text", text=json.dumps(context, indent=2))]
                self.logger.info(f"Returning not found result: {type(result)}")
                return result
            
            with open(metadata_path, 'r') as f:
                context = json.load(f)
            
            # Add artifact summary like the original method
            context["artifact_summary"] = {}
            for artifact_type, artifacts in context.get("artifacts", {}).items():
                context["artifact_summary"][artifact_type] = len(artifacts)
            
            # Add retrieval timestamp
            context["retrieved_at"] = datetime.now().isoformat()
            
            result = [TextContent(type="text", text=json.dumps(context, indent=2))]
            self.logger.info(f"Returning success result: {type(result)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting task context: {str(e)}")
            result = [TextContent(type="text", text=f"Error getting task context: {str(e)}")]
            self.logger.info(f"Returning error result: {type(result)}")
            return result
    
    async def _handle_list_project_tasks(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle listing tasks for a project including hierarchical tasks."""
        try:
            project_name = args.get("project_name", "ATLAS")
            include_hierarchical = args.get("include_hierarchical", True)
            
            # Get all tasks - use empty list if storage manager not available
            if not self.storage_manager:
                response_data = {
                    "error": "Storage manager not available",
                    "project_name": project_name,
                    "tasks": [],
                    "total_tasks": 0
                }
                return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
            
            # Get tasks from storage with hierarchical support
            all_tasks = self.storage_manager.list_project_tasks(project_name, include_hierarchical)
            
            # Enhanced task compression to show hierarchical structure
            compressed_tasks = []
            for task in all_tasks[:20]:  # Increased limit to show more tasks
                compressed_task = {
                    "id": task.get("task_id", "unknown"),
                    "type": task.get("task_type", "task"),
                    "status": task.get("status", "unknown"),
                    "created": task.get("created_at", "")[:10] if task.get("created_at") else ""
                }
                
                # Add hierarchical information if present
                if task.get("hierarchical", False):
                    compressed_task["hierarchical"] = True
                    if task.get("parent_task_id"):
                        compressed_task["parent"] = task.get("parent_task_id")
                
                compressed_tasks.append(compressed_task)
            
            response_data = {
                "project_name": project_name,
                "tasks": compressed_tasks,
                "total_tasks": len(all_tasks),
                "showing": len(compressed_tasks),
                "hierarchical_included": include_hierarchical,
                "timestamp": datetime.now().isoformat()
            }
            
            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error listing tasks: {str(e)}")
            return [TextContent(type="text", text=f"Error listing tasks: {str(e)}")]
    
    async def _handle_create_task_backup(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle creating task backups."""
        self._validate_required_args(args, ["project_name", "task_id"])
        
        result = self.storage_manager.create_task_backup(
            args["project_name"],
            args["task_id"],
            args.get("backup_type", "checkpoint"),
            args.get("description", "")
        )
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_archive_task(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle archiving completed tasks."""
        self._validate_required_args(args, ["project_name", "task_id"])
        
        result = self.storage_manager.archive_task(
            args["project_name"],
            args["task_id"],
            args.get("keep_backups", True)
        )
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_filter_tasks(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle filtering tasks with advanced criteria."""
        tasks = self.storage_manager.filter_tasks(
            project_name=args.get("project_name"),
            status=args.get("status"),
            task_type=args.get("task_type"), 
            priority=args.get("priority"),
            days_old=args.get("days_old"),
            ready_only=args.get("ready_only", False),
            blocked_only=args.get("blocked_only", False)
        )
        
        return [TextContent(type="text", text=json.dumps(tasks, indent=2))]
    
    async def _handle_calculate_task_progress(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle calculating detailed task progress."""
        self._validate_required_args(args, ["project_name", "task_id"])
        
        progress = self.storage_manager.calculate_task_progress(
            args["project_name"],
            args["task_id"]
        )
        
        return [TextContent(type="text", text=json.dumps(progress, indent=2))]
    
    def _compress_task_list(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress task data to essential fields only."""
        compressed = []
        for task in tasks:
            # Extract only essential fields to minimize tokens
            essential_task = {
                "id": task.get("task_id", "unknown"),
                "name": task.get("task_name", task.get("description", "")[:50] + "..."),
                "type": task.get("task_type", "task"),
                "status": task.get("status", "unknown"),
                "priority": task.get("priority", "medium"),
                "created": task.get("created_at", "")[:10],  # Date only, no time
                "progress": task.get("completion_percentage", 0),
                "phase": task.get("current_phase", "")
            }
            
            # Remove empty fields to save tokens
            essential_task = {k: v for k, v in essential_task.items() if v not in ["", None, 0]}
            
            compressed.append(essential_task)
        
        return compressed
    
    async def _handle_test_simple_tool(self, args: Dict[str, Any]) -> List[TextContent]:
        """Simple test tool to verify async handling works correctly."""
        result = {
            "status": "success",
            "message": "Test tool working correctly",
            "args_received": args,
            "timestamp": datetime.now().isoformat()
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]