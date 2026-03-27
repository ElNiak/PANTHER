"""Workflow management module for PANTHER.

This module provides lightweight workflow state tracking focused on experiment coordination.
"""

from .workflow_tracker import WorkflowState, WorkflowStateTracker

__all__ = ["WorkflowState", "WorkflowStateTracker"]
