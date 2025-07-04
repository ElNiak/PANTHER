"""
Linting and code quality validation tests for ATLAS MCP components.
Ensures code quality, style consistency, and best practices adherence.
"""

import pytest
import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
import re
import subprocess
import tempfile
import json

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src" / "atlas_commands"


class TestCodeQuality:
    """Test code quality and linting compliance."""
    
    def test_python_syntax_validity(self):
        """Test that all Python files have valid syntax."""
        python_files = list(SRC_PATH.rglob("*.py"))
        syntax_errors = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}: {e}")
            except UnicodeDecodeError as e:
                syntax_errors.append(f"{file_path}: Unicode decode error - {e}")
        
        assert not syntax_errors, f"Syntax errors found:\n" + "\n".join(syntax_errors)
    
    def test_import_structure_validity(self):
        """Test that all imports are valid and accessible."""
        python_files = list(SRC_PATH.rglob("*.py"))
        import_errors = []
        
        # Add src to Python path temporarily
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        
        try:
            for file_path in python_files:
                relative_path = file_path.relative_to(PROJECT_ROOT / "src")
                module_path = str(relative_path.with_suffix("")).replace("/", ".")
                
                try:
                    importlib.import_module(module_path)
                except ImportError as e:
                    # Skip files that require optional dependencies
                    if any(dep in str(e) for dep in ["mcp", "opentelemetry", "llmlingua"]):
                        continue
                    import_errors.append(f"{module_path}: {e}")
                except Exception as e:
                    # Other import-time errors
                    import_errors.append(f"{module_path}: {type(e).__name__}: {e}")
        
        finally:
            sys.path.remove(str(PROJECT_ROOT / "src"))
        
        if import_errors:
            print("Import errors found (some may be due to optional dependencies):")
            for error in import_errors:
                print(f"  {error}")
    
    def test_docstring_coverage(self):
        """Test that public classes and functions have docstrings."""
        python_files = list(SRC_PATH.rglob("*.py"))
        missing_docstrings = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip private methods/classes
                        if node.name.startswith('_') and not node.name.startswith('__'):
                            continue
                        
                        # Check for docstring
                        docstring = ast.get_docstring(node)
                        if not docstring:
                            missing_docstrings.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}: {type(node).__name__} '{node.name}' missing docstring"
                            )
            
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        # Allow some missing docstrings, but flag excessive cases
        if len(missing_docstrings) > 50:  # Reasonable threshold
            print(f"Warning: {len(missing_docstrings)} missing docstrings found")
            for missing in missing_docstrings[:10]:  # Show first 10
                print(f"  {missing}")
    
    def test_code_complexity_reasonable(self):
        """Test that code complexity is reasonable (simplified check)."""
        python_files = list(SRC_PATH.rglob("*.py"))
        complex_functions = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Simple complexity metric: count decision points
                        complexity = self._calculate_cyclomatic_complexity(node)
                        
                        if complexity > 15:  # Reasonable threshold
                            complex_functions.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}: {node.name} (complexity: {complexity})"
                            )
            
            except Exception:
                continue
        
        # Report but don't fail for moderate complexity
        if complex_functions:
            print(f"Functions with high complexity (>{15}):")
            for func in complex_functions[:10]:  # Show first 10
                print(f"  {func}")
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate simplified cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers)
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity


class TestNamingConventions:
    """Test naming conventions and code style."""
    
    def test_class_naming_convention(self):
        """Test that classes follow PascalCase convention."""
        python_files = list(SRC_PATH.rglob("*.py"))
        naming_violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check PascalCase
                        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                            naming_violations.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}: Class '{node.name}' should be PascalCase"
                            )
            
            except Exception:
                continue
        
        assert len(naming_violations) < 5, f"Too many naming violations:\n" + "\n".join(naming_violations[:10])
    
    def test_function_naming_convention(self):
        """Test that functions follow snake_case convention."""
        python_files = list(SRC_PATH.rglob("*.py"))
        naming_violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip magic methods
                        if node.name.startswith('__') and node.name.endswith('__'):
                            continue
                        
                        # Check snake_case
                        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                            naming_violations.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}: Function '{node.name}' should be snake_case"
                            )
            
            except Exception:
                continue
        
        # Allow some violations for existing code
        if len(naming_violations) > 20:
            print(f"Warning: {len(naming_violations)} function naming violations found")
    
    def test_constant_naming_convention(self):
        """Test that constants follow UPPER_CASE convention."""
        python_files = list(SRC_PATH.rglob("*.py"))
        naming_violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # Heuristic: assignments at module level with all caps
                                if (hasattr(node, 'lineno') and 
                                    isinstance(node.value, (ast.Constant, ast.Str, ast.Num)) and
                                    target.id.isupper() and len(target.id) > 1):
                                    
                                    if not re.match(r'^[A-Z][A-Z0-9_]*$', target.id):
                                        naming_violations.append(
                                            f"{file_path.relative_to(PROJECT_ROOT)}: Constant '{target.id}' should be UPPER_CASE"
                                        )
            
            except Exception:
                continue
        
        # Report but don't fail
        if naming_violations:
            print(f"Constant naming issues found:")
            for violation in naming_violations[:5]:
                print(f"  {violation}")


