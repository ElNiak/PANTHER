# Phase 0 - Dispatch 1D: Plugin System Documentation Evidence

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE

## Key Findings

### CRITICAL: CLAUDE.md Contains Wrong Decorator Names
- `@service_plugin`, `@protocol_plugin`, `@environment_plugin` **DO NOT EXIST**
- Real decorators: `@register_plugin(plugin_type=PluginType.X)` and `@register_protocol()`
- Severity: CRITICAL (ACC-01) - CLAUDE.md is authoritative project documentation

### CRITICAL: Plugin File Naming Convention Wrong in Dev Guide
- `development.md:299` documents main file as `plugin.py`
- Discovery system requires `<plugin_name>/<plugin_name>.py`
- Following the template exactly produces an undiscoverable plugin
- Severity: CRITICAL (ACC-04)

### CRITICAL: Dependency Resolution Claimed but Not Implemented
- `development.md:517` claims "Automatic dependency resolution with semantic versioning"
- `plugin_catalog.py:138-152` is a no-op stub with TODO comment
- Severity: CRITICAL (ACC-01)

### MAJOR: runtime_mode Docstring Bug
- Docstring lists "production" as valid; code rejects it with ValueError
- Only valid: "minimal", "debug", "profile"
- Severity: MAJOR (ACC-01)

### MAJOR: Plugin Inventory Incomplete
- `gdb` plugin fully implemented but absent from `plugins_inventory.md`
- `http` (IUT service) directory exists as stub, not inventoried
- Severity: MAJOR (CMP-11)

### MAJOR: README References Non-Existent Files
- `panther/plugins/plugin_loader.py` - does not exist
- `panther/plugins/plugin_creator.py` - does not exist at stated path
- `PluginLoader` class referenced in template - does not exist
- Severity: MAJOR (ACC-06)

### MINOR: Undocumented Plugin Discovery Behaviors
- `mixins`, `utils`, `base`, `tests` directories silently skipped during scan
- `OBSERVER` and `SERVICE` PluginType enum values exist but undocumented
- CLI flags (`--create-plugin`, `--dev-mode`, etc.) reference old argparse interface
- Severity: MINOR (CMP-10)

## Evidence Summary Table

| Claim | Source | Status | Severity |
|-------|--------|--------|----------|
| `@service_plugin` exists | CLAUDE.md | INACCURATE | CRITICAL |
| `@protocol_plugin` exists | CLAUDE.md | INACCURATE | CRITICAL |
| Main plugin file is `plugin.py` | development.md:299 | INACCURATE | CRITICAL |
| Dependency resolution works | development.md:517 | INACCURATE | CRITICAL |
| `runtime_mode="production"` valid | plugin_decorators.py:175 | INACCURATE | MAJOR |
| `gdb` in inventory | plugins_inventory.md | MISSING | MAJOR |
| `plugin_loader.py` exists | README.md:48 | INACCURATE | MAJOR |
| `plugin_creator.py` exists | README.md:46 | INACCURATE | MAJOR |
| `PluginLoader` importable | plugin_template.md:155 | INACCURATE | MAJOR |
| `@register_plugin` is primary | development.md:468 | ACCURATE | - |
| 5-step registration flow | development.md:535 | ACCURATE | - |
| Reserved dir names documented | N/A | UNDOCUMENTED | MINOR |
