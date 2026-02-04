# PANTHER Task Completion Checklist

## After Completing Any Code Task

### 1. Format Code
```bash
black panther/
isort panther/
```

### 2. Run Pre-commit Hooks
```bash
pre-commit run --all-files
```
Or for specific files:
```bash
pre-commit run --files path/to/file.py
```

### 3. Run Relevant Tests
```bash
# Unit tests (fast)
pytest tests/unit/ -m "not slow" -x

# If you modified specific modules, run targeted tests
pytest tests/unit/test_core/ -v

# Full test suite before PR
pytest tests/ -m unit --cov=panther --cov-fail-under=70
```

### 4. Type Checking (Optional but Recommended)
```bash
mypy panther/path/to/modified/file.py
```

### 5. Verify Import Works
```bash
python -c "import panther; print('OK')"
```

## Before Creating a PR

1. **Ensure tests pass**: `pytest tests/ -m unit`
2. **Coverage check**: `pytest tests/ --cov=panther --cov-fail-under=70`
3. **All pre-commit hooks**: `pre-commit run --all-files`
4. **Type check (optional)**: `mypy panther/`
5. **PR target**: `production` branch

## Special Considerations

### Docker-related Changes
- Test with `pytest tests/ -m integration` (requires Docker)
- Verify Dockerfiles build correctly

### Plugin Changes
- Verify plugin registration works: `panther plugins list`
- Check config schema validation: `panther config validate --config test.yaml`

### CLI Changes
- Test CLI commands manually
- Run: `panther --help` and subcommand help

### Configuration Changes
- Validate experiment configs: `panther config validate --config experiment.yaml`
- Test with example configs in `experiment-config/`

## Files to NEVER Modify
- `panther/plugins/services/testers/panther_ivy/` - Git submodule
- `requirements.txt` - Frozen dependencies, edit pyproject.toml instead
