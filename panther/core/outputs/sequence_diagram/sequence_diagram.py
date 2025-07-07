"""
PlantUML Sequence Diagram Generator for PANTHER Protocol Analysis

This module provides runtime sequence diagram generation capabilities for analyzing
protocol interactions and execution flows within PANTHER testing environments.
It generates PlantUML-compatible sequence diagrams by intercepting method calls
and tracking execution context.

## Architecture Purpose

The sequence diagram generator serves critical debugging and analysis purposes:

1. **Protocol Flow Analysis**: Visualizes message exchanges between protocol components
2. **Execution Tracing**: Tracks method invocation patterns across service boundaries
3. **Debugging Support**: Provides execution context for complex protocol behaviors
4. **Documentation Generation**: Automatically creates sequence diagrams for protocol specs

## Usage Patterns

```python
# Enable sequence generation
from panther.core.outputs.sequence_diagram import SequenceOn as Seq

class QuicClient:
    def send_handshake(self):
        seq = Seq("QuicClient")  # Tracks this method call
        seq.note("Initiating QUIC handshake")
        # ... handshake logic
        # Auto-generates: QuicClient -> QuicServer ++: send_handshake

# Disable tracing (performance mode)
from panther.core.outputs.sequence_diagram import SequenceOff as Seq
```

## PlantUML Integration

Generated output follows PlantUML syntax for easy integration with documentation:
- `autonumber` enables automatic sequence numbering
- `->` represents method calls between participants
- `++` indicates activation/deactivation
- `note over` adds contextual annotations

## Performance Considerations

- **SequenceOn**: Full tracing with frame inspection overhead
- **SequenceOff**: No-op implementation for production environments
- Frame inspection uses `sys._getframe()` for caller/callee detection
- Output is printed directly for minimal memory footprint

This enables seamless toggling between development tracing and production performance.
"""

import sys


class SequenceOn:
    """
    Active sequence diagram generator that traces method calls and produces PlantUML output.

    This class uses Python frame inspection to automatically detect caller/callee relationships
    and generates PlantUML sequence diagram syntax. It maintains global state for autonumbering
    and initialization to ensure consistent diagram formatting.

    ## Key Features
    - **Automatic participant detection**: Extracts class names from execution frames
    - **Activation tracking**: Shows method activation/deactivation with ++/-- notation
    - **Note annotations**: Supports contextual notes within the sequence flow
    - **Global autonumbering**: Enables sequential numbering across all method calls

    ## Implementation Details
    - Uses `sys._getframe()` to inspect call stack (caller at frame 2, callee at frame 1)
    - Detects class context via `self` in frame locals
    - Outputs PlantUML syntax directly to stdout for real-time diagram generation
    - Maintains singleton-like behavior for autonumber initialization
    """

    autonumber = True
    init_done = False


def __init__(self, participant=""):
    if not SequenceOn.init_done:
        # activate if requested only once
        if SequenceOn.autonumber:
            print("autonumber")

        SequenceOn.init_done = True

    # retrieve callee frame
    callee_frame = sys._getframe(1)

    # method/function name
    self.__funcName = callee_frame.f_code.co_name

    # look for a class name
    if "self" in callee_frame.f_locals:
        self.__className = callee_frame.f_locals["self"].__class__.__name__
    else:
        self.__className = participant

    # retrieve the caller frame and class name of the caller
    caller_frame = sys._getframe(2)

    if "self" in caller_frame.f_locals:
        self.__caller = caller_frame.f_locals["self"].__class__.__name__
    else:
        self.__caller = ""

    # print the plantuml message
    activate = "++" if self.__caller != self.__className else ""
    print(f"{self.__caller} -> {self.__className} {activate} :{self.__funcName}")


def __del__(self):
    """print the return message upon destruction"""
    if self.__caller != self.__className:
        print(f"{self.__caller} <-- {self.__className} -- ")


def note(self, msg):
    print(f"note over {self.__className}:{msg}")


class SequenceOff:
    """
    No-operation sequence diagram implementation for production environments.

    This class provides the same interface as SequenceOn but with zero-overhead
    no-op implementations. It enables seamless toggling between development tracing
    and production performance without code changes.

    ## Performance Benefits
    - **Zero overhead**: All methods are empty and compile to minimal bytecode
    - **No frame inspection**: Avoids costly `sys._getframe()` calls
    - **No I/O operations**: No stdout writes or file operations
    - **Minimal memory**: No state tracking or string formatting

    ## Usage Pattern
    ```python
    # Development mode - full tracing
    from panther.core.outputs.sequence_diagram import SequenceOn as Seq

    # Production mode - zero overhead
    from panther.core.outputs.sequence_diagram import SequenceOff as Seq

    # Usage remains identical
    def protocol_method(self):
        seq = Seq("ProtocolHandler")
        seq.note("Processing protocol message")
        # ... implementation
    ```

    This pattern allows protocol testing code to maintain tracing instrumentation
    while eliminating performance impact in production deployments.
    """

    def __init__(self, participant=""):
        pass

    def __call__(self, msg):
        pass

    def note(self, msg):
        pass
