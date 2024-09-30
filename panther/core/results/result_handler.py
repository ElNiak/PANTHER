
from abc import ABC


class ResultHandler(ABC):
    """
    Abstract base class for handling results in a chain of responsibility pattern.
    Attributes:
        next_handler (ResultHandler): The next handler in the chain.
    Methods:
        __init__() -> None:
            Initializes the ResultHandler with no next handler.
        set_next_handler(handler: ResultHandler) -> None:
            Sets the next handler in the chain.
        handle(request) -> None:
            Handles the request or passes it to the next handler in the chain.
    """
    
    def __init__(self) -> None:
        self.next_handler = None
    
    def set_next_handler(self, handler) -> None:
        self.next_handler = handler
        
    def handle(self, request) -> None:
        if self.next_handler:
            self.next_handler.handle(request)
        else:
            print("No handler found for request")