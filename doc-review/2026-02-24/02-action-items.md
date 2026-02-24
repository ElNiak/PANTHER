# Action Items

**Date:** 2026-02-24
**Total Items:** 47 (12 P0, 15 P1, 14 P2, 6 P3)

---

## P0: Immediate (CRITICAL -- actively misleading, causes errors)

### P0-01: Fix CLAUDE.md wrong decorator names [S]
- **Finding:** 1D-CRIT-01
- **File:** `CLAUDE.md:116`
- **Issue:** Documents `@service_plugin`, `@protocol_plugin` -- these do not exist
- **Fix:** Replace with `@register_plugin(plugin_type=PluginType.SERVICE)` and `@register_protocol()`

### P0-02: Fix CLAUDE.md deleted CLI reference [S]
- **Finding:** 1A-HIGH-02
- **File:** `CLAUDE.md:9,116`
- **Issue:** Claims `panther/cli/` still exists; it was deleted
- **Fix:** Remove all references to `panther/cli/`; update to `panther/cli_click/`

### P0-03: Remove fabricated QUIC IUT config tables [M]
- **Finding:** 2G-CRIT-01, 3D-ANOMALY-02
- **Files:** 8 QUIC IUT plugin READMEs (aioquic, lsquic, mvfst, quant, quic_go, quiche, quinn, picoquic)
- **Issue:** All config tables contain fields that don't exist in code
- **Fix:** Replace with tables derived from actual `config_schema.py` files; add `<!-- src: -->` annotations

### P0-04: Fix gperf_cpu and gperf_heap READMEs (wrong tool) [M]
- **Finding:** 2H-CRIT-01, 3D-ANOMALY-01, 4D-Issue2
- **Files:** `panther/plugins/environments/execution_environment/gperf_cpu/README.md`, `gperf_heap/README.md`
- **Issue:** Document GNU gperf (hash generator) instead of gperftools (profiling library)
- **Fix:** Rewrite config tables from actual `config_schema.py`; correct tool description

### P0-05: Fix broken pyproject.toml entry points [S]
- **Finding:** 1A-CRIT-01
- **File:** `pyproject.toml`
- **Issue:** `panther-metrics` and `panther-plugin-tool` entry points reference nonexistent files
- **Fix:** Remove broken entry points or create the missing modules

### P0-06: Delete or rewrite results/ phantom docstrings [M]
- **Finding:** 2B-CRIT-03..07
- **Files:** `panther/core/results/__init__.py`, `result_collector.py`, `result_handler.py`
- **Issue:** Docstrings describe capabilities that don't exist (thread-safety, batch processing, anomaly detection)
- **Fix:** Replace with accurate docstrings proportional to actual code

### P0-07: Fix GDB _get_config_value LSP violation [S]
- **Finding:** 4D-Issue7, 3C-C4
- **File:** `panther/plugins/environments/execution_environment/gdb/gdb.py`
- **Issue:** 3-arg `_get_config_value` override incompatible with base class 2-arg signature
- **Fix:** Remove override; use base class pattern: `self._get_config_value("gdb_binary", plugin_config.gdb_binary)`

### P0-08: Fix IServiceManager._do_prepare infinite recursion [S]
- **Finding:** 3C-C1
- **File:** `panther/plugins/services/services_interface.py:801`
- **Issue:** `_do_prepare()` calls itself, causing stack overflow
- **Fix:** Replace self-call with actual implementation or raise NotImplementedError

### P0-09: Fix EnvironmentTemplateRenderer undefined methods [S]
- **Finding:** 2B-CRIT-09
- **File:** `panther/core/template/template_renderer.py:283-286`
- **Issue:** Registers `self.get_env_var` and `self.get_service_name` as Jinja2 globals -- neither exists
- **Fix:** Remove registrations or implement the methods

### P0-10: Fix config api_reference.md wrong method names [M]
- **Finding:** 1C-CRIT-02
- **File:** `panther/config/api_reference.md`
- **Issue:** 5 method names wrong (merge_with, to_yaml, from_yaml, set_field, load_and_validate_config)
- **Fix:** Replace with actual method signatures from code

### P0-11: Fix tester _setup_template_renderer logic bug [S]
- **Finding:** 3G-C1
- **File:** `panther/plugins/services/testers/tester_service_manager_mixin.py:150-179`
- **Issue:** Docstring says "optional protocol support" but else branch raises ValueError unconditionally
- **Fix:** Fix logic to match docstring, or update docstring to state protocol is mandatory

### P0-12: Remove dual docs pipeline conflict [L]
- **Finding:** 4A-CRIT-01
- **Files:** `panther_builder.py:578`, `mkgendocs.yml`
- **Issue:** Two conflicting code-reference systems (gendocs + gen_ref_pages.py) target same nav section
- **Fix:** Remove gendocs/mkgendocs.yml pipeline; keep gen_ref_pages.py as sole source

---

## P1: Next Sprint (MAJOR -- significant gaps blocking understanding)

### P1-01: Fix 57 broken markdown links [L]
- **Finding:** 4B (full inventory)
- **Files:** 8 source files
- **Fix:** Convert 29 absolute-style paths to relative; remove 17 links to nonexistent targets; fix 5 ADR prefixes; remove 10 dev/docs-gen references; fix 1 case mismatch

### P1-02: Create gdb/ execution environment README [M]
- **Finding:** 2H-CRIT-02, 3D-ANOMALY-07
- **File:** Create `panther/plugins/environments/execution_environment/gdb/README.md`
- **Issue:** 24 config fields, fully functional plugin, zero documentation
- **Fix:** Write README from config_schema.py; add to parent index tables

### P1-03: Update execution_environment/README.md for base class architecture [M]
- **Finding:** 4D-Issue1
- **File:** `panther/plugins/environments/execution_environment/README.md`
- **Issue:** No mention of BaseExecutionEnvironment, _config_class, _get_plugin_config
- **Fix:** Document 3-point plugin contract and base class helpers

### P1-04: Update network_environment/README.md for BaseNetworkResolver [M]
- **Finding:** 4D-Issue4
- **File:** `panther/plugins/environments/network_environment/README.md`
- **Issue:** No mention of BaseNetworkResolver or 4-step resolution template
- **Fix:** Document abstract methods and template pattern

### P1-05: Create plugins/core README [L]
- **Finding:** 2C (17 .py files, zero markdown)
- **File:** Create `panther/plugins/core/README.md`
- **Issue:** Plugin architecture backbone (decorators, factory, discovery, catalog) completely undocumented
- **Fix:** Write README covering registration flow, factory pattern, discovery rules

### P1-06: Fix ServiceManagerEventMixin false inheritance claim [S]
- **Finding:** 3G-C2
- **File:** `panther/plugins/services/service_event_mixin.py:17-19`
- **Issue:** Class docstring says "extends IServiceManager" -- it does not
- **Fix:** Update docstring to accurately describe standalone mixin role

### P1-07: Create config ADR file [M]
- **Finding:** 1A-HIGH-04, 1C-CRIT-01, 3E-C1
- **File:** Create `panther/config/adr/0001-hybrid-pydantic-omegaconf-architecture.md`
- **Issue:** Referenced in CLAUDE.md as authoritative but never created
- **Fix:** Write ADR documenting the OmegaConf+Pydantic hybrid decision

### P1-08: Fix memcheck README config table [M]
- **Finding:** 4C-C2, 3D-ANOMALY-03
- **File:** `panther/plugins/environments/execution_environment/memcheck/README.md`
- **Issue:** Documents 2 of 20+ fields; `output_file` doesn't exist in schema
- **Fix:** Replace with comprehensive table from config_schema.py

### P1-09: Remove emoji violations from 4 files [S]
- **Finding:** 4C-C5
- **Files:** `config/README.md:1`, `tests/README.md` (9 headings), `CONTRIBUTING.md`
- **Issue:** CLAUDE.md prohibits emojis; 4 files violate
- **Fix:** Remove all emoji from headings and content

### P1-10: Fix docs_gen/README.md fictional content [M]
- **Finding:** 2F-CRIT-01, 4A-CRIT-01
- **File:** `panther/tools/docs_gen/README.md`
- **Issue:** Lists 7 tools that don't exist; references nonexistent make targets
- **Fix:** Rewrite to document only existing tools

### P1-11: Remove cli_click stale migration artifacts [M]
- **Finding:** 2E
- **Files:** 14 files in `panther/cli_click/`
- **Issue:** 20+ "BEHAVIORAL EQUIVALENCE" markers, 9 argparse module docstring refs
- **Fix:** Remove all migration markers and argparse references

### P1-12: Fix CONTRIBUTING.md duplicate section [S]
- **Finding:** 4C-C1
- **File:** `CONTRIBUTING.md:140,197`
- **Issue:** "Admonitions Usage Guide" section appears twice verbatim
- **Fix:** Remove the second duplicate (line 197)

### P1-13: Fix INTEGRATION_INSTRUCTIONS.md wrong path [S]
- **Finding:** 2F-CRIT-07, 4A-CRIT-07
- **File:** `panther/tools/docs_gen/INTEGRATION_INSTRUCTIONS.md`
- **Issue:** Uses `docs-gen/` (hyphen) in 8 command examples instead of `docs_gen/` (underscore)
- **Fix:** Replace all `docs-gen/` with `docs_gen/`

