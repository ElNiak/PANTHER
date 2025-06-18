"""
Refactored shell_utils.py - Breaking down complexity from 67 to <10 per function
This example demonstrates how to refactor the combine_shell_constructs function.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ShellConstructDetector(ABC):
    """Base class for detecting shell constructs."""
    
    @abstractmethod
    def matches(self, line: str) -> bool:
        """Check if line matches this construct type."""
        pass
    
    @abstractmethod
    def get_construct_type(self) -> str:
        """Return the construct type name."""
        pass


class FunctionConstructDetector(ShellConstructDetector):
    """Detects shell function definitions."""
    
    def matches(self, line: str) -> bool:
        line_lower = line.lower().strip()
        
        # Pattern 1: function name() { ... }
        if "function " in line_lower:
            return True
            
        # Pattern 2: name() { ... }
        if self._matches_function_pattern(line_lower):
            return True
            
        return False
    
    def _matches_function_pattern(self, line: str) -> bool:
        """Check for function pattern: name() { """
        patterns = ["() {", "(){", "()\n{", "() \n{"]
        has_pattern = any(pattern in line for pattern in patterns)
        
        ends_with_brace = line.rstrip().endswith("{")
        has_parens = "(" in line and ")" in line
        
        return has_pattern or (ends_with_brace and has_parens)
    
    def get_construct_type(self) -> str:
        return "function"


class IfConstructDetector(ShellConstructDetector):
    """Detects if/then constructs."""
    
    def matches(self, line: str) -> bool:
        line_lower = line.lower().strip()
        return line_lower.startswith("if ") and "then" in line_lower
    
    def get_construct_type(self) -> str:
        return "if"


class LoopConstructDetector(ShellConstructDetector):
    """Detects loop constructs (for/while)."""
    
    def __init__(self, loop_type: str):
        self.loop_type = loop_type
    
    def matches(self, line: str) -> bool:
        line_lower = line.lower().strip()
        return line_lower.startswith(f"{self.loop_type} ") and "do" in line_lower
    
    def get_construct_type(self) -> str:
        return self.loop_type


class ShellConstructManager:
    """Manages shell construct detection and processing."""
    
    def __init__(self):
        self.detectors: List[ShellConstructDetector] = [
            FunctionConstructDetector(),
            IfConstructDetector(),
            LoopConstructDetector("for"),
            LoopConstructDetector("while"),
        ]
        self.active_constructs: List[str] = []
        self.brace_count = 0
        
    def detect_construct(self, line: str) -> Optional[str]:
        """Detect if line starts a new construct."""
        if not line or not line.strip():
            return None
            
        for detector in self.detectors:
            if detector.matches(line):
                construct_type = detector.get_construct_type()
                logger.debug(f"Detected {construct_type} construct: {line.strip()[:40]}")
                return construct_type
                
        return None
    
    def update_brace_count(self, line: str) -> None:
        """Update brace count for tracking construct boundaries."""
        self.brace_count += line.count("{") - line.count("}")
        
    def is_construct_complete(self) -> bool:
        """Check if current construct is complete."""
        return self.brace_count <= 0 and self.active_constructs


class ShellCommandProcessor:
    """Processes shell commands with reduced complexity."""
    
    def __init__(self):
        self.construct_manager = ShellConstructManager()
        self.command_builder = CommandBuilder()
        
    def combine_shell_constructs(self, cmd_parts: List[str]) -> List[str]:
        """
        Combine shell command parts intelligently.
        Reduced from complexity 67 to <10 by delegating to specialized classes.
        """
        if not cmd_parts:
            return []
            
        combined_commands = []
        current_command = []
        
        for part in cmd_parts:
            processed_part = self._process_command_part(part)
            
            if self._should_start_new_command(processed_part):
                if current_command:
                    combined_commands.append(self._finalize_command(current_command))
                current_command = [processed_part]
            else:
                current_command.append(processed_part)
                
        # Add final command
        if current_command:
            combined_commands.append(self._finalize_command(current_command))
            
        return combined_commands
    
    def _process_command_part(self, part: str) -> str:
        """Process individual command part."""
        # Delegate construct detection
        construct = self.construct_manager.detect_construct(part)
        if construct:
            self.construct_manager.active_constructs.append(construct)
            
        # Update brace tracking
        self.construct_manager.update_brace_count(part)
        
        return part.strip()
    
    def _should_start_new_command(self, part: str) -> bool:
        """Determine if part should start a new command."""
        # Simple logic - delegate complex decisions
        return self.command_builder.is_command_separator(part)
    
    def _finalize_command(self, parts: List[str]) -> str:
        """Finalize and format command."""
        return self.command_builder.build_command(parts)


class CommandBuilder:
    """Builds shell commands from parts."""
    
    COMMAND_SEPARATORS = ["&&", "||", ";", "|"]
    
    def is_command_separator(self, part: str) -> bool:
        """Check if part is a command separator."""
        return any(sep in part for sep in self.COMMAND_SEPARATORS)
    
    def build_command(self, parts: List[str]) -> str:
        """Build command from parts."""
        return " ".join(parts)


# Usage example
def refactored_combine_example():
    """Example of using the refactored code."""
    processor = ShellCommandProcessor()
    
    cmd_parts = [
        "if [ -f test.txt ]; then",
        "echo 'File exists'",
        "fi",
        "&&",
        "function cleanup() {",
        "rm -f temp/*",
        "}"
    ]
    
    result = processor.combine_shell_constructs(cmd_parts)
    print("Combined commands:", result)


# Metrics comparison
"""
Original function:
- Cyclomatic Complexity: 67
- Lines: 436
- Nested depth: 8+ levels
- Responsibilities: 5+ (detection, parsing, building, tracking, formatting)

Refactored version:
- Max complexity per function: 8
- Total lines: ~200 (54% reduction)
- Max nested depth: 3
- Clear single responsibilities per class
- Testable components
- Extensible design (easy to add new construct types)
"""