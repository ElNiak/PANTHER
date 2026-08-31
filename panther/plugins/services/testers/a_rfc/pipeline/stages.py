"""The ordered stages, and which of them a model has to perform.

The pipeline's whole shape is here: ten stages, of which two produce content
and are therefore the agent's, and the rest are deterministic. Keeping the
distinction in the data rather than in control flow is what lets the runner
stop at an agent boundary without knowing anything about agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Kind(Enum):
    """Who performs a stage."""

    #: Deterministic Python in this package. No model, no network beyond forge.
    DETERMINISTIC = "deterministic"
    #: A model mines claims or writes prose. Nothing here can do it, by design.
    AGENT = "agent"
    #: A human clones the repository. Cloning reaches the network, which this
    #: package reserves to ``forge``, so it stays outside.
    MANUAL = "manual"


@dataclass(frozen=True)
class Stage:
    """One step of the reconstruction."""

    ordinal: int
    name: str
    kind: Kind
    #: What a reader should do when the pipeline stops here. Empty for stages
    #: the runner performs itself.
    instruction: str = ""


STAGES: tuple[Stage, ...] = (
    Stage(
        0,
        "pin",
        Kind.MANUAL,
        "Clone the implementation into <workspace>/clone and leave its tree "
        "clean. Its HEAD is the commit every anchor is verified against.",
    ),
    Stage(1, "history", Kind.DETERMINISTIC),
    Stage(2, "forge", Kind.DETERMINISTIC),
    Stage(3, "timeline", Kind.DETERMINISTIC),
    Stage(4, "views", Kind.DETERMINISTIC),
    Stage(
        5,
        "mining",
        Kind.AGENT,
        "Read the cluster evidence under <workspace>/clusters and write claims "
        "into <workspace>/manifest.yaml. Nothing in this package proposes a "
        "claim; the manifest arrives as YAML a miner put on disk.",
    ),
    Stage(6, "adjudicate", Kind.DETERMINISTIC),
    Stage(
        7,
        "prose",
        Kind.AGENT,
        "Write the Internet-Draft in <workspace>/draft, citing claims as "
        "`a_rfc:<id>` tokens, and record each revision in revisions.yaml.",
    ),
    Stage(8, "checkpoint", Kind.DETERMINISTIC),
    Stage(9, "gate", Kind.DETERMINISTIC),
)

BY_NAME = {stage.name: stage for stage in STAGES}


def stage(name: str) -> Stage:
    """Look one up by name.

    Args:
        name: The stage's name.

    Returns:
        The stage.

    Raises:
        KeyError: If no stage has that name.
    """
    return BY_NAME[name]
