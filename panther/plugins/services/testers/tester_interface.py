from abc import ABC

from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.observer.event_manager import EventManager
from panther.plugins.services.service_base import ServiceBase
from panther.core.observer.event_emitter import EventEmitter


class ITesterManager(ServiceBase, ABC):
    """
    Interface for tester service managers.

    Extends ServiceBase (which already includes ServiceManagerEventMixin) with standardized
    test run reporting and monitoring capabilities.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: EventManager | None = None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        # Will be set by plugin manager when the service is created
        self.event_emitter = None if event_manager is None else EventEmitter(event_manager)

    def notify_test_started(self, test_name: str, details: dict = None):
        """
        Notify that a test has started.

        Args:
            test_name: The name of the test being run
            details: Additional details about the test
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            test_details = {
                "service_name": self.service_name,
                "service_type": self.service_type,
                "protocol": self.protocol.name,
                "test_name": test_name,
                **(details or {}),
            }
            self.event_emitter.emit_test_event("test_started", test_details)

    def notify_test_completed(self, test_name: str, success: bool, result: dict = None):
        """
        Notify that a test has completed.

        Args:
            test_name: The name of the test that completed
            success: Whether the test was successful
            result: The test result data
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            test_details = {
                "service_name": self.service_name,
                "service_type": self.service_type,
                "protocol": self.protocol.name,
                "test_name": test_name,
                "success": success,
                "result": result or {},
            }
            self.event_emitter.emit_test_event("test_completed", test_details)

    def notify_test_error(self, test_name: str, error_message: str, error_details: dict = None):
        """
        Notify that a test has encountered an error.

        Args:
            test_name: The name of the test that failed
            error_message: The error message
            error_details: Additional details about the error
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            error_info = {
                "service_name": self.service_name,
                "service_type": self.service_type,
                "protocol": self.protocol.name,
                "test_name": test_name,
                "error_message": error_message,
                **(error_details or {}),
            }
            self.event_emitter.emit_test_event("test_error", error_info)
