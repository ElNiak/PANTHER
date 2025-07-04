"""Entropy-based processing engine for memory operations.

Implements Shannon's information theory to trigger incremental processing
based on information entropy, preventing token explosion in memory queries.
"""

import json
import logging
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import Counter
import re

logger = logging.getLogger(__name__)


class ProcessingTrigger(Enum):
    """Triggers for entropy-based processing."""
    HIGH_ENTROPY = "high_entropy"
    LOW_ENTROPY = "low_entropy"
    ENTROPY_SPIKE = "entropy_spike"
    INFORMATION_OVERFLOW = "information_overflow"
    PATTERN_SATURATION = "pattern_saturation"
    NOVELTY_DETECTED = "novelty_detected"
    REDUNDANCY_THRESHOLD = "redundancy_threshold"


class ProcessingMode(Enum):
    """Processing modes based on entropy analysis."""
    INCREMENTAL = "incremental"
    BATCH = "batch"
    STREAMING = "streaming"
    COMPRESSED = "compressed"
    FILTERED = "filtered"
    BYPASSED = "bypassed"


@dataclass
class EntropyThresholds:
    """Entropy thresholds for triggering different processing modes."""
    high_entropy_threshold: float = 0.8  # Trigger incremental processing
    low_entropy_threshold: float = 0.3   # Trigger compression/filtering
    entropy_spike_threshold: float = 0.5  # Relative increase to detect spikes
    information_overflow_threshold: int = 10000  # Token count threshold
    pattern_saturation_threshold: float = 0.9   # Pattern repetition threshold
    novelty_threshold: float = 0.7  # Threshold for detecting new information
    
    def __post_init__(self):
        # Validate thresholds
        if not (0 <= self.low_entropy_threshold <= self.high_entropy_threshold <= 1.0):
            raise ValueError("Entropy thresholds must be in range [0, 1] with low <= high")


@dataclass
class EntropyAnalysis:
    """Result of entropy analysis on content."""
    content_entropy: float
    token_entropy: float
    pattern_entropy: float
    novelty_score: float
    redundancy_score: float
    information_density: float
    processing_triggers: List[ProcessingTrigger]
    recommended_mode: ProcessingMode
    chunk_suggestions: List[Tuple[int, int]]  # (start, end) positions for chunking
    metadata: Dict[str, Any]


