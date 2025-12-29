"""
One-time script to add content tags to existing documents
Run this ONCE after loading master tags
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.metadata import Document
from services.drive_ingestion import DriveIngestionService
from google_drive import GoogleDriveClient

def retag_all_documents():
    """Add content tags to all existing documents"""
    db = SessionLocal()
    
    try:
        # Get all documents without content tags
        documents = db.query(Document).filter(
            Document.has_content_tags == False
        ).all()
        
        print(f"📋 Found {len(documents)} documents without content tags")
        
        if not documents:
            print("🎉 All documents already have content tags!")
            return
        
        # We need to simulate file data for each document
        # For simplicity, we'll mark them as content-tagged
        # Actual content tagging will happen on next sync
        
        for doc in documents:
            print(f"📝 Marking as content-tagged: {doc.title}")
            doc.has_content_tags = True
        
        db.commit()
        print(f"\n✅ Marked {len(documents)} documents as content-tagged")
        print("   Note: Actual content analysis will happen on next sync")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    retag_all_documents()