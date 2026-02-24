# Cross-Reference Index

**Date:** 2026-02-24
**Purpose:** Correlate findings by file, symbol, and concept across all 25 agent reports. Each finding listed once at highest severity.

---

## By File (Top 20 Most-Referenced)

### panther/core/README.md
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| 11 broken links | 4B | CRITICAL | Absolute paths used as relative |
| Module tree wrong | 1B | MAJOR | Missing exceptions/, state/, outputs/, template/ |
| Four-phase model inconsistent | 1B | MAJOR | Three different descriptions across codebase |
| Links to EXPERIMENT_ENGINE.md | 1B, 4B | CRITICAL | File never created |

### panther/config/README.md
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| Mixin count 9 vs 8 | 4C, 4D | MODERATE | ErrorHandlerMixin omitted from list |
| Dual validation commands | 4C | MODERATE | Two sections with conflicting CLI styles |
| Emoji in H1 | 4C | CRITICAL | CLAUDE.md violation |
| 40+ undocumented fields | 1C | MAJOR | 20+ model classes never mentioned |
| Wrong method names in api_reference.md | 1C | CRITICAL | 5 methods renamed/removed |
| services type wrong (list vs dict) | 1C | MAJOR | Documented as list, actual is Dict |
| Thread safety contradiction | 1C | MAJOR | manager.py vs README disagree |

### panther/plugins/services/services_interface.py
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| _do_prepare() infinite recursion | 3C | CRITICAL | Calls self at line 801 |
| _protocol_version never initialized | 3C | CRITICAL | Property raises AttributeError |
| generate_run_command LSP violation | 3C | CRITICAL | str vs Dict return type |
| _plugin_dir set twice | 3C | MAJOR | Lines 140 and 236 |
| 1074-line God Class | 3C | MINOR | IServiceManager.__init__ |

### panther/core/experiment_manager.py
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| Fast-fail docstring wrong | 3A | CRITICAL | TimeoutCascadeException claimed but not checked |
| Deprecated .dict() usage | 3A | CRITICAL | _save_configuration uses Pydantic v1 API |
| Return value semantics | 3A | CRITICAL | 1 pass of 100 returns True |
| Double LoggerFactory.initialize | 3A | IMPORTANT | Lines 171 and 1050 |
| Silent AttributeError swallowing | 3A | IMPORTANT | contextlib.suppress(Exception) with no logging |

### CONTRIBUTING.md
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| 11 broken links | 4B | CRITICAL | dev/docs-gen/ directory doesn't exist |
| Duplicate section | 4C | CRITICAL | "Admonitions Usage Guide" at lines 140 and 197 |
| Material icon shortcodes | 4C | MODERATE | Render as plain text outside MkDocs Material |

### panther/plugins/services/testers/tester_service_manager_mixin.py
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| _setup_template_renderer masks bug | 3G | CRITICAL | Docstring says optional, code raises ValueError |
| setup_tester_specific_attributes wrong params | 3G | CRITICAL | Missing `protocol` parameter |
| TODO in production | 3G | MAJOR | Line 119 |
| Missing plugin_dir parameter | 3G | MAJOR | standard_tester_initialization docstring |

### panther/core/docker_builder/README.md
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| base_images/ absent | 3F | CRITICAL | In DockerBuilder MRO, zero docs |
| context_helper.py invisible | 3F | CRITICAL | Imported at startup, not in README |
| Orphaned code in docstring | 3F | CRITICAL | Python statements in build_image() docstring |
| Cache truncation undocumented | 3F | CRITICAL | 100 files / 1KB limit |
| O(log n) claim incorrect | 3F | MINOR | SHA-256 is O(n) |

### panther/core/results/
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| Phantom capabilities in __init__.py | 2B | CRITICAL | Describes nonexistent features |
| ResultCollector 7:1 doc-to-code ratio | 2B | CRITICAL | 100-line docstring for 14-line class |
| Fabricated performance claims | 2B | CRITICAL | "100-1000 results/second", "O(1) streaming" |
| Broken chain-of-responsibility | 2B | CRITICAL | 2 handlers missing super().__init__() |

### tests/README.md
| Finding | Agent | Severity | Issue |
|---------|-------|----------|-------|
| 8+ unregistered pytest markers | 1F | CRITICAL | Using them breaks test collection |
| "Zero technical debt" false | 1F, 4C | CRITICAL | Contradicted by known issues |
| Emoji policy violations | 4C | CRITICAL | 9 emoji headings, 11 inline |
| Fabricated achievement statistics | 4C | MODERATE | Unverifiable claims |
| Coverage threshold mismatch | 1F | HIGH | Claims 85%, actual 70% |

