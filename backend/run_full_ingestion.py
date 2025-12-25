
import asyncio
import logging
import sys
import os

# Add parent to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pa_brands_scraper import PABrandsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("full_ingestion.log")
    ]
)

async def main():
    logging.info("Starting full ingestion process...")
    scraper = PABrandsScraper(force_rescan=True)
    await scraper.run()
    logging.info("Full ingestion process completed.")

if __name__ == "__main__":
    asyncio.run(main())
