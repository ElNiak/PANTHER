"""
IUT Plugin Event Mixin Module
This module provides the IUT-specific event emission facade.
"""

from panther.plugins.services.service_event_mixin import ServiceManagerEventMixin


class IUTManagerEventMixin(ServiceManagerEventMixin):
    """IUT event emission facade for naming clarity.

    All event methods are inherited from ServiceManagerEventMixin.
    This facade exists so IUT consumers can import from a semantically
    meaningful location without breaking existing import paths.
    """

    pass
