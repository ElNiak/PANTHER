from jinja2 import Environment, FileSystemLoader
from panther.core.utils.template_filters import TEMPLATE_FILTERS


class JinjaManager:
    def __init__(self, template_folder, **kwargs):
        """Initialize Jinja environment with custom filters and functions.

        Args:
            template_folder: Path to the templates directory
            **kwargs: Additional arguments to pass to Jinja Environment
        """
        self.template_folder = template_folder
        self.env = Environment(loader=FileSystemLoader(template_folder), **kwargs)

        # Register custom filters
        self.env.filters["safe_getattr"] = self.safe_getattr

        # Register template filters for secure command generation
        for filter_name, filter_func in TEMPLATE_FILTERS.items():
            self.env.filters[filter_name] = filter_func

        # Register custom global functions
        self.env.globals["has_attr"] = self.has_attr
        self.env.globals["safe_getattr"] = self.safe_getattr
        self.env.globals["safe_length"] = self.safe_length

        # Configure environment
        self.env.trim_blocks = True
        self.env.lstrip_blocks = True

    @staticmethod
    def has_attr(obj, attr):
        """Check if an object has an attribute."""
        return hasattr(obj, attr)

    def safe_getattr(self, obj, attr, default=None):
        """Returns the value of an attribute, or a default if it doesn't exist or can't be accessed."""
        if hasattr(obj, attr):
            try:
                return getattr(obj, attr)
            except (AttributeError, TypeError):
                return default
        return default

    def safe_length(self, obj, default=0):
        """Returns the length of an object, or a default if it doesn't exist or has no length."""
        if obj is None:
            return default
        try:
            return len(obj)
        except (TypeError, ValueError):
            return default

    def render_template(self, template_name, **context):
        """Render a template with the given context."""
        template = self.env.get_template(template_name)
        return template.render(**context)
