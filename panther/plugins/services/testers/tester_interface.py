from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.services.testers.tester_event_methods import TesterManagerEventMixin


class ITesterManager(IServiceManager, TesterManagerEventMixin):
    """
    Interface for tester service managers.

    Extends ServiceBase (which already includes TesterManagerEventMixin) with standardized
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
        self._status = {
            "state": "created",
            "details": {},
        }
        self.test_results = {}

    def run_tests(self):
        """
        Run tests with proper event notifications.

        Returns:
            Dict: Test results
        """
        try:
            # Notify test run started
            test_name = getattr(self, "test_to_compile", "unknown")
            self.notify_test_started(
                test_name=test_name,
                details={
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Run the tests
            results = self._do_run_tests()

            # Notify test run completed
            self.emit_test_completed(
                test_name=test_name, success=results.get("success", False), results=results
            )

            return results
        except Exception as e:  # pylint: disable=broad-except
            # Notify test run failed
            self.emit_test_completed(
                test_name=getattr(self, "test_to_compile", "unknown"),
                success=False,
                results={"error": str(e), "error_type": type(e).__name__},
            )
            raise

    def _do_run_tests(self):
        """
        Actual implementation of test running, to be overridden by subclasses.

        Returns:
            Dict: Test results containing at minimum a 'success' key with boolean value

        Raises:
            NotImplementedError: If the subclass does not implement this method
        """
        raise NotImplementedError("Subclasses must implement _do_run_tests")
