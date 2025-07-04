"""Naming convention enforcement tool for ATLAS development standards."""

import re
from typing import Dict, List, Optional
from enum import Enum

try:
    from pydantic import BaseModel
except ImportError:
    # Fallback for environments without pydantic
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class NamingType(Enum):
    """Types of names to validate."""
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    FILE = "file"
    TASK = "task"
    BRANCH = "branch"
    CONSTANT = "constant"
    MODULE = "module"


class NamingViolation(BaseModel):
    """A naming convention violation."""
    rule: str
    description: str
    severity: str  # "error", "warning", "info"
    suggestion: Optional[str] = None


class NamingValidationRequest(BaseModel):
    """Request model for naming validation."""
    name: str
    type: NamingType
    context: Optional[Dict] = None


class NamingValidationResponse(BaseModel):
    """Response model for naming validation."""
    is_valid: bool
    violations: List[NamingViolation]
    suggested_alternatives: List[str]
    score: int  # 0-100, where 100 is perfect compliance


class NamingConventionEnforcer:
    """Enforces ATLAS naming conventions across different contexts."""
    
    def __init__(self):
        self.forbidden_words = {
            "temporal": ["new", "old", "improved", "enhanced", "updated", "modified", "fixed", "current", "latest", "recent"],
            "vague": ["thing", "stuff", "data", "info", "temp", "tmp", "test", "example"],
            "redundant": ["manager_manager", "handler_handler", "service_service"]
        }
        
        self.python_reserved_words = {
            "and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else",
            "except", "exec", "finally", "for", "from", "global", "if", "import", "in", "is",
            "lambda", "not", "or", "pass", "print", "raise", "return", "try", "while", "with", "yield"
        }
        
        self.atlas_preferred_patterns = {
            NamingType.FUNCTION: r"^[a-z][a-z0-9_]*[a-z0-9]$",
            NamingType.CLASS: r"^[A-Z][a-zA-Z0-9]*$",
            NamingType.VARIABLE: r"^[a-z][a-z0-9_]*[a-z0-9]$",
            NamingType.CONSTANT: r"^[A-Z][A-Z0-9_]*[A-Z0-9]$",
            NamingType.FILE: r"^[a-z][a-z0-9_]*[a-z0-9]\.(py|md|json|yaml|yml|toml)$",
            NamingType.MODULE: r"^[a-z][a-z0-9_]*[a-z0-9]$",
            NamingType.TASK: r"^[a-z][a-z0-9\-]*[a-z0-9]$",
            NamingType.BRANCH: r"^(feature|fix|docs|refactor|test)/[a-z][a-z0-9\-]*[a-z0-9]$"
        }
    
    def validate_naming_convention(self, request: NamingValidationRequest) -> NamingValidationResponse:
        """
        Validate a name against ATLAS conventions.
        
        Args:
            request: Naming validation request
            
        Returns:
            Validation response with violations and suggestions
        """
        name = request.name.strip()
        naming_type = request.type
        
        violations = []
        suggestions = []
        score = 100
        
        # Basic validation
        violations.extend(self._check_basic_rules(name, naming_type))
        
        # Forbidden words check
        violations.extend(self._check_forbidden_words(name))
        
        # Pattern matching
        violations.extend(self._check_pattern_compliance(name, naming_type))
        
        # Type-specific rules
        violations.extend(self._check_type_specific_rules(name, naming_type))
        
        # Generate suggestions
        suggestions = self._generate_suggestions(name, naming_type, violations)
        
        # Calculate score
        score = self._calculate_score(violations)
        
        return NamingValidationResponse(
            is_valid=len([v for v in violations if v.severity == "error"]) == 0,
            violations=violations,
            suggested_alternatives=suggestions,
            score=score
        )
    
    def _check_basic_rules(self, name: str, naming_type: NamingType) -> List[NamingViolation]:
        """Check basic naming rules."""
        violations = []
        
        # Empty name
        if not name:
            violations.append(NamingViolation(
                rule="non_empty",
                description="Name cannot be empty",
                severity="error"
            ))
            return violations
        
        # Length checks
        if len(name) < 2:
            violations.append(NamingViolation(
                rule="minimum_length",
                description="Name must be at least 2 characters long",
                severity="error"
            ))
        
        if len(name) > 50 and naming_type != NamingType.TASK:
            violations.append(NamingViolation(
                rule="maximum_length",
                description="Name should be under 50 characters for readability",
                severity="warning"
            ))
        
        # No leading/trailing whitespace or special chars
        if name != name.strip():
            violations.append(NamingViolation(
                rule="no_whitespace",
                description="Name cannot have leading or trailing whitespace",
                severity="error"
            ))
        
        # Python reserved words
        if naming_type in [NamingType.FUNCTION, NamingType.CLASS, NamingType.VARIABLE, NamingType.CONSTANT, NamingType.MODULE]:
            if name.lower() in self.python_reserved_words:
                violations.append(NamingViolation(
                    rule="no_reserved_words",
                    description=f"'{name}' is a Python reserved word",
                    severity="error",
                    suggestion=f"Use '{name}_value' or '{name}_obj' instead"
                ))
        
        return violations
    
    def _check_forbidden_words(self, name: str) -> List[NamingViolation]:
        """Check for forbidden words in naming."""
        violations = []
        name_lower = name.lower()
        
        # Temporal words
        for word in self.forbidden_words["temporal"]:
            if word in name_lower:
                violations.append(NamingViolation(
                    rule="no_temporal_words",
                    description=f"Avoid temporal word '{word}' - use evergreen names",
                    severity="error",
                    suggestion=f"Describe what it IS, not when it was created"
                ))
        
        # Vague words
        for word in self.forbidden_words["vague"]:
            if word in name_lower:
                violations.append(NamingViolation(
                    rule="no_vague_words",
                    description=f"'{word}' is too vague - be more specific",
                    severity="warning",
                    suggestion=f"Describe the specific purpose or domain"
                ))
        
        # Redundant patterns
        for pattern in self.forbidden_words["redundant"]:
            if pattern in name_lower:
                violations.append(NamingViolation(
                    rule="no_redundancy",
                    description=f"Redundant pattern '{pattern}' detected",
                    severity="warning",
                    suggestion=f"Remove redundant words"
                ))
        
        return violations
    
    def _check_pattern_compliance(self, name: str, naming_type: NamingType) -> List[NamingViolation]:
        """Check pattern compliance for specific naming types."""
        violations = []
        
        if naming_type not in self.atlas_preferred_patterns:
            return violations
        
        pattern = self.atlas_preferred_patterns[naming_type]
        
        if not re.match(pattern, name):
            violations.append(NamingViolation(
                rule="pattern_compliance",
                description=f"Name doesn't match {naming_type.value} pattern",
                severity="error",
                suggestion=self._get_pattern_suggestion(naming_type)
            ))
        
        return violations
    
    def _check_type_specific_rules(self, name: str, naming_type: NamingType) -> List[NamingViolation]:
        """Check type-specific naming rules."""
        violations = []
        
        if naming_type == NamingType.CLASS:
            if not name[0].isupper():
                violations.append(NamingViolation(
                    rule="class_pascal_case",
                    description="Class names should use PascalCase",
                    severity="error",
                    suggestion=f"Use '{name.title()}' instead"
                ))
            
            if "_" in name:
                violations.append(NamingViolation(
                    rule="class_no_underscores",
                    description="Class names should not contain underscores",
                    severity="error",
                    suggestion=f"Use '{''.join(word.title() for word in name.split('_'))}' instead"
                ))
        
        elif naming_type == NamingType.CONSTANT:
            if not name.isupper():
                violations.append(NamingViolation(
                    rule="constant_upper_case",
                    description="Constants should use UPPER_CASE",
                    severity="error",
                    suggestion=f"Use '{name.upper()}' instead"
                ))
        
        elif naming_type in [NamingType.FUNCTION, NamingType.VARIABLE, NamingType.MODULE]:
            if not name.islower() and "_" not in name:
                violations.append(NamingViolation(
                    rule="snake_case",
                    description=f"{naming_type.value} names should use snake_case",
                    severity="error",
                    suggestion=f"Use '{self._to_snake_case(name)}' instead"
                ))
        
        elif naming_type == NamingType.TASK:
            if name.startswith("task-") or name.startswith("subtask-"):
                violations.append(NamingViolation(
                    rule="task_no_prefix",
                    description="Don't include 'task' or 'subtask' prefix in task names",
                    severity="warning",
                    suggestion=f"Use '{name.replace('task-', '').replace('subtask-', '')}' instead"
                ))
        
        elif naming_type == NamingType.BRANCH:
            if not name.startswith(("feature/", "fix/", "docs/", "refactor/", "test/")):
                violations.append(NamingViolation(
                    rule="branch_type_prefix",
                    description="Branch names should start with type prefix",
                    severity="error",
                    suggestion="Use feature/, fix/, docs/, refactor/, or test/ prefix"
                ))
        
        return violations
    
    def _generate_suggestions(self, name: str, naming_type: NamingType, violations: List[NamingViolation]) -> List[str]:
        """Generate naming suggestions based on violations."""
        suggestions = []
        
        # Extract suggestions from violations
        for violation in violations:
            if violation.suggestion:
                suggestions.append(violation.suggestion)
        
        # Generate format-specific suggestions
        if naming_type == NamingType.CLASS:
            pascal_case = ''.join(word.title() for word in re.split(r'[_\-\s]+', name))
            suggestions.append(f"PascalCase: {pascal_case}")
        
        elif naming_type in [NamingType.FUNCTION, NamingType.VARIABLE, NamingType.MODULE]:
            suggestions.append(f"snake_case: {self._to_snake_case(name)}")
        
        elif naming_type == NamingType.CONSTANT:
            suggestions.append(f"UPPER_CASE: {name.upper().replace('-', '_').replace(' ', '_')}")
        
        elif naming_type == NamingType.TASK:
            clean_name = re.sub(r'[^a-zA-Z0-9\-]', '-', name.lower())
            clean_name = re.sub(r'-+', '-', clean_name).strip('-')
            suggestions.append(f"kebab-case: {clean_name}")
        
        # Remove duplicates and limit
        suggestions = list(dict.fromkeys(suggestions))[:5]
        
        return suggestions
    
    def _get_pattern_suggestion(self, naming_type: NamingType) -> str:
        """Get pattern suggestion for naming type."""
        suggestions = {
            NamingType.FUNCTION: "Use snake_case (e.g., calculate_total)",
            NamingType.CLASS: "Use PascalCase (e.g., DataProcessor)",
            NamingType.VARIABLE: "Use snake_case (e.g., user_count)",
            NamingType.CONSTANT: "Use UPPER_CASE (e.g., MAX_RETRY_COUNT)",
            NamingType.FILE: "Use snake_case with extension (e.g., data_processor.py)",
            NamingType.MODULE: "Use snake_case (e.g., data_processing)",
            NamingType.TASK: "Use kebab-case (e.g., implement-user-auth)",
            NamingType.BRANCH: "Use type/name format (e.g., feature/user-authentication)"
        }
        return suggestions.get(naming_type, "Follow ATLAS naming conventions")
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        # Handle PascalCase and camelCase
        name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
        name = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', name)
        
        # Replace spaces and hyphens with underscores
        name = re.sub(r'[\s\-]+', '_', name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        return name.lower().strip('_')
    
    def _calculate_score(self, violations: List[NamingViolation]) -> int:
        """Calculate naming quality score."""
        if not violations:
            return 100
        
        error_penalty = len([v for v in violations if v.severity == "error"]) * 25
        warning_penalty = len([v for v in violations if v.severity == "warning"]) * 10
        info_penalty = len([v for v in violations if v.severity == "info"]) * 5
        
        score = max(0, 100 - error_penalty - warning_penalty - info_penalty)
        return score