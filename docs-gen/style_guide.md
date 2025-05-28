# PANTHER Documentation Style Guide

This guide establishes standards for documentation across the PANTHER project, ensuring consistency, accuracy, and verifiability.

## Core Principles

1. **Accuracy**: All technical documentation must be verifiable in the codebase.
2. **Clarity**: Use clear, concise language accessible to the intended audience.
3. **Hierarchy**: Organize information in a logical structure with consistent headings.
4. **Verifiability**: Include source references for technical statements.
5. **Conciseness**: Keep documents focused, preferring depth in linked documents over length.

## Document Structure

### Top-Level Documents

Top-level documents should be concise overviews (≤ 300 lines) that:

1. Explain the purpose and scope of the topic area
2. Provide a high-level architecture overview
3. Link to detailed documentation for specific components
4. Include relevant diagrams that visualize component relationships

### Plugin Documentation

Each plugin should have its own README.md following this structure:

1. **Header**: Plugin name, type, and verified source location
2. **Purpose**: Clear description of the plugin's role
3. **Requirements**: Dependencies and prerequisites
4. **Configuration**: Parameter documentation with types and examples
5. **Usage**: Complete, working examples
6. **Extension**: How to extend or customize the plugin
7. **Testing**: How to verify the plugin works correctly

## Writing Style

### General Guidelines

- Use active voice
- Write in present tense
- Be direct and concise
- Use second person ("you") for instructions
- Avoid jargon or define it when unavoidable

### Code Blocks

- Always specify the language for syntax highlighting
- Use meaningful indentation
- Include comments for complex parts
- Prefer complete examples over fragments

```yaml
# Example configuration
services:
  - name: "example_service"  # Descriptive name
    type: "tester"           # Service type
    implementation: "example_impl"
```

### Tables

Use tables for comparing options, parameters, or configurations:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name`    | string | Yes | - | Unique identifier for the service |
| `type`    | string | Yes | - | Service type (e.g., "tester") |
| `config`  | object | Yes | - | Service-specific configuration |

## Verification System

### Source References

Include source references in HTML comments for technical statements:

```markdown
PANTHER uses a plugin system for extensibility.
<!-- src: /panther/plugins/plugin_loader.py:12-15 -->
```

### Unverified Statements

Mark unverified or questionable statements for review:

```markdown
Documentation should be clear and concise.
<!-- src: /panther/plugins/README.md -->
```

### Automatic Verification

Documentation CI will:

1. Flag all `TODO:VERIFY` markers
2. Check that referenced source files and line numbers exist
3. Verify all API references against the current codebase

## Links and Cross-References

- Use relative paths for internal documentation links
- Use absolute URLs for external resources
- Link to the most specific relevant document
- Avoid deep linking to unstable anchors

## Diagrams

- Store diagrams as separate files in the `docs/images/` directory
- Use vector formats (SVG) where possible
- Include source files for editable diagrams (e.g., `.drawio`)
- Keep diagrams simple and focused on one concept

## Versioning

- Mark features with their minimum version requirement
- Note deprecated features and their removal timeline
- Document breaking changes prominently
