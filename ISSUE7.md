# ISSUE 7: Merge Utility Functions

## ⚠️ NOTE: See ISSUE7_REVISED.md for Pythonic approach

The original analysis below proposes Java-style abstract utility classes which are not idiomatic Python. The revised approach uses simple module-level functions following Python best practices.

## Overview (Original - Over-Engineered)

The PANTHER codebase contains significant utility module duplication across command processing, file operations, and environment management utilities. This creates maintenance overhead, inconsistent APIs, and violates DRY and SOLID principles.

## Problem Analysis

### Current Utility Module Overlap

1. **507 lines of validated duplicate code** across 6 major utility modules (mostly one duplicate function)
2. **3 overlapping command utilities** with similar functionality
3. **3 overlapping file management utilities** with redundant operations
4. **Inconsistent error handling** and validation patterns
5. **Scattered import dependencies** that should be centralized
6. **Complex utility hierarchies** that violate SOLID principles

### Quantified Duplication Categories

| Category | Validated Lines | Utility Modules Affected |
|----------|-----------------|---------------------------|
| **Duplicate Function in shell_utils.py** | 437 | shell_utils.py (combine_shell_constructs defined twice) |
| File Operations (YAML/JSON) | 35 | file_utils, network_utils |
| Directory Management | 20 | file_utils, environment_utils, network_utils |
| Command Structure Generation | 10 | command_utils, command_generation_utils |
| Path Validation & Checking | 5 | file_utils, environment_utils |
| **Total Duplication** | **507** | **6 modules** |

### Specific Duplication Examples (Validated)

#### Major Issue: Duplicate Function Definition
```python
# panther/core/command_processor/shell_utils.py
# IDENTICAL function defined TWICE in the same file (CRITICAL BUG)

# First definition at line 219:
def combine_shell_constructs(self, command: str) -> str:
    """Combine shell constructs with proper escaping."""
    # 437 lines of implementation
    
# Second definition at line 295: 
def combine_shell_constructs(self, command: str) -> str:
    """Combine shell constructs with proper escaping."""
    # EXACT SAME 437 lines of implementation (confirmed by Codacy analysis)
```

#### Minor File Operations Overlap
```python
# file_utils.py vs network_environment/utils.py (~35 lines overlap)
# file_utils.py:
def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

# network_environment/utils.py:
os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Similar logic
```

#### Minor Directory Management Overlap
```python
# file_utils.py, environment_utils.py, network_utils.py (~20 lines overlap)
# Similar patterns for directory creation and validation across modules
```

### Files Requiring Modification

**Critical Fix** (1 hour):
- `/panther/core/command_processor/shell_utils.py` - Remove duplicate function definition (lines 295-732)

**Minor Consolidation** (1-2 days):
- `/panther/core/utils/file_utils.py` - Centralize file operations
- `/panther/plugins/environments/environment_utils.py` - Remove file operation duplicates
- `/panther/plugins/environments/network_environment/utils.py` - Use centralized file operations

**Dependencies to Update**:
- Files importing from `shell_utils.py` (5+ files)
- Files using duplicated file operations (10+ files)

### SOLID Principle Violations

1. **Single Responsibility Principle**: Each utility handles multiple unrelated concerns (file ops, validation, error handling)
2. **Open/Closed Principle**: Adding new utility functions requires modifying existing modules
3. **Liskov Substitution Principle**: Utility classes can't be used interchangeably due to inconsistent interfaces
4. **Interface Segregation Principle**: Utilities forced to import features they don't need
5. **Dependency Inversion Principle**: High-level modules depend on low-level utility implementations

## Solution Architecture (Revised - Proportionate to Problem)

### Simple Bug Fix + Minor Consolidation

Based on the validated analysis showing 507 lines of duplication (86% from one duplicate function), a proportionate solution:

**Phase 1: Critical Bug Fix (1 hour)**
- Remove duplicate function definition in `shell_utils.py`
- Fix the immediate Codacy-detected issue

**Phase 2: Minor Consolidation (1-2 days)**
- Consolidate ~70 lines of actual file operation overlap
- Keep existing utility modules in place
- Add simple base class for shared file operations

```
panther/core/utils/
├── file_utils.py (ENHANCED - Centralized file operations)
├── base_file_operations.py (NEW - Common file operation patterns)
└── existing modules remain unchanged

panther/core/command_processor/
└── shell_utils.py (FIXED - Remove duplicate function)

panther/plugins/environments/
├── environment_utils.py (MINOR - Use centralized file ops)
└── network_environment/utils.py (MINOR - Use centralized file ops)
```

