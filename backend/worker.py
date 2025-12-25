"""
Scraper Worker Process - Runs independently from API server
"""
import asyncio
import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select, func
from app.core.database import engine
from app.models.sql_models import Brand, Document
from app.models.ingestion_status import IngestionStatus
from app.services.pa_brands_scraper import PABrandsScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScraperWorker:
    def __init__(self):
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def update_brand_status(self, brand_id: int, status: str, progress: float = 0):
        """Update ingestion status in database"""
        with Session(engine) as session:
            # First, clear any other "processing" statuses if we're starting a new one
            if status == "processing":
                other_processing = session.exec(
                    select(IngestionStatus)
                    .where(IngestionStatus.status == "processing")
                    .where(IngestionStatus.brand_id != brand_id)
                ).all()
                for other in other_processing:
                    other.status = "idle"
                    session.add(other)
            
            # Now update/create the current brand's status
            status_record = session.exec(
                select(IngestionStatus).where(IngestionStatus.brand_id == brand_id)
            ).first()
            
            if status_record:
                status_record.status = status
                status_record.progress_percent = progress
                status_record.updated_at = datetime.now()
            else:
                brand = session.get(Brand, brand_id)
                if brand:
                    status_record = IngestionStatus(
                        brand_id=brand_id,
                        brand_name=brand.name,
                        status=status,
                        progress_percent=progress
                    )
                    session.add(status_record)
            
            session.commit()
    
    def _normalize_name(self, name: str) -> str:
        """Normalize brand name for matching"""
        return name.lower().strip().replace("&", "and").replace("-", " ")
    
    def _find_scraper_brand(self, brand_name: str, scraper_brands: list) -> dict:
        """Find matching brand in scraper configuration"""
        normalized = self._normalize_name(brand_name)
        
        for scraper_brand in scraper_brands:
            scraper_normalized = self._normalize_name(scraper_brand["name"])
            # Exact match after normalization
            if normalized == scraper_normalized:
                return scraper_brand
            # Partial match (e.g., "Krk Systems" matches "Krk")
            if normalized in scraper_normalized or scraper_normalized in normalized:
                return scraper_brand
        
        return None
    
    async def scrape_brand(self, brand_name: str):
        """Scrape a single brand"""
        logger.info(f"🚀 Starting scrape for {brand_name}")
        
        try:
            with Session(engine) as session:
                brand = session.exec(
                    select(Brand).where(Brand.name == brand_name)
                ).first()
                
                if not brand:
                    logger.error(f"❌ Brand {brand_name} not found in database")
                    return
                
                # Update status to processing (this will clear other processing statuses)
                await self.update_brand_status(brand.id, "processing", 0)
            
            # Create scraper and find matching brand
            scraper = PABrandsScraper(force_rescan=False)
            matched_brand = self._find_scraper_brand(brand_name, scraper.brands_to_scrape)
            
            if not matched_brand:
                logger.info(f"⏭️  Skipping {brand_name} (not in scraper configuration)")
                return
            
            # Filter to only this brand
            scraper.brands_to_scrape = [matched_brand]
            
            logger.info(f"📥 Scraping {brand_name} (matched: {matched_brand['name']})")
            
            # Run the scraper
            await scraper.run()
            
            await self.update_brand_status(brand.id, "complete", 100)
            logger.info(f"✅ Completed scrape for {brand_name}")
            
        except Exception as e:
            logger.error(f"❌ Error scraping {brand_name}: {e}", exc_info=True)
            with Session(engine) as session:
                brand = session.exec(
                    select(Brand).where(Brand.name == brand_name)
                ).first()
                if brand:
                    await self.update_brand_status(brand.id, "error", 0)
    
    async def run_once(self, brand_name: str = None):
        """Run scraper once"""
        logger.info(f"�� Running worker in single-shot mode for {brand_name or 'next brand'}")
        
        if brand_name:
            await self.scrape_brand(brand_name)
        else:
            with Session(engine) as session:
                brands = session.exec(select(Brand)).all()
                if brands:
                    await self.scrape_brand(brands[0].name)
    
    async def run_continuous(self, delay: int = 60):
        """Run scraper continuously - Dynamic priority based on DB state"""
        logger.info(f"🔄 Scraper worker started in SMART MODE (delay: {delay}s)")
        
        while self.running:
            try:
                # 1. Determine strategy by scanning DB
                with Session(engine) as session:
                    logger.info("🧠 Scanning database to determine next best action...")
                    
                    # Get all brands and their document counts
                    brands = session.exec(select(Brand)).all()
                    brand_stats = []
                    
                    for brand in brands:
                        doc_count = session.exec(
                            select(func.count(Document.id)).where(Document.brand_id == brand.id)
                        ).one()
                        
                        # Get ingestion status
                        status = session.exec(
                            select(IngestionStatus).where(IngestionStatus.brand_id == brand.id)
                        ).first()
                        
                        status_str = status.status if status else "idle"
                        last_updated = status.updated_at if status else datetime.min
                        
                        brand_stats.append({
                            "name": brand.name,
                            "doc_count": doc_count,
                            "status": status_str,
                            "last_updated": last_updated
                        })
                
                # 2. Prioritize Brands
                # Priority 1: Brands with 0 documents (High Urgency)
                # Priority 2: Brands marked as 'error' (Retry)
                # Priority 3: Brands with oldest update time (Refresh)
                
                scraper = PABrandsScraper(force_rescan=False)
                known_scraper_brands = {b["name"] for b in scraper.brands_to_scrape}
                
                # Filter only brands we know how to scrape
                valid_brands = [b for b in brand_stats if b["name"] in known_scraper_brands]
                
                # Sort by priority
                valid_brands.sort(key=lambda x: (
                    x["doc_count"] > 0,  # False (0) comes first -> 0 docs first
                    x["status"] != "error", # False (0) comes first -> errors second
                    x["last_updated"] # Oldest dates first
                ))
                
                if not valid_brands:
                    logger.warning("⚠️ No valid brands found to scrape. Waiting...")
                    await asyncio.sleep(delay)
                    continue

                # 3. Execute Strategy
                target_brand = valid_brands[0]
                logger.info(f"🎯 STRATEGY DECISION: Selected {target_brand['name']}")
                logger.info(f"   Reason: Docs={target_brand['doc_count']}, Status={target_brand['status']}, LastUpd={target_brand['last_updated']}")
                
                await self.scrape_brand(target_brand['name'])
                
                if self.running:
                    logger.info(f"✅ Finished {target_brand['name']}, waiting {delay}s before next cycle...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ Worker error: {e}", exc_info=True)
                await asyncio.sleep(10)

async def main():
    parser = argparse.ArgumentParser(description="Brand Scraping Worker")
    parser.add_argument("--mode", choices=["continuous", "once"], default="once")
    parser.add_argument("--brand", type=str, help="Specific brand name")
    parser.add_argument("--delay", type=int, default=60)
    
    args = parser.parse_args()
    
    worker = ScraperWorker()
    
    try:
        if args.mode == "continuous":
            await worker.run_continuous(delay=args.delay)
        else:
            await worker.run_once(brand_name=args.brand)
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped")
    except Exception as e:
        logger.error(f"❌ Worker crashed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
