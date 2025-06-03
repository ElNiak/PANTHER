#!/usr/bin/env python3
"""
Script to verify the command.py logic independently.
"""

import re
import sys
import os
from pathlib import Path

# Add the PANTHER directory to the path so we can import from it
sys.path.append('/Users/elniak/Documents/Project/PANTHER')
from panther.utils.command import ShellCommand, SHELL_BUILTINS, SHELL_CONTROL_STRUCTURES

# Test cases
test_commands = [
    # Variable assignments
    "TARGET_IP=127.0.0.1",
    "export PS4=\"+ [${BASH_SOURCE:-sh}:${LINENO}] \"",
    "PATH=$PATH:/usr/local/bin",
    
    # Shell built-ins
    "set -x",
    "cd /some/directory",
    "export LANG=C",
    
    # Control structures
    "while [ ! -f /app/sync_logs/ivy_ready.log ]; do sleep 1; done",
    "if [ -f /etc/hosts ]; then cat /etc/hosts; fi",
    "for i in {1..5}; do echo $i; done",
    
    # Complex nested quotes
    "export PS4=\"+ [${BASH_SOURCE:-sh}:${LINENO}] \"",
    "echo \"The value is '$HOME'\"",
]

def test_command_detection():
    """Test the command detection logic in ShellCommand."""
    results = []
    
    print("Running command detection tests...")
    print(f"Shell builtins defined: {len(SHELL_BUILTINS)}")
    print(f"Control structures defined: {len(SHELL_CONTROL_STRUCTURES)}")
    print(f"Testing {len(test_commands)} commands:\n")
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"Testing command {i}: {cmd}")
        try:
            cmd_obj = ShellCommand.from_string(cmd)
            print(f"  Created ShellCommand object successfully")
            
            # Check specific attributes
            print(f"  is_variable_assignment = {cmd_obj.is_variable_assignment}")
            print(f"  is_shell_builtin = {cmd_obj.is_shell_builtin}")
            print(f"  is_control_structure = {cmd_obj.is_control_structure}")
            print(f"  has_nested_quotes = {cmd_obj.has_nested_quotes}")
            
            results.append({
                'command': cmd,
                'is_variable_assignment': cmd_obj.is_variable_assignment,
                'is_shell_builtin': cmd_obj.is_shell_builtin,
                'is_control_structure': cmd_obj.is_control_structure,
                'has_nested_quotes': cmd_obj.has_nested_quotes,
                'is_multiline': cmd_obj.is_multiline,
                'is_function_definition': cmd_obj.is_function_definition,
                'is_function_call': cmd_obj.is_function_call,
            })
        except Exception as e:
            print(f"  ERROR creating ShellCommand: {e}")
            results.append({
                'command': cmd,
                'error': str(e)
            })
    
    # Print the results
    print("COMMAND DETECTION TEST RESULTS\n")
    for idx, result in enumerate(results, 1):
        print(f"{idx}. Command: {result['command']}")
        print(f"   Variable Assignment: {result['is_variable_assignment']}")
        print(f"   Shell Builtin: {result['is_shell_builtin']}")
        print(f"   Control Structure: {result['is_control_structure']}")
        print(f"   Nested Quotes: {result['has_nested_quotes']}")
        print(f"   Multiline: {result['is_multiline']}")
        print(f"   Function Definition: {result['is_function_definition']}")
        print(f"   Function Call: {result['is_function_call']}")
        print()

if __name__ == "__main__":
    test_command_detection()
