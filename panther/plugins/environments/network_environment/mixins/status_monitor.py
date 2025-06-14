"""Mixin for consistent status monitoring and logging."""

import socket
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional


class ServiceStatus(Enum):
    """Service status enumeration."""

    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceHealthCheck:
    """Health check result for a service."""

    status: ServiceStatus
    is_healthy: bool
    message: str
    check_time: float
    details: Optional[Dict[str, Any]] = None


class StatusMonitorMixin:
    """
    Mixin providing consistent status monitoring and logging functionality.

    This mixin eliminates duplicated monitoring patterns across network environments.
    """

    def monitor_service_status(
        self,
        service_name: str,
        check_interval: int = 5,
        timeout: int = 60,
        ready_check: Optional[Callable[[], bool]] = None,
    ) -> ServiceHealthCheck:
        """
        Monitor service status until ready or timeout.

        Args:
            service_name: Name of the service to monitor
            check_interval: Seconds between status checks
            timeout: Maximum seconds to wait for service
            ready_check: Optional custom readiness check function

        Returns:
            ServiceHealthCheck with final status
        """
        start_time = time.time()

        self.logger.info(
            f"Monitoring service '{service_name}' status (timeout: {timeout}s)"
        )

        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time

            # Perform health check
            health = self._check_service_health(service_name, ready_check)

            if health.is_healthy and health.status == ServiceStatus.READY:
                self.logger.info(
                    f"Service '{service_name}' is ready after {elapsed:.1f}s"
                )
                return health

            # Log progress
            self.logger.debug(
                f"Service '{service_name}' status: {health.status.value} "
                f"({elapsed:.1f}s elapsed)"
            )

            # Check for failure
            if health.status == ServiceStatus.FAILED:
                self.logger.error(f"Service '{service_name}' failed: {health.message}")
                return health

            # Wait before next check
            time.sleep(check_interval)

        # Timeout reached
        return ServiceHealthCheck(
            status=ServiceStatus.FAILED,
            is_healthy=False,
            message=f"Service did not become ready within {timeout}s",
            check_time=time.time() - start_time,
        )

    def _check_service_health(
        self,
        service_name: str,
        custom_check: Optional[Callable[[], bool]] = None,
    ) -> ServiceHealthCheck:
        """
        Perform a health check on a service.

        Args:
            service_name: Name of the service
            custom_check: Optional custom health check function

        Returns:
            ServiceHealthCheck result
        """
        check_start = time.time()

        try:
            # Use custom check if provided
            if custom_check:
                is_ready = custom_check()
                return ServiceHealthCheck(
                    status=ServiceStatus.READY if is_ready else ServiceStatus.STARTING,
                    is_healthy=is_ready,
                    message="Custom check " + ("passed" if is_ready else "not ready"),
                    check_time=time.time() - check_start,
                )

            # Default: check if service process exists
            if hasattr(self, "check_process_status"):
                status = self.check_process_status(service_name)
                return ServiceHealthCheck(
                    status=status,
                    is_healthy=status in [ServiceStatus.RUNNING, ServiceStatus.READY],
                    message=f"Process status: {status.value}",
                    check_time=time.time() - check_start,
                )

            # Fallback to unknown
            return ServiceHealthCheck(
                status=ServiceStatus.UNKNOWN,
                is_healthy=False,
                message="No health check available",
                check_time=time.time() - check_start,
            )

        except Exception as e:
            return ServiceHealthCheck(
                status=ServiceStatus.FAILED,
                is_healthy=False,
                message=f"Health check error: {e}",
                check_time=time.time() - check_start,
            )

    def wait_for_port(
        self,
        host: str,
        port: int,
        timeout: int = 60,
        check_interval: int = 1,
    ) -> bool:
        """
        Wait for a network port to become available.

        Args:
            host: Host to check
            port: Port number to check
            timeout: Maximum time to wait
            check_interval: Seconds between checks

        Returns:
            True if port becomes available, False on timeout
        """
        start_time = time.time()

        self.logger.info(f"Waiting for {host}:{port} to become available")

        while time.time() - start_time < timeout:
            try:
                # Try to connect
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    elapsed = time.time() - start_time
                    self.logger.info(
                        f"Port {host}:{port} is ready after {elapsed:.1f}s"
                    )
                    return True

            except Exception as e:
                self.logger.debug(f"Port check error: {e}")

            time.sleep(check_interval)

        self.logger.error(
            f"Port {host}:{port} did not become available within {timeout}s"
        )
        return False

    def log_deployment_progress(
        self,
        stage: str,
        details: Dict[str, Any],
        level: str = "info",
    ) -> None:
        """
        Log deployment progress with consistent formatting.

        Args:
            stage: Current deployment stage
            details: Additional details to log
            level: Log level (info, debug, warning, error)
        """
        # Format details
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())

        # Get logger method
        log_method = getattr(self.logger, level, self.logger.info)

        # Log with consistent format
        log_method(f"[{stage}] {detail_str}")

    def monitor_resource_usage(
        self,
        service_name: str,
        container_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Monitor resource usage for a service.

        Args:
            service_name: Name of the service
            container_name: Optional Docker container name

        Returns:
            Dictionary with resource usage information
        """
        usage = {
            "service": service_name,
            "timestamp": time.time(),
        }

        try:
            if container_name and hasattr(self, "execute_docker_command"):
                # Get Docker stats
                result = self.execute_docker_command(
                    ["stats", "--no-stream", "--format", "json", container_name],
                    check=False,
                )

                if result.returncode == 0 and result.stdout:
                    import json

                    stats = json.loads(result.stdout)
                    usage.update(
                        {
                            "cpu_percent": stats.get("CPUPerc", "N/A"),
                            "memory_usage": stats.get("MemUsage", "N/A"),
                            "network_io": stats.get("NetIO", "N/A"),
                        }
                    )

        except Exception as e:
            self.logger.debug(f"Error collecting resource usage: {e}")
            usage["error"] = str(e)

        return usage

    def create_status_report(
        self,
        services: Dict[str, ServiceStatus],
        include_resources: bool = False,
    ) -> str:
        """
        Create a formatted status report for all services.

        Args:
            services: Dictionary of service names to status
            include_resources: Whether to include resource usage

        Returns:
            Formatted status report string
        """
        lines = ["=" * 60, "Service Status Report", "=" * 60]

        # Add timestamp
        lines.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Add service status
        for service, status in services.items():
            status_symbol = "✓" if status == ServiceStatus.READY else "✗"
            lines.append(f"{status_symbol} {service}: {status.value}")

            # Add resource usage if requested
            if include_resources:
                usage = self.monitor_resource_usage(service)
                if "cpu_percent" in usage:
                    lines.append(f"  CPU: {usage['cpu_percent']}")
                    lines.append(f"  Memory: {usage['memory_usage']}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def track_deployment_metrics(self) -> Dict[str, Any]:
        """
        Track deployment metrics for analysis.

        Returns:
            Dictionary of deployment metrics
        """
        metrics = {}

        # Calculate setup time
        if hasattr(self, "setup_start_time") and hasattr(self, "setup_end_time"):
            metrics["setup_duration"] = self.setup_end_time - self.setup_start_time

        # Calculate deployment time
        if hasattr(self, "deployment_start_time") and hasattr(
            self, "deployment_end_time"
        ):
            metrics["deployment_duration"] = (
                self.deployment_end_time - self.deployment_start_time
            )

        # Count services
        if hasattr(self, "services_managers"):
            metrics["service_count"] = len(self.services_managers)

        # Add environment info
        metrics["environment_type"] = getattr(self, "env_sub_type", "unknown")

        return metrics