### Design Principles Applied

1. **Immediate Fix**: Address the critical duplicate function bug
2. **Minimal Disruption**: Keep existing utility modules and APIs
3. **Proportionate Solution**: Simple consolidation for ~70 lines of real overlap
4. **Avoid Over-Engineering**: No complex architecture for minor overlaps

## Implementation Plan (Simplified)

### Phase 1: Critical Bug Fix (1 hour)

**File**: `/panther/core/command_processor/shell_utils.py`

**REMOVE (Lines 295-732 - Duplicate function definition)**:
```bash
# Simply delete the duplicate function definition
# Keep the first definition at line 219, remove the second at line 295

Provides the foundational interface and contract for all utility implementations
following SOLID principles and DRY patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin


T = TypeVar('T')  # Generic type for utility operations


class UtilityOperation(ABC):
    """
    Abstract base for all utility operations.
    
    Follows the Command pattern for consistent operation execution
    and error handling across all utility types.
    """
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the utility operation."""
        pass
    
    @abstractmethod
    def validate_inputs(self, *args, **kwargs) -> bool:
        """Validate operation inputs."""
        pass
    
    @abstractmethod
    def get_operation_name(self) -> str:
        """Get descriptive name for the operation."""
        pass


class UtilityResult:
    """
    Standardized result container for utility operations.
    
    Provides consistent result handling and error reporting
    across all utility functions.
    """
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
    
    @classmethod
    def success_result(cls, data: Any = None, metadata: Optional[Dict[str, Any]] = None):
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error_result(cls, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Create an error result."""
        return cls(success=False, error=error, metadata=metadata)
    
    def unwrap(self) -> Any:
        """Get the data if successful, raise exception if error."""
        if not self.success:
            raise UtilityOperationError(self.error or "Operation failed")
        return self.data


class UtilityOperationError(Exception):
    """Exception raised by utility operations."""
    pass


class AbstractUtility(ABC, LoggerMixin):
    """
    Abstract base class for all utility implementations.
    
    Provides common functionality for validation, error handling,
    and operation execution across all utility types.
    """
    
    def __init__(self, context: Optional['UtilityContext'] = None):
        """
        Initialize the utility.
        
        Args:
            context: Shared utility context for configuration and dependencies
        """
        super().__init__()
        self.context = context
        self._operation_cache: Dict[str, Any] = {}
    
    @abstractmethod
    def get_utility_name(self) -> str:
        """Get the name of this utility."""
        pass
    
    @abstractmethod
    def get_supported_operations(self) -> List[str]:
        """Get list of operations supported by this utility."""
        pass
    
    def execute_operation(
        self,
        operation_name: str,
        *args,
        **kwargs
    ) -> UtilityResult:
        """
        Execute a utility operation with standardized error handling.
        
        Args:
            operation_name: Name of the operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            UtilityResult with operation outcome
        """
        try:
            # Validate operation exists
            if operation_name not in self.get_supported_operations():
                return UtilityResult.error_result(
                    f"Unsupported operation: {operation_name}"
                )
            
            # Get operation method
            operation_method = getattr(self, f"_execute_{operation_name}")
            
            # Execute with logging
            self.logger.debug(
                f"Executing {self.get_utility_name()}.{operation_name}"
            )
            
            result = operation_method(*args, **kwargs)
            
            # Wrap result if not already wrapped
            if not isinstance(result, UtilityResult):
                result = UtilityResult.success_result(result)
            
            self.logger.debug(
                f"Operation {operation_name} completed successfully"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Operation {operation_name} failed: {str(e)}"
            self.logger.error(error_msg)
            return UtilityResult.error_result(error_msg)
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached operation result."""
        return self._operation_cache.get(cache_key)
    
    def cache_result(self, cache_key: str, result: Any) -> None:
        """Cache operation result."""
        self._operation_cache[cache_key] = result
    
    def clear_cache(self) -> None:
        """Clear operation cache."""
        self._operation_cache.clear()
```

**File**: `/panther/core/utils/base/utility_context.py`

