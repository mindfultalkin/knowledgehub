import os
from dotenv import load_dotenv
from urllib.parse import quote_plus


def get_environment_config():
    """Get configuration based on environment"""
    # Check for Railway environment
    is_railway = os.getenv("RAILWAY_ENVIRONMENT_NAME") is not None
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    
    if is_railway and railway_domain:
        # Railway deployment
        return {
            "SERVICE_API_BASE_URL": f"https://{railway_domain}/api",
            "FRONTEND_URL": f"https://{railway_domain}",
            "ALLOWED_ORIGINS": [f"https://{railway_domain}", "*"],
            "GOOGLE_REDIRECT_URIS": f"https://{railway_domain}/api/oauth2callback"
        }
    
    # Check for Vercel
    is_production = os.getenv("VERCEL_ENV") == "production"
    if is_production:
        return {
            "SERVICE_API_BASE_URL": "https://knowledgehub-production-9572.up.railway.app/api",
            "FRONTEND_URL": "https://knowledgehub-production-9572.up.railway.app",
            "ALLOWED_ORIGINS": ["https://knowledgehub-production-9572.up.railway.app"],
            "GOOGLE_REDIRECT_URIS": "https://knowledgehub-production-9572.up.railway.app/api/oauth2callback"
        }
    
    # Local development (default)
    return {
        "SERVICE_API_BASE_URL": "http://localhost:8000/api",
        "FRONTEND_URL": "http://localhost:5500",
        "ALLOWED_ORIGINS": ["http://localhost:5500", "http://127.0.0.1:5500", "*"],
        "GOOGLE_REDIRECT_URIS": "http://localhost:8000/api/oauth2callback"
    }


# Load environment variables from the .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# Load environment config
env_config = get_environment_config()

# ============================================================
# MYSQL DATABASE CONFIGURATION
# ============================================================
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Abhi@2003")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "knowledge_hub")
# URL-encode the password to handle special characters
MYSQL_PASSWORD_ENCODED = quote_plus(MYSQL_PASSWORD)

# SQLAlchemy Database URL with encoded password
MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# ============================================================
# STORAGE PATHS FOR DERIVED DATA
# ============================================================
DERIVED_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "derived_storage")
DERIVED_TEXT_DIR = os.path.join(DERIVED_STORAGE_DIR, "text")
DERIVED_THUMBNAIL_DIR = os.path.join(DERIVED_STORAGE_DIR, "thumbnails")

# Create directories if they don't exist
for directory in [DERIVED_STORAGE_DIR, DERIVED_TEXT_DIR, DERIVED_THUMBNAIL_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

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

# Redirect URI - Use environment-specific redirect URI
GOOGLE_REDIRECT_URIS = env_config["GOOGLE_REDIRECT_URIS"]

# OAuth Scopes
SCOPES = os.getenv(
    "GOOGLE_SCOPES",
    "https://www.googleapis.com/auth/drive.readonly,"
    "https://www.googleapis.com/auth/drive.metadata.readonly,"
    "https://www.googleapis.com/auth/documents.readonly"
).split(",")


# ----------------------------------------------------
# Server & Application Configuration
# ----------------------------------------------------
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))

# Use environment-specific URLs
SERVICE_API_BASE_URL = env_config["SERVICE_API_BASE_URL"]
FRONTEND_URL = env_config["FRONTEND_URL"]

# ----------------------------------------------------
# CORS Configuration
# ----------------------------------------------------
# Use environment-specific allowed origins
ALLOWED_ORIGINS = env_config["ALLOWED_ORIGINS"]

# ----------------------------------------------------
# Token Info (for loading existing credentials)
# ----------------------------------------------------
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
GOOGLE_TOKEN_EXPIRY = os.getenv("GOOGLE_TOKEN_EXPIRY", "")

# ----------------------------------------------------
# Model Storage Directory (Keep for clause extraction models)
# ----------------------------------------------------
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Create models directory if it doesn't exist
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

# ----------------------------------------------------
# Validation
# ----------------------------------------------------
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env file!")
    print("Please check your .env configuration.")

# Debug information
if __name__ == "__main__":
    print(f"Environment: {'Railway' if os.getenv('RAILWAY_ENVIRONMENT_NAME') else 'production' if os.getenv('VERCEL_ENV') == 'production' else 'development'}")
    print(f"API Base URL: {SERVICE_API_BASE_URL}")
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Redirect URI: {GOOGLE_REDIRECT_URIS}")
    print(f"Allowed Origins: {ALLOWED_ORIGINS}")
    print(f"Database URL: {MYSQL_DATABASE_URL}")
