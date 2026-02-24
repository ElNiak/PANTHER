# Phase 3 - Dispatch 4C: Documentation Style Consistency Audit

**Agent:** rfc-reviewer
**Status:** COMPLETE
**Assessment:** REQUIRES REVISION
**Scope:** 9 representative files across documentation tiers

## Summary

Substantial style fragmentation across documentation tiers. 4 of 9 files violate CLAUDE.md emoji policy. Most critical: verbatim duplicate section in CONTRIBUTING.md, complete absence of MkDocs admonitions in core module READMEs, and mirror-check failures where Memcheck README documents 2 fields against 20+ actual Pydantic model fields.

## Consistency Matrix

| File | Heading | Admonitions | Code Blocks | Links | Tables | Diataxis | Citations | Emojis |
|------|---------|-------------|-------------|-------|--------|----------|-----------|--------|
| CONTRIBUTING.md | WARN | PASS | WARN | WARN | PASS | PASS | PARTIAL | FAIL |
| command_processor/README.md | PASS | ABSENT | FAIL | ABSENT | ABSENT | PASS | ABSENT | PASS |
| docker_builder/README.md | PASS | ABSENT | FAIL | ABSENT | ABSENT | PASS | ABSENT | PASS |
| config/README.md | WARN | PARTIAL | PASS | WARN | PASS | PASS | ABSENT | FAIL |
| picoquic/README.md | PASS | PARTIAL | PASS | PASS | PASS | PASS | PASS | PASS |
| memcheck/README.md | PASS | PASS | PASS | WARN | PASS | PASS | ABSENT | PASS |
| quic_protocol/README.md | PASS | ABSENT | PASS | ABSENT | PASS | PASS | PARTIAL | PASS |
| tests/README.md | FAIL | ABSENT | PASS | ABSENT | PASS | PASS | ABSENT | FAIL |
| docs_gen/README.md | PASS | PARTIAL | PASS | PARTIAL | PASS | PASS | ABSENT | PASS |

## Critical Findings (6)

### C-1: CONTRIBUTING.md duplicate "Admonitions Usage Guide" section
- **Location:** Lines 140 and 197
- Both blocks present admonition tables and syntax examples; second is near-identical copy-paste artifact

### C-2: Memcheck README documents only 2 of 20+ config fields
- **Location:** memcheck/README.md lines 30-34
- Documents only `enabled` and `output_file`; actual `MemcheckConfig` has 20+ fields
- `output_file` is not even a MemcheckConfig field (inherited from parent)
- Implementers have no knowledge of `leak_check`, `track_origins`, `show_leak_kinds`, etc.

### C-3: Memcheck Valgrind command example doesn't match defaults
- **Location:** memcheck/README.md lines 71-73
- README shows: `--leak-check=full --track-origins=yes --show-leak-kinds=all`
- Actual defaults: `leak_check="summary"`, `track_origins=False`, `show_leak_kinds="definite,possible"`

### C-4: quic_protocol/README.md citation references nonexistent file
- **Location:** Lines 11, 58
- References `panther/plugins/protocols/client_server/quic/config_schema.py` -- file does not exist
- Actual source: `quic.py`

### C-5: CLAUDE.md emoji policy violations in 4 files
- `config/README.md` line 1: emoji in H1 title
- `tests/README.md`: 9 emoji headings, 11+ inline emoji
- `CONTRIBUTING.md`: Material icon shortcodes (`:material-file-tree:`, etc.)

### C-6: quic_protocol/README.md usage example has wrong implementation type
- **Location:** Line 99
- Shows `type: "tester"` for Picoquic client; should be `type: "iut"`
- `"tester"` is reserved for formal verification tools

## Moderate Findings (10)

| # | Issue | Location |
|---|-------|----------|
| M-1 | config/README.md mixin list (8 items) vs stated count (9) | Lines 112, 118-125 |
| M-2 | config/README.md duplicate "Validation Commands" sections with conflicting CLI styles | Lines 513-528 and 595-609 |
| M-3 | docker_builder/README.md untagged code blocks (bare ```) | Lines 27-44 |
| M-4 | picoquic/README.md code example misrepresents implementation (stubs vs 40-line methods) | Lines 33-56 |
| M-5 | picoquic/README.md "66.7% code reduction to 89 lines" -- actual file is ~587 lines | Line 60 |
| M-6 | picoquic/README.md inheritance diagram omits 4 of 5 parent classes | Architecture section |
| M-7 | tests/README.md "Zero technical debt" claim contradicts known issues | Line 588 |
| M-8 | tests/README.md fabricated achievement statistics (unverifiable) | Lines 579-591 |
| M-9 | quic_protocol/README.md references nonexistent test files | Lines 149-153 |
| M-10 | CONTRIBUTING.md icon shortcodes render as plain text outside MkDocs Material | Lines 4-9 |

## Minor Findings (2)

| # | Issue | Location |
|---|-------|----------|
| m-1 | Terminology inconsistency: "PicoQUIC" vs "Picoquic" vs "picoquic" | picoquic/README.md |
| m-2 | memcheck/README.md has 11 admonitions in 120 lines (over-use vs 0 in core READMEs) | memcheck/README.md |

## Style Patterns to Standardize

1. **Plugin Metadata Block**: Blockquote-style (`> **Plugin Type**: ...`) used in plugin READMEs but absent from core
2. **Leading Admonition**: Plugin READMEs open with `!!! info`; core READMEs do not
3. **Source Citations**: `<!-- src: /path/to/file.py -->` format used in 2 of 9 files; absent from 7
4. **Code Block Tags**: Tree-view diagrams should use ` ```text ` not bare ` ``` `
5. **Admonition Density**: Ranges from 0 (core) to 11 per 120 lines (memcheck) -- needs bounds

## Tier Rankings (Most to Least Consistent)

1. **Plugin READMEs** (picoquic, memcheck) -- clearest implied template, consistent structure
2. **Tool READMEs** (docs_gen) -- reasonable structure, partial citations
3. **Root docs** (CONTRIBUTING.md, config/README.md) -- structural issues but content-rich
4. **Core module READMEs** (command_processor, docker_builder) -- no admonitions, no citations, no cross-links
5. **tests/README.md** -- worst quality: emoji violations, fabricated stats, promotional tone

## Issues Summary
- **Critical:** 6
- **Moderate:** 10
- **Minor:** 2
