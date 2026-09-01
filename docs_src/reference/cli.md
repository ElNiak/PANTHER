# CLI Reference

Complete reference for the `panther` command-line interface.

!!! note "Not every command in the repository is a `panther` subcommand"

    The `ai_rfc` substrate, which reconstructs a requirement specification from
    an existing implementation's history, is deliberately not registered as a
    plugin type and has no console script. Its eight entry points are reached as
    `python -m panther.plugins.services.testers.ai_rfc...` and are documented in
    [ai_rfc (reconstructed specs)](ai_rfc.md) — nothing below covers them.

::: mkdocs-click
    :module: panther.cli.core.main
    :command: cli
    :prog_name: panther
    :depth: 2
