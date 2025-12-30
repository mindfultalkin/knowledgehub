"""
Content-Based Tagging System for Law Documents
Uses master taxonomy to tag documents based on ACTUAL CONTENT
"""
import re
from typing import List, Dict
from collections import Counter


class ContentBasedTagger:
    """Tag documents based on actual content analysis using master taxonomy"""
    
    # Master tag taxonomy from your Excel sheet
    MASTER_TAXONOMY = {
        # Document Types
        "Document Type": {
            "Employment Agreement": [
                "employment agreement", "employment contract", "employee agreement",
                "terms of employment", "job agreement", "work contract",
                "salary", "wages", "compensation", "benefits", "allowances",
                "working hours", "overtime", "leave", "vacation", "holidays",
                "probation", "probationary period", "confirmation", "appointment",
                "employer", "employee", "full-time", "part-time", "permanent"
            ],
            "Offer Letter": [
                "offer letter", "letter of offer", "appointment letter",
                "joining letter", "offer of employment", "job offer",
                "position", "designation", "start date", "reporting to",
                "compensation package", "joining bonus", "relocation"
            ],
            "Consultancy Agreement": [
                "consultancy agreement", "consulting agreement", "consultant agreement",
                "consulting services", "independent contractor", "freelance agreement",
                "scope of work", "deliverables", "consulting fee", "payment terms",
                "contractor", "consultant", "freelancer", "service provider"
            ],
            "NDA": [
                "non-disclosure agreement", "nda", "confidentiality agreement",
                "confidential disclosure", "proprietary information", "trade secret",
                "disclose", "recipient", "discloser", "confidentiality obligation",
                "non-disclosure", "confidentiality clause"
            ],
            "Termination Letter": [
                "termination letter", "dismissal letter", "termination notice",
                "separation letter", "exit letter", "notice of termination",
                "last working day", "severance", "notice pay", "final settlement",
                "resignation acceptance", "employment termination"
            ],
            "HR Policy": [
                "hr policy", "human resources policy", "personnel policy",
                "company policy", "workplace policy", "employee policy",
                "code of conduct", "dress code", "attendance policy",
                "leave policy", "travel policy", "expense policy"
            ],
            "Practice Note": [
                "practice note", "legal note", "guidance note", "internal memo",
                "legal opinion", "best practices", "checklist", "style guide",
                "manual", "procedure", "guideline", "advisory"
            ]
        },
        
        # Lifecycle Stage
        "Lifecycle Stage": {
            "Pre-Hire": [
                "pre-hire", "recruitment", "hiring process", "interview",
                "background check", "reference check", "offer stage",
                "pre-employment", "screening", "selection process"
            ],
            "Onboarding": [
                "onboarding", "induction", "orientation", "joining process",
                "employee onboarding", "new hire", "first day", "welcome kit",
                "orientation program", "company introduction"
            ],
            "Probation": [
                "probation", "probationary", "trial period", "probation period",
                "performance review", "probation assessment", "confirmation",
                "probation completion", "probation extension"
            ],
            "Termination": [
                "termination", "dismissal", "resignation", "separation",
                "exit process", "exit interview", "handover", "termination procedure",
                "employment termination", "service termination"
            ],
            "Post-Termination": [
                "post-termination", "after termination", "post-employment",
                "severance pay", "experience certificate", "relieving letter",
                "full and final settlement", "exit formalities", "garden leave"
            ]
        },
        
        # Clauses
        "Clause": {
            "Confidentiality": [
                "confidentiality", "non-disclosure", "confidential information",
                "trade secret", "proprietary information", "protected information",
                "disclosure restriction", "information protection"
            ],
            "Non-Compete": [
                "non-compete", "non-competition", "restrictive covenant",
                "competition restriction", "post-employment restriction",
                "competitive business", "restraint of trade"
            ],
            "IP Assignment": [
                "intellectual property", "ip assignment", "copyright",
                "patent", "trademark", "invention", "work product",
                "assignment of rights", "ownership", "ip rights"
            ],
            "Arbitration": [
                "arbitration", "arbitral", "dispute resolution", "arbitrator",
                "arbitral tribunal", "arbitral award", "conciliation", "mediation"
            ],
            "Data Protection": [
                "data protection", "data privacy", "personal data", "privacy",
                "gdpr", "data security", "sensitive information", "data breach",
                "consent", "data processing"
            ]
        },
        
        # Jurisdiction
        "Jurisdiction": {
            "India": [
                "india", "indian", "delhi", "mumbai", "bangalore", "chennai",
                "kolkata", "hyderabad", "companies act", "income tax act",
                "gst", "epf", "esi", "posh act", "gratuity act"
            ],
            "US": [
                "united states", "usa", "us", "california", "new york", "texas",
                "federal", "state law", "irs", "sec", "dol", "eeoc"
            ],
            "UK": [
                "united kingdom", "uk", "england", "london", "wales", "scotland",
                "hmrc", "companies house", "employment tribunal", "acas"
            ],
            "Cross-Border": [
                "cross-border", "international", "multinational", "global",
                "foreign", "offshore", "multi-country", "jurisdictional",
                "conflict of laws", "choice of law"
            ]
        },
        
        # Employee Type
        "Employee Type": {
            "Permanent Employee": [
                "permanent employee", "regular employee", "full-time employee",
                "confirmed employee", "on rolls", "staff employee"
            ],
            "Consultant": [
                "consultant", "contractor", "freelancer", "independent contractor",
                "external consultant", "third-party consultant", "service provider"
            ],
            "Intern": [
                "intern", "internship", "trainee", "apprentice", "student intern",
                "summer intern", "training period", "stipend"
            ],
            "Senior Management": [
                "senior management", "director", "vice president", "cfo", "ceo",
                "board member", "executive", "leadership", "partner", "md"
            ]
        },
        
        # Risk Level
        "Risk Level": {
            "High Risk": [
                "high risk", "critical", "sensitive", "litigation",
                "dispute", "penalty", "fine", "legal action", "breach",
                "default", "liability", "indemnity"
            ],
            "Medium Risk": [
                "medium risk", "moderate risk", "standard", "routine",
                "compliance", "regulatory", "review required", "approval needed"
            ],
            "Low Risk": [
                "low risk", "routine", "administrative", "standard form",
                "template", "boilerplate", "simple", "basic agreement"
            ]
        },
        
        # Compliance
        "Compliance": {
            "POSH Act": [
                "posh", "sexual harassment", "prevention of sexual harassment",
                "workplace harassment", "internal committee", "ic",
                "complaint committee", "anti-harassment"
            ],
            "EPF Act": [
                "epf", "provident fund", "employee provident fund", "pf",
                "epfo", "pension", "retirement benefits", "provident fund act"
            ],
            "Gratuity Act": [
                "gratuity", "gratuity act", "payment of gratuity",
                "retirement benefit", "terminal benefit", "continuous service"
            ]
        },
        
        # Workflow Status
        "Workflow Status": {
            "Draft": [
                "draft", "working draft", "preliminary", "version",
                "in progress", "under review", "for comments", "review copy"
            ],
            "Approved": [
                "approved", "final approved", "authorized", "sanctioned",
                "cleared", "ratified", "endorsed", "signed off"
            ],
            "Signed": [
                "signed", "executed", "countersigned", "witnessed",
                "notarized", "stamped", "registered", "filed"
            ],
            "Expired": [
                "expired", "lapsed", "terminated", "completed",
                "ended", "superseded", "replaced", "archived"
            ]
        }
    }
    
    @staticmethod
    def extract_tags_from_text(text: str) -> List[str]:
        """
        Analyze text content and return matching tags from master taxonomy
        
        Args:
            text: Document text content
            
        Returns:
            List of tag names that match the content
        """
        if not text or len(text) < 10:  # Need minimum text
            return []
            
        text_lower = text.lower()
        tags_found = set()
        
        # Check each category and tag
        for category, tag_dict in ContentBasedTagger.MASTER_TAXONOMY.items():
            for tag_name, keywords in tag_dict.items():
                # Check if ANY keyword is in the text
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        # Format: "Category: Tag Name" (except for Document Type)
                        if category == "Document Type":
                            tags_found.add(tag_name)
                        else:
                            tags_found.add(f"{category}: {tag_name}")
                        break  # Found one keyword, move to next tag
        
        return list(tags_found)


