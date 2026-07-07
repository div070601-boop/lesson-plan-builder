"""
Briefing Service — Conversational briefing logic.
Manages the chat flow, AI-powered field extraction, and completion detection.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import UploadFile

from models.brief import (
    Brief,
    BriefData,
    BriefMessage,
    BriefMessageResponse,
)
from services.providers import provider_service, ProviderError

logger = logging.getLogger(__name__)

# In-memory store for v1 (will migrate to Supabase)
_briefs: dict[str, Brief] = {}

# The fields we need to complete a brief
REQUIRED_FIELDS = [
    "client_name",
    "client_industry",
    "target_audience",
    "learning_objectives",
    "session_format",
    "branding_mode",
]

BRIEFING_QUESTIONS = [
    {
        "field": "client_name",
        "question": "Let's start building your lesson plan. Which client is this for? And what industry or niche are they in?",
        "extracts": ["client_name", "client_industry"],
    },
    {
        "field": "target_audience",
        "question": "Who's the audience? Tell me about their seniority level, function, and how much they already know about the topic.",
        "extracts": ["target_audience", "audience_seniority", "audience_function", "prior_knowledge_level"],
    },
    {
        "field": "learning_objectives",
        "question": "What should learners know or be able to do after this session? Give me the key learning objectives.",
        "extracts": ["learning_objectives"],
    },
    {
        "field": "session_format",
        "question": "How will this session be delivered? In-person, virtual, or hybrid? And roughly how long is the session?",
        "extracts": ["session_format", "session_duration", "is_standalone"],
    },
    {
        "field": "branding_mode",
        "question": "For branding — should this use the client's branding, Acemac's default, or a mix of both?",
        "extracts": ["branding_mode"],
    },
    {
        "field": "additional_context",
        "question": "Anything else I should know? Any specific frameworks, activities, or reference materials you want to include? You can also upload documents here.",
        "extracts": ["additional_context"],
    },
]

# System prompt for AI-powered briefing
BRIEFING_SYSTEM_PROMPT = """You are an expert L&D (Learning & Development) briefing assistant for Acemac, a corporate training company. 
Your job is to have a natural conversation to gather requirements for a new lesson plan.

You are collecting the following information through conversation:
1. Client name and industry
2. Target audience (seniority, function, prior knowledge level)
3. Learning objectives (what learners should know/do after the session)
4. Session format (in-person/virtual/hybrid) and duration
5. Branding mode (client branding, Acemac default, or mixed)
6. Any additional context (frameworks, activities, reference materials)

CONVERSATION RULES:
- Be warm, professional, and conversational — like briefing a knowledgeable colleague
- Ask one question group at a time, don't overwhelm
- If the user provides multiple pieces of info at once, acknowledge all of them
- Ask clarifying follow-ups when answers are vague
- When you have enough info, indicate the brief is complete

RESPONSE FORMAT:
You must respond with valid JSON in this exact format:
{
  "message": "Your conversational response to the user",
  "extracted_fields": {
    "client_name": "extracted value or null",
    "client_industry": "extracted value or null",
    "target_audience": "extracted value or null",
    "audience_seniority": "extracted value or null",
    "audience_function": "extracted value or null",
    "prior_knowledge_level": "introductory|intermediate|advanced or null",
    "learning_objectives": ["obj1", "obj2"] or null,
    "session_duration": "extracted value or null",
    "session_format": "in_person|virtual|hybrid or null",
    "is_standalone": true/false or null,
    "branding_mode": "client|acemac_default|mixed or null",
    "additional_context": "extracted value or null"
  },
  "is_complete": false
}

