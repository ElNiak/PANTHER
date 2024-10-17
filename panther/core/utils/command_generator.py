# panther/utils/command_generator.py

import logging
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

class CommandGenerator:
    def __init__(self, templates_dir: str = "panther/templates/commands"):
        self.logger = logging.getLogger("CommandGenerator")
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['yaml', 'yml', 'xml', 'html'])
        )

    def load_template(self, template_name: str) -> Template:
        """
        Loads a Jinja2 template by name.
        """
        try:
            template = self.env.get_template(template_name)
            self.logger.debug(f"Loaded template '{template_name}'")
            return template
        except Exception as e:
            self.logger.error(f"Failed to load template '{template_name}': {e}")
            raise e

    def render_command(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Renders a command string based on the template and context.
        """
        try:
            template = self.load_template(template_name)
            command = template.render(context)
            self.logger.debug(f"Rendered command using template '{template_name}': {command}")
            return command.strip()
        except Exception as e:
            self.logger.error(f"Failed to render command from template '{template_name}': {e}")
            raise e

    def generate_command_list(self, config: Dict[str, Any], extra_context: Dict[str, Any] = {}) -> str:
        """
        Generates the command string based on the provided configuration and extra context.
        """
        template_name = config.get("template")
        if not template_name:
            self.logger.error("No template specified in configuration.")
            raise ValueError("Template not specified.")
        
        # Prepare the context for rendering
        context = {
            "executable": config.get("executable"),
            "parameters": config.get("parameters", {}),
            "additional_options": config.get("additional_options", "")
        }
        
        # Merge any extra context (e.g., environment variables)
        context.update(extra_context)

        command = self.render_command(template_name, context)
        return command
