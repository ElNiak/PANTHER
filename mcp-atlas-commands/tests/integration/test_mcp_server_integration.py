"""
Integration tests for ATLAS MCP Server - Full MCP Protocol Testing
Testing server capabilities, resources, tools, and prompts following MCP patterns.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Resource, Tool, Prompt, TextContent

from src.atlas_commands.server import EnhancedAtlasCommandsServer
from src.atlas_commands.tools.orchestrate_intelligent_tasks import orchestrate_intelligent_tasks
from src.atlas_commands.tools.adaptive_command_selection import adaptive_command_selection
from src.atlas_commands.tools.analyze_workflow_patterns import analyze_workflow_patterns


class TestMCPServerIntegration:
    """Integration tests for full MCP server functionality."""
    
    @pytest.fixture
    async def mcp_server(self):
        """Create an actual MCP server instance for integration testing."""
        server = EnhancedAtlasCommandsServer()
        await server.initialize()
        return server
    
    @pytest.fixture
    def mcp_client_mock(self):
        """Mock MCP client for testing server responses."""
        client = Mock()
        client.send_request = AsyncMock()
        client.notifications = []
        return client
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test MCP server initializes correctly with all capabilities."""
        assert mcp_server is not None
        
        # Verify server has MCP capabilities
        assert hasattr(mcp_server, 'list_tools')
        assert hasattr(mcp_server, 'list_resources') 
        assert hasattr(mcp_server, 'list_prompts')
        assert hasattr(mcp_server, 'call_tool')
        assert hasattr(mcp_server, 'read_resource')
        
    @pytest.mark.asyncio
    async def test_list_tools_capability(self, mcp_server):
        """Test MCP list_tools capability returns ATLAS tools."""
        tools = await mcp_server.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Verify tool structure follows MCP specification
        for tool in tools:
            assert isinstance(tool, dict)
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            
        # Verify ATLAS-specific tools are present
        tool_names = [tool['name'] for tool in tools]
        expected_tools = [
            'orchestrate_intelligent_tasks',
            'adaptive_command_selection', 
            'analyze_workflow_patterns',
            'track_progress_milestones'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_call_tool_orchestration(self, mcp_server):
        """Test calling orchestration tool through MCP interface."""
        tool_call_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Implement REST API endpoints',
                'context': {
                    'domain': 'backend',
                    'team_size': 3,
                    'deadline': '2025-07-15'
                },
                'requirements': {
                    'performance_target': '< 200ms',
                    'security_level': 'high'
                }
            }
        }
        
        result = await mcp_server.call_tool(tool_call_request)
        
        assert result is not None
        assert 'content' in result
        assert isinstance(result['content'], list)
        
        # Verify orchestration result structure
        content = result['content'][0]
        assert 'text' in content
        
        # Parse orchestration response
        orchestration_data = json.loads(content['text'])
        assert 'task_analysis' in orchestration_data
        assert 'coordination_strategy' in orchestration_data
        assert 'execution_sequence' in orchestration_data
        assert 'estimated_efficiency_gain' in orchestration_data
    
    @pytest.mark.asyncio
    async def test_call_tool_adaptive_selection(self, mcp_server):
        """Test adaptive command selection tool through MCP."""
        tool_call_request = {
            'name': 'adaptive_command_selection',
            'arguments': {
                'current_context': {
                    'project_type': 'microservices',
                    'current_phase': 'development',
                    'team_experience': 'senior'
                },
                'available_commands': [
                    'analyze', 'design', 'implement', 'test', 'deploy'
                ],
                'user_preferences': {
                    'automation_level': 'high',
                    'detail_level': 'comprehensive'
                }
            }
        }
        
        result = await mcp_server.call_tool(tool_call_request)
        
        assert result is not None
        content_data = json.loads(result['content'][0]['text'])
        
        assert 'recommended_command' in content_data
        assert 'confidence_score' in content_data
        assert 'reasoning' in content_data
        assert 'alternative_commands' in content_data
    
    @pytest.mark.asyncio
    async def test_list_resources_capability(self, mcp_server):
        """Test MCP list_resources capability."""
        resources = await mcp_server.list_resources()
        
        assert isinstance(resources, list)
        
        # Verify resource structure
        for resource in resources:
            assert isinstance(resource, dict)
            assert 'uri' in resource
            assert 'name' in resource
            assert 'mimeType' in resource or 'description' in resource
            
    @pytest.mark.asyncio
    async def test_read_resource_capability(self, mcp_server):
        """Test MCP read_resource capability."""
        # First get available resources
        resources = await mcp_server.list_resources()
        
        if resources:
            resource_uri = resources[0]['uri']
            
            resource_content = await mcp_server.read_resource(resource_uri)
            
            assert resource_content is not None
            assert 'contents' in resource_content
            assert isinstance(resource_content['contents'], list)
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_tool(self, mcp_server):
        """Test MCP server error handling for invalid tool calls."""
        invalid_tool_request = {
            'name': 'nonexistent_tool',
            'arguments': {}
        }
        
        with pytest.raises(Exception) as exc_info:
            await mcp_server.call_tool(invalid_tool_request)
            
        # Verify error is properly structured
        assert exc_info.value is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_arguments(self, mcp_server):
        """Test error handling for invalid tool arguments."""
        invalid_args_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                # Missing required fields
                'invalid_field': 'invalid_value'
            }
        }
        
        with pytest.raises(Exception) as exc_info:
            await mcp_server.call_tool(invalid_args_request)
            
        assert exc_info.value is not None


