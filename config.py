import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "maintenance_tracker.db"
EXPORTS_DIR = BASE_DIR / "exports"
CREDENTIALS_FILE = BASE_DIR / "service_account.json"

EXPORTS_DIR.mkdir(exist_ok=True)

# Default system settings
DEFAULT_CONFIG = {
    "GOOGLE_SPREADSHEET_ID": os.getenv("GOOGLE_SPREADSHEET_ID", ""),
    "GOOGLE_SHEET_NAME": os.getenv("GOOGLE_SHEET_NAME", "Maintenance_Logs"),
    "META_WHATSAPP_TOKEN": os.getenv("META_WHATSAPP_TOKEN", ""),
    "META_PHONE_NUMBER_ID": os.getenv("META_PHONE_NUMBER_ID", ""),
    "META_VERIFY_TOKEN": os.getenv("META_VERIFY_TOKEN", "antigravity_verify_123"),
    "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID", ""),
    "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN", ""),
    "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER", ""),
    "SUPABASE_URL": os.getenv("SUPABASE_URL", "https://durbufowkgwimbmsunsq.supabase.co"),
    "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR1cmJ1Zm93a2d3aW1ibXN1bnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA2NzUzMzgsImV4cCI6MjEwNjI1MTMzOH0.u3w4eumVQKpoQ4ZsV30JKpQR-Kgmns2iEiJeJDsFPPw")
}
