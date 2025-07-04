"""File operation validation tool to enforce ATLAS convention of editing over creating."""

import os
import fnmatch
from pathlib import Path
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


class FileOperationType(Enum):
    """Types of file operations."""
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"


class ValidationResult(Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class FileOperationValidationRequest(BaseModel):
    """Request model for file operation validation."""
    operation: FileOperationType
    file_path: str
    project_root: Optional[str] = None
    context: Optional[Dict] = None


class FileOperationValidationResponse(BaseModel):
    """Response model for file operation validation."""
    validation_result: ValidationResult
    suggestions: List[str]
    affected_files: List[str]
    reasoning: str
    should_proceed: bool


class FileOperationValidator:
    """Validates file operations against ATLAS conventions."""
    
    def __init__(self):
        self.forbidden_create_patterns = [
            "*.md",  # Documentation files
            "README*",  # README files
            "*_new.*",  # Files with 'new' in name
            "*_improved.*",  # Files with 'improved' in name
            "*_enhanced.*",  # Files with 'enhanced' in name
        ]
        
        self.edit_preferred_extensions = [
            ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"
        ]
        
        self.atlas_core_patterns = [
            "CLAUDE.md",
            "SELF/*.md", 
            ".claude/commands/*.md",
            "DEVELOPMENT_*.md",
            "IMPORTANT_NOTES.md"
        ]
    
    def validate_file_operation(self, request: FileOperationValidationRequest) -> FileOperationValidationResponse:
        """
        Validate a file operation against ATLAS conventions.
        
        Args:
            request: File operation validation request
            
        Returns:
            Validation response with suggestions and affected files
        """
        operation = request.operation
        file_path = request.file_path
        project_root = request.project_root or os.getcwd()
        
        # Convert to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_root, file_path)
        
        # Get file info
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        
        if operation == FileOperationType.CREATE:
            return self._validate_create_operation(file_path, file_name, file_ext, project_root)
        elif operation == FileOperationType.EDIT:
            return self._validate_edit_operation(file_path, file_name, file_ext, project_root)
        elif operation == FileOperationType.DELETE:
            return self._validate_delete_operation(file_path, file_name, file_ext, project_root)
        
        return FileOperationValidationResponse(
            validation_result=ValidationResult.FAIL,
            suggestions=["Unknown operation type"],
            affected_files=[],
            reasoning="Invalid operation type specified",
            should_proceed=False
        )
    
    def _validate_create_operation(self, file_path: str, file_name: str, file_ext: str, project_root: str) -> FileOperationValidationResponse:
        """Validate file creation operation."""
        suggestions = []
        affected_files = []
        reasoning = ""
        
        # Check if file already exists
        if os.path.exists(file_path):
            return FileOperationValidationResponse(
                validation_result=ValidationResult.FAIL,
                suggestions=["Use EDIT operation instead - file already exists"],
                affected_files=[file_path],
                reasoning="File already exists, should edit instead of create",
                should_proceed=False
            )
        
        # Check forbidden creation patterns
        for pattern in self.forbidden_create_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                similar_files = self._find_similar_files(file_path, project_root)
                suggestions.append(f"ATLAS convention: Don't create {pattern} files")
                suggestions.append("Consider editing existing files instead:")
                suggestions.extend([f"  - {f}" for f in similar_files[:3]])
                
                return FileOperationValidationResponse(
                    validation_result=ValidationResult.FAIL,
                    suggestions=suggestions,
                    affected_files=similar_files,
                    reasoning=f"Creating {pattern} files violates ATLAS convention",
                    should_proceed=False
                )
        
        # Check for forbidden naming patterns
        forbidden_words = ["new", "improved", "enhanced", "updated", "modified", "fixed"]
        for word in forbidden_words:
            if word.lower() in file_name.lower():
                suggestions.append(f"Avoid temporal words like '{word}' in filenames")
                suggestions.append("Use evergreen, descriptive names instead")
                suggestions.append(f"Example: {file_name.replace(word, '').replace('_', '').replace('-', '')}")
                
                return FileOperationValidationResponse(
                    validation_result=ValidationResult.WARNING,
                    suggestions=suggestions,
                    affected_files=[],
                    reasoning=f"Filename contains temporal word '{word}' which isn't evergreen",
                    should_proceed=False
                )
        
        # Check if similar functionality exists
        if file_ext in self.edit_preferred_extensions:
            similar_files = self._find_similar_functionality(file_path, project_root)
            if similar_files:
                suggestions.append("Found similar files - consider extending existing code:")
                suggestions.extend([f"  - {f}" for f in similar_files[:3]])
                
                return FileOperationValidationResponse(
                    validation_result=ValidationResult.WARNING,
                    suggestions=suggestions,
                    affected_files=similar_files,
                    reasoning="Similar functionality may already exist",
                    should_proceed=True
                )
        
        # File creation is acceptable
        return FileOperationValidationResponse(
            validation_result=ValidationResult.PASS,
            suggestions=["File creation approved"],
            affected_files=[],
            reasoning="No convention violations detected",
            should_proceed=True
        )
    
    def _validate_edit_operation(self, file_path: str, file_name: str, file_ext: str, project_root: str) -> FileOperationValidationResponse:
        """Validate file edit operation."""
        if not os.path.exists(file_path):
            return FileOperationValidationResponse(
                validation_result=ValidationResult.FAIL,
                suggestions=["File doesn't exist - use CREATE operation"],
                affected_files=[],
                reasoning="Cannot edit non-existent file",
                should_proceed=False
            )
        
        # Check if it's an ATLAS core file that needs special handling
        rel_path = os.path.relpath(file_path, project_root)
        for pattern in self.atlas_core_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return FileOperationValidationResponse(
                    validation_result=ValidationResult.WARNING,
                    suggestions=["This is an ATLAS core file - ensure changes align with architecture"],
                    affected_files=[file_path],
                    reasoning="Modifying ATLAS core configuration files",
                    should_proceed=True
                )
        
        # Edit operation is generally preferred
        return FileOperationValidationResponse(
            validation_result=ValidationResult.PASS,
            suggestions=["Edit operation approved - follows ATLAS conventions"],
            affected_files=[],
            reasoning="Editing existing files is preferred over creating new ones",
            should_proceed=True
        )
    
    def _validate_delete_operation(self, file_path: str, file_name: str, file_ext: str, project_root: str) -> FileOperationValidationResponse:
        """Validate file deletion operation."""
        if not os.path.exists(file_path):
            return FileOperationValidationResponse(
                validation_result=ValidationResult.FAIL,
                suggestions=["File doesn't exist - nothing to delete"],
                affected_files=[],
                reasoning="Cannot delete non-existent file",
                should_proceed=False
            )
        
        # Check if it's an ATLAS core file
        rel_path = os.path.relpath(file_path, project_root)
        for pattern in self.atlas_core_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return FileOperationValidationResponse(
                    validation_result=ValidationResult.FAIL,
                    suggestions=["Cannot delete ATLAS core files", "Consider editing content instead"],
                    affected_files=[file_path],
                    reasoning="ATLAS core files should not be deleted",
                    should_proceed=False
                )
        
        # Deletion is acceptable for non-core files
        return FileOperationValidationResponse(
            validation_result=ValidationResult.PASS,
            suggestions=["Deletion approved"],
            affected_files=[],
            reasoning="Non-core file deletion is acceptable",
            should_proceed=True
        )
    
    def _find_similar_files(self, file_path: str, project_root: str) -> List[str]:
        """Find files similar to the one being created."""
        file_name = os.path.basename(file_path)
        file_base = os.path.splitext(file_name)[0]
        file_ext = os.path.splitext(file_name)[1]
        
        similar_files = []
        
        # Search for files with similar names
        for root, dirs, files in os.walk(project_root):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path_full = os.path.join(root, file)
                rel_path = os.path.relpath(file_path_full, project_root)
                
                # Check for similar name or extension
                if (file_base.lower() in file.lower() or 
                    file.lower() in file_base.lower() or
                    (file_ext and file.endswith(file_ext))):
                    similar_files.append(rel_path)
        
        return similar_files[:10]  # Limit results
    
    def _find_similar_functionality(self, file_path: str, project_root: str) -> List[str]:
        """Find files that might have similar functionality."""
        file_name = os.path.basename(file_path)
        file_base = os.path.splitext(file_name)[0]
        
        # Extract potential keywords from filename
        keywords = []
        for delimiter in ['_', '-', '.']:
            keywords.extend(file_base.split(delimiter))
        
        keywords = [k.lower() for k in keywords if len(k) > 3]  # Filter short words
        
        similar_files = []
        
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_lower = file.lower()
                
                # Check if any keyword appears in filename
                for keyword in keywords:
                    if keyword in file_lower:
                        file_path_full = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path_full, project_root)
                        similar_files.append(rel_path)
                        break
        
        return similar_files[:5]  # Limit results