import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google OAuth Configuration from .env
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

# OAuth URIs
GOOGLE_AUTH_URI = os.getenv('GOOGLE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
GOOGLE_TOKEN_URI = os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token')
GOOGLE_AUTH_PROVIDER_CERT_URL = os.getenv('GOOGLE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs')

# Redirect URIs
GOOGLE_REDIRECT_URIS = os.getenv('GOOGLE_REDIRECT_URIS', 'http://localhost:8000/oauth2callback,http://localhost:5500/oauth2callback').split(',')

# OAuth Scopes
SCOPES = os.getenv('GOOGLE_SCOPES', 'https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/drive.metadata.readonly').split(',')

# Server Configuration
BACKEND_HOST = os.getenv('BACKEND_HOST', '0.0.0.0')
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 8000))

# CORS Configuration
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5500,http://localhost:8000,http://127.0.0.1:5500,http://127.0.0.1:8000').split(',')

# Token information (for loading existing tokens)
GOOGLE_ACCESS_TOKEN = os.getenv('GOOGLE_ACCESS_TOKEN', '')
GOOGLE_REFRESH_TOKEN = os.getenv('GOOGLE_REFRESH_TOKEN', '')
GOOGLE_TOKEN_EXPIRY = os.getenv('GOOGLE_TOKEN_EXPIRY', '')

# Validate required environment variables
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env file!")
    print("Please check your .env file configuration.")
