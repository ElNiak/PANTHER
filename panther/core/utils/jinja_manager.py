import jinja2
from jinja2 import Environment, FileSystemLoader
import os

class JinjaManager:
    def __init__(self, template_folder, **kwargs):
        """Initialize Jinja environment with custom filters and functions.

        Args:
            template_folder: Path to the templates directory
            **kwargs: Additional arguments to pass to Jinja Environment
        """
        self.template_folder = template_folder
        self.env = Environment(
            loader=FileSystemLoader(template_folder),
            **kwargs
        )

        # Register custom filters
        self.env.filters['safe_getattr'] = self.safe_getattr

        # Register custom global functions
        self.env.globals['has_attr'] = self.has_attr
        self.env.globals['safe_getattr'] = self.safe_getattr

        # Configure environment
        self.env.trim_blocks = True
        self.env.lstrip_blocks = True

    @staticmethod
    def has_attr(obj, attr):
        """Check if an object has an attribute."""
        return hasattr(obj, attr)

    @staticmethod
    def safe_getattr(obj, attr, default=None):
        """Safely get an attribute from an object, returning default if not found."""
        return getattr(obj, attr, default)

    def render_template(self, template_name, **context):
        """Render a template with the given context."""
        template = self.env.get_template(template_name)
        return template.render(**context)