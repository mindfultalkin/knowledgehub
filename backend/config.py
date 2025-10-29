import os

# ========================================
# IMPORTANT: Replace with YOUR credentials!
# ========================================
GOOGLE_CLIENT_ID = "762643628753-3fl7gtj1q290nkcmo91sgr1tpuphepr7.apps.googleusercontent.com"
GOOGLE_API_KEY = "AIzaSyCHMv90jjDv55k7h8n__ZeS150oGCkmKQk"

# OAuth Scopes (what permissions we need)
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# Server Configuration
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000

# CORS Configuration (allow these origins to access the API)
ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "http://localhost:3000"
]
