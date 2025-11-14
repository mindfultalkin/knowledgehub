"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import time
import os
from urllib.parse import quote_plus

# Get database configuration directly from environment variables
# (Railway provides these automatically)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "railway")

# URL-encode the password to handle special characters
MYSQL_PASSWORD_ENCODED = quote_plus(MYSQL_PASSWORD)

# Construct database URL
MYSQL_DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

print(f"🔧 Database Configuration:")
print(f"   Host: {MYSQL_HOST}")
print(f"   Port: {MYSQL_PORT}")
print(f"   Database: {MYSQL_DATABASE}")
print(f"   User: {MYSQL_USER}")

def create_engine_with_retry():
    """
    Create database engine with retry logic for Railway
    """
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                MYSQL_DATABASE_URL,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,  # Set to True for debugging
                connect_args={"connect_timeout": 30}
            )
            
            # Test connection
            with engine.connect() as conn:
                print("✅ Database connection successful!")
                return engine
                
        except Exception as e:
            print(f"❌ Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("💥 All database connection attempts failed")
                raise

# Create SQLAlchemy engine with retry logic
try:
    engine = create_engine_with_retry()
except Exception as e:
    print(f"💥 Critical: Could not connect to database: {e}")
    # Create a null engine to prevent immediate crash
    engine = None

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Create Base class for models
Base = declarative_base()

def get_db():
    """
    FastAPI dependency for database sessions
    """
    if not SessionLocal:
        raise Exception("Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    """
    if not SessionLocal:
        raise Exception("Database not available")
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    """
    Initialize database - create all tables
    """
    if not engine:
        print("❌ Cannot initialize database - no engine available")
        return False
    
    try:
        print("🔄 Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def test_connection():
    """
    Test database connection
    """
    if not engine:
        return False
        
    try:
        with engine.connect() as connection:
            print("✅ Database connection test successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False