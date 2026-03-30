"""Template Renderer Utilities.

This module provides utilities for template rendering operations,
reducing duplication of Jinja2 template handling across service managers.
"""

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import jinja2

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.core.command_processor import ShellCommand
from panther.core.command_processor.utils.summarizer import CommandSummarizer
from panther.core.utils.logging_mixin import LoggerMixin


class TemplateRenderer(LoggerMixin):
    """Utility class for rendering Jinja2 templates with common patterns.

    Reduces duplication of template rendering logic across service managers.
    """

    def __init__(
        self,
        template_dir: Union[str, Path],
        enable_autoescape: bool = False,
        custom_filters: Optional[Dict[str, Callable]] = None,
    ):
        """Initialize the template renderer.

        Args:
            template_dir: Directory containing templates
            enable_autoescape: Enable Jinja2 autoescape
            custom_filters: Dictionary of custom Jinja2 filters
        """
        super().__init__()
        self.template_dir = Path(template_dir)
        self.logger.debug(
            f"Initializing TemplateRenderer with directory: {self.template_dir}"
        )

        # Add default filters including quote_shell
        self.custom_filters = custom_filters or {}
        self.custom_filters.setdefault("quote_shell", shlex.quote)

        # Initialize Jinja2 environment
        self._init_jinja_env(enable_autoescape)

    def _init_jinja_env(self, enable_autoescape: bool) -> None:
        """Initialize the Jinja2 environment."""
        if not self.template_dir.exists():
            raise ValueError(f"Template directory does not exist: {self.template_dir}")

        loader = jinja2.FileSystemLoader(str(self.template_dir))

        if enable_autoescape:
            self.jinja_env = jinja2.Environment(
                loader=loader, autoescape=jinja2.select_autoescape(["html", "xml"])
            )
        else:
            self.jinja_env = jinja2.Environment(loader=loader, autoescape=True)

        # Add custom filters
        for name, filter_func in self.custom_filters.items():
            self.jinja_env.filters[name] = filter_func

    def render_template(
        self, template_name: str, context: Dict[str, Any], strict: bool = False
    ) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of the template file
            context: Context dictionary for rendering
            strict: Whether to raise on undefined variables

        Returns:
            Rendered template as string

        Raises:
            jinja2.TemplateNotFound: If template doesn't exist
            jinja2.TemplateError: If rendering fails
        """
        try:
            if strict:
                self.jinja_env.undefined = jinja2.StrictUndefined
            else:
                self.jinja_env.undefined = jinja2.Undefined

            # Log template rendering with smart context summarization
            context_summary = CommandSummarizer.summarize_template_context(context)
            self.logger.debug(
                "Rendering template '%s' with context: %s",
                template_name,
                context_summary,
            )

            # Full context available at TRACE level
            if self.logger.isEnabledFor(5):  # TRACE level
                self.logger.trace(
                    "Full template context for '%s': %s", template_name, context
                )

            template = self.jinja_env.get_template(template_name)
            return template.render(**context)

        except jinja2.TemplateNotFound:
            self.logger.error(f"Template not found: {template_name}")
            raise
        except jinja2.TemplateError as e:
            self.logger.error(f"Template rendering error in {template_name}: {e}")
            raise

    def render_to_file(
        self,
        template_name: str,
        context: Dict[str, Any],
        output_path: Union[str, Path],
        create_dirs: bool = True,
    ) -> Path:
        """Render a template and write to a file.

        Args:
            template_name: Name of the template file
            context: Context dictionary for rendering
            output_path: Path to write the rendered content
            create_dirs: Whether to create parent directories

        Returns:
            Path to the created file
        """
        output_path = Path(output_path)

        if create_dirs:
            output_path.parent.mkdir(parents=True, exist_ok=True)

        rendered = self.render_template(template_name, context)

        with open(output_path, "w") as f:
            f.write(rendered)

        # Log template rendering result with context summary
        context_summary = CommandSummarizer.summarize_template_context(
            context, max_keys=3
        )
        self.logger.debug(
            "Rendered template '%s' to '%s' | %s",
            template_name,
            output_path.name,
            context_summary,
        )

        return output_path

    def render_command_template(
        self,
        template_name: str,
        params: Dict[str, Any],
        command_args: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> "ShellCommand":
        """Render a command template to a ShellCommand.

        Args:
            template_name: Name of the command template
            params: Parameters for template rendering
            command_args: Pre-built command arguments
            env_vars: Environment variables

        Returns:
            StructuredCommand object
        """
        # Lazy import to avoid circular dependency
        from panther.core.command_processor import ShellCommand

        # Build context with command args and env vars
        context = params.copy()

        if command_args is not None:
            context["command_args"] = command_args
            context["command_args_string"] = " ".join(command_args)

        if env_vars is not None:
            context["env_vars"] = env_vars

        # Render the template
        rendered = self.render_template(template_name, context)

        # Parse the rendered command
        # Assume template renders to format: COMMAND [ARGS]
        parts = rendered.strip().split(None, 1)
        command = parts[0] if parts else ""
        args_string = parts[1] if len(parts) > 1 else ""

        # Build full command
        full_command = f"{command} {args_string}" if args_string else command

        return ShellCommand(command=full_command, environment=env_vars or {})

    def get_template_for_role(
        self, role: str, template_suffix: str = "_command.jinja"
    ) -> str:
        """Get template name based on role.

        Args:
            role: Role name (e.g., "client", "server")
            template_suffix: Template file suffix

        Returns:
            Template filename
        """
        return f"{role.lower()}{template_suffix}"

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self.jinja_env.get_template(template_name)
            return True
        except jinja2.TemplateNotFound:
            return False

    def list_templates(self, pattern: Optional[str] = None) -> List[str]:
        """List available templates.

        Args:
            pattern: Optional glob pattern to filter templates

        Returns:
            List of template names
        """
        templates = []

        if pattern:
            for template_path in self.template_dir.glob(pattern):
                if template_path.is_file():
                    templates.append(template_path.name)
        else:
            for template_path in self.template_dir.iterdir():
                if template_path.is_file() and template_path.suffix in [
                    ".jinja",
                    ".j2",
                    ".jinja2",
                ]:
                    templates.append(template_path.name)

        return sorted(templates)


class EnvironmentTemplateRenderer(TemplateRenderer):
    """Specialized template renderer for environments.

    Provides additional functionality specific to environment command rendering.
    """

    def __init__(self, template_dir: Union[str, Path], **kwargs):
        """Initialize environment template renderer.

        Args:
            template_dir: Directory containing environment templates
            **kwargs: Additional arguments for TemplateRenderer
        """
        super().__init__(template_dir, **kwargs)
        self.logger.debug(
            f"Initialized EnvironmentTemplateRenderer with directory: {self.template_dir}"
        )
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir), autoescape=True
        )


class ServiceTemplateRenderer(TemplateRenderer):
    """Specialized template renderer for service managers.

    Provides additional functionality specific to service command rendering.
    """

    def __init__(
        self,
        service_dir: Union[str, Path],
        protocol_dir: Optional[Union[str, Path]] = None,
        **kwargs,
    ):
        """Initialize service template renderer.

        Args:
            service_dir: Service directory containing templates/ subdirectory
            protocol_dir: Protocol name for protocol-specific template subdirectory
            **kwargs: Additional arguments for TemplateRenderer
        """
        service_dir = Path(service_dir)

        # Build template directory: service_dir/templates/protocol_dir
        template_dir = service_dir / "templates"
        if protocol_dir:
            template_dir = template_dir / protocol_dir

        super().__init__(template_dir, **kwargs)
        self.service_dir = service_dir
        self.protocol_dir = protocol_dir

    def render_structured_command(
        self,
        role: str,
        params: Dict[str, Any],
        command_args: List[str],
        env_vars: Optional[Dict[str, str]] = None,
        use_structured: bool = True,
    ) -> "ShellCommand":
        """Render a structured command template with fallback.

        Args:
            role: Service role (client/server)
            params: Template parameters
            command_args: Command arguments
            env_vars: Environment variables
            use_structured: Try structured template first

        Returns:
            ShellCommand object
        """
        # Try structured template first if requested
        if use_structured:
            structured_template = self.get_template_for_role(
                role, "_command_structured.jinja"
            )

            if self.template_exists(structured_template):
                try:
                    return self.render_command_template(
                        structured_template, params, command_args, env_vars
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to render structured template: {e}, "
                        "falling back to regular template"
                    )

        # Fallback to regular template
        template_name = self.get_template_for_role(role)
        return self.render_command_template(
            template_name, params, command_args, env_vars
        )

    def render_config_file(
        self, config_template: str, params: Dict[str, Any], output_filename: str
    ) -> Path:
        """Render a configuration file template.

        Args:
            config_template: Name of config template
            params: Template parameters
            output_filename: Output filename

        Returns:
            Path to rendered config file
        """
        # Render to service directory by default
        output_path = self.service_dir / output_filename

        return self.render_to_file(config_template, params, output_path)

    def get_role_templates(self, role: str) -> List[str]:
        """Get all templates for a specific role."""
        return [t for t in self.list_templates() if t.startswith(f"{role.lower()}_")]
