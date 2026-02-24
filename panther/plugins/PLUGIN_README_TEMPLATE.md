# <Plugin Name>

> **Plugin Type**: <Service (IUT) | Execution Environment | Network Environment | Protocol>
> **Source Location**: `plugins/<category>/<plugin_name>/`

## Overview

<2-3 factual sentences describing what the plugin does and its primary use case.>

<!-- src: <main_python_file> -->

## Configuration Options

<Tables grouped by category, derived from config_schema.py. Use this format:>

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `field_name` | `type` | `default` | Description of the field |

<!-- src: config_schema.py -->

## Usage Example

```yaml
tests:
  - name: "Example Test"
    # Minimal YAML config snippet showing this plugin in use
```

## Integration

- Bullet points describing how this plugin integrates with other PANTHER components
- Keep to 2-4 points

## Troubleshooting (optional)

Common issues with concise solutions. Use subsections or a table.

## References (optional)

- Links to external documentation, upstream project pages, or related PANTHER docs

<!--
Template rules:
- Max 2 admonitions per README (only for genuinely critical warnings)
- No opening `!!! info` admonition (duplicates Overview section)
- Source citations required near config tables
- Config tables must match actual config_schema.py
- All code fences must have language tags (yaml, python, bash, dockerfile, text)
- Metadata block uses blockquote style (> **Key**: Value)
-->
