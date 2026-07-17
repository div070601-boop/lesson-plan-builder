"""
Library Service — Deck repository browsing backed by Supabase cache.
Reads deck metadata from Supabase `decks` table for fast serving.
Falls back to filesystem scan + analysis if Supabase is empty.
"""

import json
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from models.deck import Deck, DeckAnalysis, DeckListResponse, LibraryProfile
from services.onedrive import local_library

logger = logging.getLogger(__name__)

# In-memory cache loaded from Supabase on startup
_deck_cache: list[Deck] = []
_cache_loaded: bool = False


def _deck_to_db_row(deck: Deck) -> dict:
    """Convert a Deck pydantic model to a Supabase row dict."""
    return {
        "id": deck.id,
        "filename": deck.filename,
        "file_size": deck.file_size,
        "client_id": deck.client_id,
        "client_name": deck.client_name,
        "module_name": deck.module_name,
        "topic_tags": deck.topic_tags,
        "slide_count": deck.slide_count,
        "slide_titles": deck.slide_titles,
        "analysis": deck.analysis.model_dump() if deck.analysis else None,
        "summary": deck.summary,
        "onedrive_path": deck.onedrive_path,
        "file_hash": deck.file_hash,
        "indexed_at": deck.indexed_at.isoformat() if deck.indexed_at else None,
        "analyzed_at": deck.analyzed_at.isoformat() if deck.analyzed_at else None,
    }


def _db_row_to_deck(row: dict) -> Deck:
    """Convert a Supabase row dict back to a Deck model."""
    analysis = None
    if row.get("analysis"):
        analysis_data = row["analysis"]
        if isinstance(analysis_data, str):
            analysis_data = json.loads(analysis_data)
        analysis = DeckAnalysis(**analysis_data)

    return Deck(
        id=row["id"],
        filename=row["filename"],
        file_size=row.get("file_size"),
        client_id=row.get("client_id"),
        client_name=row.get("client_name"),
        module_name=row.get("module_name"),
        topic_tags=row.get("topic_tags", []),
        slide_count=row.get("slide_count", 0),
        slide_titles=row.get("slide_titles", []),
        analysis=analysis,
        summary=row.get("summary"),
        onedrive_path=row.get("onedrive_path"),
        file_hash=row.get("file_hash"),
        indexed_at=datetime.fromisoformat(row["indexed_at"]) if row.get("indexed_at") else None,
        analyzed_at=datetime.fromisoformat(row["analyzed_at"]) if row.get("analyzed_at") else None,
    )


def load_cache_from_supabase() -> list[Deck]:
    """Load all decks from Supabase into memory cache. Called on startup."""
    global _deck_cache, _cache_loaded
    from services.database import supabase

    if supabase:
        try:
            res = supabase.table("decks").select("*").execute()
            if res.data:
                _deck_cache = [_db_row_to_deck(row) for row in res.data]
                _cache_loaded = True
                logger.info(f"Loaded {len(_deck_cache)} decks from Supabase cache")
                return _deck_cache
        except Exception as e:
            logger.warning(f"Failed to load decks from Supabase (table may not exist yet): {e}")

    _cache_loaded = True
    return _deck_cache


def upsert_deck_to_cache(deck: Deck):
    """Upsert a single deck into both Supabase and in-memory cache."""
    global _deck_cache
    from services.database import supabase

    # Update in-memory cache
    _deck_cache = [d for d in _deck_cache if d.id != deck.id]
    _deck_cache.append(deck)

    # Persist to Supabase
    if supabase:
        try:
            row = _deck_to_db_row(deck)
            supabase.table("decks").upsert(row).execute()
        except Exception as e:
            logger.warning(f"Failed to upsert deck {deck.filename} to Supabase: {e}")


def get_cached_file_hashes() -> dict[str, str]:
    """Return {filename: file_hash} from the current cache for change detection."""
    return {d.filename: (d.file_hash or "") for d in _deck_cache}


class LibraryService:
    """Serves deck metadata from Supabase cache with filesystem fallback."""

    def _get_all_decks(self) -> list[Deck]:
        global _deck_cache, _cache_loaded

        # Load from Supabase if not done yet
        if not _cache_loaded:
            load_cache_from_supabase()

        # If we have cached data, use it
        if _deck_cache:
            return _deck_cache.copy()

        # Fallback: scan filesystem and analyze
        local_files = local_library.list_all_files(extensions=[".pptx", ".ppt"])
        if not local_files:
            return []

        from services.deck_analyzer import analyze_pptx

        decks = []
        library_base = str(local_library.library_path.resolve())
        for item in local_files:
            filepath = str(Path(library_base) / item.path)
            deck = analyze_pptx(filepath, onedrive_path=item.path)
            if deck:
                decks.append(deck)
                upsert_deck_to_cache(deck)

        _deck_cache = decks
        return decks.copy()

    async def list_decks(
        self,
        query: Optional[str] = None,
        client_id: Optional[str] = None,
        domain: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> DeckListResponse:
        """List decks with optional filtering."""
        all_decks = self._get_all_decks()
        filtered = all_decks.copy()

        if query:
            q = query.lower()
            filtered = [
                d for d in filtered
                if q in d.filename.lower()
                or q in (d.summary or "").lower()
                or q in (d.client_name or "").lower()
                or q in (d.module_name or "").lower()
                or any(q in t for t in d.topic_tags)
                or any(q in t.lower() for t in d.slide_titles)
            ]

        if client_id:
            filtered = [d for d in filtered if d.client_id == client_id]

        if domain:
            filtered = [d for d in filtered if domain in d.topic_tags]

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated = filtered[start:end]

        return DeckListResponse(
            decks=paginated,
            total=len(filtered),
            page=page,
            per_page=per_page,
        )

    async def get_deck(self, deck_id: str) -> Optional[Deck]:
        """Get a specific deck by ID."""
        for deck in self._get_all_decks():
            if deck.id == deck_id:
                return deck
        return None

    async def get_profile(self) -> LibraryProfile:
        """Get the cross-deck library profile."""
        all_decks = self._get_all_decks()

        # Aggregate frameworks across all decks
        fw_counts: dict[str, int] = {}
        tone_map: dict[str, str] = {}
        for d in all_decks:
            if d.analysis:
                for fw in d.analysis.frameworks_and_models:
                    fw_counts[fw] = fw_counts.get(fw, 0) + 1
                if d.client_name and d.analysis.tone_profile:
                    tone_map[d.client_name.lower()] = d.analysis.tone_profile

        frequent_fw = sorted(fw_counts, key=fw_counts.get, reverse=True)[:8]

        return LibraryProfile(
            common_slide_sequences=[
                "title → agenda → objectives → content → activity → summary",
                "title → objectives → framework_intro → case_study → activity → debrief → summary",
            ],
            frequent_frameworks=frequent_fw,
            tone_by_industry=tone_map,
            activity_by_format={
                "in_person": ["group_discussion", "paired_exercise", "case_study", "role_play"],
                "virtual": ["breakout_room", "poll", "chat_reflection", "shared_whiteboard"],
                "hybrid": ["group_discussion", "poll", "individual_reflection"],
            },
            total_decks_analyzed=len(all_decks),
            last_updated=datetime.now(),
        )
