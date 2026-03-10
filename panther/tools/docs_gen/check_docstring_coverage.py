#!/usr/bin/env python3
"""Check docstring coverage for __init__.py files.

Ensures that module-level docstrings exist in __init__.py files
across the panther package. Used in CI to maintain documentation quality.
"""

import ast
import sys
from pathlib import Path


def check_docstring_coverage(package_dir: str = "panther", threshold: float = 0.95):
    """Check that __init__.py files have module docstrings.

    Args:
        package_dir: Root package directory to scan.
        threshold: Minimum ratio of files with docstrings (0.0 to 1.0).

    Returns:
        Tuple of (passed: bool, ratio: float, missing: list[str])
    """
    root = Path(package_dir)
    init_files = sorted(root.rglob("__init__.py"))

    # Skip panther_ivy submodule
    init_files = [f for f in init_files if "panther_ivy" not in f.parts]

    total = len(init_files)
    missing = []

    for init_file in init_files:
        try:
            source = init_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
            docstring = ast.get_docstring(tree)
            if not docstring or len(docstring.strip()) < 10:
                missing.append(str(init_file))
        except (SyntaxError, UnicodeDecodeError):
            missing.append(str(init_file))

    covered = total - len(missing)
    ratio = covered / total if total > 0 else 1.0

    return ratio >= threshold, ratio, missing


def main():
    """Run docstring coverage check."""
    import argparse

    parser = argparse.ArgumentParser(description="Check __init__.py docstring coverage")
    parser.add_argument(
        "--package", default="panther", help="Package directory to scan"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Minimum coverage ratio (default: 0.95)",
    )
    args = parser.parse_args()

    passed, ratio, missing = check_docstring_coverage(args.package, args.threshold)

    print(f"Docstring coverage: {ratio:.1%} ({len(missing)} files missing)")

    if missing:
        print("\nFiles missing docstrings:")
        for path in missing:
            print(f"  - {path}")

    if not passed:
        print(f"\nFAILED: Coverage {ratio:.1%} is below threshold {args.threshold:.0%}")
        sys.exit(1)
    else:
        print(f"\nPASSED: Coverage {ratio:.1%} meets threshold {args.threshold:.0%}")


if __name__ == "__main__":
    main()
