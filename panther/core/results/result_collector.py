
from typing import Callable, Dict, List
from core.results.result_handler import ResultHandler


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
        self.handlers: Dict[str, List[ResultHandler]] = {}
        
    def collect(self, result: Dict) -> None:
        # TODO 
        for handler in self.handlers.get(result.get('type'), []):
            handler.handle(result)