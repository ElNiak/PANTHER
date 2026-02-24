"""Shell command utility functions."""

import logging
import re
import shlex
from typing import TYPE_CHECKING, List, Optional, Tuple

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.core.command_processor.models import ShellCommand


def escape_shell_command(cmd: str) -> str:
    """
    Properly escape a shell command using Python's built-in tools.

    This function handles escaping for different contexts:
    - For single-line commands, it properly quotes the entire command
    - For multiline commands, it preserves the structure while escaping quotes
    - For chained commands with semicolons, each command is properly escaped
    - For commands ending with control operators (&&, ;, &), they are normalized
    - For shell built-in commands like set, export, etc., special handling is applied
    - For commands with complex quoting and variable assignments, special handling is applied
    - For variable assignments (e.g. VAR=value), they are not quoted
    - For shell control structures (if, while, for, until), they are not quoted
    - For commands with redirection operators, redirection parts are preserved

    Args:
        cmd: The shell command to escape

    Returns:
        Escaped shell command safe for inclusion in shell scripts
    """
    # Remove surrounding quotes if they exist
    cmd = cmd.strip()
    if (cmd.startswith('"') and cmd.endswith('"')) or (
        cmd.startswith("'") and cmd.endswith("'")
    ):
        cmd = cmd[1:-1]

    # Handle multiline commands
    if "\n" in cmd:
        lines = cmd.split("\n")
        escaped_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # Process each line separately
                escaped_line = _escape_single_line(line)
                escaped_lines.append(escaped_line)
        return "\n".join(escaped_lines)

    # Handle single line commands
    return _escape_single_line(cmd)


def _escape_single_line(cmd: str) -> str:
    """Escape a single line command."""
    # Check for shell control structures
    control_structures = ["if ", "while ", "for ", "until ", "case ", "function "]
    if any(cmd.startswith(struct) for struct in control_structures):
        return cmd

    # Check for variable assignments
    if "=" in cmd and not cmd.startswith("(") and not " " in cmd.split("=")[0]:
        parts = cmd.split(" ", 1)
        if "=" in parts[0] and not parts[0].startswith("-"):
            # This is a variable assignment
            return cmd

    # Check for shell built-ins
    shell_builtins = ["export", "set", "unset", "source", ".", "eval", "exec"]
    first_word = cmd.split()[0] if cmd.split() else ""
    if first_word in shell_builtins:
        return cmd

    # Handle commands with semicolons
    if ";" in cmd and not cmd.count('"') % 2 and not cmd.count("'") % 2:
        # Split by semicolon, but not within quotes and not escaped semicolons (\;)
        parts = []
        current = []
        in_single_quote = False
        in_double_quote = False
        prev_char = ""

        for char in cmd:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif (
                char == ";"
                and not in_single_quote
                and not in_double_quote
                and prev_char != "\\"
            ):
                parts.append("".join(current).strip())
                current = []
                prev_char = char
                continue
            current.append(char)
            prev_char = char

        if current:
            parts.append("".join(current).strip())

        # If only one part after splitting, the semicolons were all escaped - treat as simple command
        if len(parts) <= 1:
            return _escape_simple_command(parts[0] if parts else cmd)

        escaped_parts = [_escape_simple_command(part) for part in parts if part]
        return " ; ".join(escaped_parts)

    # Handle simple commands
    return _escape_simple_command(cmd)


def _escape_simple_command(cmd: str) -> str:
    """Escape a simple command without complex shell constructs."""
    # Handle redirections
    cmd_without_redir, redirections = parse_command_with_redirections(cmd)

    # Escape the command part
    escaped_cmd = escape_shell_command_without_redirections(cmd_without_redir)

    # Reconstruct with redirections
    if redirections:
        return reconstruct_command_with_redirections(escaped_cmd, redirections)

    return escaped_cmd


