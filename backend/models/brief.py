"""
Brief models — Conversational briefing data structures.
Maps to the briefing flow from PRD Section 3.1.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class BrandingMode(str, Enum):
    CLIENT = "client"
    ACEMAC_DEFAULT = "acemac_default"
    MIXED = "mixed"


class SessionFormat(str, Enum):
    IN_PERSON = "in_person"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class AudienceLevel(str, Enum):
    INTRODUCTORY = "introductory"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class BriefField(BaseModel):
    """A single extracted field from the briefing conversation."""
    name: str
    value: Optional[str] = None
    confirmed: bool = False


class BriefMessage(BaseModel):
    """A single message in the briefing conversation."""
    id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attachments: list[str] = Field(default_factory=list)


class BriefData(BaseModel):
    """Structured brief extracted from the conversation."""
    client_name: Optional[str] = None
    client_industry: Optional[str] = None
    target_audience: Optional[str] = None
    audience_seniority: Optional[str] = None
    audience_function: Optional[str] = None
    prior_knowledge_level: Optional[AudienceLevel] = None
    learning_objectives: list[str] = Field(default_factory=list)
    session_duration: Optional[str] = None
    session_format: Optional[SessionFormat] = None
    is_standalone: Optional[bool] = None
    branding_mode: Optional[BrandingMode] = None
    reference_deck_id: Optional[str] = None
    additional_context: Optional[str] = None


class Brief(BaseModel):
    """Full brief including conversation history and extracted data."""
    id: str
    user_id: Optional[str] = None
    status: str = "in_progress"  # in_progress | review | confirmed | generating | completed
    messages: list[BriefMessage] = Field(default_factory=list)
    data: BriefData = Field(default_factory=BriefData)
    uploaded_files: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BriefMessageRequest(BaseModel):
    """Incoming message from the user during briefing."""
    message: str
    brief_id: Optional[str] = None


class BriefMessageResponse(BaseModel):
    """AI response during briefing conversation."""
    brief_id: str
    message: BriefMessage
    brief_data: BriefData
    is_complete: bool = False
    completion_percentage: int = 0


class BriefConfirmRequest(BaseModel):
    """User confirms the brief and optionally edits fields."""
    data: BriefData
