from typing import Dict, List, Union
#!/usr/bin/env python3
"""
PANTHER Documentation Link Validator

This script verifies and can auto-fix links in Markdown files across the PANTHER codebase.
It checks both internal links (relative file paths) and external URLs, reporting any issues found.

Usage:
    python verify_links.py [--autofix] [--check-external]

Options:
    --autofix       Automatically fix detected issues when possible
    --check-external Check external URLs (might be slow)
"""

import os
import re
import sys
import argparse
from pathlib import Path
import urllib.parse
import yaml
from dataclasses import dataclass
from enum import Enum
import concurrent.futures

# Try to import requests for external URL validation
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Constants
REPO_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_MKDOCS_CONFIG = REPO_ROOT / "mkdocs.yml"
DOCS_DIR = "docs"  # Default docs directory used by MkDocs
GITHUB_REPO_URL = "https://github.com/ElNiak/PANTHER"
MAX_EXTERNAL_CHECK_THREADS = 5
EXTERNAL_TIMEOUT_SECONDS = 5

# Markdown link regex pattern - matches [text](link) format
# Group 1: Link text, Group 2: URL or path
LINK_PATTERN = r"\[([^\]]+)\]\(([^)]+)\)"
# Anchor pattern - matches headings in Markdown files (e.g., # Heading)
HEADING_PATTERN = r"^(#{1,6})\s+(.+?)(?:\s+\{#([a-z0-9_-]+)\})?\s*$"
# Image pattern - matches ![alt](image) format
IMAGE_PATTERN = r"!\[([^\]]*)\]\(([^)]+)\)"

class LinkType(Enum):
    """Enumeration of link types."""

    INTERNAL = "internal"  # Links to files within the repository
    ANCHOR = "anchor"  # Fragment/anchor links within a file
    EXTERNAL = "external"  # Links to external resources
    IMAGE = "image"  # Image references

class LinkStatus(Enum):
    """Enumeration of link validation status."""

    OK = "OK"  # Link is valid
    BROKEN = "BROKEN"  # Link is broken (file not found, etc.)
    REDIRECT = "REDIRECT"  # External link redirects to another URL
    ANCHOR_MISSING = "ANCHOR_MISSING"  # Anchor does not exist in target file
    UNFIXABLE = "UNFIXABLE"  # Cannot automatically fix the issue
    FIXED = "FIXED"  # Issue was automatically fixed
    UNVALIDATED = "UNVALIDATED"  # Link has not been validated (e.g., external links when --check-external not used)

@dataclass
class LinkInfo:
    """Information about a link found in a Markdown file."""

    source_file: Path
    link_text: str
    raw_link: str
    link_type: LinkType
    status: LinkStatus = LinkStatus.UNVALIDATED
    target_file: Optional[Path] = None
    anchor: Optional[str] = None
    fixed_link: Optional[str] = None
    message: Optional[str] = None
    line_number: Optional[int] = None

