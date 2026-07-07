"""
Briefing Router — Conversational briefing endpoints.
Handles the chat-based brief creation flow (PRD Section 3.1-3.3).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import uuid

from models.brief import (
    Brief,
    BriefMessageRequest,
    BriefMessageResponse,
    BriefConfirmRequest,
    BriefData,
    BriefMessage,
)
from services.briefing import BriefingService

router = APIRouter(prefix="/api/brief", tags=["briefing"])
briefing_service = BriefingService()


@router.post("/message", response_model=BriefMessageResponse)
async def send_message(request: BriefMessageRequest):
    """Process a user message in the briefing conversation.
    Creates a new brief if no brief_id is provided."""
    brief_id = request.brief_id or str(uuid.uuid4())
    response = await briefing_service.process_message(brief_id, request.message)
    return response


@router.post("/{brief_id}/upload")
async def upload_document(brief_id: str, file: UploadFile = File(...)):
    """Upload a supporting document (PDF, PPTX, DOCX) during briefing.
    Extracts entities and returns a summary for user confirmation."""
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Accepted: PDF, PPTX, DOCX",
        )

    result = await briefing_service.process_upload(brief_id, file)
    return result


@router.get("/{brief_id}", response_model=Brief)
async def get_brief(brief_id: str):
    """Get the current state of a brief including conversation and extracted data."""
    brief = await briefing_service.get_brief(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@router.put("/{brief_id}/confirm", response_model=Brief)
async def confirm_brief(brief_id: str, request: BriefConfirmRequest):
    """Confirm the brief with optional field edits. This is the mandatory
    checkpoint before generation begins (PRD Section 3.3)."""
    brief = await briefing_service.confirm_brief(brief_id, request.data)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief
