#!/usr/bin/env python3
"""
Test ingestion for a single Halilit brand with detailed diagnostics
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.sql_models import Brand
from sqlmodel import select
import logging

# Import the ingestion functions
from ingest_halilit_brands import scrape_brand_products, ingest_product_page

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

async def test_single_brand(brand_name: str, max_products: int = 5):
    """
    Test ingestion for a single brand with limited products
    """
    # Get brand from database
    session = next(get_session())
    brand = session.exec(
        select(Brand).where(Brand.name == brand_name)
    ).first()
    
    if not brand:
        logger.error(f"Brand '{brand_name}' not found in database")
        return False
    
    logger.info("="*80)
    logger.info(f"TESTING INGESTION FOR: {brand.name}")
    logger.info("="*80)
    logger.info(f"Website: {brand.website_url}")
    logger.info(f"Max products: {max_products}")
    logger.info("")
    
    # Step 1: Scrape products
    logger.info("STEP 1: Scraping product list...")
    products = await scrape_brand_products(brand, max_products)
    
    if not products:
        logger.error(f"✗ FAILED: No products found for {brand.name}")
        return False
    
    logger.info(f"✓ Found {len(products)} products")
    logger.info("")
    logger.info("Product URLs:")
    for i, product in enumerate(products, 1):
        logger.info(f"  {i}. {product['name']}")
        logger.info(f"     URL: {product['url']}")
    
    logger.info("")
    logger.info("STEP 2: Testing product page ingestion...")
    logger.info("")
    
    # Step 2: Test ingesting first product
    success_count = 0
    fail_count = 0
    
    for i, product in enumerate(products[:3], 1):  # Test first 3
        logger.info(f"[{i}/3] Testing: {product['name'][:60]}...")
        try:
            result = await ingest_product_page(product, brand)
            if result:
                success_count += 1
                logger.info(f"  ✓ SUCCESS")
            else:
                logger.info(f"  ⏭️  SKIPPED (already ingested)")
        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ FAILED: {e}")
        
        await asyncio.sleep(0.5)
    
    logger.info("")
    logger.info("="*80)
    logger.info("TEST RESULTS")
    logger.info("="*80)
    logger.info(f"Products found: {len(products)}")
    logger.info(f"Successful ingestions: {success_count}")
    logger.info(f"Failed ingestions: {fail_count}")
    logger.info("="*80)
    
    if fail_count == 0 and success_count > 0:
        logger.info("✅ TEST PASSED - Ready for full ingestion!")
        return True
    elif fail_count == 0 and success_count == 0:
        logger.info("⚠️  TEST SKIPPED - All products already ingested")
        return True
    else:
        logger.error("❌ TEST FAILED - Fix errors before full ingestion")
        return False

async def main():
    # Default to Adam Audio since it's already partially ingested
    test_brand = "Nord" if len(sys.argv) < 2 else sys.argv[1]
    
    logger.info(f"Starting test ingestion for: {test_brand}")
    logger.info("")
    
    success = await test_single_brand(test_brand, max_products=10)
    
    if success:
        logger.info("\n✅ Test completed successfully!")
        logger.info("You can now run the full ingestion with confidence:")
        logger.info("  python3 scripts/ingest_halilit_brands.py")
        sys.exit(0)
    else:
        logger.error("\n❌ Test failed - please fix errors first")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
