"""
Main API router combining all controllers
"""
from fastapi import APIRouter
from app.controllers import (
    auth_router,
    clause_router,
    document_router,
    risk_router,
    search_router,
    sync_router,
    tag_router
)

# Create main router
router = APIRouter()

# Include all routers
router.include_router(auth_router)
router.include_router(clause_router)
router.include_router(document_router)
router.include_router(risk_router)
router.include_router(search_router)
router.include_router(sync_router)
router.include_router(tag_router)

print("✅ Combined all controllers into main API router")