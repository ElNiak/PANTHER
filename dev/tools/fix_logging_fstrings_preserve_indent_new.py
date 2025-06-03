#!/usr/bin/env python3
"""
Script to fix logging f-string interpolation issues in Python files.

This script converts code like:
    logger.info(f"Some message {variable}")
To:
    logger.info("Some message %s", variable)

It handles multi-line strings and multiple variables within a logging statement.
It preserves the original indentation of the code.
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
        default='panther/plugins/services/testers/panther_ivy/submodule, panther/plugins/services/testers/panther_ivy/ivy,*.venv*,.venv',
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
        self.logger_names = set()  # Track logger variable names we find
        
    def is_logger_object(self, node):
        """Check if a node represents a logger object."""
        # Direct logger variable (logger, _logger)
        if isinstance(node, ast.Name) and ('logger' in node.id or node.id.endswith('_logger')):
            self.logger_names.add(node.id)
            return True
            
        # Instance/class attribute (self.logger, cls.logger)
        if isinstance(node, ast.Attribute) and ('logger' in node.attr or node.attr.endswith('_logger')):
            self.logger_names.add(f"{self.get_attribute_source(node)}.{node.attr}")
            return True
            
        # Module access (logging.getLogger)
        if isinstance(node, ast.Attribute) and node.attr == 'getLogger':
            if isinstance(node.value, ast.Name) and node.value.id == 'logging':
                return True
                
        return False
    
    def get_attribute_source(self, node):
        """Get the source of an attribute (e.g., 'self' in 'self.logger')"""
        if isinstance(node.value, ast.Name):
            return node.value.id
        return "object"  # Generic fallback
        
    def visit_Call(self, node):
        """Visit function call nodes to find logging statements with f-strings."""
        # Check if it's a logging function call
        if isinstance(node.func, ast.Attribute) and hasattr(node.func, 'attr'):
            log_methods = ('debug', 'info', 'warning', 'warn', 'error', 'critical', 'exception', 'log')
            
            if node.func.attr in log_methods:
                # Check if the object is a logger
                if self.is_logger_object(node.func.value) or self.is_potential_logger(node.func.value):
                    # Check for f-strings in arguments
                    if node.args and isinstance(node.args[0], ast.JoinedStr):
                        start_line = node.args[0].lineno
                        end_line = node.args[-1].end_lineno if hasattr(node.args[-1], 'end_lineno') else start_line
                        self.logging_locations.append((start_line, end_line))
            
            # Handle logging.getLogger().info(...) pattern
            elif node.func.attr == 'getLogger' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'logging':
                # Track the next function call on this result
                self.generic_visit(node)
                
        # Check for logger constructor assignments
        elif isinstance(node.func, ast.Name) and node.func.id == 'getLogger':
            # This might be logging.getLogger without the logging. prefix
            self.generic_visit(node)
                
        # Continue traversing the tree for other nodes
        self.generic_visit(node)
    
    def is_potential_logger(self, node):
        """Check if a node might be a logger object based on conventions."""
        # Handle cases like module_logger, app_logger, etc.
        if isinstance(node, ast.Name) and ('_logger' in node.id or node.id.endswith('logger')):
            return True
        
        # Check for common patterns in attribute access
        if isinstance(node, ast.Attribute):
            attr_names = ['logger', 'log']
            return any(name in node.attr for name in attr_names)
        
        return False
        
    def visit_Assign(self, node):
        """Track logger variable assignments."""
        # Look for patterns like: logger = logging.getLogger(__name__)
        if isinstance(node.value, ast.Call):
            if (isinstance(node.value.func, ast.Attribute) and 
                node.value.func.attr == 'getLogger' and
                isinstance(node.value.func.value, ast.Name) and
                node.value.func.value.id == 'logging'):
                
                # Get the name of the variable being assigned
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.logger_names.add(target.id)
        
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
        
        # Build a comprehensive pattern for different logging patterns:
        # 1. Standard loggers: logger.info(), _logger.info(), module_logger.info() 
        # 2. Instance/class attributes: self.logger.info(), cls.logger.info()
        # 3. Direct logging module: logging.info(), logging.error()
        # 4. Getlogger patterns: logging.getLogger(__name__).info()
        
        # Common logging methods
        log_methods = r'(?:debug|info|warning|warn|error|critical|exception|log)'
        
        # Logger variable patterns
        logger_vars = r'(?:logger|_logger|[a-zA-Z0-9_]+_logger|[a-zA-Z0-9_]+logger)'
        
        # Different access patterns
        patterns = [
            # Standard logger variable
            fr'{logger_vars}\s*\.\s*{log_methods}\s*\(\s*f[\"|\']',
            
            # Instance/class attribute logger
            fr'(?:self|cls|[a-zA-Z0-9_]+)\s*\.\s*{logger_vars}\s*\.\s*{log_methods}\s*\(\s*f[\"|\']',
            
            # Direct logging module usage
            fr'logging\s*\.\s*{log_methods}\s*\(\s*f[\"|\']',
            
            # getLogger pattern
            fr'(?:logging\s*\.)?\s*getLogger\s*\([^)]*\)\s*\.\s*{log_methods}\s*\(\s*f[\"|\']'
        ]
        
        combined_pattern = '|'.join(patterns)
        return bool(re.search(combined_pattern, content))
    except (UnicodeDecodeError, IOError):
        return False


def find_fstring_logging_calls(content: str) -> List[Tuple[int, int, str, int]]:
    """
    Find logging calls with f-strings in the content.
    
    Returns a list of tuples: (start_line, end_line, original_text, indentation)
    where indentation is the number of spaces at the start of the line
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
        pattern = r'(?:\w+\.)*(?:logger|_logger|logging)\s*\.\s*(debug|info|warning|warn|error|critical|exception|log)\s*\('
        match = re.search(pattern, line)
        
        if match:
            # Calculate indentation (number of spaces at the beginning)
            indentation = len(line) - len(line.lstrip())
            
            # Find where the statement ends
            start_line = line_number
            current = line
            
            # Keep accumulating lines until we have balanced parentheses
            open_parens = current.count('(') - current.count(')')
            end_line = start_line
            found_fstring = 'f"' in current or "f'" in current or 'f"""' in current or "f'''" in current
            
            # Look ahead to see if an f-string appears in the next few lines (part of this statement)
            while open_parens > 0 and end_line + 1 < len(lines):
                end_line += 1
                next_line = lines[end_line]
                open_parens += next_line.count('(') - next_line.count(')')
                current += '\n' + next_line
                
                # Check if we've found an f-string in the accumulated content
                if ('f"' in next_line or "f'" in next_line or 
                    'f"""' in next_line or "f'''" in next_line):
                    found_fstring = True
            
            # Only add to results if we found an f-string inside the statement
            if found_fstring:
                # Additional verification with a more tolerant pattern
                fstring_pattern = r'(?:\w+\.)*(?:logger|_logger|logging)\s*\.\s*(?:debug|info|warning|warn|error|critical|exception|log).*f[\'"]{1,3}'
                
                if re.search(fstring_pattern, current, re.DOTALL):
                    # Check if the f-string is in any of the arguments
                    args_start = current.find('(') + 1
                    if args_start > 0:
                        args_text = current[args_start:]
                        if 'f"' in args_text or "f'" in args_text or 'f"""' in args_text or "f'''" in args_text:
                            result.append((start_line, end_line, current, indentation))
            
            # Skip to the end of the processed statement
            line_number = end_line
        
        line_number += 1
    
    return result


