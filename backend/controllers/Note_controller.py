# backend/controllers/note_controller.py
"""
Note Controller — Create Google Docs from user notes and save to Drive.
Uses the existing drive_client (same pattern as all other controllers).
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from core.google_client import drive_client

router = APIRouter()


# ==================== PYDANTIC MODELS ====================

class CreateNoteRequest(BaseModel):
    fileName: str
    content: str


# ==================== ROUTES ====================

@router.post("/notes/create")
async def create_note(request: CreateNoteRequest):
    """
    Create a Google Doc in the user's Drive from note content.
    Uses the existing drive_client credentials — no session needed.

    Body:
        fileName  (str) — desired document name (auto-appends .docx if missing)
        content   (str) — plain text content to write into the doc

    Returns:
        fileId, fileName, webViewLink, createdTime
    """
    if not drive_client or not drive_client.creds:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")

    file_name = request.fileName.strip()
    content = request.content.strip()

    if not file_name:
        raise HTTPException(status_code=400, detail="File name is required")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    # Ensure .docx extension so it displays as a proper document
    if not file_name.lower().endswith(".docx"):
        file_name = f"{file_name}.docx"

    try:
        creds = drive_client.creds
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)

        # Step 1: Create an empty Google Doc
        file_metadata = {
            "name": file_name,
            "mimeType": "application/vnd.google-apps.document",
        }

        file = drive_service.files().create(
            body=file_metadata,
            fields="id, name, webViewLink, createdTime",
        ).execute()

        doc_id = file["id"]
        print(f"📝 Created Google Doc: {file['name']} (ID: {doc_id})")

        # Step 2: Insert the content into the doc
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 1},
                            "text": content,
                        }
                    }
                ]
            },
        ).execute()

        print(f"✅ Note content written to doc: {doc_id}")

        return {
            "success": True,
            "message": "Note created successfully",
            "fileId": doc_id,
            "fileName": file["name"],
            "webViewLink": file.get("webViewLink"),
            "createdTime": file.get("createdTime"),
        }

    except Exception as e:
        print(f"❌ Error creating note: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")


@router.get("/notes/health")
async def notes_health():
    """Quick check that the notes service is available"""
    return {
        "status": "healthy",
        "drive_connected": bool(drive_client and drive_client.creds),
    }