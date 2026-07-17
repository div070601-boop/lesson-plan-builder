"""
Lesson Plan Builder — FastAPI Backend
AI-powered lesson plan generation for Acemac's L&D team.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings
from routers import brief, generate, history, library, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Create required directories
    Path(settings.temp_upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.library_path).mkdir(parents=True, exist_ok=True)
    print(f"[START] {settings.app_name} v{settings.app_version} starting...")
    print(f"   Debug mode: {settings.debug}")
    print(f"   CORS origins: {settings.cors_origins}")

    # Load deck cache from Supabase for instant serving
    try:
        from services.library import load_cache_from_supabase
        cached = load_cache_from_supabase()
        print(f"   📦 Deck cache: {len(cached)} decks loaded from Supabase")
    except Exception as e:
        print(f"   ⚠️  Deck cache load failed: {e}")

    yield
    print("[STOP] Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered lesson plan generation grounded in deep pedagogical analysis of existing content libraries.",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and any production HTTPS domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex="https://.*|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(brief.router)
app.include_router(generate.router)
app.include_router(history.router)
app.include_router(library.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from services.providers import provider_service

    return {
        "status": "healthy",
        "version": settings.app_version,
        "providers": provider_service.get_status(),
    }
