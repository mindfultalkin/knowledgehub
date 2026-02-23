# backend/risk_analysis_api.py - Dedicated Risk Analysis API Router
"""
Separate router for temporary risk analysis features.
Keeps main api.py clean and modular.
Works with your existing class-based service architecture.
"""

from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import tempfile
import os
from pathlib import Path
from pydantic import BaseModel

from database import get_db

# Import your existing class-based services
from services.universal_content_extractor import UniversalContentExtractor
from services.clause_extractor import ClauseExtractor
from services.risk_scoring import score_contract

# Create router
router = APIRouter(prefix="/risk-analysis", tags=["Risk Analysis"])



# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class QuickAnalysisResponse(BaseModel):
    success: bool
    filename: str
    clauses_count: int
    risk_score: int
    risk_level: str
    good_clauses: List[str]
    caution_clauses: List[str]
    missing_clauses: List[str]
    clauses: List[dict]


class ClauseDetail(BaseModel):
    clause_number: int
    section_number: str
    title: str
    content: str
    risk_level: str
    risk_score: int
    risk_factors: List[str]
    recommendations: List[str]


# ============================================================================
# HELPER FUNCTION TO EXTRACT TEXT FROM FILE
# ============================================================================

def extract_text_from_file(file_path: str, filename: str) -> str:
    """
    Extract text from uploaded file (PDF or DOCX).
    Works WITHOUT Drive API - processes local files directly.
    """
    file_ext = Path(filename).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            # Extract from PDF
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PyPDF2 not installed. Run: pip install PyPDF2"
                )
        
        elif file_ext in ['.docx', '.doc']:
            # Extract from DOCX
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="python-docx not installed. Run: pip install python-docx"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text: {str(e)}"
        )


def extract_clauses_from_text_simple(text: str) -> list:
    """
    Simple clause extraction without needing Drive API.
    Looks for common clause patterns in contracts.
    """
    clauses = []
    
    # Split by common clause indicators
    lines = text.split('\n')
    current_clause = None
    current_content = []
    clause_number = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if line looks like a clause heading
        # Pattern: "1. Title" or "Article 1: Title" or "Section 1 - Title"
        if any([
            line.startswith(f"{i}.") or 
            line.startswith(f"{i})") or
            f"Article {i}" in line or
            f"Section {i}" in line or
            f"Clause {i}" in line
            for i in range(1, 50)
        ]):
            # Save previous clause
            if current_clause:
                clauses.append({
                    'clause_number': clause_number,
                    'section_number': str(clause_number),
                    'title': current_clause,
                    'content': ' '.join(current_content)
                })
                clause_number += 1
            
            # Start new clause
            current_clause = line
            current_content = []
        else:
            # Add to current clause content
            if current_clause:
                current_content.append(line)
    
    # Don't forget the last clause
    if current_clause:
        clauses.append({
            'clause_number': clause_number,
            'section_number': str(clause_number),
            'title': current_clause,
            'content': ' '.join(current_content)
        })
    
    # If no clauses found using patterns, split into paragraphs
    if not clauses:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs[:20], 1):  # Max 20 paragraphs
            # Use first sentence or first 50 chars as title
            first_sentence = para.split('.')[0][:50]
            clauses.append({
                'clause_number': i,
                'section_number': str(i),
                'title': first_sentence,
                'content': para
            })
    
    return clauses


# ============================================================================
# MAIN ANALYSIS ENDPOINT
# ============================================================================

@router.post("/quick-analysis")
async def quick_risk_analysis(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    One-step risk analysis: upload + extract + analyze.
    Perfect for the Risk Score page - NO DATABASE STORAGE.
    
    Returns:
    - Overall risk score (0-100)
    - Risk level (LOW/MEDIUM/HIGH)
    - Protected clauses
    - Risk areas
    - Missing critical clauses
    - Per-clause analysis
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(allowed_extensions)}"
            )
        
        print(f"📄 Processing file: {file.filename}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Step 1: Extract text
            print(f"🔍 Extracting text from {file.filename}...")
            text = extract_text_from_file(temp_path, file.filename)
            
            if not text or len(text.strip()) < 50:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract sufficient text from document. Please ensure the document contains readable text."
                )
            
            print(f"✅ Extracted {len(text)} characters")
            
            # Step 2: Extract clauses
            print(f"📋 Extracting clauses...")
            clauses = extract_clauses_from_text_simple(text)
            
            if not clauses or len(clauses) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Could not identify clauses in document. Please ensure the document is a contract with clear clause structure."
                )
            
            print(f"✅ Found {len(clauses)} clauses")
            
            # Step 3: Calculate risk score
            print(f"⚖️ Calculating risk score...")
            risk_analysis = score_contract(clauses)
            
            print(f"✅ Risk Analysis Complete:")
            print(f"   - Overall Score: {risk_analysis['risk_score']}/100")
            print(f"   - Risk Level: {risk_analysis['risk_level']}")
            print(f"   - Protected Clauses: {len(risk_analysis['good_clauses'])}")
            print(f"   - Risk Areas: {len(risk_analysis['caution_clauses'])}")
            print(f"   - Missing Clauses: {len(risk_analysis['missing_clauses'])}")
            
            return {
                "success": True,
                "filename": file.filename,
                "clauses_count": len(clauses),
                "risk_score": risk_analysis['risk_score'],
                "risk_level": risk_analysis['risk_level'],
                "good_clauses": risk_analysis['good_clauses'],
                "caution_clauses": risk_analysis['caution_clauses'],
                "missing_clauses": risk_analysis['missing_clauses'],
                "clauses": risk_analysis['clauses']
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"🗑️ Cleaned up temp file")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in quick risk analysis: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze document: {str(e)}"
        )


