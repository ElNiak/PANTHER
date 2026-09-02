# CLI Reference

Complete reference for the `panther` command-line interface.

!!! note "The `ai-rfc` subcommands forward their arguments"

    The `ai_rfc` substrate, which reconstructs a requirement specification from
    an existing implementation's history, is deliberately not registered as a
    plugin type — it is reached as `panther ai-rfc <verb>`. Its eight
    subcommands below are passthroughs onto standalone `argparse` commands, so
    their arguments are not described here; see
    [ai_rfc (reconstructed specs)](ai_rfc.md) for each one's options.

    Every verb is equally reachable as
    `python -m panther.plugins.services.testers.ai_rfc[.SUB]`, which is
    unchanged and is what the agent harness invokes.

::: mkdocs-click
    :module: panther.cli.core.main
    :command: cli
    :prog_name: panther
    :depth: 2
