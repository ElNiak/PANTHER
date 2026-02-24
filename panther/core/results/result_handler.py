import logging
import os
from abc import ABC


class ResultHandler(ABC):
    """Abstract base for chain-of-responsibility result handlers.

    On init, creates output_dir ({output_dir}/{experiment_name}/) and a logs/
    subdirectory. Provides set_next_handler() to chain handlers together.
    The default handle() delegates to next_handler or prints a warning if
    no handler is set. Subclasses override handle() to process results.
    """

    def __init__(self, output_dir: str, experiment_name: str):
        self.next_handler = None
        self.output_dir = os.path.join(output_dir, experiment_name)
        os.makedirs(self.output_dir, exist_ok=True)
        logging.info("Results will be saved to %s", self.output_dir)
        self.log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

    def set_next_handler(self, handler) -> None:
        self.next_handler = handler

    def handle(self, request) -> None:
        if self.next_handler:
            self.next_handler.handle(request)
        else:
            print("No handler found for request")
