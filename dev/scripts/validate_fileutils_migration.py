#!/usr/bin/env python3
"""
Validation script to ensure FileUtils migration completeness.

This script checks for any remaining direct file operations in the codebase.
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

class MigrationValidator:
    """Validator for FileUtils migration."""
    
    def __init__(self):
        self.violations = []
        self.validated_files = 0
        self.skipped_files = 0
        
        # Patterns to detect
        self.violation_patterns = {
            'yaml_load': re.compile(r'yaml\.(safe_)?load\s*\('),
            'yaml_dump': re.compile(r'yaml\.(safe_)?dump\s*\('),
            'json_load': re.compile(r'json\.load\s*\('),
            'json_dump': re.compile(r'json\.dumps?\s*\('),
            'file_open': re.compile(r'(?<!def\s)open\s*\([^)]*["\']r["\']'),
            'makedirs': re.compile(r'os\.makedirs\s*\('),
            'path_mkdir': re.compile(r'\.mkdir\s*\('),
        }
        
        # Files/patterns to skip
        self.skip_patterns = [
            '__pycache__',
            '.git',
            'file_utils.py',
            'migrate_to_fileutils.py',
            'validate_fileutils_migration.py',
            'panther_ivy',  # Third-party code
            'submodules',   # External dependencies
        ]
        
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        path_str = str(file_path)
        return any(pattern in path_str for pattern in self.skip_patterns)
        
    def validate_file(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """
        Validate a single file for direct file operations.
        
        Returns:
            List of (violation_type, line_number, line_content) tuples
        """
        violations = []
        
        if self.should_skip_file(file_path):
            self.skipped_files += 1
            return violations
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                # Skip import lines
                if line.strip().startswith(('import ', 'from ')):
                    continue
                    
                # Check each violation pattern
                for violation_type, pattern in self.violation_patterns.items():
                    if pattern.search(line):
                        violations.append((violation_type, line_num, line.strip()))
                        
            self.validated_files += 1
            
        except Exception as e:
            violations.append(('error', 0, f"Error reading file: {e}"))
            
        return violations
        
    def validate_directory(self, directory: Path, pattern: str = "**/*.py") -> bool:
        """
        Validate all Python files in a directory.
        
        Returns:
            bool: True if no violations found
        """
        python_files = list(directory.glob(pattern))
        total_files = len(python_files)
        
        print(f"\n🔍 Validating {total_files} Python files...")
        
        for i, py_file in enumerate(python_files, 1):
            if i % 50 == 0:  # Progress indicator
                print(f"  Progress: {i}/{total_files} files...")
                
            file_violations = self.validate_file(py_file)
            if file_violations:
                self.violations.append((py_file, file_violations))
                
        return len(self.violations) == 0
        
    def generate_report(self) -> str:
        """Generate validation report."""
        report = [
            "\n" + "=" * 60,
            "FileUtils Migration Validation Report",
            "=" * 60,
            f"\n📊 Summary:",
            f"  - Files validated: {self.validated_files}",
            f"  - Files skipped: {self.skipped_files}",
            f"  - Files with violations: {len(self.violations)}",
        ]
        
        if not self.violations:
            report.append("\n✅ All files passed validation!")
            report.append("🎉 FileUtils migration is complete!")
        else:
            # Count violations by type
            violation_counts = {}
            total_violations = 0
            for _, file_violations in self.violations:
                for vtype, _, _ in file_violations:
                    violation_counts[vtype] = violation_counts.get(vtype, 0) + 1
                    total_violations += 1
                    
            report.append(f"  - Total violations: {total_violations}")
            report.append("\n📈 Violations by Type:")
            for vtype, count in sorted(violation_counts.items()):
                report.append(f"  - {vtype}: {count}")
                
            report.append("\n❌ Files with Violations:")
            for file_path, file_violations in self.violations[:20]:  # Show first 20
                report.append(f"\n📄 {file_path}:")
                for vtype, line_num, content in file_violations[:5]:  # Show first 5 per file
                    report.append(f"  Line {line_num} [{vtype}]: {content[:80]}...")
                if len(file_violations) > 5:
                    report.append(f"  ... and {len(file_violations) - 5} more violations")
                    
            if len(self.violations) > 20:
                report.append(f"\n... and {len(self.violations) - 20} more files with violations")
                
        report.append("\n" + "=" * 60)
        return '\n'.join(report)
        
    def generate_fix_suggestions(self) -> str:
        """Generate suggestions for fixing violations."""
        if not self.violations:
            return ""
            
        suggestions = ["\n💡 Fix Suggestions:"]
        
        # Group files by directory
        by_directory = {}
        for file_path, _ in self.violations:
            dir_path = file_path.parent
            by_directory.setdefault(dir_path, []).append(file_path)
            
        # Suggest batch fixes by directory
        for dir_path, files in sorted(by_directory.items()):
            if len(files) > 1:
                suggestions.append(f"\n  # Fix all files in {dir_path}:")
                suggestions.append(f"  python scripts/migrate_to_fileutils.py {dir_path}")
                
        suggestions.append("\n  # Or fix all at once:")
        suggestions.append("  python scripts/migrate_to_fileutils.py .")
        
        return '\n'.join(suggestions)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate FileUtils migration completeness"
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory to validate (default: current directory)'
    )
    parser.add_argument(
        '--pattern',
        default='**/*.py',
        help='Glob pattern for files (default: **/*.py)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit with error code if violations found'
    )
    parser.add_argument(
        '--fix-suggestions',
        action='store_true',
        help='Show suggestions for fixing violations'
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = MigrationValidator()
    
    # Run validation
    path = Path(args.path)
    is_valid = validator.validate_directory(path, args.pattern)
    
    # Generate report
    print(validator.generate_report())
    
    # Show fix suggestions if requested
    if args.fix_suggestions and not is_valid:
        print(validator.generate_fix_suggestions())
    
    # Exit code
    if args.strict and not is_valid:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()