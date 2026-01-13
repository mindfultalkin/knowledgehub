"""
Tag management controllers
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

# Import models
from database import get_db
from app.models.document import Document
from app.models.tag import Tag, DocumentTag

router = APIRouter()

class TagUpdateRequest(BaseModel):
    tag: str

def _load_tags_from_doc(doc, db: Session):
    """
    Load tag NAMES for a document from DocumentTag/Tag tables.
    """
    from app.models.tag import Tag, DocumentTag
    
    # Query tags for this document
    tags = db.query(Tag).join(
        DocumentTag, Tag.id == DocumentTag.tag_id
    ).filter(
        DocumentTag.document_id == doc.id
    ).all()
    
    return [tag.name for tag in tags if tag and tag.name]

def _save_tags_to_doc(doc, tag_names, db: Session):
    """
    Replace current tags with provided tag_names list.
    Safe version: handles errors and rolls back.
    """
    try:
        db.query(DocumentTag).filter(DocumentTag.document_id == doc.id).delete()
        db.flush()

        for name in tag_names:
            clean = name.strip()
            if not clean:
                continue

            tag_obj = db.query(Tag).filter(Tag.name == clean).first()
            if not tag_obj:
                tag_obj = Tag(name=clean, category="custom")
                db.add(tag_obj)
                db.flush()

            link = DocumentTag(document_id=doc.id, tag_id=tag_obj.id)
            db.add(link)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Tag save error for document {doc.id}: {e}")
        raise

def _get_document_by_any_id(db: Session, doc_id: str):
    # Try primary key
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        return doc
    # Try drive_file_id (when frontend passes Drive ID)
    return db.query(Document).filter(Document.drive_file_id == doc_id).first()

@router.post("/documents/{document_id}/tags/add")
async def add_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    print("\n================ TAG ADD DEBUG START ================")

    try:
        print("➡️ URL document_id:", document_id)

        tag_name = (payload.tag or "").strip()
        print("➡️ Payload tag:", tag_name)

        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        # STEP 1: Find document
        doc = db.query(Document).filter(
            (Document.drive_file_id == document_id) | (Document.id == document_id)
        ).first()

        print("➡️ Document found:", bool(doc))
        if doc:
            print("   doc.id:", doc.id)
            print("   doc.drive_file_id:", doc.drive_file_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # STEP 2: Get or create tag
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        print("➡️ Tag exists:", bool(tag))

        if not tag:
            tag = Tag(name=tag_name, category="user")
            db.add(tag)
            db.flush()
            print("✅ Tag created with id:", tag.id)
        else:
            print("➡️ Tag id:", tag.id)

        # STEP 3: Check existing relation
        existing = db.execute(
            text("""
                SELECT id FROM document_tags
                WHERE document_id = :doc_id AND tag_id = :tag_id
            """),
            {"doc_id": doc.id, "tag_id": tag.id}
        ).fetchone()

        print("➡️ Existing document_tag row:", existing)

        if not existing:
            print("➡️ Attempting INSERT into document_tags")

            result = db.execute(
                text("""
                    INSERT INTO document_tags
                    (document_id, tag_id, source, created_by, created_at)
                    VALUES (:doc_id, :tag_id, 'user', 'web_ui', NOW())
                """),
                {"doc_id": doc.id, "tag_id": tag.id}
            )

            print("➡️ INSERT executed")
            print("➡️ rowcount:", result.rowcount)

        print("➡️ Committing transaction")
        db.commit()

        # STEP 5: Fetch ALL tags for this document
        all_tags = db.query(Tag.name).join(
            DocumentTag, Tag.id == DocumentTag.tag_id
        ).filter(
            DocumentTag.document_id == doc.id
        ).all()

        tags_list = [t[0] for t in all_tags]


        # STEP 4: VERIFY USING SAME CONNECTION
        verify = db.execute(
            text("""
                SELECT id, document_id, tag_id
                FROM document_tags
                WHERE document_id = :doc_id AND tag_id = :tag_id
            """),
            {"doc_id": doc.id, "tag_id": tag.id}
        ).fetchall()

        print("🔥 VERIFICATION ROWS AFTER COMMIT:", verify)

        # EXTRA: show DB name + connection id
        db_name = db.execute(text("SELECT DATABASE()")).scalar()
        conn_id = db.execute(text("SELECT CONNECTION_ID()")).scalar()
        print("🔥 DATABASE:", db_name)
        print("🔥 CONNECTION_ID:", conn_id)

        print("================ TAG ADD DEBUG END =================\n")

        return {
            "success": True,
            "document_id": document_id,
            "tags": tags_list,
            "message": f"Tag '{tag_name}' added (debug mode)"
        }

    except Exception as e:
        print("❌ EXCEPTION:", e)
        db.rollback()
        raise


@router.post("/documents/{document_id}/tags/remove")
async def remove_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    try:
        tag_name = (payload.tag or "").strip()
        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        doc = db.query(Document).filter(
            (Document.drive_file_id == document_id) | (Document.id == document_id)
        ).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        effective_document_id = document_id  # 🔥

        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        doc_tag = db.query(DocumentTag).filter(
            DocumentTag.document_id == effective_document_id,
            DocumentTag.tag_id == tag.id
        ).first()

        if doc_tag:
            db.delete(doc_tag)
            db.commit()

        all_tags_from_db = db.query(Tag.name).join(
            DocumentTag, Tag.id == DocumentTag.tag_id
        ).filter(
            DocumentTag.document_id == effective_document_id
        ).all()

        tags_list = [t[0] for t in all_tags_from_db if t and t[0]]

        return {
            "success": True,
            "document_id": effective_document_id,
            "tags": tags_list
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))