def fix_fstring_logging(match: str, indentation: int) -> str:
    """
    Convert a logging f-string to %-formatting while preserving indentation.
    
    Example:
    logger.info(f"Hello {name}") -> logger.info("Hello %s", name)
    
    Args:
        match: The original logging statement text
        indentation: Number of spaces to indent the result
    """
    try:
        # Extract the logger and method part (preserving any prefix like self.logger, etc.)
        logger_match = re.search(r'((?:\w+\.)*(?:logger|_logger|logging)\s*\.\s*)(debug|info|warning|warn|error|critical|exception|log)', match)
        if not logger_match:
            return match
            
        logger_prefix = logger_match.group(1)
        method = logger_match.group(2)
        
        # Extract the f-string, handling multi-line strings and indentation
        fstring_match = re.search(r'f(["\'])(.*?)(\1)', match, re.DOTALL)
        if not fstring_match:
            # Try with triple quotes
            fstring_match = re.search(r'f(["\'])\1\1(.*?)(\1\1\1)', match, re.DOTALL)
            if not fstring_match:
                return match
                
        quote_char = fstring_match.group(1)
        fstring_content = fstring_match.group(2)
        
        # Find all expressions within braces
        expr_pattern = r'\{([^{}]+?)\}'
        expressions = re.findall(expr_pattern, fstring_content)
        
        # Replace each expression with %s
        new_content = re.sub(expr_pattern, '%s', fstring_content)
        
        # Determine if this is a multi-line statement
        is_multiline = '\n' in match
        indent_str = ' ' * indentation
        
        # Get opening parenthesis position to determine if f-string is on same line
        opening_paren = match.find('(')
        first_line_end = match.find('\n') if '\n' in match else len(match)
        fstring_on_first_line = ('f"' in match[:first_line_end] or "f'" in match[:first_line_end] or 
                               'f"""' in match[:first_line_end] or "f'''" in match[:first_line_end])
        
        # Determine proper continuation indentation based on statement structure
        if is_multiline and not fstring_on_first_line:
            # Find the indentation of the line with the f-string
            lines = match.split('\n')
            for i, line in enumerate(lines):
                if ('f"' in line or "f'" in line or 
                    'f"""' in line or "f'''" in line):
                    continuation_indent = len(line) - len(line.lstrip())
                    break
            else:
                continuation_indent = indentation + 4  # Default continuation indent
        else:
            continuation_indent = indentation + 4  # Default continuation indent
        
        continuation_indent_str = ' ' * continuation_indent
        
        if is_multiline:
            # For multi-line statements, create a properly formatted output
            opening_line = f"{indent_str}{logger_prefix}{method}("
            string_line = f"{continuation_indent_str}{quote_char}{new_content}{quote_char},"
            
            # Format each expression as a separate argument
            args_lines = []
            for expr in expressions:
                args_lines.append(f"{continuation_indent_str}{expr}")
            
            # Join all parts with proper newlines and add closing parenthesis
            result = opening_line + "\n" + string_line + "\n" + ",\n".join(args_lines) + "\n" + indent_str + ")"
            return result
        else:
            # For single line statements
            new_args = ", ".join(expressions)
            if new_args:
                new_args = ", " + new_args
            
            # Create the new logging statement with proper indentation
            new_match = f"{indent_str}{logger_prefix}{method}({quote_char}{new_content}{quote_char}{new_args})"
            return new_match
    except Exception as e:
        # If there's any error in parsing, return the original match
        print(f"Error parsing f-string: {e}. Skipping.")
        return match


