# ADR-0001: Click CLI Migration

## Status

Accepted

## Context

PANTHER's original CLI used argparse, which became difficult to maintain as the command surface grew. Key limitations included:

- No built-in support for command groups and subcommands
- Manual help text formatting and validation
- Difficult to compose commands from plugins
- No standardized parameter types or callbacks

The CLI needed better command organization, automatic help generation, and plugin-friendly extensibility.

## Decision

Migrate the CLI from argparse to the Click framework (`panther/cli_click/`).

Click provides:
- Declarative command groups with automatic help
- Built-in parameter types, validation, and callbacks
- Composable command structure suitable for plugin integration
- Consistent error handling and output formatting

## Consequences

### Positive
- Cleaner command definitions with decorator-based syntax
- Automatic help text generation from docstrings
- Easy addition of new commands from plugins
- Standardized parameter validation

### Negative
- Migration effort from existing argparse commands
- Click dependency added to core requirements
- Legacy argparse CLI code remains as dead code until fully removed

### Mitigation Strategies
- Incremental migration: new commands use Click, old commands migrated over time
- Legacy CLI module preserved but unused during transition

## Related Decisions
- Plugin system architecture (plugins contribute CLI commands)