# ============================================================================
# DETAILED CLAUSE ANALYSIS
# ============================================================================

@router.post("/detailed-clause-analysis")
async def detailed_clause_analysis(
    clause_data: dict,
    db: Session = Depends(get_db)
):
    """
    Get detailed analysis for a specific clause including:
    - Risk factors
    - Specific recommendations
    - Industry best practices
    - Alternative language suggestions
    """
    try:
        clause_title = clause_data.get('title', '')
        clause_content = clause_data.get('content', '')
        
        if not clause_title or not clause_content:
            raise HTTPException(
                status_code=400,
                detail="Clause title and content are required"
            )
        
        # Analyze the clause
        risk_factors = []
        recommendations = []
        
        # Check for problematic language
        problematic_terms = [
            'at-will', 'immediate termination', 'without cause', 
            'sole discretion', 'unlimited liability', 'no limitation'
        ]
        
        content_lower = clause_content.lower()
        
        for term in problematic_terms:
            if term in content_lower:
                risk_factors.append(f"Contains potentially problematic term: '{term}'")
        
        # Generate recommendations based on clause type
        if 'termination' in clause_title.lower():
            if 'notice' not in content_lower:
                risk_factors.append("No notice period specified")
                recommendations.append("Add a minimum notice period (e.g., 30 days)")
            
            if 'cause' not in content_lower:
                risk_factors.append("No 'for cause' termination clause")
                recommendations.append("Specify grounds for termination with and without cause")
        
        if 'liability' in clause_title.lower() or 'indemnification' in clause_title.lower():
            if 'cap' not in content_lower and 'limit' not in content_lower:
                risk_factors.append("No liability cap specified")
                recommendations.append("Consider adding a liability cap to limit exposure")
        
        if 'confidentiality' in clause_title.lower():
            if 'duration' not in content_lower and 'term' not in content_lower:
                risk_factors.append("No confidentiality duration specified")
                recommendations.append("Specify how long confidentiality obligations last")
        
        # If no risk factors found, it's a good clause
        if not risk_factors:
            risk_factors.append("No significant risk factors identified")
            recommendations.append("Clause appears to be well-drafted")
        
        return {
            "success": True,
            "clause_title": clause_title,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "risk_level": "HIGH" if len(risk_factors) > 3 else "MEDIUM" if len(risk_factors) > 1 else "LOW"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in detailed clause analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPARISON ENDPOINT (For comparing multiple contracts)
# ============================================================================

@router.post("/compare-contracts")
async def compare_contracts(
    analysis_results: List[dict],
    db: Session = Depends(get_db)
):
    """
    Compare multiple contract risk analyses side-by-side.
    Used when user uploads multiple documents for comparison.
    
    Returns:
    - Side-by-side comparison
    - Best/worst performers
    - Common issues
    - Unique risks per contract
    """
    try:
        if not analysis_results or len(analysis_results) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 contracts required for comparison"
            )
        
        # Sort by risk score
        sorted_contracts = sorted(
            analysis_results,
            key=lambda x: x.get('risk_score', 0),
            reverse=True
        )
        
        # Find best and worst
        best_contract = sorted_contracts[0]
        worst_contract = sorted_contracts[-1]
        
        # Find common issues
        all_missing = set()
        for result in analysis_results:
            all_missing.update(result.get('missing_clauses', []))
        
        common_missing = []
        for clause in all_missing:
            count = sum(1 for r in analysis_results if clause in r.get('missing_clauses', []))
            if count == len(analysis_results):
                common_missing.append(clause)
        
        return {
            "success": True,
            "total_contracts": len(analysis_results),
            "best_contract": {
                "name": best_contract.get('filename'),
                "score": best_contract.get('risk_score')
            },
            "worst_contract": {
                "name": worst_contract.get('filename'),
                "score": worst_contract.get('risk_score')
            },
            "common_missing_clauses": common_missing,
            "comparison_data": sorted_contracts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error comparing contracts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Check if risk analysis service is available"""
    return {
        "status": "healthy",
        "service": "Risk Analysis API",
        "version": "2.0.0",
        "features": [
            "Quick Analysis",
            "Detailed Clause Analysis",
            "Contract Comparison",
            "No Database Storage",
            "Standalone Processing"
        ]
    }