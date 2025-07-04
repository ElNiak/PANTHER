# ATLAS MCP Testing Procedure

## Overview
This document outlines the complete procedure for testing ATLAS MCP integration with Claude Code, including container rebuilding, test execution, and result analysis.

## Prerequisites
- Docker and Docker Compose installed
- Python 3.10+ with required dependencies
- ATLAS MCP project cloned and configured
- Claude Code with MCP support

## Step-by-Step Procedure

### Phase 1: Environment Preparation

#### 1.1 Rebuild Containers
```bash
# Navigate to project directory
cd /Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/mcp-atlas-commands

# Stop existing containers
docker-compose down

# Remove old images (optional, for clean rebuild)
docker rmi atlas-commands-mcp:latest atlas-commands-mcp:fast 2>/dev/null || true

# Rebuild containers with latest changes
docker-compose build --no-cache

# Start containers in detached mode
docker-compose up -d

# Wait for health checks
sleep 30

# Verify container status
docker ps | grep atlas
```

#### 1.2 Validate Container Health
```bash
# Run quick fix script to ensure everything is operational
./atlas-mcp-quick-fix.sh

# Check logs for any startup errors
docker logs atlas-commands-mcp --tail 50
```

### Phase 2: Test Execution

#### 2.1 Basic Connectivity Tests
```bash
# Test MCP client connectivity
python mcp-client-working.py test

# Run basic connectivity suite
python test-runner.py --quick
```

#### 2.2 Full Test Suite
```bash
# Run comprehensive test suite
python test-runner.py

# Alternative: Run with automated fixes if issues detected
python test-runner.py --fix
```

#### 2.3 Claude Code Integration Test
```bash
# Verify Claude Code can connect to ATLAS MCP server
# This requires Claude Code to be running with updated .mcp.json

# Test from Claude Code interface:
# 1. Open Claude Code
# 2. Try using ATLAS tools: create_hierarchical_task, list_project_tasks
# 3. Verify responses and functionality
```

### Phase 3: Result Analysis

#### 3.1 Review Test Results
```bash
# Check latest test results
ls -la atlas_mcp_test_results_*.json | tail -1

# View summary from test logs
tail -50 atlas_mcp_tests.log
```

#### 3.2 Performance Validation
- Response times should be < 3 seconds per tool call
- Memory usage should remain stable
- Cache hit rates should improve over time
- No data loss between sessions

#### 3.3 Integration Validation
- All 49 tools should be available
- Auto-approved tools should work without prompts
- Task persistence across sessions
- Memory graph relationships preserved

## Common Issues and Fixes

### Issue 1: Container Won't Start
```bash
# Check Docker daemon
sudo systemctl status docker

# Check port conflicts
netstat -tulpn | grep 8765

# Review container logs
docker logs atlas-commands-mcp
```

### Issue 2: MCP Connection Failures
```bash
# Restart MCP server
docker restart atlas-commands-mcp

# Clear caches
./atlas-mcp-quick-fix.sh

# Test basic connectivity
python mcp-client-working.py list-tools
```

### Issue 3: Tool Call Errors
```bash
# Check parameter validation
# Review tool schemas in mcp.json
# Verify required fields are provided

# Check storage permissions
docker exec atlas-commands-mcp ls -la /app/REPOS
```

### Issue 4: Performance Issues
```bash
# Clear ML model cache
docker exec atlas-commands-mcp python -c "from atlas_commands.caching.cache_manager import CacheManager; CacheManager.clear_all_cache()"

# Restart with fresh cache
docker-compose restart atlas-commands
```

## Success Criteria

### Minimum Viable Integration ✓
- [ ] All 49 tools callable from Claude Code
- [ ] Basic task creation and management works
- [ ] Memory graph operations functional
- [ ] No data loss between sessions
- [ ] Response times < 5 seconds

### Full Feature Integration ✓
- [ ] All test categories pass (>90% success rate)
- [ ] Performance within acceptable limits (<3s per tool call)
- [ ] Error recovery mechanisms work
- [ ] Integration workflows complete successfully
- [ ] ML recommendations provide value

### Production Readiness ✓
- [ ] Stress testing with concurrent operations
- [ ] Data backup and recovery verified
- [ ] Monitoring and alerting functional
- [ ] Documentation complete and accurate
- [ ] Claude Code seamless integration

## Rollback Procedure

If tests fail consistently:

```bash
# 1. Stop containers
docker-compose down

# 2. Revert to known good configuration
git checkout HEAD~1 -- docker-compose.yml src/

# 3. Rebuild with stable version
docker-compose build
docker-compose up -d

# 4. Re-run basic tests
python test-runner.py --quick
```

## Next Session Preparation

### Files to Review
- `atlas_mcp_test_results_*.json` - Latest test results
- `atlas_mcp_tests.log` - Execution logs
- `ATLAS_MCP_INTERACTION_TESTS.md` - Test specifications
- `.mcp.json` - Claude Code configuration

### Key Metrics to Track
- Test success rate percentage
- Average tool response time
- Memory usage patterns
- Cache hit/miss ratios
- Error frequency and types

### Documentation Updates Needed
- Update tool documentation based on test results
- Record any configuration changes required
- Document new issues discovered
- Update performance benchmarks

---

**Last Updated**: July 1, 2025
**Version**: 1.0.0
**Status**: Ready for execution