# Fix ivyc Staging Path for MCP ivy_compile Tool

**Date:** 2026-04-10
**Scope:** `ivy_lsp/core/verification.py` in the `ivy-lsp` submodule

## Problem

The `ivy_compile` MCP tool passes the full absolute resolved path to `ivyc`. When layer-specific staging is active, `resolve_staging_path` returns paths like `/var/folders/.../ivy-lsp-stage-.../layer_bgp/bgp_speaker_test_accept.ivy`. ivyc derives its output basename from the input argument, producing:

```
builddir + '/' + basename + '.h'
= '.' + '/' + '/var/folders/.../layer_bgp/bgp_speaker_test_accept' + '.h'
= './/var/folders/.../layer_bgp/bgp_speaker_test_accept.h'
```

This path is invalid because `builddir` (`.`) is prepended to an absolute path.

## Root Cause

`run_ivy_compile` (line 154) appends the full `resolved` path to the ivyc command, even though CWD is already set to `os.path.dirname(resolved)`. ivyc should receive just the filename since it resolves relative to CWD.

Secondary issue: the staging directory has no `build/` subdirectory, so ivyc falls back to `builddir = '.'`, mixing output with staging symlinks.

## Fix

In `run_ivy_compile` (`ivy_lsp/core/verification.py:132-186`):

1. After resolving the staging path, create a `build/` directory inside the CWD:
   ```python
   cwd = os.path.dirname(resolved)
   os.makedirs(os.path.join(cwd, "build"), exist_ok=True)
   ```

2. Pass only the basename to ivyc:
   ```python
   cmd.append(os.path.basename(resolved))
   ```

This produces `build/bgp_speaker_test_accept.h` — matching Docker compilation behavior.

Apply the same basename fix to `run_ivy_check` (line 99) and `run_ivy_show` for consistency, since they also pass the full resolved path. No `build/` directory needed for those tools (they don't write output files).

## Verification

After the fix, `ivy_compile(relative_path="protocol-testing/bgp/bgp_tests/speaker_tests/bgp_speaker_test_accept.ivy", target="test")` should either succeed or fail with an Ivy-level error (not a FileNotFoundError).