Only include fields in extracted_fields that you can confidently extract from the CURRENT message.
Set is_complete to true only when all required fields have been gathered.
Always return valid JSON. No markdown, no explanation outside the JSON."""


class BriefingService:
    """Manages the conversational briefing flow."""

    async def process_message(
        self, brief_id: str, user_message: str
    ) -> BriefMessageResponse:
        """Process a user message and return the next AI question."""
        # Get or create brief
        brief = _briefs.get(brief_id)
        if not brief:
            brief = Brief(id=brief_id)
            _briefs[brief_id] = brief

        # Add user message
        user_msg = BriefMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=user_message,
            timestamp=datetime.utcnow(),
        )
        brief.messages.append(user_msg)

        # Try AI-powered extraction first, fall back to heuristic
        try:
            ai_response = await self._ai_extract_and_respond(brief, user_message)
            if ai_response:
                return ai_response
        except Exception as e:
            logger.warning(f"AI briefing failed, falling back to heuristic: {e}")

        # Fallback: heuristic extraction
        self._extract_fields_heuristic(brief, user_message)

        # Determine next question
        completion_pct, next_question = self._get_next_question(brief)
        is_complete = completion_pct >= 100

        if is_complete:
            ai_content = (
                "I have everything I need for the brief. Here's a summary of what I've captured. "
                "Please review it on the next screen and confirm when you're ready to generate."
            )
        elif next_question:
            ai_content = next_question
        else:
            ai_content = "Thanks for that. Let me know if you have any other details to add, or we can proceed to review."

        # Add AI response
        ai_msg = BriefMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=ai_content,
            timestamp=datetime.utcnow(),
        )
        brief.messages.append(ai_msg)
        brief.updated_at = datetime.utcnow()

        if is_complete:
            brief.status = "review"

        return BriefMessageResponse(
            brief_id=brief_id,
            message=ai_msg,
            brief_data=brief.data,
            is_complete=is_complete,
            completion_percentage=completion_pct,
        )

    async def _ai_extract_and_respond(
        self, brief: Brief, user_message: str
    ) -> Optional[BriefMessageResponse]:
        """Use AI to extract fields and generate a natural response."""
        # Build conversation history for context
        conversation_history = []
        for msg in brief.messages[-10:]:  # Last 10 messages for context
            conversation_history.append(f"{msg.role}: {msg.content}")

        # Build the current brief state
        current_state = {
            "client_name": brief.data.client_name,
            "client_industry": brief.data.client_industry,
            "target_audience": brief.data.target_audience,
            "audience_seniority": brief.data.audience_seniority,
            "audience_function": brief.data.audience_function,
            "prior_knowledge_level": brief.data.prior_knowledge_level,
            "learning_objectives": brief.data.learning_objectives if brief.data.learning_objectives else None,
            "session_duration": brief.data.session_duration,
            "session_format": brief.data.session_format,
            "is_standalone": brief.data.is_standalone,
            "branding_mode": brief.data.branding_mode,
            "additional_context": brief.data.additional_context,
        }

        prompt = f"""Current conversation:
{chr(10).join(conversation_history)}

Current brief state (fields already collected):
{json.dumps(current_state, indent=2, default=str)}

The user just said: "{user_message}"

