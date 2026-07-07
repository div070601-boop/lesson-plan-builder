"""
Lesson Plan Builder — Backend Configuration
All settings are loaded from environment variables via .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Lesson Plan Builder API"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"

    # Supabase
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None

    # AI Providers
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None

    # OneDrive / Microsoft Graph
    ms_graph_client_id: Optional[str] = None
    ms_graph_client_secret: Optional[str] = None
    ms_graph_tenant_id: Optional[str] = None
    onedrive_folder_id: Optional[str] = None
    onedrive_share_urls: list[str] = []  # OneDrive share links to crawl

    # Provider priority lists (configurable per task type)
    embedding_providers: list[str] = ["gemini", "huggingface"]
    analysis_providers: list[str] = ["groq", "gemini", "cerebras"]
    generation_providers: list[str] = ["groq", "gemini", "cerebras"]
    planning_providers: list[str] = ["groq", "cerebras", "gemini"]

    # Generation
    max_slides: int = 30
    output_expiry_hours: int = 24
    temp_upload_dir: str = "./temp_uploads"
    output_dir: str = "./outputs"
    library_path: str = "./library"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

