"""
Initialize database - create all tables
Run this once to set up the database schema
"""
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.database import init_database, test_connection, engine
from app.config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER

def main():
    print("="*60)
    print("KNOWLEDGE HUB - DATABASE INITIALIZATION")
    print("="*60)
    print(f"\nDatabase: {MYSQL_DATABASE}")
    print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"User: {MYSQL_USER}\n")
    
    # Test connection
    print("🔄 Testing database connection...")
    if not test_connection():
        print("\n❌ Cannot connect to database!")
        print("Please check your MySQL configuration in .env file")
        return
    
    # Initialize database
    print("\n🔄 Creating database tables...")
    try:
        init_database()
        print("\n✅ Database initialized successfully!")
        
        # Print created tables
        print("\n📋 Created tables:")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        for table_name in inspector.get_table_names():
            print(f"   ✓ {table_name}")
        
        print("\n🎉 Database setup complete!")
        print("\nNext steps:")
        print("1. Run your FastAPI backend: python main.py")
        print("2. Test the connection: curl http://localhost:8000/api/health")
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()