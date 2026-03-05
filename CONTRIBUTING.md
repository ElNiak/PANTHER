# Contributing

> [!NOTE]
> "Quick Navigation"
> - :material-file-tree: [Project Structure](#open_file_folder-project-structure)
> - :material-book-open: [Documentation Guidelines](#contributing-to-panther-documentation)
> - :material-palette: [Admonitions Guide](#admonitions-usage-guide)
> - :material-workflow: [Review Process](#documentation-review-process)

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

> [!WARNING]
> "Plugin Development Requirements"
> Before creating a new plugin, ensure you understand the plugin architecture by reading the [Plugin Developer Guide](panther/plugins/development.md). All plugins must implement the required interfaces and follow naming conventions.

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

Documentation generation tools are located in `panther/tools/docs_gen/`.

## Documentation Tools and Workflow

PANTHER provides documentation generation tools in `panther/tools/docs_gen/`:

1. **Source Discovery** - `panther/tools/docs_gen/discover_sources.py`: Discovers documentation source files
2. **Build Mapping** - `panther/tools/docs_gen/generate_build_mapping.py`: Generates build mapping for documentation

## Writing Style

General formatting guidelines:

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

> [!TIP]
> "Strategic Placement Guidelines"
> - **Maximum one admonition per screenful** to avoid visual clutter
> - Place admonitions **before** the content they relate to
> - Use **specific, descriptive titles** rather than generic ones
> - Keep admonition content **concise and focused**

### Basic Syntax

```markdown
> [!NOTE]
> "Descriptive Title"
> Content goes here with proper 4-space indentation.
>
> Can include multiple paragraphs and code blocks.
```

### Examples

**System Requirements:**

```markdown
> [!NOTE]
> "System Requirements"
> **Target platform:** Linux (x86-64) with Docker >= 27
```

**Best Practices:**

```markdown
> [!TIP]
> "Recommended Setup"
> Using a virtual environment is highly recommended.
```

**Critical Warnings:**

```markdown
> [!CAUTION]
> "Common Failure Points"
> Most issues occur during plugin loading or container builds.
```

## Documentation Review Process

1. **Self-review**: Ensure your documentation follows all guidelines.
2. **Peer review**: Have another contributor review your documentation.
3. **Verification**: Ensure all technical statements have source references.
4. **Integration**: Update any affected index files or links.

## Tools and Resources

- [MkDocs Material Theme Reference](https://squidfunk.github.io/mkdocs-material/reference/)
- [Markdown Lint Rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
- [Plugin Documentation Template](panther/plugins/plugin_template.md)
