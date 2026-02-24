# Phase 2 - Dispatch 3D: Config Schema Documentation Accuracy

**Agent:** doc-miner-evidence-gatherer
**Status:** COMPLETE
**Scope:** All 20 config_schema.py files + corresponding READMEs

## Summary

Comprehensive completeness matrix covering all plugin config schemas. 8 of 9 QUIC IUT plugins have ENTIRELY fabricated config tables (100% phantom fields). gperf_cpu and gperf_heap document the wrong tool entirely (GNU gperf vs gperftools). gdb has 24 fields with zero documentation (no README). Only picoquic_shadow has a substantially accurate QUIC README.

## Completeness Matrix

| Plugin | Total Own Fields | Documented | Undocumented | Phantom (README not code) | Default Mismatches |
|--------|:---:|:---:|:---:|:---:|:---:|
| **QUIC IUT Plugins** |||||
| picoquic | 7 | 0 | 7 | 3 | N/A |
| aioquic | 17 | 0 | 17 | 15 | N/A |
| lsquic | 18 | 0 | 18 | 19 | N/A |
| mvfst | 3 | 0 | 3 | 10 | N/A |
| quant | 3 | 0 | 3 | 23 | N/A |
| quic_go | 3 | 0 | 3 | 28 | N/A |
| quiche | 3 | 0 | 3 | 0 (no table) | N/A |
| quinn | 3 | 0 | 3 | 34 | N/A |
| picoquic_shadow | 4 | 7 | 0 | 0 | 0 |
| **Exec Env Plugins** |||||
| memcheck | 29 | 2 | 27 | 1 (output_file) | 0 |
| helgrind | 21 | 3 | 18 | 1 (trace_children) | 0 |
| gdb | 24 | 0 | 24 | 0 (no README) | N/A |
| gperf_cpu | 12 | 0 | 12 | 11 (GNU gperf) | N/A |
| gperf_heap | 17 | 0 | 17 | 9 (GNU gperf) | N/A |
| strace | 26 | 9 | 17 | 0 | 3 |
| iterations | 7 | 5 | 2 | 0 | 0 |
| **Network Env Plugins** |||||
| docker_compose | 12 | 5 | 7 | 1 (network_name) | 0 |
| shadow_ns | 16 | 7 | 9 | 1 (wrong name) | 1 |
| localhost_sc | 4 | 4 | 0 | 1 (inherited) | 0 |

**Totals:** 229 own fields across 19 plugins. 42 documented correctly (18.3%). 187 undocumented (81.7%). 157 phantom fields in READMEs that don't exist in code.

## Critical Anomalies

### ANOMALY 1: gperf_cpu and gperf_heap document WRONG TOOL
Both READMEs document GNU gperf (hash function generator) parameters: `input_file`, `language`, `keyword_only`, `readonly_tables`, `hash_function`. Actual plugins use Google Performance Tools (`libprofiler.so`, `libtcmalloc.so`). Every documented field is phantom.

### ANOMALY 2: 8 Standard QUIC IUTs have entirely fabricated config tables
All READMEs for picoquic, aioquic, lsquic, mvfst, quant, quic_go, quiche, quinn document fields that do not exist. Fabricated fields appear to be aspirational or copied from QUIC interop runner parameters. Actual schemas are minimal (3 fields: name, type, version sub-model) or implementation-specific (aioquic: 17, lsquic: 18).

### ANOMALY 3: memcheck phantom field `output_file`
README documents `output_file: String, default: memcheck.log`. Field does NOT exist in MemcheckConfig. Actual output control field: `output_format: str = Field(default="xml")`.

### ANOMALY 4: helgrind phantom field `trace_children`
README documents `trace_children: Boolean, default: true`. Field does NOT exist in HelgrindConfig. This is a strace field (copy-paste error).

### ANOMALY 5: strace README wrong defaults for 3 fields
- `trace_network_syscalls`: README=true, code=False
- `timeout`: README=60, code=100
- `network_focus`: README=true, code=False

### ANOMALY 6: shadow_ns wrong field name
README: `general.model_unblocked_syscall_latency`. Code: `unblocked_syscall_latency` (no `model_` prefix).

### ANOMALY 7: gdb has 24 fields with zero documentation
GdbConfig defines 24 fields across 7 logical groups. No README exists. Not listed in parent index tables.

### ANOMALY 8: Base class output_format conflicts
`ExecutionEnvironmentPluginConfig` base defines `output_format: str = "json"`. Memcheck overrides to `"xml"`, GDB to `"detailed"`, strace to `"verbose"`. No README documents this inheritance or shadowing.

## Inherited Base Fields (Reference)

| Base Class | Fields |
|------------|--------|
| BasePluginConfig | enabled, version, priority |
| ServicePluginConfig | docker_image, build_from_source, source_repository |
| ExecutionEnvironmentPluginConfig | output_format, collect_metrics |
| NetworkEnvironmentPluginConfig | network_name, subnet, enable_ipv6 |

## Issues Summary
- **Critical:** 8 anomalies (wrong tool, fabricated tables, phantom fields, missing README)
- **Major:** 187 undocumented fields across 19 plugins
- **Documentation accuracy:** 18.3% of fields correctly documented
