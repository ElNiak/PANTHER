---
description: Google-style docstring conventions for Griffe/mkdocstrings
applyTo: "**/*.py"
---

# Docstring Style Guide — PANTHER

PANTHER uses **Google-style docstrings** parsed by Griffe.
`docs/` is **auto-generated** from source code — docstrings are the single source of truth.

## Module-level (`__init__.py`)

```python
"""Short summary (one line).

Extended description with architecture notes, design rationale,
or usage guidance. Use Markdown freely — Griffe renders it.

Note:
    Admonition rendered by Griffe as a callout block.

Example:
    ```python
    from panther.plugins.environments import ...
    ```

Attributes:
    MODULE_CONSTANT: Description of a module-level constant.
"""
```

## Class-level

```python
class Foo:
    """Short summary.

    Extended description.

    Attributes:
        name: Human-readable name.
        config: Validated Pydantic model.

    Example:
        ```python
        foo = Foo(name="bar")
        ```
    """
```

## Method / Function

```python
def run(self, config: dict[str, Any], *, dry_run: bool = False) -> Result:
    """Execute the experiment.

    Args:
        config: Validated experiment configuration.
        dry_run: If True, validate without executing.

    Returns:
        Experiment result with metrics and status.

    Raises:
        ExperimentError: If execution fails after retries.

    Example:
        ```python
        result = manager.run(cfg, dry_run=True)
        ```
    """
```

## Rules

1. **Style**: Google (`Args:`, `Returns:`, `Raises:`, `Attributes:`, `Example:`, `Note:`, `Warning:`, `Tip:`).
2. **Forbidden**: Sphinx directives (`:param:`, `:class:`, `:mod:`, `:func:`, `:doc:`).
3. **Cross-references**: Use backtick-wrapped fully-qualified names — Griffe auto-links them when `signature_crossrefs: true`.
   - `panther.core.experiment_manager.ExperimentManager`
   - Short form `ExperimentManager` works within the same package.
4. **Markdown**: Use `**bold**`, `` `code` ``, fenced code blocks, tables, and Mermaid diagrams.
5. **No manual docs/**: Never create hand-written `.md` in `docs/`. Put content in `__init__.py` or class/function docstrings instead.
6. **No nested READMEs**: Package documentation lives in `__init__.py` module docstrings, not README.md files.