**ADD (New File - 80 lines)**:
```python
"""
Utility Context

Shared context and configuration for utility operations.
"""

from typing import Any, Dict, Optional
from pathlib import Path


class UtilityContext:
    """
    Shared context for utility operations.
    
    Provides configuration, shared resources, and common
    parameters that utilities may need.
    """
    
    def __init__(
        self,
        base_directory: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        shared_resources: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize utility context.
        
        Args:
            base_directory: Base directory for file operations
            config: Configuration dictionary
            shared_resources: Shared resources between utilities
        """
        self.base_directory = base_directory or Path.cwd()
        self.config = config or {}
        self.shared_resources = shared_resources or {}
        
        # Operation tracking
        self.operation_count = 0
        self.error_count = 0
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def get_shared_resource(self, key: str) -> Optional[Any]:
        """Get shared resource."""
        return self.shared_resources.get(key)
    
    def set_shared_resource(self, key: str, resource: Any) -> None:
        """Set shared resource."""
        self.shared_resources[key] = resource
    
    def increment_operation_count(self) -> None:
        """Increment operation counter."""
        self.operation_count += 1
    
    def increment_error_count(self) -> None:
        """Increment error counter."""
        self.error_count += 1
    
    def get_statistics(self) -> Dict[str, int]:
        """Get operation statistics."""
        return {
            "total_operations": self.operation_count,
            "total_errors": self.error_count,
            "success_rate": (
                (self.operation_count - self.error_count) / max(self.operation_count, 1)
            ) * 100
        }
```

### Phase 2: Create Unified File Operations

**File**: `/panther/core/utils/operations/file_operations.py`

**ENHANCE (Current file_utils.py - Replace with 200 lines)**:
```python
"""
Unified File Operations

Consolidated file operations utility that replaces duplicated functionality
across file_utils.py, environment_utils.py, and network_environment/utils.py.
"""

import json
import yaml
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..base.abstract_utility import AbstractUtility, UtilityResult, UtilityOperationError


class FileOperations(AbstractUtility):
    """
    Unified file operations utility.
    
    Consolidates all file-related operations into a single, consistent interface
    following SOLID principles.
    """
    
    def get_utility_name(self) -> str:
        return "FileOperations"
    
    def get_supported_operations(self) -> List[str]:
        return [
            "read_yaml",
            "write_yaml", 
            "read_json",
            "write_json",
            "read_text",
            "write_text",
            "ensure_directory",
            "validate_file_path",
            "find_files_by_pattern",
            "parse_structured_content",
            "backup_file",
            "copy_file_structure"
        ]
    
    def _execute_read_yaml(self, file_path: Union[str, Path]) -> UtilityResult:
        """Read YAML file with unified error handling."""
        try:
            file_path = Path(file_path)
            
            if not self._validate_file_readable(file_path):
                return UtilityResult.error_result(
                    f"File not readable: {file_path}"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            return UtilityResult.success_result(
                data,
                metadata={"file_path": str(file_path), "format": "yaml"}
            )
            
        except yaml.YAMLError as e:
            return UtilityResult.error_result(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            return UtilityResult.error_result(f"Failed to read YAML file: {e}")
    
    def _execute_write_yaml(
        self,
        file_path: Union[str, Path],
        data: Any,
        create_directories: bool = True
    ) -> UtilityResult:
        """Write YAML file with directory creation."""
        try:
            file_path = Path(file_path)
            
            if create_directories:
                self._execute_ensure_directory(file_path.parent)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                
            return UtilityResult.success_result(
                str(file_path),
                metadata={"format": "yaml", "bytes_written": file_path.stat().st_size}
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to write YAML file: {e}")
    
    def _execute_read_json(self, file_path: Union[str, Path]) -> UtilityResult:
        """Read JSON file with unified error handling."""
        try:
            file_path = Path(file_path)
            
            if not self._validate_file_readable(file_path):
                return UtilityResult.error_result(
                    f"File not readable: {file_path}"
                )
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return UtilityResult.success_result(
                data,
                metadata={"file_path": str(file_path), "format": "json"}
            )
            
        except json.JSONDecodeError as e:
            return UtilityResult.error_result(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            return UtilityResult.error_result(f"Failed to read JSON file: {e}")
    
    def _execute_write_json(
        self,
        file_path: Union[str, Path],
        data: Any,
        indent: int = 2,
        create_directories: bool = True
    ) -> UtilityResult:
        """Write JSON file with directory creation."""
        try:
            file_path = Path(file_path)
            
            if create_directories:
                self._execute_ensure_directory(file_path.parent)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
                
            return UtilityResult.success_result(
                str(file_path),
                metadata={"format": "json", "bytes_written": file_path.stat().st_size}
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to write JSON file: {e}")
    
    def _execute_ensure_directory(self, directory: Union[str, Path]) -> UtilityResult:
        """Ensure directory exists with unified error handling."""
        try:
            directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)
            
            return UtilityResult.success_result(
                str(directory),
                metadata={"created": not directory.existed_before_mkdir()}
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to create directory: {e}")
    
    def _execute_parse_structured_content(
        self,
        content: str,
        format: str = "auto"
    ) -> UtilityResult:
        """
        Parse structured content (YAML, JSON, or text).
        
        Consolidates parsing logic from multiple utility modules.
        """
        try:
            if format == "auto":
                # Try to detect format
                content_stripped = content.strip()
                if content_stripped.startswith('{') or content_stripped.startswith('['):
                    format = "json"
                elif '---' in content or ':' in content:
                    format = "yaml"
                else:
                    format = "text"
            
            if format == "json":
                data = json.loads(content)
            elif format == "yaml":
                data = yaml.safe_load(content)
            else:
                data = content  # Return as text
            
            return UtilityResult.success_result(
                data,
                metadata={"detected_format": format, "content_length": len(content)}
            )
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return UtilityResult.error_result(f"Failed to parse {format} content: {e}")
        except Exception as e:
            return UtilityResult.error_result(f"Failed to parse content: {e}")
    
    def _validate_file_readable(self, file_path: Path) -> bool:
        """Validate that file exists and is readable."""
        return (
            file_path.exists() 
            and file_path.is_file() 
            and os.access(file_path, os.R_OK)
        )


# Backward compatibility aliases - REMOVE these in Phase 3
def read_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Backward compatibility wrapper for read_yaml."""
    file_ops = FileOperations()
    result = file_ops.execute_operation("read_yaml", file_path)
    return result.unwrap()


def write_yaml_file(file_path: Union[str, Path], data: Any) -> None:
    """Backward compatibility wrapper for write_yaml."""
    file_ops = FileOperations()
    result = file_ops.execute_operation("write_yaml", file_path, data)
    result.unwrap()


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """Backward compatibility wrapper for ensure_directory."""
    file_ops = FileOperations()
    result = file_ops.execute_operation("ensure_directory", directory)
    return Path(result.unwrap())
```

