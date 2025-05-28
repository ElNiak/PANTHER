# Documentation Link Management

This document explains how to maintain and verify links across the PANTHER documentation.

## Link Verification Tool

The project includes a tool called `verify_links.py` located in the `docs-gen` directory. This tool scans all Markdown files in the project, validates both internal and external links, and can automatically fix common issues.

### Features

- Validates internal links between Markdown files
- Checks whether anchors (#headings) exist in the target files
- Converts GitHub URLs to repository files into relative links
- Reports broken external URLs
- Automatically fixes common issues (with the `--autofix` flag)

### Usage

To run the link verification tool:

```bash
# Navigate to the project root
cd /path/to/PANTHER

# Check all links without fixing
python docs-gen/verify_links.py

# Check all links and auto-fix issues where possible
python docs-gen/verify_links.py --autofix

# Check both internal and external links
python docs-gen/verify_links.py --check-external
```

### Link Types Verified

1. **Internal Links** - Links to other files within the repository
   - Checks if the file exists
   - Validates that relative paths resolve correctly
   - Automatically converts absolute GitHub URLs to relative paths

2. **Anchor Links** - Links to specific headings within files using `#anchors`
   - Verifies if the target heading exists
   - Uses the same slugification logic as MkDocs

3. **External Links** - Links to websites outside the project
   - Validates that the URL is accessible (with `--check-external` flag)
   - Reports redirects or broken links

4. **Image Links** - References to images using `![alt](path)` syntax
   - Verifies that the image file exists

## Best Practices for Documentation Links

### Internal Links

- Use relative paths for links between documentation files
- Link to specific headings with anchors when appropriate: `[Text](file.md#heading)`
- When linking to directories, use explicit index files: `[Text](directory/README.md)`

### Anchors

- MkDocs generates anchor IDs by converting headings to lowercase, replacing spaces with hyphens, and removing special characters
- For more control, you can specify custom anchors with the attribute syntax: `# My Heading {#custom-id}`

### External Links

- Always use HTTPS when available
- Consider adding link checking to CI to catch broken external links

### Cross-Reference Documentation

Root documentation files should link to relevant plugin documentation, and plugin README files should link back to the core documentation.

Example structure for a good README:

```markdown
# Component Name

Brief description of what this component does.

## Features

* Feature 1
* Feature 2

## Usage

Basic usage instructions...

## See Also

* [Quick Start Guide](../../../quick_start.md)
* [API Reference](../../reference/component.md)
* [Related Plugin](../related_plugin/README.md)
```

## Continuous Integration

The link verification tool can be integrated into CI workflows to ensure documentation quality. Add the following step to your GitHub Actions workflow:

```yaml
- name: Verify Documentation Links
  run: |
    pip install pyyaml requests
    python docs-gen/verify_links.py
```

This will fail the CI build if any broken internal links are found.

## MkDocs Navigation

The `mkdocs.yml` file should be kept in sync with the documentation structure. All Markdown files should be included exactly once in the navigation tree.

The basic structure should be:

- Home / Overview
- Installation / Getting Started
- User Guides
- Plugin System
  - Services
  - Protocols
  - Environments
- Development
  - Contributing
  - Documentation Guidelines
- API Reference
- Additional Resources

## Troubleshooting

### Common Issues

1. **Broken internal links**
   - Check for typos in filenames or paths
   - Ensure the target file exists in the expected location
   - Use `--autofix` to automatically fix common issues

2. **Missing anchors**
   - Verify that the heading exists in the target document
   - Check that the anchor matches the slugified heading name
   - Remember that anchors are case-sensitive in the markdown but case-insensitive in the browser

3. **External links failing**
   - Verify that the external site is accessible
   - Check if the URL has changed or is redirecting
