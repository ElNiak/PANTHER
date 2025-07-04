"""Main MCP server for ATLAS command system."""

import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel

from .checklist.manager import ChecklistManager
from .checklist.templates import ChecklistTemplates
from .todowrite.integration import TodoWriteIntegration
from .todowrite.manager import TodoWriteManager
from .memory.graph_manager import MemoryGraphManager
from .memory.pattern_tracker import PatternTracker
from .workflow.enforcer import WorkflowEnforcer
from .workflow.validator import CommandValidator


class EnhancedAtlasCommandsServer:
    """MCP server providing ATLAS command utilities."""
    
    def __init__(self):
        self.server = Server("atlas-commands")
        self.checklist_manager = ChecklistManager()
        self.checklist_templates = ChecklistTemplates()
        self.todowrite_integration = TodoWriteIntegration()
        self.todowrite_manager = TodoWriteManager()
        self.memory_manager = MemoryGraphManager()
        self.pattern_tracker = PatternTracker()
        self.workflow_enforcer = WorkflowEnforcer()
        self.command_validator = CommandValidator()
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Register the list_tools handler
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="create_unified_checklist",
                    description="Create a unified checklist with consistent formatting and TodoWrite integration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command_name": {"type": "string", "description": "Name of the command (plan, execute, verify, complete)"},
                            "task_id": {"type": "string", "description": "Task identifier"},
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "description": {"type": "string"},
                                        "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                                        "estimate": {"type": "string"},
                                        "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED"]},
                                        "dependencies": {"type": "array", "items": {"type": "string"}}
                                    },
                                    "required": ["id", "description"]
                                }
                            },
                            "title": {"type": "string", "description": "Checklist title"},
                            "template_type": {"type": "string", "description": "Template type if using predefined template"}
                        },
                        "required": ["command_name", "task_id", "title"]
                    }
                ),
                Tool(
                    name="update_checklist_item",
                    description="Update the status of a checklist item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "checklist_id": {"type": "string"},
                            "item_id": {"type": "string"},
                            "status": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED"]},
                            "notes": {"type": "string"}
                        },
                        "required": ["checklist_id", "item_id", "status"]
                    }
                ),
                Tool(
                    name="get_checklist_progress",
                    description="Get progress summary for a checklist",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "checklist_id": {"type": "string"}
                        },
                        "required": ["checklist_id"]
                    }
                ),
                Tool(
                    name="create_todowrite_integration",
                    description="Create integrated checklist and TodoWrite tasks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command_name": {"type": "string"},
                            "task_id": {"type": "string"},
                            "title": {"type": "string"},
                            "checklist_items": {"type": "array"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                            "estimate": {"type": "string"}
                        },
                        "required": ["command_name", "task_id", "title", "checklist_items"]
                    }
                ),
                Tool(
                    name="create_memory_entity",
                    description="Create a standardized memory graph entity for command execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command_type": {"type": "string"},
                            "target": {"type": "string"},
                            "observations": {"type": "array", "items": {"type": "string"}},
                            "pattern": {"type": "string"},
                            "step": {"type": "string"},
                            "focus": {"type": "string"},
                            "approach": {"type": "string"},
                            "subtask": {"type": "string"},
                            "level": {"type": "string"}
                        },
                        "required": ["command_type", "target", "observations"]
                    }
                ),
                Tool(
                    name="create_workflow",
                    description="Create a workflow with validation and enforcement",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {"type": "string"},
                            "pattern": {"type": "string", "enum": ["explore-plan-code-commit", "quick-fix", "refactor", "tdd"]},
                            "target": {"type": "string"},
                            "flags": {"type": "object"}
                        },
                        "required": ["workflow_id", "pattern", "target"]
                    }
                ),
                Tool(
                    name="validate_command",
                    description="Validate command parameters and execution context",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"},
                            "parameters": {"type": "object"},
                            "context": {"type": "object"}
                        },
                        "required": ["command", "parameters"]
                    }
                ),
                Tool(
                    name="track_command_pattern",
                    description="Record command execution for pattern learning",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command_type": {"type": "string"},
                            "target": {"type": "string"},
                            "parameters": {"type": "object"},
                            "outcome": {"type": "string", "enum": ["success", "failure", "partial"]},
                            "metrics": {"type": "object"},
                            "observations": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["command_type", "target", "outcome", "observations"]
                    }
                ),
                Tool(
                    name="get_pattern_recommendations",
                    description="Get pattern-based recommendations for command execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command_type": {"type": "string"},
                            "target": {"type": "string"},
                            "context": {"type": "object"}
                        },
                        "required": ["command_type", "target"]
                    }
                ),
                Tool(
                    name="compact_memory_graph",
                    description="Compact old memory graph entities based on entropy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_old": {"type": "integer", "default": 30},
                            "keep_important": {"type": "boolean", "default": True}
                        }
                    }
                ),
                Tool(
                    name="orchestrate_intelligent_tasks",
                    description="Intelligent task creation, dependency detection, and execution orchestration based on command patterns",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_context": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "complexity": {"type": "string", "enum": ["simple", "moderate", "complex"]},
                                    "domain": {"type": "string"},
                                    "target": {"type": "string"}
                                },
                                "required": ["description", "complexity", "domain"]
                            },
                            "orchestration_options": {
                                "type": "object",
                                "properties": {
                                    "auto_decompose": {"type": "boolean", "default": True},
                                    "detect_dependencies": {"type": "boolean", "default": True},
                                    "suggest_workflow": {"type": "boolean", "default": True},
                                    "create_subtasks": {"type": "boolean", "default": False}
                                }
                            },
                            "project_name": {"type": "string", "default": "ATLAS"}
                        },
                        "required": ["task_context"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            
            try:
                if name == "create_unified_checklist":
                    return await self._handle_create_unified_checklist(arguments)
                elif name == "update_checklist_item":
                    return await self._handle_update_checklist_item(arguments)
                elif name == "get_checklist_progress":
                    return await self._handle_get_checklist_progress(arguments)
                elif name == "create_todowrite_integration":
                    return await self._handle_create_todowrite_integration(arguments)
                elif name == "create_memory_entity":
                    return await self._handle_create_memory_entity(arguments)
                elif name == "create_workflow":
                    return await self._handle_create_workflow(arguments)
                elif name == "validate_command":
                    return await self._handle_validate_command(arguments)
                elif name == "track_command_pattern":
                    return await self._handle_track_command_pattern(arguments)
                elif name == "get_pattern_recommendations":
                    return await self._handle_get_pattern_recommendations(arguments)
                elif name == "compact_memory_graph":
                    return await self._handle_compact_memory_graph(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
            except Exception as e:
                return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]
    
    async def _handle_create_unified_checklist(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle unified checklist creation."""
        
        command_name = args["command_name"]
        task_id = args["task_id"]
        title = args["title"]
        
        # Use template if specified, otherwise use provided items
        if "template_type" in args:
            items = self.checklist_templates.get_template_by_command(
                command_name, 
                task_id=task_id,
                **args.get("template_params", {})
            )
        else:
            items = args.get("items", [])
        
        # Create checklist
        checklist_markdown = self.checklist_manager.create_unified_checklist(
            items, title
        )
        
        # Create TodoWrite integration
        integration = self.todowrite_manager.create_checklist_todowrite_integration(
            items, title, command_name, task_id
        )
        
        result = {
            "checklist_markdown": checklist_markdown,
            "checklist_id": integration["checklist_id"],
            "todowrite_integration": integration,
            "item_count": len(items)
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_update_checklist_item(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle checklist item update."""
        
        success = self.checklist_manager.update_item_status(
            args["checklist_id"],
            args["item_id"],
            args["status"],
            args.get("notes")
        )
        
        # Sync to TodoWrite
        if success:
            self.todowrite_manager.sync_checklist_progress_to_todowrite(
                args["checklist_id"],
                args["item_id"],
                args["status"]
            )
        
        result = {
            "success": success,
            "checklist_id": args["checklist_id"],
            "item_id": args["item_id"],
            "new_status": args["status"]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_get_checklist_progress(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle checklist progress request."""
        
        progress = self.todowrite_manager.get_integrated_progress(args["checklist_id"])
        
        return [TextContent(type="text", text=json.dumps(progress, indent=2))]
    
    async def _handle_create_todowrite_integration(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle TodoWrite integration creation."""
        
        integration = self.todowrite_manager.create_checklist_todowrite_integration(
            args["checklist_items"],
            args["title"],
            args["command_name"],
            args["task_id"]
        )
        
        return [TextContent(type="text", text=json.dumps(integration, indent=2))]
    
    async def _handle_create_memory_entity(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle memory entity creation."""
        
        entity_name = self.memory_manager.create_command_entity(
            args["command_type"],
            args["target"],
            args["observations"],
            **{k: v for k, v in args.items() if k not in ["command_type", "target", "observations"]}
        )
        
        result = {
            "entity_name": entity_name,
            "command_type": args["command_type"],
            "target": args["target"],
            "observation_count": len(args["observations"])
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_create_workflow(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle workflow creation."""
        
        steps = self.workflow_enforcer.create_workflow(
            args["workflow_id"],
            args["pattern"],
            args["target"],
            args.get("flags")
        )
        
        result = {
            "workflow_id": args["workflow_id"],
            "pattern": args["pattern"],
            "target": args["target"],
            "step_count": len(steps),
            "steps": [
                {
                    "command": step.command,
                    "target": step.target,
                    "parameters": step.parameters,
                    "prerequisites": step.prerequisites
                }
                for step in steps
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_validate_command(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle command validation."""
        
        validation_results = self.command_validator.validate_command(
            args["command"],
            args["parameters"],
            args.get("context")
        )
        
        summary = self.command_validator.get_validation_summary(validation_results)
        
        result = {
            "command": args["command"],
            "validation_summary": summary,
            "can_proceed": summary["can_proceed"],
            "validation_details": [
                {
                    "valid": r.valid,
                    "level": r.level.value,
                    "message": r.message,
                    "suggestion": r.suggestion
                }
                for r in validation_results
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_track_command_pattern(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle command pattern tracking."""
        
        execution_id = self.pattern_tracker.record_command_execution(
            args["command_type"],
            args["target"],
            args.get("parameters", {}),
            args["outcome"],
            args.get("metrics", {}),
            args["observations"]
        )
        
        result = {
            "execution_id": execution_id,
            "command_type": args["command_type"],
            "target": args["target"],
            "outcome": args["outcome"],
            "tracked": True
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_get_pattern_recommendations(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle pattern recommendations request."""
        
        recommendations = self.pattern_tracker.get_pattern_recommendations(
            args["command_type"],
            args["target"],
            args.get("context", {})
        )
        
        result = {
            "command_type": args["command_type"],
            "target": args["target"],
            "recommendation_count": len(recommendations),
            "recommendations": recommendations
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def _handle_compact_memory_graph(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle memory graph compaction."""
        
        compaction_result = self.memory_manager.compact_old_entities(
            args.get("days_old", 30),
            args.get("keep_important", True)
        )
        
        return [TextContent(type="text", text=json.dumps(compaction_result, indent=2))]


async def main():
    """Main server entry point."""
    server = EnhancedAtlasCommandsServer()
    
    # Run the server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())