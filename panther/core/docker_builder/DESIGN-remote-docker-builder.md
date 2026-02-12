# Design: Remote Docker Builder Support for PANTHER

**Status**: Proposed
**Date**: 2026-02-12
**Branch**: `feature/remote-docker-builder-plan`

## Context

On Apple Silicon Macs, PANTHER builds x86_64 Docker images via QEMU emulation through `docker buildx`, which is extremely slow. A remote x86_64 Linux machine on the same LAN can build natively.

**Solution**: Use `docker buildx create --driver docker-container --platform linux/amd64 ssh://user@host` to offload Docker builds to the remote x86 machine. The remote machine builds natively (fast), then `--load` pulls the finished image back to the Mac's Docker daemon for local execution via Rosetta 2.

**Why this fits PANTHER well**: The codebase already has `buildx_builder` config, `--builder` flag (commented out in `_build_with_buildx`), and platform detection logic. The changes are surgical -- we're enabling an existing architectural pattern rather than adding a fundamentally new one.

### Performance Impact

| Action | Current (Local QEMU) | With Remote Builder |
|--------|---------------------|---------------------|
| Building x64 image | Slow (QEMU emulation) | Fast (native x64 on remote) |
| Running x64 image | Fast (Rosetta 2) | Fast (Rosetta 2) |

## Prerequisites (Manual Setup)

Before using remote builder, users must:

1. Install Docker on Linux PC: `curl -fsSL https://get.docker.com | sh`
2. Add user to docker group: `sudo usermod -aG docker $USER`
3. Setup passwordless SSH: `ssh-copy-id user@linux-pc-ip`
4. Verify: `ssh user@linux-pc-ip docker info`

## Files to Modify

| File | Changes |
|------|---------|
| `panther/config/core/models/global_config.py` | Add `RemoteBuilderConfig` sub-model, add field to `DockerConfig` |
| `panther/core/docker_builder/docker_builder.py` | ~8 methods: builder setup, buildx command, platform detection, context switching |
| `panther/core/docker_builder/utils/context_helper.py` | Add SSH validation helper, update `_recreate_builder` |
| `panther/core/docker_builder/caching/buildkit_cache_mixin.py` | Skip local cache mounts for remote builders |
| `panther/cli_click/commands/run.py` | Pass `remote_builder` key from YAML config |
| `tests/unit/test_core/test_docker_builder_remote.py` | New test file for remote builder logic |

## Implementation Steps

### Step 1: Config Schema (`global_config.py`)

Add `RemoteBuilderConfig` sub-model before `DockerConfig`:

```python
class RemoteBuilderConfig(BaseUnifiedModel):
    """Remote Docker builder configuration for SSH-based build offloading."""
    ssh_host: str = Field(..., description="SSH endpoint (e.g., 'user@host')")
    platform: str = Field("linux/amd64", description="Remote builder platform")
    builder_name: Optional[str] = Field(None, description="Custom builder name. Auto-generated if not set.")
    image_transfer: str = Field(
        "load",
        description="How to transfer built images: 'load' (pull back via SSH, default) or 'push' (push to registry, requires docker.registry)"
    )

    @field_validator("ssh_host", mode="before")
    def normalize_ssh_host(cls, v):
        if v and not v.startswith("ssh://"):
            v = f"ssh://{v}"
        return v

    @field_validator("image_transfer", mode="before")
    def validate_image_transfer(cls, v):
        if v not in ("load", "push"):
            raise ValueError("image_transfer must be 'load' or 'push'")
        return v
```

Add to `DockerConfig`:

```python
remote_builder: Optional[RemoteBuilderConfig] = Field(
    None, description="Remote Docker builder for SSH-based build offloading (single builder)"
)
```

### Step 2: CLI Passthrough (`run.py`)

Line ~313 - add `"remote_builder"` to the list of forwarded docker config keys:

```python
for key in ["user_mapping", "build_args", "network_mode", "buildx_builder",
            "multi_platform", "target_platform", "remote_builder"]:
```

### Step 3: Helper Method (`docker_builder.py`)

Add `_get_remote_builder_config()` utility method:

```python
def _get_remote_builder_config(self):
    if (hasattr(self, "global_config") and self.global_config
            and hasattr(self.global_config, "docker")
            and getattr(self.global_config.docker, "remote_builder", None)):
        return self.global_config.docker.remote_builder
    return None
```

### Step 4: Remote Builder Setup (`docker_builder.py` - `_setup_buildx_builder`)

Extend to detect remote config and create SSH-based builder:

```bash
docker buildx create --name panther-remote-user-host \
  --driver docker-container \
  --platform linux/amd64 \
  --use \
  ssh://user@host
docker buildx inspect panther-remote-user-host --bootstrap  # validates connectivity
```

