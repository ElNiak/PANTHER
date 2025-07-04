"""
Quality Gates Module for Git Protocol Automation

Integrates linting, type checking, testing, and other quality checks
into the Git workflow to ensure code quality before commits.
"""

import subprocess
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CheckType(Enum):
    """Types of quality checks"""
    LINT = "lint"
    TYPE_CHECK = "type_check"
    TEST = "test"
    SECURITY = "security"
    COVERAGE = "coverage"
    DOCUMENTATION = "documentation"
    CONVENTION = "convention"


class CheckStatus(Enum):
    """Status of quality check"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a quality check"""
    check_type: CheckType
    status: CheckStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    file_issues: Optional[Dict[str, List[str]]] = None


@dataclass
class QualityGateReport:
    """Complete quality gate report"""
    overall_status: CheckStatus
    checks: List[CheckResult]
    can_commit: bool
    fix_suggestions: List[str]
    command_outputs: Dict[str, str]


class QualityGates:
    """Manages quality checks for Git workflow"""
    
    def __init__(self):
        # Python-specific tools configuration
        self.python_configs = {
            CheckType.LINT: {
                "tools": ["ruff", "flake8", "pylint"],
                "commands": {
                    "ruff": ["ruff", "check", "--format=json"],
                    "flake8": ["flake8", "--format=json"],
                    "pylint": ["pylint", "--output-format=json"]
                }
            },
            CheckType.TYPE_CHECK: {
                "tools": ["mypy", "pyright"],
                "commands": {
                    "mypy": ["mypy", "--json-report", "-"],
                    "pyright": ["pyright", "--outputjson"]
                }
            },
            CheckType.TEST: {
                "tools": ["pytest", "unittest"],
                "commands": {
                    "pytest": ["pytest", "--json-report", "--json-report-file=-"],
                    "unittest": ["python", "-m", "unittest", "discover"]
                }
            }
        }
        
        # JavaScript/TypeScript-specific tools
        self.js_configs = {
            CheckType.LINT: {
                "tools": ["eslint"],
                "commands": {
                    "eslint": ["eslint", "--format=json"]
                }
            },
            CheckType.TYPE_CHECK: {
                "tools": ["tsc"],
                "commands": {
                    "tsc": ["tsc", "--noEmit", "--pretty", "false"]
                }
            },
            CheckType.TEST: {
                "tools": ["jest", "mocha"],
                "commands": {
                    "jest": ["jest", "--json", "--outputFile=-"],
                    "mocha": ["mocha", "--reporter", "json"]
                }
            }
        }
        
        # Generic tools
        self.generic_configs = {
            CheckType.SECURITY: {
                "tools": ["gitleaks", "bandit"],
                "commands": {
                    "gitleaks": ["gitleaks", "detect", "--report-format", "json"],
                    "bandit": ["bandit", "-r", "-f", "json"]
                }
            }
        }
    
    def run_quality_gates(self, 
                         files: List[str], 
                         check_types: Optional[List[CheckType]] = None,
                         auto_fix: bool = False) -> QualityGateReport:
        """
        Run quality gates on specified files.
        
        Args:
            files: List of files to check
            check_types: Specific checks to run (None = all applicable)
            auto_fix: Whether to attempt auto-fixes
            
        Returns:
            Complete quality gate report
        """
        if not check_types:
            check_types = list(CheckType)
        
        checks = []
        command_outputs = {}
        
        # Group files by language
        file_groups = self._group_files_by_language(files)
        
        # Run checks for each language
        for language, lang_files in file_groups.items():
            if not lang_files:
                continue
                
            for check_type in check_types:
                if check_type in [CheckType.DOCUMENTATION, CheckType.CONVENTION]:
                    # These are handled separately
                    continue
                    
                result = self._run_language_check(
                    language, check_type, lang_files, auto_fix
                )
                if result:
                    checks.append(result)
                    if result.details and "command_output" in result.details:
                        command_outputs[f"{language}_{check_type.value}"] = result.details["command_output"]
        
        # Run language-agnostic checks
        if CheckType.DOCUMENTATION in check_types:
            doc_result = self._check_documentation(files)
            checks.append(doc_result)
        
        if CheckType.CONVENTION in check_types:
            conv_result = self._check_conventions(files)
            checks.append(conv_result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        can_commit = overall_status != CheckStatus.FAILED
        
        # Generate fix suggestions
        fix_suggestions = self._generate_fix_suggestions(checks, auto_fix)
        
        return QualityGateReport(
            overall_status=overall_status,
            checks=checks,
            can_commit=can_commit,
            fix_suggestions=fix_suggestions,
            command_outputs=command_outputs
        )
    
    def _group_files_by_language(self, files: List[str]) -> Dict[str, List[str]]:
        """Group files by programming language"""
        groups = {
            "python": [],
            "javascript": [],
            "typescript": [],
            "other": []
        }
        
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext in [".py", ".pyw"]:
                groups["python"].append(file_path)
            elif ext in [".js", ".jsx", ".mjs"]:
                groups["javascript"].append(file_path)
            elif ext in [".ts", ".tsx"]:
                groups["typescript"].append(file_path)
            else:
                groups["other"].append(file_path)
        
        return groups
    
    def _run_language_check(self, 
                           language: str, 
                           check_type: CheckType,
                           files: List[str],
                           auto_fix: bool) -> Optional[CheckResult]:
        """Run language-specific quality check"""
        # Get appropriate config
        if language == "python":
            configs = self.python_configs
        elif language in ["javascript", "typescript"]:
            configs = self.js_configs
        else:
            configs = self.generic_configs
        
        if check_type not in configs:
            return None
        
        config = configs[check_type]
        
        # Try each tool until one works
        for tool in config["tools"]:
            if self._is_tool_available(tool):
                return self._run_tool_check(
                    tool, config["commands"][tool], files, check_type, auto_fix
                )
        
        # No tools available
        return CheckResult(
            check_type=check_type,
            status=CheckStatus.SKIPPED,
            message=f"No {check_type.value} tools available for {language}",
            details={"suggested_tools": config["tools"]}
        )
    
    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in the environment"""
        try:
            result = subprocess.run(
                ["which", tool],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _run_tool_check(self, 
                       tool: str,
                       command: List[str],
                       files: List[str],
                       check_type: CheckType,
                       auto_fix: bool) -> CheckResult:
        """Run a specific tool check"""
        try:
            # Add files to command
            full_command = command + files
            
            # Add auto-fix flag if supported and requested
            if auto_fix and tool in ["ruff", "eslint"]:
                if tool == "ruff":
                    full_command = ["ruff", "check", "--fix"] + files
                elif tool == "eslint":
                    full_command = ["eslint", "--fix"] + files
            
            # Run the command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse results based on tool
            return self._parse_tool_output(tool, result, check_type, files)
            
        except subprocess.TimeoutExpired:
            return CheckResult(
                check_type=check_type,
                status=CheckStatus.FAILED,
                message=f"{tool} timed out after 60 seconds"
            )
        except Exception as e:
            return CheckResult(
                check_type=check_type,
                status=CheckStatus.FAILED,
                message=f"{tool} error: {str(e)}"
            )
    
    def _parse_tool_output(self, 
                          tool: str,
                          result: subprocess.CompletedProcess,
                          check_type: CheckType,
                          files: List[str]) -> CheckResult:
        """Parse tool output to determine check result"""
        # Success if return code is 0 (most tools)
        if result.returncode == 0:
            return CheckResult(
                check_type=check_type,
                status=CheckStatus.PASSED,
                message=f"{tool} check passed for {len(files)} files",
                details={"command_output": result.stdout}
            )
        
        # Try to parse JSON output for detailed issues
        file_issues = {}
        try:
            if tool in ["ruff", "flake8", "eslint"]:
                # These tools output JSON with file issues
                issues = json.loads(result.stdout)
                for file_path, file_issues_list in issues.items():
                    if isinstance(file_issues_list, list):
                        file_issues[file_path] = [
                            f"{issue.get('line', '?')}:{issue.get('column', '?')} - {issue.get('message', 'Unknown issue')}"
                            for issue in file_issues_list
                        ]
        except:
            # Fallback to text parsing
            file_issues["general"] = result.stdout.split('\n')[:10]  # First 10 lines
        
        # Determine status based on return code and issues
        status = CheckStatus.FAILED if result.returncode > 0 else CheckStatus.WARNING
        
        return CheckResult(
            check_type=check_type,
            status=status,
            message=f"{tool} found issues in {len(file_issues)} files",
            details={
                "return_code": result.returncode,
                "command_output": result.stdout[:1000]  # Limit output size
            },
            file_issues=file_issues
        )
    
    def _check_documentation(self, files: List[str]) -> CheckResult:
        """Check documentation standards"""
        issues = {}
        total_issues = 0
        
        for file_path in files:
            if not file_path.endswith('.py'):
                continue
                
            file_issues = []
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Check for module docstring
                if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                    file_issues.append("1:1 - Missing module docstring")
                
                # Check for function/class docstrings
                for i, line in enumerate(lines):
                    if line.strip().startswith('def ') or line.strip().startswith('class '):
                        # Check if next non-empty line is a docstring
                        j = i + 1
                        while j < len(lines) and not lines[j].strip():
                            j += 1
                        if j < len(lines) and not (lines[j].strip().startswith('"""') or lines[j].strip().startswith("'''")):
                            file_issues.append(f"{i+1}:1 - Missing docstring for {line.strip()}")
                
                if file_issues:
                    issues[file_path] = file_issues
                    total_issues += len(file_issues)
                    
            except Exception as e:
                issues[file_path] = [f"Error checking file: {str(e)}"]
        
        status = CheckStatus.PASSED if total_issues == 0 else CheckStatus.WARNING
        
        return CheckResult(
            check_type=CheckType.DOCUMENTATION,
            status=status,
            message=f"Documentation check: {total_issues} issues found",
            file_issues=issues
        )
    
    def _check_conventions(self, files: List[str]) -> CheckResult:
        """Check ATLAS coding conventions"""
        issues = {}
        total_issues = 0
        
        forbidden_patterns = [
            ("improved", "Avoid 'improved' in names"),
            ("new_", "Avoid 'new_' prefix in names"),
            ("enhanced", "Avoid 'enhanced' in names"),
            ("TODO", "TODOs should be tracked in task system"),
            ("FIXME", "FIXMEs should be tracked in task system")
        ]
        
        for file_path in files:
            file_issues = []
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines):
                    for pattern, message in forbidden_patterns:
                        if pattern in line:
                            file_issues.append(f"{i+1}:1 - {message}: '{pattern}' found")
                
                if file_issues:
                    issues[file_path] = file_issues
                    total_issues += len(file_issues)
                    
            except Exception as e:
                issues[file_path] = [f"Error checking file: {str(e)}"]
        
        status = CheckStatus.PASSED if total_issues == 0 else CheckStatus.WARNING
        
        return CheckResult(
            check_type=CheckType.CONVENTION,
            status=status,
            message=f"Convention check: {total_issues} issues found",
            file_issues=issues
        )
    
    def _determine_overall_status(self, checks: List[CheckResult]) -> CheckStatus:
        """Determine overall status from individual checks"""
        if any(check.status == CheckStatus.FAILED for check in checks):
            return CheckStatus.FAILED
        elif any(check.status == CheckStatus.WARNING for check in checks):
            return CheckStatus.WARNING
        else:
            return CheckStatus.PASSED
    
    def _generate_fix_suggestions(self, checks: List[CheckResult], auto_fix_attempted: bool) -> List[str]:
        """Generate suggestions for fixing issues"""
        suggestions = []
        
        for check in checks:
            if check.status == CheckStatus.FAILED:
                if check.check_type == CheckType.LINT:
                    if not auto_fix_attempted:
                        suggestions.append("Run with auto_fix=True to fix lint issues automatically")
                    else:
                        suggestions.append("Manual fixes needed for remaining lint issues")
                elif check.check_type == CheckType.TYPE_CHECK:
                    suggestions.append("Add type annotations or fix type errors")
                elif check.check_type == CheckType.TEST:
                    suggestions.append("Fix failing tests before committing")
            elif check.status == CheckStatus.WARNING:
                if check.check_type == CheckType.DOCUMENTATION:
                    suggestions.append("Add missing docstrings for better code documentation")
                elif check.check_type == CheckType.CONVENTION:
                    suggestions.append("Review ATLAS coding conventions in DEVELOPMENT_CONVENTION.md")
            elif check.status == CheckStatus.SKIPPED:
                if check.details and "suggested_tools" in check.details:
                    tools = ", ".join(check.details["suggested_tools"])
                    suggestions.append(f"Install {check.check_type.value} tools: {tools}")
        
        return suggestions
    
    def get_recommended_checks(self, file_paths: List[str]) -> List[CheckType]:
        """Get recommended checks based on file types"""
        checks = set()
        
        for file_path in file_paths:
            ext = Path(file_path).suffix.lower()
            
            # Always recommend these
            checks.add(CheckType.CONVENTION)
            
            # Language-specific recommendations
            if ext in [".py", ".js", ".ts"]:
                checks.add(CheckType.LINT)
                checks.add(CheckType.TYPE_CHECK)
                checks.add(CheckType.DOCUMENTATION)
            
            # Test files
            if "test" in file_path.lower():
                checks.add(CheckType.TEST)
            
            # Security for certain files
            if ext in [".env", ".yml", ".yaml", ".json"]:
                checks.add(CheckType.SECURITY)
        
        return list(checks)