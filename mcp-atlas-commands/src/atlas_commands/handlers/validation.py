"""
Validation Handler

Handles convention validation, file operation checks, naming enforcement,
and git protocol automation.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from ..tool_registry import ToolHandler
from ..refactor_config import get_config
import logging


class ValidationHandler(ToolHandler):
    """Handler for validation and convention enforcement tools."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "validation"
    
    def get_tool_names(self) -> List[str]:
        return [
            "validate_file_operation",
            "validate_naming_convention",
            "validate_code_standards", 
            "enforce_git_protocol"
        ]
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle validation tool calls."""
        try:
            if self.config.enable_consistent_error_handling:
                self.logger.info(f"Processing validation tool: {name}")
            
            # Route to appropriate handler method
            if name == "validate_file_operation":
                return await self._handle_validate_file_operation(arguments)
            elif name == "validate_naming_convention":
                return await self._handle_validate_naming_convention(arguments)
            elif name == "validate_code_standards":
                return await self._handle_validate_code_standards(arguments)
            elif name == "enforce_git_protocol":
                return await self._handle_enforce_git_protocol(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown validation tool: {name}")]
                
        except Exception as e:
            error_msg = f"Error in validation handler for {name}: {str(e)}"
            self.logger.error(error_msg)
            if self.config.enable_consistent_error_handling:
                return [TextContent(type="text", text=f"Validation Error: {str(e)}")]
            else:
                raise e
    
    # Validation implementation methods
    async def _handle_validate_file_operation(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Validate file operation safety and compliance."""
        import os
        import json
        from pathlib import Path
        
        try:
            file_path = arguments.get("file_path", "")
            operation = arguments.get("operation", "read")  # read, write, delete, move
            
            if not file_path:
                return [TextContent(type="text", text="Error: file_path is required")]
            
            path = Path(file_path)
            
            validation_result = {
                "file_path": file_path,
                "operation": operation,
                "validation_status": "valid",
                "warnings": [],
                "errors": [],
                "recommendations": []
            }
            
            # Security checks
            if ".." in file_path or file_path.startswith("/"):
                validation_result["errors"].append("Path traversal detected - absolute or parent directory access not allowed")
                validation_result["validation_status"] = "invalid"
            
            # Operation-specific validations
            if operation == "write":
                if path.exists() and not arguments.get("confirm_overwrite", False):
                    validation_result["warnings"].append("File exists - overwrite not confirmed")
                    validation_result["recommendations"].append("Add confirm_overwrite=true if intentional")
                    
            elif operation == "delete":
                if not path.exists():
                    validation_result["warnings"].append("File does not exist")
                else:
                    validation_result["warnings"].append("Destructive operation - ensure backup exists")
                    
            elif operation == "read":
                if not path.exists():
                    validation_result["errors"].append("File does not exist")
                    validation_result["validation_status"] = "invalid"
            
            # File type validations
            if path.suffix in [".py", ".js", ".ts", ".java", ".cpp"]:
                validation_result["recommendations"].append("Code file detected - consider linting before operation")
            
            return [TextContent(type="text", text=json.dumps(validation_result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"File operation validation error: {str(e)}")]
    
    async def _handle_validate_naming_convention(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Validate naming convention compliance."""
        import json
        import re
        
        try:
            name = arguments.get("name", "")
            convention = arguments.get("convention", "snake_case")  # snake_case, camelCase, PascalCase, kebab-case
            context = arguments.get("context", "general")  # variable, function, class, file, etc.
            
            validation_result = {
                "name": name,
                "convention": convention,
                "context": context,
                "is_valid": False,
                "violations": [],
                "suggestions": []
            }
            
            # Convention patterns
            patterns = {
                "snake_case": r"^[a-z][a-z0-9_]*$",
                "camelCase": r"^[a-z][a-zA-Z0-9]*$", 
                "PascalCase": r"^[A-Z][a-zA-Z0-9]*$",
                "kebab-case": r"^[a-z][a-z0-9-]*$",
                "SCREAMING_SNAKE": r"^[A-Z][A-Z0-9_]*$"
            }
            
            if convention in patterns:
                pattern = patterns[convention]
                if re.match(pattern, name):
                    validation_result["is_valid"] = True
                else:
                    validation_result["violations"].append(f"Does not match {convention} pattern")
                    
                    # Generate suggestions
                    if convention == "snake_case":
                        suggestion = re.sub(r'[A-Z]', lambda m: '_' + m.group().lower(), name).lstrip('_')
                        validation_result["suggestions"].append(suggestion)
                    elif convention == "camelCase":
                        words = re.split(r'[_\-\s]+', name.lower())
                        suggestion = words[0] + ''.join(word.capitalize() for word in words[1:])
                        validation_result["suggestions"].append(suggestion)
                    elif convention == "PascalCase":
                        words = re.split(r'[_\-\s]+', name.lower())
                        suggestion = ''.join(word.capitalize() for word in words)
                        validation_result["suggestions"].append(suggestion)
            else:
                validation_result["violations"].append(f"Unknown convention: {convention}")
            
            return [TextContent(type="text", text=json.dumps(validation_result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Naming convention validation error: {str(e)}")]
    
    async def _handle_validate_code_standards(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Validate code against quality standards."""
        import json
        
        try:
            code = arguments.get("code", "")
            language = arguments.get("language", "python")
            standards = arguments.get("standards", ["length", "complexity", "style"])
            
            validation_result = {
                "language": language,
                "standards_checked": standards,
                "violations": [],
                "score": 100,
                "recommendations": []
            }
            
            lines = code.split('\n')
            
            # Line length check
            if "length" in standards:
                max_length = 120 if language == "python" else 100
                for i, line in enumerate(lines, 1):
                    if len(line) > max_length:
                        validation_result["violations"].append(f"Line {i}: Exceeds {max_length} characters ({len(line)})")
                        validation_result["score"] -= 5
            
            # Complexity checks
            if "complexity" in standards and language == "python":
                # Simple complexity indicators
                nested_level = 0
                for i, line in enumerate(lines, 1):
                    indent = len(line) - len(line.lstrip())
                    if indent > 16:  # 4 levels deep
                        validation_result["violations"].append(f"Line {i}: Excessive nesting (>4 levels)")
                        validation_result["score"] -= 10
            
            # Style checks
            if "style" in standards and language == "python":
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.endswith(' '):
                        validation_result["violations"].append(f"Line {i}: Trailing whitespace")
                        validation_result["score"] -= 2
                    if '==' in stripped and stripped.count('=') > 2:
                        validation_result["recommendations"].append(f"Line {i}: Consider using 'is' for None comparisons")
            
            # Final score adjustment
            validation_result["score"] = max(0, validation_result["score"])
            
            if validation_result["score"] >= 90:
                validation_result["grade"] = "A"
            elif validation_result["score"] >= 80:
                validation_result["grade"] = "B"
            elif validation_result["score"] >= 70:
                validation_result["grade"] = "C"
            else:
                validation_result["grade"] = "F"
            
            return [TextContent(type="text", text=json.dumps(validation_result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Code standards validation error: {str(e)}")]
    
    async def _handle_enforce_git_protocol(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Enforce git workflow protocols and best practices."""
        import json
        import subprocess
        
        try:
            action = arguments.get("action", "check")  # check, enforce, suggest
            
            protocol_result = {
                "action": action,
                "git_status": "unknown",
                "violations": [],
                "enforcements": [],
                "suggestions": []
            }
            
            # Check git status
            try:
                result = subprocess.run(['git', 'status', '--porcelain'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    protocol_result["git_status"] = "clean" if not result.stdout.strip() else "dirty"
                    
                    if protocol_result["git_status"] == "dirty":
                        protocol_result["violations"].append("Working directory has uncommitted changes")
                        protocol_result["suggestions"].append("Review changes with 'git diff' before committing")
                else:
                    protocol_result["git_status"] = "error"
                    protocol_result["violations"].append("Git repository not found or inaccessible")
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                protocol_result["git_status"] = "unavailable"
                protocol_result["violations"].append("Git command not available")
            
            # Check current branch
            try:
                result = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
                    protocol_result["current_branch"] = current_branch
                    
                    if current_branch == "main" or current_branch == "master":
                        protocol_result["violations"].append("Working directly on main/master branch")
                        protocol_result["suggestions"].append("Create feature branch for development")
                        
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Protocol recommendations
            protocol_result["suggestions"].extend([
                "Use descriptive commit messages",
                "Keep commits focused and atomic", 
                "Test changes before committing",
                "Use branch protection for main/master"
            ])
            
            return [TextContent(type="text", text=json.dumps(protocol_result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Git protocol enforcement error: {str(e)}")]