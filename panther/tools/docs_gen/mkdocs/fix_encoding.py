#!/usr/bin/env python3
"""Script to check and fix encoding issues in markdown files."""

from pathlib import Path

import chardet


def fix_file_encoding(file_path):
    """Detect the encoding of a file and convert it to UTF-8 if needed.

    Args:
        file_path (str): Path to the file to fix

    Returns:
        bool: True if the file was fixed, False otherwise
    """
    print(f"Checking {file_path}")

    try:
        # Try to read as UTF-8 first
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return False  # No need to fix
    except UnicodeDecodeError:
        # If that fails, detect encoding and convert
        with open(file_path, "rb") as f:
            raw_data = f.read()

        result = chardet.detect(raw_data)
        encoding = result["encoding"]
        confidence = result["confidence"]

        print(
            f"  Detected encoding: {encoding} with {confidence * 100:.1f}% confidence"
        )

        if encoding and encoding.lower() != "utf-8":
            try:
                content = raw_data.decode(encoding)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  Fixed: Converted from {encoding} to UTF-8")
                return True
            except Exception as e:
                print(f"  Error converting {file_path}: {e}")
                return False
        return False


def main():
    """Find and fix all markdown files with encoding issues."""
    repo_dir = Path.cwd()

    # Find all markdown files
    md_files = list(repo_dir.glob("**/*.md"))
    fixed_files = []
    error_files = []

    for md_file in md_files:
        try:
            if fix_file_encoding(md_file):
                fixed_files.append(md_file)
        except Exception as e:
            print(f"Error processing {md_file}: {e}")
            error_files.append((md_file, str(e)))

    # Print report
    print("\nEncoding Fix Report:")
    print(f"Total files checked: {len(md_files)}")
    print(f"Files fixed: {len(fixed_files)}")
    print(f"Files with errors: {len(error_files)}")

    if fixed_files:
        print("\nFixed files:")
        for file in fixed_files:
            print(f"  {file}")

    if error_files:
        print("\nFiles with errors:")
        for file, error in error_files:
            print(f"  {file}: {error}")


if __name__ == "__main__":
    main()
