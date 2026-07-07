"""
Library Router — Deck repository browser endpoints (stub).
Will connect to the indexer when OneDrive is available.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models.deck import Deck, DeckListResponse, LibraryProfile
from services.library import LibraryService

router = APIRouter(prefix="/api/library", tags=["library"])
library_service = LibraryService()


@router.get("/decks", response_model=DeckListResponse)
async def list_decks(
    query: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List indexed decks with optional filtering by client and domain."""
    return await library_service.list_decks(
        query=query, client_id=client_id, domain=domain, page=page, per_page=per_page
    )


@router.get("/decks/{deck_id}", response_model=Deck)
async def get_deck(deck_id: str):
    """Get a specific deck with its full analysis and summary."""
    deck = await library_service.get_deck(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.get("/profile", response_model=LibraryProfile)
async def get_library_profile():
    """Get the cross-deck library profile (PRD Section 4.3).
    This synthesized intelligence is injected into generation prompts."""
    return await library_service.get_profile()