class LinkValidator:
    """Validates and fixes links in Markdown files."""

    def __init__(
        self,
        root_dir: Path,
        docs_dir: str = DOCS_DIR,
        autofix: bool = False,
        check_external: bool = False,
        ignore_readme_refs: bool = False):
        self.root_dir = root_dir
        self.docs_dir = docs_dir
        self.autofix = autofix
        self.check_external = check_external
        self.ignore_readme_refs = ignore_readme_refs
        self.mkdocs_config = None
        self.external_cache: Dict[str, LinkStatus] = (
            {}
        )  # Cache external URL validation results
        self.markdown_files: List[Path] = []
        self.link_issues: List[LinkInfo] = []
        self.fixed_count = 0
        self.unfixable_count = 0
        self.total_links = 0

        # Specific links to ignore in README.md
        self.readme_ignored_links = [
            "elniak.github.io/PANTHER",
            "10.1145/3488660.3493803",
            "10.1007/978-3-319-99725-4_4",
            "SAS18.pdf",
            "10.1145/3192366.3192414",
            "10.23919/FMCAD.2018.8603008",
            "FMCAD18.pdf",
            "10.1145/2908080.2908118",
            "10.1109/FMCAD.2016.7886668",
            "SIGCOMM19.pdf",
        ]

    def load_mkdocs_config(self, config_path: Path = DEFAULT_MKDOCS_CONFIG) -> dict:
        """Load MkDocs configuration from the specified file."""
        try:
            with open(config_path, encoding="utf-8") as file:
                self.mkdocs_config = yaml.safe_load(file)
                if "docs_dir" in self.mkdocs_config:
                    self.docs_dir = self.mkdocs_config["docs_dir"]
                return self.mkdocs_config
        except Exception as e:
            print(f"Warning: Failed to load MkDocs config from {config_path}: {e}")
            return {}

    def find_markdown_files(self) -> List[Path]:
        """Find all Markdown files in the project."""
        # Exclude node_modules, venv, and other directories that should be ignored
        ignore_patterns = [
            "**/node_modules/**",
            "**/.git/**",
            "**/.venv*/**",
            "**/venv*/**",
            "**/build/**",
            "**/dist/**",
            "**/__pycache__/**",
            "**/submodules/**",
            "**/.venv-10/**",
            "**/site-packages/**",
            "**/templates/**",
            ".venv-*/**",
            "**/licenses/**",
            "**/panther_ivy/submodules/**",
            "**/panther_ivy/test/**",
            "**/panther_ivy/ivy/**",
            "**/panther_ivy/doc/**",
            "**/panther_ivy/examples/**",
        ]

        # Start with an empty list of files
        markdown_files = []

        # Walk through the directory
        for path in self.root_dir.rglob("*.md"):
            # Check if path matches any ignore pattern
            if not any(path.match(pattern) for pattern in ignore_patterns):
                markdown_files.append(path)

        self.markdown_files = markdown_files
        print(f"Found {len(markdown_files)} Markdown files to check")
        return markdown_files

    def slugify_heading(self, heading: str) -> str:
        """Mimic MkDocs/Python Markdown's slugification logic for headings."""
        # Convert to lowercase
        slug = heading.lower()
        # Replace spaces with hyphens
        slug = slug.replace(" ", "-")
        # Remove non-alphanumeric characters (except hyphens)
        slug = re.sub(r"[^\w\-]", "", slug)
        # Replace consecutive hyphens with a single hyphen
        slug = re.sub(r"-+", "-", slug)
        # Remove leading and trailing hyphens
        slug = slug.strip("-")
        return slug

    def extract_headings(self, file_content: str) -> Dict[str, str]:
        """Extract heading anchors from a Markdown file."""
        headings = {}
        for line in file_content.splitlines():
            match = re.match(HEADING_PATTERN, line)
            if match:
                level, text, explicit_id = match.groups()
                if explicit_id:
                    # If an explicit ID is provided, use it
                    headings[explicit_id] = text
                else:
                    # Otherwise, generate a slug from the heading text
                    slug = self.slugify_heading(text)
                    headings[slug] = text
        return headings

    def normalize_path(
        self, base_path: Path, link_path: str
    ) -> tuple[Path, Optional[str]]:
        """Normalize a relative link path to an absolute project path."""
        # Safety check for None or empty path
        if not link_path:
            return None, None

        # Extract anchor if present
        url_parts = urllib.parse.urlparse(link_path)
        path_part = url_parts.path
        anchor = url_parts.fragment if url_parts.fragment else None

        # Handle absolute links within the repository
        if path_part.startswith("/"):
            # Treat as absolute from repository root
            result_path = self.root_dir / path_part.lstrip("/")
        else:
            # Treat as relative to the base file
            result_path = (base_path.parent / path_part).resolve()

        return result_path, anchor

    def should_ignore_link(self, link_info: LinkInfo) -> bool:
        """Check if a link should be ignored based on exclusion patterns."""
        # Check if it's in README.md and in our ignored links list
        if self.ignore_readme_refs and link_info.source_file.name == "README.md":
            if link_info.raw_link in self.readme_ignored_links:
                return True

            # Also check DOI patterns
            if link_info.raw_link and link_info.raw_link.startswith("10."):
                return True

            # Check PDF file references
            if link_info.raw_link and link_info.raw_link.endswith(".pdf"):
                return True

        return False

    def check_internal_link(self, link_info: LinkInfo) -> LinkStatus:
        """Check if an internal link points to a valid file."""
        # Check if this link should be ignored
        if self.should_ignore_link(link_info):
            link_info.message = "Excluded by pattern rule"
            return LinkStatus.OK

        try:
            if link_info.target_file and link_info.target_file.exists():
                # If there's an anchor, check if it exists in the target file
                if link_info.anchor:
                    with open(link_info.target_file, encoding="utf-8") as file:
                        content = file.read()
                        headings = self.extract_headings(content)
                        if link_info.anchor not in headings:
                            link_info.message = f"Anchor '{link_info.anchor}' not found in {link_info.target_file.relative_to(self.root_dir)}"
                            return LinkStatus.ANCHOR_MISSING
                return LinkStatus.OK
            else:
                if not link_info.target_file:
                    link_info.message = "Invalid target file: None"
                else:
                    link_info.message = f"File not found: {link_info.target_file.relative_to(self.root_dir) if link_info.target_file.is_relative_to(self.root_dir) else link_info.target_file}"
                return LinkStatus.BROKEN
        except Exception as e:
            link_info.message = f"Error validating link: {str(e)}"
            return LinkStatus.BROKEN

    def check_external_link(self, link_info: LinkInfo) -> LinkStatus:
        """Check if an external link is valid."""
        if not REQUESTS_AVAILABLE:
            link_info.message = (
                "Package 'requests' not available, skipping external link check"
            )
            return LinkStatus.UNVALIDATED

        if not self.check_external:
            return LinkStatus.UNVALIDATED

        # Check if URL was already validated
        if link_info.raw_link in self.external_cache:
            link_info.message = "Using cached result"
            return self.external_cache[link_info.raw_link]

        try:
            # Make a HEAD request to avoid downloading the entire content
            response = requests.head(
                link_info.raw_link,
                allow_redirects=True,
                timeout=EXTERNAL_TIMEOUT_SECONDS,
            )

            if response.status_code >= 400:
                # Try with a GET request if HEAD is not allowed
                response = requests.get(
                    link_info.raw_link,
                    allow_redirects=True,
                    timeout=EXTERNAL_TIMEOUT_SECONDS,
                    stream=True,
                )
                # Close the connection without downloading the content
                response.close()

            if response.status_code >= 400:
                link_info.message = f"HTTP status code: {response.status_code}"
                status = LinkStatus.BROKEN
            elif response.history:
                link_info.message = f"Redirects to: {response.url}"
                status = LinkStatus.REDIRECT
            else:
                status = LinkStatus.OK

            # Cache the result
            self.external_cache[link_info.raw_link] = status
            return status

        except Exception as e:
            link_info.message = f"Error checking URL: {str(e)}"
            self.external_cache[link_info.raw_link] = LinkStatus.BROKEN
            return LinkStatus.BROKEN

    def extract_links(self, file_path: Path) -> List[LinkInfo]:
        """Extract all links from a Markdown file."""
        links = []
        try:
            with open(file_path, encoding="utf-8") as file:
                content = file.read()
                line_number = 1

                # Process normal links
                for match in re.finditer(LINK_PATTERN, content):
                    line_number += content[: match.start()].count("\n")
                    link_text, link_url = match.groups()

                    # Skip links that are just anchors on the same page
                    if link_url.startswith("#"):
                        anchor = link_url[1:]
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=link_text,
                            raw_link=link_url,
                            link_type=LinkType.ANCHOR,
                            target_file=file_path,
                            anchor=anchor,
                            line_number=line_number,
                        )
                        links.append(link_info)
                        continue

                    # Determine link type
                    if link_url.startswith(("http://", "https://", "ftp://")):
                        # Check if it's a GitHub link to this repository
                        if (
                            link_url.startswith(GITHUB_REPO_URL)
                            and "/blob/" in link_url
                        ):
                            try:
                                # Extract the path within the repository
                                repo_path = link_url.split("/blob/")[1].split("/", 1)[1]
                                if "#" in repo_path:
                                    repo_path, anchor = repo_path.split("#", 1)
                                else:
                                    anchor = None

                                target_file = self.root_dir / repo_path
                                link_info = LinkInfo(
                                    source_file=file_path,
                                    link_text=link_text,
                                    raw_link=link_url,
                                    link_type=LinkType.INTERNAL,
                                    target_file=target_file,
                                    anchor=anchor,
                                    line_number=line_number,
                                    message="GitHub URL can be converted to relative link",
                                )
                            except Exception:
                                # If parsing fails, treat as external link
                                link_info = LinkInfo(
                                    source_file=file_path,
                                    link_text=link_text,
                                    raw_link=link_url,
                                    link_type=LinkType.EXTERNAL,
                                    line_number=line_number,
                                )
                        else:
                            # Regular external link
                            link_info = LinkInfo(
                                source_file=file_path,
                                link_text=link_text,
                                raw_link=link_url,
                                link_type=LinkType.EXTERNAL,
                                line_number=line_number,
                            )
                    # Special case for DOI links in README.md (common in academic references)
                    elif file_path.name == "README.md" and re.match(
                        r"^10\.\d+/", link_url
                    ):
                        # Treat DOIs as external links
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=link_text,
                            raw_link=f"https://doi.org/{link_url}",  # Convert to proper DOI URL
                            link_type=LinkType.EXTERNAL,
                            line_number=line_number,
                            message="Academic DOI reference",
                        )
                    # Special case for PDF files referenced in README.md academic section
                    elif file_path.name == "README.md" and link_url.endswith(".pdf"):
                        # Treat PDFs as special case
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=link_text,
                            raw_link=link_url,
                            link_type=LinkType.EXTERNAL,  # Treat as external to bypass validation
                            line_number=line_number,
                            message="Academic PDF reference",
                        )
                    # Special case for domain without protocol
                    elif link_url.startswith("elniak.github.io/"):
                        # Fix the URL by adding https://
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=link_text,
                            raw_link=f"https://{link_url}",
                            link_type=LinkType.EXTERNAL,
                            line_number=line_number,
                            message="Missing protocol in URL",
                        )
                    else:
                        # Internal link
                        target_file, anchor = self.normalize_path(file_path, link_url)
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=link_text,
                            raw_link=link_url,
                            link_type=LinkType.INTERNAL,
                            target_file=target_file,
                            anchor=anchor,
                            line_number=line_number,
                        )

                    links.append(link_info)
                    content = content[match.end() :]

                # Process image links
                for match in re.finditer(IMAGE_PATTERN, content):
                    line_number += content[: match.start()].count("\n")
                    alt_text, image_path = match.groups()

                    if image_path.startswith(("http://", "https://")):
                        # External image
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=alt_text,
                            raw_link=image_path,
                            link_type=LinkType.IMAGE,
                            line_number=line_number,
                        )
                    else:
                        # Internal image
                        target_file, _ = self.normalize_path(file_path, image_path)
                        link_info = LinkInfo(
                            source_file=file_path,
                            link_text=alt_text,
                            raw_link=image_path,
                            link_type=LinkType.IMAGE,
                            target_file=target_file,
                            line_number=line_number,
                        )

                    links.append(link_info)
                    content = content[match.end() :]

            return links
        except Exception as e:
            print(f"Error extracting links from {file_path}: {e}")
            return []

    def validate_links(self) -> None:
        """Validate all links in all markdown files."""
        all_links = []
        ignored_links = []

        # Extract all links from all files
        for file_path in self.markdown_files:
            file_links = self.extract_links(file_path)

            # Filter out links that should be ignored
            for link in file_links:
                if self.should_ignore_link(link):
                    ignored_links.append(link)
                    link.status = LinkStatus.OK
                else:
                    all_links.append(link)

        self.total_links = len(all_links) + len(ignored_links)
        print(
            f"Found {self.total_links} links to validate ({len(ignored_links)} ignored)"
        )

        # Validate all internal links
        for link_info in all_links:
            if link_info.link_type in [
                LinkType.INTERNAL,
                LinkType.IMAGE,
                LinkType.ANCHOR,
            ]:
                link_info.status = self.check_internal_link(link_info)
                if link_info.status != LinkStatus.OK:
                    self.link_issues.append(link_info)

        # Validate external links in parallel if requested
        if self.check_external:
            external_links = [l for l in all_links if l.link_type == LinkType.EXTERNAL]
            print(f"Checking {len(external_links)} external links...")

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_EXTERNAL_CHECK_THREADS
            ) as executor:
                future_to_link = {
                    executor.submit(self.check_external_link, link): link
                    for link in external_links
                }
                for future in concurrent.futures.as_completed(future_to_link):
                    link = future_to_link[future]
                    try:
                        link.status = future.result()
                        if (
                            link.status != LinkStatus.OK
                            and link.status != LinkStatus.UNVALIDATED
                        ):
                            self.link_issues.append(link)
                    except Exception as e:
                        link.message = f"Exception during validation: {str(e)}"
                        link.status = LinkStatus.BROKEN
                        self.link_issues.append(link)

        # Try to fix issues if autofix is enabled
        if self.autofix:
            self.fix_issues()

    def fix_issues(self) -> None:
        """Attempt to fix identified issues."""
        files_to_update = (
            {}
        )  # Map of file path -> list of (old_text, new_text) replacements

        for link_info in self.link_issues:
            fixed = False

            # Try to fix GitHub URLs to relative links
            if (
                link_info.link_type == LinkType.INTERNAL
                and link_info.raw_link.startswith(GITHUB_REPO_URL)
            ):
                try:
                    # Calculate relative path from source file to target file
                    source_dir = link_info.source_file.parent
                    rel_path = os.path.relpath(link_info.target_file, source_dir)

                    # Create the new link
                    new_link = rel_path
                    if link_info.anchor:
                        new_link += f"#{link_info.anchor}"

                    link_info.fixed_link = new_link
                    old_text = f"[{link_info.link_text}]({link_info.raw_link})"
                    new_text = f"[{link_info.link_text}]({new_link})"

                    if link_info.source_file not in files_to_update:
                        files_to_update[link_info.source_file] = []
                    files_to_update[link_info.source_file].append((old_text, new_text))

                    link_info.status = LinkStatus.FIXED
                    self.fixed_count += 1
                    fixed = True
                except Exception:
                    link_info.message = "Failed to convert GitHub URL to relative link"

            # Fix links to directories by adding index.md
            if (
                not fixed
                and link_info.link_type == LinkType.INTERNAL
                and link_info.status == LinkStatus.BROKEN
            ):
                potential_index = link_info.target_file / "index.md"
                potential_readme = link_info.target_file / "README.md"

                if potential_index.exists():
                    # Fix by appending index.md to the path
                    new_link = f"{link_info.raw_link.rstrip('/')}/index.md"
                    link_info.fixed_link = new_link
                    old_text = f"[{link_info.link_text}]({link_info.raw_link})"
                    new_text = f"[{link_info.link_text}]({new_link})"

                    if link_info.source_file not in files_to_update:
                        files_to_update[link_info.source_file] = []
                    files_to_update[link_info.source_file].append((old_text, new_text))

                    link_info.status = LinkStatus.FIXED
                    self.fixed_count += 1
                    fixed = True
                elif potential_readme.exists():
                    # Fix by appending README.md to the path
                    new_link = f"{link_info.raw_link.rstrip('/')}/README.md"
                    link_info.fixed_link = new_link
                    old_text = f"[{link_info.link_text}]({link_info.raw_link})"
                    new_text = f"[{link_info.link_text}]({new_link})"

                    if link_info.source_file not in files_to_update:
                        files_to_update[link_info.source_file] = []
                    files_to_update[link_info.source_file].append((old_text, new_text))

                    link_info.status = LinkStatus.FIXED
                    self.fixed_count += 1
                    fixed = True

            # Mark as unfixable if couldn't be fixed
            if not fixed:
                link_info.status = LinkStatus.UNFIXABLE
                self.unfixable_count += 1

        # Apply all updates
        for file_path, replacements in files_to_update.items():
            try:
                with open(file_path, encoding="utf-8") as file:
                    content = file.read()

                # Apply all replacements
                for old_text, new_text in replacements:
                    content = content.replace(old_text, new_text)

                # Write updated content back to file
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)

                print(f"✅ Updated {file_path.name} with {len(replacements)} fixes")
            except Exception as e:
                print(f"❌ Error updating {file_path}: {e}")

    def print_report(self) -> None:
        """Print a report of all link issues."""
        if not self.link_issues:
            print("\n✅ No link issues found!")
            return

        print(
            f"\nFound {len(self.link_issues)} link issues out of {self.total_links} total links."
        )
        if self.autofix:
            print(f"Automatically fixed: {self.fixed_count}")
            print(f"Unable to fix: {self.unfixable_count}")

        # Group issues by type
        broken_internal = []
        broken_anchors = []
        redirects = []
        broken_external = []

        for link in self.link_issues:
            if link.link_type == LinkType.INTERNAL and link.status in [
                LinkStatus.BROKEN,
                LinkStatus.UNFIXABLE,
            ]:
                broken_internal.append(link)
            elif link.status == LinkStatus.ANCHOR_MISSING:
                broken_anchors.append(link)
            elif link.status == LinkStatus.REDIRECT:
                redirects.append(link)
            elif (
                link.link_type == LinkType.EXTERNAL and link.status == LinkStatus.BROKEN
            ):
                broken_external.append(link)

        # Print each category
        if broken_internal:
            print("\n📁 BROKEN INTERNAL LINKS:")
            for link in broken_internal:
                rel_source = link.source_file.relative_to(self.root_dir)
                print(
                    f"  • {rel_source}:{link.line_number} - [{link.link_text}]({link.raw_link})"
                )
                print(f"    → {link.message}")

        if broken_anchors:
            print("\n🔗 MISSING ANCHORS:")
            for link in broken_anchors:
                rel_source = link.source_file.relative_to(self.root_dir)
                print(
                    f"  • {rel_source}:{link.line_number} - [{link.link_text}]({link.raw_link})"
                )
                print(f"    → {link.message}")

        if redirects:
            print("\n🔄 REDIRECTED LINKS:")
            for link in redirects:
                rel_source = link.source_file.relative_to(self.root_dir)
                print(
                    f"  • {rel_source}:{link.line_number} - [{link.link_text}]({link.raw_link})"
                )
                print(f"    → {link.message}")

        if broken_external:
            print("\n🌐 BROKEN EXTERNAL LINKS:")
            for link in broken_external:
                rel_source = link.source_file.relative_to(self.root_dir)
                print(
                    f"  • {rel_source}:{link.line_number} - [{link.link_text}]({link.raw_link})"
                )
                print(f"    → {link.message}")

