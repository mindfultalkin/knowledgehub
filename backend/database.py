"""
Database configuration - Works with Railway's variable names
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import time
import os
import logging
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway uses MYSQLHOST, MYSQLPORT etc (no underscore)
# Local dev uses MYSQL_HOST, MYSQL_PORT etc (with underscore)
# Support both!
def get_env(key_with_underscore, key_without_underscore, default=""):
    """Get environment variable supporting both Railway and local naming"""
    return os.getenv(key_with_underscore) or os.getenv(key_without_underscore) or default

MYSQL_HOST = get_env("MYSQL_HOST", "MYSQLHOST", "localhost")
MYSQL_PORT = int(get_env("MYSQL_PORT", "MYSQLPORT", "3306"))
MYSQL_USER = get_env("MYSQL_USER", "MYSQLUSER", "root")
MYSQL_PASSWORD = get_env("MYSQL_PASSWORD", "MYSQLPASSWORD", "")
MYSQL_DATABASE = get_env("MYSQL_DATABASE", "MYSQLDATABASE", "railway")

# URL-encode password
MYSQL_PASSWORD_ENCODED = quote_plus(MYSQL_PASSWORD) if MYSQL_PASSWORD else ""

# Build connection URL
if MYSQL_PASSWORD_ENCODED:
    MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
else:
    MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

logger.info(f"🔧 Database Configuration:")
logger.info(f"   Host: {MYSQL_HOST}")
logger.info(f"   Port: {MYSQL_PORT}")
logger.info(f"   Database: {MYSQL_DATABASE}")
logger.info(f"   User: {MYSQL_USER}")


def create_engine_with_retry():
    """Create database engine with retry logic"""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                MYSQL_DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=5,
                max_overflow=10,
                echo=False,
                connect_args={
                    "connect_timeout": 10,
                    "charset": "utf8mb4"
                }
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("✅ Database connection successful!")
                return engine
                
        except Exception as e:
            logger.error(f"❌ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("💥 All connection attempts failed")
                raise

# Initialize engine
engine = None
SessionLocal = None

try:
    engine = create_engine_with_retry()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("✅ Database engine created")
except Exception as e:
    logger.error(f"💥 Failed to create database engine: {e}")
    engine = None
    SessionLocal = None

Base = declarative_base()


def get_db():
    """FastAPI dependency for database sessions"""
    if not SessionLocal or not engine:
        logger.error("❌ Database not initialized")
        raise Exception("Database not available")
    
    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


@contextmanager
def get_db_context():
    """Context manager for database operations"""
    if not SessionLocal:
        raise Exception("Database not available")
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Transaction error: {e}")
        raise
    finally:
        db.close()


def init_database():
    """Initialize database tables"""
    if not engine:
        logger.error("❌ Cannot initialize database")
        return False
    
    try:
        logger.info("🔄 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created!")
        return True
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        return False


def test_connection():
    """Test database connection"""
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Database test passed!")
            return True
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False
