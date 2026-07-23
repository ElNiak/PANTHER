# BGP IUT Integration & ivy_compile Native Fix

**Date:** 2026-04-10
**Status:** Draft
**Scope:** Two independent deliverables — (1) fix `ivy_compile` MCP tool for native compilation, (2) create PANTHER BGP integration with MCP wrapper tool

---

## Piece 1: Fix `ivy_compile` Native Execution

### Problem

The `ivy_compile` MCP tool fails when invoked natively (outside Docker) because:

1. **Broken guard check** — `verification.py:250` references `ctx.docker_image`, an attribute that does not exist on `ToolContext`. This causes the tool to bail early whenever `ivyc` is not on PATH.
2. **Missing Z3 paths** — `ivyc` generates C++ that includes `<z3++.h>` and links against `libz3`. The native subprocess inherits no `Z3DIR` environment variable, so the C++ compiler cannot find Z3 headers even when Z3 is installed (e.g., via Homebrew at `/opt/homebrew/opt/z3`).
3. **Missing file staging** — `ivyc` resolves `include` directives relative to its working directory and `ivy/include/1.7/`. Protocol model files (stack, utils, shims, entities) are not staged there for native compilation.

### Solution

**File: `ivy_lsp/mcp/tools/verification.py`**

Replace the guard at line 250. The corrected logic:
- If `ivyc` is on PATH → proceed to native path
- Else if `ctx.executor is not None` → proceed to Docker path
- Else → return error ("ivyc not found and no Docker executor configured")

**File: `ivy_lsp/core/environment.py` (new)**

Add `detect_z3_dir() -> Optional[str]` that checks in order:
1. `Z3DIR` environment variable (respect user override)
2. `brew --prefix z3` on macOS (subprocess call, cached)
3. `/usr/local/include/z3++.h` existence
4. `/usr/include/z3++.h` existence

Cache result at process level (`functools.lru_cache`).

**File: `ivy_lsp/core/verification.py`, `run_ivy_compile()`**

Two changes:
1. Before calling `run_ivy_subprocess()`, inject `Z3DIR` into the environment if `detect_z3_dir()` returns a value. Extend `run_ivy_subprocess()` to accept an optional `env` dict merged with `os.environ`.
2. When `target=test`, stage protocol workspace files into Ivy's `include/1.7/` directory before compilation:
   - Walk up from the target file to find `.ivyworkspace`
   - Copy all `.ivy` files from workspace layer directories into the Ivy include dir
   - After compilation (success or failure), remove the copied files
   - Also copy the worktree's `tcp_impl.ivy` if it differs from the installed version (handles the addr-parameter refactor)

### Files Changed

| File | Change |
|------|--------|
| `ivy_lsp/mcp/tools/verification.py` | Fix guard check (~line 250) |
| `ivy_lsp/core/environment.py` | New file: `detect_z3_dir()` |
| `ivy_lsp/core/verification.py` | Inject Z3DIR env, add staging logic (`run_ivy_subprocess` already accepts `env` param) |

### Validation

- `ivy_compile(relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_join.ivy", target="test")` produces a binary
- `ivy_compile` on a QUIC test file also works (regression check)
- Staged files are cleaned up after compilation

---

## Piece 2: PANTHER BGP Integration + MCP Wrapper

### Problem

The BGP Ivy model compiles and produces test binaries, but there is no way to run them against a real BGP implementation through PANTHER's experiment pipeline. PANTHER needs a BGP protocol registration, an IUT plugin (FRRouting), Ivy tester BGP support, and an experiment config.

### Architecture

Two layers:
1. **PANTHER plugin infrastructure** — makes `panther run` work for BGP experiments
2. **MCP `ivy_iut_test` tool** — thin wrapper that generates experiment configs and invokes `panther run`

### Layer A: PANTHER BGP Plugin Infrastructure

#### A1. BGP Protocol Registration

**File: `panther/plugins/protocols/client_server/bgp/__init__.py`** (empty)
**File: `panther/plugins/protocols/client_server/bgp/bgp.py`**

```python
@register_protocol(
    name="bgp",
    type="client_server",
    versions=["rfc4271"],
    default_version="rfc4271",
    description="BGP-4 path-vector routing protocol (RFC 4271)",
    capabilities=["route-advertisement", "as-path", "communities", "fsm"],
    tags=["routing", "tcp"],
    default_config={"port": 179, "hold_time": 180, "version": 4},
)
class BGPProtocol(IProtocolManager):
    ...
```

Default port 179. Methods: `validate_config()`, `load_config()`, `get_version_parameters()`, `get_default_server_port() -> 179`.

#### A2. FRRouting IUT Plugin

**Directory: `panther/plugins/services/iut/bgp/frr_bgp/`**

