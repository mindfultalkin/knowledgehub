"""
Clause Extraction Service
Extracts clause sections from documents
"""
import re
from typing import List, Dict


class ClauseExtractor:
    """
    Extract clauses/sections from legal documents
    """
    
    def extract_clauses_from_content(self, content: str) -> List[Dict]:
        """
        Main method: Extract all clauses from document content
        Returns list of clauses with titles and content
        """
        try:
            print(f"📄 Parsing document content ({len(content)} characters)")
            
            if not content:
                print("❌ No content to parse")
                return []
            
            # Parse document structure and find clauses
            clauses = self._parse_document_structure(content)
            
            print(f"✅ Found {len(clauses)} clauses")
            return clauses
            
        except Exception as e:
            print(f"❌ Error extracting clauses: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def _parse_document_structure(self, content: str) -> List[Dict]:
        """
        Parse document and identify clause sections
        """
        clauses = []
        lines = content.split('\n')
        
        current_clause = None
        clause_content = []
        clause_number = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped:
                continue
            
            # Check if this line is a section header
            is_header, section_num, title = self._is_section_header(line_stripped)
            
            if is_header:
                # Save previous clause
                if current_clause and clause_content:
                    current_clause['content'] = '\n'.join(clause_content).strip()
                    if current_clause['content']:  # Only add if has content
                        clauses.append(current_clause)
                
                # Start new clause
                clause_number += 1
                
                # Clean title - remove any sentence fragments
                # If title has a period followed by text, take only up to period
                if '. ' in title:
                    title = title.split('. ')[0]
                
                current_clause = {
                    'clause_number': clause_number,
                    'section_number': section_num or str(clause_number),
                    'title': title.strip(),
                    'content': '',
                    'start_line': i
                }
                clause_content = []
            else:
                # Add to current clause content
                if current_clause:
                    clause_content.append(line_stripped)
        
        # Save last clause
        if current_clause and clause_content:
            current_clause['content'] = '\n'.join(clause_content).strip()
            if current_clause['content']:
                clauses.append(current_clause)
        
        return clauses

    
    def _is_section_header(self, line: str) -> tuple:
        """
        Determine if a line is a section header
        Returns: (is_header, section_number, title)
        """
        # Skip if line is too long (likely not a header)
        if len(line) > 100:
            return (False, '', '')
        
        # Pattern 1: "1. Title" or "1.1 Title" (followed by period and space)
        match = re.match(r'^(\d+(?:\.\d+)*)\.\s+([A-Z][^\n]{0,80})$', line.strip())
        if match:
            section_num = match.group(1)
            title = match.group(2).strip()
            # Remove trailing punctuation except period
            title = re.sub(r'[,;:]$', '', title)
            return (True, section_num, title)
        
        # Pattern 2: "§1 Title" or "Section 1: Title"
        match = re.match(r'^(?:§|Section)\s*(\d+)\s*[:\-]?\s*([A-Z][^\n]{0,80})$', line.strip(), re.IGNORECASE)
        if match:
            section_num = match.group(1)
            title = match.group(2).strip()
            title = re.sub(r'[,;:]$', '', title)
            return (True, section_num, title)
        
        # Pattern 3: "ARTICLE I" or "ARTICLE 1"
        match = re.match(r'^ARTICLE\s+([IVX\d]+)\s*[:\-]?\s*([A-Z][^\n]{0,80})?$', line.strip(), re.IGNORECASE)
        if match:
            section_num = match.group(1)
            title = match.group(2).strip() if match.group(2) else "Article"
            return (True, section_num, title)
        
        # Pattern 4: ALL CAPS header (10-80 characters, ends with period or nothing)
        if line.isupper() and 10 <= len(line) <= 80:
            # Check if it's likely a header (not a full sentence)
            if not line.startswith(('SCHEDULE', 'EXHIBIT', 'APPENDIX', 'WHEREAS', 'NOW THEREFORE')):
                # If it ends with a period, it's the full header
                if line.endswith('.'):
                    return (True, '', line[:-1])  # Remove trailing period
                # If no period but all caps and reasonable length
                elif '.' not in line or line.count('.') == 1:
                    return (True, '', line)
        
        return (False, '', '')
