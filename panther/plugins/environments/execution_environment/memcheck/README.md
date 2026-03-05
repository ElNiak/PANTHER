# Memcheck Execution Environment Plugin

> **Plugin Type**: Execution Environment
> **Source Location**: `plugins/environments/execution_environment/memcheck/`

## Overview

The Memcheck Execution Environment plugin integrates Valgrind's Memcheck tool into the PANTHER testing framework. Memcheck is a memory error detector that helps find memory leaks, use of uninitialized memory, invalid memory access, and other memory-related issues in programs.

> [!WARNING]
> "Performance Impact"
> Memcheck significantly slows down program execution (10-30x slower) and increases memory usage. Use only for debugging and testing scenarios, not performance benchmarking.

## Configuration Options

All fields from `MemcheckConfig` (inherits `ExecutionEnvironmentPluginConfig` and `BasePluginConfig`):

### Inherited Fields

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | `bool` | `true` | Whether the plugin is enabled (inherited from `BasePluginConfig`) |
| `version` | `Optional[str]` | `None` | Plugin version (inherited from `BasePluginConfig`) |
| `priority` | `int` | `100` | Plugin execution priority (inherited from `BasePluginConfig`) |
| `output_format` | `str` | `"json"` | Output format for results (inherited from `ExecutionEnvironmentPluginConfig`; overridden to `"xml"` in MemcheckConfig) |
| `collect_metrics` | `bool` | `true` | Whether to collect metrics (inherited from `ExecutionEnvironmentPluginConfig`) |

### Plugin Identity

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | `str` | `"memcheck"` | Execution environment type identifier. Do not change. |

### Leak Detection Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `leak_check` | `str` | `"summary"` | Search for memory leaks when the client program finishes. Options: `no`, `summary`, `yes`, `full`. `summary` gives a count per leak kind; `full` lists each individual leak in detail. |
| `leak_resolution` | `str` | `"high"` | How strictly Memcheck merges multiple leaks into a single report based on call-stack similarity. Options: `low` (aggressive merging), `med`, `high` (least merging, most detail). |
| `show_leak_kinds` | `str` | `"definite,possible"` | Comma-separated leak kinds to display in a full leak search. Values: `definite`, `indirect`, `possible`, `reachable`, `all`, `none`. |
| `errors_for_leak_kinds` | `str` | `"definite,possible"` | Comma-separated leak kinds to count as errors (affecting the exit code). Same values as `show_leak_kinds`. |
| `leak_check_heuristics` | `str` | `"all"` | Comma-separated heuristics for identifying interior pointers to heap blocks. Values: `stdstring`, `length64`, `newarray`, `multipleinheritance`, `all`, `none`. |
| `show_reachable` | `Optional[str]` | `None` | Alternative way to control display of reachable blocks. Values: `yes`, `no`. When set, overrides `show_leak_kinds` for the `reachable` category. |
| `show_possibly_lost` | `Optional[str]` | `None` | Alternative way to control display of possibly-lost blocks. Values: `yes`, `no`. When set, overrides `show_leak_kinds` for the `possible` category. |
| `xtree_leak` | `bool` | `false` | Output leak search results as a Callgrind-format execution tree file, viewable in KCachegrind. |
| `xtree_leak_file` | `str` | `"xtleak.kcg.%p"` | Filename for the xtree leak report. The `%p` placeholder is replaced with the process PID. |

### Undefined Value Detection Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `undef_value_errors` | `bool` | `true` | Report uses of undefined (uninitialized) value errors. Disable to reduce noise when only leak checking is needed. |
| `track_origins` | `bool` | `false` | Track the origin of uninitialized values back to their point of creation. Increases memory overhead (~100 MB) and slows execution (~1.5x), but produces more actionable error reports. |
| `partial_loads_ok` | `bool` | `true` | Allow partial loads from addresses where some bytes are addressable and others are not. Set to `false` for stricter checking. |
| `expensive_definedness_checks` | `str` | `"auto"` | Use more precise but expensive instrumentation for bit-level definedness tracking. Options: `no` (fastest), `auto` (Valgrind decides), `yes` (most precise). |

