# ivy_iut_test Tool Completion & Workflow Integration

**Date:** 2026-04-11
**Status:** Design approved, ready for implementation planning
**Scope:** Fix gaps in `ivy_iut_test` MCP tool, add unit tests, integrate into verify workflow, create shortcut command

---

## 1. Problem Statement

The `ivy_iut_test` MCP tool at `ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py` is a functional skeleton that generates a temp experiment config and runs `panther run` as a subprocess. It works for basic pass/fail but has five gaps that prevent it from being useful in the developer inner loop, the verify workflow, or future CI/headless pipelines:

1. `extra_params` is accepted but never passed to config generation
2. No output directory parsing — structured results in `experiment_summary.json` and `test.log` are ignored
3. No input validation — invalid protocol or IUT names produce cryptic failures
4. No way to use existing experiment configs — only generates from scratch
5. Not integrated into any plugin skill or workflow — the verify workflow stops at formal verification

## 2. Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Config strategy | Hybrid: generate from scratch by default, accept optional `config_path` | Zero-config for inner loop, power users and CI can reference curated configs |
| Output parsing depth | Structured summary: `experiment_summary.json` + `test.log` | Covers diagnostic needs without context bloat; deeper inspection via Read on output_dir |
| Output dir identification | Deterministic path (primary) + timestamp correlation (fallback) | Deterministic for generated configs (no ambiguity), timestamp for user-provided configs |
| Workflow integration | Optional Phase 5b in verify, plus standalone shortcut command | Both workflow-guided and direct access use cases |
| Skip `error_events.jsonl` | Deferred to follow-up file reads | Keeps response bounded; workflow can Read the file if needed |

## 3. Tool API

### Parameters

```
ivy_iut_test(
    protocol: str,              # "bgp", "quic", etc.
    test_name: str,             # "bgp_speaker_test_join" (no .ivy extension)
    iut_name: str,              # "frr_bgp" — registered IUT plugin
    version: str = "",          # Protocol version (default: protocol's default)
    timeout: int = 120,         # Total timeout in seconds
    extra_params: dict = None,  # Override version_config values
    config_path: str = None,    # Path to existing experiment config YAML
)
```

When `config_path` is provided, the tool reads the YAML and overrides `test_name` and `timeout` in the first test entry. `protocol` and `iut_name` are still required for the return dict but are not validated against config contents.

When `config_path` is omitted, the tool generates a config from scratch with a deterministic output directory (`outputs/ivy-iut-{run_id}/`). `extra_params` is merged into both IUT and tester service configs as `version_config_overrides`.

### Return Dict

```python
{
    "verdict": "pass|fail|error|timeout",
    "test_name": str,
    "iut_name": str,
    "protocol": str,
    "test_stdout": str,                  # last 5000 chars of subprocess stdout
    "test_stderr": str,                  # last 2000 chars of subprocess stderr
    "iut_logs": str,                     # NEW: test.log content, last 3000 chars
    "duration_seconds": float,
    "output_dir": str,                   # NEW: absolute path to experiment output
    "experiment_summary": dict | None,   # NEW: parsed experiment_summary.json
    "error": str | None,
}
```

### Input Validation

Before running, the tool checks:
1. `protocol`, `test_name`, `iut_name` are non-empty strings
2. Protocol plugin directory exists at `panther/plugins/protocols/client_server/{protocol}/`
3. IUT plugin directory exists at `panther/plugins/services/iut/{protocol}/{iut_name}/`

On validation failure, returns `{"success": False, "error": "<message>"}` with a hint listing known protocols.

Validation is skipped when `config_path` is provided (user is responsible for consistency).

## 4. Config Generation

### Generated Config (no config_path)

