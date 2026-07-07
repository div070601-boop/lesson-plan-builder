from supabase import create_client, Client
import logging
from config import settings

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client | None = None

if settings.supabase_url and settings.supabase_service_role_key:
    try:
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase = None
else:
    logger.warning("Supabase URL or Service Role Key not set. Running without Supabase.")

