# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
The current development OS is MacOS, but the code should be compatible with Linux.

## Current Development Context

**Active Branch**: `development-http-microservices` (working branch)  
**Target Branch**: `production` (for PRs)  
**Current Focus**: Protocol testing framework with plugin-based architecture  
**Development Stage**: Active development with focus on stability and external plugin support

When modifying or adding code, please follow these guidelines:
Read the content of .pre-commit-config.yaml

ALWAYS FOLLOW DRY (Don't Repeat Yourself) and SOLID principles.
ALWAYS CHECK for existing functionality before implementing new features.

## Essential Development Commands

### Environment Setup (Required First)

```bash
# Create and activate virtual environment (Python 3.10+)
python3.10 -m venv .venv && source .venv/bin/activate

# Install development dependencies
pip install -e .[dev]

# Setup pre-commit hooks (mandatory)
pre-commit install
```

### Quality Assurance (Run Before Every Commit)

```bash
# Complete development validation
source .venv/bin/activate && \
pytest tests/unit/ -m "not slow" --tb=line -q && \
flake8 . --max-line-length=88 --extend-ignore=E203,W503 && \
echo "✅ Ready to commit"
```

## Feature Development Workflows

PANTHER implements comprehensive 3-phase development workflows with 17 integrated slash commands, including advanced legacy detection and technical debt management.

### Complete Feature Development Process

```bash
# Phase 1: Investigation & Planning
/pre-flight-check <task_id> --strict              # Environment validation
/breakdown-task "think about [feature_description]" # Strategic planning
/generate-modifications <task_id> --enhanced       # Precise change planning
/validate-modifications <task_id> --strict         # Pre-implementation validation

# Phase 2: Implementation & Monitoring  
/real-time-validator start                         # Start continuous monitoring
/implement-task <task_id>                          # Git-managed implementation
/sync-todos --auto                                 # Enable TODO synchronization

# Phase 3: Validation & Quality Assurance
/detect-legacy --scan-type=all --export-report     # Comprehensive legacy analysis
/validate-implementation <feature_name>            # Feature consistency validation
/real-time-validator stop                          # Stop monitoring
```

### Workflow Decision Matrix

| Task Type | Commands | Thinking Mode | Monitoring |
|-----------|----------|---------------|------------|
| **Simple Bug Fix** | `/implement-task` | None | Basic |
| **New Plugin** | `/plugin-development` → `/implement-task` | `think` | Medium |
| **Feature Addition** | Full 3-phase workflow | `think hard` | High |
| **Architecture Change** | Full workflow + validation | `think harder` | Maximum |

## Strategic Thinking Modes

### Thinking Mode Activation

- **`"think"`** - Basic extended thinking for planning and analysis
- **`"think hard"`** - Deeper analysis for complex problems  
- **`"think harder"`** - Advanced reasoning for architectural decisions
- **`"ultrathink"`** - Maximum computational depth for critical analysis

### Workflow Integration Examples

```bash
# Feature development with progressive thinking
/breakdown-task "think about implementing new metrics collection"
/generate-modifications TASK_001 --enhanced  # Uses "think hard" internally
/implement-task TASK_001                     # Uses "think" for strategy

# Complex refactoring with elevated thinking
/breakdown-task "think harder about refactoring command processor"
/validate-implementation "think harder about architectural consistency"

# Critical system analysis
/breakdown-task "ultrathink about systematic approach to eliminate code duplication"
```

## Claude Code Slash Commands

### Available Commands (17 Total)

#### Core Workflow Commands
- **`/run-experiment`** - Execute experiments with MCP quality analysis
- **`/validate-config`** - Configuration validation with security scanning
- **`/clean-docker`** - Docker resource cleanup with security checks
- **`/analyze-results`** - Experiment result analysis with MCP integration

#### Task Management & Planning Commands  
- **`/breakdown-task`** - Strategic task breakdown with thinking modes
- **`/plugin-development`** - Isolated plugin development guide
- **`/todo-manager`** - Smart TODO management with auto-detection
- **`/sync-todos`** - Automatic TODO synchronization with Git commits

#### Implementation & Validation Commands
- **`/pre-flight-check`** - Comprehensive pre-task validation (includes legacy detection)
- **`/generate-modifications`** - Precise line-level change planning
- **`/validate-modifications`** - Pre-implementation validation  
- **`/implement-task`** - Git-managed implementation with branch automation
- **`/validate-implementation`** - Feature consistency validation with legacy analysis

#### Quality Assurance & Legacy Detection Commands
- **`/detect-legacy`** - Comprehensive legacy code and technical debt detection
- **`/real-time-validator`** - Continuous monitoring with real-time alerts
- **`/mcp-integration`** - Complete MCP tools usage guide

### Quick Usage Examples

```bash
# Complete feature workflow (recommended)
/pre-flight-check new_feature --strict
/breakdown-task "think hard about implementing comprehensive metrics"
/generate-modifications TASK_001 --enhanced-templates
/real-time-validator start
/implement-task TASK_001
/validate-implementation new_feature

# Plugin development (external developers)
/plugin-development
/implement-task TASK_002

# Quality improvement workflow with legacy detection
/detect-legacy --scan-type=all --fix-suggestions --export-report
/todo-manager create "Fix performance issue" --priority high
/sync-todos --auto
/real-time-validator start --watch-paths=panther/core/

# Legacy code analysis workflow
/detect-legacy --scan-type=duplications --threshold=0.9
/detect-legacy --scan-type=comments --export-report
/validate-implementation command_processor --check-legacy
```

### Command Features

- **Advanced MCP Integration**: All commands integrate with Codacy, Refactor Graph, Memory, and Sequential Thinking MCP servers
- **Legacy Detection**: Comprehensive technical debt analysis with function similarity detection and refactoring recommendations
- **Quality Gates**: Automated flake8, security validation, and advanced refactoring analysis with real-time monitoring
- **Error Prevention**: Pre-flight validation, legacy detection, context checking, and conflict detection
- **Smart Automation**: Automatic TODO synchronization, background monitoring, and refactoring opportunity identification
- **Command Chaining**: Seamless integration between commands for optimal workflows with progressive quality improvement

## MCP Server Integration

PANTHER integrates with **4 MCP servers** for enhanced development workflows:

1. **Codacy MCP Server** - Code quality and security analysis
   - **Always use**: provider: `gh`, organization: `ElNiak`, repository: `PANTHER`
   - **Integrated in**: `/real-time-validator`, `/pre-flight-check`, `/validate-modifications`

2. **Refactor Graph MCP Server** - Advanced function similarity and refactoring analysis
   - **Advanced similarity detection** with configurable thresholds
   - **Argument count mismatch detection** for API consistency
   - **Integrated in**: `/detect-legacy`, `/pre-flight-check`, `/validate-implementation`

3. **Memory MCP Server** - Knowledge graph for development patterns
   - **Used by**: `/todo-manager`, `/sync-todos`, `/validate-implementation`
   - **Automatic pattern recognition** and completion tracking

4. **Sequential Thinking MCP Server** - Complex problem analysis
   - **Embedded in all workflow commands** with appropriate thinking modes
   - **Progressive thinking escalation** from "think" to "ultrathink"

### MCP Integration Examples

```bash
# Complete workflow with MCP integration
/pre-flight-check task --strict                    # Sequential Thinking for analysis
/breakdown-task "think hard about feature"         # Sequential Thinking + Memory
/generate-modifications TASK_001                   # Sequential + Codacy analysis
/real-time-validator start                         # Continuous Codacy monitoring
/implement-task TASK_001                           # All MCP servers integrated
/validate-implementation feature                   # Sequential + Memory analysis
```

## Legacy Code Detection and Technical Debt Management

PANTHER includes comprehensive legacy code detection using multiple MCP servers for advanced analysis:

### `/detect-legacy` Command Capabilities

```bash
# Comprehensive legacy analysis (all types)
/detect-legacy --scan-type=all --fix-suggestions --export-report

# Specific analysis types
/detect-legacy --scan-type=comments                     # TODO, FIXME, HACK detection
/detect-legacy --scan-type=functions --threshold=0.9    # Function similarity analysis
/detect-legacy --scan-type=duplications                 # Advanced refactoring opportunities
/detect-legacy --scan-type=patterns --fix-suggestions   # Anti-pattern detection
```

### Advanced Refactoring Analysis

The system leverages **Refactor Graph MCP** for sophisticated analysis:

- **Function Similarity Detection**: Identifies functions with >80% similarity for potential consolidation
- **Argument Count Mismatches**: Detects API inconsistencies across similar function calls
- **Refactoring Opportunities**: Provides concrete recommendations for base class extraction
- **Complexity Metrics**: Analyzes cyclomatic complexity and suggests improvements

### Automated Quality Gates

Legacy detection is integrated into workflow commands:

```bash
# Pre-flight check includes legacy analysis
/pre-flight-check TASK_001 --strict    # Includes legacy debt assessment

# Feature validation with legacy pattern checking
/validate-implementation feature_name --check-legacy --check-duplications

# Real-time monitoring includes similarity detection
/real-time-validator start --legacy-threshold=0.85
```

### Technical Debt Reporting

Generates comprehensive reports:
- **JSON Reports**: Machine-readable analysis for CI/CD integration
- **Markdown Summaries**: Human-readable recommendations with priority levels
- **Consolidated Reports**: Multi-analysis summaries with actionable next steps
- **Memory Integration**: Tracks improvements and pattern evolution over time

## External Developer Plugin Workflow

PANTHER supports **isolated plugin development** for external contributors:

### Quick Start for External Developers

1. **Use the plugin development command**: `/plugin-development`
2. **Key principles**: Zero core modifications, inherit from base classes, follow isolation
3. **Workflow**: `/plugin-development` → `/breakdown-task` → `/implement-task`

### Plugin Development Isolation

External developers should ONLY modify:
```
panther/plugins/services/iut/[protocol]/[your_implementation]/
├── __init__.py
├── config_schema.py  
├── [your_implementation].py
├── Dockerfile
└── README.md
```

**Never touch**: Core PANTHER files, base classes, other plugins, configuration managers

## Development Best Practices

### Enhanced Workflow Requirements

1. **Always Use Enhanced Workflows**: Start with `/pre-flight-check` and `/breakdown-task`
2. **Follow Plugin Philosophy**: External developers use isolation, core team uses full workflow
3. **Quality Gates Are Mandatory**: Run flake8, use MCP scanning, address Critical/High issues
4. **Git Branch Management**: Use `/implement-task` for automatic branch creation
5. **Task Tracking**: Use `/generate-modifications` and `/validate-modifications`
6. **Enable Automation**: Use `/sync-todos --auto` and `/real-time-validator`

### MCP Integration Requirements

All development MUST use MCP tools:
- **Codacy MCP**: Continuous quality monitoring with automatic analysis
- **Memory MCP**: Pattern recognition and completion tracking  
- **Sequential Thinking MCP**: Progressive thinking escalation in all commands

### Quality Assurance

```bash
# Before implementation
/pre-flight-check <task_id> --strict --auto-fix

# During implementation  
/real-time-validator alerts

# After implementation
/validate-implementation <feature> --detect-improvements
```

## Quick Reference

### Essential Commands

```bash
# Virtual Environment (Required)
python3.10 -m venv .venv && source .venv/bin/activate

# Basic Experiment
/run-experiment experiment-config/experiment_config_example_minimal.yaml

# Configuration Validation
/validate-config config.yaml

# Plugin Development
/plugin-development  # External developers
/breakdown-task "Add new feature"  # Core team

# Docker Cleanup
/clean-docker all
```

### Basic Configuration

**For quiet experiments (recommended)**:
```yaml
logging:
  level: ERROR
observers:
  logger:
    log_level: "ERROR"
```

**For debugging**:
```yaml
logging:
  level: DEBUG
observers:
  logger:
    log_level: "DEBUG"
```

## Important Guidelines

**NEVER create files unless explicitly required for your task.**
**ALWAYS prefer editing existing files to creating new ones.**
**NEVER proactively create documentation files (*.md) or README files unless explicitly requested.**

These guidelines ensure PANTHER maintains code quality, architectural consistency, and supports both core development and external plugin contributions effectively.

---

## Summary: Enhanced PANTHER Development

PANTHER provides a comprehensive, automated development experience through **16 integrated slash commands** with **3-phase workflows**, **4 thinking modes**, and **3 MCP servers** for unparalleled workflow automation, error prevention, and quality assurance.

**Quick Start**: `/pre-flight-check` → `/breakdown-task` → `/generate-modifications` → `/implement-task` → `/validate-implementation`