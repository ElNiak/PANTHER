#!/usr/bin/env python3
"""
Script to fix logging f-string interpolation issues in Python files.

This script converts code like:
    logger.info(f"Some message with {variable}")
To:
    logger.info("Some message with %s", variable)

It handles multi-line strings and multiple variables within a logging statement.
"""

import os
import re
import sys
import ast
import argparse
import glob
from typing import List, Tuple, Set, Optional, Dict


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Fix f-string interpolation in logging statements'
    )
    parser.add_argument(
        '-d', '--directory',
        default='panther',
        help='Directory to recursively process (default: panther)'
    )
    parser.add_argument(
        '--exclude',
        default='panther/plugins/services/testers/panther_ivy,*.venv*,.venv',
        help='Comma-separated list of directories and patterns to exclude (default: panther/plugins/services/testers/panther_ivy,*.venv*,.venv)'
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


class FStringVisitor(ast.NodeVisitor):
    """AST visitor to find f-string usage in logging statements."""
    
    def __init__(self):
        self.logging_locations = []
        
    def visit_Call(self, node):
        """Visit function call nodes to find logging statements with f-strings."""
        # Check if it's a logging function call
        if isinstance(node.func, ast.Attribute) and hasattr(node.func, 'attr'):
            log_methods = ('debug', 'info', 'warning', 'error', 'critical', 'exception', 'log')
            
            if node.func.attr in log_methods:
                # Check the object is logger
                if isinstance(node.func.value, ast.Name) and 'logger' in node.func.value.id:
                    # Check for f-strings in arguments
                    if node.args and isinstance(node.args[0], ast.JoinedStr):
                        start_line = node.args[0].lineno
                        end_line = node.args[-1].end_lineno if hasattr(node.args[-1], 'end_lineno') else start_line
                        self.logging_locations.append((start_line, end_line))
        
        # Continue traversing the tree
        self.generic_visit(node)


def has_logging_fstrings(file_path: str) -> bool:
    """Check if a file has logging statements with f-strings using the AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        tree = ast.parse(content)
        visitor = FStringVisitor()
        visitor.visit(tree)
        
        return len(visitor.logging_locations) > 0
    except (SyntaxError, UnicodeDecodeError):
        # If we can't parse the file, we'll use a more basic regex approach
        return has_logging_fstrings_regex(file_path)


def has_logging_fstrings_regex(file_path: str) -> bool:
    """Fallback method to check for f-strings in logging using regex."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Look for patterns like logger.info(f"...") or logger.debug(f'...')
        pattern = r'logger\s*\.\s*(debug|info|warning|error|critical|exception|log)\s*\(\s*f[\"|\']'
        return bool(re.search(pattern, content))
    except (UnicodeDecodeError, IOError):
        return False


def find_fstring_logging_calls(content: str) -> List[Tuple[int, int, str]]:
    """
    Find logging calls with f-strings in the content.
    
    Returns a list of tuples: (start_line, end_line, original_text)
    """
    # Split the content into lines for easier processing
    lines = content.splitlines()
    result = []
    
    # We'll build a line-by-line representation to handle multi-line statements
    line_number = 0
    while line_number < len(lines):
        line = lines[line_number]
        
        # More comprehensive regex to catch different logging patterns
        # Matches patterns like: logger.info(f"..."), self.logger.info(f"..."), _logger.info(f"...")
        pattern = r'(?:\w+\.)*(?:logger|_logger)\s*\.\s*(debug|info|warning|warn|error|critical|exception|log)\s*\(\s*f[\"|\']'
        if re.search(pattern, line):
            # Find where the statement ends
            start_line = line_number
            current = line
            
            # Keep accumulating lines until we have balanced parentheses
            open_parens = current.count('(') - current.count(')')
            end_line = start_line
            
            while open_parens > 0 and end_line + 1 < len(lines):
                end_line += 1
                next_line = lines[end_line]
                open_parens += next_line.count('(') - next_line.count(')')
                current += '\n' + next_line
            
            result.append((start_line, end_line, current))
            line_number = end_line
        
        line_number += 1
    
    return result


def fix_fstring_logging(match: str) -> str:
    """
    Convert a logging f-string to %-formatting.
    
    Example:
    logger.info(f"Hello {name}") -> logger.info("Hello %s", name)
    """
    try:
        # Extract the logger and method part (preserving any prefix like self.logger, etc.)
        logger_match = re.search(r'((?:\w+\.)*(?:logger|_logger)\s*\.\s*)(debug|info|warning|warn|error|critical|exception|log)', match)
        if not logger_match:
            return match
            
        logger_prefix = logger_match.group(1)
        method = logger_match.group(2)
        
        # Extract the f-string
        fstring_match = re.search(r'f(["\'])(.*?)(\1)', match)
        if not fstring_match:
            return match
            
        quote_char = fstring_match.group(1)
        fstring_content = fstring_match.group(2)
        
        # Find all expressions within braces
        expr_pattern = r'\{([^{}]+?)\}'
        expressions = re.findall(expr_pattern, fstring_content)
        
        # Replace each expression with %s
        new_content = re.sub(expr_pattern, '%s', fstring_content)
        
        # Create the new logging statement
        new_args = ", ".join(expressions)
        if new_args:
            new_args = ", " + new_args
        
        # Create the new logging statement with proper quoting
        new_match = '{0}{1}({2}{3}{2}{4})'.format(
            logger_prefix, method, quote_char, new_content, new_args
        )
        
        return new_match
    except Exception:
        # If there's any error in parsing, return the original match
        print("Error parsing f-string. Skipping.")
        return match


def process_file(file_path: str, dry_run: bool = False, verbose: bool = False) -> bool:
    """Process a single file to fix f-string logging issues."""
    modified = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Quick check to avoid unnecessary processing
        if ('logger.' not in content and '_logger.' not in content) or ('f"' not in content and "f'" not in content):
            return False

        fstring_calls = find_fstring_logging_calls(content)
        if not fstring_calls:
            return False

        lines = content.splitlines()
        
        # Process matches from end to beginning to avoid line number issues
        for start_line, end_line, original_text in sorted(fstring_calls, reverse=True):
            # Fix the f-string
            fixed_text = fix_fstring_logging(original_text)
            
            if fixed_text != original_text:
                modified += 1
                
                if verbose:
                    print("In {} lines {}-{}:".format(file_path, start_line+1, end_line+1))
                    print("  - {}".format(original_text))
                    print("  + {}".format(fixed_text))
                
                # Replace the original lines with our fixed version
                old_lines = lines[start_line:end_line + 1]
                if len(old_lines) == 1:
                    # Simple single-line case
                    lines[start_line] = fixed_text
                else:
                    # For multi-line statements, replace with fixed version
                    # (simplified; might need adjustments for complex multi-line cases)
                    lines[start_line:end_line + 1] = [fixed_text]
        
        if modified > 0 and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(lines))
            
            if verbose:
                print("Fixed {}".format(file_path))
        
        return modified
    except Exception:
        print("Error processing {}. Skipping.".format(file_path))
        return modified


