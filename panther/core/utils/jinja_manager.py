
import jinja2
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os

class JinjaManager:
    """
    A utility class for managing Jinja2 templates.
    """
    
    def __init__(self, template_dir):
        """
        Initialize the JinjaManager with a template directory.
        
        Args:
            template_dir: Path to the template directory
        """
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add helper functions to safely access nested attributes
        self.env.globals['safe_getattr'] = self.safe_getattr
        self.env.globals['hasattr'] = hasattr
        self.env.globals['get_nested_attr'] = self.get_nested_attr
        self.env.globals['safe_length'] = self.safe_length
        self.env.globals['safe_dict_access'] = self.safe_dict_access
        self.env.globals['has_key'] = self.has_key
        
        # Add filters for attribute access
        self.env.filters['attr'] = self.safe_getattr
        self.env.filters['has_attr'] = hasattr
        self.env.filters['get_nested'] = self.get_nested_attr
        self.env.filters['safe_len'] = self.safe_length

    def get_nested_attr(self, obj, attr_path, default=None):
        """Safely access a nested attribute path, returning default if any part is not found"""
        if obj is None:
            return default
            
        attrs = attr_path.split('.')
        current = obj
        
        for attr in attrs:
            if hasattr(current, attr):
                current = getattr(current, attr)
            elif isinstance(current, dict) and attr in current:
                current = current[attr]
            else:
                return default
            
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
            if hasattr(obj, attr):
                return getattr(obj, attr)
            elif isinstance(obj, dict) and attr in obj:
                return obj[attr]
            return default
        except (AttributeError, TypeError):
            return default
            
    def safe_dict_access(self, dictionary, key, default=None):
        """Safely access a dictionary key, returning default if not found"""
        if dictionary is None:
            return default
        try:
            return dictionary.get(key, default)
        except (AttributeError, TypeError):
            return default
            
    def has_key(self, dictionary, key):
        """Check if a dictionary has a key"""
        if dictionary is None:
            return False
        try:
            return key in dictionary
        except (TypeError, AttributeError):
            return False

    def render_template(self, template_name, **context):
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template to render
            **context: Template context variables
            
        Returns:
            Rendered template as a string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
