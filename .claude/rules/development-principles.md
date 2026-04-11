## Development Principles

Use existing PANTHER/Ivy infrastructure and parser tooling rather than building new tools or using regex-based approaches. Always ask before creating new tooling.

When a semantic parser, AST-based tool, or existing utility already handles a problem in the PANTHER codebase, use it. Do not propose building separate Docker Compose tools, standalone parsers, or regex-based workarounds when the infrastructure already provides the capability.
