#!/usr/bin/env python3
"""
Make website_url nullable in Brand table

SQLite doesn't support ALTER COLUMN, so we need to:
1. Create new table with correct schema
2. Copy data
3. Drop old table
4. Rename new table
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


def migrate_brand_table():
    print("🔧 Migrating Brand table to make website_url nullable...")
    
    with engine.begin() as conn:
        # Disable foreign key constraints temporarily
        print("0️⃣  Disabling foreign key constraints...")
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        
        # Create new table with correct schema
        print("1️⃣  Creating new brand table...")
        conn.execute(text("""
            CREATE TABLE brand_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL,
                logo_url VARCHAR,
                website_url VARCHAR,
                description VARCHAR,
                primary_color VARCHAR,
                secondary_color VARCHAR
            )
        """))
        
        # Copy existing data
        print("2️⃣  Copying existing brand data...")
        conn.execute(text("""
            INSERT INTO brand_new (id, name, logo_url, website_url, description, primary_color, secondary_color)
            SELECT id, name, logo_url, website_url, description, primary_color, secondary_color
            FROM brand
        """))
        
        # Drop old table
        print("3️⃣  Dropping old brand table...")
        conn.execute(text("DROP TABLE brand"))
        
        # Rename new table
        print("4️⃣  Renaming new table to brand...")
        conn.execute(text("ALTER TABLE brand_new RENAME TO brand"))
        
        # Recreate index
        print("5️⃣  Recreating indexes...")
        conn.execute(text("CREATE INDEX ix_brand_name ON brand (name)"))
        
        # Re-enable foreign key constraints
        print("6️⃣  Re-enabling foreign key constraints...")
        conn.execute(text("PRAGMA foreign_keys = ON"))
        
        print("✅ Migration complete!")
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM brand"))
        count = result.scalar()
        print(f"📊 Brands in database: {count}")


if __name__ == "__main__":
    migrate_brand_table()
