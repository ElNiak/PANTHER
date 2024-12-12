from abc import ABC
import os
import logging


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

    def __init__(self, output_dir: str, experiment_name: str):
        self.next_handler = None
        self.output_dir = os.path.join(output_dir, experiment_name)
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info(f"Results will be saved to {self.output_dir}")
        self.log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

    def set_next_handler(self, handler) -> None:
        self.next_handler = handler

    def handle(self, request) -> None:
        if self.next_handler:
            self.next_handler.handle(request)
        else:
            print("No handler found for request")
