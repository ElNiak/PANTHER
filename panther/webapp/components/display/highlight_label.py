"""HighlightLabel — a label that highlights matching substrings.

Wraps ``ui.label`` and applies ``<mark>`` tags around query match
substrings, making it useful for search result highlighting in tables
and detail views.

Example::

    from panther.webapp.components.display.highlight_label import highlight_label

    highlight_label("Hello World", "World", "my-class")
    # Renders: Hello <mark>World</mark>
"""

import html
import re

from nicegui import ui


def highlight_html(text: object, query: str = "") -> str:
    """Return escaped HTML with every query match wrapped in a highlight span."""
    escaped = html.escape(str(text))
    if not query:
        return escaped

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(
        lambda match: f'<span class="panther-highlight">{match.group(0)}</span>',
        escaped,
    )


def live_status(text: str = "") -> ui.label:
    """Render an inline status message suitable for dynamic filter feedback."""
    return (
        ui.label(text)
        .classes("panther-inline-status text-caption text-grey-7")
        .props("role=status aria-live=polite")
    )


def highlight_label(text: str, query: str = "", extra_classes: str = "") -> ui.label:
    """Render a label with matching substrings wrapped in ``<mark>`` tags.

    The search is case-insensitive. Matching occurrences of *query*
    inside *text* are wrapped in highlight markup. If *query* is empty, the text is
    rendered as-is.

    Args:
        text: The full text string to display.
        query: The search term to highlight.
        extra_classes: Additional CSS classes to apply to the label
            (e.g., ``"text-body2"``).

    Returns:
        The ``ui.label`` instance.
    """
    label = ui.label()
    label.element.inner_html = highlight_html(text, query)
    if extra_classes:
        label.classes(extra_classes)
    return label


class HighlightLabel:
    """Component wrapper for ``highlight_label``, usable in both class and functional styles."""

    @staticmethod
    def render(text: str, query: str = "", extra_classes: str = "") -> ui.label:
        """Render a highlighted label (alias for the module-level function)."""
        return highlight_label(text, query, extra_classes)
