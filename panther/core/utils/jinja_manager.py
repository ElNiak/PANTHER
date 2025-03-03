import jinja2
from jinja2 import Environment, FileSystemLoader
import os

class JinjaManager:
    def __init__(self, template_dir):
        """Initialize the JinjaManager with a template directory.

        Args:
            template_dir (str): The directory containing Jinja2 templates.
        """
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))

        # Add helper functions to safely access nested attributes
        self.env.globals['safe_getattr'] = self.safe_getattr
        self.env.globals['has_attr'] = self.has_attr
        self.env.globals['get_nested_attr'] = self.get_nested_attr
        self.env.globals['safe_length'] = self.safe_length

    def has_attr(self, obj, attr):
        """Check if an object has an attribute"""
        if obj is None:
            return False
        return hasattr(obj, attr)

    def get_nested_attr(self, obj, attr_path, default=None):
        """Safely access a nested attribute path, returning default if any part is not found"""
        if obj is None:
            return default

        attrs = attr_path.split('.')
        current = obj

        for attr in attrs:
            if not hasattr(current, attr):
                return default
            current = getattr(current, attr)

        return current

    def safe_length(self, obj, default=0):
        """Safely get the length of an object, returning default if not possible"""
        try:
            return len(obj) if obj is not None else default
        except (TypeError, AttributeError):
            return default

    def safe_getattr(self, obj, attr, default=None):
        """Safely access an attribute of an object, returning default if not found"""
        try:
            if obj is None:
                return default
            return getattr(obj, attr, default)
        except (AttributeError, TypeError):
            return default

    def render_template(self, template_name, **kwargs):
        """Render a template with the given context.

        Args:
            template_name (str): The name of the template to render.
            **kwargs: Template context.

        Returns:
            str: The rendered template.
        """
        template = self.env.get_template(template_name)
        return template.render(**kwargs)