Builder name auto-generated from SSH host if not provided. Check-if-exists first (idempotent).

### Step 5: `_should_use_buildx()` - Force True for Remote Builders

Early return `True` when remote builder is configured (remote builds always use buildx, by definition).

### Step 6: `get_target_platform()` - Remote Platform Awareness

Insert check after config override but before host architecture detection: if remote builder configured, return `remote_config.platform` (e.g., `linux/amd64`). This prevents ARM64 QEMU logic from kicking in.

### Step 7: `_ensure_buildx_context()` - Skip for Remote Builders

Early return `True` - remote SSH builders are context-independent and don't need Docker CLI context reconciliation.

### Step 8: `_build_with_buildx()` - Core Build Command Changes

Four changes:
1. **Uncomment `--builder` flag** (lines 1072-1073): Include `--builder <name>` when `builder_name != "default"`
2. **Skip context switching** (lines 1127-1175): Remote builders don't need the "switch to default context" dance
3. **Fix `BUILDPLATFORM`/`BUILDARCH` build args**: When remote builder active, set to remote's platform (the actual build machine), not the Mac's
4. **`--load` vs `--push`**: When `remote_config.image_transfer == "push"` AND `docker.registry` is set, use `--push` and then `docker pull` locally. Default `"load"` uses `--load` (pull image back via SSH tunnel)

### Step 9: `validate_build_mode_for_architecture()` - Use Remote Arch

Currently checks `platform.machine()` (local Mac = arm64), which blocks advanced build modes (rel-lto, debug-asan). When remote builder is x86, allow all build modes.

### Step 10: Cache System (`buildkit_cache_mixin.py`)

In `_get_cache_mount_args()`: return empty list when remote builder is active. Local `/tmp/buildkit-cache-*` paths are meaningless on the remote machine. The remote BuildKit daemon has its own implicit layer cache.

### Step 11: Context Helper (`context_helper.py`)

Add `validate_remote_builder_ssh()` function that runs `ssh -o BatchMode=yes user@host docker info` to validate connectivity (used during builder bootstrap for better error messages).

### Step 12: Unit Tests

New file `tests/unit/test_core/test_docker_builder_remote.py`:
- Config validation (ssh_host normalization, defaults)
- `_get_remote_builder_config()` returns None vs config
- Builder setup constructs correct `docker buildx create` command
- `get_target_platform()` returns remote platform
- `_should_use_buildx()` returns True for remote builders
- `validate_build_mode_for_architecture()` allows advanced modes
- Cache args empty for remote builders
- Builder name auto-generation

## YAML Configuration Examples

**Basic (--load, recommended for LAN)**:
```yaml
docker:
  force_build_docker_image: true
  use_buildx: true
  remote_builder:
    ssh_host: "user@192.168.1.100"
    platform: "linux/amd64"
    # builder_name: "my-builder"        # optional, auto-generated
    # image_transfer: "load"            # default: pull image back via SSH
```

**With registry (--push, for larger images or CI)**:
```yaml
docker:
  force_build_docker_image: true
  use_buildx: true
  registry: "registry.example.com"      # required when image_transfer=push
  remote_builder:
    ssh_host: "user@192.168.1.100"
    platform: "linux/amd64"
    image_transfer: "push"              # push to registry, then pull locally
```

## Edge Cases & Risks

| Risk | Mitigation |
|------|------------|
| SSH auth fails (no key) | `--bootstrap` during builder creation catches this; clear error message |
| Remote Docker not running | `validate_remote_builder_ssh()` pre-check; bootstrap validates |
| Large images slow over `--load` | Use `image_transfer: "push"` + `registry` for registry-based transfer |
| Builder name collision | Auto-generated from SSH host; deterministic = shared safely |
| Crash leaves builder | Builders are just config pointers; persist safely; BuildKit GCs on remote |
| `--network host` in buildx | Refers to remote machine's network during build; correct behavior |
| Local cache mounts pointless | Disabled for remote builders; remote BuildKit has implicit cache |

## Verification Plan

1. **Unit tests**: `pytest tests/unit/test_core/test_docker_builder_remote.py -v`
2. **Config validation**: `panther config validate --config <config-with-remote-builder>.yaml`
3. **Integration test** (requires actual remote machine):
   - Create config with `remote_builder.ssh_host` pointing to Linux PC
   - Run `panther run --config <config>.yaml`
   - Verify: builder created (`docker buildx ls`), image built on remote, loaded locally (`docker images`)
4. **Fallback test**: Remove remote_builder from config, verify standard local buildx still works unchanged