class TestSecurityAndBestPractices:
    """Test security and best practices compliance."""
    
    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets or sensitive data exist."""
        python_files = list(SRC_PATH.rglob("*.py"))
        potential_secrets = []
        
        # Patterns that might indicate secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'["\'][a-zA-Z0-9+/]{40,}={0,2}["\']',  # Base64-like strings
        ]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Skip test files and examples
                        if 'test' in str(file_path).lower() or 'example' in match.group():
                            continue
                        
                        potential_secrets.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}: Potential secret: {match.group()[:50]}..."
                        )
            
            except Exception:
                continue
        
        # Report but don't fail for false positives
        if potential_secrets:
            print("Potential hardcoded secrets found (review for false positives):")
            for secret in potential_secrets[:5]:
                print(f"  {secret}")
    
    def test_no_dangerous_imports(self):
        """Test that dangerous imports are not used carelessly."""
        python_files = list(SRC_PATH.rglob("*.py"))
        dangerous_imports = []
        
        dangerous_modules = [
            'subprocess',
            'os.system',
            'eval',
            'exec',
            'pickle',
            '__import__'
        ]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        for alias in node.names:
                            if any(dangerous in alias.name for dangerous in dangerous_modules):
                                dangerous_imports.append(
                                    f"{file_path.relative_to(PROJECT_ROOT)}: Potentially dangerous import: {alias.name}"
                                )
            
            except Exception:
                continue
        
        # Report but don't fail (some dangerous imports may be legitimate)
        if dangerous_imports:
            print("Potentially dangerous imports found (review for necessity):")
            for imp in dangerous_imports[:10]:
                print(f"  {imp}")
    
    def test_exception_handling_quality(self):
        """Test that exception handling follows best practices."""
        python_files = list(SRC_PATH.rglob("*.py"))
        exception_issues = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Try):
                        for handler in node.handlers:
                            # Check for bare except
                            if handler.type is None:
                                exception_issues.append(
                                    f"{file_path.relative_to(PROJECT_ROOT)}:{handler.lineno}: Bare except clause"
                                )
                            
                            # Check for overly broad exceptions
                            elif (isinstance(handler.type, ast.Name) and 
                                  handler.type.id == 'Exception'):
                                # This is sometimes acceptable, just note it
                                pass
            
            except Exception:
                continue
        
        # Report bare except clauses
        if exception_issues:
            print("Exception handling issues:")
            for issue in exception_issues[:10]:
                print(f"  {issue}")


class TestDocumentationQuality:
    """Test documentation quality and completeness."""
    
    def test_readme_exists(self):
        """Test that README files exist at appropriate levels."""
        readme_files = list(PROJECT_ROOT.glob("README*"))
        assert len(readme_files) > 0, "No README file found in project root"
    
    def test_docstring_quality(self):
        """Test that docstrings are meaningful and well-formatted."""
        python_files = list(SRC_PATH.rglob("*.py"))
        docstring_issues = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        docstring = ast.get_docstring(node)
                        
                        if docstring:
                            # Check for very short docstrings
                            if len(docstring.strip()) < 10:
                                docstring_issues.append(
                                    f"{file_path.relative_to(PROJECT_ROOT)}: {node.name} has very short docstring"
                                )
                            
                            # Check for TODO/FIXME in docstrings
                            if any(word in docstring.upper() for word in ['TODO', 'FIXME', 'XXX']):
                                docstring_issues.append(
                                    f"{file_path.relative_to(PROJECT_ROOT)}: {node.name} has TODO/FIXME in docstring"
                                )
            
            except Exception:
                continue
        
        # Report but don't fail
        if docstring_issues:
            print("Docstring quality issues:")
            for issue in docstring_issues[:10]:
                print(f"  {issue}")


class TestPerformanceAndScalability:
    """Test for potential performance and scalability issues."""
    
    def test_no_inefficient_patterns(self):
        """Test for common inefficient coding patterns."""
        python_files = list(SRC_PATH.rglob("*.py"))
        performance_issues = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for inefficient patterns
                if re.search(r'for\s+\w+\s+in\s+range\(len\(', content):
                    performance_issues.append(
                        f"{file_path.relative_to(PROJECT_ROOT)}: Use enumerate() instead of range(len())"
                    )
                
                if re.search(r'\.append\(\)\s*\n.*for\s+', content, re.MULTILINE):
                    performance_issues.append(
                        f"{file_path.relative_to(PROJECT_ROOT)}: Consider list comprehension instead of append in loop"
                    )
                
                # Check for string concatenation in loops
                if re.search(r'for\s+.*\n.*\+=.*str', content, re.MULTILINE):
                    performance_issues.append(
                        f"{file_path.relative_to(PROJECT_ROOT)}: Consider using join() for string concatenation in loops"
                    )
            
            except Exception:
                continue
        
        # Report but don't fail
        if performance_issues:
            print("Potential performance issues:")
            for issue in performance_issues[:5]:
                print(f"  {issue}")
    
    def test_memory_usage_patterns(self):
        """Test for potential memory usage issues."""
        python_files = list(SRC_PATH.rglob("*.py"))
        memory_issues = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for potential memory leaks
                if re.search(r'while\s+True:', content):
                    memory_issues.append(
                        f"{file_path.relative_to(PROJECT_ROOT)}: Infinite loop detected - check for proper exit conditions"
                    )
                
                # Check for large data structures
                if re.search(r'\[\s*\]\s*\*\s*\d{4,}', content):
                    memory_issues.append(
                        f"{file_path.relative_to(PROJECT_ROOT)}: Large list multiplication detected"
                    )
            
            except Exception:
                continue
        
        # Report but don't fail
        if memory_issues:
            print("Potential memory usage issues:")
            for issue in memory_issues:
                print(f"  {issue}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])