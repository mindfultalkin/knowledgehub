# backend/controllers/note_controller.py
"""
Note Controller — Create Google Docs from user notes and save to Drive.

Supports two content modes:
  * htmlContent (preferred) — rich text from the frontend editor. We upload
    the HTML to Drive with target MIME application/vnd.google-apps.document,
    and Drive natively converts it to a Google Doc preserving headings,
    bold/italic/underline, lists, alignment, colors, font family/size, etc.
  * content (fallback) — plain text. We create an empty Doc and insertText
    via the Docs API (legacy behavior, backward compatible).

After the Google Doc is created we also:
  * insert a `documents` row so the note appears in the app immediately
    (without waiting for the next Drive sync),
  * ensure a "Note" tag exists, and
  * link the new document to that tag via `document_tags`.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from core.google_client import drive_client
from database import get_db
from models.metadata import Document, Tag, DocumentTag, ContentType

router = APIRouter()


# Fields we ask Drive to return when creating the file. Kept in one place so
# the two creation paths stay in sync.
_CREATE_FIELDS = (
    "id, name, mimeType, webViewLink, iconLink, thumbnailLink, "
    "createdTime, modifiedTime, parents, "
    "owners(emailAddress,displayName)"
)

# Canonical name of the auto-tag we attach to every created note.
_NOTE_TAG_NAME = "Note"

# Every note created via the app is filed into a single top-level folder in
# the user's Drive so they don't clutter the root "My Drive" view. The folder
# is resolved by name (case-insensitive) and cached per-process. If the user
# has renamed/trashed their folder we auto-recreate one so the save flow is
# never blocked.
_NOTES_FOLDER_NAME = "Notes"
_notes_folder_cache: dict[str, str] = {}


# ==================== PYDANTIC MODELS ====================


class CreateNoteRequest(BaseModel):
    fileName: str
    content: str
    # Optional rich-text HTML. When present, it takes precedence over `content`
    # and is converted to a native Google Doc by Drive on upload.
    htmlContent: Optional[str] = None


# ==================== ROUTES ====================


@router.post("/notes/create")
async def create_note(request: CreateNoteRequest, db: Session = Depends(get_db)):
    """Create a Google Doc in the user's Drive from note content."""
    if not drive_client or not drive_client.creds:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")

    file_name = request.fileName.strip()
    content = (request.content or "").strip()
    html_content = (request.htmlContent or "").strip()

    if not file_name:
        raise HTTPException(status_code=400, detail="File name is required")
    if not content and not html_content:
        raise HTTPException(status_code=400, detail="Content is required")

    # Ensure .docx extension so it displays as a proper document
    if not file_name.lower().endswith(".docx"):
        file_name = f"{file_name}.docx"

    try:
        creds = drive_client.creds
        drive_service = build("drive", "v3", credentials=creds)

        # Resolve (or create) the "Notes" folder and file every note there.
        # Failure to resolve shouldn't block note creation — fall back to
        # creating the Doc at the Drive root and surface a warning log.
        notes_folder_id = _get_or_create_notes_folder(drive_service)
        parents = [notes_folder_id] if notes_folder_id else None

        # ---- Rich-text path: upload HTML; Drive converts to a Google Doc ----
        if html_content:
            media = MediaInMemoryUpload(
                _wrap_html_document(html_content).encode("utf-8"),
                mimetype="text/html",
                resumable=False,
            )
            body = {
                "name": file_name,
                "mimeType": "application/vnd.google-apps.document",
            }
            if parents:
                body["parents"] = parents
            file_info = drive_service.files().create(
                body=body,
                media_body=media,
                fields=_CREATE_FIELDS,
            ).execute()
            print(
                f"📝 Created Google Doc from rich text: {file_info['name']} "
                f"(ID: {file_info['id']}) in folder {notes_folder_id or 'ROOT'}"
            )

        # ---- Plain-text path (legacy) ----
        else:
            body = {
                "name": file_name,
                "mimeType": "application/vnd.google-apps.document",
            }
            if parents:
                body["parents"] = parents
            file_info = drive_service.files().create(
                body=body,
                fields=_CREATE_FIELDS,
            ).execute()
            doc_id = file_info["id"]
            print(
                f"📝 Created Google Doc: {file_info['name']} "
                f"(ID: {doc_id}) in folder {notes_folder_id or 'ROOT'}"
            )

            docs_service = build("docs", "v1", credentials=creds)
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={
                    "requests": [
                        {"insertText": {"location": {"index": 1}, "text": content}}
                    ]
                },
            ).execute()
            print(f"✅ Note content written to doc: {doc_id}")

        # ---- Persist to DB + attach the "Note" tag ----
        # Wrapped in its own try so a DB problem never fails the whole request
        # (the Doc itself was already created successfully in Drive).
        try:
            _persist_note_and_tag(db, file_info)
        except Exception as persist_err:
            print(f"⚠️  Note saved to Drive, but DB persistence failed: {persist_err}")
            import traceback
            traceback.print_exc()

        return {
            "success": True,
            "message": "Note created successfully",
            "fileId": file_info["id"],
            "fileName": file_info["name"],
            "webViewLink": file_info.get("webViewLink"),
            "createdTime": file_info.get("createdTime"),
            "autoTag": _NOTE_TAG_NAME,
        }

    except HTTPException:
        raise
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


