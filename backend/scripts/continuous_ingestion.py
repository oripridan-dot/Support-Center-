#!/usr/bin/env python3
"""
Continuous Background Ingestion Service
Runs ingestion tasks periodically to build the complete product catalog
Monitors progress and logs status to the UI
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import create_db_and_tables, engine
from app.models.sql_models import Brand, Document
from app.services.ingestion_tracker import tracker
from sqlmodel import Session, select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/tmp/continuous_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Brands with specific scripts for high-quality ingestion
SPECIAL_SCRIPTS = {
    "Montarbo": "ingest_montarbo.py",
    "RCF": "ingest_rcf_robust.py",
    "Allen & Heath": "ingest_ah_complete_v2.py",
    "Rode": "ingest_comprehensive_brands.py",
    "Roland": "ingest_comprehensive_brands.py",
    "Boss": "ingest_comprehensive_brands.py",
    "Mackie": "ingest_comprehensive_brands.py",
    "PreSonus": "ingest_comprehensive_brands.py",
}

class ContinuousIngestionService:
    """Service to manage continuous background ingestion"""
    
    def __init__(self):
        self.is_running = False
        self.current_brand = None
        self.last_cycle_start = None
        self.cycle_count = 0
        create_db_and_tables()
        
    async def start(self):
        """Start the continuous ingestion service"""
        logger.info("=" * 80)
        logger.info("CONTINUOUS INGESTION SERVICE STARTED")
        logger.info("=" * 80)
        self.is_running = True
        
        while self.is_running:
            try:
                await self.run_ingestion_cycle()
            except Exception as e:
                logger.error(f"Error in ingestion cycle: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
                
    async def get_brands_to_ingest(self) -> List[Dict]:
        """Fetch brands from DB and prioritize those with 0 documents"""
        brands_to_ingest = []
        with Session(engine) as session:
            brands = session.exec(select(Brand)).all()
            for brand in brands:
                # Count documents
                doc_count = len(session.exec(select(Document).where(Document.brand_id == brand.id)).all())
                
                script = SPECIAL_SCRIPTS.get(brand.name, "ingest_generic_brand.py")
                
                brands_to_ingest.append({
                    "id": brand.id,
                    "brand": brand.name,
                    "script": script,
                    "doc_count": doc_count,
                    "website": brand.website_url
                })
        
        # Sort: 0 docs first, then by name
        brands_to_ingest.sort(key=lambda x: (x["doc_count"] > 0, x["brand"]))
        return brands_to_ingest

    async def run_ingestion_cycle(self):
        """Run one complete ingestion cycle through all brands"""
        self.cycle_count += 1
        self.last_cycle_start = datetime.now()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"INGESTION CYCLE #{self.cycle_count}")
        logger.info(f"Start Time: {self.last_cycle_start}")
        logger.info(f"{'='*80}\n")
        
        queue = await self.get_brands_to_ingest()
        total_brands = len(queue)
        
        tracker.start("Complete Catalog Ingestion")
        
        completed_brands = 0
        
        for item in queue:
            brand_name = item["brand"]
            self.current_brand = brand_name
            
            try:
                logger.info(f"\n[{completed_brands + 1}/{total_brands}] Starting ingestion for: {brand_name} ({item['doc_count']} existing docs)")
                
                tracker.update_step(
                    step=f"[{completed_brands + 1}/{total_brands}] Ingesting {brand_name}...",
                    brand=brand_name
                )

                # Run the ingestion script
                args = [brand_name]
                if item["script"] == "ingest_generic_brand.py":
                    args.append(item["website"] or "")

                await self.run_ingestion_script(item["script"], brand_name, args)
                completed_brands += 1
                
                # Wait before next brand (be respectful to servers)
                if completed_brands < total_brands:
                    logger.info(f"Waiting 5 seconds before next brand...")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Failed to ingest {brand_name}: {e}")
                continue
        
        # Cycle complete
        cycle_end = datetime.now()
        cycle_duration = (cycle_end - self.last_cycle_start).total_seconds() / 60
        
        logger.info(f"\n{'='*80}")
        logger.info(f"INGESTION CYCLE #{self.cycle_count} COMPLETED")
        logger.info(f"Duration: {cycle_duration:.1f} minutes")
        logger.info(f"Brands Completed: {completed_brands}/{total_brands}")
        logger.info(f"End Time: {cycle_end}")
        logger.info(f"{'='*80}\n")
        
        tracker.complete()
        
        # Schedule next cycle (run every 24 hours)
        wait_seconds = 86400
        logger.info(f"Next ingestion cycle in 24 hours ({wait_seconds/3600:.0f}h)")
        await asyncio.sleep(wait_seconds)
        
    async def run_ingestion_script(self, script_name: str, brand_name: str, args: List[str] = None):
        """Run a single ingestion script"""
        import os
        
        script_path = Path(__file__).parent / script_name
        
        if not script_path.exists():
            logger.warning(f"Ingestion script not found: {script_path}. Skipping.")
            return
        
        logger.info(f"Executing: {script_name} {' '.join(args or [])}")
        
        # Set up environment with PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent.parent)
        
        cmd = ["python3", str(script_path)]
        if args:
            cmd.extend(args)
            
        # Run the script
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(__file__).parent.parent),
            env=env
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully ingested {brand_name}")
        else:
            error_msg = stderr.decode() if stderr else "No error details"
            logger.error(f"❌ Script failed for {brand_name}: {error_msg}")
    
    def stop(self):
        """Stop the service gracefully"""
        logger.info("Stopping continuous ingestion service...")
        self.is_running = False


async def main():
    """Main entry point"""
    service = ContinuousIngestionService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received")
        service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
