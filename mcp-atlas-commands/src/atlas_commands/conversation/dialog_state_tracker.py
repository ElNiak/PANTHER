"""
Dialog State Tracking for ATLAS MCP

Maintains conversational context and dialog state across MCP interactions,
enabling intelligent conversation flow management and context-aware responses.
"""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from collections import deque, defaultdict

from .conversation_manager import ConversationManager, MessageType
from ..entropy.entropy_processor import EntropyProcessor
from ..observability.logging import get_logger


class DialogState(Enum):
    """States of dialog flow."""
    GREETING = "greeting"
    TASK_ANALYSIS = "task_analysis" 
    REQUIREMENTS_GATHERING = "requirements_gathering"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    COMPLETION = "completion"
    ERROR_HANDLING = "error_handling"
    CLARIFICATION = "clarification"
    CONTEXT_SWITCH = "context_switch"


class DialogIntent(Enum):
    """User intents in dialog."""
    REQUEST_TASK = "request_task"
    ASK_QUESTION = "ask_question"
    PROVIDE_FEEDBACK = "provide_feedback"
    REQUEST_STATUS = "request_status"
    MODIFY_REQUIREMENT = "modify_requirement"
    APPROVE_PLAN = "approve_plan"
    REJECT_PLAN = "reject_plan"
    REQUEST_HELP = "request_help"
    CLARIFY_REQUIREMENT = "clarify_requirement"
    SWITCH_CONTEXT = "switch_context"


class ContextType(Enum):
    """Types of conversational context."""
    TECHNICAL = "technical"
    PROJECT = "project"
    TASK = "task"
    PERSONAL = "personal"
    PROCEDURAL = "procedural"
    DOMAIN_SPECIFIC = "domain_specific"


@dataclass
class DialogContext:
    """Context information for dialog state."""
    current_state: DialogState
    previous_state: Optional[DialogState]
    intent_history: List[DialogIntent]
    active_contexts: Set[ContextType]
    context_stack: List[Dict[str, Any]]
    unresolved_questions: List[str]
    pending_confirmations: List[str]
    last_state_change: datetime
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "intent_history": [intent.value for intent in self.intent_history],
            "active_contexts": [ctx.value for ctx in self.active_contexts],
            "context_stack": self.context_stack,
            "unresolved_questions": self.unresolved_questions,
            "pending_confirmations": self.pending_confirmations,
            "last_state_change": self.last_state_change.isoformat(),
            "confidence_score": self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DialogContext':
        """Create from dictionary."""
        return cls(
            current_state=DialogState(data["current_state"]),
            previous_state=DialogState(data["previous_state"]) if data["previous_state"] else None,
            intent_history=[DialogIntent(intent) for intent in data["intent_history"]],
            active_contexts={ContextType(ctx) for ctx in data["active_contexts"]},
            context_stack=data["context_stack"],
            unresolved_questions=data["unresolved_questions"],
            pending_confirmations=data["pending_confirmations"],
            last_state_change=datetime.fromisoformat(data["last_state_change"]),
            confidence_score=data["confidence_score"]
        )


@dataclass
class DialogTransition:
    """Records a state transition in dialog."""
    from_state: DialogState
    to_state: DialogState
    trigger: str
    confidence: float
    timestamp: datetime
    context_changes: Dict[str, Any]


