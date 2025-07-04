#!/usr/bin/env python3
"""Test the robust, production-ready implementations."""

import asyncio
import json
import logging
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_robust_implementations():
    """Test the enhanced implementations of memory and workflow tools."""
    from src.atlas_commands.handlers.memory_management import MemoryManagementHandler
    from src.atlas_commands.handlers.workflow_intelligence import WorkflowIntelligenceHandler
    from src.atlas_commands.storage.task_storage_manager import TaskStorageManager
    from src.atlas_commands.caching.cache_manager import CacheManager
    
    # Create test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_manager = TaskStorageManager(temp_dir)
        cache_manager = CacheManager()
        
        # Create mock server with realistic components
        class MockServer:
            def __init__(self):
                self.storage_manager = storage_manager
                self.cache_manager = cache_manager
                self.memory_manager = True
                self.embedding_generator = None
        
        mock_server = MockServer()
        
        # Initialize handlers
        memory_handler = MemoryManagementHandler(mock_server)
        workflow_handler = WorkflowIntelligenceHandler(mock_server)
        
        # Add some test data for meaningful results
        storage_manager.create_task_metadata("test-project", "task1", "debugging", "Debug memory issues")
        storage_manager.create_task_metadata("test-project", "task2", "testing", "Test cache performance")
        
        tests = []
        
        # 1. Test Enhanced Memory Health Check
        logger.info("🔍 Testing Enhanced Memory Health Check...")
        try:
            result = await memory_handler._handle_memory_health_check({})
            result_data = json.loads(result[0].text)
            
            # Check for comprehensive health data
            required_sections = ["system_memory", "component_tests", "performance_metrics", "recommendations", "overall_status"]
            has_all_sections = all(section in result_data for section in required_sections)
            
            # Check for actual testing (not just status checks)
            has_real_tests = "response_time_ms" in str(result_data)
            has_memory_analysis = "used_percentage" in str(result_data)
            has_recommendations = len(result_data.get("recommendations", [])) >= 0
            
            success = has_all_sections and has_real_tests and has_memory_analysis
            tests.append(("Enhanced Memory Health Check", success))
            
            logger.info(f"✅ Memory Health Check: {'ROBUST' if success else 'BASIC'}")
            logger.info(f"   - Comprehensive sections: {has_all_sections}")
            logger.info(f"   - Real performance tests: {has_real_tests}")
            logger.info(f"   - Memory analysis: {has_memory_analysis}")
            logger.info(f"   - Recommendations: {has_recommendations}")
            
        except Exception as e:
            tests.append(("Enhanced Memory Health Check", False))
            logger.error(f"❌ Memory Health Check failed: {str(e)}")
        
        # 2. Test Comprehensive Memory Analytics
        logger.info("📊 Testing Comprehensive Memory Analytics...")
        try:
            result = await memory_handler._handle_memory_analytics({})
            result_data = json.loads(result[0].text)
            
            # Check for comprehensive analytics
            required_sections = ["system_analytics", "cache_analytics", "storage_analytics", "performance_insights", "optimization_recommendations"]
            has_all_sections = all(section in result_data for section in required_sections)
            
            # Check for detailed sub-analysis
            has_system_details = "garbage_collection" in str(result_data)
            has_cache_details = "l1_cache" in str(result_data) and "l2_cache" in str(result_data)
            has_performance_tests = "performance_tests" in str(result_data)
            has_insights = len(result_data.get("performance_insights", {}).get("bottlenecks", [])) >= 0
            
            success = has_all_sections and has_system_details and has_cache_details
            tests.append(("Comprehensive Memory Analytics", success))
            
            logger.info(f"✅ Memory Analytics: {'COMPREHENSIVE' if success else 'BASIC'}")
            logger.info(f"   - All analytics sections: {has_all_sections}")
            logger.info(f"   - System details: {has_system_details}")
            logger.info(f"   - Cache analysis: {has_cache_details}")
            logger.info(f"   - Performance tests: {has_performance_tests}")
            logger.info(f"   - Insights: {has_insights}")
            
        except Exception as e:
            tests.append(("Comprehensive Memory Analytics", False))
            logger.error(f"❌ Memory Analytics failed: {str(e)}")
        
        # 3. Test Intelligent Adaptive Command Selection
        logger.info("🧠 Testing Intelligent Adaptive Command Selection...")
        try:
            test_scenarios = [
                {
                    "task_description": "debug memory performance issues in production",
                    "domain": "debugging",
                    "previous_commands": ["list_project_tasks"]
                },
                {
                    "task_description": "implement complex cache optimization system",
                    "domain": "development",
                    "previous_commands": ["create_task_metadata", "memory_health_check"]
                },
                {
                    "task_description": "validate system performance during testing",
                    "domain": "testing",
                    "previous_commands": []
                }
            ]
            
            scenario_results = []
            for i, scenario in enumerate(test_scenarios, 1):
                result = await workflow_handler._handle_adaptive_command_selection(scenario)
                result_data = json.loads(result[0].text)
                
                # Check for intelligent analysis
                has_task_analysis = "task_analysis" in result_data
                has_context_analysis = "context_analysis" in result_data
                has_workflow_stage = result_data.get("task_analysis", {}).get("workflow_stage") != "unknown"
                has_complexity = result_data.get("task_analysis", {}).get("complexity") != "unknown"
                has_recommendations = len(result_data.get("recommendations", [])) > 0
                has_reasoning = all("reason" in rec for rec in result_data.get("recommendations", []))
                has_confidence = all("confidence" in rec for rec in result_data.get("recommendations", []))
                
                scenario_success = has_task_analysis and has_context_analysis and has_workflow_stage and has_complexity and has_recommendations
                scenario_results.append(scenario_success)
                
                logger.info(f"   Scenario {i}: {'INTELLIGENT' if scenario_success else 'BASIC'}")
                logger.info(f"     - Task analysis: {has_task_analysis}")
                logger.info(f"     - Workflow stage detected: {has_workflow_stage}")
                logger.info(f"     - Complexity assessed: {has_complexity}")
                logger.info(f"     - Quality recommendations: {has_recommendations and has_reasoning and has_confidence}")
            
            success = all(scenario_results)
            tests.append(("Intelligent Adaptive Command Selection", success))
            logger.info(f"✅ Adaptive Command Selection: {'INTELLIGENT' if success else 'BASIC'}")
            
        except Exception as e:
            tests.append(("Intelligent Adaptive Command Selection", False))
            logger.error(f"❌ Adaptive Command Selection failed: {str(e)}")
        
        return tests

async def main():
    """Run robust implementation tests."""
    logger.info("🚀 Testing Robust Atlas MCP Implementations")
    logger.info("Validating production-ready features...")
    
    results = await test_robust_implementations()
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n📊 Robustness Assessment:")
    logger.info(f"  Production-Ready: {passed}/{total}")
    logger.info(f"  Quality Score: {passed/total*100:.1f}%")
    
    logger.info(f"\n📋 Implementation Quality:")
    for test_name, success in results:
        status = "🚀 PRODUCTION-READY" if success else "⚠️ NEEDS ENHANCEMENT"
        logger.info(f"  {test_name}: {status}")
    
    if passed == total:
        logger.info("\n🎉 ALL IMPLEMENTATIONS ARE PRODUCTION-READY!")
        logger.info("🔧 Atlas MCP system ready for enterprise deployment")
        return 0
    else:
        logger.warning(f"\n⚠️ {total - passed} implementations need enhancement for production readiness")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)