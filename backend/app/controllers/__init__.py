"""
Controllers for Knowledge Hub API
"""

from .auth_controller import router as auth_router
from .clause_controller import router as clause_router
from .document_controller import router as document_router
from .risk_controller import router as risk_router
from .search_controller import router as search_router
from .sync_controller import router as sync_router
from .tag_controller import router as tag_router

__all__ = [
    'auth_router',
    'clause_router',
    'document_router',
    'risk_router',
    'search_router',
    'sync_router',
    'tag_router'
]