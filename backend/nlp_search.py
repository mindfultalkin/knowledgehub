import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string
import pickle
import os
from config import INDEX_PATH, EMBEDDINGS_PATH
import re

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class NLPSearchEngine:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.document_embeddings = None
        self.is_trained = False
        
    def preprocess_text(self, text):
        """Clean and preprocess text for better embeddings"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def extract_text_from_content(self, content, max_length=1000):
        """Extract meaningful text from content (for legal documents)"""
        if not content:
            return ""
            
        # For legal documents, we want to keep important sections
        lines = content.split('\n')
        meaningful_lines = []
        
        legal_keywords = ['agreement', 'contract', 'clause', 'party', 'term', 'condition', 
                         'obligation', 'right', 'responsibility', 'payment', 'termination']
        
        for line in lines:
            line = line.strip()
            if len(line) > 20:  # Skip very short lines
                # Check if line contains legal content
                if any(keyword in line.lower() for keyword in legal_keywords):
                    meaningful_lines.append(line)
                
                # Also include section headers
                if line.isupper() or line.endswith(':') or (len(line) < 100 and any(c.isupper() for c in line)):
                    meaningful_lines.append(line)
        
        # Combine and limit length
        result = ' '.join(meaningful_lines[:50])  # Take first 50 meaningful lines
        return result[:max_length]
    
    def create_embeddings(self, documents):
        """Create embeddings for all documents"""
        self.documents = documents
        
        # Prepare texts for embedding
        texts = []
        for doc in documents:
            # Combine filename and content for better search
            filename = doc.get('name', '')
            content = self.extract_text_from_content(doc.get('content', ''))
            
            # Create searchable text
            search_text = f"{filename} {content}"
            processed_text = self.preprocess_text(search_text)
            texts.append(processed_text)
        
        print(f"Creating embeddings for {len(texts)} documents...")
        
        # Create embeddings
        self.document_embeddings = self.model.encode(texts, convert_to_tensor=False)
        
        # Create FAISS index for fast similarity search
        dimension = self.document_embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(self.document_embeddings)
        self.index.add(self.document_embeddings)
        
        self.is_trained = True
        print("✅ NLP search engine trained successfully!")
        
        return self.index
    
    def search(self, query, top_k=10, min_score=0.3):
        """Search for similar documents - ONLY HIGH RELEVANCE"""
        if not self.is_trained or self.index is None:
            return []
        
        # Preprocess query
        processed_query = self.preprocess_text(query)
        
        # Create query embedding
        query_embedding = self.model.encode([processed_query], convert_to_tensor=False)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, min(top_k * 3, len(self.documents)))  # Get more results to filter
        
        # Prepare results - ONLY HIGH SCORE RESULTS
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents) and score >= min_score:  # Only include high relevance
                results.append({
                    'document': self.documents[idx],
                    'score': float(score),
                    'relevance': self._get_relevance_label(score)
                })
        
        # Sort by score descending and take top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _get_relevance_label(self, score):
        """Convert similarity score to relevance label - STRICTER THRESHOLDS"""
        if score > 0.7:
            return "Very High"
        elif score > 0.5:
            return "High" 
        elif score > 0.3:
            return "Medium"
        else:
            return "Low"  # Will be filtered out by min_score

    def _get_relevance_label(self, score):
        """Convert similarity score to relevance label - STRICTER THRESHOLDS"""
        if score > 0.7:
            return "Very High"
        elif score > 0.5:
            return "High" 
        elif score > 0.3:
            return "Medium"
        else:
            return "Low"  # Will be filtered out by min_score
    
    def _get_relevance_label(self, score):
        """Convert similarity score to relevance label"""
        if score > 0.8:
            return "Very High"
        elif score > 0.6:
            return "High"
        elif score > 0.4:
            return "Medium"
        elif score > 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def save_model(self, filepath):
        """Save the trained model and index"""
        if self.is_trained:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'embeddings': self.document_embeddings,
                    'index': self.index
                }, f)
            print(f"✅ Model saved to {filepath}")
    
    def load_model(self, filepath):
        """Load a trained model and index"""
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.document_embeddings = data['embeddings']
                self.index = data['index']
                self.is_trained = True
            print(f"✅ Model loaded from {filepath}")