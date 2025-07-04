"""Command validation for ATLAS workflow system."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import re


class ValidationLevel(Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult:
    """Result of command validation."""
    
    def __init__(
        self,
        valid: bool,
        level: ValidationLevel,
        message: str,
        suggestion: Optional[str] = None
    ):
        self.valid = valid
        self.level = level
        self.message = message
        self.suggestion = suggestion
        self.timestamp = datetime.now()


class CommandValidator:
    """Validates command parameters and execution context."""
    
    def __init__(self):
        self.validation_rules = self._define_validation_rules()
        self.parameter_schemas = self._define_parameter_schemas()
    
    def _define_validation_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Define validation rules for each command."""
        
        return {
            "plan": [
                {
                    "name": "target_format",
                    "check": lambda params: self._validate_target_format(params.get("target", "")),
                    "level": ValidationLevel.ERROR,
                    "message": "Target must be a valid identifier (alphanumeric, hyphens, underscores)"
                },
                {
                    "name": "complexity_valid",
                    "check": lambda params: params.get("complexity", "medium") in ["simple", "medium", "complex"],
                    "level": ValidationLevel.WARNING,
                    "message": "Complexity should be 'simple', 'medium', or 'complex'"
                }
            ],
            "execute": [
                {
                    "name": "target_exists",
                    "check": lambda params: bool(params.get("target")),
                    "level": ValidationLevel.ERROR,
                    "message": "Target is required for execute command"
                },
                {
                    "name": "subtask_format",
                    "check": lambda params: self._validate_subtask_format(params.get("subtask_id", "")),
                    "level": ValidationLevel.WARNING,
                    "message": "Subtask ID should follow format: XX-description (e.g., 01-core-implementation)"
                }
            ],
            "verify": [
                {
                    "name": "verification_level",
                    "check": lambda params: params.get("level", "standard") in ["basic", "standard", "thorough", "comprehensive"],
                    "level": ValidationLevel.WARNING,
                    "message": "Verification level should be 'basic', 'standard', 'thorough', or 'comprehensive'"
                }
            ],
            "complete": [
                {
                    "name": "archive_level",
                    "check": lambda params: params.get("archive_level", "standard") in ["minimal", "standard", "comprehensive", "release-ready"],
                    "level": ValidationLevel.WARNING,
                    "message": "Archive level should be 'minimal', 'standard', 'comprehensive', or 'release-ready'"
                }
            ],
            "analyze": [
                {
                    "name": "focus_valid",
                    "check": lambda params: self._validate_analyze_focus(params.get("focus", "")),
                    "level": ValidationLevel.INFO,
                    "message": "Consider specifying analysis focus (architecture, performance, security, etc.)"
                }
            ],
            "design": [
                {
                    "name": "approach_valid",
                    "check": lambda params: self._validate_design_approach(params.get("approach", "")),
                    "level": ValidationLevel.INFO,
                    "message": "Consider specifying design approach (detailed, high-level, iterative, etc.)"
                }
            ]
        }
    
    def _define_parameter_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define parameter schemas for commands."""
        
        return {
            "plan": {
                "required": ["target"],
                "optional": ["complexity", "type", "phase"],
                "types": {
                    "target": str,
                    "complexity": str,
                    "type": str,
                    "phase": str
                }
            },
            "execute": {
                "required": ["target"],
                "optional": ["subtask_id", "sub_subtask_id", "mode"],
                "types": {
                    "target": str,
                    "subtask_id": str,
                    "sub_subtask_id": str,
                    "mode": str
                }
            },
            "verify": {
                "required": ["target"],
                "optional": ["subtask_id", "level"],
                "types": {
                    "target": str,
                    "subtask_id": str,
                    "level": str
                }
            },
            "complete": {
                "required": ["target"],
                "optional": ["subtask_id", "archive_level"],
                "types": {
                    "target": str,
                    "subtask_id": str,
                    "archive_level": str
                }
            }
        }
    
    def validate_command(
        self,
        command: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ValidationResult]:
        """Validate a command with its parameters."""
        
        results = []
        
        # Schema validation
        schema_results = self._validate_parameter_schema(command, parameters)
        results.extend(schema_results)
        
        # Rule validation
        if command in self.validation_rules:
            for rule in self.validation_rules[command]:
                try:
                    is_valid = rule["check"](parameters)
                    if not is_valid:
                        result = ValidationResult(
                            valid=False,
                            level=rule["level"],
                            message=rule["message"],
                            suggestion=rule.get("suggestion")
                        )
                        results.append(result)
                except Exception as e:
                    # Rule check failed
                    result = ValidationResult(
                        valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Validation rule '{rule['name']}' failed: {str(e)}"
                    )
                    results.append(result)
        
        # Context validation
        if context:
            context_results = self._validate_context(command, parameters, context)
            results.extend(context_results)
        
        return results
    
    def _validate_parameter_schema(
        self,
        command: str,
        parameters: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate parameters against schema."""
        
        results = []
        
        if command not in self.parameter_schemas:
            return results
        
        schema = self.parameter_schemas[command]
        
        # Check required parameters
        for required_param in schema.get("required", []):
            if required_param not in parameters or parameters[required_param] is None:
                result = ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Required parameter '{required_param}' is missing",
                    suggestion=f"Add {required_param} parameter"
                )
                results.append(result)
        
        # Check parameter types
        for param, expected_type in schema.get("types", {}).items():
            if param in parameters and parameters[param] is not None:
                if not isinstance(parameters[param], expected_type):
                    result = ValidationResult(
                        valid=False,
                        level=ValidationLevel.WARNING,
                        message=f"Parameter '{param}' should be of type {expected_type.__name__}",
                        suggestion=f"Convert {param} to {expected_type.__name__}"
                    )
                    results.append(result)
        
        return results
    
    def _validate_context(
        self,
        command: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate command execution context."""
        
        results = []
        
        # Check workflow context
        if "workflow_id" in context:
            workflow_validation = self._validate_workflow_context(command, context)
            results.extend(workflow_validation)
        
        # Check resource availability
        resource_validation = self._validate_resource_availability(command, parameters, context)
        results.extend(resource_validation)
        
        # Check timing constraints
        timing_validation = self._validate_timing_constraints(command, context)
        results.extend(timing_validation)
        
        return results
    
    def _validate_workflow_context(
        self,
        command: str,
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate command within workflow context."""
        
        results = []
        
        workflow_id = context.get("workflow_id")
        if not workflow_id:
            return results
        
        # Check if command is part of workflow
        workflow_commands = context.get("workflow_commands", [])
        if command not in workflow_commands:
            result = ValidationResult(
                valid=False,
                level=ValidationLevel.WARNING,
                message=f"Command '{command}' not found in workflow '{workflow_id}'",
                suggestion="Consider adding command to workflow or executing outside workflow"
            )
            results.append(result)
        
        return results
    
    def _validate_resource_availability(
        self,
        command: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate resource availability for command."""
        
        results = []
        
        # Check disk space for commands that create artifacts
        if command in ["execute", "verify", "complete"]:
            available_space = context.get("disk_space_mb", 1000)  # Default assumption
            if available_space < 100:  # Minimum 100MB
                result = ValidationResult(
                    valid=False,
                    level=ValidationLevel.WARNING,
                    message="Low disk space detected",
                    suggestion="Clean up disk space before proceeding"
                )
                results.append(result)
        
        # Check if target exists
        target = parameters.get("target")
        if target and "existing_targets" in context:
            existing_targets = context["existing_targets"]
            if target not in existing_targets and command in ["execute", "verify", "complete"]:
                result = ValidationResult(
                    valid=False,
                    level=ValidationLevel.WARNING,
                    message=f"Target '{target}' not found in existing targets",
                    suggestion="Verify target name or create target first"
                )
                results.append(result)
        
        return results
    
    def _validate_timing_constraints(
        self,
        command: str,
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate timing constraints."""
        
        results = []
        
        # Check for time-sensitive operations
        current_time = datetime.now()
        
        # Warn about long-running operations during work hours
        if command in ["execute", "verify"] and context.get("work_hours", True):
            if current_time.hour >= 17:  # After 5 PM
                result = ValidationResult(
                    valid=True,
                    level=ValidationLevel.INFO,
                    message="Executing long-running command outside work hours",
                    suggestion="Consider scheduling for off-hours if this is a large task"
                )
                results.append(result)
        
        return results
    
    def _validate_target_format(self, target: str) -> bool:
        """Validate target format."""
        if not target:
            return False
        
        # Allow alphanumeric, hyphens, underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, target))
    
    def _validate_subtask_format(self, subtask_id: str) -> bool:
        """Validate subtask ID format."""
        if not subtask_id:
            return True  # Optional parameter
        
        # Format: XX-description or XX.Y-description
        pattern = r'^(\d{2}|\d{2}\.\d+)-[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, subtask_id))
    
    def _validate_analyze_focus(self, focus: str) -> bool:
        """Validate analyze focus parameter."""
        if not focus:
            return True  # Optional, but info level suggestion
        
        valid_focuses = [
            "architecture", "performance", "security", "refactoring",
            "dependencies", "complexity", "maintainability", "scalability"
        ]
        return focus.lower() in valid_focuses
    
    def _validate_design_approach(self, approach: str) -> bool:
        """Validate design approach parameter."""
        if not approach:
            return True  # Optional, but info level suggestion
        
        valid_approaches = [
            "detailed", "high-level", "iterative", "incremental",
            "architectural", "modular", "component-based", "service-oriented"
        ]
        return approach.lower() in valid_approaches
    
    def get_validation_summary(
        self,
        validation_results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Get summary of validation results."""
        
        by_level = {
            ValidationLevel.CRITICAL: [],
            ValidationLevel.ERROR: [],
            ValidationLevel.WARNING: [],
            ValidationLevel.INFO: []
        }
        
        for result in validation_results:
            by_level[result.level].append(result)
        
        return {
            "total_issues": len(validation_results),
            "critical_count": len(by_level[ValidationLevel.CRITICAL]),
            "error_count": len(by_level[ValidationLevel.ERROR]),
            "warning_count": len(by_level[ValidationLevel.WARNING]),
            "info_count": len(by_level[ValidationLevel.INFO]),
            "can_proceed": len(by_level[ValidationLevel.CRITICAL]) == 0 and len(by_level[ValidationLevel.ERROR]) == 0,
            "issues_by_level": {
                level.value: [
                    {
                        "message": result.message,
                        "suggestion": result.suggestion,
                        "timestamp": result.timestamp.isoformat()
                    }
                    for result in results
                ]
                for level, results in by_level.items()
                if results
            }
        }