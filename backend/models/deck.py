"""
Deck models — Indexed deck metadata and analysis fields.
Maps to the deep library analysis from PRD Section 4.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeckAnalysis(BaseModel):
    """Full pedagogical and stylistic analysis of a single deck.
    These are the 10 analysis fields from PRD Section 4.1."""
    learning_arc: Optional[str] = None
    tone_profile: Optional[str] = None
    assumed_knowledge_level: Optional[str] = None
    frameworks_and_models: list[str] = Field(default_factory=list)
    activity_design: Optional[str] = None
    client_industry_signals: Optional[str] = None
    content_domain_tags: list[str] = Field(default_factory=list)
    slide_type_sequence: list[str] = Field(default_factory=list)
    complexity_arc: Optional[str] = None
    recurring_language_patterns: list[str] = Field(default_factory=list)


class Deck(BaseModel):
    """An indexed deck from the OneDrive repository."""
    id: str
    filename: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    module_name: Optional[str] = None  # Parent folder / module context
    topic_tags: list[str] = Field(default_factory=list)
    slide_count: int = 0
    file_size: Optional[int] = None  # File size in bytes
    slide_titles: list[str] = Field(default_factory=list)  # Extracted slide titles
    analysis: Optional[DeckAnalysis] = None
    summary: Optional[str] = None  # 150-200 word natural language summary
    master_template_ref: Optional[str] = None
    onedrive_path: Optional[str] = None
    file_hash: Optional[str] = None  # MD5 of first 8KB for change detection
    indexed_at: Optional[datetime] = None
    analyzed_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None


class LibraryProfile(BaseModel):
    """Cross-deck intelligence synthesized from the full library.
    From PRD Section 4.3."""
    common_slide_sequences: list[str] = Field(default_factory=list)
    frequent_frameworks: list[str] = Field(default_factory=list)
    tone_by_industry: dict[str, str] = Field(default_factory=dict)
    activity_by_format: dict[str, list[str]] = Field(default_factory=dict)
    total_decks_analyzed: int = 0
    last_updated: Optional[datetime] = None


class DeckListResponse(BaseModel):
    """Paginated list of indexed decks."""
    decks: list[Deck] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20