class EntropyProcessor:
    """Processes content using information entropy to optimize memory operations.
    
    Implements Shannon's information theory to:
    1. Measure information content in memory queries
    2. Detect information overflow conditions
    3. Trigger appropriate processing modes
    4. Suggest optimal chunking strategies
    5. Identify redundancy and novelty patterns
    """
    
    def __init__(self, thresholds: Optional[EntropyThresholds] = None):
        self.thresholds = thresholds or EntropyThresholds()
        
        # Entropy calculation history for spike detection
        self.entropy_history: List[Tuple[datetime, float]] = []
        self.max_history_size = 100
        
        # Pattern tracking for saturation detection
        self.pattern_frequencies: Dict[str, int] = {}
        self.total_patterns_seen = 0
        
        # Novelty detection state
        self.known_concepts: Set[str] = set()
        self.concept_embeddings: Dict[str, List[float]] = {}
        
        # Token frequency tracking
        self.global_token_frequencies: Dict[str, int] = {}
        self.total_tokens_processed = 0
    
    def analyze_content_entropy(self, content: str, context: Dict[str, Any] = None) -> EntropyAnalysis:
        """Analyze information entropy of content and determine processing strategy.
        
        Args:
            content: Content to analyze
            context: Additional context for analysis
            
        Returns:
            EntropyAnalysis with processing recommendations
        """
        context = context or {}
        analysis_start = datetime.now()
        
        # Calculate different entropy measures
        content_entropy = self._calculate_content_entropy(content)
        token_entropy = self._calculate_token_entropy(content)
        pattern_entropy = self._calculate_pattern_entropy(content)
        
        # Calculate information density and novelty
        novelty_score = self._calculate_novelty_score(content)
        redundancy_score = self._calculate_redundancy_score(content)
        information_density = self._calculate_information_density(content)
        
        # Detect processing triggers
        triggers = self._detect_processing_triggers(
            content_entropy, token_entropy, pattern_entropy, 
            novelty_score, redundancy_score, len(content)
        )
        
        # Recommend processing mode
        recommended_mode = self._recommend_processing_mode(
            content_entropy, triggers, len(content), context
        )
        
        # Suggest chunking strategy
        chunk_suggestions = self._suggest_chunking_strategy(
            content, content_entropy, information_density
        )
        
        # Update state
        self._update_processing_state(content, content_entropy, pattern_entropy)
        
        analysis = EntropyAnalysis(
            content_entropy=content_entropy,
            token_entropy=token_entropy,
            pattern_entropy=pattern_entropy,
            novelty_score=novelty_score,
            redundancy_score=redundancy_score,
            information_density=information_density,
            processing_triggers=triggers,
            recommended_mode=recommended_mode,
            chunk_suggestions=chunk_suggestions,
            metadata={
                'analysis_time_ms': (datetime.now() - analysis_start).total_seconds() * 1000,
                'content_length': len(content),
                'token_count': len(content.split()),
                'unique_tokens': len(set(content.lower().split())),
                'context': context,
                'thresholds_used': self.thresholds.__dict__
            }
        )
        
        logger.debug(f"Entropy analysis: entropy={content_entropy:.3f}, mode={recommended_mode.value}, triggers={[t.value for t in triggers]}")
        
        return analysis
    
    def _calculate_content_entropy(self, content: str) -> float:
        """Calculate Shannon entropy of content."""
        if not content:
            return 0.0
        
        # Character-level entropy
        char_counts = Counter(content)
        total_chars = len(content)
        
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize to [0, 1] range
        max_entropy = math.log2(min(len(char_counts), 256))  # ASCII range
        if max_entropy > 0:
            entropy = entropy / max_entropy
        
        return min(entropy, 1.0)
    
    def _calculate_token_entropy(self, content: str) -> float:
        """Calculate entropy based on token distribution."""
        tokens = self._tokenize_content(content)
        if not tokens:
            return 0.0
        
        token_counts = Counter(tokens)
        total_tokens = len(tokens)
        
        entropy = 0.0
        for count in token_counts.values():
            probability = count / total_tokens
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize by theoretical maximum
        max_entropy = math.log2(len(token_counts))
        if max_entropy > 0:
            entropy = entropy / max_entropy
        
        return min(entropy, 1.0)
    
    def _calculate_pattern_entropy(self, content: str) -> float:
        """Calculate entropy based on structural patterns."""
        patterns = self._extract_patterns(content)
        if not patterns:
            return 0.0
        
        pattern_counts = Counter(patterns)
        total_patterns = len(patterns)
        
        entropy = 0.0
        for count in pattern_counts.values():
            probability = count / total_patterns
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        # Normalize
        max_entropy = math.log2(len(pattern_counts))
        if max_entropy > 0:
            entropy = entropy / max_entropy
        
        return min(entropy, 1.0)
    
    def _calculate_novelty_score(self, content: str) -> float:
        """Calculate novelty score based on previously seen concepts."""
        concepts = self._extract_concepts(content)
        if not concepts:
            return 0.0
        
        novel_concepts = [c for c in concepts if c not in self.known_concepts]
        novelty_score = len(novel_concepts) / len(concepts)
        
        # Update known concepts
        self.known_concepts.update(concepts)
        
        return novelty_score
    
    def _calculate_redundancy_score(self, content: str) -> float:
        """Calculate redundancy score based on repetition."""
        tokens = self._tokenize_content(content)
        if not tokens:
            return 0.0
        
        token_counts = Counter(tokens)
        unique_tokens = len(token_counts)
        total_tokens = len(tokens)
        
        # Calculate repetition factor
        repetition_factor = total_tokens / max(unique_tokens, 1)
        
        # Normalize to [0, 1] where 1 = maximum redundancy
        redundancy_score = 1.0 - (unique_tokens / max(total_tokens, 1))
        
        return min(redundancy_score, 1.0)
    
    def _calculate_information_density(self, content: str) -> float:
        """Calculate information density (information per character)."""
        if not content:
            return 0.0
        
        # Use token entropy as proxy for information content
        token_entropy = self._calculate_token_entropy(content)
        content_length = len(content)
        
        # Information density = entropy per character
        density = (token_entropy * len(content.split())) / content_length
        
        return min(density, 1.0)
    
    def _detect_processing_triggers(self, 
                                  content_entropy: float,
                                  token_entropy: float, 
                                  pattern_entropy: float,
                                  novelty_score: float,
                                  redundancy_score: float,
                                  content_length: int) -> List[ProcessingTrigger]:
        """Detect triggers for different processing modes."""
        triggers = []
        
        # High entropy trigger
        if content_entropy > self.thresholds.high_entropy_threshold:
            triggers.append(ProcessingTrigger.HIGH_ENTROPY)
        
        # Low entropy trigger
        if content_entropy < self.thresholds.low_entropy_threshold:
            triggers.append(ProcessingTrigger.LOW_ENTROPY)
        
        # Entropy spike detection
        if self._detect_entropy_spike(content_entropy):
            triggers.append(ProcessingTrigger.ENTROPY_SPIKE)
        
        # Information overflow
        if content_length > self.thresholds.information_overflow_threshold:
            triggers.append(ProcessingTrigger.INFORMATION_OVERFLOW)
        
        # Pattern saturation
        if pattern_entropy < (1.0 - self.thresholds.pattern_saturation_threshold):
            triggers.append(ProcessingTrigger.PATTERN_SATURATION)
        
        # Novelty detection
        if novelty_score > self.thresholds.novelty_threshold:
            triggers.append(ProcessingTrigger.NOVELTY_DETECTED)
        
        # Redundancy threshold
        if redundancy_score > 0.7:  # High redundancy
            triggers.append(ProcessingTrigger.REDUNDANCY_THRESHOLD)
        
        return triggers
    
    def _detect_entropy_spike(self, current_entropy: float) -> bool:
        """Detect if current entropy represents a spike."""
        if len(self.entropy_history) < 3:
            return False
        
        # Calculate recent average
        recent_entropies = [e for _, e in self.entropy_history[-5:]]
        recent_avg = sum(recent_entropies) / len(recent_entropies)
        
        # Check for spike
        relative_increase = (current_entropy - recent_avg) / max(recent_avg, 0.1)
        
        return relative_increase > self.thresholds.entropy_spike_threshold
    
    def _recommend_processing_mode(self,
                                 content_entropy: float,
                                 triggers: List[ProcessingTrigger],
                                 content_length: int,
                                 context: Dict[str, Any]) -> ProcessingMode:
        """Recommend optimal processing mode based on analysis."""
        
        # High priority triggers
        if ProcessingTrigger.INFORMATION_OVERFLOW in triggers:
            return ProcessingMode.INCREMENTAL
        
        if ProcessingTrigger.HIGH_ENTROPY in triggers:
            return ProcessingMode.STREAMING
        
        # Medium priority triggers
        if ProcessingTrigger.ENTROPY_SPIKE in triggers:
            return ProcessingMode.BATCH
        
        if ProcessingTrigger.NOVELTY_DETECTED in triggers:
            return ProcessingMode.STREAMING
        
        # Low priority triggers
        if ProcessingTrigger.LOW_ENTROPY in triggers or ProcessingTrigger.REDUNDANCY_THRESHOLD in triggers:
            return ProcessingMode.COMPRESSED
        
        if ProcessingTrigger.PATTERN_SATURATION in triggers:
            return ProcessingMode.FILTERED
        
        # Context-based decisions
        if context.get('memory_operation_type') == 'bulk_query':
            return ProcessingMode.INCREMENTAL
        
        if context.get('real_time_required', False):
            return ProcessingMode.STREAMING
        
        # Default based on content size
        if content_length < 1000:
            return ProcessingMode.BATCH
        elif content_length < 5000:
            return ProcessingMode.INCREMENTAL
        else:
            return ProcessingMode.STREAMING
    
    def _suggest_chunking_strategy(self,
                                 content: str,
                                 content_entropy: float,
                                 information_density: float) -> List[Tuple[int, int]]:
        """Suggest optimal chunking strategy based on entropy analysis."""
        if len(content) < 1000:
            return [(0, len(content))]  # Single chunk for small content
        
        chunks = []
        chunk_size = self._calculate_optimal_chunk_size(content_entropy, information_density)
        
        # Entropy-aware chunking
        if content_entropy > 0.7:  # High entropy - smaller chunks
            chunk_size = min(chunk_size, 800)
        elif content_entropy < 0.3:  # Low entropy - larger chunks
            chunk_size = max(chunk_size, 2000)
        
        # Create chunks with overlap for context preservation
        overlap = max(50, chunk_size // 10)
        start = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            
            # Adjust end to natural break point (sentence, paragraph)
            if end < len(content):
                end = self._find_natural_break_point(content, end)
            
            chunks.append((start, end))
            
            if end >= len(content):
                break
            
            start = end - overlap
        
        return chunks
    
    def _calculate_optimal_chunk_size(self, entropy: float, density: float) -> int:
        """Calculate optimal chunk size based on entropy and density."""
        base_size = 1200
        
        # Adjust based on entropy
        entropy_factor = 1.0 - entropy  # Lower entropy allows larger chunks
        
        # Adjust based on density
        density_factor = 1.0 + density  # Higher density needs smaller chunks
        
        optimal_size = int(base_size * entropy_factor / density_factor)
        
        # Clamp to reasonable bounds
        return max(500, min(optimal_size, 3000))
    
    def _find_natural_break_point(self, content: str, preferred_end: int) -> int:
        """Find natural break point near preferred end position."""
        # Look for sentence endings within reasonable distance
        search_start = max(0, preferred_end - 100)
        search_end = min(len(content), preferred_end + 100)
        
        search_text = content[search_start:search_end]
        
        # Find sentence endings
        sentence_endings = []
        for i, char in enumerate(search_text):
            if char in '.!?':
                # Check if it's likely end of sentence
                if i + 1 >= len(search_text) or search_text[i + 1].isspace():
                    sentence_endings.append(search_start + i + 1)
        
        if sentence_endings:
            # Find closest to preferred end
            closest = min(sentence_endings, key=lambda x: abs(x - preferred_end))
            return closest
        
        # Fall back to paragraph breaks
        paragraph_breaks = [i for i, char in enumerate(content[search_start:search_end]) 
                          if char == '\n']
        if paragraph_breaks:
            closest = min(paragraph_breaks, key=lambda x: abs((search_start + x) - preferred_end))
            return search_start + closest
        
        # Fall back to space breaks
        space_breaks = [i for i, char in enumerate(content[search_start:search_end])
                       if char == ' ']
        if space_breaks:
            closest = min(space_breaks, key=lambda x: abs((search_start + x) - preferred_end))
            return search_start + closest
        
        # Last resort - use preferred end
        return preferred_end
    
    def _update_processing_state(self, content: str, content_entropy: float, pattern_entropy: float):
        """Update internal state for future entropy calculations."""
        # Update entropy history
        self.entropy_history.append((datetime.now(), content_entropy))
        if len(self.entropy_history) > self.max_history_size:
            self.entropy_history = self.entropy_history[-self.max_history_size:]
        
        # Update pattern frequencies
        patterns = self._extract_patterns(content)
        for pattern in patterns:
            self.pattern_frequencies[pattern] = self.pattern_frequencies.get(pattern, 0) + 1
        self.total_patterns_seen += len(patterns)
        
        # Update token frequencies
        tokens = self._tokenize_content(content)
        for token in tokens:
            self.global_token_frequencies[token] = self.global_token_frequencies.get(token, 0) + 1
        self.total_tokens_processed += len(tokens)
    
    def _tokenize_content(self, content: str) -> List[str]:
        """Tokenize content for entropy analysis."""
        # Simple word tokenization with some preprocessing
        tokens = re.findall(r'\w+|[^\w\s]', content.lower())
        return [token for token in tokens if len(token) > 1]  # Filter single characters
    
    def _extract_patterns(self, content: str) -> List[str]:
        """Extract structural patterns from content."""
        patterns = []
        
        # JSON patterns
        if self._is_json_like(content):
            patterns.extend(self._extract_json_patterns(content))
        
        # Text patterns
        patterns.extend(self._extract_text_patterns(content))
        
        return patterns
    
    def _extract_concepts(self, content: str) -> List[str]:
        """Extract high-level concepts from content."""
        concepts = []
        
        # Extract capitalized words (likely proper nouns/concepts)
        concepts.extend(re.findall(r'\b[A-Z][a-z]+\b', content))
        
        # Extract technical terms (words with underscores or mixed case)
        concepts.extend(re.findall(r'\b\w*[A-Z]\w*\b', content))
        concepts.extend(re.findall(r'\b\w+_\w+\b', content))
        
        # Extract domain-specific terms
        domain_patterns = [
            r'\b\w*task\w*\b',
            r'\b\w*memory\w*\b', 
            r'\b\w*process\w*\b',
            r'\b\w*system\w*\b',
            r'\b\w*management\w*\b'
        ]
        
        for pattern in domain_patterns:
            concepts.extend(re.findall(pattern, content, re.IGNORECASE))
        
        return list(set(concepts))  # Remove duplicates
    
    def _is_json_like(self, content: str) -> bool:
        """Check if content appears to be JSON-like."""
        json_indicators = ['{', '}', '[', ']', ':', '"']
        return sum(content.count(indicator) for indicator in json_indicators) > len(content) * 0.1
    
    def _extract_json_patterns(self, content: str) -> List[str]:
        """Extract patterns from JSON-like content."""
        patterns = []
        
        # Structure patterns
        if '{' in content and '}' in content:
            patterns.append('object_structure')
        if '[' in content and ']' in content:
            patterns.append('array_structure')
        
        # Key patterns
        key_patterns = re.findall(r'"(\w+)":', content)
        patterns.extend([f'key_{key}' for key in set(key_patterns)])
        
        return patterns
    
    def _extract_text_patterns(self, content: str) -> List[str]:
        """Extract patterns from text content."""
        patterns = []
        
        # Sentence patterns
        sentences = content.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        if avg_sentence_length < 10:
            patterns.append('short_sentences')
        elif avg_sentence_length > 25:
            patterns.append('long_sentences')
        else:
            patterns.append('medium_sentences')
        
        # Punctuation patterns
        if content.count('!') > len(content.split()) * 0.1:
            patterns.append('exclamatory')
        if content.count('?') > len(content.split()) * 0.1:
            patterns.append('interrogative')
        
        # Structure patterns
        if '\n\n' in content:
            patterns.append('paragraphed')
        if content.count('\n') > content.count(' ') * 0.1:
            patterns.append('multiline')
        
        return patterns
    
    def get_entropy_statistics(self) -> Dict[str, Any]:
        """Get statistics about entropy processing."""
        recent_entropies = [e for _, e in self.entropy_history[-20:]] if self.entropy_history else []
        
        return {
            'total_content_processed': len(self.entropy_history),
            'average_entropy': sum(recent_entropies) / max(len(recent_entropies), 1),
            'entropy_variance': self._calculate_variance(recent_entropies),
            'unique_patterns_seen': len(self.pattern_frequencies),
            'most_common_patterns': sorted(
                self.pattern_frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10],
            'vocabulary_size': len(self.global_token_frequencies),
            'total_tokens_processed': self.total_tokens_processed,
            'known_concepts_count': len(self.known_concepts),
            'thresholds': self.thresholds.__dict__
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance