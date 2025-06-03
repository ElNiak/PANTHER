#!/usr/bin/env python3
"""
Script to fix indentation issues with logging statements after f-string conversion.

This script specifically focuses on properly preserving indentation of logging statements
that may have been broken during previous f-string conversion.
"""

import os
import re
import sys
import argparse
from typing import List, Tuple

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Fix indentation issues in logging statements'
    )
    parser.add_argument(
        '-d', '--directory',
        default='panther',
        help='Directory to recursively process (default: panther)'
    )
    parser.add_argument(
        '--exclude',
        default='panther/plugins/services/testers/panther_ivy/**,**/.venv/**,.venv/**,**/__pycache__/**,**/build/**,**/dist/**',
        help='''Comma-separated list of patterns to exclude:
                - Direct pattern: "dir/subdir" matches if path contains this substring
                - Directory pattern: "dirname/" matches specific directories
                - Glob pattern: "*.pyc" or "**/__pycache__/**" for wildcards'''
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


def should_exclude(path: str, exclude_patterns: List[str]) -> bool:
    """
    Check if a path matches any exclude pattern.
    
    Supports:
    - Direct substring matching (e.g., 'foo' will match '/path/to/foo/bar')
    - Path-aware matching (e.g., 'foo/' only matches directory named foo)
    - Glob patterns with * and ** wildcards (e.g., '*.pyc', '**/__pycache__/**')
    """
    import fnmatch
    from pathlib import Path
    
    # Normalize path for consistent matching
    path = os.path.normpath(path)
    posix_path = path.replace("\\", "/")
    path_obj = Path(path)
    
    # Always exclude these common patterns regardless of arguments
    if "/.venv/" in posix_path or "/__pycache__/" in posix_path:
        return True
        
    for pattern in exclude_patterns:
        # Special case for **/ patterns (match any directory depth)
        if "**" in pattern:
            # Convert to Path-compatible pattern
            if fnmatch.fnmatch(posix_path, pattern):
                return True
        
        # Handle glob patterns (with * wildcards)
        elif "*" in pattern:
            if fnmatch.fnmatch(path_obj.name, pattern):
                return True
            if fnmatch.fnmatch(posix_path, pattern):
                return True
        
        # Handle directory-specific patterns (ending with /)
        elif pattern.endswith('/'):
            dir_pattern = pattern[:-1]  # Remove trailing slash
            if dir_pattern in posix_path.split('/'):
                return True
        
        # Handle direct substring match
        elif pattern in posix_path:
            return True
            
    return False


def detect_indentation_issues(file_path: str) -> List[Tuple[int, str, str]]:
    """
    Detect indentation issues in logging statements.
    
    Returns list of tuples (line_number, original_line, fixed_line)
    """
    issues = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # First pass: determine block structure and expected indentation levels
    indent_stack = [(0, "global")]  # Stack of (indent_level, block_type) tuples
    expected_indents = {}  # Maps line number to expected indentation
    
    for i, line in enumerate(lines):
        line_str = line.rstrip()
        if not line_str:  # Skip empty lines
            continue
            
        current_indent = len(line) - len(line.lstrip())
        
        # Pop completed blocks
        while indent_stack and current_indent < indent_stack[-1][0]:
            indent_stack.pop()
        
        # Detect new blocks - lines ending with colon
        if line_str.rstrip().endswith(':'):
            # Calculate next indent level (current + 4)
            next_indent = current_indent + 4
            block_type = line_str.strip().split()[0]
            indent_stack.append((next_indent, block_type))
            
            # Mark next line's expected indent
            if i + 1 < len(lines):
                expected_indents[i + 1] = next_indent
    
    # Second pass: check logging statements for proper indentation
    for i, line in enumerate(lines):
        # Skip non-logging lines
        if not ('logger.' in line or '_logger.' in line):
            continue
            
        current_indent = len(line) - len(line.lstrip())
        line_num = i + 1
        
        # If line is supposed to be in a block (from previous analysis)
        if i in expected_indents:
            expected_indent = expected_indents[i]
            if current_indent < expected_indent:
                # Fix the indentation
                fixed_line = ' ' * expected_indent + line.lstrip()
                issues.append((line_num, line, fixed_line))
                continue
        
        # Additional checks for specific cases that might have been missed
        if i > 0:
            prev_line = lines[i-1].rstrip()
            
            # Look for control flow statements that should have indented logging
            control_patterns = [
                r'^\s*if\s+.*:$',
                r'^\s*elif\s+.*:$',
                r'^\s*else:$',
                r'^\s*except\s+.*:$',
                r'^\s*except:$',
                r'^\s*try:$',
                r'^\s*for\s+.*:$',
                r'^\s*while\s+.*:$',
                r'^\s*with\s+.*:$',
                r'^\s*def\s+.*:$',
                r'^\s*class\s+.*:$'
            ]
            
            if any(re.match(pattern, prev_line) for pattern in control_patterns):
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                # If indented less than 4 spaces from the control statement, it's likely wrong
                if current_indent <= prev_indent:
                    proper_indent = prev_indent + 4
                    fixed_line = ' ' * proper_indent + line.lstrip()
                    issues.append((line_num, line, fixed_line))
            
            # Check if this is a continuation line from a multi-line statement
            elif prev_line.endswith('\\'):
                prev_indent = len(prev_line) - len(prev_line.lstrip())
                if current_indent != prev_indent:
                    fixed_line = ' ' * prev_indent + line.lstrip()
                    issues.append((line_num, line, fixed_line))
    
    return issues


def fix_indentation_issues(file_path: str, issues: List[Tuple[int, str, str]], 
                           dry_run: bool = False, verbose: bool = False) -> bool:
    """Fix indentation issues in the specified file."""
    if not issues:
        return False
        
    if verbose:
        print(f"Found {len(issues)} indentation issues in {file_path}")
        
    if dry_run:
        for line_num, original, fixed in issues:
            print(f"Line {line_num} in {file_path}:")
            print(f"  - |{original.rstrip()}|")
            print(f"  + |{fixed.rstrip()}|")
        return True
    
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix the issues (adjusting for 0-based indexing)
    for line_num, _, fixed in issues:
        lines[line_num-1] = fixed
    
    # Write back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    if verbose:
        print(f"Fixed {len(issues)} indentation issues in {file_path}")
        
    return True


def process_file(file_path: str, dry_run: bool = False, verbose: bool = False) -> bool:
    """Process a single file to fix indentation issues."""
    try:
        # Detect indentation issues
        issues = detect_indentation_issues(file_path)
        
        # Fix the issues
        if issues:
            return fix_indentation_issues(file_path, issues, dry_run, verbose)
            
        return False
    except (IOError, OSError) as e:
        print(f"File I/O error processing {file_path}: {str(e)}")
        return False
    except UnicodeDecodeError:
        print(f"Unicode decode error in {file_path}. Skipping.")
        return False
    except ValueError as e:
        print(f"Value error in {file_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error processing {file_path}: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Split exclude patterns
    exclude_patterns = [p.strip() for p in args.exclude.split(',') if p.strip()]
    
    if args.verbose:
        print(f"Scanning directory: {args.directory}")
        print(f"Exclude patterns: {', '.join(exclude_patterns)}")
        print("Searching for indentation issues in logging statements...\n")
    
    # Walk through the directory tree
    fixed_files = []
    skipped_paths = 0
    processed_files = 0
    
    for root, dirs, files in os.walk(args.directory):
        # Modify dirs in-place to avoid traversing excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d), exclude_patterns)]
        
        if should_exclude(root, exclude_patterns):
            skipped_paths += 1
            continue
            
        for filename in files:
            if not filename.endswith('.py'):
                continue
                
            file_path = os.path.join(root, filename)
            
            if should_exclude(file_path, exclude_patterns):
                skipped_paths += 1
                continue
                
            processed_files += 1
            was_modified = process_file(file_path, args.dry_run, args.verbose)
            if was_modified:
                fixed_files.append(file_path)
    
    # Print summary
    print("\nSummary:")
    print(f"  - Processed {processed_files} Python files")
    print(f"  - Skipped {skipped_paths} paths due to exclusion patterns")
    print(f"  - {'Would fix' if args.dry_run else 'Fixed'} indentation in {len(fixed_files)} files")
    
    if args.verbose and fixed_files:
        print("\nModified files:")
        for f in sorted(fixed_files):
            print(f"  - {f}")
            
    if args.dry_run and fixed_files:
        print("\nThis was a dry run. No files were actually modified.")
        print("Run without --dry-run to apply the changes.")
        print("\nExample usage to apply changes:")
        print(f"  python fix_logging_indentation.py -d {args.directory}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
