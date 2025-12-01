# backend/services/risk_scoring.py

REQUIRED_CLAUSES = [
    "indemnification", "governing law", "dispute resolution", "confidentiality", "force majeure", "termination", "payment terms", "intellectual property"
]

RISK_KEYWORDS = {
    "termination": ["at-will", "immediate", "without notice", "sole discretion"],
    "governing law": ["laws of", "jurisdiction", "venue"],
    "confidentiality": ["disclose", "confidential information", "non-disclosure"],
    "indemnification": ["hold harmless", "indemnify", "liability"],
    # Add more clause keyword lists as needed...
}

def score_clause(clause):
    title = (clause.get("title") or "").lower()
    content = (clause.get("content") or "").lower()
    risk_level = "Low"
    score = 90

    if not content or len(content) < 18:
        risk_level, score = "High", 40
    elif "termination" in title and "immediate" in content:
        risk_level, score = "Medium", 65
    elif any(k in content for k in RISK_KEYWORDS.get(title, [])):
        risk_level, score = "High", 50

    return {
        "clause_number": clause.get("clause_number"),
        "section_number": clause.get("section_number"),
        "title": clause.get("title"),
        "content": clause.get("content"),
        "risk_level": risk_level,
        "risk_score": score
    }

def score_contract(clauses):
    results = [score_clause(clause) for clause in clauses]
    found_titles = {c["title"].lower() for c in clauses}
    missing = [c for c in REQUIRED_CLAUSES if c not in found_titles]
    good = [c["title"] for c in results if c["risk_level"] == "Low"]
    caution = [c["title"] for c in results if c["risk_level"] in ("Medium", "High")]
    contract_score = round(sum([c["risk_score"] for c in results]) / len(results)) if results else 0
    level = (
        "High Risk" if contract_score <= 55 else
        "Medium Risk" if contract_score <= 75 else
        "Low Risk"
    )
    return {
            "risk_score": contract_score,
            "risk_level": level.upper().replace(" RISK", ""),  # "Low", "Medium", "High" -> "LOW", "MEDIUM", "HIGH"
            "good_clauses": good,
            "caution_clauses": caution,
            "missing_clauses": missing,
            "clauses": results
        }
