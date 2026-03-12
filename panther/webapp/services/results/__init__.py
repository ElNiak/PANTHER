"""Results service package — browsing, analysis, and charting of experiment results.

Split into mixins by concern:
- ``results_service`` — facade class + experiment-level methods
- ``test_data_mixin`` — per-test data access (listing, detail, events, logs)
- ``analytics_mixin`` — summaries, metrics, aggregation
"""

from panther.webapp.services.results.results_service import ResultsService

__all__ = ["ResultsService"]
