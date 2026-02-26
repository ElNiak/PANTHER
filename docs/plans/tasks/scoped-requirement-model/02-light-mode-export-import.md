# Task 2: Light-Mode Export/Import Extraction

**Status:** pending
**Depends on:** Task 1

**Files:**
- Modify: `ivy_lsp/analysis/light_mode_extractor.py` (add regex patterns + function)
- Test: `tests/test_export_import_extraction.py` (extend)

---

## Step 1: Write the failing test

Append to `tests/test_export_import_extraction.py`:

```python
from ivy_lsp.analysis.light_mode_extractor import extract_exports_imports_light

FILEPATH = "/test/test_file.ivy"


class TestLightModeExportExtraction:
    def test_single_export(self):
        source = "export quic.send\n"
        info = extract_exports_imports_light(source, FILEPATH)
        assert info.exports == ["quic.send"]
        assert info.export_lines["quic.send"] == 0

    def test_single_import(self):
        source = "import tls.handshake\n"
        info = extract_exports_imports_light(source, FILEPATH)
        assert info.imports == ["tls.handshake"]
        assert info.import_lines["tls.handshake"] == 0

    def test_multiple_exports_and_imports(self):
        source = (
            "export quic.send\n"
            "export quic.recv\n"
            "import tls.client_hello\n"
        )
        info = extract_exports_imports_light(source, FILEPATH)
        assert len(info.exports) == 2
        assert len(info.imports) == 1
        assert "quic.send" in info.exports
        assert "quic.recv" in info.exports
        assert "tls.client_hello" in info.imports

    def test_export_with_surrounding_code(self):
        source = (
            "#lang ivy1.7\n"
            "include quic_types\n"
            "\n"
            "export quic.send\n"
            "export quic.recv\n"
            "\n"
            "before quic.send {\n"
            "    require connected;\n"
            "}\n"
        )
        info = extract_exports_imports_light(source, FILEPATH)
        assert info.exports == ["quic.send", "quic.recv"]
        assert info.export_lines["quic.send"] == 3
        assert info.export_lines["quic.recv"] == 4

    def test_no_exports_or_imports(self):
        source = (
            "#lang ivy1.7\n"
            "type cid\n"
            "relation connected(X:cid, Y:cid)\n"
        )
        info = extract_exports_imports_light(source, FILEPATH)
        assert info.exports == []
        assert info.imports == []
        assert info.has_exports is False

    def test_empty_source(self):
        info = extract_exports_imports_light("", FILEPATH)
        assert info.exports == []
        assert info.imports == []

    def test_indented_export_inside_object(self):
        source = (
            "object test_runner = {\n"
            "    export quic.send\n"
            "    import quic.recv\n"
            "}\n"
        )
        info = extract_exports_imports_light(source, FILEPATH)
        assert "quic.send" in info.exports
        assert "quic.recv" in info.imports

    def test_commented_export_ignored(self):
        source = (
            "# export quic.send\n"
            "export quic.recv\n"
        )
        info = extract_exports_imports_light(source, FILEPATH)
        assert "quic.recv" in info.exports
        assert "quic.send" not in info.exports
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_export_import_extraction.py::TestLightModeExportExtraction -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_exports_imports_light'`

## Step 3: Write minimal implementation

Add to `ivy_lsp/analysis/light_mode_extractor.py` (after the existing `ACTION_RE`):

```python
# At module top, after ACTION_RE:
EXPORT_RE = re.compile(r"^\s*export\s+([\w.]+)", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE)


def extract_exports_imports_light(
    source: str,
    filepath: str,
) -> "ExportImportInfo":
    """Regex-based export/import extraction for light mode."""
    from ivy_lsp.analysis.test_scope import ExportImportInfo

    exports: list = []
    imports: list = []
    export_lines: dict = {}
    import_lines: dict = {}

    for m in EXPORT_RE.finditer(source):
        name = m.group(1)
        line = source[: m.start()].count("\n")
        exports.append(name)
        export_lines[name] = line

    for m in IMPORT_RE.finditer(source):
        name = m.group(1)
        line = source[: m.start()].count("\n")
        imports.append(name)
        import_lines[name] = line

    return ExportImportInfo(
        file=filepath,
        exports=exports,
        imports=imports,
        export_lines=export_lines,
        import_lines=import_lines,
    )
```

**Note:** The `EXPORT_RE` pattern uses `^\s*export` to match indented exports inside objects but also matches `# export` since `#` is not whitespace-only. The `test_commented_export_ignored` test catches this -- the regex `^\s*` will NOT match `# export` since `#` is not `\s`. Verify this works correctly.

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_export_import_extraction.py::TestLightModeExportExtraction -v
```

Expected: PASS (8 tests)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/light_mode_extractor.py tests/test_export_import_extraction.py
git commit -m "feat(light-mode): add regex-based export/import extraction"
```
