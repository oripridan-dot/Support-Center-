import asyncio
import logging
import json
import os
import argparse
from typing import List, Dict, Any
from .base_scraper import BaseScraper
from .discovery_engine import DiscoveryEngine
from .ingestion_engine import IngestionEngine
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LearningEngine:
    def __init__(self, headless: bool = True):
        self.scraper = BaseScraper(headless=headless)
        self.knowledge_base_dir = "/workspaces/Support-Center-/backend/data/knowledge"
        os.makedirs(self.knowledge_base_dir, exist_ok=True)

    async def start(self):
        await self.scraper.start()

    async def stop(self):
        await self.scraper.stop()

    def get_brand_info(self, brand_name: str):
        with Session(engine) as session:
            brand = session.exec(select(Brand).where(Brand.name == brand_name)).first()
            return brand

    async def process_brand(self, brand_name: str, base_url: str, strategies: List[str] = ["sitemap", "guessing"]):
        logger.info(f"--- Starting Learning Process for {brand_name} ---")
        brand = self.get_brand_info(brand_name)
        if not brand:
            logger.error(f"Brand {brand_name} not found in database.")
            return

        await self.scraper.establish_session(base_url)

        discovery = DiscoveryEngine(self.scraper, brand_name, base_url)
        ingestion = IngestionEngine(self.scraper)

        # 1. Discovery Phase
        logger.info(f"Phase 1: Discovery (Strategies: {strategies})")
        discovered_urls = await discovery.run_discovery(strategies=strategies)
        
        if not discovered_urls:
            logger.warning("No URLs discovered.")
            return

        # 2. Ingestion Phase
        logger.info(f"Phase 2: Ingestion ({len(discovered_urls)} URLs)")
        # Filter out URLs that are already in the DB if needed, 
        # but IngestionEngine handles hash checks.
        results = await ingestion.run_ingestion(discovered_urls, brand.id)
        
        # 3. Learning Phase
        logger.info("Phase 3: Learning and Refinement")
        successful_urls = [url for url, success in zip(discovered_urls, results) if success]
        discovery.learn_pattern(successful_urls)
        
        # Store summary
        summary = {
            "brand": brand_name,
            "total_discovered": len(discovered_urls),
            "total_ingested": len(successful_urls),
            "success_rate": len(successful_urls) / len(discovered_urls) if discovered_urls else 0,
            "patterns": discovery.patterns
        }
        
        summary_path = os.path.join(self.knowledge_base_dir, f"{brand_name.lower().replace(' ', '_')}_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
            
        logger.info(f"--- Finished Learning Process for {brand_name} ---")
        logger.info(f"Summary: {len(successful_urls)}/{len(discovered_urls)} URLs ingested successfully.")
        return summary

async def run_cli():
    parser = argparse.ArgumentParser(description="Learning Scraping and Ingestion Engine")
    parser.add_argument("--brand", help="Brand name to process")
    parser.add_argument("--url", help="Base URL for the brand")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--strategies", nargs="+", default=["sitemap", "guessing"], help="Discovery strategies")
    
    args = parser.parse_args()
    
    if not args.brand or not args.url:
        parser.print_help()
        return

    engine = LearningEngine(headless=args.headless)
    await engine.start()
    try:
        await engine.process_brand(args.brand, args.url, strategies=args.strategies)
    finally:
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(run_cli())
