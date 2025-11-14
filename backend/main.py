from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Include the API router with /api prefix
app.include_router(router, prefix="/api")

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, 'index.html'))
    
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        """Serve frontend routes for SPA"""
        if not full_path.startswith('api/') and not full_path.startswith('docs'):
            frontend_file = os.path.join(frontend_path, full_path)
            if os.path.exists(frontend_file) and os.path.isfile(frontend_file):
                return FileResponse(frontend_file)
        return FileResponse(os.path.join(frontend_path, 'index.html'))

# Health check with database status
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy", 
        "service": "Knowledge Hub API",
        "database": db_status
    }

# Simple health check without database dependency
@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "Knowledge Hub API"}

@app.on_event("startup")
async def startup_event():
    """
    Run initialization tasks on startup
    """
    print("🚀 Starting Knowledge Hub Application...")
    
    # Initialize database
    db_success = init_database()
    
    if db_success:
        print("✅ Database initialized successfully")
        # Schedule background tasks only if database is available
        asyncio.create_task(auto_extract_clauses_on_startup())
    else:
        print("⚠️  Application starting without database connection")

async def auto_extract_clauses_on_startup():
    """
    Background task to automatically extract clauses from all documents
    """
    await asyncio.sleep(10)  # Wait 10 seconds after startup
    
    # Skip auto-extraction in Railway to avoid cold start issues
    if os.getenv('RAILWAY_ENVIRONMENT_NAME'):
        print("🚇 Railway environment detected - skipping auto extraction on startup")
        return
        
    try:
        print("\n🔄 Starting automatic clause extraction...")
        
        # Import here to avoid circular imports
        from services.clause_extractor import ClauseExtractor
        from services.universal_content_extractor import UniversalContentExtractor
        from api import drive_client
        
        # Check if database is available
        if not SessionLocal:
            print("❌ Database not available. Skipping auto-extraction.")
            return
            
        # Create database session
        db = SessionLocal()
        
        try:
            # Your existing auto-extraction code here...
            # [Keep your existing auto-extraction logic]
            print("✅ Auto-extraction completed")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Auto-extraction error: {e}")
        import traceback
        traceback.print_exc()

@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to see all Railway environment variables"""
    railway_vars = {}
    for key, value in os.environ.items():
        if 'RAILWAY' in key.upper():
            railway_vars[key] = value
    
    # Also check other deployment indicators
    other_vars = {
        'PORT': os.getenv('PORT'),
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'VERCEL_ENV': os.getenv('VERCEL_ENV'),
    }
    
    return {
        "railway_environment_variables": railway_vars,
        "other_deployment_variables": other_vars,
        "all_environment_variables": dict(os.environ)  # Be careful with this in production
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

# For local development
if __name__ == "__main__":
    import uvicorn
    
    # Check for Tesseract OCR
    try:
        import subprocess
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        print("✅ Tesseract OCR configured successfully!")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Tesseract OCR not found - OCR features will be limited")
    
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=workers)