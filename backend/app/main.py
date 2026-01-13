"""
Main FastAPI application - Run from app folder
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import config from the same app directory
try:
    from config import ALLOWED_ORIGINS, SERVICE_API_BASE_URL, FRONTEND_URL
    print("✅ Config imported successfully")
except ImportError as e:
    print(f"❌ Config import error: {e}")
    # Set defaults
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8000", "http://localhost:5500"]
    SERVICE_API_BASE_URL = "http://localhost:8000/api"
    FRONTEND_URL = "http://localhost:5500"

try:
    from database import test_connection
    print("✅ Database module imported")
except ImportError as e:
    print(f"❌ Database import error: {e}")
    def test_connection():
        return False

# Try to import the combined API router
try:
    from api import router
    print("✅ API router imported from api.py")
except ImportError as e:
    print(f"❌ API router import error: {e}")
    # Fallback: Try to import controllers individually
    try:
        print("🔄 Trying to import controllers...")
        from controllers.auth_controller import router as auth_router
        from controllers.clause_controller import router as clause_router
        from controllers.document_controller import router as document_router
        from controllers.risk_controller import router as risk_router
        from controllers.search_controller import router as search_router
        from controllers.sync_controller import router as sync_router
        from controllers.tag_controller import router as tag_router
        
        # Combine all routers
        from fastapi import APIRouter
        router = APIRouter()
        router.include_router(auth_router)
        router.include_router(clause_router)
        router.include_router(document_router)
        router.include_router(risk_router)
        router.include_router(search_router)
        router.include_router(sync_router)
        router.include_router(tag_router)
        print("✅ All controllers imported and combined")
    except ImportError as e2:
        print(f"❌ Controller import error: {e2}")
        # Create empty router
        from fastapi import APIRouter
        router = APIRouter()
        print("⚠️ Created empty router")

# Create FastAPI app
app = FastAPI(
    title="Knowledge Hub Backend",
    version="1.0.0",
    description="Document Management System with Google Drive Integration",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(router, prefix="/api")

print(f"✅ API routes registered with prefix /api")
print(f"🌐 API Base URL: {SERVICE_API_BASE_URL}")
print(f"🌍 Frontend URL: {FRONTEND_URL}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Knowledge Hub Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_base": SERVICE_API_BASE_URL,
        "frontend": FRONTEND_URL
    }

@app.get("/health")
async def health_check():
    db_ok = test_connection()
    return {
        "status": "online",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": "2025-01-13T20:20:00Z"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Knowledge Hub Application...")
    
    # Test database connection
    if test_connection():
        print("✅ Database connection successful")
    else:
        print("⚠️ Database connection failed")
    
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"🔧 Environment: {'production' if os.getenv('VERCEL_ENV') == 'production' else 'development'}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"\n{'='*50}")
    print(f"🚀 KNOWLEDGE HUB BACKEND")
    print(f"{'='*50}")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🌐 URL: http://localhost:{port}")
    print(f"📚 Docs: http://localhost:{port}/docs")
    print(f"{'='*50}\n")
    
    uvicorn.run("main:app", host=host, port=port, reload=True)