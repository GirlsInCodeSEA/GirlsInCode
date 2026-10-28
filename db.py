from pathlib import Path
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent / '.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
supabase = (create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            if SUPABASE_URL and SUPABASE_SERVICE_KEY else None)
