import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prospects.db")

# App settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
PORT = int(os.getenv("PORT", "8000"))

# Heyreach API settings
HEYREACH_API_KEY = os.getenv("HEYREACH_API_KEY", "")
HEYREACH_API_BASE_URL = os.getenv("HEYREACH_API_BASE_URL", "https://api.heyreach.io/api/public")
HEYREACH_CAMPAIGN_ID = os.getenv("HEYREACH_CAMPAIGN_ID", "")
