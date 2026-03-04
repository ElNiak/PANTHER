# PANTHER Suggested Commands

## System Information
- OS: Darwin (macOS)
- Standard Unix commands available: `ls`, `cd`, `grep`, `find`, `cat`, `git`, etc.

## Virtual Environment (REQUIRED)
```bash
# Create and activate (must do before any development)
python -m venv .venv
source .venv/bin/activate
```

## Installation & Development
```bash
# Development install (recommended)
python panther_builder.py package-dev

# Other build commands
python panther_builder.py docs           # Build documentation
python panther_builder.py clean          # Remove build artifacts
python panther_builder.py serve-docs     # Local docs server
```

## CLI Commands (after package-dev)
```bash
panther run --config experiment.yaml     # Execute experiment
panther config validate --config x.yaml  # Validate config
panther plugins list                     # List plugins
panther tools status                     # Show tool installation status
```

## Testing
```bash
# Run tests with markers
pytest tests/ -n auto -m unit             # Fast unit tests (no external deps)
pytest tests/ -n auto -m integration     # Requires Docker
pytest tests/ -n auto -m "not slow"      # Skip slow tests
pytest tests/ -n auto --cov=panther --cov-fail-under=70  # With coverage (70% required)

# Run single test file
pytest tests/unit/test_core/test_docker_builder_tag_generation.py -v
```

## Code Quality Tools
```bash
# Formatting
black panther/                           # Format code
isort panther/                           # Sort imports

# Linting
flake8 panther/                          # Lint
mypy panther/                            # Type check
pylint panther/                          # Detailed linting

# Pre-commit
pre-commit run --all-files               # Run all hooks
pre-commit run black --all-files         # Run specific hook
```

## Git Workflow
```bash
# PR target
git checkout production                   # Main branch

# Submodules
git submodule update --init --recursive   # Initialize submodules
```

## Docker
```bash
# Check Docker
docker --version
docker compose version

# Build images (if needed manually)
docker build -f Dockerfile.buildkit -t panther:latest .
```
