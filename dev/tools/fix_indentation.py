#!/usr/bin/env python3
"""
Script to correct indentation issues in Python files that have been modified
by the fix_logging_fstrings.py script.

This script restores proper indentation to logging statements.
"""

import os
import re
import sys
import argparse
from typing import List, Tuple


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Fix indentation in logging statements'
    )
    parser.add_argument(
        '-d', '--directory',
        default='panther',
        help='Directory to recursively process (default: panther)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print files that would be modified, without making changes'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print detailed information about fixes'
    )
    return parser.parse_args()


def find_unindented_logger_calls(content: str) -> List[Tuple[int, re.Match]]:
    """Find logging statements that are not properly indented."""
    lines = content.splitlines()
    result = []
    
    # Find logger statements at the beginning of lines (no indentation)
    pattern = r'^(logger|_logger)\.(?:debug|info|warning|warn|error|critical|exception|log)'
    
    for i, line in enumerate(lines):
        match = re.match(pattern, line)
        if match and i > 0:
            # Check if previous line has indentation
            prev_line = lines[i-1]
            if re.match(r'^\s+', prev_line):
                # Calculate the indentation from the previous line
                indentation = len(prev_line) - len(prev_line.lstrip())
                result.append((i, indentation))
    
    return result


def fix_indentation(file_path: str, dry_run: bool, verbose: bool) -> bool:
    """Fix indentation in a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.splitlines()
        modified = False
        
        # Detect patterns like logger.info at the start of lines
        for i in range(1, len(lines)):
            line = lines[i]
            if re.match(r'^(logger|_logger)\.(debug|info|warning|warn|error|critical|exception|log)', line):
                # Look at the surrounding lines to determine correct indentation
                prev_line = lines[i-1]
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                next_indent = 0
                
                if i < len(lines) - 1:
                    next_line = lines[i+1]
                    next_indent = len(next_line) - len(next_line.lstrip())
                
                # Determine correct indentation - use prev_indent if it has indentation
                indent = prev_indent if prev_indent > 0 else next_indent
                
                if indent > 0:
                    if verbose:
                        print(f"In {file_path} line {i+1}:")
                        print(f"  - {line}")
                        print(f"  + {' ' * indent}{line}")
                    
                    lines[i] = ' ' * indent + line
                    modified = True
        
        if modified and not dry_run:
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            
            if verbose:
                print(f"Fixed indentation in {file_path}")
        
        return modified
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function."""
    args = parse_args()
    
    modified_files = []
    
    for root, _, files in os.walk(args.directory):
        for file in files:
            if not file.endswith('.py'):
                continue
            
            file_path = os.path.join(root, file)
            
            if fix_indentation(file_path, args.dry_run, args.verbose):
                modified_files.append(file_path)
    
    print(f"\nSummary:")
    print(f"  - Found and {'would fix' if args.dry_run else 'fixed'}: {len(modified_files)} files")
    
    if args.verbose and modified_files:
        print("\nModified files:")
        for f in sorted(modified_files):
            print(f"  - {f}")
    
    if args.dry_run and modified_files:
        print("\nThis was a dry run. No files were actually modified.")
        print("Run without --dry-run to apply the changes.")


if __name__ == "__main__":
    main()
