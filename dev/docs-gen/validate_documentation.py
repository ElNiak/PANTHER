#!/usr/bin/env python3
"""
Documentation Structure Validation Script

Validates the new PANTHER documentation structure for:
- File consistency
- Required sections
- Cross-reference integrity
- mkdocs compatibility
"""

import re
from pathlib import Path


class DocumentationValidator:
    def __init__(self, panther_root: Path):
        self.panther_root = panther_root
        self.plugins_root = panther_root / "plugins"
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> dict[str, bool]:
        """Run all validation checks."""
        results = {
            "file_structure": self.validate_file_structure(),
            "required_sections": self.validate_required_sections(),
            "cross_references": self.validate_cross_references(),
            "mkdocs_compatibility": self.validate_mkdocs_compatibility(),
        }

        return results

    def validate_file_structure(self) -> bool:
        """Validate that required documentation files exist."""
        required_files = [
            "README.md",
            "plugins/README.md",
            "plugins/services/README.md",
            "plugins/protocols/README.md",
            "plugins/environments/README.md",
            "core/README.md",
        ]

        success = True
        for file_path in required_files:
            full_path = self.panther_root / file_path
            if not full_path.exists():
                self.errors.append(f"Missing required file: {file_path}")
                success = False
            elif full_path.stat().st_size == 0:
                self.warnings.append(f"Empty file: {file_path}")

        return success

    def validate_required_sections(self) -> bool:
        """Validate that documentation files have required sections."""
        section_requirements = {
            "README.md": ["# PANTHER Framework", "## Quick Start", "## Architecture"],
            "plugins/README.md": [
                "# PANTHER Plugin System",
                "## Plugin Categories",
                "## Quick Start",
            ],
            "plugins/services/README.md": [
                "# PANTHER Service Plugins",
                "## Service Categories",
                "## Quick Start",
            ],
            "plugins/protocols/README.md": [
                "# PANTHER Protocol Plugins",
                "## Protocol Categories",
                "## Quick Start",
            ],
            "plugins/environments/README.md": [
                "# PANTHER Environment Plugins",
                "## Environment Categories",
                "## Quick Start",
            ],
        }

        success = True
        for file_path, required_sections in section_requirements.items():
            full_path = self.panther_root / file_path
            if full_path.exists():
                content = full_path.read_text()
                for section in required_sections:
                    if section not in content:
                        self.errors.append(
                            f"Missing section '{section}' in {file_path}"
                        )
                        success = False

        return success

    def validate_cross_references(self) -> bool:
        """Validate that internal links point to existing files."""
        success = True

        for readme_file in self.panther_root.rglob("README.md"):
            content = readme_file.read_text()

            # Find markdown links: [text](path)
            link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
            links = re.findall(link_pattern, content)

            for link_text, link_path in links:
                # Skip external links
                if link_path.startswith(("http://", "https://", "mailto:")):
                    continue

                # Skip anchor links
                if link_path.startswith("#"):
                    continue

                # Resolve relative path
                target_path = (readme_file.parent / link_path).resolve()

                if not target_path.exists():
                    self.errors.append(
                        f"Broken link in {readme_file.relative_to(self.panther_root)}: {link_path}"
                    )
                    success = False

        return success

    def validate_mkdocs_compatibility(self) -> bool:
        """Validate compatibility with mkdocs generation."""
        success = True

        # Check for conflicting index.md files
        for index_file in self.plugins_root.rglob("index.md"):
            parent_dir = index_file.parent
            readme_file = parent_dir / "README.md"

            if readme_file.exists():
                self.warnings.append(
                    f"Both index.md and README.md exist in {parent_dir.relative_to(self.panther_root)}"
                )

        return success

    def report_results(self, results: dict[str, bool]) -> None:
        """Print validation results."""
        print("🔍 PANTHER Documentation Validation Results")
        print("=" * 50)

        for check, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} {check.replace('_', ' ').title()}")

        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors and not self.warnings:
            print("\n🎉 All documentation validation checks passed!")

        overall_success = all(results.values()) and not self.errors
        return overall_success


def main():
    """Main validation entry point."""
    panther_root = Path(__file__).parent / "panther"

    if not panther_root.exists():
        print(f"❌ Error: panther directory not found at {panther_root}")
        return False

    validator = DocumentationValidator(panther_root)
    results = validator.validate_all()
    success = validator.report_results(results)

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
