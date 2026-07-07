"""
History Router — Generation history endpoints.
Searchable, per-user or shared (PRD Build Scope: Output and History).
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from models.history import HistoryEntry, HistoryListResponse, HistorySearchParams
from services.history import HistoryService

router = APIRouter(prefix="/api/history", tags=["history"])
history_service = HistoryService()


@router.get("", response_model=HistoryListResponse)
async def list_history(
    query: Optional[str] = Query(None, description="Search query"),
    client_name: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List generation history with optional search and filtering.
    History is shared across the Acemac and Moonfly team."""
    params = HistorySearchParams(
        query=query,
        client_name=client_name,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return await history_service.search(params)


@router.get("/{history_id}", response_model=HistoryEntry)
async def get_history_entry(history_id: str):
    """Get a specific history entry with full metadata."""
    entry = await history_service.get_entry(history_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    return entry
