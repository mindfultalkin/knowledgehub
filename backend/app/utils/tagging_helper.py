from typing import List
import re

class TaggingHelper:
    """Helper utilities for tagging"""
    
    @staticmethod
    def get_content_preview(content: str, query: str, preview_length: int = 200) -> str:
        """Get content preview for search results"""
        if not content or not query:
            return content[:preview_length] + '...' if len(content) > preview_length else content
        
        content_lower = content.lower()
        query_words = [word.lower() for word in query.split() if len(word) > 2]
        
        for word in query_words:
            position = content_lower.find(word)
            if position != -1:
                start = max(0, position - 50)
                end = min(len(content), position + 150)
                return f"...{content[start:end]}..."
        
        return content[:preview_length] + '...' if len(content) > preview_length else content
    
    @staticmethod
    def clean_query(query: str) -> List[str]:
        """Clean search query"""
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        words = [word.strip() for word in clean_query.split() if word.strip()]
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [word for word in words if word not in common_words and len(word) > 2]