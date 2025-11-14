from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
import asyncio

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from .config import ALLOWED_ORIGINS
from .api import router
from .database import SessionLocal, Base, engine
from .models import Document, DocumentClause, ClauseLibrary

# Create database tables
Base.metadata.create_all(bind=engine)

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

async def auto_extract_clauses_on_startup():
    """
    Background task to automatically extract clauses from all documents
    """
    await asyncio.sleep(10)  # Wait 10 seconds after startup to ensure app is ready
    
    # Skip auto-extraction in Railway to avoid cold start issues
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("🚇 Railway environment detected - skipping auto extraction on startup")
        return
        
    try:
        print("\n🔄 Starting automatic clause extraction...")
        
        # Import here to avoid circular imports
        from services.clause_extractor import ClauseExtractor
        from services.universal_content_extractor import UniversalContentExtractor
        from api import drive_client  # Import from api module
        
        # Create database session
        db = SessionLocal()
        
        # Check if drive client exists
        if not drive_client:
            print("❌ Google Drive not connected. Skipping auto-extraction.")
            db.close()
            return
        
        # Get all files from Google Drive
        files_response = drive_client.service.files().list(
            pageSize=50,  # Reduced for Railway
            fields="files(id, name, mimeType)",
            q="trashed=false"
        ).execute()
        
        files = files_response.get('files', [])
        
        # Filter only document files (PDF, DOCX, Google Docs)
        doc_files = [
            f for f in files 
            if any(ext in f['mimeType'].lower() for ext in ['pdf', 'word', 'document', 'text'])
        ]
        
        print(f"📄 Found {len(doc_files)} document files to process")
        
        content_extractor = UniversalContentExtractor(drive_client)
        clause_extractor = ClauseExtractor()
        
        for idx, file in enumerate(doc_files, 1):
            try:
                file_id = file['id']
                file_name = file['name']
                mime_type = file['mimeType']
                
                # Check if already extracted
                existing = db.query(DocumentClause).filter(
                    DocumentClause.document_id == file_id
                ).first()
                
                if existing:
                    print(f"  ⏭️  [{idx}/{len(doc_files)}] Skipping {file_name} (already extracted)")
                    continue
                
                print(f"  🔍 [{idx}/{len(doc_files)}] Extracting clauses from: {file_name}")
                
                # Extract content
                content = content_extractor.extract_content(file_id, mime_type)
                
                if not content or len(content) < 50:  # Reduced threshold
                    print(f"     ⚠️  Skipped (insufficient content)")
                    continue
                
                # Extract clauses
                clauses = clause_extractor.extract(content)
                
                if not clauses:
                    print(f"     ⚠️  No clauses found")
                    continue
                
                # Save to database (limit clauses to avoid memory issues)
                for clause in clauses[:20]:  # Limit clauses per document
                    db_clause = DocumentClause(
                        document_id=file_id,
                        clause_number=clause['clause_number'],
                        section_number=clause.get('section_number', str(clause['clause_number'])),
                        clause_title=clause['title'],
                        clause_content=clause['content'][:1000]  # Limit content length
                    )
                    db.add(db_clause)
                
                db.commit()
                print(f"     ✅ Extracted {len(clauses[:20])} clauses")
                
            except Exception as e:
                print(f"     ❌ Error processing {file['name']}: {str(e)}")
                db.rollback()
                continue
        
        db.close()
        print("\n✅ Automatic clause extraction completed!\n")
        
    except Exception as e:
        print(f"❌ Auto-extraction error: {e}")
        import traceback
        print(traceback.format_exc())

# Schedule auto-extraction on startup
@app.on_event("startup")
async def startup_event():
    """
    Run background tasks on startup
    """
    # Don't block startup with extraction in production
    asyncio.create_task(auto_extract_clauses_on_startup())

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Knowledge Hub API"}

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
    workers = int(os.getenv("WORKERS", 1))  # Default to 1 worker for Railway
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=workers)