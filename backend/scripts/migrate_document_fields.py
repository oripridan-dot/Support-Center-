#!/usr/bin/env python3
"""
Add missing fields to Document table

Adds:
- content (TEXT) - Full document text
- doc_type (VARCHAR) - Type of document
- file_path (VARCHAR) - Local file path
- created_at (DATETIME) - Creation timestamp
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


def migrate_document_table():
    print("🔧 Migrating Document table to add missing fields...")
    
    with engine.begin() as conn:
        # Check current schema
        result = conn.execute(text("PRAGMA table_info(document)"))
        columns = {row[1] for row in result.fetchall()}
        print(f"📊 Current columns: {columns}")
        
        # Add missing columns (SQLite requires constant defaults or NULL)
        to_add = []
        if 'content' not in columns:
            to_add.append(('content', 'TEXT'))
        if 'doc_type' not in columns:
            to_add.append(('doc_type', "VARCHAR"))
        if 'file_path' not in columns:
            to_add.append(('file_path', 'VARCHAR'))
        if 'created_at' not in columns:
            to_add.append(('created_at', 'DATETIME'))
        
        if not to_add:
            print("✅ All columns already exist!")
            return
        
        print(f"\n📝 Adding {len(to_add)} new columns:")
        for col_name, col_type in to_add:
            print(f"  + {col_name} ({col_type})")
            conn.execute(text(f"ALTER TABLE document ADD COLUMN {col_name} {col_type}"))
        
        # Set default values for existing rows
        if 'doc_type' in [col[0] for col in to_add]:
            print("  📝 Setting default doc_type values...")
            conn.execute(text("UPDATE document SET doc_type = 'manual' WHERE doc_type IS NULL"))
        
        if 'created_at' in [col[0] for col in to_add]:
            print("  📝 Setting default created_at values...")
            conn.execute(text("UPDATE document SET created_at = last_updated WHERE created_at IS NULL"))
        
        print("\n✅ Migration complete!")
        
        # Verify
        result = conn.execute(text("PRAGMA table_info(document)"))
        columns = result.fetchall()
        print(f"\n📊 Updated Document table schema:")
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            print(f"  {col[1]} ({col[2]}) - {nullable}")


if __name__ == "__main__":
    migrate_document_table()