```yaml
logging:
  level: INFO
paths:
  output_dir: "outputs/ivy-iut-{run_id}"
  plugin_dir: "panther/plugins"
docker:
  force_build_docker_image: false
  use_buildx: true
tests:
  - name: "IUT Test: {test_name} vs {iut_name}"
    network_environment:
      type: docker_compose
    iterations: 1
    services:
      iut:
        name: iut
        timeout: {timeout}
        implementation:
          name: {iut_name}
          type: iut
          version_config_overrides: {extra_params}  # only if extra_params provided
        protocol:
          name: {protocol}
          version: {version}  # only if version provided
          role: server
      ivy_tester:
        name: ivy_tester
        timeout: {timeout}
        implementation:
          name: panther_ivy
          type: testers
          test: {test_name}
          version_config_overrides: {extra_params}  # only if extra_params provided
        protocol:
          name: {protocol}
          version: {version}  # only if version provided
          role: client
          target: iut
```

The deterministic output dir `outputs/ivy-iut-{run_id}/` uses the same `run_id` (uuid4 first 8 chars) already generated in the code.

### User-Provided Config (config_path given)

The tool reads the YAML, finds the first test entry, and overrides:
- `tests[0].services.*.timeout` with the `timeout` parameter
- For the tester service (identified by `implementation.type == "testers"`): override `implementation.test` with `test_name`

Only the first test entry (`tests[0]`) is used. If the config has multiple tests, the rest are ignored. This is consistent with the generated config, which always has exactly one test.

The output dir is NOT overridden. The tool records `time.monotonic()` before execution and uses timestamp correlation to find the newest output directory created after that time.

Temp config is always cleaned up after execution. PANTHER output directories are NOT cleaned up.

## 5. Output Parsing

Three steps after `panther run` completes:

**Step 1 — Find output directory.**
- Generated config: look for `{root}/outputs/ivy-iut-{run_id}/`
- User config: find newest directory under `{root}/outputs/` with `st_mtime` after pre-execution timestamp
- If neither finds a directory: `output_dir` returns empty string, `experiment_summary` returns None, `iut_logs` returns empty string. The subprocess verdict is preserved.

**Step 2 — Parse experiment_summary.json.**
Load `{output_dir}/experiment_summary.json` as a dict. Include verbatim in response as `experiment_summary`. Refine the verdict using the summary's per-test status:
- Summary says "passed" → verdict = "pass"
- Summary says "failed" → verdict = "fail"
- Summary says "timeout" → verdict = "timeout"
- Summary says "error" or "unknown" → keep subprocess verdict (error or fail)
- Summary not found → keep subprocess verdict

**Step 3 — Collect test.log.**
Walk subdirectories of `output_dir`, read `test.log` from each test subdirectory. Concatenate with headers (`--- {subdir_name}/test.log ---`). Truncate to last 3000 chars.

## 6. Verify Workflow Integration

### Phase 5b — IUT Testing (optional)

Added to `skills/verify/SKILL.md` after Phase 4 (Execute via `ivy_verify`).

**Trigger:** After formal verification passes (Phase 4 verdict = PASS), the workflow offers:

> "Formal verification passed. Want to run this test against a real implementation?"

If user declines → proceed to existing completion flow (return to navigate).

If user accepts:

1. **IUT selection.** Scan `panther/plugins/services/iut/{protocol}/` for available IUT plugin directories. Present as options. If only one IUT exists, suggest it directly.
2. **Execute.** Call `ivy_iut_test(protocol=<detected>, test_name=<from Phase 2>, iut_name=<selected>)`.
3. **Result handling:**
   - Pass: report success, show duration, offer follow-ups (run another test, review coverage)
   - Fail: present `iut_logs` and `experiment_summary` for diagnosis. Show `output_dir` path for deeper inspection. Offer: "Want me to investigate the failure?"
   - Error/timeout: present error details, suggest checking Docker status and IUT plugin configuration

**Skip condition:** When `invocation_depth > 0` (verify called as sub-workflow from build), Phase 5b is skipped. Build has its own quality gate.