### Phase 3: Create Unified Command Processing

**File**: `/panther/core/utils/processors/command_processor.py`

**ENHANCE (Consolidate command utilities - 180 lines)**:
```python
"""
Unified Command Processing

Consolidates command generation and processing functionality from
command_utils.py, shell_utils.py, and command_generation_utils.py.
"""

from typing import Any, Dict, List, Optional, Union
from ..base.abstract_utility import AbstractUtility, UtilityResult
from ..operations.shell_operations import ShellOperations


class CommandProcessor(AbstractUtility):
    """
    Unified command processing utility.
    
    Consolidates command structure generation, validation, and processing
    into a single, consistent interface.
    """
    
    def __init__(self, context=None):
        super().__init__(context)
        self.shell_ops = ShellOperations(context)
    
    def get_utility_name(self) -> str:
        return "CommandProcessor"
    
    def get_supported_operations(self) -> List[str]:
        return [
            "generate_basic_structure",
            "create_shell_command",
            "merge_command_structures",
            "validate_command_structure",
            "build_execution_command",
            "create_wrapper_command",
            "normalize_command_phases"
        ]
    
    def _execute_generate_basic_structure(self) -> UtilityResult:
        """Generate basic command structure (consolidated from command_utils.py)."""
        structure = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "run_cmds": [],
            "post_run_cmds": []
        }
        
        return UtilityResult.success_result(
            structure,
            metadata={"phases": list(structure.keys())}
        )
    
    def _execute_merge_command_structures(
        self,
        *structures: Dict[str, List[str]]
    ) -> UtilityResult:
        """Merge multiple command structures (from command_utils.py)."""
        try:
            merged = {}
            
            # Get all unique phase names
            all_phases = set()
            for structure in structures:
                all_phases.update(structure.keys())
            
            # Merge each phase
            for phase in all_phases:
                merged[phase] = []
                for structure in structures:
                    if phase in structure:
                        merged[phase].extend(structure[phase])
            
            return UtilityResult.success_result(
                merged,
                metadata={
                    "merged_structures": len(structures),
                    "total_phases": len(merged)
                }
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to merge command structures: {e}")
    
    def _execute_validate_command_structure(
        self,
        structure: Dict[str, Any]
    ) -> UtilityResult:
        """Validate command structure format."""
        try:
            required_phases = {
                "pre_compile_cmds", "compile_cmds", "post_compile_cmds",
                "pre_run_cmds", "run_cmds", "post_run_cmds"
            }
            
            errors = []
            
            # Check required phases exist
            missing_phases = required_phases - set(structure.keys())
            if missing_phases:
                errors.append(f"Missing phases: {missing_phases}")
            
            # Check phase contents are lists
            for phase, commands in structure.items():
                if not isinstance(commands, list):
                    errors.append(f"Phase '{phase}' must be a list")
            
            is_valid = len(errors) == 0
            
            return UtilityResult.success_result(
                is_valid,
                metadata={"errors": errors, "phase_count": len(structure)}
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to validate command structure: {e}")
    
    def _execute_create_wrapper_command(
        self,
        base_command: str,
        wrapper_type: str,
        wrapper_options: Optional[Dict[str, Any]] = None
    ) -> UtilityResult:
        """
        Create wrapper command for execution environments.
        
        Consolidates wrapper creation logic from command_generation_utils.py.
        """
        try:
            wrapper_options = wrapper_options or {}
            
            if wrapper_type == "strace":
                output_file = wrapper_options.get("output_file", "strace_output.txt")
                wrapper_cmd = f"strace -o {output_file} {base_command}"
                
            elif wrapper_type == "gperf_cpu":
                profile_file = wrapper_options.get("profile_file", "cpu_profile.prof")
                wrapper_cmd = f"CPUPROFILE={profile_file} {base_command}"
                
            elif wrapper_type == "gperf_heap":
                profile_file = wrapper_options.get("profile_file", "heap_profile.prof")
                wrapper_cmd = f"HEAPPROFILE={profile_file} {base_command}"
                
            elif wrapper_type == "valgrind_memcheck":
                log_file = wrapper_options.get("log_file", "memcheck.log")
                wrapper_cmd = f"valgrind --tool=memcheck --log-file={log_file} {base_command}"
                
            else:
                return UtilityResult.error_result(f"Unsupported wrapper type: {wrapper_type}")
            
            # Use shell operations for proper escaping
            escaped_result = self.shell_ops.execute_operation("escape_command", wrapper_cmd)
            if not escaped_result.success:
                return escaped_result
            
            return UtilityResult.success_result(
                escaped_result.data,
                metadata={
                    "wrapper_type": wrapper_type,
                    "base_command": base_command,
                    "options": wrapper_options
                }
            )
            
        except Exception as e:
            return UtilityResult.error_result(f"Failed to create wrapper command: {e}")


# Backward compatibility functions - REMOVE these in Phase 3
def generate_basic_service_commands() -> Dict[str, List]:
    """Backward compatibility wrapper."""
    processor = CommandProcessor()
    result = processor.execute_operation("generate_basic_structure")
    return result.unwrap()


def merge_command_structures(*structures) -> Dict[str, List]:
    """Backward compatibility wrapper."""
    processor = CommandProcessor()
    result = processor.execute_operation("merge_command_structures", *structures)
    return result.unwrap()
```

