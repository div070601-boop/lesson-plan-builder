"""
Generation models — Pipeline stages, slide content, and progress tracking.
Maps to the generation pipeline from PRD Section 7.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SlideType(str, Enum):
    TITLE = "title"
    OBJECTIVES = "objectives"
    CONTENT = "content"
    ACTIVITY = "activity"
    QUIZ = "quiz"
    SUMMARY = "summary"
    TRANSITION = "transition"
    AGENDA = "agenda"


class GenerationStatus(str, Enum):
    QUEUED = "queued"
    RETRIEVING = "retrieving"
    SYNTHESIZING = "synthesizing"
    PLANNING = "planning"
    PLANNING_LESSON = "planning_lesson"
    LESSON_PLAN_REVIEW = "lesson_plan_review"
    PLANNING_SLIDES = "planning_slides"
    GENERATING = "generating"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class SlideContent(BaseModel):
    """Content for a single generated slide."""
    index: int
    slide_type: SlideType
    title: str
    body: list[str] = Field(default_factory=list)
    speaker_notes: Optional[str] = None
    activity_instructions: Optional[str] = None
    estimated_duration: Optional[str] = None


class LessonPlanModule(BaseModel):
    """A single module in the lesson plan."""
    module_name: str
    objective: str
    outline: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)


class LessonPlan(BaseModel):
    """The client-facing lesson plan table."""
    title: str
    modules: list[LessonPlanModule] = Field(default_factory=list)


class SlidePlan(BaseModel):
    """Planned slide before content generation."""
    index: int
    slide_type: SlideType
    content_directive: str
    source_deck_refs: list[str] = Field(default_factory=list)


class TeachingContext(BaseModel):
    """Synthesized teaching context from retrieved decks."""
    dominant_learning_arc: Optional[str] = None
    appropriate_tone: Optional[str] = None
    knowledge_level: Optional[str] = None
    relevant_frameworks: list[str] = Field(default_factory=list)
    activity_conventions: list[str] = Field(default_factory=list)
    industry_language_patterns: list[str] = Field(default_factory=list)
    library_profile_summary: Optional[str] = None


class GenerationProgress(BaseModel):
    """Real-time progress update for the generation pipeline."""
    generation_id: str
    status: GenerationStatus
    current_step: str
    current_slide: Optional[int] = None
    total_slides: Optional[int] = None
    slides_completed: list[SlideContent] = Field(default_factory=list)
    message: str = ""
    progress_percentage: int = 0


class GenerationRequest(BaseModel):
    """Request to start generation from a confirmed brief."""
    brief_id: str


class GenerationResult(BaseModel):
    """Final generation result with download link and metadata."""
    id: str
    brief_id: str
    status: GenerationStatus
    lesson_plan: Optional[LessonPlan] = None
    slides: list[SlideContent] = Field(default_factory=list)
    slide_plan: list[SlidePlan] = Field(default_factory=list)
    teaching_context: Optional[TeachingContext] = None
    branding_mode: Optional[str] = None
    source_decks: list[str] = Field(default_factory=list)
    download_url: Optional[str] = None
    models_used: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
