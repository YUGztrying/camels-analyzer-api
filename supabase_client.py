import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.warning("SUPABASE_URL / SUPABASE_SERVICE_KEY not set — Supabase calls will fail")


def get_client() -> Client:
    """Return a Supabase client using the service-role key."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
