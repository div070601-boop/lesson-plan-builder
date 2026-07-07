"""
Generation Service — Orchestrates the 6-step generation pipeline.
From PRD Section 7: Retrieve → Synthesize → Plan → Generate → Assemble → Output.
"""

import uuid
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator
from pathlib import Path

from models.generation import (
    GenerationResult,
    GenerationProgress,
    GenerationStatus,
    SlideContent,
    SlidePlan,
    SlideType,
    TeachingContext,
)
from config import settings
from services.pptx_builder import PPTXBuilder
from services.retrieval import retrieval_service
from services.providers import provider_service, ProviderError

logger = logging.getLogger(__name__)

# In-memory store for v1
_generations: dict[str, GenerationResult] = {}
_progress_queues: dict[str, asyncio.Queue] = {}


async def _check_ai_available() -> bool:
    """Check if any AI provider is configured and responsive.
    Re-checks every time so adding a key at runtime works without restart."""
    status = provider_service.get_status()
    return any(v == "configured" for v in status.values())


# System prompts for AI generation pipeline
SYNTHESIS_PROMPT = """You are an expert Learning & Development content designer analyzing matched training decks.

Given the brief and matched deck analyses below, synthesize a TeachingContext that will guide content generation.

Respond with valid JSON only:
{
  "dominant_learning_arc": "linear_progressive|spiral|framework_first|case_based",
  "appropriate_tone": "formal_instructional|professional_conversational|motivational_conversational|casual_technical",
  "knowledge_level": "introductory|intermediate|advanced",
  "relevant_frameworks": ["framework1", "framework2"],
  "activity_conventions": ["activity_type1", "activity_type2"],
  "industry_language_patterns": ["term1", "term2"],
  "library_profile_summary": "A 1-2 sentence summary of what the library tells us about this type of content"
}"""

PLANNING_LESSON_PROMPT = """You are an expert instructional designer.
Given the brief and teaching context, design a high-level Lesson Plan table.

RULES:
- Create 3-5 modules based on the session duration.
- Each module should have a name, a learning objective, an outline (bullet points), and expected outcomes.

Respond with valid JSON only:
{
  "title": "Course Title",
  "modules": [
    {
      "module_name": "Module 1",
      "objective": "What they will learn",
      "outline": ["Point 1", "Point 2"],
      "outcomes": ["Outcome 1"]
    }
  ]
}"""

PLANNING_SLIDES_PROMPT = """You are an expert instructional designer planning a slide sequence for a training session.

Given the approved Lesson Plan and teaching context, create a detailed slide plan.

RULES:
- Vary slide types to maintain engagement
- Include at least 1 activity for every 3-4 content slides
- Start with title, agenda, objectives
- End with summary/takeaways
- Match the session duration (more slides for longer sessions)

Respond with valid JSON array only:
[
  {"index": 0, "slide_type": "title", "content_directive": "What this slide should contain"},
  {"index": 1, "slide_type": "agenda", "content_directive": "..."},
  ...
]

Valid slide_type values: title, agenda, objectives, content, activity, quiz, summary, transition"""

SLIDE_GEN_PROMPT = """You are an expert training content writer. Generate the content for a single training slide.

Respond with valid JSON only:
{
  "title": "Slide title",
  "body": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
  "speaker_notes": "Detailed guidance for the facilitator",
  "activity_instructions": "Setup instructions (only for activity slides, null otherwise)",
  "estimated_duration": "X minutes (only for activity slides, null otherwise)"
}

RULES:
- Title should be concise and engaging (3-6 words)
- Body should have 3-6 bullet points, each 5-15 words
- Speaker notes should be 1-3 sentences of practical facilitator guidance
- Match the tone and language patterns specified in the teaching context"""


