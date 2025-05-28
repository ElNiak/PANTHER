# Documentation System

This document provides an overview of the PANTHER documentation system and how to use it.

## Documentation Structure

PANTHER documentation is organized in the following structure:

- `docs/` - The generated documentation directory (git-ignored)
- `docs-gen/` - Documentation generation tools and templates
- Source markdown files throughout the repository

## Rebuilding and Auditing Documentation

To rebuild and audit the documentation locally, follow these steps:

### 1. Collect and Process Documentation

```bash
python scripts/collect_docs.py
```

This script:

- Discovers all markdown files in the repository
- Maps them to the proper location in the docs/ directory
- Copies and refines the content for accuracy and clarity
- Rewrites internal links to work in the new structure
- Verifies links and anchors
- Generates the MkDocs navigation structure

### 2. Complete Rebuild and Validation

To perform a complete rebuild and validation in one step:

```bash
make docs
```

This will:

1. Run the collection script
2. Generate the plugin inventory
3. Verify the documentation for issues
4. Build the documentation with MkDocs
5. Start a local server to preview the documentation

Visit [http://localhost:8000/](http://localhost:8000/) to view the documentation.

## Documentation Best Practices

When writing or updating documentation:

1. **Source Files**: Always edit the original markdown files, not the copies in `docs/`
2. **Headings**: Each file should start with a single Level 1 heading (`#`) that matches the filename
3. **Code Blocks**: Always specify a language for fenced code blocks (e.g., ```python)
4. **Links**: Use relative links to reference other documentation files
5. **Concrete References**: Avoid vague time references like "recently" or "today"

For more detailed information, see the [Documentation Workflow](docs-gen/documentation_workflow.md) guide.