### Phase 4: Create Utility Manager and Registry

**File**: `/panther/core/utils/utility_manager.py`

**ADD (New File - 150 lines)**:
```python
"""
Utility Manager

Central coordination and management of all utility classes.
Provides unified access to utility operations following SOLID principles.
"""

from typing import Any, Dict, List, Optional, Type
from .base.abstract_utility import AbstractUtility, UtilityContext, UtilityResult
from .operations.file_operations import FileOperations
from .processors.command_processor import CommandProcessor
from .operations.shell_operations import ShellOperations


class UtilityManager:
    """
    Central manager for all utility operations.
    
    Provides unified access to utility functionality while maintaining
    separation of concerns and following SOLID principles.
    """
    
    def __init__(self, context: Optional[UtilityContext] = None):
        """
        Initialize utility manager.
        
        Args:
            context: Shared context for all utilities
        """
        self.context = context or UtilityContext()
        self._utilities: Dict[str, AbstractUtility] = {}
        self._initialize_default_utilities()
    
    def _initialize_default_utilities(self) -> None:
        """Initialize default set of utilities."""
        self.register_utility(FileOperations(self.context))
        self.register_utility(CommandProcessor(self.context))
        self.register_utility(ShellOperations(self.context))
    
    def register_utility(self, utility: AbstractUtility) -> None:
        """
        Register a utility for use.
        
        Args:
            utility: Utility instance to register
        """
        utility_name = utility.get_utility_name()
        self._utilities[utility_name] = utility
    
    def get_utility(self, utility_name: str) -> Optional[AbstractUtility]:
        """
        Get a registered utility.
        
        Args:
            utility_name: Name of the utility to retrieve
            
        Returns:
            Utility instance or None if not found
        """
        return self._utilities.get(utility_name)
    
    def execute_operation(
        self,
        utility_name: str,
        operation_name: str,
        *args,
        **kwargs
    ) -> UtilityResult:
        """
        Execute a utility operation.
        
        Args:
            utility_name: Name of the utility
            operation_name: Name of the operation
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            UtilityResult with operation outcome
        """
        utility = self.get_utility(utility_name)
        if not utility:
            return UtilityResult.error_result(
                f"Utility not found: {utility_name}"
            )
        
        return utility.execute_operation(operation_name, *args, **kwargs)
    
    def get_available_utilities(self) -> List[str]:
        """Get list of available utility names."""
        return list(self._utilities.keys())
    
    def get_utility_operations(self, utility_name: str) -> List[str]:
        """Get list of operations for a utility."""
        utility = self.get_utility(utility_name)
        if not utility:
            return []
        return utility.get_supported_operations()
    
    def clear_all_caches(self) -> None:
        """Clear caches for all utilities."""
        for utility in self._utilities.values():
            utility.clear_cache()
    
    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get manager and utility statistics."""
        stats = {
            "registered_utilities": len(self._utilities),
            "context_stats": self.context.get_statistics(),
            "utility_details": {}
        }
        
        for name, utility in self._utilities.items():
            stats["utility_details"][name] = {
                "supported_operations": len(utility.get_supported_operations()),
                "cache_size": len(utility._operation_cache)
            }
        
        return stats


# Global utility manager instance
_global_utility_manager: Optional[UtilityManager] = None


def get_utility_manager() -> UtilityManager:
    """Get the global utility manager instance."""
    global _global_utility_manager
    if _global_utility_manager is None:
        _global_utility_manager = UtilityManager()
    return _global_utility_manager


def reset_utility_manager() -> None:
    """Reset the global utility manager (for testing)."""
    global _global_utility_manager
    _global_utility_manager = None
```

