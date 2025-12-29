"""
Google Drive Ingestion Service
Syncs files from Google Drive to database with multi-user support
"""
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from google_drive import GoogleDriveClient
from models.metadata import (
    Document, 
    ProcessingQueue, 
    SyncCheckpoint, 
    TaskType, 
    ProcessingStatus,
    Tag,
    DocumentTag
)
from tagging import SimpleTagger
import hashlib
import config
import os  # FIXED: Added missing import

# Add conditional imports for text extraction libraries
try:
    import PyPDF2
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_EXTRACTION_AVAILABLE = False
    print("⚠️ PyPDF2 not available - PDF text extraction disabled")

try:
    from docx import Document as DocxDocument
    DOCX_EXTRACTION_AVAILABLE = True
except ImportError:
    DOCX_EXTRACTION_AVAILABLE = False
    print("⚠️ python-docx not available - DOCX text extraction disabled")


class DriveIngestionService:
    """Service to sync Google Drive files to database"""

    def __init__(self, drive_client: GoogleDriveClient, db: Session):
        self.drive_client = drive_client
        self.db = db
        self.tagger = SimpleTagger()
        self._current_user_email = None
        
        # Create temp_downloads directory if it doesn't exist
        temp_dir = 'temp_downloads'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            print(f"✅ Created directory: {temp_dir}")

    def sync_all_files(self) -> Dict:
        """
        Sync all files from Google Drive to database
        ✅ Each user's files stored with their email
        ✅ ALWAYS creates tags for all files
        """
        print("🔄 Starting full sync from Google Drive (ALWAYS CREATE TAGS)...")

        # ✅ GET CURRENT USER EMAIL ONCE AT START
        current_user_email = None
        try:
            about = self.drive_client.service.about().get(fields='user').execute()
            current_user_email = about['user']['emailAddress']
            self._current_user_email = current_user_email
            print(f"📧 Syncing for user: {current_user_email}")
        except Exception as e:
            print(f"⚠️ Could not get user: {e}")

        stats = {
            "total_files": 0,
            "new_files": 0,
            "updated_files": 0,
            "tags_created": 0,  # NEW: Count of files that got tags
            "errors": 0,
            "skipped": 0
        }

        try:
            page_token = None

            while True:
                results = self.drive_client.list_files(page_size=100, page_token=page_token)
                files = results.get('files', [])

                if not files:
                    break

                stats["total_files"] += len(files)

                for file in files:
                    try:
                        # ✅ PASS EMAIL TO PROCESS FILE - ALWAYS CREATES TAGS
                        result = self._process_file(file, current_user_email)
                        
                        if result == "new":
                            stats["new_files"] += 1
                            stats["tags_created"] += 1
                        elif result == "updated_tags":
                            stats["updated_files"] += 1
                            stats["tags_created"] += 1
                        elif result == "skipped":
                            stats["skipped"] += 1
                    except Exception as e:
                        print(f"❌ Error processing file: {e}")
                        stats["errors"] += 1

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            self._save_checkpoint(stats)
            print(f"🎉 Sync complete: {stats}")
            print(f"   📊 Tags created for {stats['tags_created']}/{stats['total_files']} files")
            return stats

        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            print(traceback.format_exc())
            return stats

    def _process_file(self, file_data: Dict, account_email: str = None) -> str:
        """
        Process a single file - ALWAYS CREATE TAGS, even for unchanged files
        """
        drive_file_id = file_data.get('id')
        file_name = file_data.get('name', 'Unknown')
        
        print(f"📄 Processing file: {file_name}")
        
        # Get modified time from Google Drive (but we'll ignore it for tagging)
        modified_time_str = file_data.get('modifiedTime')
        drive_modified_at = None
        
        if modified_time_str:
            try:
                modified_time_str = modified_time_str.replace('Z', '+00:00')
                drive_modified_at = datetime.fromisoformat(modified_time_str)
                
                if drive_modified_at.tzinfo is None:
                    drive_modified_at = drive_modified_at.replace(tzinfo=timezone.utc)
                
                drive_modified_at = drive_modified_at.replace(microsecond=0)
                
            except Exception as e:
                print(f"⚠️ Could not parse time for {file_name}: {e}")
                drive_modified_at = datetime.now(timezone.utc)
    
        try:
            # Check if file exists in database
            existing_doc = self.db.query(Document).filter(
                Document.drive_file_id == drive_file_id
            ).first()
            
            if existing_doc:
                print(f"🔄 Updating existing document: {file_name}")
                
                # Check if file was modified (only for metadata update)
                db_modified_at = existing_doc.modified_at
                
                if db_modified_at and db_modified_at.tzinfo is None:
                    db_modified_at = db_modified_at.replace(tzinfo=timezone.utc)
                
                if db_modified_at:
                    db_modified_at = db_modified_at.replace(microsecond=0)
                
                # Update metadata if file was modified
                if drive_modified_at and db_modified_at and drive_modified_at > db_modified_at:
                    print(f"📝 File modified, updating metadata: {file_name}")
                    file_metadata = self._extract_metadata(file_data, account_email)
                    
                    for key, value in file_metadata.items():
                        setattr(existing_doc, key, value)
                    
                    existing_doc.db_updated_at = datetime.utcnow()
                    self.db.commit()
                
                # ⭐⭐⭐ ALWAYS CREATE TAGS - EVEN IF FILE UNCHANGED ⭐⭐⭐
                print(f"🏷️  Creating content-based tags for: {file_name}")
                self._create_simple_tags(drive_file_id, file_data)
                
                # Queue processing tasks if file was modified or never processed
                if not existing_doc.last_indexed_at or (drive_modified_at and existing_doc.modified_at and drive_modified_at > existing_doc.modified_at):
                    self._queue_processing_tasks(drive_file_id)
                
                return "updated_tags"
                
            else:
                # New file
                print(f"✅ Adding new document: {file_name}")
                file_metadata = self._extract_metadata(file_data, account_email)
                
                new_doc = Document(**file_metadata)
                self.db.add(new_doc)
                self.db.flush()  # Get the ID
                self.db.commit()
                
                # ⭐⭐⭐ CREATE TAGS FOR NEW FILE ⭐⭐⭐
                print(f"🏷️  Creating content-based tags for new file: {file_name}")
                self._create_simple_tags(drive_file_id, file_data)
                
                self._queue_processing_tasks(drive_file_id)
                
                print(f"✅ Added: {file_name} (User: {account_email})")
                return "new"
        
        except Exception as e:
            print(f"❌ Error processing '{file_name}': {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _create_simple_tags(self, document_id: str, file_data: Dict):
        """
        Create tags based on document CONTENT (not filename)
        ALWAYS creates tags, even if some files fail
        """
        # Get document from database
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            doc = self.db.query(Document).filter(Document.drive_file_id == document_id).first()
        if not doc:
            print(f"⚠️ Skipping tag creation; document not in DB: {document_id}")
            return
        
        file_name = file_data.get('name', '')
        
        print(f"🔍 Analyzing content for tags: {file_name}")
        
        # Try to get document text from extracted text file
        document_text = ""
        if hasattr(doc, 'derived_text_path') and doc.derived_text_path:
            try:
                with open(doc.derived_text_path, 'r', encoding='utf-8') as f:
                    document_text = f.read()
                print(f"📖 Found extracted text: {len(document_text)} characters")
            except Exception as e:
                print(f"⚠️ Could not read extracted text: {e}")
                document_text = ""
        
        # If no extracted text, try to extract from temp file
        if not document_text:
            temp_file_path = os.path.join('temp_downloads', f"{doc.id}.temp")
            if os.path.exists(temp_file_path):
                try:
                    # Simple text extraction with error handling
                    if doc.mime_type == 'application/pdf' and PDF_EXTRACTION_AVAILABLE:
                        with open(temp_file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            for page in pdf_reader.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    document_text += page_text + "\n"
                    
                    elif doc.mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                          'application/msword'] and DOCX_EXTRACTION_AVAILABLE:
                        docx = DocxDocument(temp_file_path)
                        for para in docx.paragraphs:
                            if para.text:
                                document_text += para.text + "\n"
                    
                    elif doc.mime_type == 'text/plain':
                        with open(temp_file_path, 'r', encoding='utf-8') as f:
                            document_text = f.read()
                    
                    print(f"📖 Extracted text directly: {len(document_text)} characters")
                except Exception as e:
                    print(f"⚠️ Could not extract text: {e}")
        
        # If still no text, use filename as content
        if not document_text or len(document_text) < 10:
            print(f"ℹ️  No text content found for: {file_name}, using filename")
            document_text = file_name
        
        # Generate tags from content
        try:
            from tagging import ContentBasedTagger
            content_tagger = ContentBasedTagger()
            tags_to_create = content_tagger.extract_tags_from_text(document_text)
            
            if not tags_to_create:
                print(f"ℹ️  No content-based tags found for: {file_name}")
                # Still try filename-based tags as fallback
                tags_to_create = []
                name_lower = file_name.lower()
                
                # Simple filename matching
                if "employment" in name_lower and "agreement" in name_lower:
                    tags_to_create.append("Employment Agreement")
                elif "offer" in name_lower and "letter" in name_lower:
                    tags_to_create.append("Offer Letter")
                elif "consultancy" in name_lower or "consulting" in name_lower:
                    tags_to_create.append("Consultancy Agreement")
                elif "nda" in name_lower or "non-disclosure" in name_lower:
                    tags_to_create.append("NDA")
                elif "termination" in name_lower:
                    tags_to_create.append("Termination Letter")
                elif "policy" in name_lower:
                    tags_to_create.append("HR Policy")
            
        except Exception as e:
            print(f"⚠️ Error in content tagger: {e}")
            tags_to_create = []
        
        if not tags_to_create:
            print(f"ℹ️  No tags created for: {file_name}")
            return
        
        print(f"🏷️  Creating content-based tags for {file_name}: {tags_to_create}")
        
        try:
            # Remove any existing tags first (clean slate)
            existing_tags = self.db.query(DocumentTag).filter(
                DocumentTag.document_id == doc.id
            ).all()
            for tag in existing_tags:
                self.db.delete(tag)
            
            tags_added = 0
            for tag_name in set(tags_to_create):
                # Find tag in master taxonomy
                tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    # Try without category prefix
                    if ": " in tag_name:
                        simple_name = tag_name.split(": ")[1]
                        tag = self.db.query(Tag).filter(Tag.name == simple_name).first()
                
                if tag:
                    doc_tag = DocumentTag(
                        document_id=doc.id,
                        tag_id=tag.id,
                        confidence_score=1.0,
                        source='content_analysis',
                        created_at=datetime.utcnow()
                    )
                    self.db.add(doc_tag)
                    tags_added += 1
                    print(f"   ✅ Added tag: {tag_name}")
                else:
                    print(f"   ⏭️ Skipping: {tag_name} (not in master list)")
            
            if tags_added > 0:
                self.db.commit()
                print(f"🎉 Added {tags_added} tags for: {file_name}")
            else:
                print(f"ℹ️  No valid tags found in master list for: {file_name}")
            
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error creating tags for {file_name}: {e}")
            import traceback
            print(traceback.format_exc())

    def _extract_metadata(self, file_data: Dict, account_email: str = None) -> Dict:
        """
        Extract metadata from Google Drive file data
        ✅ NEW: Include account_email to track which user this file belongs to
        """
        # Parse timestamps
        created_time = file_data.get('createdTime')
        modified_time = file_data.get('modifiedTime')

        def parse_iso_time(time_str):
            if not time_str:
                return None
            try:
                time_str = time_str.replace('Z', '+00:00')
                return datetime.fromisoformat(time_str)
            except Exception as e:
                print(f"⚠️ Could not parse time '{time_str}': {e}")
                return None

        created_at = parse_iso_time(created_time)
        modified_at = parse_iso_time(modified_time)

        # Extract owner info
        owners = file_data.get('owners', [])
        owner_email = owners[0].get('emailAddress') if owners else None
        owner_name = owners[0].get('displayName') if owners else None

        # Get file extension
        file_name = file_data.get('name', '')
        file_format = self._get_file_extension(file_name)

        # Create checksum
        checksum = hashlib.md5(
            f"{file_data.get('id')}{modified_time}".encode()
        ).hexdigest()

        metadata = {
            'id': file_data.get('id'),
            'drive_file_id': file_data.get('id'),
            'title': file_name,
            'mime_type': file_data.get('mimeType'),
            'file_format': file_format,
            'size_bytes': int(file_data.get('size', 0)) if file_data.get('size') else None,
            'owner_email': owner_email,
            'owner_name': owner_name,
            'file_url': file_data.get('webViewLink'),
            'thumbnail_link': file_data.get('thumbnailLink'),
            'icon_link': file_data.get('iconLink'),
            'created_at': created_at,
            'modified_at': modified_at,
            'status': 'active',
            # ✅ THIS IS THE KEY - Store which account this file belongs to
            'account_email': account_email,
            'account_id': None,
            'checksum': checksum,
            'db_created_at': datetime.utcnow(),
            'db_updated_at': datetime.utcnow()
        }

        return metadata

    def _get_file_extension(self, filename: str) -> Optional[str]:
        """Extract file extension"""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return None

    def _queue_processing_tasks(self, document_id: str):
        """
        Queue processing tasks for a document
        Creates 3 tasks per document:
        1. Extract text
        2. AI tagging
        3. Create embeddings
        """
        tasks = [
            TaskType.EXTRACT_TEXT,
            TaskType.AI_TAGGING,
            TaskType.CREATE_EMBEDDING
        ]

        for task_type in tasks:
            # Check if task already exists
            existing_task = self.db.query(ProcessingQueue).filter(
                ProcessingQueue.document_id == document_id,
                ProcessingQueue.task_type == task_type,
                ProcessingQueue.status.in_([ProcessingStatus.PENDING, ProcessingStatus.PROCESSING])
            ).first()

            if not existing_task:
                new_task = ProcessingQueue(
                    document_id=document_id,
                    task_type=task_type,
                    status=ProcessingStatus.PENDING,
                    priority=5 if task_type == TaskType.EXTRACT_TEXT else 7,
                    retry_count=0,
                    max_retries=3
                )
                self.db.add(new_task)

        self.db.commit()

    def _save_checkpoint(self, stats: Dict):
        """
        Save sync checkpoint
        Records when sync happened, how many files, any errors
        """
        checkpoint = SyncCheckpoint(
            source='google_drive',
            last_sync_time=datetime.utcnow(),
            files_processed=stats.get('total_files', 0),
            files_failed=stats.get('errors', 0),
            status='completed' if stats['errors'] == 0 else 'completed_with_errors'
        )
        self.db.add(checkpoint)
        self.db.commit()

    def get_last_sync_info(self) -> Optional[Dict]:
        """Get information about last sync"""
        last_checkpoint = self.db.query(SyncCheckpoint).filter(
            SyncCheckpoint.source == 'google_drive'
        ).order_by(SyncCheckpoint.created_at.desc()).first()

        if last_checkpoint:
            return {
                'last_sync_time': last_checkpoint.last_sync_time.isoformat(),
                'files_processed': last_checkpoint.files_processed,
                'files_failed': last_checkpoint.files_failed,
                'status': last_checkpoint.status
            }
        return None

    def get_sync_stats(self) -> Dict:
        """Get overall sync statistics"""
        total_docs = self.db.query(Document).count()
        pending_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.PENDING
        ).count()

        processing_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.PROCESSING
        ).count()

        failed_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.FAILED
        ).count()

        return {
            'total_documents': total_docs,
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'failed_tasks': failed_tasks,
            'last_sync': self.get_last_sync_info()
        }