| File | Purpose | Est. Lines |
|------|---------|-----------|
| `__init__.py` | Package marker | 1 |
| `frr_bgp.py` | Service manager with `@register_plugin` | ~100 |
| `config_schema.py` | Pydantic model: AS number, router ID, neighbor config | ~60 |
| `Dockerfile` | FROM `frrouting/frr:10.2.1`, copies config templates | ~15 |
| `version_configs/rfc4271.yaml` | Parameters: AS, router ID, port, neighbor, hold timer | ~50 |
| `templates/server_command.jinja` | Renders bgpd startup command | ~5 |
| `templates/bgpd.conf.jinja` | FRR config: router bgp, neighbor statements | ~20 |

The plugin uses the same 6-class mixin chain as `ping_pong`: `IUTServiceManagerMixin`, `ServiceManagerDockerMixin`, `IUTManagerEventMixin`, `ErrorHandlerMixin`, `IImplementationManager`, `StringRepresentationMixin`. Key behavior:
- `generate_run_command()` starts `bgpd` with a generated `bgpd.conf`
- `bgpd.conf` is templated from version_config parameters, with neighbor IP resolved from `@{ivy_tester:ip:decimal}` placeholder
- Docker image uses `frrouting/frr:10.2.1` (pinned for reproducibility, official, multi-arch)

FRR `bgpd.conf` template:
```
router bgp {{ as_number }}
  bgp router-id {{ router_id }}
  neighbor {{ neighbor_ip }} remote-as {{ neighbor_as }}
  neighbor {{ neighbor_ip }} timers {{ hold_time }} {{ keepalive_time }}
```

#### A3. Ivy Tester BGP Support

**File: `panther/plugins/services/testers/panther_ivy/panther_ivy.py`**

Add `"bgp"` to `supported_protocols` list (line ~59).

**File: `panther/plugins/services/testers/panther_ivy/version_configs/bgp/rfc4271.yaml`**

Follows the same structure as `version_configs/quic/rfc9000.yaml`. The placeholder format is `@{role_service:ip:decimal}` (e.g., `@{server_service:ip:decimal}`), resolved by `IvyNetworkResolutionMixin` at runtime. BGP's Ivy model expects hex IP addresses (`0x0a000001`), but the resolution system only supports `decimal` format. A hex format specifier (`@{role_service:ip:hex}`) must be added to `IvyNetworkResolutionMixin`, or hex conversion must happen in the Jinja template.

```yaml
version: "rfc4271"
parameters:
  speaker_addr:
    value: "@{client_service:ip:hex}"
    description: "Ivy speaker IP address (hex)"
  speaker_id:
    value: "@{client_service:ip:hex}"
    description: "Ivy speaker BGP identifier (hex)"
  speaker_as:
    value: "1"
    description: "Ivy speaker AS number"
  speaker_impl_addr:
    value: "@{server_service:ip:hex}"
    description: "IUT speaker IP address (hex)"
  speaker_impl_id:
    value: "@{server_service:ip:hex}"
    description: "IUT speaker BGP identifier (hex)"
  speaker_impl_as:
    value: "2"
    description: "IUT speaker AS number"
server:
  binary:
    dir: "PANTHER_IVY_INSTALL_DIR/protocol-testing/"
    name: "bgp_speaker_test_accept"
client:
  binary:
    dir: "PANTHER_IVY_INSTALL_DIR/protocol-testing/"
    name: "bgp_speaker_test_join"
```

**Files: `panther/plugins/services/testers/panther_ivy/templates/bgp/client_command.jinja` and `server_command.jinja`**

Render the test binary parameter arguments (flat variables, no `params.` prefix — matching the QUIC template pattern):
```jinja
speaker_addr={{ speaker_addr }} speaker_id={{ speaker_id }} speaker_as={{ speaker_as }} speaker_impl_addr={{ speaker_impl_addr }} speaker_impl_id={{ speaker_impl_id }} speaker_impl_as={{ speaker_impl_as }}
```

#### A4. Experiment Config

**File: `experiment-config/protocols/bgp/experiment_config_bgp.yaml`**

```yaml
logging:
  level: INFO
paths:
  output_dir: "outputs"
  plugin_dir: "panther/plugins"
docker:
  force_build_docker_image: false
  use_buildx: true
tests:
  - name: "BGP Session Establishment (Join)"
    network_environment:
      type: docker_compose
    iterations: 1
    services:
      frr_router:
        name: frr_router
        timeout: 60
        implementation:
          name: frr_bgp
          type: iut
        protocol:
          name: bgp
          version: rfc4271
          role: server
        ports:
          - "179:179"
      ivy_tester:
        name: ivy_tester
        timeout: 60
        implementation:
          name: panther_ivy
          type: testers
          test: bgp_speaker_test_join
        protocol:
          name: bgp
          version: rfc4271
          role: client
          target: frr_router
```

### Layer B: MCP `ivy_iut_test` Tool

**File: `ivy_lsp/mcp/tools/iut_testing.py` (new)**

Registered via `register_iut_testing_tools()` in the MCP server startup.

