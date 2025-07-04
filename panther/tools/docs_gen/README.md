# PANTHER Documentation Generator Tools

!!! info "Documentation Automation"
    This directory contains automated tools for generating, validating, and maintaining PANTHER's comprehensive documentation ecosystem. These tools ensure documentation stays synchronized with code changes.

This directory contains tools for generating, validating, and maintaining documentation for the PANTHER project.

## Documentation Structure

The documentation is organized into the following main sections:

- **Getting Started** - Quick start guides, installation, and basic concepts
- **User Guide** - Configuration, workflows, and common use cases
- **Developer Guide** - Contributing guidelines and plugin development
- **Reference** - API references, plugin documentation, and configuration details
- **Project Information** - Changelog, license, and roadmap

## Key Tools

| Tool | Description |
|------|-------------|
| `scripts/collect_docs.py` | Main script for collecting, refining, and organizing documentation |
| `scripts/check_docs.py` | Validates documentation structure and links |
| `verify_links.py` | Verifies and fixes links in Markdown files |
| `add_cross_references.py` | Adds cross-references between related documents |
| `update_mkdocs_nav.py` | Updates the MkDocs navigation structure |
| `enhance_mkdocs_config.py` | Adds link checking plugins to MkDocs |
| `pre_commit_docs.py` | Pre-commit hook for documentation checks |
| `mkdocs/docs_structure.py` | Organizes documentation files |
| `mkdocs/mkdocs.yml.j2` | Jinja2 template for MkDocs configuration |

## How to Rebuild and Audit Docs Locally

!!! tip "Quick Documentation Update"
    Use `make docs` for a complete documentation rebuild, or individual scripts for targeted updates. Always run `docs-verify` after making documentation changes to catch broken links.

For a complete documentation update:

```bash
make docs
```

This single command:

1. Collects and refines documentation from across the repository (`docs-collect`)
2. Generates the documentation inventory (`docs-inventory`)
3. Verifies links and references (`docs-verify`)
4. Builds the MkDocs site and starts a local server (`mkdocs`)

### Individual Steps

You can run individual steps of the documentation process:

1. **Collect and refine documentation**:

   ```bash
   make docs-collect
   ```

   This runs `scripts/collect_docs.py` which:
   - Discovers all Markdown files in the repository
   - Organizes them into the correct structure in `docs/`
   - Refines content (fixes headings, code blocks, links, etc.)
   - Updates the MkDocs navigation template

2. **Generate plugin inventory**:

   ```bash
   make docs-inventory
   ```

3. **Verify documentation**:

   ```bash
   make docs-verify
   ```

4. **Build MkDocs site**:

   ```bash
   make mkdocs
   ```

### Documentation Refinements

The `collect_docs.py` script performs several refinements:

- Ensures each file has a proper top-level heading matching the filename
- Adds language identifiers to code blocks
- Replaces vague time references with specific dates
- Fixes internal links to work in the new structure
- Verifies anchor links in Markdown files
- Normalizes formatting and style

### Documentation Workflow

1. **Collection**: Source markdown files are discovered and mapped to the docs structure
2. **Refinement**: Content is improved by fixing headings, links, and code blocks
3. **Organization**: Files are copied to their proper location in the docs/ directory
4. **Navigation**: MkDocs navigation is generated from the organized structure
5. **Validation**: Links, anchors, and references are verified
6. **Building**: MkDocs builds the final site

## Documentation Guides

- [Documentation Workflow](documentation_WORKFLOW.md): Step-by-step guide for updating documentation
- [Documentation Integration](documentation_integration.md): How all the documentation tools work together

## Directory Structure

- `mkdocs/` - Scripts for MkDocs integration and API documentation generation
- `graph/` - Diagrams and visual documentation
- `readme-res/` - Resources for README files

## Pre-commit Integration

To automatically check documentation when committing changes:

```bash
pre-commit install
```

## Continuous Integration

Documentation is automatically checked in CI using the configuration in `documentation-ci.yml`.

## For More Information

See the [Documentation Workflow](documentation_WORKFLOW.md) guide for detailed instructions on maintaining documentation.