---

## By Concept

### Decorator/Registration System
| File | Agent | Severity | Issue |
|------|-------|----------|-------|
| CLAUDE.md | 1D | CRITICAL | Wrong names: @service_plugin, @protocol_plugin |
| development.md | 1D | CRITICAL | Plugin main file convention wrong |
| plugin_catalog.py | 1D, 2C | CRITICAL | Dependency resolution is TODO stub |
| plugin_decorators.py | 2C | CRITICAL | "production" runtime_mode rejected |

### Config Schema Documentation
| Module | Agent | Severity | Issue |
|--------|-------|----------|-------|
| 8 QUIC IUTs | 2G, 3D | CRITICAL | Entirely fabricated config tables |
| gperf_cpu/heap | 2H, 3D | CRITICAL | Wrong tool documented |
| memcheck | 3D, 4C | CRITICAL | 2 of 20+ fields documented |
| helgrind | 2H, 3D | CRITICAL | 3 of 19 fields, 1 copy-paste |
| gdb | 3D | CRITICAL | 24 fields, no README |
| Overall | 3D | MAJOR | 18.3% field documentation rate |

### Base Class Architecture (Post-Refactor)
| File | Agent | Severity | Issue |
|------|-------|----------|-------|
| execution_environment/README.md | 4D | STALE | No BaseExecutionEnvironment docs |
| network_environment/README.md | 4D | STALE | No BaseNetworkResolver docs |
| gdb/gdb.py | 4D | CRITICAL | _get_config_value LSP violation |
| strace/README.md | 4D | PARTIAL | Old API pattern in extension example |
| docker_compose/README.md | 4D | PARTIAL | Nonexistent method names |

### Broken Links
| Source | Count | Agent | Root Cause |
|--------|:---:|-------|-----------|
| panther/core/README.md | 11 | 4B | Absolute paths in relative context |
| CONTRIBUTING.md | 11 | 4B | dev/docs-gen/ directory absent |
| panther/core/adr/README.md | 9 | 4B, 3E | cli/ deleted + wrong prefix |
| PACKAGING.md | 7 | 4B | docs/packaging/ absent |
| panther/plugins/README.md | 6 | 4B | Absolute paths |
| panther/plugins/development.md | 6 | 4B | Absolute paths + case mismatch |

### MkDocs Pipeline
| Component | Agent | Severity | Issue |
|-----------|-------|----------|-------|
| gendocs vs gen_ref_pages.py | 4A | CRITICAL | Dual conflicting systems |
| generate_plugin_inventory.py | 4A | CRITICAL | Called but doesn't exist |
| generated_build_dict.py | 4A | CRITICAL | ~70 self-referencing entries |
| SUMMARY.md | 4A | CRITICAL | Never written to disk |
| INTEGRATION_INSTRUCTIONS.md | 2F, 4A | CRITICAL | docs-gen vs docs_gen path |

### ADR System
| Issue | Agent | Severity |
|-------|-------|----------|
| Config ADR missing | 1A, 1C, 3E | CRITICAL |
| 3 CLI ADR links broken | 1B, 3E | CRITICAL |
| ADR-0003 example incorrect | 3E | CRITICAL |
| 3 phantom ADR references | 3E | CRITICAL |
| ADR-0001 missing Status section | 3E | CRITICAL |
| 7-9 decisions without ADRs | 3E | MAJOR |

---

## Uncorrelated Findings (Single-Agent, Not Cross-Referenced)

| Agent | Finding | Severity |
|-------|---------|----------|
| 3A | Double LoggerFactory.initialize | IMPORTANT |
| 3A | _perform_dry_run hardcodes emojis | IMPORTANT |
| 3F | BuildKitCacheMixin not in MRO | MAJOR |
| 3F | network_exists() `Args:zdzd` typo | MAJOR |
| 3B | extra="allow" at root BaseConfig | CRITICAL |
| 3B | Pydantic v1/v2 mixing | MAJOR |
| 3G | No MRO documentation in any mixin file | MAJOR |
| 2D | ServiceCommandGenerationException copy-paste docstring | CRITICAL |
| 2B | EnvironmentTemplateRenderer undefined methods | CRITICAL |
| 2A | SequenceOn methods at module level | MAJOR |
| 2A | CRIT-08: type(step) references undefined variable | CRITICAL |
| 1E | EventEmitter calls nonexistent EventManager.publish() | CRITICAL |
