"""
Workflow Intelligence Handler

Handles intelligent task orchestration, command recommendations,
workflow pattern analysis, and progress milestone tracking.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from ..tool_registry import ToolHandler
from ..refactor_config import get_config
import logging


class WorkflowIntelligenceHandler(ToolHandler):
    """Handler for workflow intelligence and automation tools."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "workflow_intelligence"
    
    def get_tool_names(self) -> List[str]:
        return [
            "orchestrate_intelligent_tasks",
            "adaptive_command_selection",
            "analyze_workflow_patterns",
            "track_progress_milestones"
        ]
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle workflow intelligence tool calls."""
        try:
            if self.config.enable_consistent_error_handling:
                self.logger.info(f"Processing workflow intelligence tool: {name}")
            
            # Route to appropriate handler method
            if name == "orchestrate_intelligent_tasks":
                return await self._handle_orchestrate_intelligent_tasks(arguments)
            elif name == "adaptive_command_selection":
                return await self._handle_adaptive_command_selection(arguments)
            elif name == "analyze_workflow_patterns":
                return await self._handle_analyze_workflow_patterns(arguments)
            elif name == "track_progress_milestones":
                return await self._handle_track_progress_milestones(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown workflow intelligence tool: {name}")]
                
        except Exception as e:
            error_msg = f"Error in workflow intelligence handler for {name}: {str(e)}"
            self.logger.error(error_msg)
            if self.config.enable_consistent_error_handling:
                return [TextContent(type="text", text=f"Workflow Intelligence Error: {str(e)}")]
            else:
                raise e
    
    # Delegate to existing server methods with consistent error handling
    async def _handle_orchestrate_intelligent_tasks(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_orchestrate_intelligent_tasks(arguments)
    
    async def _handle_adaptive_command_selection(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle intelligent adaptive command selection with context analysis."""
        import re
        from datetime import datetime
        
        try:
            task_description = arguments.get("task_description", "")
            domain = arguments.get("domain", "general")
            previous_commands = arguments.get("previous_commands", [])
            project_name = arguments.get("project_name", "")
            
            # Initialize recommendation engine
            recommendations = []
            context_analysis = {
                "task_complexity": "unknown",
                "workflow_stage": "unknown",
                "system_state_requirements": [],
                "dependency_chain": [],
                "risk_factors": []
            }
            
            # 1. Advanced Task Analysis
            description_lower = task_description.lower()
            
            # Complexity assessment
            complexity_indicators = {
                "simple": ["test", "check", "get", "list", "show", "view"],
                "medium": ["create", "update", "modify", "analyze", "validate", "configure"],
                "complex": ["migrate", "refactor", "optimize", "integrate", "troubleshoot", "debug"]
            }
            
            task_complexity = "simple"
            for complexity, keywords in complexity_indicators.items():
                if any(keyword in description_lower for keyword in keywords):
                    task_complexity = complexity
            
            context_analysis["task_complexity"] = task_complexity
            
            # Workflow stage detection
            stage_indicators = {
                "planning": ["plan", "design", "analyze", "investigate", "research"],
                "implementation": ["create", "build", "implement", "develop", "code"],
                "testing": ["test", "validate", "verify", "check", "debug"],
                "deployment": ["deploy", "release", "publish", "launch"],
                "maintenance": ["fix", "update", "optimize", "monitor", "maintain"]
            }
            
            workflow_stage = "planning"
            for stage, keywords in stage_indicators.items():
                if any(keyword in description_lower for keyword in keywords):
                    workflow_stage = stage
                    break
            
            context_analysis["workflow_stage"] = workflow_stage
            
            # 2. System State Analysis
            system_requirements = []
            
            # Check if storage operations needed
            if any(keyword in description_lower for keyword in ["task", "project", "save", "store", "create", "update"]):
                system_requirements.append("storage_manager")
            
            # Check if cache operations needed
            if any(keyword in description_lower for keyword in ["cache", "performance", "speed", "fast", "optimize"]):
                system_requirements.append("cache_manager")
            
            # Check if memory operations needed
            if any(keyword in description_lower for keyword in ["memory", "analytics", "health", "monitor", "system"]):
                system_requirements.append("memory_manager")
            
            # Check if validation needed
            if any(keyword in description_lower for keyword in ["validate", "check", "verify", "standards", "quality"]):
                system_requirements.append("validation")
            
            context_analysis["system_state_requirements"] = system_requirements
            
            # 3. Intelligent Command Recommendations Based on Context
            
            # Workflow-stage based recommendations
            if workflow_stage == "planning":
                if "project" in description_lower or "task" in description_lower:
                    recommendations.append({
                        "command": "list_project_tasks",
                        "confidence": 0.85,
                        "reason": "Planning phase - review existing tasks to avoid duplication",
                        "category": "context_planning"
                    })
                    recommendations.append({
                        "command": "search_similar_tasks",
                        "confidence": 0.80,
                        "reason": "Planning phase - find similar work patterns for guidance",
                        "category": "context_planning"
                    })
                
                recommendations.append({
                    "command": "memory_health_check",
                    "confidence": 0.75,
                    "reason": "Planning phase - ensure system is ready for upcoming work",
                    "category": "context_planning"
                })
            
            elif workflow_stage == "implementation":
                recommendations.append({
                    "command": "create_task_metadata",
                    "confidence": 0.90,
                    "reason": "Implementation phase - structure work with proper task tracking",
                    "category": "context_implementation"
                })
                
                if task_complexity in ["medium", "complex"]:
                    recommendations.append({
                        "command": "create_hierarchical_task",
                        "confidence": 0.85,
                        "reason": "Complex implementation - break down into subtasks",
                        "category": "context_implementation"
                    })
                
                recommendations.append({
                    "command": "validate_code_standards",
                    "confidence": 0.70,
                    "reason": "Implementation phase - maintain quality standards",
                    "category": "context_implementation"
                })
            
            elif workflow_stage == "testing":
                recommendations.append({
                    "command": "memory_health_check",
                    "confidence": 0.85,
                    "reason": "Testing phase - verify system health before testing",
                    "category": "context_testing"
                })
                recommendations.append({
                    "command": "get_cache_stats",
                    "confidence": 0.80,
                    "reason": "Testing phase - monitor performance during tests",
                    "category": "context_testing"
                })
                recommendations.append({
                    "command": "add_task_artifact",
                    "confidence": 0.75,
                    "reason": "Testing phase - document test results and findings",
                    "category": "context_testing"
                })
            
            elif workflow_stage == "maintenance":
                recommendations.append({
                    "command": "memory_analytics",
                    "confidence": 0.90,
                    "reason": "Maintenance phase - comprehensive system analysis",
                    "category": "context_maintenance"
                })
                recommendations.append({
                    "command": "get_cache_stats",
                    "confidence": 0.85,
                    "reason": "Maintenance phase - check cache performance",
                    "category": "context_maintenance"
                })
                recommendations.append({
                    "command": "list_project_tasks",
                    "confidence": 0.70,
                    "reason": "Maintenance phase - review task completion status",
                    "category": "context_maintenance"
                })
            
            # 4. Domain-specific expert recommendations
            domain_expertise = {
                "debugging": [
                    {"command": "memory_analytics", "confidence": 0.95, "reason": "Debug: Comprehensive system analysis for issue identification"},
                    {"command": "get_task_context", "confidence": 0.90, "reason": "Debug: Understand current task state and history"},
                    {"command": "search_similar_tasks", "confidence": 0.80, "reason": "Debug: Find patterns in similar issues"}
                ],
                "performance": [
                    {"command": "memory_analytics", "confidence": 0.95, "reason": "Performance: Deep analysis of system resource usage"},
                    {"command": "get_cache_stats", "confidence": 0.90, "reason": "Performance: Cache performance optimization"},
                    {"command": "memory_health_check", "confidence": 0.85, "reason": "Performance: System health baseline"}
                ],
                "development": [
                    {"command": "validate_code_standards", "confidence": 0.85, "reason": "Development: Maintain code quality"},
                    {"command": "create_task_metadata", "confidence": 0.80, "reason": "Development: Structure development work"},
                    {"command": "list_project_tasks", "confidence": 0.75, "reason": "Development: Review existing development tasks"}
                ],
                "testing": [
                    {"command": "memory_health_check", "confidence": 0.90, "reason": "Testing: Verify system readiness"},
                    {"command": "add_task_artifact", "confidence": 0.85, "reason": "Testing: Document test results"},
                    {"command": "get_cache_stats", "confidence": 0.80, "reason": "Testing: Monitor performance during tests"}
                ]
            }
            
            if domain in domain_expertise:
                recommendations.extend([
                    {**rec, "category": f"domain_{domain}"} 
                    for rec in domain_expertise[domain]
                ])
            
            # 5. Context-aware keyword analysis
            keyword_mappings = {
                "cache": [
                    {"command": "get_cache_stats", "confidence": 0.95, "reason": "Direct cache operation requested"},
                    {"command": "memory_analytics", "confidence": 0.85, "reason": "Cache analysis requires memory insights"}
                ],
                "memory": [
                    {"command": "memory_analytics", "confidence": 0.95, "reason": "Direct memory operation requested"},
                    {"command": "memory_health_check", "confidence": 0.90, "reason": "Memory health assessment"}
                ],
                "task": [
                    {"command": "list_project_tasks", "confidence": 0.90, "reason": "Task management operation"},
                    {"command": "get_task_context", "confidence": 0.85, "reason": "Task context analysis"},
                    {"command": "create_task_metadata", "confidence": 0.75, "reason": "Task creation workflow"}
                ],
                "validate": [
                    {"command": "validate_code_standards", "confidence": 0.90, "reason": "Validation operation requested"},
                    {"command": "validate_file_operation", "confidence": 0.80, "reason": "File validation support"}
                ],
                "hierarchical": [
                    {"command": "create_hierarchical_task", "confidence": 0.95, "reason": "Hierarchical task structure requested"},
                    {"command": "list_project_tasks", "confidence": 0.80, "reason": "Review hierarchical task relationships"}
                ]
            }
            
            for keyword, keyword_recs in keyword_mappings.items():
                if keyword in description_lower:
                    recommendations.extend([
                        {**rec, "category": f"keyword_{keyword}"} 
                        for rec in keyword_recs
                    ])
            
            # 6. Command sequence analysis and dependencies
            dependency_chains = {
                "create_task_metadata": ["add_task_artifact", "update_task_status"],
                "list_project_tasks": ["get_task_context", "search_similar_tasks"],
                "memory_health_check": ["memory_analytics", "get_cache_stats"],
                "validate_code_standards": ["validate_file_operation", "validate_naming_convention"]
            }
            
            # Add logical next steps based on previous commands
            if previous_commands:
                last_command = previous_commands[-1] if previous_commands else None
                if last_command in dependency_chains:
                    for next_cmd in dependency_chains[last_command]:
                        if next_cmd not in previous_commands[-3:]:  # Avoid recent repetition
                            recommendations.append({
                                "command": next_cmd,
                                "confidence": 0.70,
                                "reason": f"Logical next step after {last_command}",
                                "category": "dependency_chain"
                            })
            
            # 7. Advanced filtering and optimization
            
            # Remove duplicates and merge similar recommendations
            unique_recommendations = {}
            for rec in recommendations:
                cmd = rec["command"]
                if cmd not in unique_recommendations or rec["confidence"] > unique_recommendations[cmd]["confidence"]:
                    unique_recommendations[cmd] = rec
            
            recommendations = list(unique_recommendations.values())
            
            # Apply previous command penalties
            for rec in recommendations:
                if rec["command"] in previous_commands[-5:]:  # Last 5 commands
                    position = previous_commands[-5:].index(rec["command"])
                    penalty = 0.8 ** (5 - position)  # More recent = higher penalty
                    rec["confidence"] *= penalty
                    rec["reason"] += f" (confidence reduced - recently used)"
            
            # 8. Risk assessment
            risk_factors = []
            if task_complexity == "complex" and len(previous_commands) < 2:
                risk_factors.append("Complex task with minimal preparation")
            
            if "memory" in description_lower and "memory_health_check" not in [r["command"] for r in recommendations[:3]]:
                risk_factors.append("Memory operations without health verification")
            
            context_analysis["risk_factors"] = risk_factors
            
            # 9. Final ranking and selection
            recommendations.sort(key=lambda x: x["confidence"], reverse=True)
            top_recommendations = recommendations[:8]  # Increased to 8 for better selection
            
            # 10. Generate final response
            result = {
                "task_analysis": {
                    "task_description": task_description,
                    "domain": domain,
                    "complexity": task_complexity,
                    "workflow_stage": workflow_stage,
                    "system_requirements": system_requirements,
                    "risk_factors": risk_factors
                },
                "recommendations": top_recommendations,
                "context_analysis": context_analysis,
                "selection_metadata": {
                    "total_candidates": len(recommendations),
                    "selected_count": len(top_recommendations),
                    "previous_commands_considered": len(previous_commands),
                    "selection_strategy": "intelligent_context_aware",
                    "confidence_threshold": 0.5
                },
                "timestamp": datetime.now().isoformat()
            }
            
            import json
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            self.logger.error(f"Error in intelligent adaptive command selection: {str(e)}")
            import traceback
            return [TextContent(type="text", text=f"Adaptive command selection error: {str(e)}\n{traceback.format_exc()}")]
    
    async def _handle_analyze_workflow_patterns(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_analyze_workflow_patterns(arguments)
    
    async def _handle_track_progress_milestones(self, arguments: Dict[str, Any]) -> List[TextContent]:
        return await self.server._handle_track_progress_milestones(arguments)