Extract any new information from the user's message and respond naturally to continue the briefing. 
Ask the next required question or confirm completion if all fields are filled."""

        try:
            response_text, model_used = await provider_service.complete(
                prompt=prompt,
                system=BRIEFING_SYSTEM_PROMPT,
                task_type="analysis",
            )

            # Parse the AI response
            # Clean up response — sometimes models wrap in markdown
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)

            # Update brief data with extracted fields
            extracted = parsed.get("extracted_fields", {})
            self._apply_extracted_fields(brief, extracted)

            # Calculate completion
            completion_pct = self._calculate_completion(brief.data)
            is_complete = parsed.get("is_complete", False) or completion_pct >= 100

            # Create AI message
            ai_content = parsed.get("message", "Could you tell me more?")
            ai_msg = BriefMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=ai_content,
                timestamp=datetime.utcnow(),
            )
            brief.messages.append(ai_msg)
            brief.updated_at = datetime.utcnow()

            if is_complete:
                brief.status = "review"

            logger.info(f"AI briefing response from {model_used}, completion: {completion_pct}%")

            return BriefMessageResponse(
                brief_id=brief.id,
                message=ai_msg,
                brief_data=brief.data,
                is_complete=is_complete,
                completion_percentage=completion_pct,
            )

        except ProviderError:
            # No AI providers configured — fall through to heuristic
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"AI response was not valid JSON: {e}")
            return None

    def _apply_extracted_fields(self, brief: Brief, extracted: dict) -> None:
        """Apply AI-extracted fields to the brief data."""
        data = brief.data

        if extracted.get("client_name") and not data.client_name:
            data.client_name = extracted["client_name"]
        if extracted.get("client_industry") and not data.client_industry:
            data.client_industry = extracted["client_industry"]
        if extracted.get("target_audience") and not data.target_audience:
            data.target_audience = extracted["target_audience"]
        if extracted.get("audience_seniority") and not data.audience_seniority:
            data.audience_seniority = extracted["audience_seniority"]
        if extracted.get("audience_function") and not data.audience_function:
            data.audience_function = extracted["audience_function"]
        if extracted.get("prior_knowledge_level") and not data.prior_knowledge_level:
            data.prior_knowledge_level = extracted["prior_knowledge_level"]
        if extracted.get("learning_objectives") and not data.learning_objectives:
            data.learning_objectives = extracted["learning_objectives"]
        if extracted.get("session_duration") and not data.session_duration:
            data.session_duration = extracted["session_duration"]
        if extracted.get("session_format") and not data.session_format:
            data.session_format = extracted["session_format"]
        if extracted.get("is_standalone") is not None and data.is_standalone is None:
            data.is_standalone = extracted["is_standalone"]
        if extracted.get("branding_mode") and not data.branding_mode:
            data.branding_mode = extracted["branding_mode"]
        if extracted.get("additional_context") and not data.additional_context:
            data.additional_context = extracted["additional_context"]

    def _calculate_completion(self, data: BriefData) -> int:
        """Calculate completion percentage based on filled fields."""
        filled = self._count_filled(data)
        total = len(BRIEFING_QUESTIONS)
        return int((filled / total) * 100)

    def _extract_fields_heuristic(self, brief: Brief, message: str) -> None:
        """Simple field extraction from user message.
        Used as fallback when no AI providers are configured."""
        msg_lower = message.lower()
        data = brief.data

        # Count which question we're on based on filled fields
        filled = self._count_filled(data)

        # Simple heuristic: assign message content to the current question's field
        if filled == 0:
            data.client_name = message.split(",")[0].strip() if "," in message else message.strip()
            if "," in message:
                data.client_industry = message.split(",", 1)[1].strip()
        elif filled == 1:
            data.target_audience = message.strip()
        elif filled == 2:
            data.learning_objectives = [obj.strip() for obj in message.split(",")]
        elif filled == 3:
            if "virtual" in msg_lower:
                data.session_format = "virtual"
            elif "hybrid" in msg_lower:
                data.session_format = "hybrid"
            else:
                data.session_format = "in_person"
            data.session_duration = message.strip()
        elif filled == 4:
            if "client" in msg_lower:
                data.branding_mode = "client"
            elif "mix" in msg_lower:
                data.branding_mode = "mixed"
            else:
                data.branding_mode = "acemac_default"
        elif filled >= 5:
            data.additional_context = message.strip()

    def _count_filled(self, data: BriefData) -> int:
        """Count how many required field groups are filled."""
        count = 0
        if data.client_name:
            count += 1
        if data.target_audience:
            count += 1
        if data.learning_objectives:
            count += 1
        if data.session_format:
            count += 1
        if data.branding_mode:
            count += 1
        if data.additional_context:
            count += 1
        return count

    def _get_next_question(self, brief: Brief) -> tuple[int, Optional[str]]:
        """Determine completion percentage and next question to ask."""
        filled = self._count_filled(brief.data)
        total = len(BRIEFING_QUESTIONS)
        pct = int((filled / total) * 100)

        if filled < total:
            return pct, BRIEFING_QUESTIONS[filled]["question"]
        return 100, None

    async def process_upload(self, brief_id: str, file: UploadFile) -> dict:
        """Process an uploaded document and extract entities."""
        brief = _briefs.get(brief_id)
        if not brief:
            brief = Brief(id=brief_id)
            _briefs[brief_id] = brief

        # Store file reference
        brief.uploaded_files.append(file.filename or "unknown")

        # TODO: Implement actual document parsing with PDF/DOCX/PPTX extractors
        return {
            "brief_id": brief_id,
            "filename": file.filename,
            "status": "uploaded",
            "extracted_entities": {
                "summary": f"Document '{file.filename}' uploaded successfully. Entity extraction will be available when AI providers are configured.",
            },
        }

    async def get_brief(self, brief_id: str) -> Optional[Brief]:
        """Get a brief by ID."""
        return _briefs.get(brief_id)

    async def confirm_brief(
        self, brief_id: str, data: BriefData
    ) -> Optional[Brief]:
        """Confirm a brief with optionally edited fields."""
        brief = _briefs.get(brief_id)
        if not brief:
            return None

        brief.data = data
        brief.status = "confirmed"
        brief.updated_at = datetime.utcnow()
        return brief
