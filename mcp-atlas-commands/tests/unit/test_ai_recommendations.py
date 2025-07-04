#!/usr/bin/env python3
"""Quick test of AI recommendations."""

import asyncio
import sys
import json

sys.path.insert(0, './src')

from atlas_commands.handlers.workflow_intelligence import WorkflowIntelligenceHandler

async def test_ai_recommendations():
    handler = WorkflowIntelligenceHandler()
    
    # Test with a task description that should trigger recommendations
    args = {
        "task_description": "Create a new task to validate memory performance and cache statistics",
        "domain": "validation"
    }
    
    result = await handler._handle_adaptive_command_selection(args)
    response = json.loads(result[0].text)
    
    print(f"Recommendations count: {len(response.get('recommendations', []))}")
    print(f"Top 3 recommendations:")
    for i, rec in enumerate(response.get('recommendations', [])[:3]):
        print(f"  {i+1}. {rec.get('command')} (confidence: {rec.get('confidence'):.2f})")
    
    return len(response.get('recommendations', [])) > 0

if __name__ == "__main__":
    success = asyncio.run(test_ai_recommendations())