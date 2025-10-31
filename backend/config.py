import os
from dotenv import load_dotenv

# Load environment variables from the .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# ----------------------------------------------------
# Google OAuth Configuration
# ----------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# OAuth URIs
GOOGLE_AUTH_URI = os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
GOOGLE_TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
GOOGLE_AUTH_PROVIDER_CERT_URL = os.getenv("GOOGLE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs")

# Redirect URIs
GOOGLE_REDIRECT_URIS = os.getenv(
    "GOOGLE_REDIRECT_URIS",
    "http://localhost:5500,http://localhost:8000,http://127.0.0.1:5500,http://127.0.0.1:8000,https://knowledgehub-eta.vercel.app/,https://knowledgehub-eta.vercel.app/api"
).split(",")

# OAuth Scopes
SCOPES = os.getenv(
    "GOOGLE_SCOPES",
    "https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive.metadata.readonly"
).split(",")

# ----------------------------------------------------
# Server & Application Configuration
# ----------------------------------------------------
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
SERVICE_API_BASE_URL = os.getenv("SERVICE_API_BASE_URL", "https://knowledgehub-eta.vercel.app/api")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://knowledgehub-eta.vercel.app/")

# ----------------------------------------------------
# CORS Configuration
# ----------------------------------------------------
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://localhost:8000,http://127.0.0.1:5500,http://127.0.0.1:8000,https://knowledgehub-eta.vercel.app/,https://knowledgehub-eta.vercel.app/api"
).split(",")

# ----------------------------------------------------
# Token Info (for loading existing credentials)
# ----------------------------------------------------
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_TOKEN_EXPIRY = os.getenv("GOOGLE_TOKEN_EXPIRY", "")

# ----------------------------------------------------
# Validation
# ----------------------------------------------------
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env file!")
    print("Please check your .env configuration.")
