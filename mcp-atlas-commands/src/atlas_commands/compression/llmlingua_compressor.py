"""LLMLingua-inspired compression for inter-tool communication.

Based on research findings from Microsoft's LLMLingua paper:
- Achieves 3-5x compression ratios
- Maintains 90% accuracy in preserved content
- Uses information-theoretic importance scoring
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of compression operation."""
    original_content: str
    compressed_content: str
    compression_ratio: float
    preserved_tokens: int
    original_tokens: int
    metadata: Dict[str, Any]
    
    @property
    def efficiency_score(self) -> float:
        """Calculate efficiency score (higher is better)."""
        return self.compression_ratio * (self.preserved_tokens / max(self.original_tokens, 1))


@dataclass 
class CompressionConfig:
    """Configuration for LLMLingua compression."""
    target_compression_ratio: float = 0.5  # Compress to 50% of original
    min_importance_threshold: float = 0.3
    preserve_structure_keywords: bool = True
    preserve_mcp_metadata: bool = True
    enable_semantic_clustering: bool = True
    quality_threshold: float = 0.85  # Minimum quality to accept compression
    

class LLMLinguaCompressor:
    """LLMLingua-inspired compressor for MCP tool communication.
    
    Implements information-theoretic compression strategies:
    1. Token importance scoring using TF-IDF-like metrics
    2. Structural preservation for MCP-specific elements
    3. Semantic clustering to maintain context coherence
    4. Quality validation to ensure compressed content remains useful
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self._token_frequencies: Dict[str, int] = {}
        self._document_frequencies: Dict[str, int] = {}
        self._total_documents = 0
        self._quality_cache: Dict[str, float] = {}
        
        # MCP-specific keywords to preserve
        self.mcp_keywords = {
            'task_id', 'project_name', 'status', 'priority', 'description',
            'content', 'metadata', 'artifacts', 'dependencies', 'hierarchical',
            'subtask', 'parent_task_id', 'completion_percentage', 'domain',
            'error', 'success', 'result', 'timestamp', 'backup', 'checkpoint'
        }
        
        # Structure indicators to preserve
        self.structure_indicators = {
            '{', '}', '[', ']', ':', ',', '"', "'",
            'true', 'false', 'null', 'None', 'True', 'False'
        }
    
    def compress_tool_communication(self, content: str, context: Dict[str, Any] = None) -> CompressionResult:
        """Compress content for inter-tool communication.
        
        Args:
            content: Original content to compress
            context: Additional context for compression decisions
            
        Returns:
            CompressionResult with compressed content and metrics
        """
        context = context or {}
        
        # Tokenize and analyze content
        tokens = self._tokenize(content)
        token_importance = self._calculate_token_importance(tokens, context)
        
        # Apply compression strategies
        compressed_tokens = self._compress_tokens(tokens, token_importance)
        compressed_content = self._reconstruct_content(compressed_tokens, content)
        
        # Calculate metrics
        original_tokens = len(tokens)
        preserved_tokens = len(compressed_tokens)
        compression_ratio = preserved_tokens / max(original_tokens, 1)
        
        # Validate quality
        quality_score = self._validate_compression_quality(content, compressed_content, context)
        
        result = CompressionResult(
            original_content=content,
            compressed_content=compressed_content,
            compression_ratio=compression_ratio,
            preserved_tokens=preserved_tokens,
            original_tokens=original_tokens,
            metadata={
                'quality_score': quality_score,
                'context': context,
                'compression_config': self.config.__dict__,
                'timestamp': datetime.now().isoformat(),
                'content_hash': hashlib.md5(content.encode()).hexdigest()[:8]
            }
        )
        
        # Only return compression if quality is acceptable
        if quality_score >= self.config.quality_threshold:
            self._update_learning_data(tokens, token_importance)
            return result
        else:
            logger.warning(f"Compression quality {quality_score:.3f} below threshold {self.config.quality_threshold}, returning original")
            return CompressionResult(
                original_content=content,
                compressed_content=content,  # Return original if quality too low
                compression_ratio=1.0,
                preserved_tokens=original_tokens,
                original_tokens=original_tokens,
                metadata={**result.metadata, 'quality_rejected': True}
            )
    
    def _tokenize(self, content: str) -> List[str]:
        """Tokenize content while preserving structure."""
        # Handle JSON structure preservation
        if self._is_json(content):
            return self._tokenize_json_aware(content)
        
        # Standard tokenization with structure awareness
        # Split on whitespace and punctuation while preserving structure
        tokens = re.findall(r'\w+|[^\w\s]', content)
        return [token for token in tokens if token.strip()]
    
    def _tokenize_json_aware(self, content: str) -> List[str]:
        """JSON-aware tokenization that preserves structure."""
        try:
            # Parse JSON to identify structure vs content
            parsed = json.loads(content)
            tokens = []
            
            def extract_tokens(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        # Preserve key names (structure)
                        tokens.extend(['{', f'"{key}"', ':'])
                        extract_tokens(value, f"{path}.{key}")
                        tokens.append(',')
                elif isinstance(obj, list):
                    tokens.append('[')
                    for i, item in enumerate(obj):
                        extract_tokens(item, f"{path}[{i}]")
                        if i < len(obj) - 1:
                            tokens.append(',')
                    tokens.append(']')
                else:
                    # Content tokens - these are candidates for compression
                    if isinstance(obj, str):
                        content_tokens = re.findall(r'\w+', str(obj))
                        tokens.extend(content_tokens)
                    else:
                        tokens.append(str(obj))
            
            extract_tokens(parsed)
            return tokens
            
        except json.JSONDecodeError:
            # Fall back to regular tokenization
            return re.findall(r'\w+|[^\w\s]', content)
    
    def _calculate_token_importance(self, tokens: List[str], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate importance score for each token using TF-IDF-like metrics."""
        importance_scores = {}
        token_counts = {}
        
        # Count token frequencies
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1
        
        total_tokens = len(tokens)
        
        for token in set(tokens):
            # Base importance from frequency (TF component)
            tf = token_counts[token] / total_tokens
            
            # Inverse document frequency (IDF component)
            # Use global frequencies if available, otherwise estimate
            idf = self._calculate_idf(token)
            
            # Context-specific importance boosts
            context_boost = self._get_context_boost(token, context)
            
            # MCP-specific importance
            mcp_boost = self._get_mcp_importance_boost(token)
            
            # Structure preservation
            structure_boost = self._get_structure_boost(token)
            
            # Combine scores
            importance = (tf * idf * context_boost * mcp_boost * structure_boost)
            importance_scores[token] = min(importance, 2.0)  # Cap at 2.0
        
        return importance_scores
    
    def _calculate_idf(self, token: str) -> float:
        """Calculate inverse document frequency."""
        if self._total_documents == 0:
            return 1.0
        
        doc_freq = self._document_frequencies.get(token, 1)
        return max(0.1, 1.0 - (doc_freq / self._total_documents))
    
    def _get_context_boost(self, token: str, context: Dict[str, Any]) -> float:
        """Calculate context-specific importance boost."""
        boost = 1.0
        
        # Boost tokens that appear in context keys/values
        for key, value in context.items():
            if token.lower() in str(key).lower():
                boost *= 1.5
            if token.lower() in str(value).lower():
                boost *= 1.2
        
        return boost
    
    def _get_mcp_importance_boost(self, token: str) -> float:
        """Boost MCP-specific keywords."""
        if token.lower() in self.mcp_keywords:
            return 2.0
        return 1.0
    
    def _get_structure_boost(self, token: str) -> float:
        """Boost structural elements."""
        if self.config.preserve_structure_keywords and token in self.structure_indicators:
            return 3.0
        return 1.0
    
    def _compress_tokens(self, tokens: List[str], importance_scores: Dict[str, float]) -> List[str]:
        """Compress tokens based on importance scores."""
        # Sort tokens by position and importance
        token_importance_pairs = [
            (i, token, importance_scores.get(token, 0.0))
            for i, token in enumerate(tokens)
        ]
        
        # Apply different compression strategies
        if self.config.enable_semantic_clustering:
            return self._semantic_clustering_compression(token_importance_pairs)
        else:
            return self._threshold_compression(token_importance_pairs)
    
    def _threshold_compression(self, token_importance_pairs: List[Tuple[int, str, float]]) -> List[str]:
        """Simple threshold-based compression."""
        preserved_tokens = []
        
        for pos, token, importance in token_importance_pairs:
            if importance >= self.config.min_importance_threshold:
                preserved_tokens.append(token)
            elif pos % 3 == 0:  # Keep every 3rd token regardless to maintain flow
                preserved_tokens.append(token)
        
        return preserved_tokens
    
    def _semantic_clustering_compression(self, token_importance_pairs: List[Tuple[int, str, float]]) -> List[str]:
        """Semantic clustering-based compression to maintain coherence."""
        preserved_tokens = []
        current_cluster = []
        cluster_importance = 0.0
        
        for pos, token, importance in token_importance_pairs:
            current_cluster.append((pos, token, importance))
            cluster_importance += importance
            
            # End cluster on structure tokens or every 5 tokens
            if (token in self.structure_indicators or 
                len(current_cluster) >= 5 or 
                pos == len(token_importance_pairs) - 1):
                
                # Decide whether to preserve this cluster
                avg_importance = cluster_importance / len(current_cluster)
                
                if avg_importance >= self.config.min_importance_threshold:
                    # Preserve entire cluster
                    preserved_tokens.extend([t[1] for t in current_cluster])
                else:
                    # Preserve only high-importance tokens from cluster
                    for _, cluster_token, cluster_imp in current_cluster:
                        if cluster_imp >= self.config.min_importance_threshold * 1.5:
                            preserved_tokens.append(cluster_token)
                
                # Reset for next cluster
                current_cluster = []
                cluster_importance = 0.0
        
        return preserved_tokens
    
    def _reconstruct_content(self, compressed_tokens: List[str], original_content: str) -> str:
        """Reconstruct content from compressed tokens."""
        if self._is_json(original_content):
            return self._reconstruct_json(compressed_tokens, original_content)
        
        # Simple reconstruction with proper spacing
        result = []
        for i, token in enumerate(compressed_tokens):
            if i > 0 and not (token in self.structure_indicators or 
                             compressed_tokens[i-1] in self.structure_indicators):
                result.append(' ')
            result.append(token)
        
        return ''.join(result)
    
    def _reconstruct_json(self, compressed_tokens: List[str], original_content: str) -> str:
        """Reconstruct JSON from compressed tokens."""
        try:
            # Try to maintain valid JSON structure
            result = []
            in_string = False
            brace_stack = []
            
            for token in compressed_tokens:
                if token == '"' and (not result or result[-1] != '\\'):
                    in_string = not in_string
                
                if not in_string:
                    if token in ['{', '[']:
                        brace_stack.append(token)
                    elif token in ['}', ']']:
                        if brace_stack:
                            brace_stack.pop()
                
                result.append(token)
            
            # Close any unclosed braces
            while brace_stack:
                closing = '}' if brace_stack.pop() == '{' else ']'
                result.append(closing)
            
            reconstructed = ''.join(result)
            
            # Validate JSON
            json.loads(reconstructed)
            return reconstructed
            
        except (json.JSONDecodeError, IndexError):
            # Fall back to simple reconstruction
            return ' '.join(compressed_tokens)
    
    def _validate_compression_quality(self, original: str, compressed: str, context: Dict[str, Any]) -> float:
        """Validate that compressed content maintains sufficient quality."""
        # Quick cache check
        cache_key = hashlib.md5(f"{original}{compressed}".encode()).hexdigest()[:16]
        if cache_key in self._quality_cache:
            return self._quality_cache[cache_key]
        
        # Quality metrics
        scores = []
        
        # 1. Structural preservation (for JSON)
        if self._is_json(original):
            structural_score = self._validate_json_structure(original, compressed)
            scores.append(structural_score * 0.4)  # 40% weight
        
        # 2. Key information preservation
        key_info_score = self._validate_key_information(original, compressed, context)
        scores.append(key_info_score * 0.3)  # 30% weight
        
        # 3. Semantic coherence
        coherence_score = self._validate_semantic_coherence(original, compressed)
        scores.append(coherence_score * 0.3)  # 30% weight
        
        final_score = sum(scores)
        self._quality_cache[cache_key] = final_score
        return final_score
    
    def _validate_json_structure(self, original: str, compressed: str) -> float:
        """Validate JSON structure preservation."""
        try:
            orig_parsed = json.loads(original)
            comp_parsed = json.loads(compressed)
            
            # Check key preservation
            orig_keys = self._extract_all_keys(orig_parsed)
            comp_keys = self._extract_all_keys(comp_parsed)
            
            key_preservation = len(comp_keys & orig_keys) / max(len(orig_keys), 1)
            return key_preservation
            
        except json.JSONDecodeError:
            return 0.5  # Medium score if not valid JSON
    
    def _extract_all_keys(self, obj: Any, keys: set = None) -> set:
        """Extract all keys from nested JSON object."""
        if keys is None:
            keys = set()
        
        if isinstance(obj, dict):
            keys.update(obj.keys())
            for value in obj.values():
                self._extract_all_keys(value, keys)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_all_keys(item, keys)
        
        return keys
    
    def _validate_key_information(self, original: str, compressed: str, context: Dict[str, Any]) -> float:
        """Validate preservation of key information."""
        # Extract important terms from context and MCP keywords
        important_terms = set()
        
        # Add context terms
        for key, value in context.items():
            important_terms.add(key.lower())
            if isinstance(value, str):
                important_terms.update(re.findall(r'\w+', value.lower()))
        
        # Add MCP keywords
        important_terms.update(self.mcp_keywords)
        
        # Count preservation of important terms
        orig_terms = set(re.findall(r'\w+', original.lower()))
        comp_terms = set(re.findall(r'\w+', compressed.lower()))
        
        important_orig = orig_terms & important_terms
        important_comp = comp_terms & important_terms
        
        if not important_orig:
            return 1.0  # No important terms to preserve
        
        return len(important_comp) / len(important_orig)
    
    def _validate_semantic_coherence(self, original: str, compressed: str) -> float:
        """Validate semantic coherence using simple heuristics."""
        # Check word order preservation
        orig_words = re.findall(r'\w+', original.lower())
        comp_words = re.findall(r'\w+', compressed.lower())
        
        if not orig_words or not comp_words:
            return 0.5
        
        # Calculate longest common subsequence ratio
        lcs_length = self._longest_common_subsequence(orig_words, comp_words)
        coherence_score = lcs_length / max(len(orig_words), 1)
        
        return min(coherence_score * 2, 1.0)  # Boost and cap at 1.0
    
    def _longest_common_subsequence(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate longest common subsequence length."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def _update_learning_data(self, tokens: List[str], importance_scores: Dict[str, float]):
        """Update learning data for future compressions."""
        self._total_documents += 1
        
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self._token_frequencies[token] = self._token_frequencies.get(token, 0) + 1
            self._document_frequencies[token] = self._document_frequencies.get(token, 0) + 1
    
    def _is_json(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content.strip())
            return True
        except json.JSONDecodeError:
            return False
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics and learning data."""
        return {
            'total_documents_processed': self._total_documents,
            'vocabulary_size': len(self._token_frequencies),
            'most_frequent_tokens': sorted(
                self._token_frequencies.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20],
            'cache_size': len(self._quality_cache),
            'config': self.config.__dict__
        }