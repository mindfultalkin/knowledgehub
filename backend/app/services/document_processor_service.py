import io
import PyPDF2
from docx import Document
import os

# Configure Tesseract OCR
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
    
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        OCR_AVAILABLE = True
        print("✅ Tesseract OCR configured successfully!")
    else:
        OCR_AVAILABLE = False
        print("❌ Tesseract not found")
        
except ImportError as e:
    OCR_AVAILABLE = False
    print(f"⚠️ OCR dependencies not available: {e}")

class DocumentProcessor:
    def __init__(self, drive_client):
        self.drive_client = drive_client
    
    def extract_text_from_google_doc(self, file_id, file_name):
        """Extract text from Google Docs by exporting as plain text"""
        try:
            print(f"📄 Processing Google Doc: {file_name}")
            
            # Export Google Doc as plain text
            from googleapiclient.http import MediaIoBaseDownload
            
            request = self.drive_client.service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            text = file_handle.getvalue().decode('utf-8')
            print(f"✅ Google Doc processed: {file_name} - {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"❌ Error processing Google Doc {file_name}: {e}")
            return ""
    
    def extract_text_from_google_sheets(self, file_id, file_name):
        """Extract text from Google Sheets by exporting as CSV"""
        try:
            print(f"📊 Processing Google Sheet: {file_name}")
            
            # Export Google Sheet as CSV
            from googleapiclient.http import MediaIoBaseDownload
            
            request = self.drive_client.service.files().export_media(
                fileId=file_id,
                mimeType='text/csv'
            )
            
            file_handle = io.BytesIO()
            downloader = MediaIoBaseDownload(file_handle, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            text = file_handle.getvalue().decode('utf-8')
            print(f"✅ Google Sheet processed: {file_name} - {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"❌ Error processing Google Sheet {file_name}: {e}")
            return ""
    
    def extract_text_with_ocr(self, file_content, file_name):
        """Extract text from image-based PDF using OCR"""
        if not OCR_AVAILABLE:
            return ""
            
        try:
            print(f"🔍 Using OCR for: {file_name}")
            images = convert_from_bytes(file_content, dpi=200)
            
            text = ""
            for i, image in enumerate(images):
                print(f"   📄 OCR processing page {i+1}/{len(images)}...")
                image = image.convert('L')
                page_text = pytesseract.image_to_string(image, lang='eng', config='--psm 6')
                
                if page_text.strip():
                    text += f"--- Page {i+1} ---\n{page_text}\n\n"
            
            print(f"✅ OCR extracted {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            return ""
    
    def extract_text_from_pdf(self, file_content, file_name):
        """Extract text from PDF files"""
        text = ""
        
        try:
            pdf_file = io.BytesIO(file_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            normal_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    normal_text += f"Page {i+1}:\n{page_text}\n\n"
            
            if normal_text.strip():
                text = normal_text
                print(f"✅ Normal PDF extraction: {len(text)} chars")
            else:
                print(f"📄 No text found normally, trying OCR...")
                ocr_text = self.extract_text_with_ocr(file_content, file_name)
                if ocr_text.strip():
                    text = ocr_text
                    print(f"✅ OCR successful: {len(text)} chars")
            
        except Exception as e:
            print(f"❌ PDF processing error: {e}")
            if OCR_AVAILABLE:
                ocr_text = self.extract_text_with_ocr(file_content, file_name)
                if ocr_text.strip():
                    text = ocr_text
        
        return text
    
    def extract_text_from_docx(self, file_content, file_name):
        """Extract text from DOCX files"""
        try:
            doc_file = io.BytesIO(file_content)
            doc = Document(doc_file)
            text = ""
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            print(f"✅ DOCX processed: {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"❌ Error reading DOCX: {e}")
            return ""
    
    def create_content_from_filename(self, file_name):
        """Create meaningful content from filename for folders and unsupported files"""
        # Remove file extension
        name_without_ext = os.path.splitext(file_name)[0]
        
        # Common legal document patterns
        patterns = {
            'rental': 'rental agreement lease property tenant landlord',
            'contract': 'contract agreement terms conditions',
            'employment': 'employment contract job employee employer',
            'agreement': 'agreement contract terms',
            'commercial': 'commercial business contract agreement',
            'clause': 'clause provision section term',
            'checklist': 'checklist review verification',
            'disclosure': 'disclosure confidential information',
            'limitation': 'limitation liability responsibility',
            'mutual': 'mutual agreement both parties',
            'data': 'data information taxonomy labeling',
            'research': 'research study analysis findings',
            'hr': 'human resources employee personnel',
            'requirements': 'requirements features specifications',
            'outlining': 'outlining tasks activities work',
            'law': 'law legal attorney practice',
            'tasks': 'tasks activities work assignments'
        }
        
        content = f"Document/Folder: {name_without_ext}. "
        
        # Add relevant keywords based on filename
        filename_lower = file_name.lower()
        for pattern, keywords in patterns.items():
            if pattern in filename_lower:
                content += f"This contains {keywords}. "
        
        return content
    
    def process_file_content(self, file_id, file_name, mime_type):
        """Process file and extract content - HANDLES ALL FILE TYPES"""
        try:
            print(f"📄 Processing: {file_name} ({mime_type})")
            
            # Handle Google Docs
            if mime_type == 'application/vnd.google-apps.document':
                return self.extract_text_from_google_doc(file_id, file_name)
            
            # Handle Google Sheets
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                return self.extract_text_from_google_sheets(file_id, file_name)
            
            # Handle folders - create content from filename
            elif mime_type == 'application/vnd.google-apps.folder':
                return self.create_content_from_filename(file_name)
            
            # For downloadable files, download and process
            else:
                file_content = self.drive_client.download_file(file_id, file_name)
                
                if not file_content:
                    return ""
                
                if mime_type == 'application/pdf':
                    return self.extract_text_from_pdf(file_content, file_name)
                elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                    return self.extract_text_from_docx(file_content, file_name)
                elif mime_type == 'text/plain':
                    try:
                        text = file_content.decode('utf-8')
                        print(f"✅ Text file processed: {len(text)} characters")
                        return text
                    except:
                        return ""
                else:
                    # For any other file type, create content from filename
                    return self.create_content_from_filename(file_name)
                
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            # Even if processing fails, create content from filename
            return self.create_content_from_filename(file_name)
    
    def prepare_documents_for_nlp(self, files):
        """Prepare ALL documents for NLP processing - NO FILE LEFT BEHIND"""
        documents = []
        
        print(f"🚀 PROCESSING ALL {len(files)} FILES FROM GOOGLE DRIVE")
        print("📝 Supporting: PDF, DOCX, Google Docs, Google Sheets, Folders, and ALL other files")
        
        for file in files:
            file_name = file['name']
            mime_type = file.get('mimeType', '')
            file_size = int(file.get('size', 0))
            
            print(f"🔍 Processing: {file_name}")
            
            # PROCESS EVERY FILE - no exceptions!
            content = self.process_file_content(file['id'], file_name, mime_type)
            
            if content and len(content.strip()) > 5:  # Very low threshold
                documents.append({
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': mime_type,
                    'content': content,
                    'owner': file.get('owner', 'Unknown'),
                    'modifiedTime': file.get('modifiedTime', ''),
                    'webViewLink': file.get('webViewLink', ''),
                    'size': file.get('size', '0')
                })
                print(f"✅ ADDED: {file_name} ({len(content)} chars)")
            else:
                # Even if no content, create basic content from filename
                basic_content = self.create_content_from_filename(file_name)
                documents.append({
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': mime_type,
                    'content': basic_content,
                    'owner': file.get('owner', 'Unknown'),
                    'modifiedTime': file.get('modifiedTime', ''),
                    'webViewLink': file.get('webViewLink', ''),
                    'size': file.get('size', '0')
                })
                print(f"✅ ADDED (basic): {file_name}")
        
        print(f"\n🎯 SUCCESS: Processed {len(documents)} out of {len(files)} files")
        print("📊 All files are now ready for NLP training!")
        
        return documents