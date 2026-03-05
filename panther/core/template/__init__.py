"""Template Module - Jinja2 Template Rendering for PANTHER.

Provides secure Jinja2-based template rendering with custom filters
for generating shell commands, configuration files, and plugin scaffolding.

Components:
    TemplateRenderer
        Jinja2 environment with autoescape and custom filters for safe
        command generation across shell, YAML, and JSON contexts.

    Custom Filters:
        - ``quote_shell`` -- safely quotes values with ``shlex`` for shell injection prevention
        - ``quote_yaml`` -- YAML-safe quoting for configuration generation
        - ``quote_json`` -- JSON-safe quoting for structured output

Example::

    from panther.core.template.template_renderer import TemplateRenderer

    renderer = TemplateRenderer(template_dir="templates/")
    output = renderer.render("service.sh.j2", name="picoquic", port=4433)

See Also:
    :mod:`panther.core.command_processor` -- uses templates for command generation
"""
