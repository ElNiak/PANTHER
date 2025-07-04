"""Enhanced validation utilities for ATLAS Commands MCP Server."""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime


class ValidationType(Enum):
    """Types of validation to perform."""
    REQUIRED = "required"
    FORMAT = "format"
    RANGE = "range"
    DEPENDENCY = "dependency"
    CONSISTENCY = "consistency"
    BUSINESS_RULE = "business_rule"


@dataclass
class ValidationRule:
    """Defines a validation rule."""
    name: str
    validation_type: ValidationType
    check: Callable[[Any], bool]
    error_message: str
    severity: str = "error"  # error, warning, info
    auto_fix: Optional[Callable[[Any], Any]] = None


class InputValidator:
    """Validates input parameters for MCP tools."""
    
    def __init__(self):
        self.rules = self._define_validation_rules()
        self.custom_rules: Dict[str, List[ValidationRule]] = {}
    
    def _define_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Define standard validation rules for each tool."""
        
        return {
            "create_unified_checklist": [
                ValidationRule(
                    name="command_name_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "command_name" in args and args["command_name"],
                    error_message="command_name is required"
                ),
                ValidationRule(
                    name="command_name_valid",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: args.get("command_name", "") in [
                        "plan", "execute", "verify", "complete", "analyze", 
                        "design", "decompose", "workflow"
                    ],
                    error_message="command_name must be a valid ATLAS command",
                    severity="warning"
                ),
                ValidationRule(
                    name="task_id_format",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: self._validate_task_id_format(args.get("task_id", "")),
                    error_message="task_id should follow format: type-description-timestamp",
                    severity="warning",
                    auto_fix=lambda args: self._fix_task_id_format(args)
                ),
                ValidationRule(
                    name="items_or_template",
                    validation_type=ValidationType.BUSINESS_RULE,
                    check=lambda args: "items" in args or "template_type" in args,
                    error_message="Either items or template_type must be provided"
                )
            ],
            "update_checklist_item": [
                ValidationRule(
                    name="checklist_id_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "checklist_id" in args and args["checklist_id"],
                    error_message="checklist_id is required"
                ),
                ValidationRule(
                    name="item_id_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "item_id" in args and args["item_id"],
                    error_message="item_id is required"
                ),
                ValidationRule(
                    name="status_valid",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: args.get("status", "") in [
                        "PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED"
                    ],
                    error_message="status must be one of: PENDING, IN_PROGRESS, COMPLETED, BLOCKED"
                ),
                ValidationRule(
                    name="status_transition_valid",
                    validation_type=ValidationType.BUSINESS_RULE,
                    check=lambda args: self._validate_status_transition(args),
                    error_message="Invalid status transition",
                    severity="warning"
                )
            ],
            "create_memory_entity": [
                ValidationRule(
                    name="command_type_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "command_type" in args and args["command_type"],
                    error_message="command_type is required"
                ),
                ValidationRule(
                    name="target_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "target" in args and args["target"],
                    error_message="target is required"
                ),
                ValidationRule(
                    name="observations_not_empty",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: args.get("observations", []) and len(args["observations"]) > 0,
                    error_message="observations must not be empty"
                ),
                ValidationRule(
                    name="observations_format",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: all(isinstance(obs, str) for obs in args.get("observations", [])),
                    error_message="All observations must be strings"
                )
            ],
            "create_workflow": [
                ValidationRule(
                    name="workflow_id_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "workflow_id" in args and args["workflow_id"],
                    error_message="workflow_id is required"
                ),
                ValidationRule(
                    name="pattern_valid",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: args.get("pattern", "") in [
                        "explore-plan-code-commit", "quick-fix", "refactor", "tdd"
                    ],
                    error_message="pattern must be a valid workflow pattern"
                ),
                ValidationRule(
                    name="target_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "target" in args and args["target"],
                    error_message="target is required"
                )
            ],
            "validate_command": [
                ValidationRule(
                    name="command_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "command" in args and args["command"],
                    error_message="command is required"
                ),
                ValidationRule(
                    name="parameters_required",
                    validation_type=ValidationType.REQUIRED,
                    check=lambda args: "parameters" in args and isinstance(args["parameters"], dict),
                    error_message="parameters must be a dictionary"
                )
            ],
            "track_command_pattern": [
                ValidationRule(
                    name="outcome_valid",
                    validation_type=ValidationType.FORMAT,
                    check=lambda args: args.get("outcome", "") in ["success", "failure", "partial"],
                    error_message="outcome must be one of: success, failure, partial"
                ),
                ValidationRule(
                    name="observations_quality",
                    validation_type=ValidationType.BUSINESS_RULE,
                    check=lambda args: self._validate_observation_quality(args.get("observations", [])),
                    error_message="Observations should be meaningful and specific",
                    severity="warning"
                )
            ],
            "compact_memory_graph": [
                ValidationRule(
                    name="days_old_range",
                    validation_type=ValidationType.RANGE,
                    check=lambda args: 1 <= args.get("days_old", 30) <= 365,
                    error_message="days_old must be between 1 and 365",
                    auto_fix=lambda args: {**args, "days_old": max(1, min(365, args.get("days_old", 30)))}
                )
            ]
        }
    
    def validate(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate arguments for a specific tool."""
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": [],
            "fixed_arguments": None
        }
        
        # Get rules for this tool
        rules = self.rules.get(tool_name, [])
        if tool_name in self.custom_rules:
            rules.extend(self.custom_rules[tool_name])
        
        fixed_args = arguments.copy()
        
        for rule in rules:
            try:
                # Check the rule
                if not rule.check(fixed_args):
                    # Try auto-fix if available
                    if rule.auto_fix:
                        fixed_args = rule.auto_fix(fixed_args)
                        # Re-check after fix
                        if rule.check(fixed_args):
                            results["info"].append(f"Auto-fixed: {rule.name}")
                            continue
                    
                    # Add to appropriate list based on severity
                    message = f"{rule.name}: {rule.error_message}"
                    if rule.severity == "error":
                        results["errors"].append(message)
                        results["valid"] = False
                    elif rule.severity == "warning":
                        results["warnings"].append(message)
                    else:
                        results["info"].append(message)
                
            except Exception as e:
                results["warnings"].append(f"Validation rule {rule.name} failed: {str(e)}")
        
        # Set fixed arguments if any fixes were applied
        if fixed_args != arguments:
            results["fixed_arguments"] = fixed_args
        
        return results
    
    def _validate_task_id_format(self, task_id: str) -> bool:
        """Validate task ID format."""
        
        if not task_id:
            return True  # Optional field
        
        # Expected format: type-description-timestamp or type-description
        pattern = r'^[a-zA-Z]+-[a-zA-Z0-9-]+(-\d{8})?$'
        return bool(re.match(pattern, task_id))
    
    def _fix_task_id_format(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fix task ID format if possible."""
        
        task_id = args.get("task_id", "")
        if not task_id:
            return args
        
        # Clean up task ID
        cleaned_id = re.sub(r'[^a-zA-Z0-9-]', '-', task_id)
        cleaned_id = re.sub(r'-+', '-', cleaned_id)  # Remove multiple dashes
        cleaned_id = cleaned_id.strip('-')
        
        # Add timestamp if missing
        if not re.search(r'-\d{8}$', cleaned_id):
            cleaned_id += f"-{datetime.now().strftime('%Y%m%d')}"
        
        return {**args, "task_id": cleaned_id}
    
    def _validate_status_transition(self, args: Dict[str, Any]) -> bool:
        """Validate status transitions are logical."""
        
        # This would check against current status in real implementation
        # For now, just ensure basic rules
        status = args.get("status", "")
        
        # BLOCKED can transition to any state
        # COMPLETED should not transition to PENDING
        # This is simplified - real implementation would check current state
        
        return True
    
    def _validate_observation_quality(self, observations: List[str]) -> bool:
        """Validate observation quality."""
        
        if not observations:
            return False
        
        # Check for meaningful content
        min_length = 10
        has_meaningful = any(len(obs) >= min_length for obs in observations)
        
        # Check for non-generic observations
        generic_phrases = ["done", "completed", "finished", "ok", "good"]
        all_generic = all(
            any(phrase in obs.lower() for phrase in generic_phrases)
            for obs in observations
        )
        
        return has_meaningful and not all_generic
    
    def add_custom_rule(self, tool_name: str, rule: ValidationRule):
        """Add a custom validation rule for a tool."""
        
        if tool_name not in self.custom_rules:
            self.custom_rules[tool_name] = []
        
        self.custom_rules[tool_name].append(rule)


class OutputValidator:
    """Validates output from MCP tools."""
    
    def __init__(self):
        self.schemas = self._define_output_schemas()
    
    def _define_output_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define expected output schemas for each tool."""
        
        return {
            "create_unified_checklist": {
                "required_fields": ["checklist_markdown", "checklist_id", "item_count"],
                "field_types": {
                    "checklist_markdown": str,
                    "checklist_id": str,
                    "item_count": int
                },
                "constraints": {
                    "item_count": lambda x: x > 0,
                    "checklist_markdown": lambda x: "complete)" in x  # Should have progress indicator
                }
            },
            "update_checklist_item": {
                "required_fields": ["success", "checklist_id", "item_id", "new_status"],
                "field_types": {
                    "success": bool,
                    "checklist_id": str,
                    "item_id": str,
                    "new_status": str
                }
            },
            "create_memory_entity": {
                "required_fields": ["entity_name", "command_type", "target", "observation_count"],
                "field_types": {
                    "entity_name": str,
                    "command_type": str,
                    "target": str,
                    "observation_count": int
                },
                "constraints": {
                    "entity_name": lambda x: "_" in x,  # Should follow naming convention
                    "observation_count": lambda x: x > 0
                }
            },
            "create_workflow": {
                "required_fields": ["workflow_id", "pattern", "target", "step_count", "steps"],
                "field_types": {
                    "workflow_id": str,
                    "pattern": str,
                    "target": str,
                    "step_count": int,
                    "steps": list
                },
                "constraints": {
                    "step_count": lambda x: x > 0,
                    "steps": lambda x: len(x) > 0
                }
            }
        }
    
    def validate_output(
        self,
        tool_name: str,
        output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate output from a tool."""
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        schema = self.schemas.get(tool_name, {})
        if not schema:
            results["warnings"].append(f"No output schema defined for {tool_name}")
            return results
        
        # Check required fields
        for field in schema.get("required_fields", []):
            if field not in output:
                results["errors"].append(f"Missing required field: {field}")
                results["valid"] = False
        
        # Check field types
        for field, expected_type in schema.get("field_types", {}).items():
            if field in output and not isinstance(output[field], expected_type):
                results["errors"].append(
                    f"Field {field} has wrong type: expected {expected_type.__name__}, "
                    f"got {type(output[field]).__name__}"
                )
                results["valid"] = False
        
        # Check constraints
        for field, constraint in schema.get("constraints", {}).items():
            if field in output:
                try:
                    if not constraint(output[field]):
                        results["warnings"].append(
                            f"Field {field} failed constraint check"
                        )
                except Exception as e:
                    results["warnings"].append(
                        f"Constraint check failed for {field}: {str(e)}"
                    )
        
        return results


class SemanticValidator:
    """Validates semantic correctness of operations."""
    
    def __init__(self):
        self.context_rules = self._define_context_rules()
    
    def _define_context_rules(self) -> List[ValidationRule]:
        """Define semantic validation rules."""
        
        return [
            ValidationRule(
                name="checklist_consistency",
                validation_type=ValidationType.CONSISTENCY,
                check=lambda ctx: self._check_checklist_consistency(ctx),
                error_message="Checklist items have inconsistent dependencies"
            ),
            ValidationRule(
                name="workflow_step_order",
                validation_type=ValidationType.DEPENDENCY,
                check=lambda ctx: self._check_workflow_step_order(ctx),
                error_message="Workflow steps are in incorrect order"
            ),
            ValidationRule(
                name="memory_entity_uniqueness",
                validation_type=ValidationType.CONSISTENCY,
                check=lambda ctx: self._check_memory_entity_uniqueness(ctx),
                error_message="Memory entity name already exists",
                severity="warning"
            )
        ]
    
    def validate_semantic_context(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate semantic correctness of an operation in context."""
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        for rule in self.context_rules:
            try:
                if not rule.check(context):
                    if rule.severity == "error":
                        results["errors"].append(rule.error_message)
                        results["valid"] = False
                    else:
                        results["warnings"].append(rule.error_message)
            except Exception as e:
                results["warnings"].append(f"Semantic validation failed: {str(e)}")
        
        # Add context-specific suggestions
        suggestions = self._get_context_suggestions(operation, context)
        results["suggestions"] = suggestions
        
        return results
    
    def _check_checklist_consistency(self, context: Dict[str, Any]) -> bool:
        """Check checklist items have consistent dependencies."""
        
        items = context.get("checklist_items", [])
        if not items:
            return True
        
        item_ids = {item.get("id") for item in items}
        
        for item in items:
            dependencies = item.get("dependencies", [])
            for dep in dependencies:
                if dep not in item_ids:
                    return False
        
        return True
    
    def _check_workflow_step_order(self, context: Dict[str, Any]) -> bool:
        """Check workflow steps are in correct order."""
        
        pattern = context.get("workflow_pattern")
        if not pattern:
            return True
        
        # Define expected step orders
        expected_orders = {
            "explore-plan-code-commit": ["explore", "plan", "code", "commit"],
            "tdd": ["test", "code", "refactor"],
            "refactor": ["analyze", "refactor", "verify"]
        }
        
        if pattern in expected_orders:
            steps = context.get("steps", [])
            expected = expected_orders[pattern]
            
            # Check if steps follow expected order
            step_commands = [step.get("command") for step in steps]
            
            # Simple check - more sophisticated in real implementation
            return True
        
        return True
    
    def _check_memory_entity_uniqueness(self, context: Dict[str, Any]) -> bool:
        """Check if memory entity name is unique."""
        
        # In real implementation, would check against existing entities
        return True
    
    def _get_context_suggestions(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """Get context-specific suggestions."""
        
        suggestions = []
        
        if operation == "create_unified_checklist":
            if context.get("item_count", 0) > 20:
                suggestions.append("Consider breaking down into smaller checklists")
        
        elif operation == "create_workflow":
            if context.get("step_count", 0) > 10:
                suggestions.append("Consider using sub-workflows for complex processes")
        
        return suggestions