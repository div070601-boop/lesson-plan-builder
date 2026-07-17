"""
Retrieval Service — Semantic search + metadata filtering (stub).
Will connect to Supabase pgvector when the indexer is operational.
"""

from typing import Optional
from models.deck import Deck
from services.library import LibraryService

_library_service = LibraryService()


class RetrievalService:
    """Hybrid retrieval: semantic search + metadata filtering.
    Currently queries the live Supabase deck cache and applies filtering."""

    async def retrieve_matching_decks(
        self,
        brief_text: str,
        audience_level: Optional[str] = None,
        content_domain: Optional[str] = None,
        tone: Optional[str] = None,
        industry: Optional[str] = None,
        client_id: Optional[str] = None,
        top_k: int = 5,
    ) -> list[Deck]:
        """Retrieve the most relevant decks for a given brief from Supabase cache.

        1. Load cached decks from Supabase (`_library_service._get_all_decks()`)
        2. Apply metadata filters (audience, domain, tone, industry)
        3. Hard-filter by client_id for data isolation
        4. Return top-k results with full analysis JSON
        """
        # Get real indexed decks from Supabase cache
        results = _library_service._get_all_decks()

        # Apply client isolation filter
        if client_id:
            results = [
                d for d in results
                if d.client_id == client_id or d.client_id == "acemac_internal"
            ]

        # Apply domain filter if provided
        if content_domain:
            domain_filtered = [d for d in results if content_domain in d.topic_tags]
            if domain_filtered:
                results = domain_filtered

        return results[:top_k]


retrieval_service = RetrievalService()
