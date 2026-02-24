"""
Tester Plugin Event Mixin Module
This module provides the tester-specific event emission facade.
"""

from panther.plugins.services.service_event_mixin import ServiceManagerEventMixin


class TesterManagerEventMixin(ServiceManagerEventMixin):
    """Tester event emission facade for naming clarity.

    All event methods are inherited from ServiceManagerEventMixin.
    This facade exists so tester consumers can import from a semantically
    meaningful location without breaking existing import paths.

    MRO: TesterManagerEventMixin -> ServiceManagerEventMixin
    """

    pass
