import io
import os
import PyPDF2
from docx import Document
from typing import Optional

class FileProcessor:
    """Utility for processing different file types"""
    
    @staticmethod
    def extract_text_from_google_doc(drive_service, file_id: str, file_name: str) -> str:
        """Extract text from Google Doc"""
        try:
            request = drive_service.service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            file_handle = io.BytesIO()
            downloader = drive_service.MediaIoBaseDownload(file_handle, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            text = file_handle.getvalue().decode('utf-8')
            return text
            
        except Exception as e:
            print(f"❌ Error processing Google Doc {file_name}: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_pdf(file_content: bytes, file_name: str) -> str:
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
            else:
                print(f"📄 No text found normally")
            
        except Exception as e:
            print(f"❌ PDF processing error: {e}")
        
        return text
    
    @staticmethod
    def extract_text_from_docx(file_content: bytes, file_name: str) -> str:
        """Extract text from DOCX files"""
        try:
            doc_file = io.BytesIO(file_content)
            doc = Document(doc_file)
            text = ""
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            return text
            
        except Exception as e:
            print(f"❌ Error reading DOCX: {e}")
            return ""
    
    @staticmethod
    def create_content_from_filename(file_name: str) -> str:
        """Create meaningful content from filename"""
        name_without_ext = os.path.splitext(file_name)[0]
        
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
        
        filename_lower = file_name.lower()
        for pattern, keywords in patterns.items():
            if pattern in filename_lower:
                content += f"This contains {keywords}. "
        
        return content