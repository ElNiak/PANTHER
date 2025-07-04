"""Compression manager for coordinating different compression strategies.

Integrates LLMLingua and semantic compression with intelligent strategy selection
based on content type, size, and quality requirements.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
import asyncio
from enum import Enum

from .llmlingua_compressor import LLMLinguaCompressor, CompressionResult, CompressionConfig
from .semantic_compressor import SemanticCompressor, SemanticCompressionResult

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Available compression strategies."""
    LLMLINGUA = "llmlingua"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    ADAPTIVE = "adaptive"
    NONE = "none"


@dataclass
class CompressionDecision:
    """Decision about which compression strategy to use."""
    strategy: CompressionStrategy
    confidence: float
    reasoning: str
    estimated_reduction: float
    quality_expectation: float


@dataclass
class CompressionPerformance:
    """Performance metrics for compression operations."""
    strategy_used: CompressionStrategy
    compression_time_ms: float
    token_reduction_ratio: float
    quality_score: float
    content_type: str
    content_size_bytes: int
    success: bool
    error_message: Optional[str] = None


class CompressionManager:
    """Manages compression strategies for inter-tool communication.
    
    Provides intelligent compression strategy selection based on:
    1. Content type and structure
    2. Size and complexity requirements  
    3. Quality thresholds
    4. Historical performance data
    5. Real-time adaptation
    """
    
    def __init__(self,
                 default_strategy: CompressionStrategy = CompressionStrategy.ADAPTIVE,
                 min_size_threshold: int = 500,  # Only compress if larger than 500 bytes
                 enable_learning: bool = True):
        self.default_strategy = default_strategy
        self.min_size_threshold = min_size_threshold
        self.enable_learning = enable_learning
        
        # Initialize compression engines
        self.llmlingua_compressor = LLMLinguaCompressor(
            CompressionConfig(
                target_compression_ratio=0.5,
                quality_threshold=0.85
            )
        )
        
        self.semantic_compressor = SemanticCompressor(
            target_reduction=0.35,
            min_semantic_preservation=0.80
        )
        
        # Performance tracking
        self.performance_history: List[CompressionPerformance] = []
        self.strategy_performance: Dict[CompressionStrategy, Dict[str, float]] = {
            strategy: {'avg_quality': 0.0, 'avg_reduction': 0.0, 'success_rate': 0.0}
            for strategy in CompressionStrategy
        }
        
        # Content type detection patterns
        self.content_type_patterns = {
            'json': lambda x: self._is_json(x),
            'task_metadata': lambda x: any(keyword in x.lower() for keyword in 
                                         ['task_id', 'project_name', 'status', 'priority']),
            'hierarchical_data': lambda x: any(keyword in x.lower() for keyword in 
                                             ['parent_task_id', 'subtask', 'hierarchical']),
            'error_logs': lambda x: any(keyword in x.lower() for keyword in 
                                      ['error', 'exception', 'traceback', 'failed']),
            'description_text': lambda x: len(x.split()) > 20 and 'description' in x.lower(),
            'code_snippet': lambda x: any(keyword in x for keyword in ['def ', 'class ', 'import ', 'function'])
        }
    
    async def compress(self, 
                      content: str, 
                      context: Dict[str, Any] = None, 
                      strategy: Optional[CompressionStrategy] = None,
                      min_quality: float = 0.8) -> Union[CompressionResult, SemanticCompressionResult]:
        """Compress content using optimal strategy.
        
        Args:
            content: Content to compress
            context: Additional context for compression decisions
            strategy: Force specific strategy (overrides adaptive selection)
            min_quality: Minimum quality threshold
            
        Returns:
            Compression result with compressed content and metrics
        """
        start_time = datetime.now()
        context = context or {}
        
        # Check size threshold
        if len(content.encode()) < self.min_size_threshold:
            logger.debug(f"Content size {len(content.encode())} below threshold {self.min_size_threshold}")
            return self._create_no_compression_result(content, "below_size_threshold")
        
        # Determine strategy
        if strategy is None:
            decision = await self._select_optimal_strategy(content, context, min_quality)
            strategy = decision.strategy
        else:
            decision = CompressionDecision(
                strategy=strategy,
                confidence=1.0,
                reasoning="user_specified",
                estimated_reduction=0.3,
                quality_expectation=0.85
            )
        
        # Apply compression
        try:
            if strategy == CompressionStrategy.LLMLINGUA:
                result = await self._apply_llmlingua_compression(content, context, min_quality)
            elif strategy == CompressionStrategy.SEMANTIC:
                result = await self._apply_semantic_compression(content, context, min_quality)
            elif strategy == CompressionStrategy.HYBRID:
                result = await self._apply_hybrid_compression(content, context, min_quality)
            elif strategy == CompressionStrategy.ADAPTIVE:
                result = await self._apply_adaptive_compression(content, context, min_quality)
            else:  # NONE
                result = self._create_no_compression_result(content, "strategy_none")
            
            # Record performance
            compression_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._record_performance(strategy, result, content, compression_time, True)
            
            return result
            
        except Exception as e:
            logger.error(f"Compression failed with strategy {strategy}: {str(e)}")
            compression_time = (datetime.now() - start_time).total_seconds() * 1000
            await self._record_performance(strategy, None, content, compression_time, False, str(e))
            
            # Return original content on failure
            return self._create_no_compression_result(content, f"error: {str(e)}")
    
    async def _select_optimal_strategy(self, 
                                     content: str, 
                                     context: Dict[str, Any], 
                                     min_quality: float) -> CompressionDecision:
        """Select optimal compression strategy based on content analysis."""
        content_type = self._detect_content_type(content)
        content_size = len(content.encode())
        
        # Analyze content characteristics
        is_structured = self._is_json(content) or any(char in content for char in ['{', '[', ':'])
        has_repetition = self._has_significant_repetition(content)
        complexity_score = self._calculate_content_complexity(content)
        
        # Get historical performance for content type
        historical_performance = self._get_historical_performance(content_type)
        
        # Decision logic
        decisions = []
        
        # LLMLingua decision
        llmlingua_score = 0.7  # Base score
        if content_size > 2000:  # Good for larger content
            llmlingua_score += 0.1
        if has_repetition:  # Excels at repetitive content
            llmlingua_score += 0.15
        if historical_performance.get(CompressionStrategy.LLMLINGUA, {}).get('success_rate', 0) > 0.8:
            llmlingua_score += 0.1
        
        decisions.append(CompressionDecision(
            strategy=CompressionStrategy.LLMLINGUA,
            confidence=llmlingua_score,
            reasoning=f"Content type: {content_type}, size: {content_size}, repetition: {has_repetition}",
            estimated_reduction=0.5,
            quality_expectation=0.9
        ))
        
        # Semantic decision
        semantic_score = 0.6  # Base score  
        if is_structured:  # Good for structured content
            semantic_score += 0.15
        if content_type in ['task_metadata', 'hierarchical_data']:  # Excellent for task data
            semantic_score += 0.2
        if complexity_score < 0.5:  # Better for simpler content
            semantic_score += 0.1
        if historical_performance.get(CompressionStrategy.SEMANTIC, {}).get('avg_quality', 0) > min_quality:
            semantic_score += 0.1
        
        decisions.append(CompressionDecision(
            strategy=CompressionStrategy.SEMANTIC,
            confidence=semantic_score,
            reasoning=f"Structured: {is_structured}, type: {content_type}, complexity: {complexity_score:.2f}",
            estimated_reduction=0.35,
            quality_expectation=0.85
        ))
        
        # Hybrid decision
        hybrid_score = 0.5  # Base score
        if content_size > 1500 and is_structured:  # Good for large structured content
            hybrid_score += 0.2
        if content_type == 'description_text' and has_repetition:  # Good for verbose descriptions
            hybrid_score += 0.15
        if min_quality > 0.85:  # Conservative choice for high quality requirements
            hybrid_score += 0.1
        
        decisions.append(CompressionDecision(
            strategy=CompressionStrategy.HYBRID,
            confidence=hybrid_score,
            reasoning=f"Large structured content with quality requirement {min_quality}",
            estimated_reduction=0.4,
            quality_expectation=0.88
        ))
        
        # Select best decision
        best_decision = max(decisions, key=lambda d: d.confidence)
        
        # Override if confidence is too low
        if best_decision.confidence < 0.7:
            best_decision = CompressionDecision(
                strategy=CompressionStrategy.NONE,
                confidence=0.9,
                reasoning="Low confidence in compression strategies",
                estimated_reduction=0.0,
                quality_expectation=1.0
            )
        
        logger.info(f"Selected strategy: {best_decision.strategy} (confidence: {best_decision.confidence:.3f})")
        return best_decision
    
    async def _apply_llmlingua_compression(self, 
                                         content: str, 
                                         context: Dict[str, Any], 
                                         min_quality: float) -> CompressionResult:
        """Apply LLMLingua compression."""
        # Adjust config based on quality requirement
        config = CompressionConfig(
            target_compression_ratio=0.5,
            quality_threshold=min_quality,
            preserve_mcp_metadata=True
        )
        
        compressor = LLMLinguaCompressor(config)
        result = compressor.compress_tool_communication(content, context)
        
        return result
    
    async def _apply_semantic_compression(self, 
                                        content: str, 
                                        context: Dict[str, Any], 
                                        min_quality: float) -> SemanticCompressionResult:
        """Apply semantic compression."""
        compressor = SemanticCompressor(
            target_reduction=0.35,
            min_semantic_preservation=min_quality
        )
        
        result = compressor.compress_semantically(content, context)
        return result
    
    async def _apply_hybrid_compression(self, 
                                      content: str, 
                                      context: Dict[str, Any], 
                                      min_quality: float) -> CompressionResult:
        """Apply hybrid compression using both strategies."""
        # First apply semantic compression for structure preservation
        semantic_result = await self._apply_semantic_compression(content, context, min_quality)
        
        # Then apply LLMLingua for token reduction
        if semantic_result.semantic_preservation_score >= min_quality:
            llmlingua_result = await self._apply_llmlingua_compression(
                semantic_result.compressed_content, 
                context, 
                min_quality * 0.9  # Slightly lower threshold for second pass
            )
            
            # Combine results
            combined_result = CompressionResult(
                original_content=content,
                compressed_content=llmlingua_result.compressed_content,
                compression_ratio=len(llmlingua_result.compressed_content.encode()) / len(content.encode()),
                preserved_tokens=llmlingua_result.preserved_tokens,
                original_tokens=len(content.split()),
                metadata={
                    'strategy': 'hybrid',
                    'semantic_score': semantic_result.semantic_preservation_score,
                    'llmlingua_quality': llmlingua_result.metadata.get('quality_score', 0),
                    'two_pass_compression': True,
                    'semantic_reduction': semantic_result.token_reduction_ratio,
                    'llmlingua_reduction': llmlingua_result.compression_ratio,
                    'combined_reduction': 1.0 - (len(llmlingua_result.compressed_content.encode()) / len(content.encode()))
                }
            )
            
            return combined_result
        else:
            # Semantic compression failed, fallback to LLMLingua only
            return await self._apply_llmlingua_compression(content, context, min_quality)
    
    async def _apply_adaptive_compression(self, 
                                        content: str, 
                                        context: Dict[str, Any], 
                                        min_quality: float) -> Union[CompressionResult, SemanticCompressionResult]:
        """Apply adaptive compression that selects strategy based on real-time analysis."""
        # Run quick analysis on content subset
        sample_size = min(len(content), 500)
        content_sample = content[:sample_size]
        
        # Test both strategies on sample
        tasks = [
            self._test_compression_quality(content_sample, context, CompressionStrategy.LLMLINGUA),
            self._test_compression_quality(content_sample, context, CompressionStrategy.SEMANTIC)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results and pick best
        best_strategy = CompressionStrategy.SEMANTIC  # Default
        best_score = 0.0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            
            strategy = [CompressionStrategy.LLMLINGUA, CompressionStrategy.SEMANTIC][i]
            quality_score = result.get('quality_score', 0.0)
            reduction = result.get('reduction', 0.0)
            
            # Combined score: quality * reduction
            combined_score = quality_score * reduction
            
            if combined_score > best_score:
                best_score = combined_score
                best_strategy = strategy
        
        # Apply selected strategy to full content
        if best_strategy == CompressionStrategy.LLMLINGUA:
            return await self._apply_llmlingua_compression(content, context, min_quality)
        else:
            return await self._apply_semantic_compression(content, context, min_quality)
    
    async def _test_compression_quality(self, 
                                      content_sample: str, 
                                      context: Dict[str, Any], 
                                      strategy: CompressionStrategy) -> Dict[str, float]:
        """Test compression quality on a content sample."""
        try:
            if strategy == CompressionStrategy.LLMLINGUA:
                result = self.llmlingua_compressor.compress_tool_communication(content_sample, context)
                return {
                    'quality_score': result.metadata.get('quality_score', 0.0),
                    'reduction': 1.0 - result.compression_ratio
                }
            elif strategy == CompressionStrategy.SEMANTIC:
                result = self.semantic_compressor.compress_semantically(content_sample, context)
                return {
                    'quality_score': result.semantic_preservation_score,
                    'reduction': result.token_reduction_ratio
                }
        except Exception as e:
            logger.warning(f"Test compression failed for {strategy}: {e}")
            return {'quality_score': 0.0, 'reduction': 0.0}
    
    def _create_no_compression_result(self, content: str, reason: str) -> CompressionResult:
        """Create a result for no compression applied."""
        return CompressionResult(
            original_content=content,
            compressed_content=content,
            compression_ratio=1.0,
            preserved_tokens=len(content.split()),
            original_tokens=len(content.split()),
            metadata={
                'strategy': 'none',
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def _detect_content_type(self, content: str) -> str:
        """Detect the type of content for strategy selection."""
        for content_type, detector in self.content_type_patterns.items():
            if detector(content):
                return content_type
        return 'generic'
    
    def _is_json(self, content: str) -> bool:
        """Check if content is valid JSON."""
        try:
            json.loads(content.strip())
            return True
        except json.JSONDecodeError:
            return False
    
    def _has_significant_repetition(self, content: str) -> bool:
        """Check if content has significant repetition."""
        words = content.lower().split()
        if len(words) < 10:
            return False
        
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Check if any word appears more than 20% of the time
        max_freq = max(word_freq.values())
        return max_freq / len(words) > 0.2
    
    def _calculate_content_complexity(self, content: str) -> float:
        """Calculate content complexity score (0-1, higher = more complex)."""
        # Simple complexity metrics
        unique_words = len(set(content.lower().split()))
        total_words = len(content.split())
        
        if total_words == 0:
            return 0.0
        
        # Vocabulary diversity
        vocab_diversity = unique_words / total_words
        
        # Sentence length variation
        sentences = content.split('.')
        if len(sentences) > 1:
            sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
            if sentence_lengths:
                length_variance = max(sentence_lengths) - min(sentence_lengths)
                length_complexity = min(length_variance / 20, 1.0)  # Normalize
            else:
                length_complexity = 0.0
        else:
            length_complexity = 0.0
        
        # Combine metrics
        complexity = (vocab_diversity * 0.7) + (length_complexity * 0.3)
        return min(complexity, 1.0)
    
    def _get_historical_performance(self, content_type: str) -> Dict[CompressionStrategy, Dict[str, float]]:
        """Get historical performance data for content type."""
        # Filter performance history by content type
        type_performance = [p for p in self.performance_history 
                          if p.content_type == content_type]
        
        if not type_performance:
            return {}
        
        # Calculate metrics by strategy
        performance = {}
        for strategy in CompressionStrategy:
            strategy_data = [p for p in type_performance if p.strategy_used == strategy]
            if strategy_data:
                performance[strategy] = {
                    'avg_quality': sum(p.quality_score for p in strategy_data) / len(strategy_data),
                    'avg_reduction': sum(p.token_reduction_ratio for p in strategy_data) / len(strategy_data),
                    'success_rate': sum(p.success for p in strategy_data) / len(strategy_data)
                }
        
        return performance
    
    async def _record_performance(self, 
                                strategy: CompressionStrategy, 
                                result: Optional[Union[CompressionResult, SemanticCompressionResult]], 
                                original_content: str,
                                compression_time_ms: float, 
                                success: bool, 
                                error_message: Optional[str] = None):
        """Record compression performance for learning."""
        if not self.enable_learning:
            return
        
        content_type = self._detect_content_type(original_content)
        
        if result:
            if isinstance(result, CompressionResult):
                quality_score = result.metadata.get('quality_score', 0.0)
                reduction_ratio = 1.0 - result.compression_ratio
            else:  # SemanticCompressionResult
                quality_score = result.semantic_preservation_score
                reduction_ratio = result.token_reduction_ratio
        else:
            quality_score = 0.0
            reduction_ratio = 0.0
        
        performance = CompressionPerformance(
            strategy_used=strategy,
            compression_time_ms=compression_time_ms,
            token_reduction_ratio=reduction_ratio,
            quality_score=quality_score,
            content_type=content_type,
            content_size_bytes=len(original_content.encode()),
            success=success,
            error_message=error_message
        )
        
        self.performance_history.append(performance)
        
        # Keep only last 1000 entries to prevent memory growth
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
        
        # Update strategy performance summary
        self._update_strategy_performance()
    
    def _update_strategy_performance(self):
        """Update strategy performance summaries."""
        for strategy in CompressionStrategy:
            strategy_data = [p for p in self.performance_history if p.strategy_used == strategy]
            
            if strategy_data:
                self.strategy_performance[strategy] = {
                    'avg_quality': sum(p.quality_score for p in strategy_data) / len(strategy_data),
                    'avg_reduction': sum(p.token_reduction_ratio for p in strategy_data) / len(strategy_data),
                    'success_rate': sum(p.success for p in strategy_data) / len(strategy_data)
                }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get compression performance statistics."""
        return {
            'total_compressions': len(self.performance_history),
            'strategy_performance': self.strategy_performance,
            'content_type_distribution': self._get_content_type_distribution(),
            'avg_compression_time_ms': sum(p.compression_time_ms for p in self.performance_history) / max(len(self.performance_history), 1),
            'overall_success_rate': sum(p.success for p in self.performance_history) / max(len(self.performance_history), 1),
            'settings': {
                'default_strategy': self.default_strategy.value,
                'min_size_threshold': self.min_size_threshold,
                'enable_learning': self.enable_learning
            }
        }
    
    def _get_content_type_distribution(self) -> Dict[str, int]:
        """Get distribution of content types processed."""
        distribution = {}
        for perf in self.performance_history:
            distribution[perf.content_type] = distribution.get(perf.content_type, 0) + 1
        return distribution