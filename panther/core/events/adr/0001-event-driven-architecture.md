# ADR-0001: Event-Driven Architecture

## Status

Accepted

## Context

PANTHER's experiment execution involves multiple components (experiment manager, service managers, network environments, execution environments) that need to communicate state changes without tight coupling. Requirements:

- Components should not directly reference each other
- State changes (test started, service ready, error occurred) must propagate reliably
- Multiple observers may need to react to the same event
- Event handling must not block the main execution flow

## Decision

Adopt an observer pattern with typed events for inter-component communication (`panther/core/events/`).

Key design elements:
- `EventManager` singleton coordinates event dispatch
- Typed event classes (e.g., `TestStartedEvent`, `ServiceReadyEvent`) ensure type safety
- Observers implement `ITypedObserver` interface and subscribe to specific event types
- Events carry structured payloads with all necessary context

## Consequences

### Positive
- Decoupled components: emitters don't know about consumers
- Easy to add new observers (metrics, logging, reporting) without modifying emitters
- Typed events provide compile-time and runtime validation
- Supports the four-phase execution model with clear phase transition events

### Negative
- Indirect control flow can be harder to trace during debugging
- Event ordering is not guaranteed across different observer types
- Singleton EventManager is a global state point

### Mitigation Strategies
- Feature-aware logging (ADR-0001 in utils) provides event tracing
- Observer priority system controls execution order when needed
- EventManager reset capability for testing isolation

## Related Decisions
- [Feature-Aware Logging Architecture](../../utils/adr/0001-feature-aware-logging-architecture.md)
- [Centralized Statistics Collection](../../utils/adr/0002-centralized-statistics-collection.md)