# ==================== HELPERS ====================


def _get_or_create_notes_folder(drive_service) -> Optional[str]:
    """
    Resolve the ID of the top-level "Notes" folder in the connected user's
    Drive. If the folder doesn't exist yet, create it. The ID is cached
    per-process keyed by the connected Drive account email, so the lookup
    only happens once per server lifetime (and again after the folder is
    re-created because the user trashed the old one).

    Never raises — returns ``None`` if resolution fails, in which case the
    caller should fall back to saving the note at the Drive root so the
    user never loses their note content.
    """
    # Cache key: the account email attached to the credentials currently in
    # drive_client. If the backend ever supports multiple simultaneous Drive
    # accounts this will transparently give each its own cached folder id.
    try:
        account_email = getattr(drive_client, "account_email", None) or "default"
    except Exception:
        account_email = "default"

    cached_id = _notes_folder_cache.get(account_email)
    if cached_id:
        # Verify the cached folder still exists and isn't trashed. Drive
        # occasionally returns 404 if the user deleted the folder since
        # we last cached it.
        try:
            meta = drive_service.files().get(
                fileId=cached_id,
                fields="id, trashed",
            ).execute()
            if not meta.get("trashed"):
                return cached_id
            # Cache was stale — folder is trashed. Fall through to re-resolve.
            _notes_folder_cache.pop(account_email, None)
        except Exception:
            # Stale cache (folder deleted, permissions changed, etc.) —
            # drop it and look up afresh.
            _notes_folder_cache.pop(account_email, None)

    # 1) Look for an existing, non-trashed folder named "Notes" that the
    #    current user owns. We prefer a root-level match but accept any
    #    location if that's all we find.
    try:
        # Escape single quotes in the configured name for the Drive `q` syntax.
        safe_name = _NOTES_FOLDER_NAME.replace("'", "\\'")
        query = (
            f"name = '{safe_name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        result = drive_service.files().list(
            q=query,
            spaces="drive",
            corpora="user",
            fields="files(id, name, parents)",
            pageSize=50,
        ).execute()
        folders = result.get("files", []) or []

        # Prefer root-level folders (parent == "root" or the actual root id).
        root_matches = [f for f in folders if _is_root_level(f)]
        chosen = root_matches[0] if root_matches else (folders[0] if folders else None)

        if chosen:
            folder_id = chosen["id"]
            _notes_folder_cache[account_email] = folder_id
            print(f"📁 Using existing '{_NOTES_FOLDER_NAME}' folder: {folder_id}")
            return folder_id
    except Exception as e:
        print(f"⚠️  Drive folder lookup failed: {e}")

    # 2) Nothing found — create a fresh root-level "Notes" folder.
    try:
        created = drive_service.files().create(
            body={
                "name": _NOTES_FOLDER_NAME,
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()
        folder_id = created["id"]
        _notes_folder_cache[account_email] = folder_id
        print(f"📁 Created '{_NOTES_FOLDER_NAME}' folder: {folder_id}")
        return folder_id
    except Exception as e:
        print(f"⚠️  Failed to create '{_NOTES_FOLDER_NAME}' folder: {e}")
        return None


def _is_root_level(folder: dict) -> bool:
    """
    A folder is "root-level" when its only parent is the Drive root. Drive
    represents the root either as the literal string ``"root"`` or as the
    account's actual root folder id (an opaque string). We don't know the
    latter without an extra API call, so we treat any single-parent folder
    as root-level — that's strictly better than filtering too aggressively
    and missing the user's real folder.
    """
    parents = folder.get("parents") or []
    if len(parents) != 1:
        return False
    return True


def _wrap_html_document(html_body: str) -> str:
    """
    Wrap the editor's HTML fragment in a minimal, well-formed HTML document
    so Drive's HTML→Docs converter produces consistent results regardless
    of what fragment shape the frontend sent.
    """
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        "</head><body>"
        f"{html_body}"
        "</body></html>"
    )


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _persist_note_and_tag(db: Session, file_info: dict) -> None:
    """
    Insert a `documents` row for the freshly-created note (if not already
    present) and attach the canonical "Note" tag. Idempotent — safe to call
    more than once for the same file_id.
    """
    file_id = file_info.get("id")
    name = file_info.get("name")
    if not file_id or not name:
        return

    owners = file_info.get("owners") or []
    owner_email = owners[0].get("emailAddress") if owners else None
    owner_name = owners[0].get("displayName") if owners else None
    created_at = _parse_iso(file_info.get("createdTime"))
    modified_at = _parse_iso(file_info.get("modifiedTime")) or created_at

    # --- 1) Upsert the Document row ---
    doc = db.query(Document).filter(Document.id == file_id).first()
    if not doc:
        doc = Document(
            id=file_id,
            drive_file_id=file_id,
            title=name,
            mime_type=file_info.get("mimeType"),
            file_format=".docx",
            file_url=file_info.get("webViewLink"),
            icon_link=file_info.get("iconLink"),
            thumbnail_link=file_info.get("thumbnailLink"),
            content_type=ContentType.PRACTICE_NOTE,
            owner_email=owner_email,
            owner_name=owner_name,
            account_email=owner_email,
            created_at=created_at,
            modified_at=modified_at,
        )
        db.add(doc)
        db.flush()
        print(f"🗄️  Inserted document row for note: {file_id}")
    else:
        # Edge case: row exists (e.g. Drive sync ran between request start
        # and DB write). Just make sure content_type is set.
        if doc.content_type is None:
            doc.content_type = ContentType.PRACTICE_NOTE
            db.flush()

    # --- 2) Upsert the "Note" tag ---
    note_tag = db.query(Tag).filter(Tag.name == _NOTE_TAG_NAME).first()
    if not note_tag:
        note_tag = Tag(name=_NOTE_TAG_NAME, category="document_type")
        db.add(note_tag)
        db.flush()
        print(f"🏷️  Created tag: {_NOTE_TAG_NAME}")

    # --- 3) Link them (if not already linked) ---
    already = db.query(DocumentTag).filter(
        DocumentTag.document_id == file_id,
        DocumentTag.tag_id == note_tag.id,
    ).first()
    if not already:
        db.add(DocumentTag(
            document_id=file_id,
            tag_id=note_tag.id,
            source="auto_note",
            confidence_score=1.0,
            created_by=owner_email,
        ))
        print(f"🔗 Linked document {file_id} to '{_NOTE_TAG_NAME}' tag")

    db.commit()
