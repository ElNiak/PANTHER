"""Semantic compressor for preserving meaning while reducing token count.

Implements semantic compression techniques that maintain relational meaning
while achieving 30-40% token reduction as identified in research.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)


@dataclass
class SemanticCompressionResult:
    """Result of semantic compression operation."""
    original_content: str
    compressed_content: str
    semantic_preservation_score: float
    token_reduction_ratio: float
    preserved_relations: List[str]
    compression_metadata: Dict[str, Any]


class SemanticRelation:
    """Represents a semantic relationship between concepts."""
    
    def __init__(self, subject: str, predicate: str, object_: str, confidence: float = 1.0):
        self.subject = subject
        self.predicate = predicate
        self.object = object_
        self.confidence = confidence
    
    def __str__(self) -> str:
        return f"{self.subject} --{self.predicate}--> {self.object} ({self.confidence:.2f})"
    
    def __hash__(self) -> int:
        return hash((self.subject, self.predicate, self.object))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, SemanticRelation):
            return False
        return (self.subject == other.subject and 
                self.predicate == other.predicate and 
                self.object == other.object)


class SemanticCompressor:
    """Semantic compressor that preserves relational meaning.
    
    Implements strategies for maintaining semantic relationships:
    1. Entity-relationship extraction and preservation
    2. Hierarchical structure compression
    3. Context-aware redundancy elimination
    4. Semantic clustering for coherent compression
    """
    
    def __init__(self, 
                 target_reduction: float = 0.35,  # 35% token reduction
                 min_semantic_preservation: float = 0.80):  # 80% semantic preservation
        self.target_reduction = target_reduction
        self.min_semantic_preservation = min_semantic_preservation
        
        # Semantic patterns for relation extraction
        self.relation_patterns = [
            # Task relationships
            (r'(\w+)\s+(?:is|has)\s+(\w+)', 'has_property'),
            (r'(\w+)\s+depends\s+on\s+(\w+)', 'depends_on'),
            (r'(\w+)\s+contains\s+(\w+)', 'contains'),
            (r'(\w+)\s+manages\s+(\w+)', 'manages'),
            (r'(\w+)\s+inherits\s+from\s+(\w+)', 'inherits_from'),
            (r'(\w+)\s+implements\s+(\w+)', 'implements'),
            
            # Hierarchical relationships  
            (r'parent[_\s]*task[_\s]*id["\']?\s*[:=]\s*["\']?(\w+)', 'parent_task'),
            (r'subtask[_\s]*of[_\s]*["\']?(\w+)', 'subtask_of'),
            (r'(\w+)\s+includes\s+(\w+)', 'includes'),
            
            # Status and metadata relationships
            (r'status["\']?\s*[:=]\s*["\']?(\w+)', 'has_status'),
            (r'priority["\']?\s*[:=]\s*["\']?(\w+)', 'has_priority'),
            (r'domain["\']?\s*[:=]\s*["\']?(\w+)', 'belongs_to_domain'),
        ]
        
        # Important semantic markers to preserve
        self.semantic_markers = {
            'task_structure': ['task_id', 'parent_task_id', 'subtask', 'hierarchical'],
            'status_info': ['status', 'progress', 'completion', 'priority'],
            'relationships': ['depends_on', 'related_to', 'contains', 'manages'],
            'metadata': ['timestamp', 'description', 'domain', 'artifacts'],
            'actions': ['create', 'update', 'delete', 'execute', 'verify']
        }
        
        # Redundant phrase patterns to compress
        self.redundant_patterns = [
            (r'\b(?:the|a|an)\s+', ''),  # Articles
            (r'\b(?:very|really|quite|rather|pretty)\s+', ''),  # Intensifiers
            (r'\b(?:in order to|so as to)\b', 'to'),  # Verbose infinitives
            (r'\b(?:due to the fact that|owing to the fact that)\b', 'because'),
            (r'\b(?:at this point in time|at the present time)\b', 'now'),
            (r'\b(?:it is important to note that|it should be noted that)\b', ''),
            (r'\b(?:please note that|please be aware that)\b', ''),
        ]
    
    def compress_semantically(self, content: str, context: Dict[str, Any] = None) -> SemanticCompressionResult:
        """Apply semantic compression while preserving relational meaning.
        
        Args:
            content: Original content to compress
            context: Additional context for semantic decisions
            
        Returns:
            SemanticCompressionResult with compressed content and metrics
        """
        context = context or {}
        
        # Extract semantic relationships
        original_relations = self._extract_semantic_relations(content)
        
        # Apply compression strategies
        compressed_content = content
        
        # 1. Remove redundant phrases
        compressed_content = self._remove_redundant_phrases(compressed_content)
        
        # 2. Compress verbose structures while preserving semantics
        compressed_content = self._compress_verbose_structures(compressed_content, original_relations)
        
        # 3. Apply context-aware compression
        compressed_content = self._apply_contextual_compression(compressed_content, context)
        
        # 4. Validate semantic preservation
        compressed_relations = self._extract_semantic_relations(compressed_content)
        semantic_score = self._calculate_semantic_preservation(original_relations, compressed_relations)
        
        # Calculate token reduction
        original_tokens = len(self._tokenize_semantic(content))
        compressed_tokens = len(self._tokenize_semantic(compressed_content))
        reduction_ratio = 1.0 - (compressed_tokens / max(original_tokens, 1))
        
        result = SemanticCompressionResult(
            original_content=content,
            compressed_content=compressed_content,
            semantic_preservation_score=semantic_score,
            token_reduction_ratio=reduction_ratio,
            preserved_relations=[str(rel) for rel in compressed_relations],
            compression_metadata={
                'original_relations_count': len(original_relations),
                'compressed_relations_count': len(compressed_relations),
                'original_tokens': original_tokens,
                'compressed_tokens': compressed_tokens,
                'context': context,
                'timestamp': datetime.now().isoformat(),
                'content_hash': hashlib.md5(content.encode()).hexdigest()[:8]
            }
        )
        
        # Return original if semantic preservation is too low
        if semantic_score < self.min_semantic_preservation:
            logger.warning(f"Semantic preservation {semantic_score:.3f} below threshold {self.min_semantic_preservation}")
            result.compressed_content = content
            result.token_reduction_ratio = 0.0
            result.compression_metadata['semantic_rejected'] = True
        
        return result
    
    def _extract_semantic_relations(self, content: str) -> Set[SemanticRelation]:
        """Extract semantic relationships from content."""
        relations = set()
        
        # Apply relation extraction patterns
        for pattern, relation_type in self.relation_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    subject = match.group(1).strip()
                    object_ = match.group(2).strip()
                    relations.add(SemanticRelation(subject, relation_type, object_))
        
        # Extract JSON-based relationships
        if self._is_json(content):
            json_relations = self._extract_json_relations(content)
            relations.update(json_relations)
        
        return relations
    
    def _extract_json_relations(self, content: str) -> Set[SemanticRelation]:
        """Extract relationships from JSON structure."""
        relations = set()
        
        try:
            data = json.loads(content)
            self._extract_json_relations_recursive(data, relations, "root")
        except json.JSONDecodeError:
            pass
        
        return relations
    
    def _extract_json_relations_recursive(self, obj: Any, relations: Set[SemanticRelation], parent_key: str):
        """Recursively extract relations from JSON object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Key-value relationships
                if isinstance(value, (str, int, float, bool)):
                    relations.add(SemanticRelation(parent_key, f"has_{key}", str(value)))
                
                # Hierarchical relationships
                if key == 'parent_task_id' and value:
                    relations.add(SemanticRelation(parent_key, "child_of", str(value)))
                elif key.endswith('_id'):
                    relations.add(SemanticRelation(parent_key, "has_identifier", str(value)))
                
                # Recursive extraction
                if isinstance(value, (dict, list)):
                    self._extract_json_relations_recursive(value, relations, key)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._extract_json_relations_recursive(item, relations, f"{parent_key}[{i}]")
    
    def _remove_redundant_phrases(self, content: str) -> str:
        """Remove redundant phrases while preserving meaning."""
        compressed = content
        
        for pattern, replacement in self.redundant_patterns:
            compressed = re.sub(pattern, replacement, compressed, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        compressed = re.sub(r'\s+', ' ', compressed).strip()
        
        return compressed
    
    def _compress_verbose_structures(self, content: str, original_relations: Set[SemanticRelation]) -> str:
        """Compress verbose structures while preserving semantic relationships."""
        if self._is_json(content):
            return self._compress_json_structure(content, original_relations)
        
        # Text-based compression
        compressed = content
        
        # Compress verbose task descriptions
        compressed = re.sub(
            r'task\s+with\s+(?:the\s+)?(?:following\s+)?description\s*[:\-]\s*',
            'task: ',
            compressed,
            flags=re.IGNORECASE
        )
        
        # Compress status updates
        compressed = re.sub(
            r'(?:the\s+)?(?:current\s+)?status\s+(?:of\s+(?:the\s+)?task\s+)?(?:is\s+)?(?:currently\s+)?',
            'status: ',
            compressed,
            flags=re.IGNORECASE
        )
        
        # Compress hierarchical references
        compressed = re.sub(
            r'(?:this\s+task\s+)?(?:is\s+a\s+)?(?:sub)?task\s+(?:of\s+)?(?:the\s+)?(?:parent\s+)?task\s+',
            'subtask of ',
            compressed,
            flags=re.IGNORECASE
        )
        
        return compressed
    
    def _compress_json_structure(self, content: str, original_relations: Set[SemanticRelation]) -> str:
        """Compress JSON while preserving semantic structure."""
        try:
            data = json.loads(content)
            compressed_data = self._compress_json_recursive(data, original_relations)
            return json.dumps(compressed_data, separators=(',', ':'))  # Compact JSON
        except json.JSONDecodeError:
            return content
    
    def _compress_json_recursive(self, obj: Any, relations: Set[SemanticRelation]) -> Any:
        """Recursively compress JSON while preserving relationships."""
        if isinstance(obj, dict):
            compressed = {}
            
            for key, value in obj.items():
                # Preserve semantic markers
                if any(marker in key.lower() for markers in self.semantic_markers.values() 
                      for marker in markers):
                    if isinstance(value, (dict, list)):
                        compressed[key] = self._compress_json_recursive(value, relations)
                    else:
                        compressed[key] = value
                
                # Compress descriptions but preserve key information
                elif key.lower() in ['description', 'content']:
                    if isinstance(value, str):
                        compressed[key] = self._compress_description(value)
                    else:
                        compressed[key] = value
                
                # Preserve other important fields
                else:
                    if isinstance(value, (dict, list)):
                        compressed[key] = self._compress_json_recursive(value, relations)
                    else:
                        compressed[key] = value
            
            return compressed
        
        elif isinstance(obj, list):
            return [self._compress_json_recursive(item, relations) for item in obj]
        
        else:
            return obj
    
    def _compress_description(self, description: str) -> str:
        """Compress description text while preserving key information."""
        # Remove filler words and phrases
        compressed = description
        
        # Remove redundant phrases specific to descriptions
        redundant_desc_patterns = [
            (r'\b(?:This task involves|This task is about|The purpose of this task is to)\b', ''),
            (r'\b(?:In this task, we will|For this task, we need to|The goal is to)\b', ''),
            (r'\b(?:It is necessary to|We need to|We must)\b', ''),
            (r'\b(?:make sure to|ensure that|be sure to)\b', ''),
        ]
        
        for pattern, replacement in redundant_desc_patterns:
            compressed = re.sub(pattern, replacement, compressed, flags=re.IGNORECASE)
        
        # Clean up and ensure it's still meaningful
        compressed = re.sub(r'\s+', ' ', compressed).strip()
        
        # Don't over-compress - keep minimum length
        if len(compressed) < len(description) * 0.3:
            return description  # Too aggressive, return original
        
        return compressed
    
    def _apply_contextual_compression(self, content: str, context: Dict[str, Any]) -> str:
        """Apply context-aware compression."""
        if not context:
            return content
        
        compressed = content
        
        # If context provides redundant information, remove it from content
        for context_key, context_value in context.items():
            if isinstance(context_value, str) and len(context_value) > 3:
                # Remove redundant mentions of context information
                pattern = re.escape(context_value)
                # Only remove if it appears multiple times
                if len(re.findall(pattern, compressed, re.IGNORECASE)) > 1:
                    compressed = re.sub(pattern, f"[{context_key}]", compressed, count=1, flags=re.IGNORECASE)
        
        return compressed
    
    def _calculate_semantic_preservation(self, original_relations: Set[SemanticRelation], 
                                       compressed_relations: Set[SemanticRelation]) -> float:
        """Calculate how well semantic relationships are preserved."""
        if not original_relations:
            return 1.0  # No relationships to preserve
        
        # Count preserved relationships
        preserved_count = len(original_relations & compressed_relations)
        total_count = len(original_relations)
        
        preservation_ratio = preserved_count / total_count
        
        # Weight by relationship importance
        important_relation_types = {'parent_task', 'depends_on', 'has_status', 'has_priority'}
        
        important_original = {rel for rel in original_relations 
                            if rel.predicate in important_relation_types}
        important_preserved = {rel for rel in compressed_relations 
                             if rel.predicate in important_relation_types}
        
        important_preservation = 1.0
        if important_original:
            important_preservation = len(important_original & important_preserved) / len(important_original)
        
        # Combine scores (70% general, 30% important relationships)
        final_score = (preservation_ratio * 0.7) + (important_preservation * 0.3)
        
        return min(final_score, 1.0)
    
    def _tokenize_semantic(self, content: str) -> List[str]:
        """Tokenize content for semantic analysis."""
        # Simple word tokenization that preserves semantic units
        tokens = re.findall(r'\w+|[^\w\s]', content)
        return [token for token in tokens if token.strip()]
    
    def _is_json(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content.strip())
            return True
        except json.JSONDecodeError:
            return False
    
    def get_semantic_stats(self) -> Dict[str, Any]:
        """Get semantic compression statistics."""
        return {
            'target_reduction': self.target_reduction,
            'min_semantic_preservation': self.min_semantic_preservation,
            'relation_patterns_count': len(self.relation_patterns),
            'semantic_markers': self.semantic_markers,
            'redundant_patterns_count': len(self.redundant_patterns)
        }