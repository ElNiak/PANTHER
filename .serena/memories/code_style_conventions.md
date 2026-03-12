# PANTHER Code Style and Conventions

## Python Version
- Minimum: Python 3.10
- Target versions: 3.10, 3.11, 3.12

## Formatting Tools
- **Black**: Line length 88, target Python 3.10+
- **isort**: Black-compatible profile (multi_line_output=3, trailing comma)
- **flake8**: Line length 88, extends ignored E203, W503

## Exclusions from Linting
- `panther/plugins/services/testers/panther_ivy/` - Git submodule, do not modify
- `outputs*` directories
- Test resources: `tests/tests_ressources/`

## Type Hints
- mypy configured but not strict (disallow_untyped_defs=false)
- Type hints encouraged but not mandatory
- Use `TYPE_CHECKING` imports for type-only imports

## Docstrings
- Not strictly enforced (C0111 disabled in pylint)
- When written, use Google style or numpy style

## Naming Conventions
- snake_case for functions, methods, variables
- PascalCase for classes
- UPPER_CASE for constants
- C0103 (invalid-name) disabled in pylint for flexibility

## Design Patterns Used
- **Plugin System**: Decorator-based registration
- **Observer Pattern**: Event-driven coordination in `core/observer/`
- **Template Method**: Plugin inheritance structure
- **Mixin Pattern**: Used extensively in test cases and services
- **Factory Pattern**: Plugin factory in `plugins/core/plugin_factory.py`

## Code Organization
- Configuration via OmegaConf + Pydantic hybrid
- Each plugin has its own `config_schema.py`
- Core functionality in `panther/core/`
- CLI in `panther/cli/` (new) - USE THIS
- Legacy CLI in `panther/cli/` (deprecated) - DO NOT USE

## Pre-commit Hooks
Active by default:
- trailing-whitespace
- end-of-file-fixer
- check-yaml (except mkdocs.yml)
- check-added-large-files (max 1000kb)
- check-merge-conflict
- check-json
- check-toml
- black
- isort
- test-syntax
- import-check

Manual stage (not auto-run):
- flake8
- fast-tests
- bandit
