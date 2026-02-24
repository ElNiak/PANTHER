# Phase 1 - Dispatch 2G: QUIC IUT Plugin READMEs Consistency

**Agent:** rfc-reviewer
**Status:** COMPLETE
**Assessment:** REQUIRES REVISION

## Summary

All 9 QUIC implementation READMEs have fabricated configuration tables that do not match their actual `config_schema.py` files. The quiche README is severely truncated (ends mid-document). All READMEs omit critical mixin classes from inheritance diagrams. No README has a "Known Limitations" section.

## Consistency Matrix

| Plugin | Purpose | Config Schema | Inheritance | Docker | Features | Examples | Limitations |
|--------|---------|--------------|-------------|--------|----------|----------|-------------|
| picoquic | PASS | FAIL | PARTIAL | MISSING | PARTIAL | PASS | MISSING |
| aioquic | PASS | FAIL | PARTIAL | MISSING | PASS | PASS | MISSING |
| lsquic | PASS | FAIL | PARTIAL | MISSING | PASS | PASS | MISSING |
| mvfst | PASS | FAIL | PARTIAL | PARTIAL | PARTIAL | PASS | MISSING |
| quant | PASS | FAIL | PARTIAL | MISSING | PASS | PASS | MISSING |
| quic_go | PASS | FAIL | PARTIAL | PARTIAL | PASS | PASS | MISSING |
| quiche | PASS | MISSING | PARTIAL | MISSING | MISSING | MISSING | MISSING |
| quinn | PASS | FAIL | PARTIAL | PARTIAL | PASS | PASS | MISSING |
| picoquic_shadow | PASS | FAIL | PARTIAL | MISSING | PARTIAL | PASS | MISSING |

## Critical Findings

### All 9 READMEs: Fabricated Configuration Tables (CON-02)
- **aioquic**: Documents `port`, `host`, `alpn_protocols`, `keylog_file` - NONE exist in AioquicConfig. Actual fields: `server_root`, `secrets_log`, `enable_http3`, etc.
- **lsquic**: Documents `cert_file`, `key_file`, `role`, `port` - none exist. Actual: `doc_root`, `request_path`, `library_path`, etc.
- **mvfst, quant, quic_go, quinn, picoquic_shadow**: Document elaborate typed fields that don't exist - actual schemas use VersionBase with only 5 fields (version, commit, dependencies, client, server). Runtime params live in version YAML files.
- **picoquic**: Documents `timeout`, `ports`, `generate_new_certificates` - none exist. Actual: `alpn`, `initial_rtt`, `max_stream_data`, `max_data`.

### quiche README Truncated (CMP-08)
- 158 lines, ends mid-document after "Handling Special Cases" section
- Missing: Configuration Options, Usage Examples, Features, Testing, Troubleshooting, References

### All 9 READMEs: MRO Mixins Omitted (CMP-09)
- All implementations include `IUTManagerEventMixin` and `IUTServiceManagerMixin` in class signatures
- No README documents these mixins in inheritance diagrams

### quant Missing `file_to_change/` Directory (CON-07)
- All other 8 plugins have this directory; quant does not
- Not documented as known limitation

## Structural Deviations

| Issue | Details |
|-------|---------|
| Section titles | 7 use "Purpose and Overview", 2 use "Overview" |
| YAML key format | picoquic uses correct `services: server:` pattern; others use `services: iut:` |
| Docker section | 7 of 9 missing entirely despite all having Dockerfiles |
| Features naming | "Features", "Why Choose X?", "Implementation Details", "Key Features" |
| Dev status admonition | 8 use `!!! warning`, picoquic uses `!!! info "Production"` |
| Metadata block | Inconsistent: some have `**Parent Plugin**`, some have `**Protocol**` |

## Issues Summary
- **Critical:** 11 (8 fabricated config tables + 1 truncated + 1 missing MRO + 1 missing dir)
- **Moderate:** 6 (inconsistent naming, missing Docker sections, example format)
- **Minor:** 5 (editorial)
