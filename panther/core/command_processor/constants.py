"""
Constants for command processing.

This module contains all the constants used across the command processor module.
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