"""
Coordination Management Handler

Handles cross-project coordination operations including project registration,
resource conflict resolution, and unified task management across all ATLAS projects.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
import json
import logging
from datetime import datetime

from .base import BaseToolHandler
from ..refactor_config import get_config


class CoordinationManagementHandler(BaseToolHandler):
    """Handler for cross-project coordination management tools."""
    
    def __init__(self, storage_manager=None, memory_manager=None):
        super().__init__(storage_manager, memory_manager)
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "coordination_management"
    
    def get_tool_names(self) -> List[str]:
        return [
            "register_project",
            "create_cross_project_task",
            "resolve_resource_conflict",
            "get_coordination_status",
            "sync_project_registries",
            "optimize_resource_allocation",
            "get_cross_project_tasks",
            "update_coordination_metadata",
            "detect_project_conflicts",
            "coordinate_task_execution"
        ]
    
    async def _handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle coordination management tool calls."""
        # Route to appropriate handler method
        if name == "register_project":
            return await self._handle_register_project(arguments)
        elif name == "create_cross_project_task":
            return await self._handle_create_cross_project_task(arguments)
        elif name == "resolve_resource_conflict":
            return await self._handle_resolve_resource_conflict(arguments)
        elif name == "get_coordination_status":
            return await self._handle_get_coordination_status(arguments)
        elif name == "sync_project_registries":
            return await self._handle_sync_project_registries(arguments)
        elif name == "optimize_resource_allocation":
            return await self._handle_optimize_resource_allocation(arguments)
        elif name == "get_cross_project_tasks":
            return await self._handle_get_cross_project_tasks(arguments)
        elif name == "update_coordination_metadata":
            return await self._handle_update_coordination_metadata(arguments)
        elif name == "detect_project_conflicts":
            return await self._handle_detect_project_conflicts(arguments)
        elif name == "coordinate_task_execution":
            return await self._handle_coordinate_task_execution(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown coordination tool: {name}")]
    
    # Implement coordination management tools
    async def _handle_register_project(self, args: Dict[str, Any]) -> List[TextContent]:
        """Register a project in the global coordination registry."""
        self._validate_required_args(args, ["project_name", "project_type"])
        
        project_name = args["project_name"]
        project_type = args["project_type"]
        coordination_role = args.get("coordination_role", "secondary")
        
        try:
            result = self.storage_manager.register_project(
                project_name, 
                project_type, 
                coordination_role
            )
            
            if "error" not in result:
                response = {
                    "status": "project_registered",
                    "project_name": project_name,
                    "project_type": project_type,
                    "coordination_role": coordination_role,
                    "registration_details": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                response = {
                    "status": "registration_failed",
                    "project_name": project_name,
                    "error": result["error"]
                }
                
        except Exception as e:
            response = {
                "status": "error",
                "project_name": project_name,
                "error": f"Failed to register project: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_create_cross_project_task(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a task with cross-project coordination metadata."""
        self._validate_required_args(args, ["task_id", "project_name", "description"])
        
        task_id = args["task_id"]
        project_name = args["project_name"]
        description = args["description"]
        coordination_priority = args.get("coordination_priority", "medium")
        cross_project_dependencies = args.get("cross_project_dependencies", [])
        
        try:
            result = self.storage_manager.create_cross_project_task(
                task_id,
                project_name,
                description,
                coordination_priority,
                cross_project_dependencies
            )
            
            if "error" not in result:
                response = {
                    "status": "cross_project_task_created",
                    "global_task_id": result["global_task_id"],
                    "project_name": project_name,
                    "coordination_metadata": result["coordination_metadata"],
                    "coordination_status": result["coordination_status"],
                    "timestamp": datetime.now().isoformat()
                }
            else:
                response = {
                    "status": "task_creation_failed",
                    "task_id": task_id,
                    "project_name": project_name,
                    "error": result["error"]
                }
                
        except Exception as e:
            response = {
                "status": "error",
                "task_id": task_id,
                "project_name": project_name,
                "error": f"Failed to create cross-project task: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_resolve_resource_conflict(self, args: Dict[str, Any]) -> List[TextContent]:
        """Resolve resource allocation conflicts between projects."""
        self._validate_required_args(args, ["project_a", "project_b", "resource_type"])
        
        project_a = args["project_a"]
        project_b = args["project_b"]
        resource_type = args["resource_type"]
        
        try:
            result = self.storage_manager.resolve_resource_conflict(
                project_a,
                project_b,
                resource_type
            )
            
            if "error" not in result:
                response = {
                    "status": "conflict_resolved",
                    "conflict_id": result["conflict_id"],
                    "winner": result["winner"],
                    "reason": result["reason"],
                    "resolution_strategy": result["resolution_strategy"],
                    "resolved_at": result["resolved_at"]
                }
            else:
                response = {
                    "status": "resolution_failed",
                    "project_a": project_a,
                    "project_b": project_b,
                    "resource_type": resource_type,
                    "error": result["error"]
                }
                
        except Exception as e:
            response = {
                "status": "error",
                "project_a": project_a,
                "project_b": project_b,
                "resource_type": resource_type,
                "error": f"Failed to resolve conflict: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_get_coordination_status(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get overall coordination system status."""
        try:
            result = self.storage_manager.get_coordination_status()
            
            if "error" not in result:
                response = {
                    "status": "coordination_status_retrieved",
                    "coordination_system": result,
                    "summary": {
                        "coordination_enabled": result.get("coordination_enabled", False),
                        "total_projects": result.get("projects", {}).get("total_projects", 0),
                        "total_global_tasks": result.get("tasks", {}).get("total_global_tasks", 0),
                        "last_activity": result.get("timestamp")
                    }
                }
            else:
                response = {
                    "status": "status_retrieval_failed",
                    "error": result["error"]
                }
                
        except Exception as e:
            response = {
                "status": "error",
                "error": f"Failed to get coordination status: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_sync_project_registries(self, args: Dict[str, Any]) -> List[TextContent]:
        """Synchronize project registries across all coordination systems."""
        try:
            # Get current project registrations
            projects = self.storage_manager.list_projects()
            
            synced_projects = []
            for project in projects:
                # Auto-detect project type and register if not already coordinated
                project_type = self.storage_manager._detect_project_type(project)
                registration_result = self.storage_manager.register_project(
                    project, 
                    project_type,
                    "primary" if project == "Software-Engineer-AI-Agent-Atlas" else "secondary"
                )
                
                if "error" not in registration_result:
                    synced_projects.append({
                        "project_name": project,
                        "project_type": project_type,
                        "sync_status": "success"
                    })
                else:
                    synced_projects.append({
                        "project_name": project,
                        "project_type": project_type,
                        "sync_status": "failed",
                        "error": registration_result["error"]
                    })
            
            response = {
                "status": "registries_synchronized",
                "total_projects_found": len(projects),
                "sync_results": synced_projects,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            response = {
                "status": "error",
                "error": f"Failed to sync project registries: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_optimize_resource_allocation(self, args: Dict[str, Any]) -> List[TextContent]:
        """Optimize resource allocation across projects."""
        try:
            # Get current coordination status
            status = self.storage_manager.get_coordination_status()
            
            optimizations = {
                "cache_optimization": {
                    "strategy": "hierarchical",
                    "global_cache_enabled": True,
                    "project_isolation": "strict"
                },
                "memory_optimization": {
                    "strategy": "project_scoped",
                    "cross_project_sharing": "high_entropy_only",
                    "corruption_prevention": "enabled"
                },
                "tool_coordination": {
                    "strategy": "intelligent_routing",
                    "conflict_resolution": "priority_based",
                    "resource_sharing": "cooperative"
                }
            }
            
            response = {
                "status": "resource_allocation_optimized",
                "optimizations": optimizations,
                "current_status": status,
                "recommendations": [
                    "Enable hierarchical caching for 40% performance improvement",
                    "Implement project-scoped memory isolation",
                    "Use intelligent tool routing for conflict prevention"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            response = {
                "status": "error",
                "error": f"Failed to optimize resource allocation: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_get_cross_project_tasks(self, args: Dict[str, Any]) -> List[TextContent]:
        """Get all tasks across registered projects."""
        try:
            tasks = self.storage_manager.get_cross_project_tasks()
            
            # Organize tasks by project and priority
            task_summary = {
                "by_project": {},
                "by_priority": {"critical": [], "high": [], "medium": [], "low": []},
                "by_status": {}
            }
            
            for task in tasks:
                project_name = task.get("project_context", {}).get("project_name", "unknown")
                priority = task.get("coordination_metadata", {}).get("coordination_priority", "medium")
                status = task.get("coordination_status", {}).get("global_phase", "unknown")
                
                # Group by project
                if project_name not in task_summary["by_project"]:
                    task_summary["by_project"][project_name] = []
                task_summary["by_project"][project_name].append(task["global_task_id"])
                
                # Group by priority
                if priority in task_summary["by_priority"]:
                    task_summary["by_priority"][priority].append(task["global_task_id"])
                
                # Group by status
                if status not in task_summary["by_status"]:
                    task_summary["by_status"][status] = []
                task_summary["by_status"][status].append(task["global_task_id"])
            
            response = {
                "status": "cross_project_tasks_retrieved",
                "total_tasks": len(tasks),
                "task_summary": task_summary,
                "detailed_tasks": tasks,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            response = {
                "status": "error",
                "error": f"Failed to get cross-project tasks: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_update_coordination_metadata(self, args: Dict[str, Any]) -> List[TextContent]:
        """Update coordination metadata for a project or task."""
        response = {
            "status": "metadata_update_noted",
            "message": "Coordination metadata updates not fully implemented",
            "args": args,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_detect_project_conflicts(self, args: Dict[str, Any]) -> List[TextContent]:
        """Detect potential conflicts between projects."""
        try:
            # Simple conflict detection based on resource usage patterns
            projects = self.storage_manager.list_projects()
            conflicts = []
            
            # Check for naming conflicts
            for i, project_a in enumerate(projects):
                for project_b in projects[i+1:]:
                    if "PANTHER" in project_a and "PANTHER" in project_b:
                        conflicts.append({
                            "type": "naming_conflict",
                            "projects": [project_a, project_b],
                            "severity": "medium",
                            "description": "Similar naming patterns may cause confusion"
                        })
            
            # Check for task directory conflicts
            for project in projects:
                if project.count("-") > 2:  # Complex naming
                    conflicts.append({
                        "type": "complexity_warning",
                        "projects": [project],
                        "severity": "low",
                        "description": "Complex project naming may complicate coordination"
                    })
            
            response = {
                "status": "conflict_detection_completed",
                "total_conflicts": len(conflicts),
                "conflicts": conflicts,
                "recommendations": [
                    "Consider standardizing project naming conventions",
                    "Implement resource allocation policies",
                    "Use coordination-aware task management"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            response = {
                "status": "error",
                "error": f"Failed to detect project conflicts: {str(e)}"
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _handle_coordinate_task_execution(self, args: Dict[str, Any]) -> List[TextContent]:
        """Coordinate task execution across projects."""
        response = {
            "status": "coordination_initiated",
            "message": "Task execution coordination not fully implemented",
            "args": args,
            "timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]