# PANTHER Documentation Generator Tools

This directory contains the automated tools for generating, building, and maintaining PANTHER's MkDocs-based documentation site. The tooling replaces manual build-dictionary maintenance with automated README discovery and mapping.

## Directory Structure

```bash
docs_gen/
    __init__.py                  # Package init; exports PantherSourceDiscovery, get_build_dict
    discover_sources.py          # Automated README discovery and build_dict generation
    generate_build_mapping.py    # Integration module for panther_builder.py
    generated_build_dict.py      # Auto-generated source-to-docs path mapping (do not edit)
    mkdocs.yml.bak               # Backup of MkDocs configuration
    INTEGRATION_INSTRUCTIONS.md  # Integration guide for panther_builder.py
    mkdocs/
        __init__.py              # Subpackage init; re-exports mkdocs tool modules
        automate_mkdocs.py       # MkDocs automation (nav generation, formatting, linting)
        docs_structure.py        # Documentation directory structure manager
        fix_encoding.py          # Detect and fix encoding issues in Markdown files
        fix_markdown_links.py    # Convert absolute links to project-root-relative links
        gen_ref_pages.py         # Auto-generate API reference pages (mkdocstrings recipe)
        generate_plugin_docs.py  # Extract plugin docs from README files into structured output
        mkdocs_all_import.py     # Import cleanup helper for mkdocs generation
        prepare_docs.py          # Create symlinks/copies of Markdown files into docs/
        template/
            index_template.md    # Jinja2 template for the docs index page
```

## How to Build Documentation

The primary entry point is `panther_builder.py`:

```bash
# Build the full documentation site
python panther_builder.py docs

# Serve documentation locally
python panther_builder.py serve-docs

# Deploy documentation
python panther_builder.py deploy-docs
```

## Root-Level Tools

### `discover_sources.py`

Automatically discovers `README.md` files across the repository and generates `build_dict` mappings that map source Markdown paths to their documentation output locations. Replaces manual maintenance of 85+ path entries.

```bash
python panther/tools/docs_gen/discover_sources.py --generate-build-dict
python panther/tools/docs_gen/discover_sources.py --analyze-structure
python panther/tools/docs_gen/discover_sources.py --validate-mappings
```

Key class: `PantherSourceDiscovery` -- performs AST-based Python module analysis, README categorization, and intelligent mapping generation.

### `generate_build_mapping.py`

Integration module that `panther_builder.py` calls to obtain the automated `build_dict`. Provides `get_build_dict()` and `get_automated_build_dict()` as the public API.

```python
from panther.tools.docs_gen.generate_build_mapping import get_build_dict

build_dict = get_build_dict()  # Returns Dict[str, str]
```

### `generated_build_dict.py`

Auto-generated dictionary mapping source file paths to their documentation output paths. This file is produced by `discover_sources.py` and should not be edited manually.

## MkDocs Tools (`mkdocs/`)

### `automate_mkdocs.py`

Automates MkDocs configuration: parses the project's Python modules, generates navigation structures, and manages formatting and linting integration.

### `docs_structure.py`

Manages the documentation directory layout. Creates and organizes the `docs/` directory hierarchy so that files end up in the correct MkDocs sections.

### `fix_encoding.py`

Scans Markdown files for encoding issues using `chardet` and converts them to UTF-8.

### `fix_markdown_links.py`

Rewrites links in Markdown files under `panther/` so that absolute paths (starting with `/`) become project-root-relative paths compatible with the MkDocs build.

### `gen_ref_pages.py`

Generates automatic API code-reference pages using the `mkdocstrings` recipe pattern. Integrates with `mkdocs_gen_files` to produce reference navigation.

### `generate_plugin_docs.py`

Extracts plugin documentation from `README.md` files across the plugin directories and organizes them into a coherent documentation structure suitable for MkDocs.

### `prepare_docs.py`

Prepares the `docs/` build directory by creating symlinks (or copies, on platforms without symlink support) from source Markdown files into the expected documentation tree.

### `mkdocs_all_import.py`

Helper for managing Python imports during MkDocs generation. Imports are removed before generation and restored afterward to avoid resolution issues.

## Documentation Workflow

1. **Discovery** -- `discover_sources.py` scans the repository for README files and produces `generated_build_dict.py`.
2. **Mapping** -- `generate_build_mapping.py` provides the build dict to `panther_builder.py`.
3. **Preparation** -- `prepare_docs.py` symlinks/copies source files into the `docs/` directory.
4. **Structure** -- `docs_structure.py` ensures the directory layout matches MkDocs expectations.
5. **Link Fixing** -- `fix_markdown_links.py` and `fix_encoding.py` normalize content.
6. **Reference Generation** -- `gen_ref_pages.py` and `generate_plugin_docs.py` produce API and plugin reference pages.
7. **Build** -- `automate_mkdocs.py` generates the final MkDocs configuration and the site is built.

Run the full pipeline with:

```bash
python panther_builder.py docs
```
