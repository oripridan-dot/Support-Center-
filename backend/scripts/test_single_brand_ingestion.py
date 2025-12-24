#!/usr/bin/env python3
"""
Test ingestion for a single Halilit brand
Usage: python3 test_single_brand_ingestion.py "Brand Name"
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.sql_models import Brand
from sqlmodel import select
import logging

# Import the ingestion function
from ingest_halilit_brands import ingest_brand

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_single_brand_ingestion.py 'Brand Name'")
        print("\nExample brands:")
        print("  - Adam Audio")
        print("  - Roland")
        print("  - Nord")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    
    # Get brand from database
    session = next(get_session())
    brand = session.exec(
        select(Brand).where(Brand.name == brand_name)
    ).first()
    
    if not brand:
        logger.error(f"Brand '{brand_name}' not found in database")
        sys.exit(1)
    
    logger.info(f"Testing ingestion for: {brand.name}")
    logger.info(f"Website: {brand.website_url}")
    
    success = await ingest_brand(brand, priority=True)
    
    if success:
        logger.info(f"\n✅ SUCCESS: {brand.name} ingestion completed")
    else:
        logger.error(f"\n❌ FAILED: {brand.name} ingestion failed")

if __name__ == "__main__":
    asyncio.run(main())
