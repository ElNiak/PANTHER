"""Turn a test run into ``runtime`` anchors.

``runtime`` is the strongest evidence class the promotion rule recognises and,
short of a developer signature, the only route that moves
``checked_fraction_by_req_class`` off zero. Producing one was entirely manual,
which made the metric aspirational: a reconstruction could be measured against
a number nothing in the package could raise.

This package closes that. It reads a coverage report, binds it to the commit
the run came from, and proposes a runtime anchor wherever the manifest already
cites that exact file and line as ``code`` evidence and the run reached it.

Three boundaries are deliberate:

* It **proposes**. A runtime anchor beside a code anchor takes a claim to
  ``confirmed``, so the merge is a decision and is left looking like one.
* It corroborates claims rather than making them. Emitting anchors for lines
  nobody claims would grow a manifest out of coverage, which is backwards.
* It never runs a build. The report is ingested out of band, so only ``forge``
  reaches the network and nothing here executes the implementation.

The criterion is ``line-executed``, and that is a real limit: a covered line is
one that *ran*, and no coverage format records whether an assertion examined
what it did. The promotion rule cannot tell a careful runtime anchor from a
lazy one, so the criterion travels with every proposal.
"""

from __future__ import annotations

from .commit import PinError
from .jacoco import CoverageError
from .jacoco import read as read_jacoco
from .model import CoverageReport, ExecutedLine
from .propose import PROPOSAL_CRITERION, AnchorProposal, SkippedAnchor, propose

__all__ = [
    "PinError",
    "PROPOSAL_CRITERION",
    "CoverageError",
    "CoverageReport",
    "ExecutedLine",
    "AnchorProposal",
    "SkippedAnchor",
    "propose",
    "read_jacoco",
]
