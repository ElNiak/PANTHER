#!/usr/bin/env python3
"""
Automated migration script for FileUtils refactoring.

This script automatically migrates common file operation patterns to use FileUtils.
"""
import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

class FileUtilsMigrator:
    """Automated migrator for FileUtils refactoring."""
    
    def __init__(self):
        self.files_modified = set()
        self.changes_made = []
        self.errors = []
        
        # Define migration patterns
        self.patterns = {
            # YAML loading patterns
            'yaml_load_with': (
                r'with\s+open\s*\(([^)]+)\)(?:\s+as\s+(\w+))?:\s*\n\s*(\w+)\s*=\s*yaml\.safe_load\s*\(\s*\2\s*\)',
                r'\3 = FileUtils.read_yaml_file(\1)'
            ),
            'yaml_load_direct': (
                r'yaml\.safe_load\s*\(\s*open\s*\(([^)]+)\)\s*\)',
                r'FileUtils.read_yaml_file(\1)'
            ),
            
            # JSON loading patterns
            'json_load_with': (
                r'with\s+open\s*\(([^)]+)\)(?:\s+as\s+(\w+))?:\s*\n\s*(\w+)\s*=\s*json\.load\s*\(\s*\2\s*\)',
                r'\3 = FileUtils.read_json_file(\1)'
            ),
            'json_load_direct': (
                r'json\.load\s*\(\s*open\s*\(([^)]+)\)\s*\)',
                r'FileUtils.read_json_file(\1)'
            ),
            
            # JSON dumping patterns
            'json_dump_with': (
                r'with\s+open\s*\(([^)]+),\s*["\']w["\']\)(?:\s+as\s+(\w+))?:\s*\n\s*json\.dump\s*\(([^,]+),\s*\2(?:,\s*indent\s*=\s*(\d+))?\)',
                lambda m: f'FileUtils.write_json_file({m.group(1)}, {m.group(3)}{f", indent={m.group(4)}" if m.group(4) else ""})'
            ),
            
            # YAML dumping patterns
            'yaml_dump_with': (
                r'with\s+open\s*\(([^)]+),\s*["\']w["\']\)(?:\s+as\s+(\w+))?:\s*\n\s*yaml\.safe_dump\s*\(([^,]+),\s*\2[^)]*\)',
                r'FileUtils.write_yaml_file(\1, \3)'
            ),
            
            # Directory creation patterns
            'makedirs': (
                r'os\.makedirs\s*\(([^,)]+)(?:,\s*exist_ok\s*=\s*True)?\)',
                r'FileUtils.ensure_directory_exists(\1)'
            ),
            'path_mkdir': (
                r'([^.]+)\.mkdir\s*\(\s*parents\s*=\s*True\s*,\s*exist_ok\s*=\s*True\s*\)',
                r'FileUtils.ensure_directory_exists(\1)'
            ),
            
            # Simple text file reading
            'read_text_with': (
                r'with\s+open\s*\(([^)]+)(?:,\s*["\']r["\'])?\)(?:\s+as\s+(\w+))?:\s*\n\s*(\w+)\s*=\s*\2\.read\s*\(\s*\)',
                r'\3 = FileUtils.read_text_file(\1)'
            ),
            
            # Simple text file writing
            'write_text_with': (
                r'with\s+open\s*\(([^)]+),\s*["\']w["\']\)(?:\s+as\s+(\w+))?:\s*\n\s*\2\.write\s*\(([^)]+)\)',
                r'FileUtils.write_text_file(\1, \3)'
            ),
        }
        
    def migrate_file(self, file_path: Path, dry_run: bool = False) -> bool:
        """
        Migrate a single Python file to use FileUtils.
        
        Args:
            file_path: Path to the Python file
            dry_run: If True, show changes without applying them
            
        Returns:
            bool: True if changes were made/would be made
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Skip if already uses FileUtils
            if 'from panther.core.utils.file_utils import' in content:
                print(f"  ⏭️  {file_path} - Already uses FileUtils")
                return False
            
            # Apply all migration patterns
            changes = []
            for pattern_name, (pattern, replacement) in self.patterns.items():
                matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))
                if matches:
                    for match in reversed(matches):  # Reverse to maintain positions
                        if callable(replacement):
                            new_text = replacement(match)
                        else:
                            new_text = match.expand(replacement)
                        
                        content = content[:match.start()] + new_text + content[match.end():]
                        changes.append(f"{pattern_name}: {match.group(0)[:50]}...")
            
            # Check if any changes were made
            if content != original_content:
                # Add FileUtils import at the top
                content = self._add_fileutils_import(content)
                
                if not dry_run:
                    # Write back the file
                    file_path.write_text(content, encoding='utf-8')
                    self.files_modified.add(file_path)
                    
                self.changes_made.extend([(file_path, change) for change in changes])
                print(f"  ✅ {file_path} - {len(changes)} changes made")
                return True
            else:
                print(f"  ⏭️  {file_path} - No changes needed")
                return False
                
        except Exception as e:
            self.errors.append((file_path, str(e)))
            print(f"  ❌ {file_path} - Error: {e}")
            return False
            
    def _add_fileutils_import(self, content: str) -> str:
        """Add FileUtils import to the file."""
        lines = content.split('\n')
        
        # Find the last import line
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
                
        # Add FileUtils import after the last import
        import_line = "from panther.core.utils.file_utils import FileUtils, FileOperationError"
        lines.insert(last_import_idx + 1, import_line)
        
        return '\n'.join(lines)
        
    def migrate_directory(self, directory: Path, pattern: str = "**/*.py", dry_run: bool = False):
        """
        Migrate all Python files in a directory.
        
        Args:
            directory: Directory to scan
            pattern: Glob pattern for files
            dry_run: If True, show changes without applying
        """
        print(f"\n🔍 Scanning directory: {directory}")
        python_files = list(directory.glob(pattern))
        
        print(f"📁 Found {len(python_files)} Python files")
        
        for py_file in python_files:
            # Skip some files
            if any(skip in str(py_file) for skip in ['__pycache__', 'file_utils.py', '.git']):
                continue
                
            self.migrate_file(py_file, dry_run)
            
    def generate_report(self) -> str:
        """Generate a migration report."""
        report = [
            "\n" + "=" * 60,
            "FileUtils Migration Report",
            "=" * 60,
            f"\n📊 Summary:",
            f"  - Files modified: {len(self.files_modified)}",
            f"  - Total changes: {len(self.changes_made)}",
            f"  - Errors: {len(self.errors)}",
        ]
        
        if self.files_modified:
            report.append("\n✅ Modified Files:")
            for file_path in sorted(self.files_modified):
                report.append(f"  - {file_path}")
                
        if self.changes_made:
            report.append("\n📝 Changes Made:")
            for file_path, change in self.changes_made[:10]:  # Show first 10
                report.append(f"  - {file_path}: {change}")
            if len(self.changes_made) > 10:
                report.append(f"  ... and {len(self.changes_made) - 10} more")
                
        if self.errors:
            report.append("\n❌ Errors:")
            for file_path, error in self.errors:
                report.append(f"  - {file_path}: {error}")
                
        report.append("\n" + "=" * 60)
        return '\n'.join(report)

def main():
    """Main entry point for the migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate file operations to use FileUtils",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate a single file
  python migrate_to_fileutils.py path/to/file.py
  
  # Migrate a directory (dry run)
  python migrate_to_fileutils.py path/to/dir --dry-run
  
  # Migrate specific phase
  python migrate_to_fileutils.py . --phase 1
  
  # Migrate with pattern
  python migrate_to_fileutils.py . --pattern "**/test_*.py"
        """
    )
    
    parser.add_argument('path', help='File or directory to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--pattern', default='**/*.py', help='Glob pattern for files')
    parser.add_argument('--phase', type=int, help='Migration phase (1-4)')
    
    args = parser.parse_args()
    
    # Phase-specific paths
    phase_patterns = {
        1: [  # Core infrastructure
            '**/config*.py',
            '**/__main__.py',
            '**/plugin_catalog.py',
            '**/protocol_interface.py',
        ],
        2: [  # Plugin system
            'plugins/**/*.py',
        ],
        3: [  # Utilities
            'core/template/**/*.py',
            'core/metrics/**/*.py',
            'tools/**/*.py',
        ],
        4: [  # Tests
            'tests/**/*.py',
        ]
    }
    
    # Create migrator
    migrator = FileUtilsMigrator()
    
    path = Path(args.path)
    
    if path.is_file():
        # Migrate single file
        print(f"\n📄 Migrating single file: {path}")
        migrator.migrate_file(path, args.dry_run)
    else:
        # Migrate directory
        if args.phase:
            # Use phase-specific patterns
            patterns = phase_patterns.get(args.phase, [])
            print(f"\n🎯 Running Phase {args.phase} migration")
            for pattern in patterns:
                migrator.migrate_directory(path, pattern, args.dry_run)
        else:
            # Use provided pattern
            migrator.migrate_directory(path, args.pattern, args.dry_run)
    
    # Generate report
    print(migrator.generate_report())
    
    if args.dry_run:
        print("\n⚠️  This was a DRY RUN - no files were modified")
        print("💡 Run without --dry-run to apply changes")
    
    # Exit with error if there were failures
    sys.exit(1 if migrator.errors else 0)

if __name__ == '__main__':
    main()