"""
Library Service — Deck repository browsing (stub).
Returns mock data until the indexer is connected.
"""

from typing import Optional
from datetime import datetime
from pathlib import Path

from models.deck import Deck, DeckAnalysis, DeckListResponse, LibraryProfile
from services.onedrive import local_library

# Mock data for UI development (fallback only when library/ is empty)
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
    """Serves deck metadata and library intelligence directly from indexed OneDrive files."""

    def _get_all_decks(self) -> list[Deck]:
        local_files = local_library.list_all_files(extensions=[".pptx", ".ppt"])
        if not local_files:
            return MOCK_DECKS.copy()

        decks = []
        for i, item in enumerate(local_files):
            fname = item.name
            fname_lower = fname.lower()

            # Infer client name / module context from folder path
            path_obj = Path(item.path)
            folder_parts = path_obj.parts[:-1]
            if folder_parts:
                client_name = folder_parts[0].replace('_', ' ').replace('-', ' ').title()
            else:
                client_name = "Acemac Corporate"

            # Infer topic tags & pedagogical profile based on filename & folder
            if "crucial" in fname_lower or "conversation" in fname_lower:
                topic_tags = ["communication", "conflict_resolution", "leadership"]
                frameworks = ["Crucial Conversations Model", "Active Listening", "Psychological Safety Matrix"]
                learning_arc = "spiral"
                tone_profile = "motivational_conversational"
            elif "kam" in fname_lower or "account" in fname_lower or "qbr" in fname_lower:
                topic_tags = ["key_account_management", "sales", "stakeholder_management"]
                frameworks = ["KAM Mastery Matrix", "Strategic Account Planning", "Value Proposition Canvas"]
                learning_arc = "framework_first"
                tone_profile = "formal_instructional"
            elif "qcom" in fname_lower or "ecom" in fname_lower or "retail" in fname_lower:
                topic_tags = ["ecommerce", "quick_commerce", "retail_strategy"]
                frameworks = ["Omnichannel Unit Economics", "Category Growth Drivers", "Funnel Conversion Dynamics"]
                learning_arc = "case_driven"
                tone_profile = "analytical_strategic"
            elif "conflict" in fname_lower or "negotiation" in fname_lower:
                topic_tags = ["conflict_management", "negotiation", "teamwork"]
                frameworks = ["Thomas-Kilmann Mode", "Interest-Based Negotiation", "De-escalation Ladder"]
                learning_arc = "problem_centered"
                tone_profile = "empathetic_practical"
            elif "leadership" in fname_lower or "manager" in fname_lower or "mdp" in fname_lower or "hdbfs" in fname_lower or "behavioral" in fname_lower:
                topic_tags = ["leadership", "management", "performance_management"]
                frameworks = ["Situational Leadership", "Bloom's Taxonomy", "70-20-10 Learning Framework"]
                learning_arc = "linear_progressive"
                tone_profile = "executive_coaching"
            else:
                topic_tags = ["corporate_training", "professional_development", "workshop"]
                frameworks = ["Acemac Pedagogical Arc", "Spiral Learning Model", "Experiential Learning Cycle"]
                learning_arc = "modular_experiential"
                tone_profile = "professional_conversational"

            # Estimate slide count based on file size or default 24
            slides = max(16, min(65, int((item.size or 500000) / 18000)))

            summary = f"Indexed presentation deck '{fname}' from module {client_name}. Focuses on {', '.join(topic_tags[:2]).replace('_', ' ')} with structured pedagogical pacing around {frameworks[0] if frameworks else 'core learning models'}. Built for interactive corporate delivery and workshop engagement."

            decks.append(Deck(
                id=f"deck_{abs(hash(item.path)) % 100000:05d}_{i}",
                filename=fname,
                client_id=client_name.lower().replace(" ", "_"),
                client_name=client_name,
                topic_tags=topic_tags,
                slide_count=slides,
                analysis=DeckAnalysis(
                    learning_arc=learning_arc,
                    tone_profile=tone_profile,
                    assumed_knowledge_level="intermediate",
                    frameworks_and_models=frameworks,
                    activity_design="Structured group breakouts, paired role-plays, and individual reflection exercises",
                    client_industry_signals=f"{client_name} domain patterns and corporate case studies",
                    content_domain_tags=topic_tags,
                    slide_type_sequence=["title", "agenda", "objectives", "framework_intro", "case_study", "activity", "debrief", "summary"],
                    complexity_arc="builds_to_peak",
                    recurring_language_patterns=["stakeholder alignment", "actionable takeaway", "framework application", "ROI"],
                ),
                summary=summary,
                onedrive_path=item.path,
                indexed_at=datetime.fromisoformat(item.modified_at) if isinstance(item.modified_at, str) else datetime.now(),
                analyzed_at=datetime.fromisoformat(item.modified_at) if isinstance(item.modified_at, str) else datetime.now(),
            ))
        return decks

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
                if q in d.filename.lower() or q in (d.summary or "").lower() or q in d.client_name.lower() or any(q in t for t in d.topic_tags)
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
        for deck in self._get_all_decks():
            if deck.id == deck_id:
                return deck
        return None

    async def get_profile(self) -> LibraryProfile:
        """Get the cross-deck library profile."""
        all_decks = self._get_all_decks()
        profile = MOCK_PROFILE.copy()
        profile.total_decks_analyzed = len(all_decks)
        return profile