class DialogStateTracker:
    """
    Tracks dialog state and maintains conversational context across MCP interactions.
    
    Provides intelligent state transitions, intent recognition, and context management
    for natural conversation flow.
    """
    
    def __init__(self, conversation_manager: ConversationManager, 
                 entropy_processor: EntropyProcessor):
        self.conversation_manager = conversation_manager
        self.entropy_processor = entropy_processor
        self.logger = get_logger(__name__)
        
        # State tracking
        self.session_dialogs: Dict[str, DialogContext] = {}
        
        # Intent patterns for recognition
        self.intent_patterns = self._initialize_intent_patterns()
        
        # State transition rules
        self.transition_rules = self._initialize_transition_rules()
        
        # Context tracking
        self.context_extractors = self._initialize_context_extractors()
        
        # Configuration
        self.max_intent_history = 20
        self.context_timeout_minutes = 30
        self.confidence_threshold = 0.7
        
    async def track_message(self, session_id: str, message_content: str, 
                           message_type: MessageType) -> DialogContext:
        """
        Track a message and update dialog state.
        
        Args:
            session_id: Conversation session ID
            message_content: Content of the message
            message_type: Type of message
            
        Returns:
            Updated dialog context
        """
        # Initialize dialog context if new session
        if session_id not in self.session_dialogs:
            await self._initialize_dialog_context(session_id)
        
        context = self.session_dialogs[session_id]
        
        # Analyze message for intent and context
        intent = await self._recognize_intent(message_content, context)
        new_contexts = await self._extract_contexts(message_content, context)
        
        # Update intent history
        context.intent_history.append(intent)
        if len(context.intent_history) > self.max_intent_history:
            context.intent_history.pop(0)
        
        # Update active contexts
        context.active_contexts.update(new_contexts)
        
        # Determine state transition
        new_state, confidence = await self._determine_state_transition(
            context, intent, message_content, message_type
        )
        
        # Execute state transition if needed
        if new_state != context.current_state and confidence > self.confidence_threshold:
            await self._execute_state_transition(context, new_state, 
                                               f"Intent: {intent.value}", confidence)
        
        # Update context stack
        await self._update_context_stack(context, message_content, intent)
        
        # Check for pending items resolution
        await self._check_pending_resolutions(context, message_content)
        
        # Store updated context
        self.session_dialogs[session_id] = context
        
        self.logger.debug(f"Dialog state updated for session {session_id}: "
                         f"{context.current_state.value} (confidence: {confidence:.3f})")
        
        return context
    
    async def get_dialog_suggestions(self, session_id: str) -> List[str]:
        """
        Get suggestions for continuing the dialog based on current state.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            List of suggested responses or actions
        """
        if session_id not in self.session_dialogs:
            return ["How can I help you today?"]
        
        context = self.session_dialogs[session_id]
        state = context.current_state
        
        suggestions = []
        
        # State-specific suggestions
        if state == DialogState.GREETING:
            suggestions.extend([
                "What would you like to work on?",
                "Do you have a specific task in mind?",
                "Would you like me to help you plan something?"
            ])
        
        elif state == DialogState.TASK_ANALYSIS:
            suggestions.extend([
                "Let me analyze the requirements for this task.",
                "I'll break this down into manageable steps.",
                "What are the key constraints for this work?"
            ])
        
        elif state == DialogState.REQUIREMENTS_GATHERING:
            suggestions.extend([
                "Can you provide more details about the requirements?",
                "What's the expected outcome?",
                "Are there any specific constraints I should know about?"
            ])
        
        elif state == DialogState.PLANNING:
            suggestions.extend([
                "Here's my suggested approach:",
                "Let me create a plan for this task.",
                "Would you like me to break this into smaller steps?"
            ])
        
        elif state == DialogState.EXECUTION:
            suggestions.extend([
                "I'm working on the implementation now.",
                "Let me start with the core functionality.",
                "I'll update you on progress as I go."
            ])
        
        elif state == DialogState.REVIEW:
            suggestions.extend([
                "Here's what I've completed:",
                "Please review the results.",
                "Does this meet your expectations?"
            ])
        
        elif state == DialogState.ERROR_HANDLING:
            suggestions.extend([
                "I've encountered an issue. Let me investigate.",
                "There seems to be a problem. Let me resolve it.",
                "I need to handle this error before continuing."
            ])
        
        elif state == DialogState.CLARIFICATION:
            suggestions.extend([
                "I need some clarification to proceed.",
                "Can you help me understand the requirement better?",
                "What did you mean by...?"
            ])
        
        # Add context-specific suggestions
        if ContextType.TECHNICAL in context.active_contexts:
            suggestions.append("I can provide technical details if needed.")
        
        # Add suggestions for pending items
        if context.unresolved_questions:
            suggestions.append(f"I still need answers to: {', '.join(context.unresolved_questions[:2])}")
        
        if context.pending_confirmations:
            suggestions.append(f"Please confirm: {', '.join(context.pending_confirmations[:2])}")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    async def get_dialog_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of current dialog context.
        
        Args:
            session_id: Conversation session ID
            
        Returns:
            Context summary dictionary
        """
        if session_id not in self.session_dialogs:
            return {"error": "Session not found"}
        
        context = self.session_dialogs[session_id]
        
        # Analyze recent intent patterns
        recent_intents = context.intent_history[-5:] if context.intent_history else []
        intent_pattern = " → ".join([intent.value for intent in recent_intents])
        
        # Calculate context complexity
        context_complexity = len(context.context_stack) + len(context.active_contexts)
        
        return {
            "current_state": context.current_state.value,
            "previous_state": context.previous_state.value if context.previous_state else None,
            "confidence_score": context.confidence_score,
            "active_contexts": [ctx.value for ctx in context.active_contexts],
            "recent_intent_pattern": intent_pattern,
            "context_complexity": context_complexity,
            "unresolved_items": {
                "questions": context.unresolved_questions,
                "confirmations": context.pending_confirmations
            },
            "time_in_current_state": (
                datetime.now() - context.last_state_change
            ).total_seconds(),
            "context_stack_depth": len(context.context_stack)
        }
    
    async def reset_dialog_context(self, session_id: str) -> None:
        """Reset dialog context for a session."""
        if session_id in self.session_dialogs:
            del self.session_dialogs[session_id]
        await self._initialize_dialog_context(session_id)
    
    async def handle_context_switch(self, session_id: str, new_context: str) -> DialogContext:
        """
        Handle explicit context switch in conversation.
        
        Args:
            session_id: Conversation session ID
            new_context: Description of new context
            
        Returns:
            Updated dialog context
        """
        if session_id not in self.session_dialogs:
            await self._initialize_dialog_context(session_id)
        
        context = self.session_dialogs[session_id]
        
        # Save current context to stack
        current_context_data = {
            "state": context.current_state.value,
            "contexts": [ctx.value for ctx in context.active_contexts],
            "timestamp": datetime.now().isoformat(),
            "description": new_context
        }
        context.context_stack.append(current_context_data)
        
        # Reset to initial state for new context
        await self._execute_state_transition(
            context, DialogState.TASK_ANALYSIS, 
            f"Context switch: {new_context}", 1.0
        )
        
        # Clear active contexts and start fresh
        context.active_contexts.clear()
        context.unresolved_questions.clear()
        context.pending_confirmations.clear()
        
        self.logger.info(f"Context switch executed for session {session_id}: {new_context}")
        return context
    
    # Private methods
    
    async def _initialize_dialog_context(self, session_id: str) -> None:
        """Initialize dialog context for new session."""
        context = DialogContext(
            current_state=DialogState.GREETING,
            previous_state=None,
            intent_history=[],
            active_contexts=set(),
            context_stack=[],
            unresolved_questions=[],
            pending_confirmations=[],
            last_state_change=datetime.now(),
            confidence_score=1.0
        )
        
        self.session_dialogs[session_id] = context
    
    async def _recognize_intent(self, message_content: str, 
                              context: DialogContext) -> DialogIntent:
        """Recognize user intent from message content."""
        content_lower = message_content.lower()
        
        # Check patterns for each intent
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    return intent
        
        # Default based on current state
        state_defaults = {
            DialogState.GREETING: DialogIntent.REQUEST_TASK,
            DialogState.TASK_ANALYSIS: DialogIntent.PROVIDE_FEEDBACK,
            DialogState.REQUIREMENTS_GATHERING: DialogIntent.CLARIFY_REQUIREMENT,
            DialogState.PLANNING: DialogIntent.APPROVE_PLAN,
            DialogState.EXECUTION: DialogIntent.REQUEST_STATUS,
            DialogState.REVIEW: DialogIntent.PROVIDE_FEEDBACK,
            DialogState.ERROR_HANDLING: DialogIntent.PROVIDE_FEEDBACK,
            DialogState.CLARIFICATION: DialogIntent.CLARIFY_REQUIREMENT
        }
        
        return state_defaults.get(context.current_state, DialogIntent.ASK_QUESTION)
    
    async def _extract_contexts(self, message_content: str, 
                              context: DialogContext) -> Set[ContextType]:
        """Extract context types from message content."""
        new_contexts = set()
        content_lower = message_content.lower()
        
        # Check for each context type
        for context_type, extractors in self.context_extractors.items():
            for extractor in extractors:
                if extractor(content_lower):
                    new_contexts.add(context_type)
                    break
        
        return new_contexts
    
    async def _determine_state_transition(self, context: DialogContext, 
                                        intent: DialogIntent, message_content: str,
                                        message_type: MessageType) -> Tuple[DialogState, float]:
        """Determine if state transition should occur."""
        current_state = context.current_state
        
        # Check transition rules
        for rule in self.transition_rules:
            if (rule["from_state"] == current_state and 
                rule["trigger_intent"] == intent and
                rule.get("message_type", message_type) == message_type):
                
                # Check additional conditions if any
                conditions_met = True
                if "conditions" in rule:
                    for condition in rule["conditions"]:
                        if not condition(context, message_content):
                            conditions_met = False
                            break
                
                if conditions_met:
                    return rule["to_state"], rule["confidence"]
        
        # Default: stay in current state
        return current_state, 0.5
    
    async def _execute_state_transition(self, context: DialogContext, 
                                      new_state: DialogState, trigger: str,
                                      confidence: float) -> None:
        """Execute state transition."""
        old_state = context.current_state
        
        # Create transition record
        transition = DialogTransition(
            from_state=old_state,
            to_state=new_state,
            trigger=trigger,
            confidence=confidence,
            timestamp=datetime.now(),
            context_changes={}
        )
        
        # Update context
        context.previous_state = old_state
        context.current_state = new_state
        context.confidence_score = confidence
        context.last_state_change = datetime.now()
        
        self.logger.info(f"State transition: {old_state.value} → {new_state.value} "
                        f"(trigger: {trigger}, confidence: {confidence:.3f})")
    
    async def _update_context_stack(self, context: DialogContext, 
                                  message_content: str, intent: DialogIntent) -> None:
        """Update context stack with current interaction."""
        # Add to context stack if significant
        entropy_analysis = self.entropy_processor.analyze_content_entropy(message_content)
        
        if entropy_analysis.content_entropy > 0.5:  # Moderate entropy threshold
            context_entry = {
                "content": message_content[:200],  # Truncate for storage
                "intent": intent.value,
                "entropy": entropy_analysis.content_entropy,
                "timestamp": datetime.now().isoformat()
            }
            context.context_stack.append(context_entry)
            
            # Limit context stack size
            if len(context.context_stack) > 50:
                context.context_stack.pop(0)
    
    async def _check_pending_resolutions(self, context: DialogContext, 
                                       message_content: str) -> None:
        """Check if message resolves pending questions or confirmations."""
        content_lower = message_content.lower()
        
        # Check for question answers
        resolved_questions = []
        for question in context.unresolved_questions:
            if any(keyword in content_lower for keyword in ["yes", "no", "because", "since"]):
                resolved_questions.append(question)
        
        for question in resolved_questions:
            context.unresolved_questions.remove(question)
        
        # Check for confirmations
        resolved_confirmations = []
        for confirmation in context.pending_confirmations:
            if any(keyword in content_lower for keyword in ["yes", "confirm", "proceed", "approve"]):
                resolved_confirmations.append(confirmation)
            elif any(keyword in content_lower for keyword in ["no", "reject", "cancel", "stop"]):
                resolved_confirmations.append(confirmation)
        
        for confirmation in resolved_confirmations:
            context.pending_confirmations.remove(confirmation)
    
    def _initialize_intent_patterns(self) -> Dict[DialogIntent, List[str]]:
        """Initialize patterns for intent recognition."""
        return {
            DialogIntent.REQUEST_TASK: [
                "can you", "please", "i need", "help me", "implement", "create", "build"
            ],
            DialogIntent.ASK_QUESTION: [
                "what", "how", "why", "when", "where", "which", "?"
            ],
            DialogIntent.PROVIDE_FEEDBACK: [
                "looks good", "that's correct", "yes", "no", "wrong", "issue", "problem"
            ],
            DialogIntent.REQUEST_STATUS: [
                "status", "progress", "how's it going", "update", "what's happening"
            ],
            DialogIntent.MODIFY_REQUIREMENT: [
                "change", "modify", "update", "different", "instead", "actually"
            ],
            DialogIntent.APPROVE_PLAN: [
                "approve", "go ahead", "proceed", "sounds good", "yes", "correct"
            ],
            DialogIntent.REJECT_PLAN: [
                "reject", "no", "wrong", "different approach", "not right"
            ],
            DialogIntent.REQUEST_HELP: [
                "help", "stuck", "confused", "don't understand", "explain"
            ],
            DialogIntent.CLARIFY_REQUIREMENT: [
                "clarify", "mean", "specifically", "details", "more info"
            ],
            DialogIntent.SWITCH_CONTEXT: [
                "switch", "move to", "work on", "focus on", "change topic"
            ]
        }
    
    def _initialize_transition_rules(self) -> List[Dict[str, Any]]:
        """Initialize state transition rules."""
        return [
            # From GREETING
            {
                "from_state": DialogState.GREETING,
                "trigger_intent": DialogIntent.REQUEST_TASK,
                "to_state": DialogState.TASK_ANALYSIS,
                "confidence": 0.9
            },
            {
                "from_state": DialogState.GREETING,
                "trigger_intent": DialogIntent.ASK_QUESTION,
                "to_state": DialogState.CLARIFICATION,
                "confidence": 0.8
            },
            
            # From TASK_ANALYSIS
            {
                "from_state": DialogState.TASK_ANALYSIS,
                "trigger_intent": DialogIntent.CLARIFY_REQUIREMENT,
                "to_state": DialogState.REQUIREMENTS_GATHERING,
                "confidence": 0.8
            },
            {
                "from_state": DialogState.TASK_ANALYSIS,
                "trigger_intent": DialogIntent.APPROVE_PLAN,
                "to_state": DialogState.PLANNING,
                "confidence": 0.9
            },
            
            # From REQUIREMENTS_GATHERING
            {
                "from_state": DialogState.REQUIREMENTS_GATHERING,
                "trigger_intent": DialogIntent.PROVIDE_FEEDBACK,
                "to_state": DialogState.PLANNING,
                "confidence": 0.8
            },
            
            # From PLANNING
            {
                "from_state": DialogState.PLANNING,
                "trigger_intent": DialogIntent.APPROVE_PLAN,
                "to_state": DialogState.EXECUTION,
                "confidence": 0.9
            },
            {
                "from_state": DialogState.PLANNING,
                "trigger_intent": DialogIntent.REJECT_PLAN,
                "to_state": DialogState.REQUIREMENTS_GATHERING,
                "confidence": 0.8
            },
            
            # From EXECUTION
            {
                "from_state": DialogState.EXECUTION,
                "trigger_intent": DialogIntent.REQUEST_STATUS,
                "to_state": DialogState.EXECUTION,
                "confidence": 0.7
            },
            
            # Error handling from any state
            {
                "from_state": None,  # Any state
                "trigger_intent": DialogIntent.REQUEST_HELP,
                "to_state": DialogState.ERROR_HANDLING,
                "confidence": 0.8
            },
            
            # Context switches
            {
                "from_state": None,  # Any state
                "trigger_intent": DialogIntent.SWITCH_CONTEXT,
                "to_state": DialogState.CONTEXT_SWITCH,
                "confidence": 0.9
            }
        ]
    
    def _initialize_context_extractors(self) -> Dict[ContextType, List[callable]]:
        """Initialize context extraction functions."""
        return {
            ContextType.TECHNICAL: [
                lambda text: any(term in text for term in ["code", "implementation", "bug", "error", "api"]),
                lambda text: any(term in text for term in ["database", "server", "client", "framework"])
            ],
            ContextType.PROJECT: [
                lambda text: any(term in text for term in ["project", "deadline", "milestone", "requirements"]),
                lambda text: any(term in text for term in ["stakeholder", "client", "user", "business"])
            ],
            ContextType.TASK: [
                lambda text: any(term in text for term in ["todo", "task", "action", "step"]),
                lambda text: any(term in text for term in ["priority", "urgent", "schedule"])
            ],
            ContextType.PROCEDURAL: [
                lambda text: any(term in text for term in ["process", "workflow", "procedure", "method"]),
                lambda text: any(term in text for term in ["documentation", "guide", "manual"])
            ]
        }