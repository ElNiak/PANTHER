"""Constants for command processing.

Centralizes shell-related constant lists used by ``ShellCommand``,
``CommandValidator``, ``escape_shell_command``, and ``combine_shell_constructs``
to ensure consistent detection and escaping behavior across the module.

Constants:
    SHELL_CONTROL_OPERATORS: Operators that chain or redirect commands
        (``&&``, ``||``, ``;``, ``&``, ``|``, ``>``, ``>>``, ``<<``, ``<``).
    SHELL_BUILTINS: Commands built into the shell that should not be quoted
        (``export``, ``cd``, ``echo``, ``set``, etc.).
    SHELL_CONTROL_STRUCTURES: Keywords that begin or delimit control-flow
        blocks (``if``, ``then``, ``fi``, ``for``, ``done``, ``case``,
        ``esac``, ``function``, etc.).
    REDIRECTION_OPERATORS: I/O redirection operators that must be preserved
        literally during escaping (``>``, ``>>``, ``2>``, ``&>``, etc.).
"""

# Shell control operators that could cause issues if they appear at the end of a command
SHELL_CONTROL_OPERATORS = ["&&", "||", ";", "&", "|", ">", ">>", "<<", "<"]

# Shell built-in commands that should not be quoted
SHELL_BUILTINS = [
    "set",
    "export",
    "source",
    "unset",
    ".",
    "alias",
    "bg",
    "bind",
    "builtin",
    "caller",
    "cd",
    "command",
    "compgen",
    "complete",
    "declare",
    "dirs",
    "disown",
    "echo",
    "enable",
    "eval",
    "exec",
    "exit",
    "fc",
    "fg",
    "getopts",
    "hash",
    "help",
    "history",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "mapfile",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "readarray",
    "readonly",
    "return",
    "shift",
    "shopt",
    "suspend",
    "test",
    "times",
    "trap",
    "type",
    "typeset",
    "ulimit",
    "umask",
    "unalias",
    "wait",
]

# Shell control structures that shouldn't be quoted
SHELL_CONTROL_STRUCTURES = [
    "if",
    "then",
    "else",
    "elif",
    "fi",
    "case",
    "esac",
    "for",
    "while",
    "until",
    "do",
    "done",
    "select",
    "function",
]

# Additional redirection operators that should not be escaped
REDIRECTION_OPERATORS = [">", ">>", "<", "<<", "2>", "2>>", "&>", "&>>", "|&"]