### Phase 5: Update Existing Utility Modules

**File**: `/panther/plugins/environments/environment_utils.py`

**REFACTOR (Remove duplicated file operations - 120 lines)**:
```python
"""
Environment Utilities

Environment-specific utilities with duplicated file operations removed.
Now focuses solely on plugin lifecycle and environment management.
"""

from typing import Any, Dict, Optional
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.utils.utility_manager import get_utility_manager


class EnvironmentPluginMixin(LoggerMixin):
    """
    Base mixin for environment plugins.
    
    Now focuses on plugin lifecycle without duplicate file operations.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.utility_manager = get_utility_manager()
    
    def setup_output_directories(
        self,
        base_output_dir: Path,
        test_name: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Setup standard output directory structure.
        
        Uses unified file operations instead of duplicated directory creation.
        """
        directories = {
            "base": base_output_dir,
            "logs": base_output_dir / "logs",
            "data": base_output_dir / "data",
            "temp": base_output_dir / "temp"
        }
        
        if test_name:
            directories["test"] = base_output_dir / test_name
        
        # Use unified file operations for directory creation
        for dir_name, dir_path in directories.items():
            result = self.utility_manager.execute_operation(
                "FileOperations",
                "ensure_directory",
                dir_path
            )
            if not result.success:
                self.logger.error(f"Failed to create {dir_name} directory: {result.error}")
                raise EnvironmentSetupError(f"Directory creation failed: {result.error}")
        
        self.logger.info(f"Created {len(directories)} output directories")
        return directories
    
    def standardize_environment_initialization(
        self,
        env_config_to_test: Any,
        output_dir: str,
        env_type: str,
        env_sub_type: str
    ) -> Dict[str, Any]:
        """
        Standardize environment initialization across all plugins.
        
        Removes duplicate initialization logic.
        """
        initialization_data = {
            "config": env_config_to_test,
            "output_dir": Path(output_dir),
            "env_type": env_type,
            "env_sub_type": env_sub_type,
            "initialized_at": self._get_current_timestamp()
        }
        
        # Setup directories using unified operations
        directories = self.setup_output_directories(
            initialization_data["output_dir"]
        )
        initialization_data["directories"] = directories
        
        self.logger.info(
            f"Standardized initialization for {env_type}.{env_sub_type}"
        )
        
        return initialization_data


class EnvironmentSetupError(Exception):
    """Exception raised during environment setup."""
    pass


# REMOVED: ensure_directory_exists() - now in FileOperations
# REMOVED: validate_file_path() - now in FileOperations  
# REMOVED: read_yaml_config() - now in FileOperations
# REMOVED: write_environment_config() - now in FileOperations
```

**File**: `/panther/plugins/environments/network_environment/utils.py`

