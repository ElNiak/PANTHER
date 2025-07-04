"""
Coordination Placeholder Resolver

Implements dynamic placeholder resolution for cross-project command portability,
enabling commands to work seamlessly across all ATLAS projects through context-aware
parameter substitution and project compatibility validation.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ..refactor_config import get_config


class CoordinationPlaceholderResolver:
    """Resolves dynamic placeholders for cross-project command execution."""
    
    def __init__(self, storage_manager=None, coordination_memory=None):
        self.storage_manager = storage_manager
        self.coordination_memory = coordination_memory
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Placeholder patterns
        self.placeholder_patterns = {
            "CURRENT_PROJECT": r"<CURRENT_PROJECT>",
            "PROJECT_TYPE": r"<PROJECT_TYPE>",
            "PROJECT_PATH": r"<PROJECT_PATH>",
            "COORDINATION_MODE": r"<COORDINATION_MODE>",
            "MEMORY_SCOPE": r"<MEMORY_SCOPE>",
            "CACHE_STRATEGY": r"<CACHE_STRATEGY>",
            "CROSS_PROJECT_REF": r"<CROSS_PROJECT:([^>]+)>",
            "CONDITIONAL": r"<IF_PROJECT:([^>]+):([^>]+)>",
            "TOOL_SELECTION": r"<TOOL_SELECTION:([^>]+)>"
        }
        
        # Project type mappings
        self.project_types = {
            "Software-Engineer-AI-Agent-Atlas": "documentation",
            "PANTHER": "programming",
            "PANTHER-docker-builder-enhancement": "programming",
            "PANTHER-events-deduplication": "programming",
            "atlas-command-refactor": "programming"
        }
        
        # Tool compatibility matrix
        self.tool_compatibility = {
            "documentation": ["Read", "Edit", "Write", "Glob", "Grep", "memory", "allpepper-memory-bank"],
            "programming": ["serena", "language-server", "memory", "allpepper-memory-bank"],
            "all": ["atlas-commands", "memory", "allpepper-memory-bank", "TodoWrite", "TodoRead"]
        }
    
    def resolve_current_project(self, context: Dict[str, Any] = None) -> str:
        """Resolve <CURRENT_PROJECT> based on execution context."""
        try:
            # Priority order for project detection
            
            # 1. Explicit context
            if context and "project_name" in context:
                return context["project_name"]
            
            # 2. Environment variable
            if "PROJECT_NAME" in os.environ:
                return os.environ["PROJECT_NAME"]
            
            # 3. Storage manager detection
            if self.storage_manager:
                detected_project = self.storage_manager.get_project_name()
                if detected_project and detected_project != "default-project":
                    return detected_project
            
            # 4. Git repository detection
            git_project = self._detect_project_from_git()
            if git_project:
                return git_project
            
            # 5. Directory structure detection
            cwd_project = self._detect_project_from_directory()
            if cwd_project:
                return cwd_project
            
            # 6. Default fallback
            return "Software-Engineer-AI-Agent-Atlas"
            
        except Exception as e:
            self.logger.error(f"Failed to resolve current project: {e}")
            return "Software-Engineer-AI-Agent-Atlas"
    
    def resolve_project_type(self, project_name: str) -> str:
        """Resolve <PROJECT_TYPE> based on project name."""
        return self.project_types.get(project_name, "unknown")
    
    def resolve_cross_project_reference(self, reference: str, context: Dict[str, Any] = None) -> str:
        """Resolve <CROSS_PROJECT:reference> to actual project resource."""
        try:
            # Parse reference format: project_name/resource_type/resource_id
            parts = reference.split("/")
            if len(parts) < 2:
                return reference  # Return as-is if format is invalid
            
            target_project = parts[0]
            resource_type = parts[1]
            resource_id = parts[2] if len(parts) > 2 else None
            
            # Validate target project exists
            if self.storage_manager:
                available_projects = self.storage_manager.list_projects()
                if target_project not in available_projects:
                    self.logger.warning(f"Cross-project reference to unknown project: {target_project}")
                    return f"UNKNOWN_PROJECT_{target_project}"
            
            # Resolve based on resource type
            if resource_type == "task":
                return self._resolve_cross_project_task(target_project, resource_id)
            elif resource_type == "memory":
                return self._resolve_cross_project_memory(target_project, resource_id)
            elif resource_type == "cache":
                return self._resolve_cross_project_cache(target_project, resource_id)
            else:
                return f"{target_project}_{resource_type}_{resource_id or 'default'}"
                
        except Exception as e:
            self.logger.error(f"Failed to resolve cross-project reference {reference}: {e}")
            return f"ERROR_{reference}"
    
    def resolve_conditional_placeholder(self, project_condition: str, value: str, context: Dict[str, Any] = None) -> str:
        """Resolve <IF_PROJECT:condition:value> conditionals."""
        try:
            current_project = self.resolve_current_project(context)
            
            # Check if condition matches
            if self._matches_project_condition(current_project, project_condition):
                return value
            else:
                return ""  # Empty string if condition doesn't match
                
        except Exception as e:
            self.logger.error(f"Failed to resolve conditional placeholder: {e}")
            return ""
    
    def resolve_tool_selection(self, tool_category: str, context: Dict[str, Any] = None) -> str:
        """Resolve <TOOL_SELECTION:category> to appropriate tools for current project."""
        try:
            current_project = self.resolve_current_project(context)
            project_type = self.resolve_project_type(current_project)
            
            # Get compatible tools for project type
            compatible_tools = self.tool_compatibility.get(project_type, [])
            universal_tools = self.tool_compatibility.get("all", [])
            
            all_tools = compatible_tools + universal_tools
            
            # Filter by category if specified
            if tool_category == "code_intelligence" and project_type == "programming":
                return "mcp__serena__get_symbols_overview, mcp__serena__find_symbol"
            elif tool_category == "file_operations" and project_type == "documentation":
                return "Read, Edit, Glob, Grep"
            elif tool_category == "memory_management":
                return "mcp__memory__search_nodes, mcp__allpepper-memory-bank__memory_bank_read"
            elif tool_category == "task_management":
                return "mcp__atlas-commands__create_hierarchical_task, TodoWrite"
            else:
                return ", ".join(all_tools)
                
        except Exception as e:
            self.logger.error(f"Failed to resolve tool selection for {tool_category}: {e}")
            return "TodoWrite"  # Safe fallback
    
    def validate_project_compatibility(self, command: str, target_project: str) -> bool:
        """Validate command compatibility with target project."""
        try:
            # Check project type compatibility
            project_type = self.resolve_project_type(target_project)
            
            # Extract tool references from command
            tool_patterns = [
                r"mcp__serena__\w+",
                r"mcp__language-server__\w+", 
                r"Read\(",
                r"Edit\(",
                r"Glob\(",
                r"Grep\("
            ]
            
            used_tools = []
            for pattern in tool_patterns:
                matches = re.findall(pattern, command)
                used_tools.extend(matches)
            
            # Check tool compatibility
            for tool in used_tools:
                if not self._is_tool_compatible(tool, project_type):
                    self.logger.warning(f"Tool {tool} not compatible with project type {project_type}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate project compatibility: {e}")
            return False
    
    def resolve_all_placeholders(self, template: str, context: Dict[str, Any] = None) -> str:
        """Resolve all placeholders in a template string."""
        try:
            resolved = template
            
            # Resolve each placeholder type
            for placeholder_type, pattern in self.placeholder_patterns.items():
                if placeholder_type == "CURRENT_PROJECT":
                    resolved = re.sub(pattern, self.resolve_current_project(context), resolved)
                
                elif placeholder_type == "PROJECT_TYPE":
                    current_project = self.resolve_current_project(context)
                    project_type = self.resolve_project_type(current_project)
                    resolved = re.sub(pattern, project_type, resolved)
                
                elif placeholder_type == "PROJECT_PATH":
                    project_path = self._resolve_project_path(context)
                    resolved = re.sub(pattern, project_path, resolved)
                
                elif placeholder_type == "COORDINATION_MODE":
                    coord_mode = os.environ.get("ATLAS_COORDINATION_MODE", "enabled")
                    resolved = re.sub(pattern, coord_mode, resolved)
                
                elif placeholder_type == "MEMORY_SCOPE":
                    memory_scope = os.environ.get("ATLAS_MEMORY_ISOLATION", "strict")
                    resolved = re.sub(pattern, memory_scope, resolved)
                
                elif placeholder_type == "CACHE_STRATEGY":
                    cache_strategy = os.environ.get("ATLAS_CACHE_MODE", "hierarchical")
                    resolved = re.sub(pattern, cache_strategy, resolved)
                
                elif placeholder_type == "CROSS_PROJECT_REF":
                    def replace_cross_ref(match):
                        return self.resolve_cross_project_reference(match.group(1), context)
                    resolved = re.sub(pattern, replace_cross_ref, resolved)
                
                elif placeholder_type == "CONDITIONAL":
                    def replace_conditional(match):
                        return self.resolve_conditional_placeholder(match.group(1), match.group(2), context)
                    resolved = re.sub(pattern, replace_conditional, resolved)
                
                elif placeholder_type == "TOOL_SELECTION":
                    def replace_tool_selection(match):
                        return self.resolve_tool_selection(match.group(1), context)
                    resolved = re.sub(pattern, replace_tool_selection, resolved)
            
            # Log placeholder resolution
            if resolved != template:
                self.logger.debug(f"Resolved placeholders in template")
            
            return resolved
            
        except Exception as e:
            self.logger.error(f"Failed to resolve placeholders: {e}")
            return template  # Return original template on error
    
    def _detect_project_from_git(self) -> Optional[str]:
        """Detect project name from git repository."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                # Extract project name from git URL
                if "Software-Engineer-AI-Agent-Atlas" in remote_url:
                    return "Software-Engineer-AI-Agent-Atlas"
                elif "PANTHER" in remote_url:
                    return "PANTHER"
                
        except Exception:
            pass  # Git not available or not a git repo
        
        return None
    
    def _detect_project_from_directory(self) -> Optional[str]:
        """Detect project name from current directory structure."""
        try:
            cwd = Path.cwd()
            
            # Check directory name patterns
            if "Software-Engineer-AI-Agent-Atlas" in str(cwd):
                return "Software-Engineer-AI-Agent-Atlas"
            elif "PANTHER" in str(cwd):
                if "docker-builder" in str(cwd):
                    return "PANTHER-docker-builder-enhancement"
                elif "events-deduplication" in str(cwd):
                    return "PANTHER-events-deduplication"
                else:
                    return "PANTHER"
            elif "atlas-command" in str(cwd):
                return "atlas-command-refactor"
            
        except Exception:
            pass
        
        return None
    
    def _resolve_project_path(self, context: Dict[str, Any] = None) -> str:
        """Resolve project path for current project."""
        if self.storage_manager:
            current_project = self.resolve_current_project(context)
            if hasattr(self.storage_manager, 'base_path'):
                return str(self.storage_manager.base_path / f"{current_project}_TASKS")
        
        return str(Path.cwd())
    
    def _resolve_cross_project_task(self, target_project: str, task_id: str) -> str:
        """Resolve cross-project task reference."""
        if self.storage_manager and task_id:
            try:
                # Check if task exists in target project
                task_context = self.storage_manager.get_task_context(target_project, task_id)
                return f"{target_project}:{task_id}"
            except:
                return f"MISSING_TASK_{target_project}_{task_id}"
        
        return f"{target_project}_TASKS"
    
    def _resolve_cross_project_memory(self, target_project: str, memory_id: str) -> str:
        """Resolve cross-project memory reference."""
        if self.coordination_memory:
            try:
                project_memory = self.coordination_memory.get_project_memory(target_project)
                return f"{target_project}_MEMORY_{memory_id or 'default'}"
            except:
                return f"MISSING_MEMORY_{target_project}_{memory_id}"
        
        return f"{target_project}_MEMORY"
    
    def _resolve_cross_project_cache(self, target_project: str, cache_id: str) -> str:
        """Resolve cross-project cache reference."""
        if self.storage_manager:
            cache_path = self.storage_manager.get_project_cache(target_project)
            return str(cache_path / (cache_id or "default"))
        
        return f"{target_project}_CACHE"
    
    def _matches_project_condition(self, current_project: str, condition: str) -> bool:
        """Check if current project matches the condition."""
        condition = condition.lower()
        current_project = current_project.lower()
        
        # Direct match
        if condition == current_project:
            return True
        
        # Type-based match
        project_type = self.resolve_project_type(current_project).lower()
        if condition == project_type:
            return True
        
        # Pattern match
        if condition in current_project or current_project in condition:
            return True
        
        return False
    
    def _is_tool_compatible(self, tool: str, project_type: str) -> bool:
        """Check if tool is compatible with project type."""
        tool_lower = tool.lower()
        
        # Programming project tools
        if project_type == "programming":
            if any(prog_tool in tool_lower for prog_tool in ["serena", "language-server"]):
                return True
        
        # Documentation project tools  
        if project_type == "documentation":
            if any(doc_tool in tool_lower for doc_tool in ["read", "edit", "glob", "grep"]):
                return True
        
        # Universal tools
        universal_tools = ["memory", "allpepper-memory-bank", "atlas-commands", "todowrite"]
        if any(universal_tool in tool_lower for universal_tool in universal_tools):
            return True
        
        return False
    
    def get_resolution_context(self, project_name: str = None) -> Dict[str, Any]:
        """Get context information for placeholder resolution."""
        if not project_name:
            project_name = self.resolve_current_project()
        
        return {
            "current_project": project_name,
            "project_type": self.resolve_project_type(project_name),
            "coordination_enabled": os.environ.get("ATLAS_COORDINATION_MODE", "enabled") == "enabled",
            "memory_isolation": os.environ.get("ATLAS_MEMORY_ISOLATION", "strict"),
            "cache_mode": os.environ.get("ATLAS_CACHE_MODE", "hierarchical"),
            "available_projects": self.storage_manager.list_projects() if self.storage_manager else [],
            "timestamp": datetime.now().isoformat()
        }