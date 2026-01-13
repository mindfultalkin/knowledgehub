"""
Risk scoring controllers
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Import models and services
from database import get_db
from app.models.clause import DocumentClause
from app.services.risk_scoring_service import score_contract

router = APIRouter()

@router.get("/contracts/{file_id}/risk-score")
async def risk_score(file_id: str, db: Session = Depends(get_db)):
    """
    Returns contract-level risk summary, per-clause risk, and missing clause checklist.
    """
    try:
        # Fetch all clauses for this document
        clauses = db.query(DocumentClause).filter(DocumentClause.document_id == file_id).all()
        clause_list = [
            {
                "clause_number": c.clause_number,
                "section_number": c.section_number,
                "title": c.clause_title,
                "content": c.clause_content,
            }
            for c in clauses
        ]
        return score_contract(clause_list)
    except Exception as e:
        print(f"❌ Risk scoring error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))