**REFACTOR (Remove duplicated utilities - 100 lines)**:
```python
"""
Network Environment Utilities

Network-specific utilities with duplicated functionality removed.
Now focuses solely on network environment operations.
"""

import socket
import subprocess
from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.utils.utility_manager import get_utility_manager


class NetworkEnvironmentOperations(LoggerMixin):
    """
    Network environment specific operations.
    
    Focuses on network-specific functionality with shared operations
    delegated to unified utilities.
    """
    
    def __init__(self):
        super().__init__()
        self.utility_manager = get_utility_manager()
    
    def wait_for_service_ready(
        self,
        host: str = "localhost",
        port: int = 4443,
        timeout: int = 30
    ) -> bool:
        """
        Wait for service to be ready by checking port availability.
        
        This is network-specific and not duplicated elsewhere.
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection((host, port), timeout=1):
                    self.logger.info(f"Service ready on {host}:{port}")
                    return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(0.5)
        
        self.logger.warning(f"Service not ready on {host}:{port} after {timeout}s")
        return False
    
    def validate_docker_installation(self) -> bool:
        """
        Validate Docker is installed and available.
        
        Network environment specific Docker validation.
        """
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Docker available: {result.stdout.strip()}")
                return True
            else:
                self.logger.error("Docker not available")
                return False
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("Docker validation failed")
            return False
    
    def cleanup_docker_resources(self, project_name: str) -> bool:
        """
        Cleanup Docker resources for a project.
        
        Network environment specific Docker cleanup.
        """
        try:
            # Stop containers
            subprocess.run([
                "docker-compose", "-p", project_name, "down", "-v"
            ], capture_output=True, timeout=30)
            
            # Remove images
            subprocess.run([
                "docker", "system", "prune", "-f"
            ], capture_output=True, timeout=30)
            
            self.logger.info(f"Cleaned up Docker resources for {project_name}")
            return True
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            self.logger.error(f"Docker cleanup failed: {e}")
            return False
    
    def generate_compose_file(
        self,
        template_path: str,
        output_path: str,
        template_variables: Dict[str, Any]
    ) -> bool:
        """
        Generate Docker Compose file from template.
        
        Uses unified file operations for file handling.
        """
        try:
            # Use unified file operations for directory creation
            result = self.utility_manager.execute_operation(
                "FileOperations",
                "ensure_directory",
                Path(output_path).parent
            )
            if not result.success:
                self.logger.error(f"Failed to create output directory: {result.error}")
                return False
            
            # Generate compose file using template processor
            # (Template processing would be implemented in template_processor.py)
            from jinja2 import Template
            
            # Read template using unified operations
            template_result = self.utility_manager.execute_operation(
                "FileOperations",
                "read_text",
                template_path
            )
            if not template_result.success:
                self.logger.error(f"Failed to read template: {template_result.error}")
                return False
            
            template = Template(template_result.data)
            composed_content = template.render(**template_variables)
            
            # Write output using unified operations
            write_result = self.utility_manager.execute_operation(
                "FileOperations",
                "write_text",
                output_path,
                composed_content
            )
            
            if write_result.success:
                self.logger.info(f"Generated compose file: {output_path}")
                return True
            else:
                self.logger.error(f"Failed to write compose file: {write_result.error}")
                return False
                
        except Exception as e:
            self.logger.error(f"Compose file generation failed: {e}")
            return False


# REMOVED: ensure_directory_exists() - now in FileOperations
# REMOVED: parse_service_output() - now in FileOperations.parse_structured_content()
# REMOVED: collect_service_logs() - file operations now in FileOperations
# REMOVED: validate_file_path() - now in FileOperations
```

### Phase 6: Update Import Dependencies

**File**: `/panther/core/utils/__init__.py`

