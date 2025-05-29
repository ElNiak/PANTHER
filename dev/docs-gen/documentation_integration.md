# PANTHER Documentation Integration Guide

This guide explains how the different documentation tools in the PANTHER project work together to create a comprehensive and well-connected documentation system.

## Documentation Components

The PANTHER documentation system consists of several components:

1. **Markdown Files**: Source files for documentation, including READMEs and guides
2. **MkDocs Configuration**: The `mkdocs.yml` file that controls the documentation site structure
3. **API Documentation**: Generated from Python docstrings
4. **Plugin Documentation**: Generated from plugin README files
5. **Cross-References**: Links between related documentation files
6. **Navigation Structure**: Organized hierarchy of documentation

## Documentation Tools Overview

| Tool | Purpose | Location |
|------|---------|----------|
| `add_cross_references.py` | Adds "See Also" sections to connect related docs | `dev/docs-gen/` |
| `verify_links.py` | Validates and auto-fixes links in Markdown files | `dev/docs-gen/` |
| `update_mkdocs_nav.py` | Updates MkDocs navigation structure | `dev/docs-gen/` |
| `enhance_mkdocs_config.py` | Adds link checking plugins to MkDocs config | `dev/docs-gen/` |
| `gen_ref_pages.py` | Generates API reference docs from docstrings | `dev/docs-gen/mkdocs/` |
| `generate_plugin_docs.py` | Generates plugin documentation | `dev/docs-gen/mkdocs/` |
| `pre_commit_docs.py` | Pre-commit hook for documentation checks | `dev/docs-gen/` |
| `update_docs.sh` | Script to run all documentation tasks | `dev/docs-gen/` |

## Automated Integration

The documentation tools are integrated at multiple levels:

### 1. Pre-Commit Hook

The pre-commit hook (`pre_commit_docs.py`) runs whenever you commit changes that include Markdown files. It:

- Verifies and fixes links
- Adds cross-references
- Updates MkDocs navigation

To enable the pre-commit hook:

```bash
pre-commit install
```

### 2. CI/CD Integration

The GitHub Actions workflow (`documentation-ci.yml`) runs documentation checks on every push and pull request. It:

- Verifies internal links
- Adds cross-references
- Updates MkDocs navigation
- Generates API documentation
- Builds the documentation site
- (Optionally) Checks external links

### 3. Manual Update

You can manually update all documentation by running:

```bash
./dev/docs-gen/update_docs.sh
```

This will run all documentation tasks in the correct order.

## Documentation Flow

The PANTHER documentation flow works as follows:

1. **Write documentation**: Create or update Markdown files
2. **Add cross-references**: Links are added between related documents
3. **Verify links**: Links are validated and fixed when possible
4. **Generate API docs**: API reference is generated from docstrings
5. **Update navigation**: MkDocs navigation is updated to include all files
6. **Build documentation**: MkDocs builds the static site
7. **Deploy**: The site is deployed to GitHub Pages

## Best Practices for Documentation Integration

### Cross-Document References

When referencing other documents, use relative links:

```markdown
See the [Quick Start Guide](../../QUICK_START.md) for more information.
```

### API References

When referencing API classes or functions, use the proper format:

```markdown
See the [`MyClass`](../../../reference/mymodule.md#myclass) for more information.
```

### Plugin Documentation

Plugin documentation should follow this structure:

- `README.md`: Overview of the plugin
- `development.md`: Development guide for the plugin
- `index.md`: Entry point for MkDocs navigation

### MkDocs Configuration

The MkDocs configuration is automatically updated by `update_mkdocs_nav.py`. If you need to add custom navigation, edit the `DEFAULT_SECTIONS` dictionary in that script.

## Troubleshooting

### Broken Links

If you encounter broken links:

1. Run `python dev/docs-gen/verify_links.py --autofix` to automatically fix them
2. Check the output for any links that couldn't be automatically fixed
3. Manually fix any remaining issues

### Missing Cross-References

If documents aren't properly cross-referenced:

1. Run `python dev/docs-gen/add_cross_references.py` to add cross-references
2. Check the output to see which files were updated
3. Add any missing references manually if needed

### Navigation Issues

If documents aren't showing up in the MkDocs navigation:

1. Run `python dev/docs-gen/update_mkdocs_nav.py` to update the navigation
2. Check `mkdocs.yml` to ensure the document is included
3. Make sure the document is in a location recognized by the navigation updater

## Further Reading

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [MkDocstrings](https://mkdocstrings.github.io/)
- [Pre-commit Hooks](https://pre-commit.com/)
