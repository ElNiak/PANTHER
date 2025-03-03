import jinja2
from pathlib import Path
import os
from omegaconf import OmegaConf

class JinjaManager:
    def __init__(self, template_dir=None):
        if template_dir is None:
            # Default to a templates directory in the current working directory
            template_dir = Path(os.getcwd()) / "templates"

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

    def prepare_data(self, data):
        """
        Prepare data for template rendering

        Args:
            data: Data to prepare (can be a list, dict, or object)

        Returns:
            Data prepared for template rendering
        """
        if hasattr(data, "__dict__"):
            # Convert objects to dictionaries
            result = {}
            # Include all attributes except methods and private attributes
            for key, value in data.__dict__.items():
                if not key.startswith('_') and not callable(value):
                    result[key] = self.prepare_data(value)
            return result
        elif isinstance(data, list):
            return [self.prepare_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.prepare_data(value) for key, value in data.items()}
        elif hasattr(data, 'to_container'):
            # Handle OmegaConf objects
            return OmegaConf.to_container(data)
        else:
            return data

    def render_template(self, template_name, **context):
        """
        Render a template with the given context

        Args:
            template_name: Name of the template file
            context: Variables to pass to the template

        Returns:
            Rendered template as string
        """
        # Prepare context data
        prepared_context = {key: self.prepare_data(value) for key, value in context.items()}

        template = self.env.get_template(template_name)
        return template.render(**prepared_context)

    def render_string(self, template_string, **context):
        """
        Render a template string with the given context

        Args:
            template_string: Template as a string
            context: Variables to pass to the template

        Returns:
            Rendered template as string
        """
        # Prepare context data
        prepared_context = {key: self.prepare_data(value) for key, value in context.items()}

        template = self.env.from_string(template_string)
        return template.render(**prepared_context)