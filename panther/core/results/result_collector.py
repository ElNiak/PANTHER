from typing import Dict, List

from panther.core.results.result_handler import ResultHandler


class ResultCollector:
    """Type-based handler registry that dispatches results to registered handlers.

    Maintains a dict mapping result type strings to lists of ResultHandler instances.
    When collect() is called, it looks up handlers by the result's "type" key and
    calls handle() on each registered handler for that type.
    """

    def __init__(self) -> None:
        self.handlers: Dict[str, List[ResultHandler]] = {}

    def register_handler(self, result_type: str, handler: ResultHandler) -> None:
        """Registers a handler for a specific result type."""
        if result_type not in self.handlers:
            self.handlers[result_type] = []
        self.handlers[result_type].append(handler)

    def collect(self, result: dict) -> None:
        # TODO
        for handler in self.handlers.get(result.get("type"), []):
            handler.handle(result)
