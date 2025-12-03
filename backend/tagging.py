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
    
    # Common business/content tags - EXPANDED
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
        'data': ['data', 'analytics', 'statistics', 'metrics'],
        'contract': ['contract', 'agreement', 'terms'],
        'legal': ['legal', 'law', 'clause', 'provision'],
        'template': ['template', 'form', 'sample'],
        'draft': ['draft', 'version', 'revision'],
        'final': ['final', 'approved', 'signed'],
        'rental': ['rental', 'lease', 'rent'],
        'employment': ['employment', 'employee', 'job'],
        'invoice': ['invoice', 'bill', 'payment'],
        'receipt': ['receipt', 'proof', 'transaction'],
        'proposal': ['proposal', 'bid', 'offer'],
        'memo': ['memo', 'note', 'notice'],
        'policy': ['policy', 'procedure', 'guideline'],
        'manual': ['manual', 'guide', 'handbook'],
        'training': ['training', 'course', 'workshop'],
        'certificate': ['certificate', 'certification', 'diploma'],
        'license': ['license', 'permit', 'authorization']
    }
        # Master tagging rules mapped from filename patterns (from your Excel)
    TAG_RULES = [
        # Document Types
        {
            "match": ["employment_agreement", "employment-agreement", "employment agreement"],
            "tags": ["Employment Agreement", "Document Type: Employment Agreement"],
        },
        {
            "match": ["offer_letter", "offer-letter", "offer letter"],
            "tags": ["Offer Letter", "Document Type: Offer Letter"],
        },
        {
            "match": ["consultancy_agreement", "consulting_agreement", "consulting-services-agreement"],
            "tags": ["Consultancy Agreement", "Document Type: Consultancy Agreement"],
        },
        {
            "match": ["nda", "non_disclosure", "non-disclosure", "non disclosure"],
            "tags": ["NDA", "Document Type: NDA"],
        },
        {
            "match": ["termination_letter", "termination-letter", "termination letter"],
            "tags": ["Termination Letter", "Document Type: Termination Letter"],
        },

        # Lifecycle Stage
        {
            "match": ["pre-hire", "pre_hire", "prehire", "pre hire"],
            "tags": ["Lifecycle: Pre-Hire"],
        },
        {
            "match": ["onboarding"],
            "tags": ["Lifecycle: Onboarding"],
        },
        {
            "match": ["probation"],
            "tags": ["Lifecycle: Probation"],
        },
        {
            "match": ["post-termination", "post_termination", "post termination"],
            "tags": ["Lifecycle: Post-Termination"],
        },

        # Clauses
        {
            "match": ["confidentiality"],
            "tags": ["Clause: Confidentiality"],
        },
        {
            "match": ["non_compete", "non-compete", "non compete"],
            "tags": ["Clause: Non-Compete"],
        },
        {
            "match": ["ip_assignment", "ip-assignment", "ip assignment"],
            "tags": ["Clause: IP Assignment"],
        },
        {
            "match": ["arbitration"],
            "tags": ["Clause: Arbitration"],
        },
        {
            "match": ["data_protection", "data-protection", "data protection"],
            "tags": ["Clause: Data Protection"],
        },

        # Jurisdiction
        {
            "match": ["india", "_in_", "-in-", "_india_", "-india-"],
            "tags": ["Jurisdiction: India"],
        },
        {
            "match": ["_us_", "-us-", "usa", "united_states"],
            "tags": ["Jurisdiction: US"],
        },
        {
            "match": ["_uk_", "-uk-", "united_kingdom"],
            "tags": ["Jurisdiction: UK"],
        },
        {
            "match": ["cross_border", "cross-border", "cross border"],
            "tags": ["Jurisdiction: Cross-Border"],
        },

        # Employee Type
        {
            "match": ["permanent_employee", "permanent-employee", "permanent employee"],
            "tags": ["Employee Type: Permanent Employee"],
        },
        {
            "match": ["consultant"],
            "tags": ["Employee Type: Consultant"],
        },
        {
            "match": ["intern"],
            "tags": ["Employee Type: Intern"],
        },
        {
            "match": ["senior_management", "senior-management", "senior management"],
            "tags": ["Employee Type: Senior Management"],
        },

        # Risk Level
        {
            "match": ["high_risk", "high-risk", "high risk"],
            "tags": ["Risk: High"],
        },
        {
            "match": ["medium_risk", "medium-risk", "medium risk"],
            "tags": ["Risk: Medium"],
        },
        {
            "match": ["low_risk", "low-risk", "low risk"],
            "tags": ["Risk: Low"],
        },
    ]




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
        """
        Generate curated tags for a file from controlled rules.
        No raw word-split tags.
        """
        tags = set()
        name = (file_name or "").lower()

        # 1. Apply master TAG_RULES
        for rule in self.TAG_RULES:
            if any(pattern in name for pattern in rule["match"]):
                for t in rule["tags"]:
                    tags.add(t)

        # 2. Optional: high-level content tags from CONTENT_KEYWORDS (coarse)
        #    Use only if you still want 'contract', 'template', etc.
        for tag, keywords in self.CONTENT_KEYWORDS.items():
            if any(keyword in name for keyword in keywords):
                tags.add(tag)

        # 3. File type tag (document, image, etc.)
        if mime_type:
            file_type = self.detect_file_type(mime_type)
            tags.add(file_type)

        # 4. (Optional) description-based rules – currently reused same patterns
        if description:
            desc = description.lower()
            for rule in self.TAG_RULES:
                if any(pattern in desc for pattern in rule["match"]):
                    for t in rule["tags"]:
                        tags.add(t)

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
   