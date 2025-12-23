from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .services.scraper_service import BrandScraper
from .core.database import get_session, engine
from sqlmodel import Session, select
from .models.sql_models import Brand
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def update_all_brands():
    logger.info("Starting weekly update for all brands...")
    with Session(engine) as session:
        brands = session.exec(select(Brand)).all()
        for brand in brands:
            logger.info(f"Updating brand: {brand.name}")
            scraper = BrandScraper(brand.website_url)
            # In a real scenario, we would await scraper.scrape_site() 
            # and then ingest the new content into the vector DB.
            # await scraper.scrape_site()
            
    logger.info("Weekly update completed.")

def start_scheduler():
    # Schedule to run every week
    scheduler.add_job(update_all_brands, 'interval', weeks=1)
    scheduler.start()
