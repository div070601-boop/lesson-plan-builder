"""
Retrieval Service — Semantic search + metadata filtering (stub).
Will connect to Supabase pgvector when the indexer is operational.
"""

from typing import Optional
from models.deck import Deck
from services.library import MOCK_DECKS


class RetrievalService:
    """Hybrid retrieval: semantic search + metadata filtering.
    Currently returns mock results. Will use Supabase pgvector in production."""

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
        """Retrieve the most relevant decks for a given brief.

        In production, this will:
        1. Embed the brief text using Gemini embeddings
        2. Query Supabase pgvector for semantic similarity
        3. Apply metadata filters (audience, domain, tone, industry)
        4. Hard-filter by client_id for data isolation
        5. Return top-k results with full analysis JSON
        """
        # For now, return all mock decks
        results = MOCK_DECKS.copy()

        # Apply client isolation filter
        if client_id:
            results = [
                d for d in results
                if d.client_id == client_id or d.client_id == "acemac_internal"
            ]

        return results[:top_k]


retrieval_service = RetrievalService()
