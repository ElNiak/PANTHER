"""
Conversation Management Module for ATLAS MCP

Provides intelligent conversation tracking, dialog state management,
and message history analysis for enhanced conversational intelligence.
"""

from .conversation_manager import (
    ConversationManager,
    ConversationSession,
    ConversationMessage,
    MessageType,
    ConversationState
)

from .dialog_state_tracker import (
    DialogStateTracker,
    DialogContext,
    DialogState,
    DialogIntent,
    ContextType,
    DialogTransition
)

from .message_history import (
    MessageHistorySystem,
    HistoryPattern,
    ConversationSummary,
    HistorySearchMode,
    MessageCluster
)

__all__ = [
    # Conversation Manager
    "ConversationManager",
    "ConversationSession", 
    "ConversationMessage",
    "MessageType",
    "ConversationState",
    
    # Dialog State Tracker
    "DialogStateTracker",
    "DialogContext",
    "DialogState", 
    "DialogIntent",
    "ContextType",
    "DialogTransition",
    
    # Message History System
    "MessageHistorySystem",
    "HistoryPattern",
    "ConversationSummary",
    "HistorySearchMode",
    "MessageCluster"
]