class TestMCPToolDefinitions:
    """Test MCP tool definitions and schemas."""
    
    @pytest.fixture
    def atlas_server(self):
        """Create ATLAS server for tool definition testing."""
        return EnhancedAtlasCommandsServer()
    
    def test_orchestration_tool_schema(self, atlas_server):
        """Test orchestration tool has proper MCP schema definition."""
        tools = atlas_server.get_tool_definitions()
        
        orchestration_tool = None
        for tool in tools:
            if tool['name'] == 'orchestrate_intelligent_tasks':
                orchestration_tool = tool
                break
                
        assert orchestration_tool is not None
        
        # Verify schema structure
        schema = orchestration_tool['inputSchema']
        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'required' in schema
        
        # Verify required properties
        properties = schema['properties']
        assert 'task_description' in properties
        assert 'context' in properties
        assert 'requirements' in properties
        
        # Verify property types
        assert properties['task_description']['type'] == 'string'
        assert properties['context']['type'] == 'object'
        assert properties['requirements']['type'] == 'object'
    
    def test_adaptive_selection_tool_schema(self, atlas_server):
        """Test adaptive command selection tool schema."""
        tools = atlas_server.get_tool_definitions()
        
        adaptive_tool = None
        for tool in tools:
            if tool['name'] == 'adaptive_command_selection':
                adaptive_tool = tool
                break
                
        assert adaptive_tool is not None
        
        schema = adaptive_tool['inputSchema']
        properties = schema['properties']
        
        assert 'current_context' in properties
        assert 'available_commands' in properties
        assert 'user_preferences' in properties
        
        # Verify array type for available_commands
        assert properties['available_commands']['type'] == 'array'
        assert 'items' in properties['available_commands']
    
    def test_workflow_analysis_tool_schema(self, atlas_server):
        """Test workflow pattern analysis tool schema."""
        tools = atlas_server.get_tool_definitions()
        
        workflow_tool = None
        for tool in tools:
            if tool['name'] == 'analyze_workflow_patterns':
                workflow_tool = tool
                break
                
        assert workflow_tool is not None
        
        schema = workflow_tool['inputSchema']
        properties = schema['properties']
        
        assert 'workflow_data' in properties
        assert 'analysis_depth' in properties
        assert 'optimization_goals' in properties


