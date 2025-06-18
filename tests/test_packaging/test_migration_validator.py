#!/usr/bin/env python3
"""
Migration validator utility for comparing packaging outputs.
Ensures that migrating to new build backends preserves all functionality.
"""

import difflib
import fnmatch
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

class PackagingMigrationValidator:
    """Validate packaging migration to ensure no regressions."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.critical_patterns = [
            # Plugin files
            "panther/plugins/**/*.py",
            "panther/plugins/**/*.yaml",
            "panther/plugins/**/*.jinja",
            "panther/plugins/**/Dockerfile*",
            "panther/plugins/**/*.j2",
            # Service implementations
            "panther/plugins/services/iut/**/*",
            "panther/plugins/services/testers/**/*",
            # Environment plugins
            "panther/plugins/environments/**/*",
            # Web application
            "panther/webapp/**/*",
            # Templates
            "panther/**/templates/**/*",
            # Type information
            "panther/py.typed",
            # Package metadata
            "panther_net-*.dist-info/METADATA",
            "panther_net-*.dist-info/entry_points.txt",
        ]

        self.metadata_to_check = [
            "Name",
            "Version",
            "Summary",
            "Author",
            "License",
            "Requires-Python",
            "Classifier",
        ]

    def extract_wheel_contents(self, wheel_path: Path) -> Dict[str, bytes]:
        """Extract all files from a wheel with their contents."""
        contents = {}
        with zipfile.ZipFile(wheel_path, "r") as wheel:
            for info in wheel.infolist():
                if not info.is_dir():
                    contents[info.filename] = wheel.read(info.filename)
        return contents

    def get_wheel_file_list(self, wheel_path: Path) -> Set[str]:
        """Get list of all files in a wheel."""
        with zipfile.ZipFile(wheel_path, "r") as wheel:
            return set(info.filename for info in wheel.infolist() if not info.is_dir())

    def compare_file_lists(
        self, old_files: Set[str], new_files: Set[str]
    ) -> Dict[str, Set[str]]:
        """Compare file lists between old and new wheels."""
        return {
            "added": new_files - old_files,
            "removed": old_files - new_files,
            "common": old_files & new_files,
        }

    def validate_critical_files(self, wheel_files: Set[str]) -> List[str]:
        """Check if all critical files are present in the wheel."""
        missing_patterns = []

        for pattern in self.critical_patterns:
            matching_files = [f for f in wheel_files if fnmatch.fnmatch(f, pattern)]
            if not matching_files:
                missing_patterns.append(pattern)

        return missing_patterns

    def compare_metadata(
        self, old_wheel: Path, new_wheel: Path
    ) -> Dict[str, List[str]]:
        """Compare metadata between two wheels."""
        differences = {}

        old_metadata = self._extract_metadata(old_wheel)
        new_metadata = self._extract_metadata(new_wheel)

        for key in self.metadata_to_check:
            old_values = old_metadata.get(key, [])
            new_values = new_metadata.get(key, [])

            if old_values != new_values:
                differences[key] = {
                    "old": old_values,
                    "new": new_values,
                }

        return differences

    def _extract_metadata(self, wheel_path: Path) -> Dict[str, List[str]]:
        """Extract metadata from wheel's METADATA file."""
        metadata = {}

        with zipfile.ZipFile(wheel_path, "r") as wheel:
            metadata_files = [f for f in wheel.namelist() if f.endswith("METADATA")]
            if metadata_files:
                content = wheel.read(metadata_files[0]).decode("utf-8")

                for line in content.split("\n"):
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        if key in self.metadata_to_check:
                            if key not in metadata:
                                metadata[key] = []
                            metadata[key].append(value.strip())

        return metadata

    def validate_entry_points(self, wheel_path: Path) -> Dict[str, str]:
        """Extract and validate entry points from wheel."""
        entry_points = {}

        with zipfile.ZipFile(wheel_path, "r") as wheel:
            ep_files = [f for f in wheel.namelist() if f.endswith("entry_points.txt")]
            if ep_files:
                content = wheel.read(ep_files[0]).decode("utf-8")

                current_section = None
                for line in content.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1]
                    elif "=" in line and current_section:
                        name, value = line.split("=", 1)
                        entry_points[
                            f"{current_section}:{name.strip()}"
                        ] = value.strip()

        return entry_points

    def build_wheel_with_backend(self, backend: str, output_dir: Path) -> Path:
        """Build wheel with specified backend."""
        # Create temporary pyproject.toml with specified backend
        original_pyproject = self.project_root / "pyproject.toml"
        backup_pyproject = self.project_root / "pyproject.toml.backup"

        # Backup original
        shutil.copy2(original_pyproject, backup_pyproject)

        try:
            # Read and modify pyproject.toml
            with open(original_pyproject, "r") as f:
                content = f.read()

            # Replace build backend
            if backend == "hatchling":
                new_content = content.replace(
                    'build-backend = "setuptools.build_meta"',
                    'build-backend = "hatchling.build"',
                ).replace(
                    'requires = ["setuptools>=68.0", "wheel>=0.41.0"]',
                    'requires = ["hatchling>=1.18.0"]',
                )

                # Add hatchling configuration
                new_content += """

[tool.hatch.build]
artifacts = [
    "panther/plugins/**/*",
    "panther/webapp/**/*",
]

[tool.hatch.build.targets.wheel]
packages = ["panther"]
include = [
    "/panther",
    "*.md",
    "*.txt"
]
exclude = [
    "tests/",
    "outputs*/",
    ".github/",
    "**/__pycache__"
]
"""
            else:
                new_content = content

            # Write modified content
            with open(original_pyproject, "w") as f:
                f.write(new_content)

            # Build wheel
            result = subprocess.run(
                [sys.executable, "-m", "build", "--wheel", "--outdir", str(output_dir)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Build failed: {result.stderr}")

            # Find created wheel
            wheel_files = list(output_dir.glob("*.whl"))
            if not wheel_files:
                raise RuntimeError("No wheel file created")

            return wheel_files[0]

        finally:
            # Restore original pyproject.toml
            shutil.move(backup_pyproject, original_pyproject)

    def generate_comparison_report(
        self, old_wheel: Path, new_wheel: Path, output_file: Path
    ) -> bool:
        """Generate detailed comparison report between two wheels."""

        print(f"Comparing wheels:")
        print(f"  Old (baseline): {old_wheel.name}")
        print(f"  New (candidate): {new_wheel.name}")

        # Get file lists
        old_files = self.get_wheel_file_list(old_wheel)
        new_files = self.get_wheel_file_list(new_wheel)

        # Compare files
        file_comparison = self.compare_file_lists(old_files, new_files)

        # Validate critical files
        old_missing = self.validate_critical_files(old_files)
        new_missing = self.validate_critical_files(new_files)

        # Compare metadata
        metadata_diff = self.compare_metadata(old_wheel, new_wheel)

        # Compare entry points
        old_entry_points = self.validate_entry_points(old_wheel)
        new_entry_points = self.validate_entry_points(new_wheel)

        # Generate report
        report = {
            "comparison": {
                "old_wheel": str(old_wheel),
                "new_wheel": str(new_wheel),
                "timestamp": datetime.now().isoformat(),
            },
            "file_comparison": {
                "total_old": len(old_files),
                "total_new": len(new_files),
                "added": sorted(list(file_comparison["added"]))[:20],  # First 20
                "removed": sorted(list(file_comparison["removed"]))[:20],
                "added_count": len(file_comparison["added"]),
                "removed_count": len(file_comparison["removed"]),
            },
            "critical_files": {
                "old_missing": old_missing,
                "new_missing": new_missing,
            },
            "metadata_differences": metadata_diff,
            "entry_points": {
                "old": old_entry_points,
                "new": new_entry_points,
                "differences": {
                    k: v
                    for k, v in new_entry_points.items()
                    if k not in old_entry_points or old_entry_points[k] != v
                },
            },
            "validation_passed": len(new_missing) == 0
            and len(file_comparison["removed"]) == 0,
        }

        # Write report
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\nValidation Summary:")
        print(f"  Files added: {report['file_comparison']['added_count']}")
        print(f"  Files removed: {report['file_comparison']['removed_count']}")
        print(f"  Critical files missing: {len(new_missing)}")
        print(f"  Metadata differences: {len(metadata_diff)}")
        print(
            f"  Entry point differences: {len(report['entry_points']['differences'])}"
        )
        print(
            f"\n  Validation: {'PASSED ✅' if report['validation_passed'] else 'FAILED ❌'}"
        )

        if not report["validation_passed"]:
            print("\n  Issues found:")
            if new_missing:
                print(f"    - Missing critical files: {new_missing[:5]}")
            if file_comparison["removed"]:
                print(f"    - Removed files: {list(file_comparison['removed'])[:5]}")

        print(f"\nDetailed report written to: {output_file}")

        return report["validation_passed"]

import shutil
from datetime import datetime

def main():
    """Command-line interface for migration validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Python packaging migration")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )
    parser.add_argument(
        "--compare-backends",
        nargs=2,
        metavar=("OLD", "NEW"),
        default=["setuptools", "hatchling"],
        help="Compare two build backends",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("packaging_migration_report.json"),
        help="Output report file",
    )

    args = parser.parse_args()

    validator = PackagingMigrationValidator(args.project_root)

    # Build wheels with both backends
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        print(f"Building with {args.compare_backends[0]}...")
        old_wheel = validator.build_wheel_with_backend(
            args.compare_backends[0], temp_path / "old"
        )

        print(f"Building with {args.compare_backends[1]}...")
        new_wheel = validator.build_wheel_with_backend(
            args.compare_backends[1], temp_path / "new"
        )

        # Generate comparison report
        success = validator.generate_comparison_report(
            old_wheel, new_wheel, args.output
        )

        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
