"""Backward-compatible MAWAQIT helpers.

New application code should use :mod:`prayer_sync.providers.mawaqit` through
the provider registry.  These re-exports preserve the historical module API.
"""

from .providers.mawaqit import CANONICAL_PRAYERS, extract_conf_data, fetch_html, today_prayer_times

__all__ = ("CANONICAL_PRAYERS", "extract_conf_data", "fetch_html", "today_prayer_times")