def escape_shell_command_without_redirections(cmd: str) -> str:
    """
    Escape a shell command after redirections have been removed.

    Args:
        cmd: Command string without redirections

    Returns:
        Escaped command string
    """
    import re

    # Check if this is a shell control structure that should not be escaped
    control_structure_patterns = [
        r"^\s*\(",  # Commands starting with parentheses (subshells)
        r"^\s*if\s+",  # Conditional statements
        r"^\s*for\s+",  # For loops
        r"^\s*while\s+",  # While loops
        r"^\s*case\s+",  # Case statements
        r"^\s*\{",  # Brace-grouped commands
    ]

    # If this is a control structure, don't escape it (trust it's properly formed)
    for pattern in control_structure_patterns:
        if re.match(pattern, cmd):
            return cmd

    # Use shlex.quote for proper escaping of regular commands
    try:
        # Try to parse the command to see if it's already properly quoted
        parts = shlex.split(cmd)
        # If parsing succeeds, the command is already properly formatted
        return cmd
    except ValueError:
        # If parsing fails, we need to escape it
        # Check for legitimate shell variables/expansions that should NOT be escaped
        import re

        # Patterns for legitimate shell constructs that should be preserved
        shell_variable_patterns = [
            r"\$\?",  # Exit status variable
            r"\$\w+",  # Shell variables like $HOME, $PWD
            r"\$\{\w+\}",  # Shell variables in braces like ${HOME}
            r"\$\(\s*\w+.*?\)",  # Command substitution like $(command)
            r"\$\d+",  # Positional parameters like $1, $2
            r"\$\*",  # All positional parameters
            r"\$@",  # All positional parameters quoted
        ]

        # If the command contains legitimate shell constructs, don't escape the whole thing
        has_shell_constructs = any(
            re.search(pattern, cmd) for pattern in shell_variable_patterns
        )

        if has_shell_constructs:
            # This command contains shell variables/expansions, don't escape it
            return cmd

        # Quote the entire command if it contains special characters but no shell constructs
        if any(char in cmd for char in ["`", "\\", '"', "'"]):
            return shlex.quote(cmd)
        return cmd


