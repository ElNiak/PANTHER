"""Debug Command.

Developer introspection tools for the PANTHER event and observer systems.
"""

import click
from termcolor import colored

from panther.cli.core.base import (
    featured_example,
    handle_errors,
    pass_context_and_setup_logging,
)


@featured_example("panther debug events list-types")
@click.group()
def debug():
    r"""Developer debugging and introspection tools.

    Inspect PANTHER internals: event types, emitters, observers.

    \b
    Examples:
      panther debug events list-types       # List event types
      panther debug events list-emitters    # List event emitters
      panther debug observers list-types    # List observer types
    """


@debug.group()
def events():
    """Inspect the event system."""


@events.command("list-types")
@handle_errors
@pass_context_and_setup_logging
def list_event_types(_ctx):
    """List all known event types with importance levels."""
    from panther.core.events.event_summarizer import EventSummarizer

    event_types = EventSummarizer.IMPORTANT_EVENT_TYPES
    batchable = EventSummarizer.BATCHABLE_EVENTS

    click.echo(colored("Event Types:", "blue", attrs=["bold"]))
    click.echo(f"  {'Event Type':<45} {'Importance':<12} {'Batchable'}")
    click.echo("  " + "-" * 70)

    for event_type, importance in sorted(event_types.items()):
        batch_flag = "yes" if event_type in batchable else ""
        click.echo(f"  {event_type:<45} {importance.name:<12} {batch_flag}")

    click.echo()
    click.echo(f"Total: {len(event_types)} event types, {len(batchable)} batchable")


@events.command("list-emitters")
@handle_errors
@pass_context_and_setup_logging
def list_emitters(_ctx):
    """List registered event emitter types."""
    from panther.core.events.assertion.emitter import AssertionEventEmitter
    from panther.core.events.environment.emitter import EnvironmentEventEmitter
    from panther.core.events.experiment.emitter import ExperimentEventEmitter
    from panther.core.events.metrics.emitter import MetricsEventEmitter
    from panther.core.events.plugin.emitter import PluginEventEmitter
    from panther.core.events.service.emitter import ServiceEventEmitter
    from panther.core.events.step.emitter import StepEventEmitter
    from panther.core.events.test.emitter import TestEventEmitter

    # These are the emitter types managed by EmitterRegistry.get_emitter()
    emitter_map = {
        "experiment": ExperimentEventEmitter,
        "service": ServiceEventEmitter,
        "environment": EnvironmentEventEmitter,
        "step": StepEventEmitter,
        "plugin": PluginEventEmitter,
        "assertion": AssertionEventEmitter,
        "metrics": MetricsEventEmitter,
        "test": TestEventEmitter,
    }

    click.echo(colored("Event Emitters:", "blue", attrs=["bold"]))
    click.echo(f"  {'Category':<20} {'Class'}")
    click.echo("  " + "-" * 55)

    for category, cls in sorted(emitter_map.items()):
        click.echo(f"  {category:<20} {cls.__module__}.{cls.__name__}")

    click.echo()
    click.echo(f"Total: {len(emitter_map)} emitter types")
    click.echo()
    click.echo("Note: 'test' emitters are created on demand (one per test case).")


@debug.group()
def observers():
    """Inspect the observer system."""


@observers.command("list-types")
@handle_errors
@pass_context_and_setup_logging
def list_observer_types(_ctx):
    """List available observer types."""
    from panther.core.observer.factory import ObserverFactory

    factory = ObserverFactory()
    available = factory.get_available_types()
    registered_types = factory._registered_types

    click.echo(colored("Observer Types:", "blue", attrs=["bold"]))
    click.echo(f"  {'Type Name':<20} {'Class'}")
    click.echo("  " + "-" * 55)

    for type_name in sorted(available):
        cls = registered_types[type_name]
        click.echo(f"  {type_name:<20} {cls.__module__}.{cls.__name__}")

    click.echo()
    click.echo(f"Total: {len(available)} observer types")