class SimpleTagger:
    """Enhanced SimpleTagger with content-based tagging"""
    
    def __init__(self):
        self.content_tagger = ContentBasedTagger()
    
    def generate_tags(self, file_name, mime_type=None, description=None, document_text=None):
        """
        Generate tags STRICTLY from content analysis
        
        Returns:
            List of tag names that match the content (from master taxonomy ONLY)
        """
        if not document_text:
            # If no text, use filename as fallback
            document_text = file_name
        
        # Get tags from content analysis
        tags = self.content_tagger.extract_tags_from_text(document_text)
        
        # If no content tags, try filename analysis
        if not tags:
            tags = self._extract_tags_from_filename(file_name)
        
        return tags
    
    def _extract_tags_from_filename(self, filename: str) -> List[str]:
        """Extract tags from filename using master taxonomy keywords"""
        filename_lower = filename.lower()
        tags_found = set()
        
        # Check each category and tag in master taxonomy
        for category, tag_dict in ContentBasedTagger.MASTER_TAXONOMY.items():
            for tag_name, keywords in tag_dict.items():
                # Check if ANY keyword is in the filename
                for keyword in keywords:
                    if keyword.lower() in filename_lower:
                        # Format: "Category: Tag Name" (except for Document Type)
                        if category == "Document Type":
                            tags_found.add(tag_name)
                        else:
                            tags_found.add(f"{category}: {tag_name}")
                        break  # Found one keyword, move to next tag
        
        return list(tags_found)
    
    def detect_file_type(self, mime_type):
        """Simple file type detection"""
        if not mime_type:
            return 'file'
        
        if 'pdf' in mime_type:
            return 'pdf'
        elif 'word' in mime_type or 'document' in mime_type:
            return 'document'
        elif 'spreadsheet' in mime_type or 'excel' in mime_type:
            return 'spreadsheet'
        elif 'presentation' in mime_type or 'powerpoint' in mime_type:
            return 'presentation'
        elif 'image' in mime_type:
            return 'image'
        elif 'video' in mime_type:
            return 'video'
        elif 'audio' in mime_type:
            return 'audio'
        else:
            return 'file'  