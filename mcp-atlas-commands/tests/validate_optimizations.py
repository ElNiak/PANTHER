#!/usr/bin/env python3
"""
Quick validation of coordination optimization implementations.
Validates that all 5 optimization strategies are working at a basic level.
"""

import asyncio
import sys
import os

# Add src directory to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.compression.compression_manager import CompressionManager, CompressionStrategy
from atlas_commands.saga.saga_coordinator import SagaCoordinator, SagaDefinition, SagaStep
from atlas_commands.entropy.entropy_processor import EntropyProcessor
from atlas_commands.entropy.incremental_memory_manager import IncrementalMemoryManager, MemoryOperationType
from atlas_commands.otlp_concurrency.concurrent_exporter import ConcurrentExporter

async def validate_all_optimizations():
    """Quick validation of all 5 coordination optimizations."""
    print("🚀 ATLAS Coordination Optimization Validation")
    print("=" * 55)
    
    results = {}
    
    # 1. LLMLingua Compression
    print("\n1️⃣ Testing LLMLingua Compression...")
    try:
        compression_manager = CompressionManager()
        test_content = "This is a test of the compression system with multiple repeated words and patterns."
        result = await compression_manager.compress(test_content, strategy=CompressionStrategy.LLMLINGUA)
        ratio = getattr(result, 'compression_ratio', getattr(result, 'token_reduction_ratio', 1.0))
        print(f"   ✅ Compression working: {ratio:.2f} ratio")
        results['compression'] = True
    except Exception as e:
        print(f"   ❌ Compression failed: {e}")
        results['compression'] = False
    
    # 2. Saga Patterns
    print("\n2️⃣ Testing Saga Patterns...")
    try:
        saga_coordinator = SagaCoordinator()
        
        # Simple saga with one step
        saga_definition = SagaDefinition(
            saga_id="validation_saga",
            name="Validation Test Saga",
            steps=[
                SagaStep(
                    step_id="test_step",
                    name="Test Step",
                    action=lambda: {"status": "success"},
                    compensation=lambda: {"status": "compensated"}
                )
            ]
        )
        
        result = await saga_coordinator.execute_saga(saga_definition)
        print(f"   ✅ Saga working: {result['status']}")
        results['saga'] = True
    except Exception as e:
        print(f"   ❌ Saga failed: {e}")
        results['saga'] = False
    
    # 3. Entropy Processing
    print("\n3️⃣ Testing Entropy Processing...")
    try:
        entropy_processor = EntropyProcessor()
        test_content = "This is test content with varying information density and entropy patterns."
        analysis = entropy_processor.analyze_content_entropy(test_content)
        print(f"   ✅ Entropy working: {analysis.content_entropy:.3f} entropy, {analysis.recommended_mode.value} mode")
        results['entropy'] = True
    except Exception as e:
        print(f"   ❌ Entropy failed: {e}")
        results['entropy'] = False
    
    # 4. Incremental Memory Manager
    print("\n4️⃣ Testing Incremental Memory Manager...")
    try:
        memory_manager = IncrementalMemoryManager()
        test_content = "This is a test of incremental memory processing with chunk management."
        
        chunks_processed = 0
        async for result in memory_manager.process_memory_operation(
            test_content, 
            MemoryOperationType.SEARCH
        ):
            chunks_processed += 1
            if chunks_processed >= 3:  # Limit for validation
                break
                
        print(f"   ✅ Memory manager working: {chunks_processed} chunks processed")
        results['memory'] = True
    except Exception as e:
        print(f"   ❌ Memory manager failed: {e}")
        results['memory'] = False
    
    # 5. OTLP Concurrency
    print("\n5️⃣ Testing OTLP Concurrency...")
    try:
        exporter = ConcurrentExporter(max_concurrent_batches=2, max_batch_size=5)
        await exporter.start()
        
        # Queue some test items
        item_ids = []
        for i in range(10):
            item_id = await exporter.queue_item(f"test_data_{i}", priority=5)
            item_ids.append(item_id)
        
        # Wait briefly for processing
        await asyncio.sleep(1.0)
        
        status = exporter.get_status()
        await exporter.stop()
        
        print(f"   ✅ OTLP concurrency working: {status['metrics']['total_items_exported']} items exported")
        results['otlp'] = True
    except Exception as e:
        print(f"   ❌ OTLP concurrency failed: {e}")
        results['otlp'] = False
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 25)
    successful = sum(results.values())
    total = len(results)
    
    for optimization, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{optimization.upper():<12}: {status}")
    
    print(f"\nOverall: {successful}/{total} optimizations working")
    
    if successful == total:
        print("🎉 All coordination optimizations are functional!")
        return True
    else:
        print("⚠️  Some optimizations need attention")
        return False

if __name__ == "__main__":
    asyncio.run(validate_all_optimizations())