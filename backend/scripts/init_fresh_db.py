#!/usr/bin/env python3
"""
Fresh Database Initialization Script
Creates a clean database schema from scratch
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlmodel import SQLModel, create_engine, Session
from app.models.sql_models import Brand, ProductFamily, Product, Document, Media, IngestLog
from app.core.config import settings

def init_fresh_database():
    """Initialize a completely fresh database"""
    
    print("=" * 80)
    print("INITIALIZING FRESH DATABASE")
    print("=" * 80)
    
    # Create engine
    db_path = Path("support_center.db")
    if db_path.exists():
        print(f"⚠️  Database already exists: {db_path}")
        response = input("Delete and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return False
        db_path.unlink()
        print("🗑️  Deleted existing database")
    
    print(f"\n📦 Creating new database: {db_path}")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Create all tables
    print("📋 Creating tables...")
    SQLModel.metadata.create_all(engine)
    
    # Verify tables were created
    with Session(engine) as session:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
    
    print(f"\n" + "=" * 80)
    print("✅ FRESH DATABASE READY")
    print("=" * 80)
    print(f"\nDatabase: {db_path.absolute()}")
    print(f"Status: Empty and ready for ingestion")
    
    return True

if __name__ == "__main__":
    success = init_fresh_database()
    sys.exit(0 if success else 1)