# Demo slides for when backend isn't connected to AI
DEMO_SLIDES: list[SlideContent] = [
    SlideContent(index=0, slide_type=SlideType.TITLE, title="Leadership Essentials", body=["Developing Tomorrow's Leaders Today"], speaker_notes="Welcome participants and set the tone."),
    SlideContent(index=1, slide_type=SlideType.AGENDA, title="Session Agenda", body=["Introduction & Context (15 min)", "Core Leadership Frameworks (30 min)", "Group Activity: Leadership Scenarios (20 min)", "Case Study Analysis (20 min)", "Reflection & Action Planning (15 min)", "Wrap-up & Resources (10 min)"], speaker_notes="Walk through the agenda and set expectations."),
    SlideContent(index=2, slide_type=SlideType.OBJECTIVES, title="Learning Objectives", body=["Understand the key principles of effective leadership", "Apply leadership frameworks to real-world scenarios", "Develop a personal leadership action plan", "Identify strategies for leading diverse teams"], speaker_notes="Review objectives and connect to participants' goals."),
    SlideContent(index=3, slide_type=SlideType.CONTENT, title="What Makes a Leader?", body=["Vision and strategic thinking", "Emotional intelligence and empathy", "Communication and influence", "Adaptability in uncertain environments", "Building trust through consistency"], speaker_notes="Use the iceberg model to illustrate visible vs hidden leadership qualities."),
    SlideContent(index=4, slide_type=SlideType.CONTENT, title="The Leadership Framework", body=["Situational Leadership Model (Hersey & Blanchard)", "Directing → Coaching → Supporting → Delegating", "Match leadership style to team maturity", "No single style works for every situation"], speaker_notes="Walk through each quadrant with examples from participants' industries."),
    SlideContent(index=5, slide_type=SlideType.ACTIVITY, title="Group Activity: Leadership Scenarios", body=["Form groups of 3-4", "Each group receives a leadership scenario card", "Discuss: What leadership style would you apply?", "Present your approach to the wider group"], speaker_notes="Allow 10 minutes for group discussion, 10 minutes for presentations.", activity_instructions="Distribute scenario cards. Monitor discussions and prompt deeper thinking.", estimated_duration="20 minutes"),
    SlideContent(index=6, slide_type=SlideType.CONTENT, title="Case Study: Leading Through Change", body=["The challenge: Merging two teams with different cultures", "Approach: Transparent communication + phased integration", "Key lesson: Trust is built through action, not words", "Result: 40% improvement in team engagement scores"], speaker_notes="Use this case study to bridge theory with practical application."),
    SlideContent(index=7, slide_type=SlideType.ACTIVITY, title="Personal Reflection", body=["What is your default leadership style?", "In what situations does it serve you well?", "Where might you need to flex your approach?", "Write down 3 actions you'll take this month"], speaker_notes="Give participants 5 minutes of quiet reflection time.", activity_instructions="Provide reflection worksheets. Play ambient music.", estimated_duration="15 minutes"),
    SlideContent(index=8, slide_type=SlideType.SUMMARY, title="Key Takeaways", body=["Leadership is situational — adapt your style", "Emotional intelligence is as important as expertise", "Trust is built through consistent actions", "Start with small, intentional leadership shifts"], speaker_notes="Recap the main points and connect back to learning objectives."),
    SlideContent(index=9, slide_type=SlideType.CONTENT, title="Resources & Next Steps", body=["Recommended reading: 'Leaders Eat Last' by Simon Sinek", "Follow-up coaching session available (date TBC)", "Leadership assessment tool: link in email", "Questions? Reach out to your L&D team"], speaker_notes="Share resource links and next steps for continued development."),
]


