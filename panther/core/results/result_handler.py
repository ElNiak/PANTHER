import logging
import os
from abc import ABC


class ResultHandler(ABC):
    """
    Abstract base class for result processing handlers in PANTHER's chain-of-responsibility system.

    This class establishes the foundation for all result processing implementations, providing
    the core infrastructure for chaining handlers together and managing output directories.
    It implements the chain-of-responsibility pattern to enable flexible, composable
    result processing pipelines.

    ## Design Pattern

    The ResultHandler implements the classic chain-of-responsibility pattern:

    ```mermaid
    graph LR
        A[Result] --> B[Handler1]
        B --> C[Handler2]
        C --> D[Handler3]
        D --> E[HandlerN]

        B -.-> F[Process & Pass]
        C -.-> G[Process & Pass]
        D -.-> H[Process & Pass]
        E -.-> I[Process & End]
    ```

    ## Core Responsibilities

    ### 1. **Chain Management**
    - Maintains reference to the next handler in the processing chain
    - Supports dynamic chain construction and modification
    - Enables parallel processing branches through multiple next handlers
    - Provides chain traversal and execution coordination

    ### 2. **Output Directory Infrastructure**
    - Creates and manages experiment-specific output directories
    - Establishes consistent directory structure across all handlers
    - Provides log directory organization and file path management
    - Ensures proper permissions and directory existence

    ### 3. **Result Processing Framework**
    - Defines abstract interface for result processing implementations
    - Enables specialized processing logic in concrete handler classes
    - Supports error handling and recovery mechanisms
    - Provides consistent logging and monitoring integration

    ## Implementation Guidelines

    Concrete handler implementations should:

    ### Processing Logic
    ```python
    def handle(self, request) -> None:
        # 1. Perform handler-specific processing
        processed_result = self._process_result(request)

        # 2. Store or output results as needed
        self._store_result(processed_result)

        # 3. Pass to next handler if present
        if self.next_handler:
            self.next_handler.handle(processed_result)
    ```

    ### Error Handling
    ```python
    def handle(self, request) -> None:
        try:
            # Processing logic
            self._process_result(request)
        except Exception as e:
            logging.error(f"Handler {self.__class__.__name__} failed: {e}")
            # Continue chain even on failure
            if self.next_handler:
                self.next_handler.handle(request)
    ```

    ## Directory Structure

    Each handler automatically creates a standardized directory structure:

    ```
    {output_dir}/{experiment_name}/
    ├── logs/                    # Log files and processing records
    ├── results/                 # Processed result outputs
    ├── artifacts/               # Generated artifacts and reports
    └── metadata/                # Handler metadata and configuration
    ```

    ## Usage Patterns

    ### Basic Handler Chain Setup
    ```python
    # Create handlers
    validator = ValidationHandler(output_dir, "experiment_001")
    parser = ParserHandler(output_dir, "experiment_001")
    storage = LocalStorageHandler(output_dir, "experiment_001")

    # Chain handlers together
    validator.set_next_handler(parser)
    parser.set_next_handler(storage)

    # Process result through chain
    result = {"type": "quic_test", "data": {...}}
    validator.handle(result)
    ```

    ### Parallel Processing Branches
    ```python
    # Create parallel processing branches
    validator.set_next_handler(parser)
    parser.set_next_handler(storage)
    parser.set_next_handler(analyzer)  # Parallel branch
    ```

    ## Performance Considerations

    - **Directory Creation**: One-time cost during handler initialization
    - **Chain Traversal**: O(n) where n is chain length, typically 3-5 handlers
    - **Memory Usage**: O(1) per handler, minimal overhead for chain management
    - **I/O Operations**: Handlers should optimize file operations and batch writes

    ## Thread Safety

    - **Handler State**: Each handler instance maintains its own state and directories
    - **Chain Modification**: Not thread-safe - set up chains before concurrent use
    - **Result Processing**: Individual handle() calls should be thread-safe in implementations

    This base class enables the construction of flexible, maintainable result processing
    systems that can be easily extended and reconfigured for different testing scenarios.
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
