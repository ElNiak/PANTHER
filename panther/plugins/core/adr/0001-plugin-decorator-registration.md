# ADR-0001: Plugin Decorator Registration

## Status

Accepted

## Context

PANTHER requires a plugin system where service implementations, protocols, and environments can be discovered and registered without manual configuration. The system needs to:

- Allow plugins to self-register at import time
- Support multiple plugin categories (services, protocols, environments)
- Provide a consistent registration interface across plugin types
- Enable plugin discovery without scanning file systems

## Decision

Use decorator-based registration with `@register_plugin()` and `@register_protocol()` decorators defined in `panther/plugins/core/`.

Plugins register themselves by decorating their manager classes:

```python
@register_plugin(name="picoquic", category="iut")
class PicoquicServiceManager(BaseQUICServiceManager):
    ...
```

A central plugin registry maintains the mapping from names to plugin classes, populated at import time.

## Consequences

### Positive
- Self-documenting: the decorator declares the plugin's identity
- No configuration files needed for plugin discovery
- Type-safe registration with validation at import time
- Easy to add new plugins by following the decorator pattern

### Negative
- Import-time side effects (registration happens on import)
- Plugin discovery requires importing all plugin modules
- Circular import risk if registry and plugins are tightly coupled

### Mitigation Strategies
- Lazy imports where possible to reduce startup overhead
- Plugin discovery uses explicit import paths rather than filesystem scanning
- Registry is a simple dict, minimizing coupling

## Related Decisions
- Template method pattern for service managers
- Mixin-based architecture for shared behavior
