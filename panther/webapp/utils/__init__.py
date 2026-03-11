"""PANTHER webapp utilities --- form-model introspection and plugin-to-form bridging.

This package provides helpers that sit between the PANTHER plugin/config
systems and the webapp's form rendering layer.  They are used primarily
by ``PydanticForm`` and the config builder page.

Module inventory
----------------

``form_models``
    Type-introspection utilities for Pydantic config models.  Provides
    ``ComplexFieldInfo`` (a ``NamedTuple`` classifying fields as
    ``dict_str``, ``dict_model``, or ``list_model``), helper functions
    like ``get_complex_fields()``, and ``GLOBAL_SECTION_META`` with UI
    metadata (icons, descriptions) for top-level config sections.

``plugin_forms``
    Bridge between the PANTHER plugin system and the form layer.
    Discovers plugins via ``PluginManager``, extracts their config
    schemas (``config_schema.py`` per plugin), and produces
    ``PluginFormInfo`` dataclass instances that ``PydanticForm`` uses
    to render plugin-specific configuration fields.  Includes a
    process-wide discovery cache to avoid repeated filesystem scans.

See Also:
--------
panther.webapp.components.pydantic_form : Form renderer that consumes these utilities.
panther.webapp.components.dict_list_widgets : Custom widgets for complex field types.
panther.plugins : Plugin discovery and registration system.
"""
