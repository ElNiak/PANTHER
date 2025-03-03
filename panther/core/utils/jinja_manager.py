# TODO centralize all jinja logic here
import os
from pathlib import Path
import jinja2

class JinjaManager:
    """
    Centralized manager for all Jinja2 template operations in the application.
    
    This class provides a unified interface for loading and rendering Jinja2 templates
    across the application, ensuring consistent template handling.
    """
    
    def __init__(self, template_dir=None):
        """
        Initialize the JinjaManager with optional custom template directory.
        
        Args:
            template_dir (str, optional): Path to the template directory.
                If not provided, uses the default templates directory.
        """
        if template_dir is None:
            # Use default templates directory
            self.template_dir = os.path.join(
                Path(os.path.dirname(__file__)).parent.parent, 
                "webapp", 
                "templates"
            )
        else:
            self.template_dir = template_dir
            
        # Configure Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def render_template(self, template_name, **context):
        """
        Render a template with the given context.
        
        Args:
            template_name (str): Name of the template file.
            **context: Variables to pass to the template.
            
        Returns:
            str: The rendered template as a string.
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def render_string(self, template_string, **context):
        """
        Render a template string with the given context.
        
        Args:
            template_string (str): The template string to render.
            **context: Variables to pass to the template.
            
        Returns:
            str: The rendered template as a string.
        """
        template = self.env.from_string(template_string)
        return template.render(**context)
