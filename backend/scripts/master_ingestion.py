
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pa_brands_scraper import PABrandsScraper
from app.core.database import Session, engine
from app.models.sql_models import Brand
from sqlmodel import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("master_ingestion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def master_ingestion_plan():
    logger.info("🚀 STARTING MASTER INGESTION PLAN")
    logger.info("Target: 100% Official Documentation Coverage")
    logger.info("Constraint: English Documents Only")
    
    scraper = PABrandsScraper(force_rescan=True)
    
    # Get list of brands to process
    brands = scraper.brands_to_scrape
    total_brands = len(brands)
    
    logger.info(f"📋 Found {total_brands} brands to process")
    
    for i, brand_info in enumerate(brands, 1):
        brand_name = brand_info['name']
        logger.info(f"\n{'='*60}")
        logger.info(f"BRAND {i}/{total_brands}: {brand_name.upper()}")
        logger.info(f"{'='*60}")
        
        try:
            # Verify brand exists in DB
            with Session(engine) as session:
                brand = session.exec(select(Brand).where(Brand.name == brand_name)).first()
                if not brand:
                    logger.warning(f"⚠️ Brand {brand_name} not found in DB. Creating...")
                    brand = Brand(name=brand_name, website_url=brand_info['url'])
                    session.add(brand)
                    session.commit()
                    logger.info(f"✅ Created brand: {brand_name}")
            
            # Run scraper for this brand
            # Note: PABrandsScraper.run() iterates all brands. 
            # We might want to modify it to accept a specific brand or just let it run.
            # Looking at PABrandsScraper, it iterates self.brands_to_scrape.
            # So we can instantiate it with just this one brand to have granular control.
            
            single_brand_scraper = PABrandsScraper(force_rescan=True)
            single_brand_scraper.brands_to_scrape = [brand_info]
            
            logger.info(f"🕷️ Starting scrape for {brand_name}...")
            await single_brand_scraper.run()
            logger.info(f"✅ Completed {brand_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {brand_name}: {e}")
            import traceback
            traceback.print_exc()
            
        # Small pause between brands
        await asyncio.sleep(5)

    logger.info("\n🎉 MASTER INGESTION COMPLETE")

if __name__ == "__main__":
    asyncio.run(master_ingestion_plan())
