import os
import pickle
import re
import string

import faiss
import nltk
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer



# Make sure NLTK data is available
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


class NLPSearchEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Lightweight semantic search engine for Knowledge Hub.

        - Uses SentenceTransformer embeddings
        - Stores document list + embeddings in memory
        - Uses FAISS for fast similarity search
        """
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []          # list of dicts from DocumentProcessor.prepare_documents_for_nlp
        self.document_embeddings = None
        self.is_trained = False

    # ==================== TEXT PREPROCESSING ====================

    def preprocess_text(self, text: str) -> str:
        """Basic cleaning before embeddings."""
        if not text:
            return ""
        text = text.lower()
        text = " ".join(text.split())
        return text

    def extract_text_from_content(self, content: str, max_length: int = 1000) -> str:
        """
        Extract meaningful text from content (optimized for legal docs).
        Keeps lines containing legal keywords and headers.
        """
        if not content:
            return ""

        lines = content.split("\n")
        meaningful_lines = []

        legal_keywords = [
            "agreement", "contract", "clause", "party", "term", "condition",
            "obligation", "right", "responsibility", "payment", "termination",
            "lease", "rental", "nda", "non-disclosure", "confidential"
        ]

        for line in lines:
            line = line.strip()
            if len(line) <= 20:
                continue

            lower = line.lower()

            if any(k in lower for k in legal_keywords):
                meaningful_lines.append(line)

            # keep section headings
            if (
                line.isupper()
                or line.endswith(":")
                or (len(line) < 120 and any(c.isupper() for c in line))
            ):
                meaningful_lines.append(line)

        result = " ".join(meaningful_lines[:50])
        return result[:max_length]

    # ==================== TRAINING / INDEXING ====================

    def create_embeddings(self, documents):
        """
        Create embeddings for all documents.

        `documents` is a list of dicts from DocumentProcessor.prepare_documents_for_nlp,
        each with at least: id, name, content, mimeType, owner, modifiedTime, webViewLink, size.
        """
        self.documents = documents or []

        texts = []
        for doc in self.documents:
            filename = doc.get("name", "")
            content = self.extract_text_from_content(doc.get("content", ""))

            search_text = f"{filename} {content}"
            processed = self.preprocess_text(search_text)
            texts.append(processed)

        if not texts:
            self.index = None
            self.document_embeddings = None
            self.is_trained = False
            return None

        print(f"Creating embeddings for {len(texts)} documents...")

        embs = self.model.encode(texts, convert_to_tensor=False)
        self.document_embeddings = np.asarray(embs, dtype="float32")

        dim = self.document_embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)

        faiss.normalize_L2(self.document_embeddings)
        self.index.add(self.document_embeddings)

        self.is_trained = True
        print("✅ NLP search engine trained successfully!")
        return self.index

    # ==================== SEARCH ====================

    def search(self, query: str, top_k: int = 10, min_score: float = 0.3):
        """
        Semantic search over all indexed documents.

        - Returns only results above `min_score`
        - Each result: { document: <doc_dict>, score: float, relevance: str }
        """
        if not self.is_trained or self.index is None or not self.documents:
            return []

        processed_query = self.preprocess_text(query or "")
        if not processed_query:
            return []

        query_emb = self.model.encode([processed_query], convert_to_tensor=False)
        query_emb = np.asarray(query_emb, dtype="float32")
        faiss.normalize_L2(query_emb)

        k = min(top_k * 3, len(self.documents))
        scores, indices = self.index.search(query_emb, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= len(self.documents):
                continue
            if score < min_score:
                continue

            doc = self.documents[idx]
            results.append(
                {
                    "document": doc,
                    "score": float(score),
                    "relevance": self._get_relevance_label(float(score)),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _get_relevance_label(self, score: float) -> str:
        """Convert similarity score to human-friendly label."""
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

    # ==================== PERSISTENCE ====================

    def save_model(self, filepath: str):
        """Persist documents, embeddings and FAISS index."""
        if not self.is_trained or self.index is None:
            return

        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "documents": self.documents,
                    "embeddings": self.document_embeddings,
                    "index": self.index,
                },
                f,
            )
        print(f"✅ Model saved to {filepath}")

    def load_model(self, filepath: str):
        """Load previously trained model from disk."""
        if not os.path.exists(filepath):
            return

        with open(filepath, "rb") as f:
            data = pickle.load(f)

        self.documents = data.get("documents", [])
        self.document_embeddings = data.get("embeddings")
        self.index = data.get("index")
        self.is_trained = self.index is not None and self.document_embeddings is not None

        print(f"✅ Model loaded from {filepath}")