def parse_command_with_redirections(cmd: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Parse a command and extract redirection operators.

    Args:
        cmd: Command string potentially containing redirections

    Returns:
        Tuple of (command_without_redirections, list_of_redirections)
        Each redirection is a tuple of (operator, target)
    """
    # Regex to match redirection operators
    # Matches: >, >>, <, <<, 2>, 2>>, &>, &>>
    redirection_pattern = r"(\d*[<>]+&?|\d*&[<>]+)\s*(\S+)"

    redirections = []

    # Find all redirections
    for match in re.finditer(redirection_pattern, cmd):
        operator = match.group(1)
        target = match.group(2)
        redirections.append((operator, target))

    # Remove redirections from command
    cmd_without_redirections = re.sub(redirection_pattern, "", cmd).strip()

    return cmd_without_redirections, redirections


def reconstruct_command_with_redirections(
    cmd: str, redirections: List[Tuple[str, str]]
) -> str:
    """
    Reconstruct a command with its redirections.

    Args:
        cmd: Base command without redirections
        redirections: List of (operator, target) tuples

    Returns:
        Complete command with redirections
    """
    if not redirections:
        return cmd

    result = cmd
    for operator, target in redirections:
        # Preserve conventional shell redirection formatting
        # Common patterns like 2>/dev/null, 2>&1 should not have spaces
        if operator in ("2>", "1>", "2>>", "1>>", "2>&", "1>&") and target in (
            "/dev/null",
            "1",
            "2",
        ):
            result += f" {operator}{target}"
        elif operator.endswith(">&") and target.isdigit():
            # Handle patterns like 2>&1, 1>&2 without spaces
            result += f" {operator}{target}"
        elif operator.endswith(">") and target == "/dev/null":
            # Handle any redirection to /dev/null without spaces
            result += f" {operator}{target}"
        else:
            # Default case with space (for readability in other cases)
            result += f" {operator} {target}"

    return result


def validate_redirection_syntax(cmd: str) -> bool:
    """
    Validate that redirection syntax in a command is correct.

    Common issues this catches:
    - Missing > in redirections (e.g., "2/dev/null" should be "2>/dev/null")
    - Malformed redirection operators

    Args:
        cmd: Command string to validate

    Returns:
        True if redirection syntax is valid, False otherwise
    """
    import re

    # Check for patterns that look like malformed redirections
    malformed_patterns = [
        r"\d+/dev/null",  # Missing > before /dev/null
        r"\d+/\w+",  # Missing > before path-like strings
        r"\s+\d+\s+/\w+",  # Space-separated number and path (should be 2>/path)
    ]

    for pattern in malformed_patterns:
        if re.search(pattern, cmd):
            return False

    return True


def normalize_command_ending(cmd: str) -> str:
    """
    Normalize command endings to ensure consistent behavior.

    This function handles:
    - Commands ending with && (removes it)
    - Commands ending with & (removes it)
    - Commands ending with ; (removes it)

    Args:
        cmd: The command to normalize

    Returns:
        Command with normalized ending
    """
    cmd = cmd.strip()

    # Remove problematic endings
    endings_to_remove = ["&&", "&", ";"]
    for ending in endings_to_remove:
        if cmd.endswith(ending):
            cmd = cmd[: -len(ending)].strip()

    return cmd


def split_complex_command(cmd: str) -> List[str]:
    """
    Split a complex command into individual commands.

    Handles:
    - Commands separated by &&
    - Commands separated by ;
    - Commands separated by ||

    Args:
        cmd: Complex command string

    Returns:
        List of individual commands
    """
    # First, handle quoted sections
    parts = []
    current = []
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(cmd):
        char = cmd[i]

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote:
            # Check for operators
            if i + 1 < len(cmd):
                two_char = cmd[i : i + 2]
                if two_char in ["&&", "||"]:
                    parts.append("".join(current).strip())
                    current = []
                    i += 2
                    continue
            if char == ";":
                # Skip escaped semicolons (\;) used by find -exec
                prev_char = cmd[i - 1] if i > 0 else ""
                if prev_char != "\\":
                    parts.append("".join(current).strip())
                    current = []
                    i += 1
                    continue

        current.append(char)
        i += 1

    if current:
        parts.append("".join(current).strip())

    return [part for part in parts if part]


def combine_shell_constructs(command_list):
    """
    Combine consecutive elements in a command list that form a single shell construct.

    This function detects shell constructs like loops, functions, and conditional blocks
    that are split across multiple list elements and combines them into a single
    multiline command string. This is necessary because shell constructs that span
    multiple lines need to be treated as a single command unit rather than individual
    commands.

    Supported shell constructs:
    - while/done loops
    - for/done loops
    - if/fi conditionals
    - case/esac statements
    - function definitions

    Example:
        Input: ['for i in 1 2 3; do', 'echo $i', 'done']
        Output: ['for i in 1 2 3; do\necho $i\ndone']

    Args:
        command_list: List of command strings or ShellCommand objects to process

    Returns:
        A new list with combined shell constructs as multiline strings or ShellCommand objects.
        Returns an empty list if the input is empty or invalid.
    """
    # Lazy import to avoid circular dependency
    from panther.core.command_processor.models.shell_command import ShellCommand

    logger = logging.getLogger(__name__)

    # Input validation
    if not command_list:
        logger.debug("Empty command list provided to combine_shell_constructs")
        return []

    if not isinstance(command_list, list):
        logger.warning(
            "Invalid command_list type provided to combine_shell_constructs: %s",
            type(command_list),
        )
        return []

    # Filter out empty entries and process both string and ShellCommand objects
    filtered_commands = []
    original_objects = []  # Keep track of original objects

    for cmd in command_list:
        if not cmd:
            continue

        if isinstance(cmd, str):
            if cmd.strip():
                filtered_commands.append(cmd)
                original_objects.append(None)  # No original object for strings
        else:
            # Handle objects that have a command attribute (like ShellCommand)
            if hasattr(cmd, "command") and cmd.command and cmd.command.strip():
                filtered_commands.append(cmd.command)
                original_objects.append(cmd)  # Store the original object

    if not filtered_commands:
        logger.debug("No valid commands found in command_list after filtering")
        return []

    # Use filtered commands for processing
    logger.debug(
        "Processing %d commands in shell construct combination", len(filtered_commands)
    )

    # Track shell constructs we're looking for
    construct_patterns = {
        "while": {
            "start": ["while"],
            "end": ["done"],
            "patterns": [
                # while condition; do
                lambda s: s.strip()
                .lower()
                .startswith("while "),
            ],
        },
        "for": {
            "start": ["for"],
            "end": ["done"],
            "patterns": [
                # for var in list; do
                lambda s: s.strip()
                .lower()
                .startswith("for "),
            ],
        },
        "if": {
            "start": ["if"],
            "end": ["fi"],
            "patterns": [
                # if condition; then
                lambda s: s.strip()
                .lower()
                .startswith("if "),
            ],
        },
        "case": {
            "start": ["case"],
            "end": ["esac"],
            "patterns": [
                # case var in
                lambda s: s.strip()
                .lower()
                .startswith("case "),
            ],
        },
        "function": {
            "start": ["function", "() {", "(){"],
            "end": ["}"],
            # Additional patterns to identify function definitions
            "patterns": [
                # function name() { ... }
                lambda s: s.strip().lower().startswith("function ")
                and ("() {" in s or "(){" in s),
                # name() { ... }
                lambda s: ("() {" in s or "(){" in s)
                and not s.strip().lower().startswith("function "),
                # function name { ... }
                lambda s: s.strip().lower().startswith("function ") and "{" in s,
            ],
        },
    }

    result = []
    construct_buffer = []
    construct_buffer_originals = []  # Track original objects for buffered commands
    active_constructs = []

    for i, cmd in enumerate(filtered_commands):
        # Skip empty commands (should not happen after filtering)
        if not cmd or not cmd.strip():
            continue

        cmd_lower = cmd.lower().strip()
        first_word = cmd_lower.split()[0] if cmd_lower.split() else ""

        # Check if this line starts a new construct
        starts_construct = False
        for construct, patterns in construct_patterns.items():
            # First check for explicit patterns if defined
            if "patterns" in patterns:
                for pattern_func in patterns["patterns"]:
                    if pattern_func(cmd):
                        starts_construct = True
                        active_constructs.append(construct)
                        logger.debug(
                            "Starting %s construct (pattern match): %s",
                            construct,
                            cmd.strip()[:40],
                        )
                        break
                if starts_construct:
                    break

            # Then check for start keywords
            if not starts_construct and any(p in cmd_lower for p in patterns["start"]):
                # For function definitions
                if construct == "function":
                    # Check for the two common function definition styles:
                    # 1. function name() { ... }
                    # 2. name() { ... }
                    if (
                        "function " in cmd_lower
                        or (
                            any(
                                cmd_lower.find(f"{c}") > -1
                                for c in ["() {", "(){", "()\n{", "() \n{"]
                            )
                        )
                        or (
                            cmd_lower.rstrip().endswith("{")
                            and "(" in cmd_lower
                            and ")" in cmd_lower
                        )
                    ):
                        starts_construct = True
                        active_constructs.append(construct)
                        logger.debug(
                            "Starting %s construct (keyword match): %s",
                            construct,
                            cmd.strip()[:40],
                        )
                        break
                # For other constructs, check if it's the first word
                elif first_word in patterns["start"]:
                    starts_construct = True
                    active_constructs.append(construct)
                    logger.debug(
                        "Starting %s construct (first word match): %s",
                        construct,
                        cmd.strip()[:40],
                    )
                    break

        # Check if this line ends an active construct
        ends_construct = False
        if active_constructs:
            current_construct = active_constructs[-1]
            end_patterns = construct_patterns[current_construct]["end"]

            # Check for end patterns in the command
            if any(p in cmd_lower for p in end_patterns):
                # For closing braces of functions, ensure it's not part of another construct
                if current_construct == "function" and "}" in cmd_lower:
                    # Make sure it's a standalone "}" or at the end of a line
                    if (
                        cmd_lower == "}"
                        or cmd_lower.endswith("}")
                        or cmd_lower.endswith("};")
                    ):
                        ends_construct = True
                        active_constructs.pop()
                        logger.debug(
                            "Ending %s construct: %s",
                            current_construct,
                            cmd.strip()[:40],
                        )
                # For other end patterns
                else:
                    # Make sure the end pattern appears as a complete word
                    for pattern in end_patterns:
                        if pattern in cmd_lower.split() or cmd_lower.endswith(
                            pattern + ";"
                        ):
                            ends_construct = True
                            active_constructs.pop()
                            logger.debug(
                                "Ending %s construct: %s",
                                current_construct,
                                cmd.strip()[:40],
                            )
                            break

        # Buffer the current command and its original object
        construct_buffer.append(cmd)
        construct_buffer_originals.append(original_objects[i])

        # If we've ended all active constructs or encountered a standalone command
        if (ends_construct and not active_constructs) or (
            not starts_construct and not active_constructs
        ):
            # If we have only one command in buffer and it's not part of a construct, add it as is
            if (
                len(construct_buffer) == 1
                and not starts_construct
                and not ends_construct
            ):
                # If the original command was a ShellCommand, return the original object
                original_obj = construct_buffer_originals[0]
                if original_obj is not None:
                    result.append(original_obj)
                else:
                    result.append(construct_buffer[0])
            else:
                # Join the buffered commands into a single multiline command
                multiline_cmd = "\n".join(construct_buffer)

                # Check if any of the original commands were ShellCommand objects
                has_shell_command = any(
                    obj is not None for obj in construct_buffer_originals
                )

                if has_shell_command:
                    # Find the first ShellCommand object to use as a template
                    shell_cmd_template = None
                    for obj in construct_buffer_originals:
                        if obj is not None:
                            shell_cmd_template = obj
                            break

                    if shell_cmd_template and hasattr(shell_cmd_template, "command"):
                        # Create a new ShellCommand object based on the template
                        # Check if this is a function definition and adjust the description accordingly
                        description = getattr(
                            shell_cmd_template,
                            "description",
                            "Combined shell construct",
                        )
                        if "\n" in multiline_cmd and (
                            "() {" in multiline_cmd.split("\n")[0]
                            or "(){" in multiline_cmd.split("\n")[0]
                            or "function " in multiline_cmd.lower().split("\n")[0]
                        ):
                            # Extract function name for better description
                            first_line = multiline_cmd.split("\n")[0].strip().lower()
                            if "function " in first_line:
                                fn_name = (
                                    first_line.replace("function ", "")
                                    .split("{")[0]
                                    .strip()
                                )
                                if "(" in fn_name:
                                    fn_name = fn_name.split("(")[0].strip()
                            else:  # name() { syntax
                                fn_name = first_line.split("(")[0].strip()

                            # Use plain function name without special characters in description
                            description = f"Function: {fn_name}"
                            logger.debug(
                                f"Setting safer function description for combined construct: {fn_name}"
                            )

                        new_shell_cmd = ShellCommand(
                            command=multiline_cmd,
                            description=description,
                            is_critical=getattr(
                                shell_cmd_template, "is_critical", False
                            ),
                            is_multiline=True,
                            is_function_definition=getattr(
                                shell_cmd_template, "is_function_definition", False
                            ),
                            is_function_call=getattr(
                                shell_cmd_template, "is_function_call", False
                            ),
                        )
                        result.append(new_shell_cmd)
                    else:
                        result.append(multiline_cmd)
                else:
                    result.append(multiline_cmd)

                # Identify the type of construct for better logging
                construct_type = "unknown"
                if construct_buffer and construct_buffer[0]:
                    first_line = construct_buffer[0].strip().lower()
                    if (
                        "function " in first_line
                        or "() {" in first_line
                        or "(){" in first_line
                    ):
                        construct_type = "function definition"
                    elif first_line.startswith("if "):
                        construct_type = "if block"
                    elif first_line.startswith("for "):
                        construct_type = "for loop"
                    elif first_line.startswith("while "):
                        construct_type = "while loop"
                    elif first_line.startswith("case "):
                        construct_type = "case statement"

                logger.debug(
                    "Combined %s into multiline command: %s",
                    construct_type,
                    multiline_cmd.split("\n")[0].strip()[:40] + "...",
                )
            construct_buffer = []
            construct_buffer_originals = []

    # Handle any remaining commands in the buffer
    if construct_buffer:
        # If we have incomplete constructs (active_constructs not empty), log a warning
        if active_constructs:
            logger.warning(
                "Incomplete shell construct detected: %s. Commands: %s",
                active_constructs,
                [
                    cmd.strip()[:40] + "..." if len(cmd) > 40 else cmd
                    for cmd in construct_buffer
                ],
            )

        # Still combine the remaining commands to avoid losing them
        multiline_cmd = "\n".join(construct_buffer)

        # Check if any of the original commands were ShellCommand objects
        has_shell_command = any(obj is not None for obj in construct_buffer_originals)

        if has_shell_command:
            # Find the first ShellCommand object to use as a template
            shell_cmd_template = None
            for obj in construct_buffer_originals:
                if obj is not None:
                    shell_cmd_template = obj
                    break

            if shell_cmd_template and hasattr(shell_cmd_template, "command"):
                # Create a new ShellCommand object from the template
                new_shell_cmd = ShellCommand(
                    command=multiline_cmd,
                    description=getattr(
                        shell_cmd_template, "description", "Combined shell construct"
                    ),
                    is_critical=getattr(shell_cmd_template, "is_critical", False),
                    is_multiline=True,
                    is_function_definition=getattr(
                        shell_cmd_template, "is_function_definition", False
                    ),
                    is_function_call=getattr(
                        shell_cmd_template, "is_function_call", False
                    ),
                )
                result.append(new_shell_cmd)
            else:
                result.append(multiline_cmd)
        else:
            result.append(multiline_cmd)

        logger.debug(
            "Combined remaining commands into multiline command: %s",
            multiline_cmd.split("\n")[0].strip()[:40] + "...",
        )

    # Final validation - make sure we don't return empty result
    if not result:
        logger.warning(
            "Shell construct combination resulted in empty list. Original commands: %s",
            [
                str(cmd)[:40] + "..." if len(str(cmd)) > 40 else str(cmd)
                for cmd in command_list[:5]
            ],
        )

        # If we have original ShellCommand objects, return those
        if any(obj is not None for obj in original_objects):
            return [
                obj if obj is not None else cmd
                for cmd, obj in zip(filtered_commands, original_objects)
            ]

        # Otherwise return filtered string commands
        return filtered_commands

    return result