### P1-14: Standardize PANTHER acronym [S]
- **Finding:** 4A-CRIT-04, 2F
- **Files:** `prepare_docs.py:110`, `index_template.md`, various
- **Issue:** Three different expansions across codebase
- **Fix:** Standardize to "Protocol Analysis and Testing Harness for Extensible Research"

### P1-15: Fix docker_builder README missing base_images/ [M]
- **Finding:** 3F-CRIT-02
- **File:** `panther/core/docker_builder/README.md`
- **Issue:** `base_images/` (5 files, in DockerBuilder's MRO) completely absent from docs
- **Fix:** Add base_images/ documentation; fix context_helper.py omission; correct class names

---

## P2: Backlog (MINOR -- incomplete but not harmful)

### P2-01: Add MRO documentation to service mixin files [M]
- **Finding:** 3G-M1
- **Fix:** Document method resolution order in all 8 mixin files

### P2-02: Add missing docstrings to undocumented public APIs [L]
- **Finding:** 2C (18 undocumented), 2A, 3A
- **Fix:** Add Google-style docstrings to all public methods lacking them

### P2-03: Create missing Diataxis docs for core modules [L]
- **Finding:** 4C-m19
- **Fix:** Add tutorial/how-to sections to command_processor and docker_builder READMEs

### P2-04: Fix events/observer api_reference accuracy [M]
- **Finding:** 1E
- **Fix:** Update all method names, class names, and parameter signatures

### P2-05: Add source citations to core module READMEs [M]
- **Finding:** 4C-Finding6,7
- **Fix:** Add `<!-- src: path/to/file.py -->` annotations to config, command_processor, docker_builder READMEs

### P2-06: Fix helgrind README schema (3 of 19 fields) [M]
- **Finding:** 2H, 3D
- **Fix:** Replace config table with actual HelgrindConfig fields; remove copy-paste strace field

### P2-07: Remove orphaned code in docker_builder build_image() docstring [S]
- **Finding:** 3F-CRIT-04
- **Fix:** Clean Python statements embedded in docstring (lines 1393-1459)

### P2-08: Fix CriticalAssertionException typo [S]
- **Finding:** 2D
- **Fix:** Rename to `CriticalAssertionException` -> `CriticalAssertionException` (decide canonical spelling)

### P2-09: Resolve ConfigurationError vs ConfigurationException naming [M]
- **Finding:** 2D
- **Fix:** Document when to use each, or consolidate into one class

### P2-10: Fix plugin template broken imports [S]
- **Finding:** 2F-CRIT-02
- **Fix:** Update template plugins to import from correct module paths

### P2-11: Update CHANGELOG for v1.1.4 and v1.1.5 [S]
- **Finding:** 1A-HIGH-03
- **Fix:** Add entries for missing versions

### P2-12: Fix test documentation unregistered markers [M]
- **Finding:** 1F-CRIT-01
- **Fix:** Either register markers in pyproject.toml or remove from docs

### P2-13: Clean generated_build_dict.py self-referencing entries [M]
- **Finding:** 4A-CRIT-03
- **Fix:** Remove ~70 entries that copy from docs/ back into docs/

### P2-14: Exclude .pre-commit-cache from docs discovery [S]
- **Finding:** 4A-MOD-02
- **Fix:** Add path filter to PantherSourceDiscovery

---

## P3: Optional (INFO -- polish and suggestions)

### P3-01: Standardize plugin README template [M]
Create enforced template with metadata blocks, source citations, config tables.

### P3-02: Add CI step for `mkdocs build --strict` [M]
Catch broken references automatically in PRs.

### P3-03: Standardize code block language tags [S]
Use `text` for directory trees instead of bare fences.

### P3-04: Reduce memcheck admonition density [S]
11 admonitions in 120 lines; consolidate to ~3 per section.

### P3-05: Rewrite tests/README.md [L]
Remove promotional tone, fabricated statistics, emoji headings.

### P3-06: Create ADRs for undocumented architectural decisions [L]
7-9 major decisions have no ADR (see 3E recommendations).

---

## Effort Legend

| Size | Estimate | Description |
|------|----------|-------------|
| S | < 30 min | Single file edit, straightforward fix |
| M | 30 min - 2 hr | Multiple files or requires research |
| L | 2+ hr | Multi-file rewrite or creation of new docs |

## Effort Summary

| Priority | S | M | L | Total |
|----------|:-:|:-:|:-:|:---:|
| P0 | 5 | 5 | 2 | 12 |
| P1 | 5 | 7 | 3 | 15 |
| P2 | 4 | 7 | 3 | 14 |
| P3 | 2 | 2 | 2 | 6 |
| **Total** | **16** | **21** | **10** | **47** |
