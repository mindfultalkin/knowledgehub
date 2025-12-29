from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import sys
import asyncio


# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import ALLOWED_ORIGINS
from api import router
from database import SessionLocal, Base, engine, init_database, get_db
from sqlalchemy.orm import Session


app = FastAPI(
    title="Knowledge Hub Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ API ROUTES FIRST (CRITICAL!)
app.include_router(router, prefix="/api")


# Health check with database status
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from database import test_connection, MYSQL_HOST, MYSQL_DATABASE
    
    db_ok = test_connection()
    
    return {
        "status": "online",
        "database": {
            "connected": db_ok,
            "host": MYSQL_HOST,
            "database": MYSQL_DATABASE
        }
    }


# Simple health check without database dependency
@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "Knowledge Hub API"}


@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to see all Railway environment variables"""
    railway_vars = {}
    for key, value in os.environ.items():
        if 'RAILWAY' in key.upper():
            railway_vars[key] = value
    
    other_vars = {
        'PORT': os.getenv('PORT'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'VERCEL_ENV': os.getenv('VERCEL_ENV'),
    }
    
    return {
        "railway_environment_variables": railway_vars,
        "other_deployment_variables": other_vars,
        "all_environment_variables": dict(os.environ)
    }


@app.get("/debug/database")
async def debug_database():
    """Debug endpoint to check database connection"""
    try:
        from database import test_connection, engine
        connection_status = test_connection()
        
        return {
            "database_connected": connection_status,
            "database_url": str(engine.url) if engine else "No engine",
            "environment": {
                "MYSQL_HOST": os.getenv("MYSQL_HOST"),
                "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
                "MYSQL_USER": os.getenv("MYSQL_USER"),
                "MYSQL_PORT": os.getenv("MYSQL_PORT"),
            }
        }
    except Exception as e:
        return {"error": str(e)}


# ✅ FRONTEND SERVING (AFTER ALL OTHER ROUTES)
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    
    @app.get("/", include_in_schema=False)
    async def serve_root():
        """Serve frontend index.html at root"""
        return FileResponse(os.path.join(frontend_path, 'index.html'))
    
    @app.get("/{file_path:path}", include_in_schema=False)
    async def serve_static(file_path: str):
        """Serve static frontend files"""
        # Don't serve for API/system routes
        if file_path.startswith(('api/', 'docs', 'health', 'ready', 'debug', 'openapi')):
            raise HTTPException(status_code=404, detail="Not found")
        
        file_full_path = os.path.join(frontend_path, file_path)
        
        # Check if file exists
        if os.path.exists(file_full_path) and os.path.isfile(file_full_path):
            return FileResponse(file_full_path)
        
        # If not found, return index.html for SPA routing
        return FileResponse(os.path.join(frontend_path, 'index.html'))


@app.on_event("startup")
async def startup_event():
    """Run initialization tasks on startup - RAILWAY SAFE"""
    print("🚀 Starting Knowledge Hub Application...")
    
    db_success = init_database()
    
    if db_success:
        print("✅ Database initialized successfully")
        
        # ✅ RAILWAY SAFE: Skip auto_extract_clauses_on_startup() - causes faiss crash
        if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
            print("🚇 Railway detected - skipping auto-extraction (faiss safe)")
        else:
            print("🏠 Local - running auto-extraction")
            asyncio.create_task(auto_extract_clauses_on_startup())
    else:
        print("⚠️ Application starting without database connection")

# ✅ DISABLE auto_extract_clauses_on_startup for Railway
async def auto_extract_clauses_on_startup():
    """Background task - SKIPPED on Railway"""
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        print("🚇 Skipping clause extraction on Railway (faiss safe)")
        return
        
    await asyncio.sleep(10)
    
    try:
        print("\n🔄 Starting automatic clause extraction...")
        
        from services.clause_extractor import ClauseExtractor
        from services.universal_content_extractor import UniversalContentExtractor
        from api import drive_client
        
        if not SessionLocal:
            print("❌ Database not available. Skipping auto-extraction.")
            return
            
        db = SessionLocal()
        
        try:
            print("✅ Auto-extraction completed")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Auto-extraction error: {e}")
        import traceback
        traceback.print_exc()


# For local development
if __name__ == "__main__":
    import uvicorn
    
    try:
        import subprocess
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        print("✅ Tesseract OCR configured successfully!")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Tesseract OCR not found - OCR features will be limited")
    
    from api import drive_client
    if drive_client and drive_client.creds:
        print("✅ Google Drive credentials already loaded")
    else:
        print("ℹ️  Skipping auto-load - user must connect manually")
    
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=workers)
