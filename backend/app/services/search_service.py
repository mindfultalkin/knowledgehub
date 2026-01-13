# backend/app/services/search_service.py
import re
from typing import List, Dict


class SimpleTextSearch:
    def __init__(self, drive_client):
        self.drive_client = drive_client
        self.doc_processor = None  # Will be set from document_processor_service
        self.documents = []
        self.is_loaded = False
    
    def load_documents_from_drive(self):
        """Load documents directly from Google Drive for simple search"""
        try:
            if not self.drive_client.creds:
                print("❌ Simple search: Not authenticated with Google Drive")
                return False
            
            print("🔄 Simple search: Loading documents from Google Drive...")
            
            # Get files from Google Drive
            files_response = self.drive_client.list_files(page_size=100)
            files = files_response.get('files', [])
            
            # Process documents to extract content
            from .document_processor_service import DocumentProcessor
            if not self.doc_processor:
                self.doc_processor = DocumentProcessor(self.drive_client)
            
            self.documents = self.doc_processor.prepare_documents_for_nlp(files)
            self.is_loaded = True
            
            print(f"✅ Simple search: Loaded {len(self.documents)} documents")
            return True
            
        except Exception as e:
            print(f"❌ Simple search: Failed to load documents: {e}")
            return False
    
    def search_documents(self, query: str) -> List[Dict]:
        """Simple exact text search"""
        if not self.is_loaded:
            # Try to load documents if not loaded
            if not self.load_documents_from_drive():
                return []
        
        query_words = self._clean_query(query)
        
        if not query_words:
            return []
        
        print(f"🔍 SIMPLE SEARCH: '{query}' → Words: {query_words}")
        
        results = []
        for doc in self.documents:
            content = doc.get('content', '').lower()
            doc_name = doc.get('name', '').lower()
            search_text = f"{doc_name} {content}"
            
            # Check if ALL query words are found
            all_words_found = all(word in search_text for word in query_words)
            
            if all_words_found:
                match_count = sum(search_text.count(word) for word in query_words)
                results.append({
                    'document': doc,
                    'match_count': match_count
                })
                print(f"✅ SIMPLE FOUND: {doc['name']} ({match_count} matches)")
        
        # Sort by number of matches (most matches first)
        results.sort(key=lambda x: x['match_count'], reverse=True)
        
        print(f"🎯 Simple search found {len(results)} documents with exact content match")
        return results
    
    def _clean_query(self, query: str) -> List[str]:
        """Clean query words"""
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = [word.strip() for word in clean_query.split() if word.strip()]
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [word for word in words if word not in common_words and len(word) > 2]