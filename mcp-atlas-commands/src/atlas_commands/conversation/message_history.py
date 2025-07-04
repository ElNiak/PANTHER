"""
Message History System for ATLAS MCP

Intelligent message history management with ATLAS memory graph integration
for conversational intelligence and context-aware interactions.
"""

import asyncio
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path

from .conversation_manager import ConversationManager, ConversationMessage, MessageType
from .dialog_state_tracker import DialogStateTracker, DialogState, DialogIntent
from ..memory.graph_manager import MemoryGraphManager
from ..entropy.entropy_processor import EntropyProcessor
from ..embeddings.semantic_search import SemanticSearchEngine, SearchContext, SearchMode
from ..observability.logging import get_logger


class HistorySearchMode(Enum):
    """Search modes for message history."""
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"
    ENTROPY_BASED = "entropy_based"
    INTENT_BASED = "intent_based"


class MessageCluster(Enum):
    """Message clustering categories."""
    TASK_DEFINITION = "task_definition"
    REQUIREMENT_CLARIFICATION = "requirement_clarification"
    IMPLEMENTATION_DISCUSSION = "implementation_discussion"
    ERROR_RESOLUTION = "error_resolution"
    PROGRESS_UPDATE = "progress_update"
    COMPLETION_CONFIRMATION = "completion_confirmation"


@dataclass
class HistoryPattern:
    """Detected pattern in message history."""
    pattern_id: str
    pattern_type: str
    messages: List[str]  # Message IDs
    confidence: float
    frequency: int
    last_occurrence: datetime
    context_tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ConversationSummary:
    """Summary of conversation with key insights."""
    session_id: str
    summary_text: str
    key_decisions: List[str]
    unresolved_items: List[str]
    technical_context: Dict[str, Any]
    message_count: int
    high_entropy_count: int
    dominant_intents: List[str]
    time_span: timedelta
    patterns_detected: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["time_span"] = str(self.time_span)
        return result


