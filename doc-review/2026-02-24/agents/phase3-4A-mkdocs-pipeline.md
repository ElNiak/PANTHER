# Phase 3 - Dispatch 4A: MkDocs Documentation Pipeline Review

**Agent:** feature-dev:code-explorer
**Status:** COMPLETE
**Scope:** Full docs generation pipeline (`panther_builder.py` -> `mkdocs build`)

## Summary

The documentation pipeline has a critical structural defect: two conflicting code reference generation systems run simultaneously (`gendocs`/`mkgendocs.yml` producing committed files AND `gen_ref_pages.py` producing build-time virtual files), targeting the same `panther/` nav section. Additionally, `generate_plugin_inventory.py` is called by the builder but does not exist, 7 of 9 tools listed in the docs_gen README are fictional, and the `generated_build_dict.py` contains ~70 self-referencing entries that copy from `docs/` back into `docs/`.

## Pipeline Architecture

```
panther_builder.py docs
  |-- [Stage 1] get_automated_build_dict() -> generated_build_dict.py (cache)
  |-- [Stage 2] automate_mkdocs.py (AST walk, writes mkgendocs.yml)
  |-- [Stage 3] gendocs --config mkgendocs.yml (committed docs/panther/*.md)
  |-- [Stage 4] generate_plugin_inventory.py (MISSING FILE)
  |-- [Stage 5] Copy build_dict files to docs/
  |-- [Stage 6] Recursively copy panther/**/*.md -> docs/panther/
  |-- [Stage 7] mkdocs build --config-file mkdocs.yml
       |-- [gen-files plugin] gen_ref_pages.py (virtual files via mkdocs_gen_files)
       |-- [literate-nav] reads virtual panther/SUMMARY.md
       |-- mkdocstrings renders ::: ident directives
```

## Critical Findings (5)

### CRIT-01: Two conflicting code reference generation systems
- `gendocs`/`mkgendocs.yml` (Stage 3) produces committed `docs/panther/*.md` files with old flat-format markdown
- `gen_ref_pages.py` (Stage 7) produces build-time virtual files with `:::` mkdocstrings directives
- Both target the `panther/` nav section; MkDocs sees both and behavior is undefined
- The committed files may shadow the virtual ones depending on resolution order

### CRIT-02: `generate_plugin_inventory.py` does not exist
- `panther_builder.py` line 591 calls it but `if inventory_script.exists():` guard swallows silently
- `docs/plugins_inventory.md` has no automated generation path; permanently stale

### CRIT-03: `generated_build_dict.py` self-referencing entries (~70)
- Lines 17-33, 51-101 source from `docs/panther/...` paths
- When `docs/` is cleaned before building (which `panther_builder.py` does at lines 538-542), these source files do not exist
- Produces placeholder files instead of real content; cycle only works if docs built twice

### CRIT-04: Wrong PANTHER acronym in `prepare_docs.py`
- Line 110: "Protocol formal Analysis and formal Network Threat Evaluation Resources" (WRONG)
- `docs/index.md`: "Protocol Analysis and Testing Harness for Extensible Research" (CORRECT)
- `index_template.md`: yet another variant
- Three different acronym expansions exist across the codebase

### CRIT-05: `panther/SUMMARY.md` never written to disk
- `literate-nav` requires this file for `Code Reference: panther/` nav section
- Exists only in virtual filesystem during `mkdocs build`
- GitHub Pages, offline reading, or any static file server shows empty Code Reference

## Moderate Findings (5)

| # | Issue | Location |
|---|-------|----------|
| MOD-01 | `automate_mkdocs.py` requires all imports to succeed; silently skips on ImportError | automate_mkdocs.py:71-84 |
| MOD-02 | `.pre-commit-cache/` READMEs included in generated_build_dict.py (lines 163-165, 180) | generated_build_dict.py |
| MOD-03 | `pymdownx.snippets` with `check_paths: true` fails entire build on missing snippet | mkdocs.yml:133 |
| MOD-04 | `docs/index.md` GitHub-flavored callouts need `markdown-callouts` extension | mkdocs.yml |
| MOD-05 | `docs/panther/core/experiment_manager.md` line 1 is `#` with no title text (blank H1) | Generated file |

## Confirmed Pre-Identified Issues

| Issue | Status |
|-------|--------|
| docs_gen/README.md lists 7 non-existent tools | CONFIRMED: 7 of 9 tools fictional |
| INTEGRATION_INSTRUCTIONS.md uses `docs-gen` (hyphen) vs `docs_gen` (underscore) | CONFIRMED: 8 command examples broken |

## Navigation Coverage

All 38 nav entries in `mkdocs.yml` have corresponding files in `docs/` EXCEPT:
- `panther/` (Code Reference) -- depends entirely on `gen_ref_pages.py` virtual filesystem at build time

## Recommendations

1. Remove `gendocs`/`mkgendocs.yml` pipeline entirely; use only `gen_ref_pages.py` + `mkdocstrings`
2. Exclude `.pre-commit-cache/` and `.venv/` from `discover_sources.py`
3. Remove self-referencing `docs/panther/...` entries from `generated_build_dict.py`
4. Create `generate_plugin_inventory.py` or remove its call
5. Standardize PANTHER acronym to "Protocol Analysis and Testing Harness for Extensible Research"
6. Add CI step running `mkdocs build --strict` after every PR

## Issues Summary
- **Critical:** 5
- **Moderate:** 5
- **Minor:** 0
