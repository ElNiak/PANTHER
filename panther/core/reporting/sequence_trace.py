"""PlantUML Sequence Diagram Generator for PANTHER Protocol Analysis.

Optional debugging tool that traces method calls and generates PlantUML
sequence diagram syntax. Uses ``sys._getframe()`` for caller/callee detection.

Usage::

    # Development mode - full tracing
    from panther.core.reporting.sequence_trace import SequenceOn as Seq

    # Production mode - zero overhead
    from panther.core.reporting.sequence_trace import SequenceOff as Seq

    class QuicClient:
        def send_handshake(self):
            seq = Seq("QuicClient")
            seq.note("Initiating QUIC handshake")
            # Auto-generates: QuicClient -> QuicServer ++: send_handshake
"""

import sys


class SequenceOn:
    """Active sequence diagram generator that traces method calls and produces PlantUML output.

    Uses Python frame inspection to detect caller/callee relationships and
    generates PlantUML sequence diagram syntax on stdout.
    """

    autonumber = True
    init_done = False

    def __init__(self, participant=""):
        """Initialize active sequence tracer with optional participant name."""
        if not SequenceOn.init_done:
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
        """Print the return message upon destruction."""
        if self.__caller != self.__className:
            print(f"{self.__caller} <-- {self.__className} -- ")

    def note(self, msg):
        """Print a contextual annotation in the sequence diagram."""
        print(f"note over {self.__className}:{msg}")


class SequenceOff:
    """No-op sequence diagram implementation for production environments.

    Same interface as SequenceOn with zero overhead.
    """

    def __init__(self, participant=""):
        """Initialize no-op sequence tracer."""

    def __call__(self, msg):
        """No-op callable."""

    def note(self, msg):
        """No-op note."""