**Parameters:**
```
ivy_iut_test(
    protocol: str           # "bgp", "quic"
    test_name: str          # "bgp_speaker_test_join"
    iut_name: str           # "frr_bgp" — registered IUT plugin
    version: str = None     # defaults to protocol's default
    timeout: int = 120      # seconds
    extra_params: dict = {} # override version_config values
)
```

**Execution flow:**
1. Validate that `protocol`, `iut_name` are registered PANTHER plugins
2. Generate a temporary experiment YAML in `$TMPDIR/ivy-iut-{uuid}/config.yaml`
3. Invoke `panther run --config <temp_config>` as a subprocess with `timeout`
4. Parse PANTHER's output directory (`outputs/<date>/<experiment_id>/`) for:
   - Ivy test verdict (from tester service logs)
   - IUT logs
   - Compilation artifacts
5. Clean up temp config
6. Return structured result:
   ```json
   {
     "verdict": "pass|fail|error|timeout",
     "test_name": "bgp_speaker_test_join",
     "iut_name": "frr_bgp",
     "protocol": "bgp",
     "test_stdout": "...",
     "test_stderr": "...",
     "iut_logs": "...",
     "duration_seconds": 12.3,
     "output_dir": "outputs/2026-04-10/...",
     "error": null
   }
   ```

### File Summary

| # | File | Layer | New/Modified |
|---|------|-------|-------------|
| 1 | `ivy_lsp/mcp/tools/verification.py` | Piece 1 | Modified |
| 2 | `ivy_lsp/core/environment.py` | Piece 1 | New |
| 3 | `ivy_lsp/core/verification.py` | Piece 1 | Modified |
| 4 | `panther/plugins/protocols/client_server/bgp/__init__.py` | A1 | New |
| 5 | `panther/plugins/protocols/client_server/bgp/bgp.py` | A1 | New |
| 6 | `panther/plugins/services/iut/bgp/__init__.py` | A2 | New |
| 7 | `panther/plugins/services/iut/bgp/frr_bgp/__init__.py` | A2 | New |
| 8 | `panther/plugins/services/iut/bgp/frr_bgp/frr_bgp.py` | A2 | New |
| 9 | `panther/plugins/services/iut/bgp/frr_bgp/config_schema.py` | A2 | New |
| 10 | `panther/plugins/services/iut/bgp/frr_bgp/Dockerfile` | A2 | New |
| 11 | `panther/plugins/services/iut/bgp/frr_bgp/version_configs/rfc4271.yaml` | A2 | New |
| 12 | `panther/plugins/services/iut/bgp/frr_bgp/templates/server_command.jinja` | A2 | New |
| 13 | `panther/plugins/services/iut/bgp/frr_bgp/templates/bgpd.conf.jinja` | A2 | New |
| 14 | `panther/plugins/services/testers/panther_ivy/panther_ivy.py` | A3 | Modified |
| 15 | `panther/plugins/services/testers/panther_ivy/ivy_network_resolution_mixin.py` | A3 | Modified (add hex format specifier) |
| 16 | `panther/plugins/services/testers/panther_ivy/version_configs/bgp/rfc4271.yaml` | A3 | New |
| 17 | `panther/plugins/services/testers/panther_ivy/templates/bgp/client_command.jinja` | A3 | New |
| 18 | `panther/plugins/services/testers/panther_ivy/templates/bgp/server_command.jinja` | A3 | New |
| 19 | `experiment-config/protocols/bgp/experiment_config_bgp.yaml` | A4 | New |
| 20 | `ivy_lsp/mcp/tools/iut_testing.py` | B | New |
| 21 | `ivy_lsp/mcp/tools/__init__.py` | B | Modified (add `register_iut_testing_tools` call) |

### Dependencies

- Piece 1 is independent, can be implemented first
- Layer A (PANTHER plugins) is independent of Piece 1 (Docker compilation doesn't need native Z3)
- Layer B (MCP wrapper) depends on Layer A (needs registered plugins to generate configs)
- Both pieces must be tested: Piece 1 via MCP tool call, Piece 2 via `panther run` then MCP tool call

### Risks

- **FRR Docker image compatibility:** The `frrouting/frr:latest` image may have different config syntax across versions. Pin to a specific tag (e.g., `frrouting/frr:10.2.1`) in the version config.
- **ARM/Apple Silicon:** FRR Docker images are multi-arch, so this should work. The Ivy test binary is compiled natively, so it runs on the host arch. Inside Docker (PANTHER flow), Z3 ARM issues from CLAUDE.md may apply.
- **Network placeholder resolution for BGP:** The `@{target:ip:hex}` placeholder format may need adjustment. QUIC uses `@{server_service:ip:decimal}` — verify the exact syntax in `IvyNetworkResolutionMixin`.
- **BGP port 179 is privileged:** Inside Docker this is fine (containers run as root). For native testing, the Ivy binary would need `sudo` or `CAP_NET_BIND_SERVICE`.