class GenerationService:
    """Orchestrates the full generation pipeline."""

    async def start(self, brief_id: str) -> GenerationResult:
        """Start the generation pipeline from a confirmed brief."""
        generation_id = str(uuid.uuid4())

        result = GenerationResult(
            id=generation_id,
            brief_id=brief_id,
            status=GenerationStatus.QUEUED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=settings.output_expiry_hours),
        )
        _generations[generation_id] = result
        _progress_queues[generation_id] = asyncio.Queue()

        # Start pipeline in background
        asyncio.create_task(self._run_pipeline(generation_id, brief_id))

        return result

    async def _run_pipeline(self, generation_id: str, brief_id: str) -> None:
        """Execute the 6-step pipeline with progress updates."""
        result = _generations[generation_id]
        queue = _progress_queues[generation_id]

        ai_available = await _check_ai_available()

        try:
            if ai_available:
                await self._run_ai_pipeline(generation_id, brief_id, result, queue)
            else:
                await self._run_demo_pipeline(generation_id, brief_id, result, queue)
        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}", exc_info=True)
            result.status = GenerationStatus.FAILED
            await queue.put(GenerationProgress(
                generation_id=generation_id,
                status=GenerationStatus.FAILED,
                current_step="Failed",
                message=str(e),
                progress_percentage=0,
            ))

    async def _run_ai_pipeline(
        self, generation_id: str, brief_id: str,
        result: GenerationResult, queue: asyncio.Queue
    ) -> None:
        """AI-powered generation pipeline."""
        # Get brief data
        from services.briefing import _briefs
        brief = _briefs.get(brief_id)
        brief_summary = ""
        if brief:
            data = brief.data
            brief_summary = f"""Client: {data.client_name or 'Unknown'} ({data.client_industry or 'Unknown industry'})
Audience: {data.target_audience or 'Unknown'} (Seniority: {data.audience_seniority or 'Unknown'})
Learning Objectives: {', '.join(data.learning_objectives) if data.learning_objectives else 'Not specified'}
Format: {data.session_format or 'Unknown'}, Duration: {data.session_duration or 'Unknown'}
Branding: {data.branding_mode or 'acemac_default'}
Additional Context: {data.additional_context or 'None'}"""

        # Step 1: Retrieve matching decks
        result.status = GenerationStatus.RETRIEVING
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.RETRIEVING,
            current_step="Searching library for matching decks...",
            progress_percentage=10,
            message="Analyzing your brief and searching the indexed library",
        ))

        matched_decks = await retrieval_service.retrieve_matching_decks(
            brief_text=brief_summary, top_k=5
        )
        result.source_decks = [d.id for d in matched_decks]

        deck_summaries = "\n".join([
            f"- {d.filename}: {d.summary or 'No summary'}" for d in matched_decks
        ])

        # Step 2: Synthesize teaching context
        result.status = GenerationStatus.SYNTHESIZING
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.SYNTHESIZING,
            current_step="Synthesizing teaching context from library...",
            progress_percentage=25,
            message=f"Building pedagogical context from {len(matched_decks)} matched decks",
        ))

        synthesis_prompt = f"""Brief:\n{brief_summary}\n\nMatched Decks:\n{deck_summaries}"""
        try:
            synthesis_response, model = await provider_service.complete(
                prompt=synthesis_prompt, system=SYNTHESIS_PROMPT, task_type="analysis"
            )
            cleaned = synthesis_response.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            tc_data = json.loads(cleaned.strip())
            teaching_context = TeachingContext(**tc_data)
            result.models_used.append(model)
        except Exception as e:
            logger.warning(f"AI synthesis failed, using defaults: {e}")
            teaching_context = TeachingContext(
                dominant_learning_arc="linear_progressive",
                appropriate_tone="professional_conversational",
                knowledge_level="intermediate",
                relevant_frameworks=["Bloom's Taxonomy", "70-20-10"],
                activity_conventions=["group_discussion", "case_study", "reflection"],
                industry_language_patterns=["stakeholder engagement", "ROI-driven"],
                library_profile_summary="Based on Acemac's teaching conventions",
            )
        result.teaching_context = teaching_context

        # Step 3: Plan Lesson (Stage 1)
        result.status = GenerationStatus.PLANNING_LESSON
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.PLANNING_LESSON,
            current_step="Designing Lesson Plan...",
            progress_percentage=35,
            message="Designing the high-level course modules",
        ))

        plan_prompt = f"""Brief:\n{brief_summary}\n\nTeaching Context:\n{json.dumps(teaching_context.model_dump(), indent=2)}"""
        try:
            plan_response, model = await provider_service.complete(
                prompt=plan_prompt, system=PLANNING_LESSON_PROMPT, task_type="planning"
            )
            cleaned = plan_response.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            plan_data = json.loads(cleaned.strip())
            
            from models.generation import LessonPlan
            lesson_plan = LessonPlan(**plan_data)
            
            if model not in result.models_used:
                result.models_used.append(model)
        except Exception as e:
            logger.warning(f"AI planning failed, using default plan: {e}")
            from models.generation import LessonPlan, LessonPlanModule
            lesson_plan = LessonPlan(
                title="Leadership Essentials",
                modules=[
                    LessonPlanModule(module_name="Introduction", objective="Set context", outline=["Welcome", "Agenda"], outcomes=["Alignment"]),
                    LessonPlanModule(module_name="Core Concepts", objective="Understand basics", outline=["Theory", "Framework"], outcomes=["Knowledge acquisition"])
                ]
            )

        result.lesson_plan = lesson_plan
        result.status = GenerationStatus.LESSON_PLAN_REVIEW
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.LESSON_PLAN_REVIEW,
            current_step="Waiting for approval",
            progress_percentage=50,
            message="Please review and approve the Lesson Plan",
        ))
        
        # Save state to Supabase
        await self._save_to_supabase(result)
        
        # STOP HERE - Wait for client approval
        return

    async def continue_pipeline(self, generation_id: str, approved_lesson_plan: dict) -> None:
        """Stage 2: Generate slides from the approved lesson plan."""
        result = _generations.get(generation_id)
        if not result:
            raise ValueError("Generation not found")
            
        queue = _progress_queues.get(generation_id)
        if not queue:
            queue = asyncio.Queue()
            _progress_queues[generation_id] = queue
            
        from models.generation import LessonPlan
        result.lesson_plan = LessonPlan(**approved_lesson_plan)
        
        asyncio.create_task(self._run_stage_2(generation_id, result, queue))

    async def _run_stage_2(self, generation_id: str, result: GenerationResult, queue: asyncio.Queue):
        try:
            await self._run_ai_stage_2(generation_id, result, queue)
        except Exception as e:
            logger.error(f"Generation stage 2 failed: {e}", exc_info=True)
            result.status = GenerationStatus.FAILED
            await queue.put(GenerationProgress(
                generation_id=generation_id,
                status=GenerationStatus.FAILED,
                current_step="Failed",
                message=str(e),
                progress_percentage=0,
            ))
            await self._save_to_supabase(result)

    async def _run_ai_stage_2(
        self, generation_id: str, result: GenerationResult, queue: asyncio.Queue
    ) -> None:
        # Step 3.5: Plan slides based on the approved lesson plan
        result.status = GenerationStatus.PLANNING_SLIDES
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.PLANNING_SLIDES,
            current_step="Planning slide sequence from approved plan...",
            progress_percentage=55,
            message="Designing slide by slide structure",
        ))
        
        slide_plan_prompt = f"""Approved Lesson Plan:\n{result.lesson_plan.model_dump_json(indent=2)}\n\nTeaching Context:\n{json.dumps(result.teaching_context.model_dump(), indent=2)}"""
        try:
            plan_response, model = await provider_service.complete(
                prompt=slide_plan_prompt, system=PLANNING_SLIDES_PROMPT, task_type="planning"
            )
            cleaned = plan_response.strip()
            if cleaned.startswith("```json"): cleaned = cleaned[7:]
            if cleaned.startswith("```"): cleaned = cleaned[3:]
            if cleaned.endswith("```"): cleaned = cleaned[:-3]
            plan_data = json.loads(cleaned.strip())
            slide_plan = [SlidePlan(index=p["index"], slide_type=SlideType(p["slide_type"]), content_directive=p["content_directive"]) for p in plan_data]
            if model not in result.models_used:
                result.models_used.append(model)
        except Exception as e:
            logger.warning(f"AI slide planning failed: {e}")
            slide_plan = [
                SlidePlan(index=0, slide_type=SlideType.TITLE, content_directive="Opening title with session name"),
                SlidePlan(index=1, slide_type=SlideType.CONTENT, content_directive="Introduction to the topic")
            ]
            
        result.slide_plan = slide_plan
        
        brief_summary = "Use the approved lesson plan context."

        # Step 4: Generate content per slide
        result.status = GenerationStatus.GENERATING
        slides: list[SlideContent] = []

        for i, plan in enumerate(slide_plan):
            tc = result.teaching_context
            slide_prompt = f"""Brief:\n{brief_summary}

Teaching Context:
- Tone: {tc.appropriate_tone if tc else 'professional_conversational'}
- Knowledge Level: {tc.knowledge_level if tc else 'intermediate'}
- Frameworks: {', '.join(tc.relevant_frameworks) if tc else 'General'}
- Industry Patterns: {', '.join(tc.industry_language_patterns) if tc else 'General'}

Slide {plan.index + 1} of {len(slide_plan)}:
- Type: {plan.slide_type.value}
- Directive: {plan.content_directive}

Generate the content for this slide."""

            try:
                slide_response, model = await provider_service.complete(
                    prompt=slide_prompt, system=SLIDE_GEN_PROMPT, task_type="generation"
                )
                cleaned = slide_response.strip()
                if cleaned.startswith("```json"): cleaned = cleaned[7:]
                if cleaned.startswith("```"): cleaned = cleaned[3:]
                if cleaned.endswith("```"): cleaned = cleaned[:-3]
                slide_data = json.loads(cleaned.strip())

                slide = SlideContent(
                    index=plan.index,
                    slide_type=plan.slide_type,
                    title=slide_data.get("title", plan.content_directive),
                    body=slide_data.get("body", []),
                    speaker_notes=slide_data.get("speaker_notes"),
                    activity_instructions=slide_data.get("activity_instructions"),
                    estimated_duration=slide_data.get("estimated_duration"),
                )
                if model not in result.models_used:
                    result.models_used.append(model)
            except Exception as e:
                logger.warning(f"AI slide generation failed for slide {i}: {e}")
                slide = SlideContent(
                    index=plan.index,
                    slide_type=plan.slide_type,
                    title=plan.content_directive,
                    body=[f"Content for: {plan.content_directive}"],
                    speaker_notes=f"Deliver this {plan.slide_type.value} slide.",
                )

            slides.append(slide)
            await queue.put(GenerationProgress(
                generation_id=generation_id,
                status=GenerationStatus.GENERATING,
                current_step=f"Generating slide {i + 1}/{len(slide_plan)}: {slide.title}",
                current_slide=i + 1,
                total_slides=len(slide_plan),
                slides_completed=slides.copy(),
                progress_percentage=40 + int((i + 1) / len(slide_plan) * 50),
                message=f"Generated: {slide.title}",
            ))

        result.slides = slides
        await self._finalize(generation_id, result, slides, queue)

    async def _run_demo_pipeline(
        self, generation_id: str, brief_id: str,
        result: GenerationResult, queue: asyncio.Queue
    ) -> None:
        """Demo pipeline with hardcoded slides (used when no AI providers are configured)."""
        # Step 1: Retrieve
        result.status = GenerationStatus.RETRIEVING
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.RETRIEVING,
            current_step="Searching library for matching decks...",
            progress_percentage=10,
            message="Analyzing your brief and searching the indexed library",
        ))
        await asyncio.sleep(1.5)

        # Step 2: Synthesize
        result.status = GenerationStatus.SYNTHESIZING
        teaching_context = TeachingContext(
            dominant_learning_arc="linear_progressive",
            appropriate_tone="professional_conversational",
            knowledge_level="intermediate",
            relevant_frameworks=["Bloom's Taxonomy", "70-20-10"],
            activity_conventions=["group_discussion", "case_study", "reflection"],
            industry_language_patterns=["stakeholder engagement", "ROI-driven"],
            library_profile_summary="Based on Acemac's teaching conventions",
        )
        result.teaching_context = teaching_context
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.SYNTHESIZING,
            current_step="Synthesizing teaching context from library...",
            progress_percentage=25,
            message="Building pedagogical context from matched decks",
        ))
        await asyncio.sleep(1)

        # Step 3: Plan
        result.status = GenerationStatus.PLANNING
        slide_plan = [
            SlidePlan(index=i, slide_type=s.slide_type, content_directive=s.title)
            for i, s in enumerate(DEMO_SLIDES)
        ]
        result.slide_plan = slide_plan
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.PLANNING,
            current_step="Planning slide sequence...",
            total_slides=len(slide_plan),
            progress_percentage=35,
            message=f"Planned {len(slide_plan)} slides",
        ))
        await asyncio.sleep(1)

        # Step 4: Generate slides (simulated)
        result.status = GenerationStatus.GENERATING
        slides: list[SlideContent] = []

        for i, slide in enumerate(DEMO_SLIDES):
            slides.append(slide)
            await queue.put(GenerationProgress(
                generation_id=generation_id,
                status=GenerationStatus.GENERATING,
                current_step=f"Generating slide {i + 1}/{len(DEMO_SLIDES)}: {slide.title}",
                current_slide=i + 1,
                total_slides=len(DEMO_SLIDES),
                slides_completed=slides.copy(),
                progress_percentage=40 + int((i + 1) / len(DEMO_SLIDES) * 50),
                message=f"Generated: {slide.title}",
            ))
            await asyncio.sleep(0.8)

        result.slides = slides
        result.models_used = ["demo_mode"]
        result.source_decks = ["demo_deck_001", "demo_deck_002"]
        await self._finalize(generation_id, result, slides, queue)

    async def _finalize(
        self, generation_id: str, result: GenerationResult,
        slides: list[SlideContent], queue: asyncio.Queue
    ) -> None:
        """Assemble PPTX and mark generation as complete."""
        # Step 5: Assemble PPTX
        result.status = GenerationStatus.ASSEMBLING
        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.ASSEMBLING,
            current_step="Assembling PPTX file...",
            total_slides=len(slides),
            slides_completed=slides,
            progress_percentage=95,
            message="Building the presentation file",
        ))

        output_path = str(Path(settings.output_dir) / f"{generation_id}.pptx")
        try:
            builder = PPTXBuilder()
            builder.build(slides, output_path)
            logger.info(f"PPTX built successfully: {output_path}")
        except Exception as e:
            logger.error(f"PPTX build failed: {e}")

        # Step 6: Complete
        result.status = GenerationStatus.COMPLETED
        result.branding_mode = "acemac_default"
        result.download_url = f"/api/generate/{generation_id}/download"

        await queue.put(GenerationProgress(
            generation_id=generation_id,
            status=GenerationStatus.COMPLETED,
            current_step="Complete!",
            total_slides=len(slides),
            slides_completed=slides,
            progress_percentage=100,
            message="Your lesson plan is ready for download",
        ))
        
        await self._save_to_supabase(result)

    async def _save_to_supabase(self, result: GenerationResult):
        from services.database import supabase
        if not supabase:
            return
            
        try:
            data = {
                "id": result.id,
                "brief_id": result.brief_id,
                "status": result.status.value,
                "lesson_plan": result.lesson_plan.model_dump() if result.lesson_plan else None,
                "slide_plan": [sp.model_dump() for sp in result.slide_plan] if result.slide_plan else None,
                "teaching_context": result.teaching_context.model_dump() if result.teaching_context else None,
                "branding_mode": result.branding_mode,
                "source_decks": result.source_decks,
                "models_used": result.models_used,
            }
            supabase.table("generations").upsert(data).execute()
        except Exception as e:
            logger.error(f"Failed to save to Supabase: {e}")

    async def stream_progress(
        self, generation_id: str
    ) -> AsyncGenerator[GenerationProgress, None]:
        """Yield progress events as they happen."""
        queue = _progress_queues.get(generation_id)
        if not queue:
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60)
                yield event
                if event.status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
                    break
            except asyncio.TimeoutError:
                break

    async def get_result(self, generation_id: str) -> Optional[GenerationResult]:
        """Get the final generation result."""
        res = _generations.get(generation_id)
        if res:
            return res
            
        # Fallback to Supabase
        from services.database import supabase
        if supabase:
            try:
                response = supabase.table("generations").select("*").eq("id", generation_id).execute()
                if response.data:
                    row = response.data[0]
                    final_content = row.get("final_content", {})
                    # Reconstruct GenerationResult from final_content json
                    from models.generation import GenerationResult
                    return GenerationResult(**final_content)
            except Exception as e:
                logger.error(f"Failed to fetch from Supabase: {e}")
                
        return None

    async def get_download_path(self, generation_id: str) -> Optional[str]:
        """Get the file path for PPTX download."""
        result = _generations.get(generation_id)
        if not result or result.status != GenerationStatus.COMPLETED:
            return None

        file_path = Path(settings.output_dir) / f"{generation_id}.pptx"
        if file_path.exists():
            return str(file_path)
        return None
