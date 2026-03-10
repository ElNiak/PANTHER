"""Singleton form — renders a NiceCRUD inline for single-instance configs.

Uses ``NiceCRUD`` (not ``NiceCRUDCard``) to avoid the shared
``@ui.refreshable`` descriptor bug where deferred timer callbacks
all render the last-created card's fields.
"""

from niceguicrud import NiceCRUD, NiceCRUDConfig
from pydantic import BaseModel


class SingletonForm:
    """Inline form for a single BaseModel instance (no table, no buttons).

    Wraps ``NiceCRUD`` with hidden add/delete buttons to provide the same
    ``.basemodels`` interface that ``config_form_panel`` and
    ``_sync_forms_to_yaml`` expect.
    """

    def __init__(  # noqa: D107
        self,
        model_cls: type[BaseModel],
        instance: BaseModel | None = None,
        config: NiceCRUDConfig | None = None,
    ):
        self._instance = instance or model_cls()
        self._config = config or NiceCRUDConfig()
        self._crud = NiceCRUD(
            model_cls,
            basemodels=[self._instance],
            config=self._config,
        )
        self._crud.button_row.set_visibility(False)

    @property
    def basemodels(self) -> list[BaseModel]:
        """Compatibility with NiceCRUD — always returns a single-element list."""
        return self._crud.basemodels

    def set_instance(self, instance: BaseModel) -> None:
        """Replace the current instance (for YAML -> Form population)."""
        self._crud.basemodels = [instance]
