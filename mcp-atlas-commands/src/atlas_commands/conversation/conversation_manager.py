"""
Conversation Management for ATLAS MCP

Provides intelligent session tracking and context persistence for conversational intelligence
across MCP interactions, integrating with ATLAS memory graph system.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from pathlib import Path

from ..memory.graph_manager import MemoryGraphManager
from ..entropy.entropy_processor import EntropyProcessor
from ..observability.logging import get_logger


class ConversationState(Enum):
    """States of a conversation session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageType(Enum):
    """Types of messages in conversation history."""
    USER_REQUEST = "user_request"
    SYSTEM_RESPONSE = "system_response"
    TOOL_EXECUTION = "tool_execution"
    ERROR_RECOVERY = "error_recovery"
    CONTEXT_SWITCH = "context_switch"


@dataclass
class ConversationMessage:
    """Individual message in conversation history."""
    id: str
    timestamp: datetime
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    entropy_score: Optional[float] = None
    context_tags: List[str] = None
    session_id: str = ""
    
    def __post_init__(self):
        if self.context_tags is None:
            self.context_tags = []


@dataclass
class ConversationSession:
    """Complete conversation session with state and context."""
    session_id: str
    start_time: datetime
    last_activity: datetime
    state: ConversationState
    messages: List[ConversationMessage]
    context_summary: str
    active_tasks: List[str]
    memory_entities: List[str]
    session_metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "state": self.state.value,
            "messages": [asdict(msg) for msg in self.messages],
            "context_summary": self.context_summary,
            "active_tasks": self.active_tasks,
            "memory_entities": self.memory_entities,
            "session_metadata": self.session_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create session from stored dictionary."""
        messages = [
            ConversationMessage(
                id=msg["id"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                message_type=MessageType(msg["message_type"]),
                content=msg["content"],
                metadata=msg["metadata"],
                entropy_score=msg.get("entropy_score"),
                context_tags=msg.get("context_tags", []),
                session_id=msg.get("session_id", "")
            )
            for msg in data["messages"]
        ]
        
        return cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            state=ConversationState(data["state"]),
            messages=messages,
            context_summary=data["context_summary"],
            active_tasks=data["active_tasks"],
            memory_entities=data["memory_entities"],
            session_metadata=data["session_metadata"]
        )


class ConversationManager:
    """
    Manages conversation sessions and provides intelligent context tracking.
    
    Integrates with ATLAS memory system for persistent context storage and
    entropy analysis for high-value message identification.
    """
    
    def __init__(self, storage_path: str, memory_manager: MemoryGraphManager, 
                 entropy_processor: EntropyProcessor):
        self.storage_path = Path(storage_path)
        self.memory_manager = memory_manager
        self.entropy_processor = entropy_processor
        self.logger = get_logger(__name__)
        
        # Session management
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_storage_path = self.storage_path / "conversations"
        self.session_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.max_active_sessions = 10
        self.session_timeout_hours = 24
        self.high_entropy_threshold = 0.894  # Shannon's optimal threshold
        self.context_summary_trigger = 50  # Messages before summarization
        
        # Load existing sessions
        self._load_active_sessions()
    
    async def start_conversation(self, initial_context: str = "", 
                                metadata: Dict[str, Any] = None) -> str:
        """
        Start a new conversation session.
        
        Args:
            initial_context: Initial context or task description
            metadata: Additional session metadata
            
        Returns:
            Session ID for the new conversation
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = ConversationSession(
            session_id=session_id,
            start_time=now,
            last_activity=now,
            state=ConversationState.ACTIVE,
            messages=[],
            context_summary=initial_context,
            active_tasks=[],
            memory_entities=[],
            session_metadata=metadata or {}
        )
        
        # Store session
        self.active_sessions[session_id] = session
        await self._persist_session(session)
        
        # Create memory entity for conversation
        await self._create_conversation_memory_entity(session)
        
        self.logger.info(f"Started conversation session: {session_id}")
        return session_id
    
    async def add_message(self, session_id: str, message_type: MessageType,
                         content: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add a message to conversation session.
        
        Args:
            session_id: Target session ID
            message_type: Type of message being added
            content: Message content
            metadata: Additional message metadata
            
        Returns:
            Message ID
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        message_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Analyze message entropy for importance
        entropy_analysis = self.entropy_processor.analyze_content_entropy(content)
        
        # Extract context tags based on content
        context_tags = await self._extract_context_tags(content, session)
        
        message = ConversationMessage(
            id=message_id,
            timestamp=now,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            entropy_score=entropy_analysis.content_entropy,
            context_tags=context_tags,
            session_id=session_id
        )
        
        # Add to session
        session.messages.append(message)
        session.last_activity = now
        
        # Update memory if high entropy
        if entropy_analysis.content_entropy > self.high_entropy_threshold:
            await self._update_conversation_memory(session, message)
        
        # Trigger context summarization if needed
        if len(session.messages) % self.context_summary_trigger == 0:
            await self._update_context_summary(session)
        
        # Persist session
        await self._persist_session(session)
        
        self.logger.debug(f"Added message {message_id} to session {session_id} "
                         f"(entropy: {entropy_analysis.content_entropy:.3f})")
        
        return message_id
    
    async def get_conversation_context(self, session_id: str, 
                                     last_n_messages: Optional[int] = None) -> Dict[str, Any]:
        """
        Get conversation context for a session.
        
        Args:
            session_id: Target session ID
            last_n_messages: Limit to last N messages (None for all)
            
        Returns:
            Context dictionary with messages, summary, and metadata
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        
        messages = session.messages
        if last_n_messages:
            messages = messages[-last_n_messages:]
        
        # Get related memory entities
        memory_context = await self._get_session_memory_context(session)
        
        return {
            "session_id": session_id,
            "context_summary": session.context_summary,
            "active_tasks": session.active_tasks,
            "messages": [asdict(msg) for msg in messages],
            "memory_context": memory_context,
            "session_state": session.state.value,
            "last_activity": session.last_activity.isoformat(),
            "high_entropy_messages": [
                asdict(msg) for msg in messages 
                if msg.entropy_score and msg.entropy_score > self.high_entropy_threshold
            ]
        }
    
    async def update_active_tasks(self, session_id: str, tasks: List[str]) -> None:
        """Update active tasks for a session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        session.active_tasks = tasks
        session.last_activity = datetime.now()
        
        await self._persist_session(session)
        await self._update_task_memory_relations(session)
    
    async def pause_conversation(self, session_id: str, reason: str = "") -> None:
        """Pause a conversation session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        session.state = ConversationState.PAUSED
        session.session_metadata["pause_reason"] = reason
        session.session_metadata["paused_at"] = datetime.now().isoformat()
        
        await self._persist_session(session)
        self.logger.info(f"Paused conversation session: {session_id}")
    
    async def resume_conversation(self, session_id: str) -> Dict[str, Any]:
        """Resume a paused conversation session."""
        if session_id not in self.active_sessions:
            # Try to load from storage
            await self._load_session_from_storage(session_id)
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        session.state = ConversationState.ACTIVE
        session.last_activity = datetime.now()
        
        await self._persist_session(session)
        
        # Return current context for resumption
        context = await self.get_conversation_context(session_id)
        
        self.logger.info(f"Resumed conversation session: {session_id}")
        return context
    
    async def complete_conversation(self, session_id: str, 
                                  completion_summary: str = "") -> None:
        """Mark conversation as completed and archive."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        session = self.active_sessions[session_id]
        session.state = ConversationState.COMPLETED
        session.session_metadata["completion_summary"] = completion_summary
        session.session_metadata["completed_at"] = datetime.now().isoformat()
        
        # Create final memory summary
        await self._create_completion_memory_summary(session)
        
        # Archive and remove from active sessions
        await self._archive_session(session)
        del self.active_sessions[session_id]
        
        self.logger.info(f"Completed conversation session: {session_id}")
    
    async def cleanup_expired_sessions(self) -> List[str]:
        """Clean up expired sessions based on timeout."""
        expired_sessions = []
        cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
        
        for session_id, session in list(self.active_sessions.items()):
            if session.last_activity < cutoff_time:
                await self.complete_conversation(
                    session_id, 
                    "Session expired due to inactivity"
                )
                expired_sessions.append(session_id)
        
        return expired_sessions
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about conversation sessions."""
        total_messages = sum(len(session.messages) for session in self.active_sessions.values())
        high_entropy_messages = sum(
            1 for session in self.active_sessions.values()
            for msg in session.messages
            if msg.entropy_score and msg.entropy_score > self.high_entropy_threshold
        )
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_messages": total_messages,
            "high_entropy_messages": high_entropy_messages,
            "average_entropy": sum(
                msg.entropy_score for session in self.active_sessions.values()
                for msg in session.messages if msg.entropy_score
            ) / max(total_messages, 1),
            "session_states": {
                state.value: sum(1 for session in self.active_sessions.values() 
                               if session.state == state)
                for state in ConversationState
            }
        }
    
    # Private methods
    
    def _load_active_sessions(self) -> None:
        """Load active sessions from storage."""
        for session_file in self.session_storage_path.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    session = ConversationSession.from_dict(session_data)
                    
                    if session.state == ConversationState.ACTIVE:
                        self.active_sessions[session.session_id] = session
                        
            except Exception as e:
                self.logger.error(f"Failed to load session {session_file}: {e}")
    
    async def _load_session_from_storage(self, session_id: str) -> None:
        """Load specific session from storage."""
        session_file = self.session_storage_path / f"{session_id}.json"
        
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    session = ConversationSession.from_dict(session_data)
                    self.active_sessions[session_id] = session
            except Exception as e:
                self.logger.error(f"Failed to load session {session_id}: {e}")
    
    async def _persist_session(self, session: ConversationSession) -> None:
        """Persist session to storage."""
        session_file = self.session_storage_path / f"{session.session_id}.json"
        
        try:
            # Convert datetime objects to ISO format for JSON serialization
            session_data = session.to_dict()
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to persist session {session.session_id}: {e}")
    
    async def _archive_session(self, session: ConversationSession) -> None:
        """Archive completed session."""
        archive_path = self.session_storage_path / "archived"
        archive_path.mkdir(exist_ok=True)
        
        session_file = self.session_storage_path / f"{session.session_id}.json"
        archive_file = archive_path / f"{session.session_id}.json"
        
        try:
            if session_file.exists():
                session_file.rename(archive_file)
        except Exception as e:
            self.logger.error(f"Failed to archive session {session.session_id}: {e}")
    
    async def _create_conversation_memory_entity(self, session: ConversationSession) -> None:
        """Create memory entity for conversation tracking."""
        try:
            await self.memory_manager.create_entities([{
                "name": f"ConversationSession_{session.session_id}",
                "entityType": "ConversationSession",
                "observations": [
                    f"Started at {session.start_time.isoformat()}",
                    f"Initial context: {session.context_summary}",
                    f"Session metadata: {json.dumps(session.session_metadata)}"
                ]
            }])
            
            session.memory_entities.append(f"ConversationSession_{session.session_id}")
        except Exception as e:
            self.logger.error(f"Failed to create conversation memory entity: {e}")
    
    async def _update_conversation_memory(self, session: ConversationSession, 
                                        message: ConversationMessage) -> None:
        """Update conversation memory with high-entropy message."""
        try:
            entity_name = f"ConversationSession_{session.session_id}"
            
            await self.memory_manager.add_observations([{
                "entityName": entity_name,
                "contents": [
                    f"High-entropy message ({message.entropy_score:.3f}): {message.content[:200]}...",
                    f"Message type: {message.message_type.value}",
                    f"Context tags: {', '.join(message.context_tags)}",
                    f"Timestamp: {message.timestamp.isoformat()}"
                ]
            }])
        except Exception as e:
            self.logger.error(f"Failed to update conversation memory: {e}")
    
    async def _extract_context_tags(self, content: str, 
                                  session: ConversationSession) -> List[str]:
        """Extract context tags from message content."""
        tags = []
        
        # Extract technical terms
        technical_terms = ["error", "debug", "implement", "refactor", "test", "deploy"]
        for term in technical_terms:
            if term.lower() in content.lower():
                tags.append(f"tech:{term}")
        
        # Extract task-related terms
        task_terms = ["todo", "task", "complete", "start", "finish"]
        for term in task_terms:
            if term.lower() in content.lower():
                tags.append(f"task:{term}")
        
        # Extract project context from active tasks
        for task in session.active_tasks:
            if task.lower() in content.lower():
                tags.append(f"project:{task}")
        
        return tags
    
    async def _update_context_summary(self, session: ConversationSession) -> None:
        """Update conversation context summary using recent messages."""
        try:
            # Get recent high-entropy messages for summary
            recent_messages = session.messages[-self.context_summary_trigger:]
            high_entropy_content = [
                msg.content for msg in recent_messages
                if msg.entropy_score and msg.entropy_score > self.high_entropy_threshold
            ]
            
            if high_entropy_content:
                # Create summary from high-entropy content
                summary_content = " | ".join(high_entropy_content[:5])  # Limit to 5 messages
                session.context_summary = f"Recent context: {summary_content[:500]}..."
                
        except Exception as e:
            self.logger.error(f"Failed to update context summary: {e}")
    
    async def _get_session_memory_context(self, session: ConversationSession) -> Dict[str, Any]:
        """Get memory context related to session."""
        try:
            context = {}
            
            for entity_name in session.memory_entities:
                # Search for related entities
                search_results = await self.memory_manager.search_nodes(entity_name)
                context[entity_name] = search_results
            
            return context
        except Exception as e:
            self.logger.error(f"Failed to get session memory context: {e}")
            return {}
    
    async def _update_task_memory_relations(self, session: ConversationSession) -> None:
        """Update memory relations between conversation and active tasks."""
        try:
            conversation_entity = f"ConversationSession_{session.session_id}"
            
            for task in session.active_tasks:
                await self.memory_manager.create_relations([{
                    "from": conversation_entity,
                    "to": task,
                    "relationType": "discusses"
                }])
        except Exception as e:
            self.logger.error(f"Failed to update task memory relations: {e}")
    
    async def _create_completion_memory_summary(self, session: ConversationSession) -> None:
        """Create memory summary when conversation is completed."""
        try:
            entity_name = f"ConversationSession_{session.session_id}"
            
            # Summarize high-entropy messages
            high_entropy_messages = [
                msg for msg in session.messages
                if msg.entropy_score and msg.entropy_score > self.high_entropy_threshold
            ]
            
            summary_observations = [
                f"Conversation completed with {len(session.messages)} total messages",
                f"High-entropy messages: {len(high_entropy_messages)}",
                f"Active tasks: {', '.join(session.active_tasks)}",
                f"Duration: {session.last_activity - session.start_time}",
                f"Completion summary: {session.session_metadata.get('completion_summary', 'N/A')}"
            ]
            
            await self.memory_manager.add_observations([{
                "entityName": entity_name,
                "contents": summary_observations
            }])
            
        except Exception as e:
            self.logger.error(f"Failed to create completion memory summary: {e}")