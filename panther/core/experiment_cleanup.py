"""Experiment cleanup and resource teardown.

Provides ExperimentCleanupMixin with methods for cleaning up experiment
resources including observers, event handlers, metrics, and Docker resources.
"""

from panther.core.observer.factory import get_observer_factory


class ExperimentCleanupMixin:
    """Mixin providing experiment cleanup and resource teardown.

    Expects the host class to provide:
        - self.logger
        - self.experiment_name, self.experiment_dir
        - self.event_manager
        - self.metrics_collector
        - self.log_statistics_display
        - self.workflow_tracker
        - self._generate_final_log_report()
        - self._generate_experiment_report()
    """

    def cleanup(self):
        """Clean up resources including observers and event handlers.

        Each cleanup step has its own error handling so that a failure in one
        step does not prevent subsequent steps (e.g., metrics export) from running.
        """
        self.logger.info("Starting experiment cleanup")

        # Generate final log statistics report if enabled
        try:
            self._generate_final_log_report()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to generate final log report: %s", e)

        # Stop log statistics display if running
        try:
            if self.log_statistics_display and self.log_statistics_display.running:
                self.log_statistics_display.stop_display()
                self.logger.info("Stopped log statistics display")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to stop log statistics display: %s", e)

        # Clean up state observer
        try:
            if hasattr(self, "state_observer"):
                self.event_manager.unregister_observer(self.state_observer)
                self.logger.debug("Unregistered StateEventObserver")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to unregister state observer: %s", e)

        # Clean up other observers through factory
        try:
            factory = get_observer_factory()
            observer_names = [
                "experiment_logger",
                "experiment_metrics",
                "experiment_observer",
            ]
            for observer_name in observer_names:
                if factory.unregister_observer(observer_name):
                    self.logger.debug("Unregistered %s", observer_name)
                else:
                    self.logger.debug(
                        "%s was not registered or already removed", observer_name
                    )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to unregister observers: %s", e)

        # Clear workflow tracker states for this experiment
        try:
            if hasattr(self, "workflow_tracker"):
                self.workflow_tracker.clear_workflow_state(self.experiment_name)
                self.logger.debug("Cleared workflow state for experiment")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to clear workflow state: %s", e)

        # Generate experiment report
        try:
            self._generate_experiment_report()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to generate report: %s", e)

        # Export metrics to disk if collector is present
        if self.metrics_collector is not None:
            try:
                from panther.core.metrics import MetricsExporter

                self.metrics_collector.finalize()
                exporter = MetricsExporter(self.metrics_collector)
                metrics_dir = self.experiment_dir / "metrics"
                metrics_dir.mkdir(parents=True, exist_ok=True)
                exporter.export_to_json(metrics_dir / "metrics.json")
                exporter.export_to_csv(metrics_dir)
                self.logger.info("Metrics exported to: %s", metrics_dir)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("Failed to export metrics: %s", e)

        # Clean up empty directories from the experiment output tree
        try:
            from panther.core.outputs.output_cleanup import remove_empty_directories

            removed = remove_empty_directories(self.experiment_dir)
            if removed:
                self.logger.info(
                    "Cleaned %d empty directories from experiment output", removed
                )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Empty directory cleanup failed: %s", e, exc_info=True)

        # Clean up stale Docker resources (dangling images, exited containers, orphan volumes)
        try:
            self._cleanup_docker_resources()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Docker resource cleanup failed: %s", e)

    def _cleanup_docker_resources(self):
        """Remove stale Docker resources left over from the experiment.

        Cleans up dangling images, exited panther containers, and orphaned
        panther volumes. Each step is independent so a failure in one does
        not block the others.
        """
        from panther.core.docker_builder import DockerBuilder

        try:
            builder = DockerBuilder.get_instance(enable_cache=False)
        except Exception:
            self.logger.debug("DockerBuilder unavailable, skipping Docker cleanup")
            return

        if not builder.is_docker_available():
            self.logger.debug("Docker daemon unavailable, skipping Docker cleanup")
            return

        client = builder.client
        cleaned = []

        # 1. Remove dangling images (<none>:<none>)
        try:
            if builder.remove_dangling_images():
                cleaned.append("dangling images")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Dangling image cleanup failed: %s", e)

        # 2. Remove exited containers with panther label
        try:
            exited = client.containers.list(
                all=True,
                filters={"status": "exited", "label": "panther"},
            )
            for container in exited:
                container.remove(force=True)
            if exited:
                cleaned.append(f"{len(exited)} exited containers")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Exited container cleanup failed: %s", e)

        # 3. Remove orphaned panther volumes
        try:
            volumes = client.volumes.list(filters={"name": "panther"})
            removed_count = 0
            for volume in volumes:
                try:
                    volume.remove()
                    removed_count += 1
                except Exception as e:
                    self.logger.debug("Could not remove volume %s: %s", volume.name, e)
            if removed_count:
                cleaned.append(f"{removed_count} orphaned volumes")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.debug("Volume cleanup failed: %s", e)

        if cleaned:
            self.logger.info("Docker cleanup: removed %s", ", ".join(cleaned))
