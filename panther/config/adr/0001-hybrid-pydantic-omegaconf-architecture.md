# ADR-0001: Hybrid Pydantic + OmegaConf Configuration Architecture

## Status
Accepted

## Context
The PANTHER configuration system needs to handle complex network testing scenarios with requirements for:

1. **Type Safety**: Strong typing to catch configuration errors early
2. **Interpolation**: Variable substitution and environment-aware configurations
3. **Validation**: Multi-stage validation with clear error messages
4. **Flexibility**: Support for plugin-specific configuration schemas
5. **Developer Experience**: IDE support, auto-completion, and clear error messages

Existing solutions present trade-offs:
- **Pure Pydantic**: Excellent type safety and validation, but limited interpolation capabilities
- **Pure OmegaConf**: Powerful interpolation and merging, but weaker type safety
- **YAML + Manual Parsing**: Flexible but error-prone and lacks validation

## Decision
We implement a **hybrid architecture** combining Pydantic BaseModel with OmegaConf capabilities through the `BaseConfig` class.

### Architecture Design
```python
class BaseConfig(BaseModel, ABC):
    """Hybrid configuration combining Pydantic validation with OmegaConf interpolation."""

    # Pydantic provides: type safety, validation, IDE support
    # OmegaConf provides: interpolation, merging, YAML handling
```

### Key Design Principles
1. **Dual Representation**: Maintain both Pydantic model and OmegaConf DictConfig
2. **Seamless Conversion**: Bidirectional conversion between representations
3. **Validation First**: Pydantic validation as the primary type safety mechanism
4. **Interpolation Support**: OmegaConf for `${variable}` resolution
5. **Developer Experience**: Strong typing with IDE support

## Implementation Details

### Hybrid Model Features
- **Initialization**: Convert input data to both Pydantic model and OmegaConf representation
- **Field Access**: Standard dot notation through Pydantic properties
- **Interpolation**: Variable resolution through OmegaConf when needed
- **Serialization**: Multiple output formats (dict, YAML, JSON)
- **Merging**: Deep configuration merging through OmegaConf

### Mixin Architecture
The `ConfigurationManager` uses mixin composition to provide:
- `ConfigLoadingMixin`: File loading and parsing
- `ValidationOperationsMixin`: Multi-stage validation
- `PluginManagementMixin`: Dynamic plugin integration
- `CachingMixin`: Performance optimization

## Consequences

### Positive
- **Type Safety**: Catch configuration errors at load time, not runtime
- **IDE Support**: Full auto-completion and type checking in development
- **Interpolation**: Powerful variable substitution for environment-aware configs
- **Plugin Architecture**: Dynamic schema discovery and integration
- **Performance**: Intelligent caching and lazy loading
- **Error Messages**: Clear, actionable validation errors with suggestions

### Negative
- **Complexity**: Dual representation adds architectural complexity
- **Memory Overhead**: Maintaining both Pydantic and OmegaConf representations
- **Learning Curve**: Developers need to understand both Pydantic and OmegaConf concepts
- **Dependency Weight**: Additional dependencies beyond basic YAML parsing

### Mitigations
- **Documentation**: Comprehensive guides and examples for developers
- **Abstraction**: Hide complexity behind simple `ConfigurationManager` interface
- **Performance**: Lazy OmegaConf creation and intelligent caching
- **Testing**: Extensive test coverage for both representations and conversion logic

## Alternatives Considered

### Alternative 1: Pure Pydantic
**Pros**: Maximum type safety, excellent IDE support, simple architecture
**Cons**: Limited interpolation, poor environment variable support
**Decision**: Rejected due to interpolation limitations critical for deployment scenarios

### Alternative 2: Pure OmegaConf
**Pros**: Powerful interpolation, excellent YAML support, simple merging
**Cons**: Weaker type safety, limited IDE support, runtime error discovery
**Decision**: Rejected due to type safety requirements for complex configurations

### Alternative 3: Custom YAML + Marshmallow
**Pros**: Full control over parsing and validation logic
**Cons**: Significant development overhead, reinventing existing solutions
**Decision**: Rejected due to maintenance burden and ecosystem fragmentation

### Alternative 4: Layered Architecture (Pydantic over OmegaConf)
**Pros**: Clear separation of concerns, leverages strengths of both
**Cons**: Still complex, potential for representation drift
**Decision**: This is essentially what we implemented with `BaseConfig`

## Implementation Timeline

### Phase 1: Core Foundation ✅
- Implement `BaseConfig` hybrid class
- Basic conversion methods (`to_omega`, `from_omega`)
- Simple validation integration

### Phase 2: Manager Integration ✅
- Develop `ConfigurationManager` with mixin architecture
- Implement plugin discovery and schema integration
- Add caching and performance optimizations

### Phase 3: Advanced Features ✅
- Auto-fix capabilities for common configuration issues
- Environment variable resolution with defaults
- Multi-stage validation (schema, business rules, compatibility)

### Phase 4: Developer Experience ✅
- Comprehensive documentation and tutorials
- API reference generation
- Error message improvements and validation suggestions

## Validation

### Success Metrics
- **Type Coverage**: >95% of configuration fields have proper type annotations
- **Error Detection**: Configuration errors caught at load time vs runtime
- **Developer Productivity**: Time to create and validate new configurations
- **Performance**: Configuration loading time <1s for typical experiments

### Monitoring
- Track validation error frequencies to identify common issues
- Monitor cache hit rates for performance optimization
- Measure developer onboarding time and configuration error rates

## Related Decisions
- **ADR-0002**: Plugin Architecture for Configuration Schema Discovery
- **ADR-0003**: Multi-Stage Validation Strategy
- **ADR-0004**: Caching Strategy for Configuration Performance

## References
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [OmegaConf Documentation](https://omegaconf.readthedocs.io/)
- [PANTHER Configuration Requirements](../requirements/configuration_requirements.md)
- [Configuration Performance Benchmarks](../docs/performance_analysis.md)
