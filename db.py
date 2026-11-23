from pathlib import Path
import logging
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent / '.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = (create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            if SUPABASE_URL and SUPABASE_SERVICE_KEY else None)

if supabase is None:
    missing = [name for name, value in (('SUPABASE_URL', SUPABASE_URL),
                                        ('SUPABASE_SERVICE_KEY', SUPABASE_SERVICE_KEY)) if not value]
    logging.getLogger(__name__).warning(
        'Supabase is not configured (missing %s). Copy .env.example to .env and fill it in; '
        'database pages will return 503 until then.', ', '.join(missing))
