"""
Library Service — Deck repository browsing (stub).
Returns mock data until the indexer is connected.
"""

from typing import Optional
from datetime import datetime

from models.deck import Deck, DeckAnalysis, DeckListResponse, LibraryProfile

# Mock data for UI development
MOCK_DECKS = [
    Deck(
        id="deck_001",
        filename="Leadership_Fundamentals_ClientA.pptx",
        client_id="client_a",
        client_name="Client A",
        topic_tags=["leadership", "management", "soft_skills"],
        slide_count=24,
        analysis=DeckAnalysis(
            learning_arc="linear_progressive",
            tone_profile="professional_conversational",
            assumed_knowledge_level="intermediate",
            frameworks_and_models=["Situational Leadership", "Bloom's Taxonomy"],
            activity_design="Group scenarios + individual reflection, placed mid-session and pre-close",
            client_industry_signals="Financial services, stakeholder management focus",
            content_domain_tags=["leadership", "team_management"],
            slide_type_sequence=["title", "agenda", "objectives", "content", "content", "activity", "content", "activity", "summary"],
            complexity_arc="builds_to_peak",
            recurring_language_patterns=["empower", "stakeholder", "ROI", "actionable insights"],
        ),
        summary="A comprehensive leadership fundamentals deck designed for mid-level managers in financial services. Particularly strong in balancing theory (Situational Leadership model) with practical group activities. The deck builds complexity gradually, peaking with a challenging case study before closing with individual reflection. Best used as a reference for professional-tone leadership content with financial services framing.",
        indexed_at=datetime(2026, 6, 1),
        analyzed_at=datetime(2026, 6, 1),
    ),
    Deck(
        id="deck_002",
        filename="Communication_Skills_Workshop.pptx",
        client_id="acemac_internal",
        client_name="Acemac Internal",
        topic_tags=["communication", "presentation", "interpersonal"],
        slide_count=18,
        analysis=DeckAnalysis(
            learning_arc="spiral",
            tone_profile="motivational_conversational",
            assumed_knowledge_level="introductory",
            frameworks_and_models=["Active Listening Model", "Feedback Sandwich"],
            activity_design="Paired exercises every 3rd slide, building in complexity",
            client_industry_signals="Cross-industry, uses generic business examples",
            content_domain_tags=["communication", "soft_skills"],
            slide_type_sequence=["title", "objectives", "content", "activity", "content", "activity", "content", "activity", "summary"],
            complexity_arc="spiral_revisiting",
            recurring_language_patterns=["connect", "engage", "impact", "your voice matters"],
        ),
        summary="An energetic communication skills workshop using a spiral learning approach — concepts are introduced, practised, and then revisited at a deeper level. Heavy on paired activities (every 3rd slide), making it ideal for in-person delivery. Motivational tone with strong emphasis on personal empowerment. Best used as a reference for activity-heavy, introductory-level soft skills content.",
        indexed_at=datetime(2026, 5, 20),
        analyzed_at=datetime(2026, 5, 20),
    ),
    Deck(
        id="deck_003",
        filename="Compliance_Training_Healthcare.pptx",
        client_id="client_b",
        client_name="Client B",
        topic_tags=["compliance", "healthcare", "regulation"],
        slide_count=30,
        analysis=DeckAnalysis(
            learning_arc="framework_first",
            tone_profile="formal_instructional",
            assumed_knowledge_level="advanced",
            frameworks_and_models=["ADDIE", "Regulatory Compliance Framework"],
            activity_design="Knowledge check quizzes after each section, final assessment",
            client_industry_signals="Healthcare, regulatory language, patient safety focus",
            content_domain_tags=["compliance", "healthcare", "regulation"],
            slide_type_sequence=["title", "agenda", "objectives", "content", "content", "quiz", "content", "content", "quiz", "content", "quiz", "summary"],
            complexity_arc="front_loaded",
            recurring_language_patterns=["compliance requirement", "regulatory framework", "patient safety", "documentation standard"],
        ),
        summary="A dense compliance training deck for healthcare professionals using a framework-first approach — the regulatory structure is established upfront, then applied to specific scenarios. Heavily quiz-oriented with knowledge checks after each section. Formal, instructional tone appropriate for regulated industries. Best used as a reference for compliance-heavy, assessment-driven content with healthcare framing.",
        indexed_at=datetime(2026, 5, 15),
        analyzed_at=datetime(2026, 5, 15),
    ),
]

MOCK_PROFILE = LibraryProfile(
    common_slide_sequences=[
        "title → agenda → objectives → content → activity → summary",
        "title → objectives → content → content → activity → content → activity → summary",
    ],
    frequent_frameworks=["Bloom's Taxonomy", "Situational Leadership", "70-20-10", "ADDIE"],
    tone_by_industry={
        "financial_services": "professional_conversational",
        "healthcare": "formal_instructional",
        "technology": "casual_technical",
        "general": "motivational_conversational",
    },
    activity_by_format={
        "in_person": ["group_discussion", "paired_exercise", "case_study", "role_play"],
        "virtual": ["breakout_room", "poll", "chat_reflection", "shared_whiteboard"],
        "hybrid": ["group_discussion", "poll", "individual_reflection"],
    },
    total_decks_analyzed=3,
    last_updated=datetime(2026, 6, 1),
)


class LibraryService:
    """Serves deck metadata and library intelligence."""

    async def list_decks(
        self,
        query: Optional[str] = None,
        client_id: Optional[str] = None,
        domain: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> DeckListResponse:
        """List decks with optional filtering."""
        filtered = MOCK_DECKS.copy()

        if query:
            q = query.lower()
            filtered = [
                d for d in filtered
                if q in d.filename.lower() or q in (d.summary or "").lower()
            ]

        if client_id:
            filtered = [d for d in filtered if d.client_id == client_id]

        if domain:
            filtered = [
                d for d in filtered
                if domain in d.topic_tags
            ]

        return DeckListResponse(
            decks=filtered,
            total=len(filtered),
            page=page,
            per_page=per_page,
        )

    async def get_deck(self, deck_id: str) -> Optional[Deck]:
        """Get a specific deck by ID."""
        for deck in MOCK_DECKS:
            if deck.id == deck_id:
                return deck
        return None

    async def get_profile(self) -> LibraryProfile:
        """Get the cross-deck library profile."""
        return MOCK_PROFILE
