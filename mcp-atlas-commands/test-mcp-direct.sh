#!/bin/bash

# Direct MCP test script
set -e

CONTAINER_NAME="atlas-commands-mcp"

echo "Testing MCP communication directly..."

# Create test input
cat > /tmp/mcp-test-input << 'EOF'
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "atlas-client", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "method": "notifications/initialized"}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_project_tasks", "arguments": {"project_name": "TEST"}}}
EOF

echo "Sending MCP requests..."

# Test with a longer wait and proper signal handling
{
    cat /tmp/mcp-test-input | docker exec -i "$CONTAINER_NAME" python -m atlas_commands.server &
    PID=$!
    
    # Wait for a reasonable time then send SIGTERM
    sleep 15
    kill $PID 2>/dev/null || true
    wait $PID 2>/dev/null || true
} > /tmp/mcp-test-output 2>/dev/null

echo "Output captured:"
cat /tmp/mcp-test-output

echo ""
echo "Analyzing responses..."

# Extract responses
echo "Initialize response:"
grep '"id":1' /tmp/mcp-test-output | head -1 | jq '.' 2>/dev/null || echo "No initialize response found"

echo ""
echo "Tool call response:"
grep '"id":3' /tmp/mcp-test-output | head -1 | jq '.' 2>/dev/null || echo "No tool call response found"

# Cleanup
rm -f /tmp/mcp-test-input /tmp/mcp-test-output