def suggest_cross_links(mkdocs_config: dict) -> Dict[Path, List[str]]:
    """Suggest cross-links between related documentation files."""
    # This would analyze the project structure and generate suggestions for
    # links that should be added between related documents
    # For simplicity, this is just a placeholder function
    return {}

def update_mkdocs_nav(root_dir: Path, mkdocs_config: dict) -> dict:
    """Update MkDocs navigation with all Markdown files in the project."""
    # This would scan all Markdown files and build a proper navigation structure
    # For simplicity, this is just a placeholder function
    return mkdocs_config

def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(description="PANTHER Documentation Link Validator")
    parser.add_argument(
        "--autofix",
        action="store_true",
        help="Automatically fix detected issues when possible",
    )
    parser.add_argument(
        "--check-external",
        action="store_true",
        help="Check external URLs (might be slow)",
    )
    parser.add_argument(
        "--ignore-readme-refs",
        action="store_true",
        help="Ignore academic references in README.md (DOIs, PDFs)",
    )
    args = parser.parse_args()

    print("🔍 PANTHER Documentation Link Validator")
    print("=" * 50)

    validator = LinkValidator(
        root_dir=REPO_ROOT,
        autofix=args.autofix,
        check_external=args.check_external,
        ignore_readme_refs=args.ignore_readme_refs,
    )

    # Load MkDocs configuration
    validator.load_mkdocs_config()

    # Find all Markdown files
    validator.find_markdown_files()

    # Check all links
    validator.validate_links()

    # Print report of issues
    validator.print_report()

    # Exit with appropriate code
    if validator.link_issues and (not args.autofix or validator.unfixable_count > 0):
        print("\n❌ Link validation failed. Please fix the issues listed above.")
        sys.exit(1)
    else:
        if validator.fixed_count > 0:
            print(f"\n✅ Successfully fixed {validator.fixed_count} issues.")
        else:
            print("\n✅ No issues found or all issues were fixed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
