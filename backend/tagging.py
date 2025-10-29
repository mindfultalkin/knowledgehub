import re
from collections import Counter

class SimpleTagger:
    """Simple keyword-based tagging system (no AI API required)"""
    
    # Predefined categories and keywords
    CATEGORIES = {
        'document': {
            'keywords': ['doc', 'pdf', 'text', 'document', 'report', 'presentation', 'sheet', 'slide'],
            'mimetypes': ['application/pdf', 'application/msword', 
                         'application/vnd.openxmlformats', 'text/']
        },
        'image': {
            'keywords': ['image', 'photo', 'picture', 'screenshot', 'graphic', 'design'],
            'mimetypes': ['image/']
        },
        'video': {
            'keywords': ['video', 'movie', 'recording', 'clip', 'film'],
            'mimetypes': ['video/']
        },
        'audio': {
            'keywords': ['audio', 'music', 'sound', 'song', 'podcast'],
            'mimetypes': ['audio/']
        },
        'code': {
            'keywords': ['code', 'script', 'program', 'source', 'java', 'python', 'js'],
            'mimetypes': ['text/x-']
        },
        'archive': {
            'keywords': ['zip', 'archive', 'compressed', 'backup'],
            'mimetypes': ['application/zip', 'application/x-']
        }
    }
    
    # Common business/content tags
    CONTENT_KEYWORDS = {
        'business': ['business', 'company', 'enterprise', 'corporate'],
        'meeting': ['meeting', 'conference', 'discussion', 'standup'],
        'report': ['report', 'analysis', 'summary', 'findings'],
        'presentation': ['presentation', 'slides', 'deck', 'pitch'],
        'project': ['project', 'plan', 'roadmap', 'timeline'],
        'research': ['research', 'study', 'investigation', 'survey'],
        'design': ['design', 'mockup', 'wireframe', 'prototype'],
        'development': ['dev', 'development', 'coding', 'programming'],
        'marketing': ['marketing', 'campaign', 'promotion', 'advertising'],
        'financial': ['financial', 'budget', 'revenue', 'cost'],
        'personal': ['personal', 'private', 'individual'],
        'team': ['team', 'group', 'collaborative', 'shared'],
        'quarterly': ['q1', 'q2', 'q3', 'q4', 'quarterly', 'quarter'],
        'annual': ['annual', 'yearly', 'year'],
        'strategy': ['strategy', 'strategic', 'planning'],
        'data': ['data', 'analytics', 'statistics', 'metrics']
    }
    
    def extract_tags_from_filename(self, filename):
        """Extract meaningful tags from filename"""
        # Remove file extension
        name = re.sub(r'\.[^.]*$', '', filename)
        
        # Split by common separators
        words = re.split(r'[_\-\s\.]+', name.lower())
        
        # Filter and clean words
        tags = []
        for word in words:
            # Remove numbers and special characters
            clean_word = re.sub(r'[^a-z]', '', word)
            
            # Keep words that are 3+ characters
            if len(clean_word) >= 3:
                tags.append(clean_word)
        
        return tags
    
    def detect_file_type(self, mime_type):
        """Detect file type from MIME type"""
        if not mime_type:
            return 'file'
            
        for category, data in self.CATEGORIES.items():
            for mime_pattern in data['mimetypes']:
                if mime_type.startswith(mime_pattern):
                    return category
        return 'file'
    
    def generate_content_tags(self, filename):
        """Generate content-based tags"""
        tags = []
        filename_lower = filename.lower()
        
        for tag, keywords in self.CONTENT_KEYWORDS.items():
            if any(keyword in filename_lower for keyword in keywords):
                tags.append(tag)
        
        return tags
    
    def generate_tags(self, file_name, mime_type=None, description=None):
        """Generate all tags for a file"""
        tags = set()
        
        # 1. Tags from filename
        filename_tags = self.extract_tags_from_filename(file_name)
        tags.update(filename_tags[:5])  # Limit to 5 filename tags
        
        # 2. File type tag
        if mime_type:
            file_type = self.detect_file_type(mime_type)
            tags.add(file_type)
        
        # 3. Content-based tags
        content_tags = self.generate_content_tags(file_name)
        tags.update(content_tags)
        
        # 4. Tags from description if available
        if description:
            desc_tags = self.extract_tags_from_filename(description)
            tags.update(desc_tags[:3])
        
        return list(tags)
    
    def get_confidence_score(self, tag, file_name, mime_type=None):
        """Calculate confidence score for a tag"""
        score = 0.5  # Base score
        
        # Higher score if tag is in filename
        if tag.lower() in file_name.lower():
            score += 0.3
        
        # Higher score if matches category
        if mime_type:
            file_type = self.detect_file_type(mime_type)
            if tag == file_type:
                score += 0.2
        
        return min(score, 1.0)