class TestMCPResourceManagement:
    """Test MCP resource management capabilities."""
    
    @pytest.fixture
    async def server_with_resources(self):
        """Create server with test resources."""
        server = EnhancedAtlasCommandsServer()
        await server.initialize()
        
        # Add test resources
        await server.add_resource({
            'uri': 'atlas://coordination/strategies',
            'name': 'Coordination Strategies',
            'description': 'Available coordination optimization strategies',
            'mimeType': 'application/json'
        })
        
        await server.add_resource({
            'uri': 'atlas://documentation/api',
            'name': 'API Documentation', 
            'description': 'ATLAS MCP API documentation',
            'mimeType': 'text/markdown'
        })
        
        return server
    
    @pytest.mark.asyncio
    async def test_resource_listing(self, server_with_resources):
        """Test listing of available resources."""
        resources = await server_with_resources.list_resources()
        
        assert len(resources) >= 2
        
        # Verify resource URIs
        resource_uris = [r['uri'] for r in resources]
        assert 'atlas://coordination/strategies' in resource_uris
        assert 'atlas://documentation/api' in resource_uris
    
    @pytest.mark.asyncio
    async def test_resource_content_reading(self, server_with_resources):
        """Test reading resource content."""
        resource_content = await server_with_resources.read_resource(
            'atlas://coordination/strategies'
        )
        
        assert resource_content is not None
        assert 'contents' in resource_content
        
        contents = resource_content['contents']
        assert isinstance(contents, list)
        assert len(contents) > 0
        
        # Verify content structure
        content_item = contents[0]
        assert 'type' in content_item
        assert content_item['type'] in ['text', 'resource']
    
    @pytest.mark.asyncio
    async def test_dynamic_resource_updates(self, server_with_resources):
        """Test dynamic resource updates during runtime."""
        # Add new resource dynamically
        new_resource = {
            'uri': 'atlas://runtime/metrics',
            'name': 'Runtime Metrics',
            'description': 'Current system performance metrics',
            'mimeType': 'application/json'
        }
        
        await server_with_resources.add_resource(new_resource)
        
        # Verify resource appears in listing
        resources = await server_with_resources.list_resources()
        resource_uris = [r['uri'] for r in resources]
        assert 'atlas://runtime/metrics' in resource_uris


class TestMCPPromptTemplates:
    """Test MCP prompt template functionality."""
    
    @pytest.fixture
    def server_with_prompts(self):
        """Create server with test prompts."""
        server = EnhancedAtlasCommandsServer()
        
        # Add test prompts
        server.add_prompt({
            'name': 'task_decomposition',
            'description': 'Decompose complex tasks into manageable subtasks',
            'arguments': [
                {
                    'name': 'task_description',
                    'description': 'The task to decompose',
                    'required': True
                },
                {
                    'name': 'complexity_level',
                    'description': 'Target complexity level for subtasks',
                    'required': False
                }
            ]
        })
        
        return server
    
    def test_prompt_listing(self, server_with_prompts):
        """Test listing of available prompts."""
        prompts = server_with_prompts.list_prompts()
        
        assert len(prompts) >= 1
        
        # Find task decomposition prompt
        decomp_prompt = None
        for prompt in prompts:
            if prompt['name'] == 'task_decomposition':
                decomp_prompt = prompt
                break
                
        assert decomp_prompt is not None
        assert 'description' in decomp_prompt
        assert 'arguments' in decomp_prompt
    
    def test_prompt_argument_validation(self, server_with_prompts):
        """Test prompt argument validation."""
        prompts = server_with_prompts.list_prompts()
        decomp_prompt = None
        
        for prompt in prompts:
            if prompt['name'] == 'task_decomposition':
                decomp_prompt = prompt
                break
                
        assert decomp_prompt is not None
        
        # Verify argument structure
        arguments = decomp_prompt['arguments']
        assert len(arguments) >= 1
        
        # Check required argument
        required_args = [arg for arg in arguments if arg.get('required', False)]
        assert len(required_args) >= 1
        assert required_args[0]['name'] == 'task_description'


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module-level async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])