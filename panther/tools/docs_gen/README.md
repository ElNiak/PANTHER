# PANTHER Documentation Generator Tools

Tools for building and maintaining PANTHER's MkDocs-based documentation site.

## Usage

```bash
python panther_builder.py docs        # Build full documentation site
python panther_builder.py serve-docs  # Serve locally
python panther_builder.py deploy-docs # Deploy to GitHub Pages
```

## Directory Structure

```text
docs_gen/
├── __init__.py                  # Exports PantherSourceDiscovery, get_build_dict
├── discover_sources.py          # Automated README discovery and build_dict generation
├── generate_build_mapping.py    # Integration module for panther_builder.py
├── generated_build_dict.py      # Auto-generated mapping (do not edit)
├── mkdocs.yml.bak               # Backup of MkDocs configuration
└── mkdocs/
    ├── gen_ref_pages.py         # Auto-generate API reference pages (mkdocstrings)
    ├── prepare_docs.py          # Symlink/copy Markdown files into docs/
    ├── docs_structure.py        # Documentation directory layout manager
    ├── fix_encoding.py          # Fix encoding issues in Markdown files
    ├── fix_markdown_links.py    # Convert absolute links to relative
    ├── generate_plugin_docs.py  # Extract plugin docs from README files
    └── automate_mkdocs.py       # MkDocs nav generation and automation
```

## Pipeline

`python panther_builder.py docs` runs the full pipeline:

1. **Discover** sources via `discover_sources.py`
2. **Prepare** docs directory via `prepare_docs.py`
3. **Fix** links and encoding
4. **Generate** API reference and plugin docs
5. **Build** with MkDocs
