from typing import Any, Dict, Optional
from datetime import datetime

def format_response(
    success: bool = True,
    data: Any = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    status_code: int = 200
) -> Dict:
    """Format API responses consistently"""
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data or {}
    }
    
    if message:
        response["message"] = message
    
    if error:
        response["error"] = error
    
    return response