
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pa_brands_scraper import PABrandsScraper
# Import script modules dynamically or by adding scripts to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import download_brand_pdfs
import pdf_to_rag

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("ingestion_full.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_ingestion_for_brand(brand_name):
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 STARTING INGESTION FOR: {brand_name}")
    logger.info(f"{'='*60}")
    
    # 1. Scrape Website (Links & Content)
    logger.info(f"Step 1: Scraping website for {brand_name}...")
    try:
        scraper = PABrandsScraper()
        # Filter for specific brand
        scraper.brands_to_scrape = [b for b in scraper.brands_to_scrape if b['name'].lower() == brand_name.lower()]
        
        if not scraper.brands_to_scrape:
            logger.error(f"❌ Brand {brand_name} not found in scraper configuration!")
            return
            
        await scraper.run()
        logger.info(f"✅ Website scraping complete for {brand_name}")
    except Exception as e:
        logger.error(f"❌ Error scraping website for {brand_name}: {e}")
        return # Stop if scraping fails

    # 2. Download PDFs
    logger.info(f"Step 2: Downloading PDFs for {brand_name}...")
    try:
        await download_brand_pdfs.process_brand_pdfs(brand_name)
        logger.info(f"✅ PDF download complete for {brand_name}")
    except Exception as e:
        logger.error(f"❌ Error downloading PDFs for {brand_name}: {e}")

    # 3. Ingest PDFs
    logger.info(f"Step 3: Ingesting PDFs for {brand_name}...")
    try:
        processor = pdf_to_rag.PDFToRAGProcessor()
        await processor.process_brand(brand_name)
        logger.info(f"✅ PDF ingestion complete for {brand_name}")
    except Exception as e:
        logger.error(f"❌ Error ingesting PDFs for {brand_name}: {e}")

    logger.info(f"\n✨ COMPLETED INGESTION FOR: {brand_name}")

async def main():
    # Get list of brands from scraper config
    scraper = PABrandsScraper()
    brands = [b['name'] for b in scraper.brands_to_scrape]
    
    logger.info(f"Found {len(brands)} brands to process: {', '.join(brands)}")
    
    for brand in brands:
        await run_ingestion_for_brand(brand)
        # Small pause between brands
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