### Stack Trace and Free-List Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `keep_stacktraces` | `str` | `"alloc-and-free"` | Which stack traces to keep for malloc'd/free'd blocks. Options: `alloc`, `free`, `alloc-and-free` (both), `alloc-then-free` (alloc until free), `none`. More traces use more memory but give better error context. |
| `freelist_vol` | `int` | `20000000` | Maximum total size in bytes of blocks in the free queue. Larger values delay actual deallocation, increasing the chance of detecting dangling-pointer accesses. Default: ~20 MB. |
| `freelist_big_blocks` | `int` | `1000000` | Size threshold in bytes above which freed blocks are prioritized for retention in the free queue. Default: ~1 MB. |

### Compatibility and Edge-Case Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `workaround_gcc296_bugs` | `bool` | `false` | Assume some reads/writes below the stack pointer are due to GCC 2.96 bugs rather than real errors. Only needed for very old compiled code. |
| `ignore_range_below_sp` | `Optional[str]` | `None` | Range of offsets below the stack pointer to ignore, as `<size>-<delta>`. Example: `8192-8189`. |
| `show_mismatched_frees` | `bool` | `true` | Report when heap blocks are deallocated with a function that does not match the allocator (e.g., malloc/delete mismatch). |
| `show_realloc_size_zero` | `bool` | `true` | Report calls to `realloc()` with size zero, which is implementation-defined behavior. |
| `ignore_ranges` | `Optional[str]` | `None` | Comma-separated address ranges to exclude from checking. Format: `0xPP-0xQQ,0xRR-0xSS`. |
| `malloc_fill` | `Optional[str]` | `None` | Fill newly malloc'd blocks with this byte value (hex, e.g. `0xAA`). Useful for detecting use of uninitialized heap memory. |
| `free_fill` | `Optional[str]` | `None` | Fill freed blocks with this byte value (hex, e.g. `0xBB`). Useful for detecting use-after-free. |

### Output Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_format` | `str` | `"xml"` | Output format for Memcheck reports. Options: `text` (human-readable), `xml` (machine-parseable). |
| `generate_suppressions` | `bool` | `false` | Generate suppression entries for each detected error. Useful for building a suppression file to filter known issues in subsequent runs. |
| `suppression_file` | `Optional[str]` | `None` | Path to a Valgrind suppression file (`.supp`) to ignore known issues. Can be absolute or relative to the working directory. |
| `xml_user_comment` | `Optional[str]` | `None` | Arbitrary user comment embedded in XML output. Useful for tagging runs with test identifiers or build versions. |

### Additional CLI Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `additional_parameters` | `List[str]` | `[]` | Additional command-line parameters passed verbatim to `valgrind --tool=memcheck`. Example: `['--vgdb=yes', '--vgdb-error=0']`. |

<!-- src: config_schema.py -->

## Usage Example

```yaml
execution_environments:
  - type: memcheck
    leak_check: full
    track_origins: true
    show_leak_kinds: definite,possible,indirect
    output_format: xml
    suppression_file: /path/to/suppressions.supp
```

## Integration

- **Service Managers** -- Prepends Valgrind Memcheck commands to service execution.
- **Test Framework** -- Captures and reports memory errors during test execution.
- **Result Collection** -- Memcheck logs can be included in test results.

The plugin works by prepending Valgrind Memcheck commands to the service execution chain:

```bash
valgrind --tool=memcheck --leak-check=full --track-origins=yes --show-leak-kinds=all <service-command>
```

For best results, compile applications with debug symbols (`-g` flag) and minimal optimization (`-O0`) to get detailed source code references in memory error reports.

## Troubleshooting

### Performance Degradation

Memcheck significantly slows down program execution (5-20x slower). Consider using smaller test cases or running overnight for large applications.

### False Positives

Some standard library and third-party code may trigger warnings. Create suppression files (`suppression_file` config option) for known acceptable warnings.

### Integration Problems

Compile with `-O0 -g` flags for optimal Memcheck results. Higher optimization levels may hide some memory errors.

## References

- [Valgrind Memcheck Documentation](https://valgrind.org/docs/manual/mc-manual.html)
- PANTHER Execution Environment Interface
