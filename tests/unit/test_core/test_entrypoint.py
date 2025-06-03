from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from panther.utils.command import ShellCommand

# Load the templates
templates_dir = Path('/Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/network_environment/docker_compose/templates')
env = Environment(loader=FileSystemLoader(templates_dir))
env.filters['quote_shell'] = lambda s: s

# Create ShellCommand objects
commands = {
    "pre_compile_cmds": [
        ShellCommand(command="set -x;", description="Enable command tracing"),
        ShellCommand(
            command='export PS4="+ [${BASH_SOURCE:-sh}:${LINENO}] ";',
            description="Configure PS4 variable for enhanced debug output"
        ),
        ShellCommand(command="export SHELLOPTS", description="Export shell options"),
        ShellCommand(command="export PATH=$PATH:$ADDITIONAL_PATH;", description="Set PATH"),
        ShellCommand(command="export PYTHONPATH=$PYTHONPATH:$ADDITIONAL_PYTHONPATH;", description="Set PYTHONPATH"),
    ],
    "compile_cmds": [],
    "post_compile_cmds": [],
    "pre_run_cmds": [],
    "post_run_cmds": [],
    "run_cmd": None
}

# Convert ShellCommand objects to their command strings for the template
structured_commands = {
    "pre_compile_cmds": [cmd.command for cmd in commands["pre_compile_cmds"]],
    "compile_cmds": [],
    "post_compile_cmds": [],
    "pre_run_cmds": [],
    "post_run_cmds": []
}

# Try both templates
template = env.get_template('entrypoint_structured.sh.jinja')
result = template.render(
    structured_commands=structured_commands,
    additional_param={"service_name": "test_service"}
)

with open('/tmp/test_entrypoint.sh', 'w') as f:
    f.write(result)

print("Template rendered to /tmp/test_entrypoint.sh")
