# Phase 1 - Dispatch 2H: Environment Plugin READMEs Consistency

**Agent:** rfc-reviewer
**Status:** COMPLETE
**Assessment:** APPROVED WITH CORRECTIONS (pending critical fixes)

## Summary

The environment plugin README corpus covers the intended plugin set but has pervasive structural divergence, significant schema inaccuracies in 4 execution environment READMEs, 2 missing registry entries in parent READMEs, and 1 completely absent README (gdb/). The gperf_cpu and gperf_heap READMEs document the wrong tool entirely (GNU gperf instead of gperftools).

## Consistency Matrix

| Check | gperf_cpu | gperf_heap | helgrind | iterations | memcheck | strace | gdb | docker_compose | localhost_sc | shadow_ns |
|-------|-----------|------------|----------|------------|----------|--------|-----|----------------|-------------|-----------|
| Purpose | PASS | PASS | PASS | PASS | PASS | PASS | MISSING | PASS | PASS | PASS |
| Config Schema | FAIL | FAIL | FAIL | PARTIAL | FAIL | PASS | MISSING | PARTIAL | PARTIAL | PARTIAL |
| Inheritance | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | MISSING | PARTIAL | PARTIAL | PARTIAL |
| Execution Effects | PARTIAL | PARTIAL | PASS | PASS | PASS | PASS | MISSING | FAIL | FAIL | FAIL |
| Examples | PASS | PASS | PASS | PASS | PASS | PASS | MISSING | PASS | PASS | PASS |
| Dependencies | PASS | PASS | FAIL | FAIL | FAIL | PASS | MISSING | PASS | PASS | PASS |

## Critical Findings

### gperf_cpu and gperf_heap: WRONG TOOL DOCUMENTED (CON-01, CON-02)
- Both READMEs document **GNU gperf** (hash function generator) fields: `input_file`, `output_file`, `language`, `readonly_tables`, `keyword_only`
- Actual implementation is **gperftools** (Google performance library) with fields like: `profiler_library`, `sampling_frequency`, `output_format`, `generate_pdf`, `pprof_options`
- The `config_schema.py` docstring explicitly warns: "This is gperftools, not GNU gperf"
- **This is the most severe factual error in the corpus**

### gdb/ Plugin: Missing README Entirely (CMP-08)
- `gdb.py` and `config_schema.py` both exist with fully functional plugin
- `GdbConfig` has 20+ fields across 7 logical groups
- Referenced by name in gperf_heap and memcheck config schemas
- Not listed in either parent index table

### gdb/ Omitted from Parent Index Tables (CMP-09)
- Missing from `environments/README.md` lines 104-118
- Missing from `execution_environment/README.md` lines 108-114
- Also missing from directory tree (alongside `iterations/`)

### helgrind Schema: 3 of 19 Fields Documented (CON-03)
- README documents: `enabled`, `history_level`, `trace_children`
- `trace_children` is a **strace field**, not helgrind (copy-paste error)
- `enabled` not in HelgrindConfig (inherited from base)
- Actual schema has 19 fields including: `valgrind_binary`, `conflict_cache_size`, `track_lockorders`, etc.

### memcheck Schema: 2 of 26+ Fields Documented (CON-04)
- README documents: `enabled`, `output_file`
- `output_file` doesn't exist in schema (actual: `output_format`)
- Usage example `output_file: "custom_memcheck.log"` would be silently ignored

### shadow_ns: Wrong Field Name (CON-06)
- README documents `model_unblocked_syscall_latency`
- Actual field: `unblocked_syscall_latency` (no `model_` prefix)
- Documented config example is non-functional

### shadow_ns: Undocumented Fields (CON-07)
- `incompatibility` (list of strings, default `["strace", "gperf"]`) - operationally significant
- `hosts` (`HostsConfig` with server/client entries)

## Moderate Findings

| Finding | Location | Category |
|---------|----------|----------|
| iterations missing `delay_between_iterations` field | iterations/README.md | CMP-11 |
| docker_compose documents `network_name` which doesn't exist in schema | docker_compose/README.md:66 | ACC-01 |
| docker_compose missing 7 monitoring/deployment fields | docker_compose/README.md | CMP-11 |
| localhost_sc documents `network_name` not in schema | localhost_sc/README.md:75 | ACC-01 |
| Emoji in heading violates CLAUDE.md no-emoji rule | execution_environment/README.md:1 | CON-03 |
| Unclosed Python code block | localhost_sc/README.md:166-188 | CON-07 |
| Duplicate source citation tag | shadow_ns/README.md:52 | MNT-02 |
| Inconsistent YAML key: `execution_environment:` vs `execution_environments:` vs `environments:` | Multiple files | CON-06 |

## Structural Issues

- No execution environment README documents the inheritance chain
- 4 different heading structures across 6 execution environment READMEs
- Network environment READMEs more consistent (all share "Docker Build Workflow" section)
- 3 of 6 exec env READMEs missing "Requirements and Dependencies" section

## Issues Summary
- **Critical:** 7 (wrong tool, missing README, schema inaccuracies)
- **Moderate:** 8 (missing fields, phantom fields, style)
- **Minor:** 5 (editorial)
