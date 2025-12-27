#!/usr/bin/env python3
"""
Brand Ingestion Master Script
Properly ingests ONE brand at a time without duplicates

Usage:
    python3 ingest_brand.py <brand_name>
    
Example:
    python3 ingest_brand.py "RCF"
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand, ProductFamily, Product, Document
from app.services.pa_brands_scraper import PABrandsScraper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_brand(brand_name: str):
    """
    Properly ingest a single brand with NO duplicates
    
    Process:
    1. Check if brand exists in DB (avoid duplicate brands)
    2. Scrape official documentation
    3. Create unique products (no duplicates)
    4. Store documents with content hash (avoid duplicate docs)
    5. Index in vector store
    """
    
    print("=" * 80)
    print(f"INGESTING BRAND: {brand_name}")
    print("=" * 80)
    
    with Session(engine) as session:
        # Check if brand already exists
        existing = session.exec(
            select(Brand).where(Brand.name == brand_name)
        ).first()
        
        if existing:
            print(f"\n⚠️  Brand '{brand_name}' already exists in database (ID: {existing.id})")
            response = input("Continue and update? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return False
            brand_id = existing.id
            print(f"📝 Updating existing brand ID: {brand_id}")
        else:
            print(f"\n🆕 Creating new brand: {brand_name}")
            # Brand will be created by scraper
            brand_id = None
    
    # Initialize scraper
    scraper = PABrandsScraper()
    
    # Get brand data from Halilit website
    print(f"\n🔍 Fetching brand information from Halilit...")
    
    # Find brand in Halilit catalog
    # This should query the Halilit API or database for the brand
    # For now, we'll use the scraper's existing logic
    
    print(f"\n📥 Scraping documentation...")
    try:
        # The scraper should handle:
        # - Creating/updating brand entry
        # - Avoiding duplicate products (check by name+brand_id)
        # - Avoiding duplicate documents (check by content_hash)
        # - Creating unique product families
        
        await scraper.scrape_brand(brand_name)
        
        print(f"\n✅ Brand '{brand_name}' ingestion complete!")
        
        # Show summary
        with Session(engine) as session:
            brand = session.exec(
                select(Brand).where(Brand.name == brand_name)
            ).first()
            
            if brand:
                doc_count = session.exec(
                    select(Document).where(Document.brand_id == brand.id)
                ).all()
                
                product_count = session.exec(
                    select(Product)
                    .join(ProductFamily)
                    .where(ProductFamily.brand_id == brand.id)
                ).all()
                
                print(f"\n📊 Summary:")
                print(f"   Brand ID:     {brand.id}")
                print(f"   Documents:    {len(doc_count)}")
                print(f"   Products:     {len(product_count)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ingesting brand: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ingest_brand.py <brand_name>")
        print("\nExample: python3 ingest_brand.py 'RCF'")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    
    success = asyncio.run(ingest_brand(brand_name))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