**State update:** Update active-workflow phase to `"iut-testing"` on entry, `"iut-testing-done"` on completion.

### Shortcut Command: /nct-iut-test

New file: `commands/nct-iut-test.md`

Direct access to `ivy_iut_test` MCP tool, bypassing workflows. No workflow state management, no phase tracking.

**Usage:**
```
/nct-iut-test <protocol> <test_name> <iut_name> [version] [timeout]
```

**Behavior:**
1. Parse arguments (protocol, test_name, iut_name required; version and timeout optional)
2. Call `ivy_iut_test` with parsed arguments
3. Present results using Ivy-guided output style:
   - Verdict prominently displayed
   - Duration and output_dir
   - On failure: iut_logs content, experiment_summary test status, suggestion to inspect output_dir

## 7. CLAUDE.md Updates

Add to the plugin CLAUDE.md tool reference tables:

**Under "Analysis MCP tools":**
```
`ivy_iut_test` (run compiled Ivy test against a real IUT via PANTHER experiment pipeline)
```

**Under "Shortcut Commands":**
```
`/nct-iut-test` (ivy_iut_test), ...
```

## 8. Files Changed

| # | File | Action | What |
|---|------|--------|------|
| 1 | `ivy-lsp/ivy_lsp/mcp/tools/iut_testing.py` | Rewrite | Add config_path, extra_params passthrough, validation, output parsing, deterministic output dir |
| 2 | `ivy-lsp/tests/test_iut_testing.py` | Create | 15 unit tests with mocked subprocess |
| 3 | `panther-ivy-plugin/skills/verify/SKILL.md` | Modify | Add Phase 5b (IUT Testing) |
| 4 | `panther-ivy-plugin/commands/nct-iut-test.md` | Create | Shortcut command |
| 5 | `panther-ivy-plugin/CLAUDE.md` | Modify | Add ivy_iut_test to tool tables, /nct-iut-test to shortcuts |

**Not changed:**
- `ivy-lsp/ivy_lsp/mcp/tools/__init__.py` — registration exists, no changes needed
- `ivy_network_resolution_mixin.py` — hex IP formatting works end-to-end (verified during audit)
- `ivy-toolkit` knowledge skill — lower priority, follow-up

## 9. Test Plan

Unit tests in `ivy-lsp/tests/test_iut_testing.py`:

| Test | What it validates |
|------|------------------|
| `test_build_config_default` | Generated YAML has correct service structure |
| `test_build_config_with_extra_params` | extra_params appear in both services as version_config_overrides |
| `test_build_config_deterministic_output_dir` | output_dir path contains run_id |
| `test_validate_inputs_missing_protocol` | Returns error string for empty protocol |
| `test_validate_inputs_unknown_protocol` | Returns error with known-protocols hint |
| `test_validate_inputs_unknown_iut` | Returns error naming the expected path |
| `test_validate_inputs_valid` | Returns None for valid inputs |
| `test_refine_verdict_from_summary` | Summary status overrides subprocess verdict |
| `test_refine_verdict_no_summary` | Subprocess verdict preserved when no summary |
| `test_collect_iut_logs` | Reads test.log from subdirectory, truncates at 3000 chars |
| `test_collect_iut_logs_empty_dir` | Returns empty string for empty directory |
| `test_find_output_dir_deterministic` | Finds directory by run_id path |
| `test_find_output_dir_timestamp_fallback` | Finds newest dir after timestamp |
| `test_iut_test_panther_not_found` | Returns error when panther not on PATH |
| `test_iut_test_timeout` | Verdict is "timeout" on asyncio.TimeoutError |

## 10. Dependencies

- `panther` CLI must be installed and on PATH
- Docker must be running for IUT containers
- Protocol and IUT plugin directories must exist in PANTHER codebase
- PANTHER output directory structure must follow the current convention (`outputs/{timestamp}/` with `experiment_summary.json` and test subdirectories)
