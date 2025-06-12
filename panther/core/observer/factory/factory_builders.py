"""
Observer Factory Builder Methods

This module contains builder methods for creating specific observer types
with their configurations.
"""

import logging
from typing import Any

from panther.config.config_observer_schema import (
    LoggerObserverConfig,
    MetricsObserverConfig,
    StorageObserverConfig,
    ExperimentObserverConfig,
)
from panther.core.observer.base.observer_interface import IObserver
from panther.core.observer.impl import (
    LoggerObserver,
    MetricsObserver,
    StorageObserver,
    ExperimentObserver,
)
from .observer_factory import get_observer_factory


def create_logger(
    name: str | None = None,
    global_config=None,
    auto_register: bool = False,
    event_types: list | None = None,
    priority: int = 0,
    **kwargs,
) -> LoggerObserver:
    """
    Create an enhanced event-aware logger observer.

    Args:
        name: Optional name to register the observer with
        global_config: Global configuration for the logger
        auto_register: Whether to automatically register the observer with the event manager
        event_types: Optional list of event types to subscribe to if auto_register is True
        priority: Priority for observer registration if auto_register is True
        **kwargs: Additional configuration parameters

    Returns:
        LoggerObserver: Configured logger observer
    """
    factory = get_observer_factory(global_config)

    # Start with default config from observer_config if available
    logger_config = (
        factory._observer_config.logger
        if hasattr(factory, "_observer_config") and factory._observer_config
        else LoggerObserverConfig()
    )

    # Create config dictionary from the logger_config dataclass
    config = {
        "log_level": logger_config.log_level,
        "include_data": logger_config.include_data,
        "include_event_id": logger_config.include_event_id,
        "include_timestamp": logger_config.include_timestamp,
        "enable_colors": logger_config.enable_colors,
        "output_file": logger_config.output_file,
        "correlation_tracking": logger_config.correlation_tracking,
        "structured_output": logger_config.structured_output,
        "max_data_length": logger_config.max_data_length,
        "global_config": global_config,
    }

    # Override with any provided kwargs
    config.update(kwargs)

    # Use configured priority if not explicitly provided
    if priority == 0 and hasattr(logger_config, "priority"):
        priority = logger_config.priority

    # Use configured auto_register if not explicitly provided
    if not auto_register and hasattr(logger_config, "auto_register"):
        auto_register = logger_config.auto_register

    return factory.create_observer(
        "logger",
        name=name,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        **config,
    )


def create_metrics(
    name: str | None = None,
    global_config=None,
    auto_register: bool = False,
    event_types: list | None = None,
    priority: int = 0,
    output_dir: str | None = None,
    metrics_collector=None,
    **kwargs,
) -> MetricsObserver:
    """
    Create an enhanced metrics observer.

    Args:
        name: Optional name to register the observer with
        auto_register: Whether to automatically register the observer with the event manager
        event_types: Optional list of event types to subscribe to if auto_register is True
        priority: Priority for observer registration if auto_register is True
        output_dir: Output directory for metrics
        metrics_collector: Optional metrics collector instance
        **kwargs: Configuration parameters

    Returns:
        MetricsObserver: Configured metrics observer
    """
    factory = get_observer_factory()

    # Start with default config from observer_config if available
    metrics_config = (
        factory._observer_config.metrics
        if hasattr(factory, "_observer_config") and factory._observer_config
        else MetricsObserverConfig()
    )

    # Create config dictionary from the metrics_config dataclass
    config = {
        "log_level": metrics_config.log_level,
        "publish_metrics": metrics_config.publish_metrics,
        "collect_system_metrics": metrics_config.collect_system_metrics,
        "publish_interval": metrics_config.publish_interval,
        "enable_real_time_monitoring": metrics_config.enable_real_time_monitoring,
        "resource_collection_interval": metrics_config.resource_collection_interval,
        "metric_collection_interval": metrics_config.metric_collection_interval,
        "output_dir": output_dir,
        "metrics_collector": metrics_collector,
    }

    # Override with any provided kwargs
    config.update(kwargs)

    # Use configured priority if not explicitly provided
    if priority == 0 and hasattr(metrics_config, "priority"):
        priority = metrics_config.priority

    # Use configured auto_register if not explicitly provided
    if not auto_register and hasattr(metrics_config, "auto_register"):
        auto_register = metrics_config.auto_register

    return factory.create_observer(
        "metrics",
        name=name,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        **config,
    )


