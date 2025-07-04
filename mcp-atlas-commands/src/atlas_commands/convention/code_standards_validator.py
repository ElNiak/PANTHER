"""Code standards validation tool for ATLAS development conventions."""

import ast
import os
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


class ViolationType(Enum):
    """Types of code standard violations."""
    MISSING_TYPE_HINTS = "missing_type_hints"
    MISSING_DOCSTRING = "missing_docstring"
    IMPROPER_IMPORTS = "improper_imports"
    FORBIDDEN_PATTERNS = "forbidden_patterns"
    STYLE_VIOLATION = "style_violation"
    COMPLEXITY_ISSUE = "complexity_issue"


class ViolationSeverity(Enum):
    """Severity levels for violations."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CodeViolation(BaseModel):
    """A code standards violation."""
    type: ViolationType
    severity: ViolationSeverity
    line_number: Optional[int]
    column: Optional[int]
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False


class CodeStandardsValidationRequest(BaseModel):
    """Request model for code standards validation."""
    file_path: str
    content: Optional[str] = None
    standards_config: Optional[Dict] = None


class CodeStandardsValidationResponse(BaseModel):
    """Response model for code standards validation."""
    compliance_score: int  # 0-100
    violations: List[CodeViolation]
    auto_fix_suggestions: List[str]
    summary: Dict[str, int]  # Count violations by type


class CodeStandardsValidator:
    """Validates code against ATLAS development standards."""
    
    def __init__(self):
        self.forbidden_imports = {
            "from typing import *",  # Use specific imports
            "import *",  # Wildcard imports
        }
        
        self.required_type_hint_functions = [
            "__init__", "__call__", "__enter__", "__exit__"
        ]
        
        self.forbidden_patterns = [
            r"print\(",  # Use logging instead
            r"except:",  # Bare except clauses
            r"# TODO:",  # Use proper task management
            r"# FIXME:",  # Use proper task management
            r"# HACK:",  # Not allowed
        ]
        
        self.atlas_import_order = [
            "standard_library",
            "third_party", 
            "atlas_core",
            "local"
        ]
    
    def validate_code_standards(self, request: CodeStandardsValidationRequest) -> CodeStandardsValidationResponse:
        """
        Validate code against ATLAS standards.
        
        Args:
            request: Code standards validation request
            
        Returns:
            Validation response with violations and suggestions
        """
        file_path = request.file_path
        content = request.content
        
        # Read file if content not provided
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                return CodeStandardsValidationResponse(
                    compliance_score=0,
                    violations=[CodeViolation(
                        type=ViolationType.STYLE_VIOLATION,
                        severity=ViolationSeverity.ERROR,
                        line_number=None,
                        column=None,
                        message=f"Cannot read file: {str(e)}",
                        auto_fixable=False
                    )],
                    auto_fix_suggestions=[],
                    summary={"error": 1}
                )
        
        violations = []
        
        # Parse file extension
        file_ext = os.path.splitext(file_path)[1]
        
        if file_ext == '.py':
            violations.extend(self._validate_python_code(content, file_path))
        elif file_ext == '.md':
            violations.extend(self._validate_markdown_code(content, file_path))
        elif file_ext in ['.json', '.yaml', '.yml']:
            violations.extend(self._validate_config_file(content, file_path))
        
        # Calculate score and summary
        score = self._calculate_compliance_score(violations)
        summary = self._create_violation_summary(violations)
        auto_fix_suggestions = self._generate_auto_fix_suggestions(violations)
        
        return CodeStandardsValidationResponse(
            compliance_score=score,
            violations=violations,
            auto_fix_suggestions=auto_fix_suggestions,
            summary=summary
        )
    
    def _validate_python_code(self, content: str, file_path: str) -> List[CodeViolation]:
        """Validate Python-specific standards."""
        violations = []
        lines = content.split('\n')
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            violations.append(CodeViolation(
                type=ViolationType.STYLE_VIOLATION,
                severity=ViolationSeverity.ERROR,
                line_number=e.lineno,
                column=e.offset,
                message=f"Syntax error: {e.msg}",
                auto_fixable=False
            ))
            return violations
        
        # Check imports
        violations.extend(self._check_python_imports(tree, lines))
        
        # Check functions and classes
        violations.extend(self._check_python_functions(tree, lines))
        violations.extend(self._check_python_classes(tree, lines))
        
        # Check forbidden patterns
        violations.extend(self._check_forbidden_patterns(content, lines))
        
        # Check line length (88 chars for Black)
        violations.extend(self._check_line_length(lines, max_length=88))
        
        return violations
    
    def _check_python_imports(self, tree: ast.AST, lines: List[str]) -> List[CodeViolation]:
        """Check Python import standards."""
        violations = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
        
        # Check import order and style
        import_groups = {"standard": [], "third_party": [], "atlas": [], "local": []}
        
        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    # Check for wildcard imports
                    if alias.name == "*":
                        violations.append(CodeViolation(
                            type=ViolationType.IMPROPER_IMPORTS,
                            severity=ViolationSeverity.ERROR,
                            line_number=imp.lineno,
                            column=imp.col_offset,
                            message="Wildcard imports are forbidden",
                            suggestion="Import specific names instead",
                            auto_fixable=False
                        ))
            
            elif isinstance(imp, ast.ImportFrom):
                module = imp.module or ""
                
                # Check for relative imports at top level
                if imp.level > 0 and not module.startswith('.'):
                    violations.append(CodeViolation(
                        type=ViolationType.IMPROPER_IMPORTS,
                        severity=ViolationSeverity.WARNING,
                        line_number=imp.lineno,
                        column=imp.col_offset,
                        message="Prefer absolute imports from atlas.*",
                        suggestion=f"Use 'from atlas.{module}' instead",
                        auto_fixable=True
                    ))
                
                # Check for typing imports
                if module == "typing" and len(imp.names) > 3:
                    violations.append(CodeViolation(
                        type=ViolationType.IMPROPER_IMPORTS,
                        severity=ViolationSeverity.INFO,
                        line_number=imp.lineno,
                        column=imp.col_offset,
                        message="Consider importing specific typing classes",
                        suggestion="Use specific imports for better readability",
                        auto_fixable=True
                    ))
        
        return violations
    
    def _check_python_functions(self, tree: ast.AST, lines: List[str]) -> List[CodeViolation]:
        """Check Python function standards."""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for type hints
                if not node.returns and node.name not in ["__init__"]:
                    violations.append(CodeViolation(
                        type=ViolationType.MISSING_TYPE_HINTS,
                        severity=ViolationSeverity.WARNING,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' missing return type hint",
                        suggestion="Add -> ReturnType to function signature",
                        auto_fixable=False
                    ))
                
                # Check for parameter type hints
                for arg in node.args.args:
                    if not arg.annotation and arg.arg != "self":
                        violations.append(CodeViolation(
                            type=ViolationType.MISSING_TYPE_HINTS,
                            severity=ViolationSeverity.WARNING,
                            line_number=node.lineno,
                            column=node.col_offset,
                            message=f"Parameter '{arg.arg}' missing type hint",
                            suggestion=f"Add type hint: {arg.arg}: Type",
                            auto_fixable=False
                        ))
                
                # Check for docstrings
                if not ast.get_docstring(node) and not node.name.startswith("_"):
                    violations.append(CodeViolation(
                        type=ViolationType.MISSING_DOCSTRING,
                        severity=ViolationSeverity.WARNING,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message=f"Public function '{node.name}' missing docstring",
                        suggestion="Add docstring describing function purpose and parameters",
                        auto_fixable=False
                    ))
                
                # Check function length
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 30:
                        violations.append(CodeViolation(
                            type=ViolationType.COMPLEXITY_ISSUE,
                            severity=ViolationSeverity.WARNING,
                            line_number=node.lineno,
                            column=node.col_offset,
                            message=f"Function '{node.name}' is {func_length} lines (>30)",
                            suggestion="Consider breaking into smaller functions",
                            auto_fixable=False
                        ))
        
        return violations
    
    def _check_python_classes(self, tree: ast.AST, lines: List[str]) -> List[CodeViolation]:
        """Check Python class standards."""
        violations = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for docstrings
                if not ast.get_docstring(node):
                    violations.append(CodeViolation(
                        type=ViolationType.MISSING_DOCSTRING,
                        severity=ViolationSeverity.WARNING,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' missing docstring",
                        suggestion="Add docstring describing class purpose",
                        auto_fixable=False
                    ))
                
                # Check class naming (PascalCase)
                if not node.name[0].isupper() or '_' in node.name:
                    violations.append(CodeViolation(
                        type=ViolationType.STYLE_VIOLATION,
                        severity=ViolationSeverity.ERROR,
                        line_number=node.lineno,
                        column=node.col_offset,
                        message=f"Class '{node.name}' should use PascalCase",
                        suggestion=f"Rename to '{''.join(word.title() for word in node.name.split('_'))}'",
                        auto_fixable=True
                    ))
        
        return violations
    
    def _check_forbidden_patterns(self, content: str, lines: List[str]) -> List[CodeViolation]:
        """Check for forbidden code patterns."""
        violations = []
        
        for pattern in self.forbidden_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    suggestion = self._get_pattern_suggestion(pattern)
                    violations.append(CodeViolation(
                        type=ViolationType.FORBIDDEN_PATTERNS,
                        severity=ViolationSeverity.ERROR,
                        line_number=line_num,
                        column=None,
                        message=f"Forbidden pattern found: {pattern}",
                        suggestion=suggestion,
                        auto_fixable=False
                    ))
        
        return violations
    
    def _check_line_length(self, lines: List[str], max_length: int = 88) -> List[CodeViolation]:
        """Check line length compliance."""
        violations = []
        
        for line_num, line in enumerate(lines, 1):
            if len(line) > max_length:
                violations.append(CodeViolation(
                    type=ViolationType.STYLE_VIOLATION,
                    severity=ViolationSeverity.WARNING,
                    line_number=line_num,
                    column=max_length,
                    message=f"Line too long ({len(line)} > {max_length} characters)",
                    suggestion="Break line or use parentheses for continuation",
                    auto_fixable=True
                ))
        
        return violations
    
    def _validate_markdown_code(self, content: str, file_path: str) -> List[CodeViolation]:
        """Validate Markdown-specific standards."""
        violations = []
        lines = content.split('\n')
        
        # Check for proper heading hierarchy
        heading_levels = []
        for line_num, line in enumerate(lines, 1):
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_levels.append((level, line_num))
                
                # Check for skipped levels
                if heading_levels and len(heading_levels) > 1:
                    prev_level = heading_levels[-2][0]
                    if level > prev_level + 1:
                        violations.append(CodeViolation(
                            type=ViolationType.STYLE_VIOLATION,
                            severity=ViolationSeverity.WARNING,
                            line_number=line_num,
                            column=None,
                            message=f"Heading level skipped (#{level} after #{prev_level})",
                            suggestion="Use sequential heading levels",
                            auto_fixable=False
                        ))
        
        return violations
    
    def _validate_config_file(self, content: str, file_path: str) -> List[CodeViolation]:
        """Validate configuration file standards."""
        violations = []
        
        # Basic JSON/YAML validation would go here
        # For now, just check basic formatting
        
        return violations
    
    def _get_pattern_suggestion(self, pattern: str) -> str:
        """Get suggestion for forbidden pattern replacement."""
        suggestions = {
            r"print\(": "Use logging module instead of print statements",
            r"except:": "Specify exception type: except SpecificException:",
            r"# TODO:": "Create proper task in task management system",
            r"# FIXME:": "Create proper issue in task management system",
            r"# HACK:": "Implement proper solution instead of hack"
        }
        return suggestions.get(pattern, "See ATLAS development conventions")
    
    def _calculate_compliance_score(self, violations: List[CodeViolation]) -> int:
        """Calculate overall compliance score."""
        if not violations:
            return 100
        
        error_penalty = len([v for v in violations if v.severity == ViolationSeverity.ERROR]) * 20
        warning_penalty = len([v for v in violations if v.severity == ViolationSeverity.WARNING]) * 10
        info_penalty = len([v for v in violations if v.severity == ViolationSeverity.INFO]) * 5
        
        score = max(0, 100 - error_penalty - warning_penalty - info_penalty)
        return score
    
    def _create_violation_summary(self, violations: List[CodeViolation]) -> Dict[str, int]:
        """Create summary of violations by type."""
        summary = {}
        for violation in violations:
            severity = violation.severity.value
            summary[severity] = summary.get(severity, 0) + 1
        return summary
    
    def _generate_auto_fix_suggestions(self, violations: List[CodeViolation]) -> List[str]:
        """Generate list of auto-fixable suggestions."""
        suggestions = []
        for violation in violations:
            if violation.auto_fixable and violation.suggestion:
                suggestions.append(f"Line {violation.line_number}: {violation.suggestion}")
        return suggestions