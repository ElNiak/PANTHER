"""Chain the deterministic stages of a reconstruction.

The six substrate commands each do one stage and take every path explicitly.
That is right for them, and it leaves nobody holding the sequence: running a
reconstruction meant typing five commands with matching paths, in an order
documented only in prose.

This package holds the sequence and nothing else. It performs the deterministic
stages by calling the same sub-CLIs a person would type, reads a workspace's
state off the artifacts those stages already digest, and **stops** at the two
stages that produce content — mining claims and writing prose — because those
need a model and nothing in this package calls one. Reaching such a boundary is
success: the pipeline exits 0 and says whose turn it is.
"""

from __future__ import annotations

from .run import PipelineError, StageResult, perform, workspace_from
from .stages import STAGES, Performer, Stage, stage
from .state import NextStage, StageState, State, next_stage, state
from .workspace import Workspace, digest

__all__ = [
    "Performer",
    "NextStage",
    "PipelineError",
    "STAGES",
    "Stage",
    "StageResult",
    "StageState",
    "State",
    "Workspace",
    "digest",
    "next_stage",
    "perform",
    "stage",
    "state",
    "workspace_from",
]
