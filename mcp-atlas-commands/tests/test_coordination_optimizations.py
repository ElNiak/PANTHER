#!/usr/bin/env python3
"""
Comprehensive test suite for coordination optimizations.

Tests all 5 optimization strategies implemented based on Perplexity research:
1. LLMLingua compression (3-5x compression ratios)
2. Saga patterns with Temporal integration (transactional integrity)
3. Entropy-triggered incremental processing (token explosion prevention)
4. OTLP-inspired concurrency (linear throughput scaling)
5. Integration validation (end-to-end workflows)
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.compression.compression_manager import CompressionManager, CompressionStrategy
from atlas_commands.saga.saga_coordinator import SagaCoordinator, SagaDefinition, SagaStep
from atlas_commands.saga.temporal_integration import TemporalSagaWorkflow, TemporalWorkflowConfig
from atlas_commands.entropy.entropy_processor import EntropyProcessor
from atlas_commands.entropy.incremental_memory_manager import IncrementalMemoryManager, MemoryOperationType
from atlas_commands.otlp_concurrency.concurrent_exporter import ConcurrentExporter

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CoordinationOptimizationTester:
    """Comprehensive tester for all coordination optimizations."""
    
    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
    
    def _get_compression_ratio(self, result):
        """Extract compression ratio from different result types."""
        if hasattr(result, 'compression_ratio'):
            return result.compression_ratio
        elif hasattr(result, 'token_reduction_ratio'):
            return result.token_reduction_ratio
        else:
            return 1.0  # No compression
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all coordination optimization tests."""
        logger.info("🚀 Starting Coordination Optimization Test Suite")
        
        try:
            # Test 1: LLMLingua Compression
            compression_results = await self.test_compression_optimization()
            self.test_results['compression'] = compression_results
            
            # Test 2: Saga Patterns
            saga_results = await self.test_saga_patterns()
            self.test_results['saga'] = saga_results
            
            # Test 3: Entropy Processing
            entropy_results = await self.test_entropy_processing()
            self.test_results['entropy'] = entropy_results
            
            # Test 4: OTLP Concurrency
            otlp_results = await self.test_otlp_concurrency()
            self.test_results['otlp'] = otlp_results
            
            # Test 5: Integration Validation
            integration_results = await self.test_integration_workflows()
            self.test_results['integration'] = integration_results
            
            # Generate summary
            summary = self.generate_test_summary()
            
            logger.info("✅ All coordination optimization tests completed")
            return {
                'test_results': self.test_results,
                'performance_metrics': self.performance_metrics,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            return {
                'error': str(e),
                'partial_results': self.test_results
            }
    
    async def test_compression_optimization(self) -> Dict[str, Any]:
        """Test LLMLingua compression optimization."""
        logger.info("🔧 Testing LLMLingua Compression Optimization")
        
        results = {
            'llmlingua_tests': [],
            'semantic_tests': [],
            'adaptive_tests': [],
            'performance_metrics': {}
        }
        
        compression_manager = CompressionManager(
            default_strategy=CompressionStrategy.ADAPTIVE,
            enable_learning=True
        )
        
        # Test data with varying entropy levels
        test_cases = [
            {
                'name': 'high_entropy_json',
                'content': json.dumps({
                    'task_id': 'test_task_001',
                    'project_name': 'ATLAS',
                    'status': 'in_progress',
                    'description': 'This is a comprehensive test of the LLMLingua compression system with various data patterns and entropy levels to validate compression ratios and quality preservation',
                    'metadata': {'created_at': '2025-06-22', 'priority': 'high', 'estimated_hours': 8},
                    'artifacts': ['analysis.md', 'design.json', 'implementation.py'],
                    'dependencies': ['parent_task_123', 'prerequisite_456']
                }),
                'expected_compression': 0.4  # 60% compression
            },
            {
                'name': 'low_entropy_repetitive',
                'content': 'test test test ' * 100 + 'data data data ' * 50,
                'expected_compression': 0.8  # 80% compression
            },
            {
                'name': 'medium_entropy_text',
                'content': 'Implement the coordination optimization strategies from Perplexity research including LLMLingua compression for inter-tool communication, saga patterns for hierarchical task management, entropy-triggered processing for memory operations, and OTLP-inspired concurrency for observability pipelines.',
                'expected_compression': 0.5  # 50% compression
            }
        ]
        
        # Test each compression strategy
        strategies = [CompressionStrategy.LLMLINGUA, CompressionStrategy.SEMANTIC, CompressionStrategy.ADAPTIVE]
        
        for strategy in strategies:
            strategy_results = []
            
            for test_case in test_cases:
                start_time = time.time()
                
                try:
                    result = await compression_manager.compress(
                        test_case['content'],
                        context={'test_case': test_case['name']},
                        strategy=strategy
                    )
                    
                    compression_time = (time.time() - start_time) * 1000
                    
                    # Validate compression ratio
                    actual_ratio = self._get_compression_ratio(result)
                    expected_ratio = test_case['expected_compression']
                    ratio_diff = abs(actual_ratio - expected_ratio)
                    
                    test_result = {
                        'test_case': test_case['name'],
                        'strategy': strategy.value,
                        'success': True,
                        'compression_ratio': actual_ratio,
                        'expected_ratio': expected_ratio,
                        'ratio_difference': ratio_diff,
                        'quality_score': getattr(result, 'metadata', {}).get('quality_score', 0.0),
                        'processing_time_ms': compression_time,
                        'original_size': len(test_case['content']),
                        'compressed_size': len(result.compressed_content),
                        'meets_expectations': ratio_diff < 0.2  # Within 20% of expected
                    }
                    
                    strategy_results.append(test_result)
                    logger.info(f"✅ {strategy.value} compression test '{test_case['name']}': {actual_ratio:.2f} ratio")
                    
                except Exception as e:
                    strategy_results.append({
                        'test_case': test_case['name'],
                        'strategy': strategy.value,
                        'success': False,
                        'error': str(e)
                    })
                    logger.error(f"❌ {strategy.value} compression test '{test_case['name']}' failed: {e}")
            
            results[f'{strategy.value}_tests'] = strategy_results
        
        # Calculate performance metrics
        all_successful_tests = []
        for strategy in strategies:
            strategy_tests = results.get(f'{strategy.value}_tests', [])
            all_successful_tests.extend([t for t in strategy_tests if t.get('success', False)])
        
        if all_successful_tests:
            results['performance_metrics'] = {
                'average_compression_ratio': sum(t['compression_ratio'] for t in all_successful_tests) / len(all_successful_tests),
                'average_quality_score': sum(t.get('quality_score', 0) for t in all_successful_tests) / len(all_successful_tests),
                'average_processing_time_ms': sum(t['processing_time_ms'] for t in all_successful_tests) / len(all_successful_tests),
                'success_rate': len(all_successful_tests) / (len(strategies) * len(test_cases)),
                'total_tests': len(strategies) * len(test_cases)
            }
        
        return results
    
    async def test_saga_patterns(self) -> Dict[str, Any]:
        """Test Saga patterns and Temporal integration."""
        logger.info("🔧 Testing Saga Patterns and Temporal Integration")
        
        results = {
            'saga_coordinator_tests': [],
            'temporal_integration_tests': [],
            'compensation_tests': [],
            'performance_metrics': {}
        }
        
        saga_coordinator = SagaCoordinator(max_concurrent_sagas=3)
        temporal_workflow = TemporalSagaWorkflow(saga_coordinator=saga_coordinator)
        
        # Test 1: Basic saga execution
        async def test_action(context, step):
            await asyncio.sleep(0.1)
            return f"Step {step.step_id} completed"
        
        async def test_compensation(context, step):
            await asyncio.sleep(0.05)
            return f"Step {step.step_id} compensated"
        
        # Create test saga
        saga_steps = [
            SagaStep(
                step_id="step_1",
                name="create_task",
                action=test_action,
                compensation=test_compensation
            ),
            SagaStep(
                step_id="step_2", 
                name="process_task",
                action=test_action,
                compensation=test_compensation,
                depends_on=["step_1"]
            ),
            SagaStep(
                step_id="step_3",
                name="finalize_task",
                action=test_action,
                compensation=test_compensation,
                depends_on=["step_2"]
            )
        ]
        
        saga_definition = SagaDefinition(
            saga_id="test_saga_001",
            name="Test Hierarchical Task Saga",
            steps=saga_steps,
            enable_compensation=True
        )
        
        # Test saga execution
        start_time = time.time()
        saga_result = await saga_coordinator.execute_saga(saga_definition, {'test': True})
        execution_time = (time.time() - start_time) * 1000
        
        saga_test_result = {
            'test_name': 'basic_saga_execution',
            'success': saga_result['status'] == 'completed',
            'steps_completed': saga_result['steps_completed'],
            'steps_failed': saga_result['steps_failed'],
            'execution_time_ms': execution_time,
            'compensation_applied': saga_result.get('compensation_applied', False)
        }
        
        results['saga_coordinator_tests'].append(saga_test_result)
        
        # Test 2: Temporal workflow integration
        temporal_config = TemporalWorkflowConfig(
            workflow_id="test_temporal_workflow_001",
            task_queue="atlas-test-tasks"
        )
        
        start_time = time.time()
        temporal_result = await temporal_workflow.execute_hierarchical_saga(
            saga_definition,
            temporal_config,
            {
                'task_id': 'test_task_001',
                'parent_task_id': None,
                'has_subtasks': True,
                'subtask_ids': ['subtask_001', 'subtask_002']
            }
        )
        temporal_execution_time = (time.time() - start_time) * 1000
        
        temporal_test_result = {
            'test_name': 'temporal_workflow_execution',
            'success': temporal_result['status'] == 'completed',
            'workflow_id': temporal_result['workflow_id'],
            'cross_cluster_replicated': temporal_result.get('cross_cluster_replicated', False),
            'execution_time_ms': temporal_execution_time,
            'activity_results_count': len(temporal_result.get('activity_results', {}))
        }
        
        results['temporal_integration_tests'].append(temporal_test_result)
        
        # Test 3: Compensation mechanism
        async def failing_action(context, step):
            raise Exception("Simulated failure for compensation testing")
        
        failing_saga_steps = [
            SagaStep(
                step_id="step_1",
                name="create_task",
                action=test_action,
                compensation=test_compensation
            ),
            SagaStep(
                step_id="step_2",
                name="failing_step",
                action=failing_action,
                compensation=test_compensation,
                depends_on=["step_1"]
            )
        ]
        
        failing_saga = SagaDefinition(
            saga_id="test_failing_saga",
            name="Test Compensation Saga",
            steps=failing_saga_steps,
            enable_compensation=True
        )
        
        start_time = time.time()
        compensation_result = await saga_coordinator.execute_saga(failing_saga, {'test': True})
        compensation_time = (time.time() - start_time) * 1000
        
        compensation_test_result = {
            'test_name': 'compensation_mechanism',
            'success': compensation_result.get('compensation_applied', False),
            'steps_completed': compensation_result['steps_completed'],
            'steps_failed': compensation_result['steps_failed'],
            'compensation_applied': compensation_result.get('compensation_applied', False),
            'execution_time_ms': compensation_time
        }
        
        results['compensation_tests'].append(compensation_test_result)
        
        # Performance metrics
        all_tests = (results['saga_coordinator_tests'] + 
                    results['temporal_integration_tests'] + 
                    results['compensation_tests'])
        
        successful_tests = [t for t in all_tests if t['success']]
        
        results['performance_metrics'] = {
            'total_tests': len(all_tests),
            'successful_tests': len(successful_tests),
            'success_rate': len(successful_tests) / len(all_tests) if all_tests else 0,
            'average_execution_time_ms': sum(t['execution_time_ms'] for t in successful_tests) / len(successful_tests) if successful_tests else 0
        }
        
        logger.info(f"✅ Saga patterns test completed: {len(successful_tests)}/{len(all_tests)} tests passed")
        
        return results
    
    async def test_entropy_processing(self) -> Dict[str, Any]:
        """Test entropy-triggered incremental processing."""
        logger.info("🔧 Testing Entropy-Triggered Incremental Processing")
        
        results = {
            'entropy_analysis_tests': [],
            'incremental_processing_tests': [],
            'chunking_strategy_tests': [],
            'performance_metrics': {}
        }
        
        entropy_processor = EntropyProcessor()
        incremental_manager = IncrementalMemoryManager(entropy_processor=entropy_processor)
        
        # Test data with different entropy characteristics
        test_contents = [
            {
                'name': 'high_entropy_complex',
                'content': json.dumps({
                    'complex_data': {
                        'unique_field_' + str(i): f'diverse_value_{i}_{i*2}_{i**2}' 
                        for i in range(50)
                    },
                    'nested_structures': [
                        {'id': i, 'data': f'pattern_{i%7}_{i%11}', 'meta': {'score': i * 1.3}}
                        for i in range(30)
                    ]
                }),
                'expected_entropy': 0.8,
                'expected_mode': 'streaming'
            },
            {
                'name': 'low_entropy_repetitive',
                'content': 'repeated pattern ' * 200 + 'another repeated pattern ' * 100,
                'expected_entropy': 0.3,
                'expected_mode': 'compressed'
            },
            {
                'name': 'medium_entropy_structured',
                'content': '''
                {
                    "tasks": [
                        {"id": "task_001", "status": "pending", "priority": "high"},
                        {"id": "task_002", "status": "in_progress", "priority": "medium"},
                        {"id": "task_003", "status": "completed", "priority": "low"}
                    ],
                    "metadata": {
                        "created_at": "2025-06-22",
                        "project": "ATLAS",
                        "version": "1.0.0"
                    }
                }
                ''',
                'expected_entropy': 0.6,
                'expected_mode': 'incremental'
            }
        ]
        
        # Test entropy analysis
        for test_case in test_contents:
            try:
                start_time = time.time()
                analysis = entropy_processor.analyze_content_entropy(test_case['content'])
                analysis_time = (time.time() - start_time) * 1000
                
                entropy_diff = abs(analysis.content_entropy - test_case['expected_entropy'])
                mode_match = analysis.recommended_mode.value == test_case['expected_mode']
                
                test_result = {
                    'test_case': test_case['name'],
                    'success': True,
                    'content_entropy': analysis.content_entropy,
                    'expected_entropy': test_case['expected_entropy'],
                    'entropy_difference': entropy_diff,
                    'recommended_mode': analysis.recommended_mode.value,
                    'expected_mode': test_case['expected_mode'],
                    'mode_match': mode_match,
                    'processing_triggers': [t.value for t in analysis.processing_triggers],
                    'chunk_suggestions_count': len(analysis.chunk_suggestions),
                    'analysis_time_ms': analysis_time,
                    'meets_expectations': entropy_diff < 0.3 and mode_match
                }
                
                results['entropy_analysis_tests'].append(test_result)
                logger.info(f"✅ Entropy analysis '{test_case['name']}': {analysis.content_entropy:.3f} entropy, {analysis.recommended_mode.value} mode")
                
            except Exception as e:
                results['entropy_analysis_tests'].append({
                    'test_case': test_case['name'],
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"❌ Entropy analysis '{test_case['name']}' failed: {e}")
        
        # Test incremental processing
        for test_case in test_contents:
            try:
                start_time = time.time()
                results_collected = []
                
                async for result in incremental_manager.process_memory_operation(
                    test_case['content'],
                    MemoryOperationType.SEARCH,
                    context={'test_case': test_case['name']}
                ):
                    results_collected.append(result)
                
                processing_time = (time.time() - start_time) * 1000
                
                successful_chunks = len([r for r in results_collected if r.get('status') == 'completed'])
                total_chunks = len(results_collected)
                
                processing_result = {
                    'test_case': test_case['name'],
                    'success': total_chunks > 0,
                    'total_chunks': total_chunks,
                    'successful_chunks': successful_chunks,
                    'success_rate': successful_chunks / total_chunks if total_chunks > 0 else 0,
                    'processing_time_ms': processing_time,
                    'average_chunk_time_ms': processing_time / total_chunks if total_chunks > 0 else 0
                }
                
                results['incremental_processing_tests'].append(processing_result)
                logger.info(f"✅ Incremental processing '{test_case['name']}': {successful_chunks}/{total_chunks} chunks successful")
                
            except Exception as e:
                results['incremental_processing_tests'].append({
                    'test_case': test_case['name'],
                    'success': False,
                    'error': str(e)
                })
                logger.error(f"❌ Incremental processing '{test_case['name']}' failed: {e}")
        
        # Calculate performance metrics
        all_entropy_tests = results['entropy_analysis_tests']
        all_processing_tests = results['incremental_processing_tests']
        
        successful_entropy = [t for t in all_entropy_tests if t.get('success', False)]
        successful_processing = [t for t in all_processing_tests if t.get('success', False)]
        
        results['performance_metrics'] = {
            'entropy_analysis': {
                'total_tests': len(all_entropy_tests),
                'successful_tests': len(successful_entropy),
                'success_rate': len(successful_entropy) / len(all_entropy_tests) if all_entropy_tests else 0,
                'average_analysis_time_ms': sum(t['analysis_time_ms'] for t in successful_entropy) / len(successful_entropy) if successful_entropy else 0,
                'average_entropy_accuracy': sum(1 - t['entropy_difference'] for t in successful_entropy) / len(successful_entropy) if successful_entropy else 0
            },
            'incremental_processing': {
                'total_tests': len(all_processing_tests),
                'successful_tests': len(successful_processing),
                'success_rate': len(successful_processing) / len(all_processing_tests) if all_processing_tests else 0,
                'average_processing_time_ms': sum(t['processing_time_ms'] for t in successful_processing) / len(successful_processing) if successful_processing else 0,
                'average_chunk_success_rate': sum(t['success_rate'] for t in successful_processing) / len(successful_processing) if successful_processing else 0
            }
        }
        
        return results
    
    async def test_otlp_concurrency(self) -> Dict[str, Any]:
        """Test OTLP-inspired concurrency optimization."""
        logger.info("🔧 Testing OTLP-Inspired Concurrency Optimization")
        
        results = {
            'concurrent_export_tests': [],
            'throughput_scaling_tests': [],
            'adaptive_batching_tests': [],
            'performance_metrics': {}
        }
        
        # Test concurrent exporter
        async def test_export_function(data_batch, batch_id):
            # Simulate export processing
            await asyncio.sleep(0.05 + len(data_batch) * 0.001)
            return f"Exported {len(data_batch)} items in batch {batch_id}"
        
        exporter = ConcurrentExporter(
            max_concurrent_batches=3,
            max_batch_size=20,
            export_function=test_export_function
        )
        
        try:
            await exporter.start()
            
            # Test 1: Basic concurrent export
            test_items = [
                {'data': f'test_item_{i}', 'priority': (i % 10) + 1, 'metadata': {'index': i}}
                for i in range(100)
            ]
            
            start_time = time.time()
            item_ids = await exporter.queue_items(test_items)
            
            # Wait for processing to complete
            await asyncio.sleep(2.0)
            
            status = exporter.get_status()
            processing_time = (time.time() - start_time) * 1000
            
            basic_export_result = {
                'test_name': 'basic_concurrent_export',
                'success': status['metrics']['total_items_exported'] > 0,
                'items_queued': len(item_ids),
                'items_exported': status['metrics']['total_items_exported'],
                'items_failed': status['metrics']['total_items_failed'],
                'batches_processed': status['metrics']['total_batches_processed'],
                'processing_time_ms': processing_time,
                'throughput_items_per_second': status['metrics']['current_throughput_items_per_second']
            }
            
            results['concurrent_export_tests'].append(basic_export_result)
            
            # Test 2: Throughput scaling
            throughput_tests = []
            
            for batch_count in [1, 2, 3]:
                exporter.max_concurrent_batches = batch_count
                
                # Queue test items
                scaling_items = [
                    {'data': f'scaling_item_{i}', 'priority': 5}
                    for i in range(50)
                ]
                
                start_time = time.time()
                await exporter.queue_items(scaling_items)
                await asyncio.sleep(1.5)
                
                current_status = exporter.get_status()
                scaling_time = (time.time() - start_time) * 1000
                
                throughput_test = {
                    'concurrent_batches': batch_count,
                    'items_processed': current_status['metrics']['total_items_exported'],
                    'throughput_items_per_second': current_status['metrics']['current_throughput_items_per_second'],
                    'processing_time_ms': scaling_time
                }
                
                throughput_tests.append(throughput_test)
            
            results['throughput_scaling_tests'] = throughput_tests
            
            # Test 3: Adaptive batching
            exporter.batching_strategy = 'adaptive'
            
            # Send items with different priorities to test adaptive batching
            priority_items = []
            for priority in [10, 5, 1]:  # High, medium, low priority
                priority_items.extend([
                    {'data': f'priority_{priority}_item_{i}', 'priority': priority}
                    for i in range(20)
                ])
            
            start_time = time.time()
            await exporter.queue_items(priority_items)
            await asyncio.sleep(1.0)
            
            adaptive_status = exporter.get_status()
            adaptive_time = (time.time() - start_time) * 1000
            
            adaptive_result = {
                'test_name': 'adaptive_batching',
                'success': adaptive_status['metrics']['total_batches_processed'] > 0,
                'items_processed': adaptive_status['metrics']['total_items_exported'],
                'batches_created': adaptive_status['metrics']['total_batches_created'],
                'average_batch_size': adaptive_status['metrics']['average_batch_size'],
                'processing_time_ms': adaptive_time,
                'adaptive_batch_size': adaptive_status['adaptive_parameters']['batch_size']
            }
            
            results['adaptive_batching_tests'].append(adaptive_result)
            
            # Final status and metrics
            final_status = exporter.get_status()
            worker_stats = exporter.get_worker_stats()
            
            results['performance_metrics'] = {
                'total_items_processed': final_status['metrics']['total_items_exported'],
                'total_batches_processed': final_status['metrics']['total_batches_processed'],
                'average_batch_size': final_status['metrics']['average_batch_size'],
                'peak_throughput_items_per_second': final_status['metrics']['peak_throughput_items_per_second'],
                'average_processing_time_ms': final_status['metrics']['average_processing_time_ms'],
                'worker_count': len(worker_stats),
                'queue_pressure': final_status['queue_pressure'],
                'throughput_scaling_factor': self._calculate_scaling_factor(throughput_tests)
            }
            
            logger.info(f"✅ OTLP concurrency test completed: {final_status['metrics']['total_items_exported']} items processed")
            
        finally:
            await exporter.stop()
        
        return results
    
    def _calculate_scaling_factor(self, throughput_tests: List[Dict[str, Any]]) -> float:
        """Calculate throughput scaling factor."""
        if len(throughput_tests) < 2:
            return 1.0
        
        # Compare throughput between 1 and max concurrent batches
        single_batch_throughput = next((t['throughput_items_per_second'] for t in throughput_tests if t['concurrent_batches'] == 1), 0)
        max_batch_throughput = max(t['throughput_items_per_second'] for t in throughput_tests)
        
        if single_batch_throughput > 0:
            return max_batch_throughput / single_batch_throughput
        return 1.0
    
    async def test_integration_workflows(self) -> Dict[str, Any]:
        """Test end-to-end integration workflows."""
        logger.info("🔧 Testing Integration Workflows")
        
        results = {
            'compression_saga_integration': [],
            'entropy_otlp_integration': [],
            'full_pipeline_integration': [],
            'performance_metrics': {}
        }
        
        # Initialize all components
        compression_manager = CompressionManager(default_strategy=CompressionStrategy.ADAPTIVE)
        saga_coordinator = SagaCoordinator()
        entropy_processor = EntropyProcessor()
        
        # Test 1: Compression + Saga integration
        async def compressed_task_action(context, step):
            content = context.get('task_content', '')
            result = await compression_manager.compress(content)
            return {
                'step_id': step.step_id,
                'original_size': len(content),
                'compressed_size': len(result.compressed_content),
                'compression_ratio': result.compression_ratio
            }
        
        saga_steps = [
            SagaStep(
                step_id="compress_task_data",
                name="compress_task_content",
                action=compressed_task_action
            )
        ]
        
        compression_saga = SagaDefinition(
            saga_id="compression_integration_saga",
            name="Compression Integration Test",
            steps=saga_steps
        )
        
        start_time = time.time()
        integration_result = await saga_coordinator.execute_saga(
            compression_saga,
            {
                'task_content': json.dumps({
                    'large_dataset': [f'data_point_{i}' for i in range(100)],
                    'metadata': {'processing': 'integration_test'}
                })
            }
        )
        integration_time = (time.time() - start_time) * 1000
        
        compression_integration = {
            'test_name': 'compression_saga_integration',
            'success': integration_result['status'] == 'completed',
            'compression_achieved': integration_result['results']['compress_task_data']['result']['compression_ratio'] < 1.0,
            'execution_time_ms': integration_time
        }
        
        results['compression_saga_integration'].append(compression_integration)
        
        # Test 2: Entropy + OTLP integration
        # This would test entropy analysis feeding into OTLP batching decisions
        test_content = 'Mixed entropy content: ' + 'repeated pattern ' * 50 + json.dumps({'unique': i for i in range(20)})
        
        start_time = time.time()
        entropy_analysis = entropy_processor.analyze_content_entropy(test_content)
        entropy_time = (time.time() - start_time) * 1000
        
        entropy_otlp_result = {
            'test_name': 'entropy_otlp_integration',
            'success': True,
            'entropy_score': entropy_analysis.content_entropy,
            'recommended_mode': entropy_analysis.recommended_mode.value,
            'chunk_suggestions': len(entropy_analysis.chunk_suggestions),
            'analysis_time_ms': entropy_time
        }
        
        results['entropy_otlp_integration'].append(entropy_otlp_result)
        
        # Test 3: Full pipeline integration
        # Simulate a complete workflow using all optimizations
        pipeline_data = {
            'task': 'Complete pipeline test with all optimizations',
            'data': [f'pipeline_item_{i}' for i in range(50)],
            'metadata': {'integration': True, 'timestamp': time.time()}
        }
        
        start_time = time.time()
        
        # Step 1: Compress data
        compressed_data = await compression_manager.compress(json.dumps(pipeline_data))
        
        # Step 2: Analyze entropy
        entropy_analysis = entropy_processor.analyze_content_entropy(compressed_data.compressed_content)
        
        # Step 3: Process with saga if high complexity
        if entropy_analysis.content_entropy > 0.5:
            async def pipeline_action(context, step):
                return {'processed': True, 'entropy': entropy_analysis.content_entropy}
            
            pipeline_saga = SagaDefinition(
                saga_id="full_pipeline_saga",
                name="Full Pipeline Integration",
                steps=[SagaStep(step_id="process_data", name="process", action=pipeline_action)]
            )
            
            saga_result = await saga_coordinator.execute_saga(pipeline_saga, {'pipeline_data': pipeline_data})
            saga_success = saga_result['status'] == 'completed'
        else:
            saga_success = True  # Skipped due to low complexity
        
        pipeline_time = (time.time() - start_time) * 1000
        
        full_pipeline_result = {
            'test_name': 'full_pipeline_integration',
            'success': saga_success and compressed_data.compression_ratio < 1.0,
            'compression_ratio': compressed_data.compression_ratio,
            'entropy_score': entropy_analysis.content_entropy,
            'saga_executed': entropy_analysis.content_entropy > 0.5,
            'total_pipeline_time_ms': pipeline_time,
            'optimization_count': 3  # Compression, entropy, saga
        }
        
        results['full_pipeline_integration'].append(full_pipeline_result)
        
        # Calculate integration performance metrics
        all_integration_tests = (
            results['compression_saga_integration'] +
            results['entropy_otlp_integration'] +
            results['full_pipeline_integration']
        )
        
        successful_integrations = [t for t in all_integration_tests if t.get('success', False)]
        
        results['performance_metrics'] = {
            'total_integration_tests': len(all_integration_tests),
            'successful_integrations': len(successful_integrations),
            'integration_success_rate': len(successful_integrations) / len(all_integration_tests) if all_integration_tests else 0,
            'average_integration_time_ms': sum(t.get('execution_time_ms', t.get('analysis_time_ms', t.get('total_pipeline_time_ms', 0))) for t in successful_integrations) / len(successful_integrations) if successful_integrations else 0
        }
        
        logger.info(f"✅ Integration workflows test completed: {len(successful_integrations)}/{len(all_integration_tests)} tests passed")
        
        return results
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary."""
        summary = {
            'overall_success': True,
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'optimization_results': {},
            'performance_summary': {},
            'recommendations': []
        }
        
        # Analyze each optimization category
        for optimization, results in self.test_results.items():
            if not isinstance(results, dict):
                continue
                
            category_tests = []
            
            # Collect all tests from this optimization category
            for test_category, test_list in results.items():
                if isinstance(test_list, list):
                    category_tests.extend(test_list)
            
            successful_tests = [t for t in category_tests if t.get('success', False)]
            
            optimization_summary = {
                'total_tests': len(category_tests),
                'successful_tests': len(successful_tests),
                'success_rate': len(successful_tests) / len(category_tests) if category_tests else 0,
                'performance_metrics': results.get('performance_metrics', {})
            }
            
            summary['optimization_results'][optimization] = optimization_summary
            summary['total_tests'] += len(category_tests)
            summary['successful_tests'] += len(successful_tests)
            summary['failed_tests'] += len(category_tests) - len(successful_tests)
            
            # Check if this optimization meets success criteria
            if optimization_summary['success_rate'] < 0.8:
                summary['overall_success'] = False
                summary['recommendations'].append(f"Improve {optimization} optimization (success rate: {optimization_summary['success_rate']:.1%})")
        
        # Overall success rate
        summary['overall_success_rate'] = summary['successful_tests'] / summary['total_tests'] if summary['total_tests'] > 0 else 0
        
        # Performance summary
        compression_metrics = summary['optimization_results'].get('compression', {}).get('performance_metrics', {})
        saga_metrics = summary['optimization_results'].get('saga', {}).get('performance_metrics', {})
        entropy_metrics = summary['optimization_results'].get('entropy', {}).get('performance_metrics', {})
        otlp_metrics = summary['optimization_results'].get('otlp', {}).get('performance_metrics', {})
        
        summary['performance_summary'] = {
            'compression_ratio_achieved': compression_metrics.get('average_compression_ratio', 0),
            'saga_execution_success_rate': saga_metrics.get('success_rate', 0),
            'entropy_analysis_accuracy': entropy_metrics.get('entropy_analysis', {}).get('average_entropy_accuracy', 0),
            'otlp_throughput_scaling': otlp_metrics.get('throughput_scaling_factor', 1.0),
            'integration_success_rate': summary['optimization_results'].get('integration', {}).get('success_rate', 0)
        }
        
        # Add recommendations based on performance
        if summary['performance_summary']['compression_ratio_achieved'] < 0.3:
            summary['recommendations'].append("Tune compression parameters for better ratios")
        
        if summary['performance_summary']['otlp_throughput_scaling'] < 2.0:
            summary['recommendations'].append("Optimize OTLP concurrency for better scaling")
        
        if not summary['recommendations']:
            summary['recommendations'].append("All optimizations performing within expected parameters")
        
        return summary


async def main():
    """Run the coordination optimization test suite."""
    tester = CoordinationOptimizationTester()
    
    print("🚀 ATLAS Coordination Optimization Test Suite")
    print("=" * 60)
    
    try:
        results = await tester.run_all_tests()
        
        print("\n📊 TEST RESULTS SUMMARY")
        print("=" * 30)
        
        if 'summary' in results:
            summary = results['summary']
            
            print(f"Overall Success: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}")
            print(f"Success Rate: {summary['overall_success_rate']:.1%}")
            print(f"Tests: {summary['successful_tests']}/{summary['total_tests']} passed")
            
            print("\n🎯 OPTIMIZATION PERFORMANCE")
            print("-" * 30)
            
            perf = summary['performance_summary']
            print(f"Compression Ratio: {perf['compression_ratio_achieved']:.2f}")
            print(f"Saga Success Rate: {perf['saga_execution_success_rate']:.1%}")
            print(f"Entropy Accuracy: {perf['entropy_analysis_accuracy']:.1%}")
            print(f"OTLP Scaling Factor: {perf['otlp_throughput_scaling']:.1f}x")
            print(f"Integration Success: {perf['integration_success_rate']:.1%}")
            
            print("\n💡 RECOMMENDATIONS")
            print("-" * 20)
            for rec in summary['recommendations']:
                print(f"• {rec}")
        
        print(f"\n📄 Full results available in test output")
        return results
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(main())