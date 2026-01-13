"""
Knowledge Hub Backend Application
"""

from .config import (
    MYSQL_DATABASE_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URIS,
    SCOPES,
    FRONTEND_URL,
    SERVICE_API_BASE_URL,
    ALLOWED_ORIGINS,
    DERIVED_TEXT_DIR,
    DERIVED_THUMBNAIL_DIR
)

from .database import (
    Base,
    engine,
    SessionLocal,
    get_db,
    get_db_context,
    init_database,
    test_connection
)

__all__ = [
    'MYSQL_DATABASE_URL',
    'GOOGLE_CLIENT_ID',
    'GOOGLE_CLIENT_SECRET',
    'GOOGLE_REDIRECT_URIS',
    'SCOPES',
    'FRONTEND_URL',
    'SERVICE_API_BASE_URL',
    'ALLOWED_ORIGINS',
    'DERIVED_TEXT_DIR',
    'DERIVED_THUMBNAIL_DIR',
    'Base',
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_context',
    'init_database',
    'test_connection'
]