def process_file(file_path: str, dry_run: bool = False, verbose: bool = False) -> bool:
    """Process a single file to fix f-string logging issues."""
    modified = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Quick check to avoid unnecessary processing
        if ('logger.' not in content and '_logger.' not in content and 'logging.' not in content) or ('f"' not in content and "f'" not in content):
            return False

        fstring_calls = find_fstring_logging_calls(content)
        if not fstring_calls:
            return False

        lines = content.splitlines()
        
        # Process matches from end to beginning to avoid line number issues
        for start_line, end_line, original_text, indentation in sorted(fstring_calls, reverse=True):
            # Fix the f-string
            fixed_text = fix_fstring_logging(original_text, indentation)
            
            if fixed_text != original_text:
                modified += 1
                if verbose:
                    print("In {} lines {}-{}:".format(file_path, start_line+1, end_line+1))
                    print("  - {}".format(original_text))
                    print("  + {}".format(fixed_text))
                    print(f"Indentation found: {indentation} spaces")

                
                # Replace the original lines with our fixed version
                old_lines = lines[start_line:end_line + 1]
                if len(old_lines) == 1:
                    # Simple single-line case
                    lines[start_line] = fixed_text
                else:
                    # For multi-line statements, we need to carefully handle line replacements
                    # to preserve original indentation for lines before and after the match
                    fixed_lines = fixed_text.splitlines()
                    
                    # Replace the lines in the original content
                    lines[start_line:end_line + 1] = fixed_lines
        
        if modified > 0 and not dry_run:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(lines))
            
            if verbose:
                print("Fixed {}".format(file_path))
        
        return modified > 0
    except Exception as e:
        print(f"Error processing {file_path}. Skipping: {str(e)}")
        return False


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

    # Handle both file and directory inputs
    if os.path.isfile(args.directory):
        file_path = args.directory
        # Skip files that are in exclude patterns
        if should_exclude(file_path, exclude_patterns):
            print(f"Skipping excluded file: {file_path}")
        elif not file_path.endswith('.py'):
            print(f"Skipping non-Python file: {file_path}")
        else:
            print(f"Processing file: {file_path}")
            try:
                has_issues = has_logging_fstrings_regex(file_path)
                if has_issues:
                    was_modified = process_file(file_path, args.dry_run, args.verbose)
                    if was_modified:
                        modified_files.append(file_path)
            except Exception as e:
                print(f"Error checking file {file_path}: {str(e)}")
                skipped_files.add(file_path)
    else:
        # Process directories recursively
        for root, dirs, files in os.walk(args.directory):
            # Skip .venv directories entirely
            dirs[:] = [d for d in dirs if d != '.venv' and not d.endswith('.venv') and not "panther_ivy/submodules" in d]
            
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
                    has_issues = has_logging_fstrings_regex(file_path)
                except Exception as e:
                    print(f"Error checking file {file_path}: {str(e)}")
                    skipped_files.add(file_path)
                    continue
                    
                if has_issues:
                    print(f"Processing file: {file_path}")
                    was_modified = process_file(file_path, args.dry_run, args.verbose)
                    if was_modified:
                        modified_files.append(file_path)
    
    # Print summary
    print("\nSummary:")
    print(f"  - Found and {'would fix' if args.dry_run else 'fixed'}: {len(modified_files)} files")
    print(f"  - Skipped due to errors: {len(skipped_files)} files")
    
    if args.verbose and modified_files:
        print("\nModified files:")
        for f in sorted(modified_files):
            print(f"  - {f}")
            
    if args.dry_run and modified_files:
        print("\nThis was a dry run. No files were actually modified.")
        print("Run without --dry-run to apply the changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
