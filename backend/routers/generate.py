"""
Generation Router — Pipeline execution and progress streaming.
Handles the 6-step generation pipeline (PRD Section 7).
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sse_starlette.sse import EventSourceResponse

from models.generation import GenerationRequest, GenerationResult, GenerationProgress
from services.generation import GenerationService

router = APIRouter(prefix="/api/generate", tags=["generation"])
generation_service = GenerationService()


@router.post("", response_model=GenerationResult)
async def start_generation(request: GenerationRequest):
    """Start the generation pipeline from a confirmed brief.
    Returns the generation ID for progress tracking."""
    result = await generation_service.start(request.brief_id)
    return result

from pydantic import BaseModel
class ApproveLessonPlanRequest(BaseModel):
    lesson_plan: dict

@router.post("/{generation_id}/approve")
async def approve_lesson_plan(generation_id: str, request: ApproveLessonPlanRequest):
    """Approve the generated lesson plan and trigger stage 2 (slides generation)."""
    try:
        await generation_service.continue_pipeline(generation_id, request.lesson_plan)
        return {"status": "ok", "message": "Stage 2 started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{generation_id}/stream")
async def stream_progress(generation_id: str):
    """SSE endpoint for real-time slide-by-slide progress updates.
    The frontend connects to this during generation to show live progress."""

    async def event_generator():
        async for event in generation_service.stream_progress(generation_id):
            yield {
                "event": "progress",
                "data": event.model_dump_json(),
            }

    return EventSourceResponse(event_generator())


@router.get("/{generation_id}/result", response_model=GenerationResult)
async def get_result(generation_id: str):
    """Get the final generation result including slide content and metadata."""
    result = await generation_service.get_result(generation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Generation not found")
    return result


@router.get("/{generation_id}/download")
async def download_pptx(generation_id: str):
    """Download the generated PPTX file."""
    file_path = await generation_service.get_download_path(generation_id)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="File not found or expired (files are kept for 24 hours)",
        )
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"lesson_plan_{generation_id}.pptx",
    )