def should_exclude(path: str, exclude_patterns: List[str]) -> bool:
    """Check if a path matches any exclude pattern."""
    path = os.path.normpath(path)
    
    # Always exclude .venv directories
    if "/.venv/" in path.replace("\\", "/") or "\\.venv\\" in path.replace("/", "\\"):
        return True
    
    for pattern in exclude_patterns:
        # Handle glob patterns
        if '*' in pattern or '?' in pattern or '[' in pattern:
            if any(path.startswith(os.path.normpath(matching_path)) 
                   for matching_path in glob.glob(pattern)):
                return True
        # Handle direct substring match
        elif pattern in path:
            return True
            
    return False


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Split exclude patterns
    exclude_patterns = [p.strip() for p in args.exclude.split(',') if p.strip()]
    
    # Walk through the directory tree
    modified_files = []
    skipped_files = set()
    
    for root, dirs, files in os.walk(args.directory):
        # Skip .venv directories entirely
        dirs[:] = [d for d in dirs if d != '.venv' and not d.endswith('.venv')]
        
        if should_exclude(root, exclude_patterns):
            continue
            
        for filename in files:
            if not filename.endswith('.py'):
                continue
                
            file_path = os.path.join(root, filename)
            
            # Additional check for path exclusion
            if should_exclude(file_path, exclude_patterns):
                continue
            
            # Skip files that have syntax errors or are not valid Python
            try:
                has_issues = has_logging_fstrings(file_path)
            except Exception:
                print("Error checking {}. Skipping.".format(file_path))
                skipped_files.add(file_path)
                continue
                
            if has_issues:
                was_modified = process_file(file_path, args.dry_run, args.verbose)
                if was_modified > 0: 
                    modified_files.append(file_path)
    
    # Print summary
    print("\nSummary:")
    print("  - Found and {}: {} files".format('would fix' if args.dry_run else 'fixed', len(modified_files)))
    print("  - Skipped due to errors: {} files".format(len(skipped_files)))
    
    if args.verbose and modified_files:
        print("\nModified files:")
        for f in sorted(modified_files):
            print("  - {}".format(f))
            
    if args.dry_run and modified_files:
        print("\nThis was a dry run. No files were actually modified.")
        print("Run without --dry-run to apply the changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
