"""
History Service — Generation history storage and search.
"""

from typing import Optional
from datetime import datetime
from models.history import HistoryEntry, HistoryListResponse, HistorySearchParams

# In-memory store for v1
_history: list[HistoryEntry] = []


class HistoryService:
    """Manages generation history."""

    async def add_entry(self, entry: HistoryEntry) -> HistoryEntry:
        """Add a new history entry."""
        _history.insert(0, entry)
        return entry

    async def search(self, params: HistorySearchParams) -> HistoryListResponse:
        """Search and filter history entries."""
        filtered = _history.copy()

        if params.query:
            q = params.query.lower()
            filtered = [
                e for e in filtered
                if q in e.brief_summary.lower() or q in (e.client_name or "").lower()
            ]

        if params.client_name:
            filtered = [e for e in filtered if e.client_name == params.client_name]

        if params.user_id:
            filtered = [e for e in filtered if e.user_id == params.user_id]

        if params.date_from:
            filtered = [e for e in filtered if e.created_at >= params.date_from]

        if params.date_to:
            filtered = [e for e in filtered if e.created_at <= params.date_to]

        total = len(filtered)
        start = (params.page - 1) * params.per_page
        end = start + params.per_page
        page_entries = filtered[start:end]

        return HistoryListResponse(
            entries=page_entries,
            total=total,
            page=params.page,
            per_page=params.per_page,
        )

    async def get_entry(self, history_id: str) -> Optional[HistoryEntry]:
        """Get a specific history entry."""
        for entry in _history:
            if entry.id == history_id:
                return entry
        return None
