"""
History models — Generation history entries for search and display.
Maps to PRD Section 3.5 and Build Scope (Output and History).
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HistoryEntry(BaseModel):
    """A single generation history record."""
    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    brief_summary: str = ""
    client_name: Optional[str] = None
    client_id: Optional[str] = None
    generation_id: str
    slide_count: int = 0
    branding_mode: Optional[str] = None
    source_decks: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    download_url: Optional[str] = None
    is_expired: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class HistoryListResponse(BaseModel):
    """Paginated and filterable history list."""
    entries: list[HistoryEntry] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20


class HistorySearchParams(BaseModel):
    """Search and filter parameters for history."""
    query: Optional[str] = None
    client_name: Optional[str] = None
    user_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    per_page: int = 20