def create_storage(
    name: str | None = None,
    global_config=None,
    output_dir: str | None = None,
    auto_register: bool = False,
    event_types: list | None = None,
    priority: int = 0,
    **kwargs,
) -> StorageObserver:
    """
    Create an enhanced storage observer.

    Args:
        name: Optional name to register the observer with
        output_dir: Output directory for storage
        auto_register: Whether to automatically register the observer with the event manager
        event_types: Optional list of event types to subscribe to if auto_register is True
        priority: Priority for observer registration if auto_register is True
        **kwargs: Additional configuration parameters

    Returns:
        StorageObserver: Configured storage observer
    """
    factory = get_observer_factory()

    # Start with default config from observer_config if available
    storage_config = (
        factory._observer_config.storage
        if hasattr(factory, "_observer_config") and factory._observer_config
        else StorageObserverConfig()
    )

    # Create config dictionary from the storage_config dataclass
    config = {
        "log_level": storage_config.log_level,
        "storage_path": output_dir or storage_config.storage_path or "outputs",
        "auto_backup": storage_config.auto_backup,
        "enable_compression": storage_config.enable_compression,
        "max_storage_size": storage_config.max_storage_size,
        "backup_interval": storage_config.backup_interval,
        "retention_days": storage_config.retention_days,
        "batch_size": storage_config.batch_size,
    }

    # Override with any provided kwargs
    config.update(kwargs)

    # Use configured priority if not explicitly provided
    if priority == 0 and hasattr(storage_config, "priority"):
        priority = storage_config.priority

    # Use configured auto_register if not explicitly provided
    if not auto_register and hasattr(storage_config, "auto_register"):
        auto_register = storage_config.auto_register

    return factory.create_observer(
        "storage",
        name=name,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        **config,
    )


def create_experiment_observer(
    name: str | None = None,
    test_name: str | None = None,
    output_dir: str | None = None,
    global_config: Any = None,
    auto_register: bool = False,
    event_types: list | None = None,
    priority: int = 0,
    **kwargs,
) -> ExperimentObserver:
    """
    Create an enhanced experiment observer.

    Args:
        name: Optional name to register the observer with
        test_name: Name of the test being observed
        output_dir: Output directory path
        global_config: Global configuration object
        auto_register: Whether to automatically register the observer with the event manager
        event_types: Optional list of event types to subscribe to if auto_register is True
        priority: Priority for observer registration if auto_register is True
        **kwargs: Additional configuration parameters

    Returns:
        ExperimentObserver: Configured experiment observer
    """
    factory = get_observer_factory(global_config)

    # Start with default config from observer_config if available
    exp_config = (
        factory._observer_config.experiment
        if hasattr(factory, "_observer_config") and factory._observer_config
        else ExperimentObserverConfig()
    )

    # Create config dictionary from the exp_config dataclass
    config = {
        "log_level": exp_config.log_level,
        "output_dir": output_dir or exp_config.output_dir or "outputs",
        "test_name": test_name or exp_config.test_name,
        "track_timing": exp_config.track_timing,
        "track_steps": exp_config.track_steps,
        "global_config": global_config,
    }

    # Override with any provided kwargs
    config.update(kwargs)

    # Use configured priority if not explicitly provided
    if priority == 0 and hasattr(exp_config, "priority"):
        priority = exp_config.priority

    # Use configured auto_register if not explicitly provided
    if not auto_register and hasattr(exp_config, "auto_register"):
        auto_register = exp_config.auto_register

    return factory.create_observer(
        "experiment",
        name=name,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        **config,
    )


def create_default_observer_set(config: dict[str, Any]) -> list[IObserver]:
    """
    Create a default set of observers based on configuration.

    Args:
        config: Framework configuration dictionary

    Returns:
        List of configured observer instances
    """
    factory = get_observer_factory()
    observers = []

    # Get global configuration if available
    global_config = config.get("global_config", None)
    output_dir = config.get("paths", {}).get("output_dir", "outputs")
    test_name = config.get("test_name", None)

    # Always create enhanced logger
    logger_config = config.get("observer", {}).get("logger", {})
    logger_obs = create_logger(
        name="default_logger",
        log_level=config.get("logging", {}).get("level", "INFO"),
        global_config=global_config,
        **logger_config,
    )
    observers.append(logger_obs)

    # Create metrics observer if enabled
    metrics_config = config.get("observer", {}).get("metrics", {})
    if metrics_config.get("enabled", False):
        metrics_obs = create_metrics(
            name="default_metrics", output_dir=output_dir, **metrics_config
        )
        observers.append(metrics_obs)

    # Create storage observer if enabled
    storage_config = config.get("observer", {}).get("storage", {})
    if storage_config.get("enabled", False):
        storage_obs = create_storage(
            name="default_storage", output_dir=output_dir, **storage_config
        )
        observers.append(storage_obs)

    # Always create experiment observer for tracking and coordination
    experiment_config = config.get("observer", {}).get("experiment", {})
    experiment_obs = create_experiment_observer(
        name="default_experiment",
        test_name=test_name,
        output_dir=output_dir,
        global_config=global_config,
        **experiment_config,
    )
    observers.append(experiment_obs)

    # Register with event manager if available
    if factory._event_manager:
        for observer in observers:
            factory._event_manager.register_observer(observer)

    logger = logging.getLogger(__name__)
    logger.info("Created default observer set with %d observers", len(observers))
    return observers
