# Task 20: Implement panther.api events and schemas Modules

## Goal
Implement `panther/api/events.py` and `panther/api/schemas.py` as thin facades.

## Prerequisites
- Task 17 completed (module scaffolded)

## Source Files to Read

### For events.py:
- `panther/core/observer/management.py` - EventManager class
- `panther/core/observer/__init__.py` - Observer system exports
- `panther/core/events/base/event_base.py` (now in panther-types) - BaseEvent

### For schemas.py:
- `panther/config/core/base.py` - BaseConfig.get_schema() (returns Pydantic JSON Schema)
- `panther/config/core/models/plugin.py` - each plugin config has get_schema()
- Pydantic v2 `model_json_schema()` API

## Steps

### Step 1: Implement events.py

```python
# panther/api/events.py
"""Event subscription and streaming.

Wraps EventManager to provide event subscription, callback registration,
and async event streaming for real-time monitoring.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Callable, Dict, List, Optional


def subscribe(
    event_types: List[str],
    callback: Callable[[Any], None],
) -> str:
    """Subscribe to events of specified types.

    Args:
        event_types: List of event type names to subscribe to
            (e.g., ["TestCompletedEvent", "ServiceErrorEvent"]).
        callback: Function called with each matching event.

    Returns:
        subscription_id (str) for later unsubscription.
    """
    # Read EventManager.register_observer() and implement
    pass


def unsubscribe(subscription_id: str) -> None:
    """Remove an event subscription.

    Args:
        subscription_id: ID returned by subscribe().
    """
    pass


async def event_stream(
    experiment_id: Optional[str] = None,
    event_types: Optional[List[str]] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Async generator that yields events as they occur.

    This is designed for Server-Sent Events (SSE) or WebSocket streaming.

    Args:
        experiment_id: Optional filter to only receive events for a specific experiment.
        event_types: Optional filter for specific event types.

    Yields:
        Dict representation of each event (from BaseEvent.to_dict()).

    Example:
        async for event in event_stream(experiment_id="exp-123"):
            print(f"Event: {event['event_type']} - {event['name']}")
    """
    # Implementation will use an asyncio.Queue fed by an observer
    pass


def get_event_types() -> List[Dict[str, str]]:
    """List all available event types with descriptions.

    Returns:
        List of dicts with: name, category, description.
    """
    # Read EventType enum and all concrete event classes
    pass
```

### Step 2: Implement schemas.py

```python
# panther/api/schemas.py
"""JSON Schema generation for frontend form building.

Generates JSON Schemas from Pydantic models so frontends can
auto-generate forms for configuration, plugin settings, etc.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_config_schema() -> Dict[str, Any]:
    """Get the full JSON Schema for experiment configuration.

    Returns:
        JSON Schema dict conforming to JSON Schema Draft 2020-12.
    """
    # Use Pydantic's model_json_schema() on the ExperimentConfig model
    pass


def get_plugin_schema(plugin_name: str) -> Dict[str, Any]:
    """Get JSON Schema for a specific plugin's configuration.

    Args:
        plugin_name: Name of the plugin.

    Returns:
        JSON Schema dict for the plugin's config model.

    Raises:
        KeyError: If plugin not found.
    """
    pass


def get_all_schemas() -> Dict[str, Dict[str, Any]]:
    """Get JSON Schemas for all registered plugin configs.

    Returns:
        Dict mapping plugin_name -> JSON Schema dict.
    """
    pass


def get_service_config_schema() -> Dict[str, Any]:
    """Get JSON Schema for the ServiceConfig model.

    Returns:
        JSON Schema dict for service configuration.
    """
    pass


def get_environment_config_schema(env_type: str) -> Dict[str, Any]:
    """Get JSON Schema for an environment config.

    Args:
        env_type: Environment type (e.g., "docker_compose", "shadow_ns").

    Returns:
        JSON Schema dict for the environment config model.
    """
    pass


def validate_against_schema(
    data: Dict[str, Any],
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate a data dict against a JSON Schema.

    Args:
        data: Data to validate.
        schema: JSON Schema to validate against.

    Returns:
        Dict with: valid (bool), errors (list of error strings).
    """
    pass
```

### Step 3: Implementation Notes

For events.py:
- The `subscribe()` function creates a lightweight observer that calls the callback.
- The `event_stream()` async generator needs an `asyncio.Queue` bridge between sync observer and async generator.
- Consider a `CallbackObserver` class that bridges the gap:

```python
class _CallbackObserver(IObserver):
    def __init__(self, callback, event_types):
        super().__init__()
        self.callback = callback
        self.event_types = event_types

    def on_event(self, event):
        if not self.event_types or type(event).__name__ in self.event_types:
            self.callback(event)

    def is_interested(self, event_type):
        return not self.event_types or event_type in self.event_types
```

For schemas.py:
- Pydantic v2 provides `model_json_schema()` on any BaseModel class.
- The schema generation should handle nested models correctly.
- Consider using `jsonschema` package for validation if available, otherwise a simple approach.

### Step 4: Write tests

```python
# tests/unit/test_api/test_api_events.py
"""Tests for panther.api.events module."""
import pytest


class TestGetEventTypes:
    def test_returns_list(self):
        from panther.api.events import get_event_types
        types = get_event_types()
        assert isinstance(types, list)


class TestSubscribe:
    def test_returns_subscription_id(self):
        from panther.api.events import subscribe
        events_received = []
        sub_id = subscribe(
            event_types=["TestCompletedEvent"],
            callback=lambda e: events_received.append(e),
        )
        assert isinstance(sub_id, str)


# tests/unit/test_api/test_api_schemas.py
"""Tests for panther.api.schemas module."""
import pytest


class TestGetConfigSchema:
    def test_returns_json_schema(self):
        from panther.api.schemas import get_config_schema
        schema = get_config_schema()
        assert isinstance(schema, dict)
        # Should have JSON Schema structure
        assert "type" in schema or "properties" in schema or "$defs" in schema


class TestGetAllSchemas:
    def test_returns_dict(self):
        from panther.api.schemas import get_all_schemas
        schemas = get_all_schemas()
        assert isinstance(schemas, dict)


class TestValidateAgainstSchema:
    def test_valid_data(self):
        from panther.api.schemas import validate_against_schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = validate_against_schema({"name": "test"}, schema)
        assert result["valid"] is True

    def test_invalid_data(self):
        from panther.api.schemas import validate_against_schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        result = validate_against_schema({}, schema)
        assert result["valid"] is False
```

## Verification
```bash
pytest tests/unit/test_api/test_api_events.py tests/unit/test_api/test_api_schemas.py -v
```

## Important Notes
- `event_stream()` is async - it requires an event loop. This is intentional for web framework integration.
- The schemas module depends on Pydantic's JSON Schema generation. Verify which Pydantic v2 method to use (`model_json_schema()` vs `schema()`).
- For `validate_against_schema()`, consider whether to make `jsonschema` an optional dependency or implement a simple validator.

## Commit Message
```
feat(api): implement events and schemas API modules

Add panther.api.events (subscribe, unsubscribe, event_stream,
get_event_types) and panther.api.schemas (JSON Schema generation
from Pydantic models for frontend form building).
```

## Files Modified
- `panther/api/events.py` (implemented)
- `panther/api/schemas.py` (implemented)
- `tests/unit/test_api/test_api_events.py` (new)
- `tests/unit/test_api/test_api_schemas.py` (new)
