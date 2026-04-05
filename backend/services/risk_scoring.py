# backend/services/risk_scoring.py
"""
Risk Scoring Service + Router
- Contains scoring logic (score_clause, score_contract)
- Exposes FastAPI router with:
    GET  /contracts/{file_id}/risk-score   → DB-backed risk score (from stored clauses)
    POST /risk-analysis/quick-analysis     → Upload + analyze without DB storage
"""

from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
import tempfile
import os
from pathlib import Path

from database import get_db
from models.clauses import DocumentClause

router = APIRouter(tags=["Risk Scoring"])


# ============================================================================
# SCORING CONFIG
# ============================================================================

REQUIRED_CLAUSES = [
    "indemnification",
    "governing law",
    "dispute resolution",
    "confidentiality",
    "force majeure",
    "termination",
    "payment terms",
    "intellectual property",
]

RISK_KEYWORDS = {
    "termination": ["at-will", "immediate", "without notice", "sole discretion"],
    "governing law": ["laws of", "jurisdiction", "venue"],
    "confidentiality": ["disclose", "confidential information", "non-disclosure"],
    "indemnification": ["hold harmless", "indemnify", "liability"],
    "payment terms": ["overdue", "penalty", "interest", "late fee"],
    "dispute resolution": ["arbitration", "mediation", "litigation"],
    "force majeure": ["act of god", "unforeseeable", "beyond control"],
    "intellectual property": ["ownership", "assignment", "work for hire"],
}


# ============================================================================
# CORE SCORING LOGIC  (reusable — imported by other services if needed)
# ============================================================================

def score_clause(clause: dict) -> dict:
    """
    Score a single clause dict.
    Expects keys: clause_number, section_number, title, content
    Returns the same dict plus: risk_level, risk_score
    """
    title = (clause.get("title") or "").lower()
    content = (clause.get("content") or "").lower()

    risk_level = "Low"
    score = 90

    if not content or len(content.strip()) < 18:
        risk_level, score = "High", 40
    elif "termination" in title and "immediate" in content:
        risk_level, score = "Medium", 65
    elif any(kw in content for kw in RISK_KEYWORDS.get(title, [])):
        risk_level, score = "High", 50

    return {
        "id": clause.get("clause_number"),          # frontend ClauseItem expects `id`
        "clause_number": clause.get("clause_number"),
        "section_number": clause.get("section_number"),
        "title": clause.get("title"),
        "content": clause.get("content"),
        "risk_level": risk_level,                   # "Low" | "Medium" | "High"
        "risk_score": score,
    }


def score_contract(clauses: List[dict]) -> dict:
    """
    Score a full contract (list of clause dicts).
    Returns summary: risk_score, risk_level, good/caution/missing clauses, per-clause results.
    """
    if not clauses:
        return {
            "risk_score": 0,
            "risk_level": "HIGH",
            "good_clauses": [],
            "caution_clauses": [],
            "missing_clauses": REQUIRED_CLAUSES,
            "clauses": [],
            "clauses_count": 0,
        }

    results = [score_clause(c) for c in clauses]

    found_titles = {(c.get("title") or "").lower() for c in clauses}
    missing = [req for req in REQUIRED_CLAUSES if req not in found_titles]

    good = [c["title"] for c in results if c["risk_level"] == "Low"]
    caution = [c["title"] for c in results if c["risk_level"] in ("Medium", "High")]

    contract_score = round(sum(c["risk_score"] for c in results) / len(results))

    if contract_score <= 55:
        level = "HIGH"
    elif contract_score <= 75:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_score": contract_score,
        "risk_level": level,           # "LOW" | "MEDIUM" | "HIGH"  (matches frontend)
        "good_clauses": good,
        "caution_clauses": caution,
        "missing_clauses": missing,
        "clauses": results,
        "clauses_count": len(results),
    }


# ============================================================================
# HELPER — extract text from uploaded file (no Drive API needed)
# ============================================================================

def _extract_text(file_path: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise HTTPException(status_code=500, detail="PyPDF2 not installed. Run: pip install PyPDF2")

    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


def _extract_clauses_simple(text: str) -> List[dict]:
    """
    Lightweight clause extractor — no external service needed.
    Falls back to paragraph splitting if no numbered clauses found.
    """
    clauses = []
    lines = text.split("\n")
    current_title = None
    current_content: List[str] = []
    clause_number = 1

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect numbered headings: "1.", "1)", "Article 1", "Section 1", "Clause 1"
        is_heading = any(
            line.startswith(f"{i}.") or
            line.startswith(f"{i})") or
            line.lower().startswith(f"article {i}") or
            line.lower().startswith(f"section {i}") or
            line.lower().startswith(f"clause {i}")
            for i in range(1, 50)
        )

        if is_heading:
            if current_title:
                clauses.append({
                    "clause_number": clause_number,
                    "section_number": str(clause_number),
                    "title": current_title,
                    "content": " ".join(current_content),
                })
                clause_number += 1
            current_title = line
            current_content = []
        elif current_title:
            current_content.append(line)

    # Flush last clause
    if current_title:
        clauses.append({
            "clause_number": clause_number,
            "section_number": str(clause_number),
            "title": current_title,
            "content": " ".join(current_content),
        })

    # Fallback: split into paragraphs
    if not clauses:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs[:20], 1):
            clauses.append({
                "clause_number": i,
                "section_number": str(i),
                "title": para.split(".")[0][:60],
                "content": para,
            })

    return clauses


# ============================================================================
# ROUTE 1 — DB-backed risk score (from already-stored clauses)
# Migrated from old api.py → GET /contracts/{file_id}/risk-score
# ============================================================================

@router.get("/contracts/{file_id}/risk-score")
async def get_contract_risk_score(
    file_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns contract-level risk summary + per-clause risk for a document
    that has already been ingested and has clauses stored in the DB.

    Path param: file_id — can be the internal Document.id OR the Drive file ID.
    """
    try:
        # Try by internal id first, then by drive_file_id
        clauses = db.query(DocumentClause).filter(
            DocumentClause.document_id == file_id
        ).all()

        if not clauses:
            # Fallback: look up via drive_file_id join
            from models.metadata import Document
            doc = db.query(Document).filter(Document.drive_file_id == file_id).first()
            if doc:
                clauses = db.query(DocumentClause).filter(
                    DocumentClause.document_id == doc.id
                ).all()

        if not clauses:
            raise HTTPException(
                status_code=404,
                detail=f"No clauses found for document '{file_id}'. "
                       "Make sure the document has been ingested and clause extraction has run.",
            )

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

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Risk scoring error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROUTE 2 — Upload + analyze without DB storage
# POST /risk-analysis/quick-analysis
# (keeps risk_analysis_api.py working — mount this router there OR in main app)
# ============================================================================

@router.post("/risk-analysis/quick-analysis")
async def quick_risk_analysis(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    One-step upload → extract → score.
    No database storage — results are returned directly.
    Accepts PDF or DOCX.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .docx, .doc",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        print(f"📄 Quick analysis: {file.filename}")

        text = _extract_text(tmp_path, file.filename)
        if not text or len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract sufficient text. Ensure the document contains readable text.",
            )

        clauses = _extract_clauses_simple(text)
        if not clauses:
            raise HTTPException(
                status_code=400,
                detail="Could not identify clauses. Ensure the document has a clear clause structure.",
            )

        result = score_contract(clauses)
        result["success"] = True
        result["filename"] = file.filename
        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Quick analysis error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/risk-analysis/health")
async def health():
    return {
        "status": "healthy",
        "service": "Risk Scoring",
        "required_clauses": REQUIRED_CLAUSES,
    }