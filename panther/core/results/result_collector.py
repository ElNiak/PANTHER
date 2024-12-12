from panther.core.results.result_handler import ResultHandler


class ResultCollector:
    """
    ResultCollector is responsible for collecting and processing results using registered handlers.
    Attributes:
        handlers (Dict[str, List[ResultHandler]]): A dictionary mapping result types to lists of result handlers.
    Methods:
        __init__():
            Initializes the ResultCollector with an empty handlers dictionary.
        collect(result: Dict) -> None:
            Processes the given result using the appropriate handlers based on the result type.
            Args:
                result (Dict): The result to be processed, which should contain a 'type' key to determine the handlers.
    """

    def __init__(self) -> None:
        self.handlers: dict[str, list[ResultHandler]] = {}

    def register_handler(self, result_type: str, handler: ResultHandler) -> None:
        """Registers a handler for a specific result type."""
        if result_type not in self.handlers:
            self.handlers[result_type] = []
        self.handlers[result_type].append(handler)

    def collect(self, result: dict) -> None:
        # TODO
        for handler in self.handlers.get(result.get("type"), []):
            handler.handle(result)
