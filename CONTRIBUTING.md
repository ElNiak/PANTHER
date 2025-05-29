# Contributing

!!! info "Quick Navigation"
    - :material-file-tree: [Project Structure](#open_file_folder-project-structure)
    - :material-book-open: [Documentation Guidelines](#contributing-to-panther-documentation)
    - :material-palette: [Admonitions Guide](#admonitions-usage-guide)
    - :material-workflow: [Review Process](#documentation-review-process)

## :open_file_folder: Project Structure

The PANTHER project is organized into the following key directories:

```text
experiment-config/      # Experiments configurations files
tests/                  # Unit tests
outputs/                # Experiment results and logs
panther/
├── config/              # Configuration files and schemas
├── core/                # Core experiment logic
├── plugins/             # Plugin implementations for protocols, environments, etc.
├──── services/          # Protocol implementations
├────── iut/             # Protocol-specific implementations
├────────── quic/        # QUIC protocol implementations
├──────────── picoquic/  # Picoquic implementation
├──────────── ...
├────────── minip/       # MiniP protocol implementations
├────────── ...
├────── testers/         # Testers for protocol implementations
├────────── panther_ivy/ # Ivy tester implementation
├──── environments/      # Environment configurations
├────── network_environment/    # Network environment configurations
├────────── docker_compose/     # Docker Compose configurations
├────────── shadow_ns/          # Shadow NS configurations
├────────── localhost_single_container/     # Localhost single container configurations
├────── execution_environment/  # Execution environment configurations
├────────── strace/             # Strace configurations
├────────── gperf_heap/         # Gperf Heap profiling configurations
├────────── gperf_cpu/          # Gperf CPU profiling configurations
├──── protocols/         # Protocol definitions
└── __main__.py          # Command-line interface for PANTHER
```

---

## Contributing to PANTHER Documentation

This guide provides standards and procedures for contributing to PANTHER documentation.

## Documentation Principles

1. **Accuracy**: All documentation must reflect the current codebase.
2. **Verifiability**: Technical statements should include source references.
3. **Structure**: Follow the established hierarchical organization.
4. **Conciseness**: Top-level documents should be ≤ 300 lines.
5. **Clarity**: Write in clear, accessible language.

## Documentation Structure

PANTHER's documentation is organized into several categories:

1. **Core Documentation**: Main project documents like README.md, CONTRIBUTING.md, and WORKFLOW.md
2. **Plugin Documentation**: README.md files in each plugin directory
3. **API Documentation**: Generated from Python docstrings
4. **User Guides**: Step-by-step tutorials in the docs directory
5. **Development Guides**: Technical information for contributors

All documentation should follow the established hierarchy and use relative links to reference other documents.

## Adding New Documentation

### For New Plugins

!!! warning "Plugin Development Requirements"
    Before creating a new plugin, ensure you understand the plugin architecture by reading the [Plugin Developer Guide](panther/plugins/development.md). All plugins must implement the required interfaces and follow naming conventions.

1. Create a README.md in your plugin directory using the [plugin template](panther/plugins/plugin_template.md).
2. Add a corresponding entry in the appropriate index.md file.
3. Ensure all examples are tested and functional.

### For Existing Components

1. Use the appropriate template from the templates directory.
2. Include source references for all technical statements.
3. Keep overview files concise, linking to detailed documentation.

## Source Verification

Include source references for technical statements using HTML comments:

```markdown
PANTHER supports plugin-based architecture.
<!-- src: /panther/plugins/plugin_interface.py -->
```

For statements that need verification, mark them clearly:

```markdown
// Use this format only during documentation development, not in final docs
The system can handle multiple concurrent test runs.
<!-- Note: This needs verification once benchmarks are complete -->
```

## Documentation CI Pipeline

The documentation CI pipeline will:

1. Check all links for validity
2. Flag unverified statements (TODO:VERIFY)
3. Validate source references against the current codebase
4. Check markdown formatting compliance

Details on the CI pipeline can be found in the [Documentation CI file](dev/docs-gen/documentation-ci.yml).

## Documentation Tools and Workflow

PANTHER provides several tools to help with documentation management:

1. **Documentation Update Script** - [update_docs.sh](dev/docs-gen/update_docs.sh): All-in-one script to update documentation in the correct order
2. **Link Verification** - [verify_links.py](dev/docs-gen/verify_links.py): Validates and fixes links in Markdown files
3. **Cross-References** - [add_cross_references.py](dev/docs-gen/add_cross_references.py): Adds "See Also" sections to connect related docs
4. **MkDocs Configuration** - [enhance_mkdocs_config.py](dev/docs-gen/enhance_mkdocs_config.py): Enhances the MkDocs configuration

For a complete understanding of the documentation system, refer to:

- [Documentation Workflow Guide](dev/docs-gen/documentation_WORKFLOW.md): Step-by-step guides for updating documentation
- [Documentation Integration Guide](dev/docs-gen/documentation_integration.md): How documentation tools work together
- [Documentation Link Management](dev/docs-gen/documentation_links.md): How to manage and verify links
- [Documentation System Enhancements](dev/docs-gen/documentation_enhancements.md): Overview of recent enhancements

## Writing Style

Follow the [PANTHER Style Guide](dev/docs-gen/style_guide.md) for detailed formatting instructions. General guidelines:

1. Use active voice and present tense
2. Specify language for all code blocks
3. Use second person for instructions
4. Include tables for parameter documentation
5. Use admonitions for important information

## Admonitions Usage Guide

PANTHER documentation uses Material for MkDocs admonitions (call-out blocks) to highlight important information. Use admonitions strategically to improve readability and user experience.

### Admonition Types Reference

The most commonly used admonition types in PANTHER documentation:

| Type | Purpose | Use Cases |
|------|---------|-----------|
| `info` | General information | System requirements, platform notes |
| `tip` | Helpful suggestions | Best practices, recommended approaches |
| `note` | Additional details | Clarifications, alternative methods |
| `warning` | Important cautions | Prerequisites, potential issues |
| `danger` | Critical alerts | Failures, security issues, data loss |
| `example` | Demonstrations | Code samples, configurations |

### Best Practices

!!! tip "Strategic Placement Guidelines"
    - **Maximum one admonition per screenful** to avoid visual clutter
    - Place admonitions **before** the content they relate to
    - Use **specific, descriptive titles** rather than generic ones
    - Keep admonition content **concise and focused**

### Basic Syntax

```markdown
!!! type "Descriptive Title"
    Content goes here with proper 4-space indentation.

    Can include multiple paragraphs and code blocks.
```

### Examples

**System Requirements:**

```markdown
!!! info "System Requirements"
    **Target platform:** Linux (x86-64) with Docker >= 27
```

**Best Practices:**

```markdown
!!! tip "Recommended Setup"
    Using a virtual environment is highly recommended.
```

**Critical Warnings:**

```markdown
!!! danger "Common Failure Points"
    Most issues occur during plugin loading or container builds.
```

## Admonitions Usage Guide

Admonitions are colored call-out blocks that help highlight important information in documentation. Use them strategically to improve user experience and information scannability.

### Available Admonition Types

| Type | Purpose | Use Cases |
|------|---------|-----------|
| `note` | General information | Additional context, alternative methods |
| `tip` | Helpful suggestions | Best practices, recommended approaches |
| `warning` | Important cautions | Prerequisites, potential issues |
| `danger` | Critical warnings | Data loss risks, security concerns |
| `example` | Code examples | Sample configurations, usage demos |
| `info` | Neutral information | System requirements, version notes |
| `success` | Positive outcomes | Successful completion indicators |
| `question` | Interactive queries | User decision points |

### Admonition Syntax

```markdown
!!! note "Optional Custom Title"
    Content goes here. Maintain proper indentation (4 spaces).

    You can include:
    - Lists
    - Code blocks
    - Multiple paragraphs
```

### Admonition Guidelines

1. **Strategic Placement**: Maximum one admonition per screenful to avoid visual clutter
2. **Clear Titles**: Use descriptive titles when the default doesn't fit
3. **Proper Indentation**: Content must be indented with 4 spaces
4. **Code Blocks**: Maintain proper indentation within admonitions

### Template Examples

**System Requirements:**
```markdown
!!! info "System Requirements"
    **Target platform:** Linux (x86-64) with Docker >= 27
    **Estimated time:** ≈ 30 minutes per test
```

**Installation Tips:**
```markdown
!!! tip "Recommended Setup"
    Using a virtual environment is highly recommended:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
```

**Important Warnings:**
```markdown
!!! warning "Prerequisites Required"
    Ensure you have Docker access and at least 10GB free disk space before proceeding.
```

**Code Examples:**
```markdown
!!! example "Sample Configuration"
    Create `config.yaml`:

    ```yaml
    tests:
      - name: "Basic Test"
        protocol: quic
    ```
```

## Documentation Review Process

1. **Self-review**: Ensure your documentation follows all guidelines.
2. **Peer review**: Have another contributor review your documentation.
3. **Verification**: Ensure all technical statements have source references.
4. **Integration**: Update any affected index files or links.

## Tools and Resources

- [MkDocs Material Theme Reference](https://squidfunk.github.io/mkdocs-material/reference/)
- [Markdown Lint Rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
- [PANTHER Style Guide](dev/docs-gen/style_guide.md)
- [Plugin Documentation Template](panther/plugins/plugin_template.md)