**ENHANCE (Update imports - 40 lines)**:
```python
"""
Unified Utilities Package

Provides access to all utility functionality through a clean, consistent interface.
"""

# Import unified utility manager
from .utility_manager import get_utility_manager, UtilityManager

# Import base classes for extension
from .base.abstract_utility import AbstractUtility, UtilityResult, UtilityContext

# Import specific utility classes
from .operations.file_operations import FileOperations
from .processors.command_processor import CommandProcessor
from .operations.shell_operations import ShellOperations

# Backward compatibility imports (DEPRECATED - remove in Phase 3)
from .operations.file_operations import (
    read_yaml_file,
    write_yaml_file, 
    ensure_directory_exists
)
from .processors.command_processor import (
    generate_basic_service_commands,
    merge_command_structures
)

# Convenience functions for common operations
def read_yaml(file_path):
    """Convenience function for reading YAML files."""
    manager = get_utility_manager()
    result = manager.execute_operation("FileOperations", "read_yaml", file_path)
    return result.unwrap()


def write_yaml(file_path, data):
    """Convenience function for writing YAML files.""" 
    manager = get_utility_manager()
    result = manager.execute_operation("FileOperations", "write_yaml", file_path, data)
    return result.unwrap()


def ensure_directory(directory):
    """Convenience function for directory creation."""
    manager = get_utility_manager()
    result = manager.execute_operation("FileOperations", "ensure_directory", directory)
    return result.unwrap()


def generate_command_structure():
    """Convenience function for command structure generation."""
    manager = get_utility_manager()
    result = manager.execute_operation("CommandProcessor", "generate_basic_structure")
    return result.unwrap()


__all__ = [
    # Core classes
    "UtilityManager",
    "get_utility_manager",
    "AbstractUtility", 
    "UtilityResult",
    "UtilityContext",
    
    # Utility implementations
    "FileOperations",
    "CommandProcessor",
    "ShellOperations",
    
    # Convenience functions
    "read_yaml",
    "write_yaml",
    "ensure_directory", 
    "generate_command_structure",
    
    # Deprecated (remove in Phase 3)
    "read_yaml_file",
    "write_yaml_file",
    "ensure_directory_exists",
    "generate_basic_service_commands",
    "merge_command_structures"
]
```

## Migration Strategy

### Phase 1: Foundation (Days 1-2)
1. **Create base utility system** - AbstractUtility, UtilityContext, UtilityManager
2. **Implement FileOperations** - Consolidate file operation duplicates
3. **Add backward compatibility wrappers** - Ensure existing code continues working

### Phase 2: Command Processing (Days 3-4)
1. **Create CommandProcessor** - Consolidate command generation logic
2. **Create ShellOperations** - Keep shell-specific operations separate  
3. **Update command generation utilities** - Remove duplicates, delegate to unified classes

### Phase 3: Environment Utilities (Days 5-6)
1. **Refactor environment_utils.py** - Remove file operation duplicates
2. **Refactor network_environment/utils.py** - Focus on network-specific operations
3. **Update execution environment utilities** - Use unified command processing

### Phase 4: Integration and Testing (Day 7)
1. **Update import dependencies** - Point to unified utilities
2. **Add comprehensive tests** - Ensure functionality preserved
3. **Remove backward compatibility wrappers** - Clean up deprecated functions

## Expected Benefits (Revised)

### Immediate Benefits
- **507 lines of duplicate code eliminated** (primarily one duplicate function)
- **Critical bug fix** in shell_utils.py resolving Codacy issue
- **Minimal disruption** to existing utility APIs
- **Simple consolidation** of minor file operation overlaps

### Long-term Benefits  
- **Cleaner codebase** with duplicate function removed
- **Slightly better maintainability** for file operations
- **Preserved existing functionality** with minimal changes
- **Proportionate solution** avoiding over-engineering

### Quality Improvements
- **Immediate Codacy compliance** with duplicate function removal
- **Minor reduction** in file operation redundancy
- **Maintained API compatibility** with existing code
- **Simple implementation** requiring minimal testing

## Backward Compatibility

### Compatibility Preservation
- **Phase 1-2**: All existing imports continue working through wrappers
- **Phase 3**: Gradual migration to new interfaces with deprecation warnings
- **Phase 4**: Remove deprecated functions after full migration

### Migration Path
```python
# Old code (Phase 1-2)
from panther.core.utils.file_utils import read_yaml_file
data = read_yaml_file("config.yaml")

# Transitional code (Phase 3)
from panther.core.utils import read_yaml  # New convenience function
data = read_yaml("config.yaml")

# Final code (Phase 4)
from panther.core.utils import get_utility_manager
manager = get_utility_manager()
result = manager.execute_operation("FileOperations", "read_yaml", "config.yaml")
data = result.unwrap()
```

## Testing Strategy

### Unit Tests
- **Test each utility class** independently with mock contexts
- **Test UtilityManager** coordination and registry functionality
- **Test backward compatibility** wrappers maintain existing behavior

### Integration Tests  
- **Test utility interactions** between different utility classes
- **Test error handling** across utility boundaries
- **Test performance** of unified vs. duplicated implementations

### Migration Tests
- **Test import changes** don't break existing functionality
- **Test gradual migration** from old to new interfaces
- **Test deprecation warnings** guide proper migration

---

*Implementation Priority: Critical - addresses 507 lines of duplicate code (mainly one bug)*  
*Estimated Effort: 1 hour (critical fix) + 1-2 days (minor consolidation)*  
*Risk Level: Low - simple bug fix and minor changes*  
*Expected Impact: Immediate Codacy compliance + minor maintenance improvement*