class MessageHistorySystem:
    """
    Intelligent message history management with ATLAS memory integration.
    
    Provides conversational intelligence through semantic search, pattern detection,
    and context-aware history analysis integrated with ATLAS memory graph.
    """
    
    def __init__(self, conversation_manager: ConversationManager,
                 dialog_tracker: DialogStateTracker, memory_manager: MemoryGraphManager,
                 entropy_processor: EntropyProcessor, semantic_search: SemanticSearchEngine,
                 storage_path: str):
        self.conversation_manager = conversation_manager
        self.dialog_tracker = dialog_tracker
        self.memory_manager = memory_manager
        self.entropy_processor = entropy_processor
        self.semantic_search = semantic_search
        self.storage_path = Path(storage_path)
        self.logger = get_logger(__name__)
        
        # History storage
        self.history_path = self.storage_path / "message_history"
        self.history_path.mkdir(parents=True, exist_ok=True)
        
        # Pattern detection
        self.detected_patterns: Dict[str, List[HistoryPattern]] = defaultdict(list)
        self.pattern_cache: Dict[str, Any] = {}
        
        # Configuration
        self.max_history_size = 10000  # Maximum messages to keep in memory
        self.pattern_detection_window = 100  # Messages to analyze for patterns
        self.semantic_similarity_threshold = 0.7
        self.entropy_significance_threshold = 0.894
        
        # Initialize pattern matchers
        self.pattern_matchers = self._initialize_pattern_matchers()
    
    async def analyze_conversation_patterns(self, session_id: str) -> List[HistoryPattern]:
        """
        Analyze conversation for recurring patterns and insights.
        
        Args:
            session_id: Target conversation session
            
        Returns:
            List of detected patterns
        """
        try:
            # Get conversation context
            context = await self.conversation_manager.get_conversation_context(session_id)
            messages = context.get("messages", [])
            
            if len(messages) < 5:  # Need minimum messages for pattern detection
                return []
            
            patterns = []
            
            # Detect temporal patterns
            temporal_patterns = await self._detect_temporal_patterns(messages)
            patterns.extend(temporal_patterns)
            
            # Detect semantic patterns
            semantic_patterns = await self._detect_semantic_patterns(messages)
            patterns.extend(semantic_patterns)
            
            # Detect intent patterns
            intent_patterns = await self._detect_intent_patterns(session_id, messages)
            patterns.extend(intent_patterns)
            
            # Detect entropy patterns
            entropy_patterns = await self._detect_entropy_patterns(messages)
            patterns.extend(entropy_patterns)
            
            # Store patterns for session
            self.detected_patterns[session_id] = patterns
            
            # Update memory graph with significant patterns
            await self._store_patterns_in_memory(session_id, patterns)
            
            self.logger.info(f"Detected {len(patterns)} conversation patterns for session {session_id}")
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing conversation patterns: {e}")
            return []
    
    async def search_conversation_history(self, session_id: str, query: str,
                                        search_mode: HistorySearchMode = HistorySearchMode.SEMANTIC,
                                        limit: int = 10) -> List[ConversationMessage]:
        """
        Search conversation history using various search modes.
        
        Args:
            session_id: Target conversation session
            query: Search query
            search_mode: Mode of search to perform
            limit: Maximum results to return
            
        Returns:
            List of matching messages
        """
        try:
            # Get conversation context
            context = await self.conversation_manager.get_conversation_context(session_id)
            messages = context.get("messages", [])
            
            if not messages:
                return []
            
            # Convert to ConversationMessage objects
            conv_messages = [
                ConversationMessage(
                    id=msg["id"],
                    timestamp=datetime.fromisoformat(msg["timestamp"]),
                    message_type=MessageType(msg["message_type"]),
                    content=msg["content"],
                    metadata=msg["metadata"],
                    entropy_score=msg.get("entropy_score"),
                    context_tags=msg.get("context_tags", []),
                    session_id=session_id
                )
                for msg in messages
            ]
            
            # Apply search mode
            if search_mode == HistorySearchMode.SEMANTIC:
                results = await self._semantic_search(conv_messages, query, limit)
            elif search_mode == HistorySearchMode.TEMPORAL:
                results = await self._temporal_search(conv_messages, query, limit)
            elif search_mode == HistorySearchMode.CONTEXTUAL:
                results = await self._contextual_search(conv_messages, query, limit)
            elif search_mode == HistorySearchMode.ENTROPY_BASED:
                results = await self._entropy_search(conv_messages, query, limit)
            elif search_mode == HistorySearchMode.INTENT_BASED:
                results = await self._intent_search(conv_messages, query, limit)
            else:
                results = conv_messages[:limit]  # Default to recent messages
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching conversation history: {e}")
            return []
    
    async def generate_conversation_summary(self, session_id: str) -> ConversationSummary:
        """
        Generate intelligent summary of conversation.
        
        Args:
            session_id: Target conversation session
            
        Returns:
            Comprehensive conversation summary
        """
        try:
            # Get conversation data
            context = await self.conversation_manager.get_conversation_context(session_id)
            messages = context.get("messages", [])
            
            if not messages:
                return ConversationSummary(
                    session_id=session_id,
                    summary_text="No messages in conversation",
                    key_decisions=[],
                    unresolved_items=[],
                    technical_context={},
                    message_count=0,
                    high_entropy_count=0,
                    dominant_intents=[],
                    time_span=timedelta(0),
                    patterns_detected=[]
                )
            
            # Analyze messages
            message_count = len(messages)
            high_entropy_messages = [
                msg for msg in messages 
                if msg.get("entropy_score", 0) > self.entropy_significance_threshold
            ]
            high_entropy_count = len(high_entropy_messages)
            
            # Calculate time span
            start_time = datetime.fromisoformat(messages[0]["timestamp"])
            end_time = datetime.fromisoformat(messages[-1]["timestamp"])
            time_span = end_time - start_time
            
            # Extract key decisions from high-entropy messages
            key_decisions = await self._extract_key_decisions(high_entropy_messages)
            
            # Identify unresolved items
            unresolved_items = await self._identify_unresolved_items(messages)
            
            # Extract technical context
            technical_context = await self._extract_technical_context(messages)
            
            # Analyze intent patterns
            dominant_intents = await self._analyze_dominant_intents(session_id)
            
            # Get detected patterns
            patterns = self.detected_patterns.get(session_id, [])
            pattern_types = [p.pattern_type for p in patterns]
            
            # Generate summary text
            summary_text = await self._generate_summary_text(
                message_count, high_entropy_count, key_decisions, 
                technical_context, dominant_intents
            )
            
            summary = ConversationSummary(
                session_id=session_id,
                summary_text=summary_text,
                key_decisions=key_decisions,
                unresolved_items=unresolved_items,
                technical_context=technical_context,
                message_count=message_count,
                high_entropy_count=high_entropy_count,
                dominant_intents=dominant_intents,
                time_span=time_span,
                patterns_detected=pattern_types
            )
            
            # Store summary in memory graph
            await self._store_summary_in_memory(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating conversation summary: {e}")
            return ConversationSummary(
                session_id=session_id,
                summary_text=f"Error generating summary: {e}",
                key_decisions=[],
                unresolved_items=[],
                technical_context={},
                message_count=0,
                high_entropy_count=0,
                dominant_intents=[],
                time_span=timedelta(0),
                patterns_detected=[]
            )
    
    async def find_similar_conversations(self, session_id: str, 
                                       similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find conversations with similar patterns or content.
        
        Args:
            session_id: Reference conversation session
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of similar conversation references
        """
        try:
            # Get current conversation summary
            current_summary = await self.generate_conversation_summary(session_id)
            
            # Search memory for similar conversations
            search_query = " ".join([
                current_summary.summary_text,
                " ".join(current_summary.key_decisions),
                " ".join(current_summary.dominant_intents)
            ])
            
            similar_conversations = await self.memory_manager.search_nodes(search_query)
            
            # Filter and rank by similarity
            results = []
            for conversation in similar_conversations:
                # Calculate similarity (simplified)
                similarity = await self._calculate_conversation_similarity(
                    current_summary, conversation
                )
                
                if similarity >= similarity_threshold:
                    results.append({
                        "session_id": conversation.get("name", "unknown"),
                        "similarity_score": similarity,
                        "summary": conversation.get("observations", [])[:2],  # First 2 observations
                        "metadata": conversation.get("metadata", {})
                    })
            
            # Sort by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return results[:10]  # Return top 10 similar conversations
            
        except Exception as e:
            self.logger.error(f"Error finding similar conversations: {e}")
            return []
    
    async def get_conversation_insights(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive insights about conversation.
        
        Args:
            session_id: Target conversation session
            
        Returns:
            Dictionary of conversation insights
        """
        try:
            # Generate summary
            summary = await self.generate_conversation_summary(session_id)
            
            # Analyze patterns
            patterns = await self.analyze_conversation_patterns(session_id)
            
            # Get dialog context
            dialog_context = await self.dialog_tracker.get_dialog_context_summary(session_id)
            
            # Calculate engagement metrics
            engagement_metrics = await self._calculate_engagement_metrics(session_id)
            
            # Identify conversation quality indicators
            quality_indicators = await self._assess_conversation_quality(session_id)
            
            return {
                "summary": summary.to_dict(),
                "patterns": [p.to_dict() for p in patterns],
                "dialog_context": dialog_context,
                "engagement_metrics": engagement_metrics,
                "quality_indicators": quality_indicators,
                "recommendations": await self._generate_conversation_recommendations(
                    summary, patterns, engagement_metrics
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation insights: {e}")
            return {"error": str(e)}
    
    # Private methods for pattern detection
    
    async def _detect_temporal_patterns(self, messages: List[Dict[str, Any]]) -> List[HistoryPattern]:
        """Detect temporal patterns in message flow."""
        patterns = []
        
        # Analyze message timing
        timestamps = [datetime.fromisoformat(msg["timestamp"]) for msg in messages]
        
        # Detect burst patterns (many messages in short time)
        for i in range(len(timestamps) - 3):
            window = timestamps[i:i+4]
            time_span = window[-1] - window[0]
            
            if time_span.total_seconds() < 300:  # 5 minutes
                pattern = HistoryPattern(
                    pattern_id=f"burst_{i}",
                    pattern_type="message_burst",
                    messages=[messages[j]["id"] for j in range(i, i+4)],
                    confidence=0.8,
                    frequency=1,
                    last_occurrence=window[-1],
                    context_tags=["temporal", "burst"]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_semantic_patterns(self, messages: List[Dict[str, Any]]) -> List[HistoryPattern]:
        """Detect semantic patterns using content analysis."""
        patterns = []
        
        # Group messages by semantic similarity
        content_groups = defaultdict(list)
        
        for i, msg in enumerate(messages):
            content = msg["content"].lower()
            
            # Simple keyword-based grouping (could be enhanced with embeddings)
            if any(keyword in content for keyword in ["error", "bug", "issue", "problem"]):
                content_groups["error_discussion"].append(msg["id"])
            elif any(keyword in content for keyword in ["implement", "create", "build", "develop"]):
                content_groups["implementation_discussion"].append(msg["id"])
            elif any(keyword in content for keyword in ["test", "verify", "check", "validate"]):
                content_groups["testing_discussion"].append(msg["id"])
            elif any(keyword in content for keyword in ["plan", "strategy", "approach", "design"]):
                content_groups["planning_discussion"].append(msg["id"])
        
        # Create patterns for groups with multiple messages
        for group_type, message_ids in content_groups.items():
            if len(message_ids) >= 3:
                pattern = HistoryPattern(
                    pattern_id=f"semantic_{group_type}",
                    pattern_type=f"semantic_{group_type}",
                    messages=message_ids,
                    confidence=0.7,
                    frequency=len(message_ids),
                    last_occurrence=datetime.now(),
                    context_tags=["semantic", group_type]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_intent_patterns(self, session_id: str, 
                                    messages: List[Dict[str, Any]]) -> List[HistoryPattern]:
        """Detect patterns in user intents."""
        patterns = []
        
        # Get dialog context if available
        if session_id in self.dialog_tracker.session_dialogs:
            context = self.dialog_tracker.session_dialogs[session_id]
            intent_history = context.intent_history
            
            # Look for repeated intent sequences
            sequence_length = 3
            for i in range(len(intent_history) - sequence_length + 1):
                sequence = intent_history[i:i+sequence_length]
                sequence_str = " -> ".join([intent.value for intent in sequence])
                
                # Count occurrences of this sequence
                count = 0
                for j in range(len(intent_history) - sequence_length + 1):
                    if intent_history[j:j+sequence_length] == sequence:
                        count += 1
                
                if count >= 2:  # Pattern if occurs at least twice
                    pattern = HistoryPattern(
                        pattern_id=f"intent_sequence_{hashlib.md5(sequence_str.encode()).hexdigest()[:8]}",
                        pattern_type="intent_sequence",
                        messages=[],  # Intent patterns don't map directly to messages
                        confidence=min(0.9, count * 0.3),
                        frequency=count,
                        last_occurrence=datetime.now(),
                        context_tags=["intent", "sequence", sequence_str]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _detect_entropy_patterns(self, messages: List[Dict[str, Any]]) -> List[HistoryPattern]:
        """Detect patterns in message entropy distribution."""
        patterns = []
        
        entropy_scores = [
            msg.get("entropy_score", 0) for msg in messages 
            if msg.get("entropy_score") is not None
        ]
        
        if len(entropy_scores) < 5:
            return patterns
        
        # Detect high-entropy clusters
        high_entropy_indices = [
            i for i, score in enumerate(entropy_scores)
            if score > self.entropy_significance_threshold
        ]
        
        # Look for clusters of high-entropy messages
        clusters = []
        current_cluster = []
        
        for i in high_entropy_indices:
            if current_cluster and i - current_cluster[-1] > 5:  # Gap too large
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [i]
            else:
                current_cluster.append(i)
        
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        
        # Create patterns for clusters
        for cluster_idx, cluster in enumerate(clusters):
            message_ids = [messages[i]["id"] for i in cluster if i < len(messages)]
            
            pattern = HistoryPattern(
                pattern_id=f"entropy_cluster_{cluster_idx}",
                pattern_type="high_entropy_cluster",
                messages=message_ids,
                confidence=0.8,
                frequency=len(cluster),
                last_occurrence=datetime.now(),
                context_tags=["entropy", "cluster", "high_information"]
            )
            patterns.append(pattern)
        
        return patterns
    
    # Private methods for search modes
    
    async def _semantic_search(self, messages: List[ConversationMessage], 
                             query: str, limit: int) -> List[ConversationMessage]:
        """Perform semantic search on messages."""
        # Simple semantic search based on content similarity
        scores = []
        query_lower = query.lower()
        
        for msg in messages:
            content_lower = msg.content.lower()
            
            # Calculate simple similarity score
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            
            if query_words and content_words:
                similarity = len(query_words.intersection(content_words)) / len(query_words.union(content_words))
            else:
                similarity = 0
            
            scores.append((similarity, msg))
        
        # Sort by similarity and return top results
        scores.sort(key=lambda x: x[0], reverse=True)
        return [msg for score, msg in scores[:limit] if score > 0.1]
    
    async def _temporal_search(self, messages: List[ConversationMessage], 
                             query: str, limit: int) -> List[ConversationMessage]:
        """Search based on temporal relevance."""
        # Parse temporal query (simplified)
        now = datetime.now()
        
        if "recent" in query.lower() or "latest" in query.lower():
            return messages[-limit:]
        elif "early" in query.lower() or "beginning" in query.lower():
            return messages[:limit]
        elif "hour" in query.lower():
            cutoff = now - timedelta(hours=1)
            return [msg for msg in messages if msg.timestamp > cutoff][-limit:]
        elif "day" in query.lower():
            cutoff = now - timedelta(days=1)
            return [msg for msg in messages if msg.timestamp > cutoff][-limit:]
        else:
            return messages[-limit:]  # Default to recent
    
    async def _contextual_search(self, messages: List[ConversationMessage], 
                                query: str, limit: int) -> List[ConversationMessage]:
        """Search based on context tags."""
        query_lower = query.lower()
        matches = []
        
        for msg in messages:
            if hasattr(msg, 'context_tags') and msg.context_tags:
                for tag in msg.context_tags:
                    if query_lower in tag.lower():
                        matches.append(msg)
                        break
        
        return matches[:limit]
    
    async def _entropy_search(self, messages: List[ConversationMessage], 
                            query: str, limit: int) -> List[ConversationMessage]:
        """Search based on entropy scores."""
        if "high" in query.lower():
            # Return high-entropy messages
            high_entropy = [
                msg for msg in messages 
                if msg.entropy_score and msg.entropy_score > self.entropy_significance_threshold
            ]
            return high_entropy[-limit:]
        elif "low" in query.lower():
            # Return low-entropy messages
            low_entropy = [
                msg for msg in messages 
                if msg.entropy_score and msg.entropy_score < 0.3
            ]
            return low_entropy[-limit:]
        else:
            # Return messages sorted by entropy
            entropy_sorted = sorted(
                [msg for msg in messages if msg.entropy_score is not None],
                key=lambda x: x.entropy_score,
                reverse=True
            )
            return entropy_sorted[:limit]
    
    async def _intent_search(self, messages: List[ConversationMessage], 
                           query: str, limit: int) -> List[ConversationMessage]:
        """Search based on message types/intents."""
        query_lower = query.lower()
        
        # Map query to message types
        type_mapping = {
            "request": MessageType.USER_REQUEST,
            "response": MessageType.SYSTEM_RESPONSE,
            "tool": MessageType.TOOL_EXECUTION,
            "error": MessageType.ERROR_RECOVERY
        }
        
        target_type = None
        for keyword, msg_type in type_mapping.items():
            if keyword in query_lower:
                target_type = msg_type
                break
        
        if target_type:
            matches = [msg for msg in messages if msg.message_type == target_type]
            return matches[-limit:]
        else:
            return messages[-limit:]  # Default to recent
    
    # Private helper methods
    
    async def _store_patterns_in_memory(self, session_id: str, 
                                      patterns: List[HistoryPattern]) -> None:
        """Store significant patterns in memory graph."""
        try:
            for pattern in patterns:
                if pattern.confidence > 0.7:  # Only store high-confidence patterns
                    await self.memory_manager.create_entities([{
                        "name": f"ConversationPattern_{pattern.pattern_id}",
                        "entityType": "ConversationPattern",
                        "observations": [
                            f"Pattern type: {pattern.pattern_type}",
                            f"Confidence: {pattern.confidence:.3f}",
                            f"Frequency: {pattern.frequency}",
                            f"Context tags: {', '.join(pattern.context_tags)}",
                            f"Last occurrence: {pattern.last_occurrence.isoformat()}"
                        ]
                    }])
                    
                    # Link to conversation session
                    await self.memory_manager.create_relations([{
                        "from": f"ConversationSession_{session_id}",
                        "to": f"ConversationPattern_{pattern.pattern_id}",
                        "relationType": "exhibits_pattern"
                    }])
        except Exception as e:
            self.logger.error(f"Error storing patterns in memory: {e}")
    
    async def _extract_key_decisions(self, high_entropy_messages: List[Dict[str, Any]]) -> List[str]:
        """Extract key decisions from high-entropy messages."""
        decisions = []
        
        for msg in high_entropy_messages:
            content = msg["content"]
            
            # Look for decision indicators
            if any(indicator in content.lower() for indicator in [
                "decided", "choose", "selected", "approved", "confirmed", "agreed"
            ]):
                # Extract the decision (simplified)
                decision_text = content[:100] + "..." if len(content) > 100 else content
                decisions.append(decision_text)
        
        return decisions[:5]  # Return top 5 decisions
    
    async def _identify_unresolved_items(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Identify unresolved questions or issues."""
        unresolved = []
        
        for msg in messages:
            content = msg["content"]
            
            # Look for unresolved indicators
            if any(indicator in content.lower() for indicator in [
                "need to", "should", "todo", "pending", "waiting", "unclear", "question"
            ]) and "?" in content:
                unresolved_text = content[:100] + "..." if len(content) > 100 else content
                unresolved.append(unresolved_text)
        
        return unresolved[-5:]  # Return last 5 unresolved items
    
    async def _extract_technical_context(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract technical context from messages."""
        context = {
            "technologies": set(),
            "frameworks": set(),
            "languages": set(),
            "tools": set()
        }
        
        # Technical term mappings
        tech_terms = {
            "technologies": ["api", "database", "server", "client", "docker", "kubernetes"],
            "frameworks": ["react", "angular", "vue", "flask", "django", "express"],
            "languages": ["python", "javascript", "java", "typescript", "go", "rust"],
            "tools": ["git", "jenkins", "github", "vscode", "docker", "npm"]
        }
        
        for msg in messages:
            content = msg["content"].lower()
            
            for category, terms in tech_terms.items():
                for term in terms:
                    if term in content:
                        context[category].add(term)
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in context.items()}
    
    async def _analyze_dominant_intents(self, session_id: str) -> List[str]:
        """Analyze dominant intents in conversation."""
        if session_id not in self.dialog_tracker.session_dialogs:
            return []
        
        context = self.dialog_tracker.session_dialogs[session_id]
        intent_history = context.intent_history
        
        # Count intent frequencies
        intent_counts = defaultdict(int)
        for intent in intent_history:
            intent_counts[intent.value] += 1
        
        # Return top 3 most frequent intents
        sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)
        return [intent for intent, count in sorted_intents[:3]]
    
    async def _generate_summary_text(self, message_count: int, high_entropy_count: int,
                                   key_decisions: List[str], technical_context: Dict[str, Any],
                                   dominant_intents: List[str]) -> str:
        """Generate human-readable summary text."""
        summary_parts = []
        
        summary_parts.append(f"Conversation with {message_count} messages")
        
        if high_entropy_count > 0:
            summary_parts.append(f"{high_entropy_count} high-information exchanges")
        
        if key_decisions:
            summary_parts.append(f"{len(key_decisions)} key decisions made")
        
        if dominant_intents:
            summary_parts.append(f"Primary intents: {', '.join(dominant_intents)}")
        
        # Add technical context
        tech_items = []
        for category, items in technical_context.items():
            if items:
                tech_items.extend(items[:2])  # Max 2 items per category
        
        if tech_items:
            summary_parts.append(f"Technologies discussed: {', '.join(tech_items[:5])}")
        
        return ". ".join(summary_parts) + "."
    
    async def _store_summary_in_memory(self, summary: ConversationSummary) -> None:
        """Store conversation summary in memory graph."""
        try:
            entity_name = f"ConversationSummary_{summary.session_id}"
            
            observations = [
                f"Summary: {summary.summary_text}",
                f"Message count: {summary.message_count}",
                f"High entropy messages: {summary.high_entropy_count}",
                f"Duration: {summary.time_span}",
                f"Key decisions: {'; '.join(summary.key_decisions[:3])}",
                f"Dominant intents: {', '.join(summary.dominant_intents)}"
            ]
            
            await self.memory_manager.create_entities([{
                "name": entity_name,
                "entityType": "ConversationSummary",
                "observations": observations
            }])
            
            # Link to conversation session
            await self.memory_manager.create_relations([{
                "from": f"ConversationSession_{summary.session_id}",
                "to": entity_name,
                "relationType": "has_summary"
            }])
            
        except Exception as e:
            self.logger.error(f"Error storing summary in memory: {e}")
    
    async def _calculate_conversation_similarity(self, summary1: ConversationSummary, 
                                               conversation2: Dict[str, Any]) -> float:
        """Calculate similarity between conversations (simplified)."""
        # Simple keyword-based similarity
        text1 = summary1.summary_text.lower()
        text2 = " ".join(conversation2.get("observations", [])).lower()
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            return len(words1.intersection(words2)) / len(words1.union(words2))
        return 0.0
    
    async def _calculate_engagement_metrics(self, session_id: str) -> Dict[str, Any]:
        """Calculate conversation engagement metrics."""
        try:
            context = await self.conversation_manager.get_conversation_context(session_id)
            messages = context.get("messages", [])
            
            if not messages:
                return {"error": "No messages"}
            
            # Calculate metrics
            total_messages = len(messages)
            user_messages = len([msg for msg in messages if msg.get("message_type") == "user_request"])
            system_messages = len([msg for msg in messages if msg.get("message_type") == "system_response"])
            
            avg_message_length = sum(len(msg.get("content", "")) for msg in messages) / total_messages
            
            # Calculate response time (simplified)
            response_times = []
            for i in range(1, len(messages)):
                if (messages[i-1].get("message_type") == "user_request" and 
                    messages[i].get("message_type") == "system_response"):
                    time1 = datetime.fromisoformat(messages[i-1]["timestamp"])
                    time2 = datetime.fromisoformat(messages[i]["timestamp"])
                    response_times.append((time2 - time1).total_seconds())
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "system_messages": system_messages,
                "user_system_ratio": user_messages / max(system_messages, 1),
                "average_message_length": avg_message_length,
                "average_response_time_seconds": avg_response_time,
                "conversation_pace": total_messages / max((datetime.fromisoformat(messages[-1]["timestamp"]) - 
                                                         datetime.fromisoformat(messages[0]["timestamp"])).total_seconds() / 3600, 0.1)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement metrics: {e}")
            return {"error": str(e)}
    
    async def _assess_conversation_quality(self, session_id: str) -> Dict[str, Any]:
        """Assess conversation quality indicators."""
        try:
            context = await self.conversation_manager.get_conversation_context(session_id)
            messages = context.get("messages", [])
            high_entropy_messages = context.get("high_entropy_messages", [])
            
            # Quality indicators
            has_clear_objectives = any(
                keyword in msg.get("content", "").lower() 
                for msg in messages[:5]  # Check first 5 messages
                for keyword in ["goal", "objective", "need", "want", "help"]
            )
            
            has_structured_approach = len(high_entropy_messages) > len(messages) * 0.2
            
            has_resolution = any(
                keyword in msg.get("content", "").lower()
                for msg in messages[-5:]  # Check last 5 messages
                for keyword in ["complete", "done", "finished", "resolved", "success"]
            )
            
            information_density = len(high_entropy_messages) / max(len(messages), 1)
            
            return {
                "has_clear_objectives": has_clear_objectives,
                "has_structured_approach": has_structured_approach,
                "has_resolution": has_resolution,
                "information_density": information_density,
                "quality_score": (
                    int(has_clear_objectives) + 
                    int(has_structured_approach) + 
                    int(has_resolution) + 
                    min(information_density * 2, 1)  # Normalize information density
                ) / 4
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing conversation quality: {e}")
            return {"error": str(e)}
    
    async def _generate_conversation_recommendations(self, summary: ConversationSummary,
                                                   patterns: List[HistoryPattern],
                                                   engagement_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving conversation."""
        recommendations = []
        
        # Based on quality indicators
        quality_score = engagement_metrics.get("quality_score", 0.5)
        
        if quality_score < 0.3:
            recommendations.append("Consider establishing clearer objectives at the start")
        
        if summary.high_entropy_count < summary.message_count * 0.1:
            recommendations.append("Increase information density by focusing on key topics")
        
        if len(summary.unresolved_items) > 5:
            recommendations.append("Address unresolved items to improve conversation completion")
        
        # Based on patterns
        pattern_types = [p.pattern_type for p in patterns]
        
        if "error_discussion" in pattern_types:
            recommendations.append("Consider documenting error patterns for future reference")
        
        if "message_burst" in pattern_types:
            recommendations.append("Break down complex topics to avoid information overload")
        
        # Based on engagement
        if engagement_metrics.get("user_system_ratio", 1) < 0.5:
            recommendations.append("Encourage more user interaction and feedback")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _initialize_pattern_matchers(self) -> Dict[str, callable]:
        """Initialize pattern matching functions."""
        return {
            "error_resolution": lambda msgs: len([
                msg for msg in msgs 
                if any(term in msg.get("content", "").lower() 
                      for term in ["error", "fix", "resolved", "solution"])
            ]) >= 3,
            
            "planning_sequence": lambda msgs: any(
                all(term in msg.get("content", "").lower() 
                   for term in ["plan", "step", "approach"])
                for msg in msgs
            ),
            
            "implementation_cycle": lambda msgs: len([
                msg for msg in msgs
                if any(term in msg.get("content", "").lower()
                      for term in ["implement", "code", "create", "build"])
            ]) >= 2
        }