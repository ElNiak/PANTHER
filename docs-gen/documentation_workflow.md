# PANTHER Documentation Workflow

This guide explains how to maintain and update documentation in the PANTHER project using the improved documentation system.

## Overview

PANTHER documentation consists of several components organized in a structured hierarchy:

1. **Getting Started** - Quick start guides, installation, and basic concepts
2. **User Guide** - Configuration, workflows, and common use cases
3. **Developer Guide** - Contributing guidelines and plugin development
4. **Reference** - API references, plugin documentation, and configuration details
5. **Project Information** - Changelog, license, and roadmap

The documentation is maintained in source markdown files throughout the repository and collected into an organized structure in the `docs/` directory.

For more detailed information about how all the documentation tools integrate, see [Documentation Integration Guide](documentation_integration.md).

## Key Tools for Documentation Management

| Tool | Purpose |
|------|---------|
| `scripts/collect_docs.py` | Main script for collecting, refining, and organizing documentation |
| `scripts/check_docs.py` | Validates documentation structure, links, and anchors |
| `docs-gen/mkdocs/mkdocs.yml.j2` | Jinja2 template for MkDocs configuration |
| `verify_links.py` | Verifies and fixes links in Markdown files |
| `add_cross_references.py` | Adds "See Also" sections to create cross-references between docs |
| `gen_ref_pages.py` | Generates API reference pages from docstrings |
| `generate_plugin_docs.py` | Generates documentation for plugins |

## Documentation Workflow

You can use the all-in-one documentation build command:

```bash
make docs
```

This command runs the entire documentation process from collection to building.

The process can also be broken down into individual steps:

1. **Collect and Refine Documentation**: 
   ```bash
   make docs-collect
   ```
   This runs the `scripts/collect_docs.py` script which:
   - Discovers all markdown files in the repository
   - Maps them to the proper location in the docs structure
   - Copies and refines the content (fixing headings, links, etc.)
   - Rewrites internal links to work in the new structure
   - Verifies links and anchors
   - Updates the MkDocs navigation structure

2. **Generate Documentation Inventory**:
   ```bash
   make docs-inventory
   ```
   Updates the plugin inventory for reference.

3. **Verify Documentation**:
   ```bash
   make docs-verify
   ```
   Checks for broken links, missing anchors, and other issues.

4. **Build and Preview**:
   ```bash
   make mkdocs
   ```
   Builds the documentation with MkDocs and starts a local server.

5. **Check Documentation Manually**:
   ```bash
   python scripts/check_docs.py
   ```
   Performs a thorough check of the documentation for common issues.

## Writing Documentation Best Practices

1. **Source Files**: Always edit the source markdown files in their original locations, not the copied files in `docs/`.
2. **Headings**: Start with a single H1 heading (`# Title`) that matches the filename.
3. **Code Blocks**: Always specify a language for fenced code blocks (```python).
4. **Links**: Use relative links to other files in the repository.
5. **Dates**: Use specific dates instead of vague terms like "recently" or "today".

## Pre-Commit Hook

For contributors, we've also added a pre-commit hook that automatically checks documentation when you commit changes. To enable it, run:

```bash
pre-commit install
```

## Detailed Steps

### 1. Writing Documentation

Place markdown files in appropriate locations:

- Core documentation goes in the root directory
- Plugin documentation goes in the plugin directories
- Development guides should be named `development.md` in the respective directories

### 2. Adding Cross-References

Run the following command to add cross-references between documents:

```bash
python docs-gen/add_cross_references.py
```

This will add "See Also" sections to documentation files, linking related documents.

### 3. Verifying Links

Run the following command to check for broken links:

```bash
python docs-gen/verify_links.py
```

To automatically fix issues when possible, use the `--autofix` flag:

```bash
python docs-gen/verify_links.py --autofix
```

To check external links as well (may be slow):

```bash
python docs-gen/verify_links.py --check-external
```

### 4. Updating Navigation

Run the following command to update the MkDocs navigation structure:

```bash
python docs-gen/update_mkdocs_nav.py
```

This will scan all markdown files and update the `nav` section in `mkdocs.yml`.

### 5. Generating API Documentation

API documentation is generated from docstrings in the code. Run:

```bash
python docs-gen/mkdocs/gen_ref_pages.py
```

### 6. Building and Previewing

Build the documentation to check for any issues:

```bash
mkdocs build --strict
```

Preview the documentation locally:

```bash
mkdocs serve
```

## Continuous Integration

The documentation is automatically validated in CI using the following workflow:

1. Verify internal links with `verify_links.py`
2. Build the documentation with `mkdocs build --strict`
3. (Optional) Check external links on scheduled runs

## Best Practices

### Links

- Use relative links for internal documents
- Avoid linking to specific anchors unless necessary (they may change)
- Use proper code blocks with language specification (e.g., ```python)

### Cross-References

- Add "See Also" sections at the end of documents
- Link related documents together
- Link plugin documentation to relevant API sections

### MkDocs Navigation

- Organize documents logically
- Use consistent naming
- Ensure every document appears exactly once in the navigation

## Troubleshooting

### Broken Links

Use the `verify_links.py` script to identify and fix broken links:

```bash
python docs-gen/verify_links.py --autofix
```

### Navigation Issues

If documents are missing from the navigation, run:

```bash
python docs-gen/update_mkdocs_nav.py
```

### Build Errors

If you encounter errors when building the documentation, check:

1. The MkDocs configuration in `mkdocs.yml`
2. Markdown syntax in your documents
3. The console output for specific error messages
