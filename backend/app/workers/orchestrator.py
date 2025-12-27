"""
Worker Orchestrator

Coordinates the 3-worker ingestion pipeline:
1. Explorer discovers documentation and creates strategy
2. Scraper executes strategy and collects documents
3. Ingester vectorizes and calls Explorer for verification

This orchestrator manages the workflow and can run workers
independently or as a complete pipeline.

PARALLEL MODE: Explorer can move to next brand while Scraper/Ingester process current brand.
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from collections import deque

from app.workers.explorer import ExplorerWorker, ScrapingStrategy
from app.workers.scraper import ScraperWorker
from app.workers.ingester import IngesterWorker


class WorkerOrchestrator:
    """
    Orchestrates the 3-worker ingestion pipeline
    Supports both sequential and parallel execution modes
    """
    
    def __init__(self):
        self.explorer = ExplorerWorker()
        self.scraper = ScraperWorker()
        self.ingester = IngesterWorker()
        
        # Parallel execution queues
        self.brand_queue: asyncio.Queue = asyncio.Queue()  # Brands to explore
        self.scraper_queue: asyncio.Queue = asyncio.Queue()
        self.ingester_queue: asyncio.Queue = asyncio.Queue()
        
        # Active tasks tracking
        self.active_tasks: List[asyncio.Task] = []
        self.parallel_mode = False
        self.workers_initialized = False
    
    async def initialize(self):
        """Initialize all workers"""
        if not self.workers_initialized:
            await self.explorer.initialize()
            await self.scraper.initialize()
            self.workers_initialized = True
            print(f"✅ Workers initialized")
    
    async def shutdown(self):
        """Cleanup all workers"""
        if self.workers_initialized:
            await self.explorer.shutdown()
            await self.scraper.shutdown()
            self.workers_initialized = False
            print(f"✅ Workers shut down")
    
    async def run_full_pipeline(
        self, 
        brand_id: int,
        use_cached_strategy: bool = False,
        parallel_mode: bool = False
    ) -> Dict:
        """
        Execute the complete ingestion pipeline for a brand:
        Explorer → Scraper → Ingester → Verification
        
        Args:
            brand_id: Brand to process
            use_cached_strategy: Use existing strategy if available
            parallel_mode: If True, workers run independently. Explorer can start next brand
                          while Scraper/Ingester process current brand.
        """
        start_time = datetime.now()
        self.parallel_mode = parallel_mode
        
        mode_label = "PARALLEL" if parallel_mode else "SEQUENTIAL"
        print(f"\n{'='*80}")
        print(f"🚀 STARTING {mode_label} PIPELINE FOR BRAND {brand_id}")
        print(f"{'='*80}")
        print(f"🎯 MISSION: 100% OFFICIAL DOCUMENTATION COVERAGE")
        print(f"📋 STRATEGY: Explorer → Scraper → Ingester → Verification")
        if parallel_mode:
            print(f"⚡ MODE: Parallel - Explorer can move ahead independently")
        else:
            print(f"⚡ MODE: Sequential - Each worker waits for previous")
        print(f"{'='*80}\n")
        
        try:
            # Initialize workers
            await self.initialize()
            
            if parallel_mode:
                # Start background workers
                scraper_task = asyncio.create_task(self._scraper_worker_loop())
                ingester_task = asyncio.create_task(self._ingester_worker_loop())
                self.active_tasks = [scraper_task, ingester_task]
                print(f"🤖 Background workers started")
            
            # STAGE 1: Explorer - Discover documentation
            print(f"\n📍 STAGE 1/3: EXPLORER")
            print(f"{'-'*70}")
            strategy = await self.explorer.explore_brand(brand_id)
            
            if strategy.total_estimated_docs == 0:
                print(f"⚠️  No documentation found. Aborting pipeline.")
                return {"success": False, "error": "No documentation discovered"}
            
            # STAGE 2: Scraper - Collect documentation
            print(f"\n📍 STAGE 2/3: SCRAPER")
            print(f"{'-'*70}")
            
            if parallel_mode:
                # Queue strategy for scraper worker
                await self.scraper_queue.put((brand_id, strategy))
                print(f"✅ Strategy queued for Scraper. Explorer can now move to next brand.")
                
                # Return immediately - scraper/ingester run in background
                return {
                    "success": True,
                    "mode": "parallel",
                    "message": "Strategy queued. Scraper and Ingester will process in background.",
                    "strategy": strategy.model_dump(),
                    "discovered_docs": strategy.total_estimated_docs
                }
            else:
                # Sequential mode - wait for each stage
                scraped_docs = await self.scraper.execute_strategy(strategy)
            
            if not scraped_docs:
                print(f"⚠️  No documents scraped. Aborting pipeline.")
                return {"success": False, "error": "Scraping failed"}
            
            # Save scraped docs for potential re-ingestion
            self.scraper.save_to_disk(scraped_docs, strategy)
            
            # STAGE 3: Ingester - Vectorize and verify
            print(f"\n📍 STAGE 3/3: INGESTER + VERIFICATION")
            print(f"{'-'*70}")
            ingestion_result = await self.ingester.ingest_batch(
                scraped_docs=scraped_docs,
                brand_id=brand_id,
                verify=True  # Calls Explorer for verification
            )
            
            # Final summary
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"\n{'='*80}")
            print(f"✅ PIPELINE COMPLETE FOR BRAND {brand_id}")
            print(f"{'='*80}")
            print(f"⏱️  DURATION:    {duration:.1f} seconds")
            print(f"\n📊 RESULTS:")
            print(f"   • Discovered:  {strategy.total_estimated_docs} documents")
            print(f"   • Scraped:     {len(scraped_docs)} documents")
            print(f"   • Ingested:    {ingestion_result['ingested']} documents")
            print(f"   • Skipped:     {ingestion_result['skipped']} documents (already existed)")
            print(f"   • Errors:      {ingestion_result['errors']} documents")
            
            if ingestion_result.get('verification_report'):
                vr = ingestion_result['verification_report']
                coverage = vr['coverage_percentage']
                print(f"\n🎯 COVERAGE STATUS:")
                print(f"   • Coverage:    {coverage}%")
                
                if coverage >= 100:
                    print(f"   🎉 ✨ 100% COVERAGE ACHIEVED! MISSION COMPLETE! ✨")
                else:
                    gap = 100 - coverage
                    print(f"   ⚠️  GAP:        {gap:.1f}% remaining")
                    print(f"   🔴 Missing:    {len(vr['missing_docs'])} documents")
                    print(f"\n   📋 NEXT STEPS: Re-run pipeline or investigate missing docs")
            
            print(f"{'='*80}\n")
            
            return {
                "success": True,
                "duration_seconds": duration,
                "strategy": strategy.model_dump(),
                "scraped_count": len(scraped_docs),
                "ingestion_result": ingestion_result
            }
        
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"❌ PIPELINE FAILED FOR BRAND {brand_id}")
            print(f"{'='*70}")
            print(f"Error: {e}")
            print(f"{'='*70}\n")
            
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
        
        finally:
            # In parallel mode, don't shutdown - workers need to keep running
            if not parallel_mode:
                await self.shutdown()
    
    async def _scraper_worker_loop(self):
        """Background worker that processes scraping queue"""
        print(f"🤖 Scraper worker started (background mode)")
        
        while True:
            try:
                # Wait for strategy from Explorer
                brand_id, strategy = await self.scraper_queue.get()
                
                print(f"\n🤖 Scraper worker: Processing brand {brand_id}")
                scraped_docs = await self.scraper.execute_strategy(strategy)
                
                if scraped_docs:
                    # Save to disk
                    self.scraper.save_to_disk(scraped_docs, strategy)
                    
                    # Queue for ingester
                    await self.ingester_queue.put((brand_id, scraped_docs))
                    print(f"✅ Scraper: {len(scraped_docs)} docs → Ingester queue")
                else:
                    print(f"⚠️  Scraper: No documents scraped for brand {brand_id}")
                
                self.scraper_queue.task_done()
                
            except asyncio.CancelledError:
                print(f"🛑 Scraper worker shutting down")
                break
            except Exception as e:
                print(f"❌ Scraper worker error: {e}")
                self.scraper_queue.task_done()
    
    async def _ingester_worker_loop(self):
        """Background worker that processes ingestion queue"""
        print(f"🤖 Ingester worker started (background mode)")
        
        while True:
            try:
                # Wait for docs from Scraper
                brand_id, scraped_docs = await self.ingester_queue.get()
                
                print(f"\n🤖 Ingester worker: Processing {len(scraped_docs)} docs for brand {brand_id}")
                result = await self.ingester.ingest_batch(
                    scraped_docs=scraped_docs,
                    brand_id=brand_id,
                    verify=True
                )
                
                print(f"✅ Ingester: {result['ingested']} ingested, {result['skipped']} skipped")
                
                if result.get('verification_report'):
                    vr = result['verification_report']
                    coverage = vr['coverage_percentage']
                    print(f"📊 Coverage: {coverage}%")
                    
                    if coverage >= 100:
                        print(f"🎉 100% COVERAGE ACHIEVED for brand {brand_id}!")
                
                self.ingester_queue.task_done()
                
            except asyncio.CancelledError:
                print(f"🛑 Ingester worker shutting down")
                break
            except Exception as e:
                print(f"❌ Ingester worker error: {e}")
                self.ingester_queue.task_done()
    
    async def stop_parallel_workers(self):
        """Stop background worker tasks"""
        if self.active_tasks:
            print(f"\n🛑 Stopping parallel workers...")
            for task in self.active_tasks:
                task.cancel()
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            self.active_tasks = []
            print(f"✅ Workers stopped")
    
    async def run_explorer_only(self, brand_id: int) -> ScrapingStrategy:
        """
        Run only the Explorer to generate a scraping strategy
        Useful for planning before execution
        """
        await self.explorer.initialize()
        try:
            strategy = await self.explorer.explore_brand(brand_id)
            return strategy
        finally:
            await self.explorer.shutdown()
    
    async def run_scraper_only(self, strategy: ScrapingStrategy):
        """
        Run only the Scraper with an existing strategy
        Useful for re-scraping without re-discovery
        """
        await self.scraper.initialize()
        try:
            docs = await self.scraper.execute_strategy(strategy)
            self.scraper.save_to_disk(docs, strategy)
            return docs
        finally:
            await self.scraper.shutdown()
    
    async def run_ingester_only(self, scraped_docs, brand_id: int, verify: bool = True):
        """
        Run only the Ingester with already-scraped documents
        Useful for re-vectorization or testing
        """
        result = await self.ingester.ingest_batch(
            scraped_docs=scraped_docs,
            brand_id=brand_id,
            verify=verify
        )
        return result


# Global orchestrator instance
orchestrator = WorkerOrchestrator()


# Convenience functions for API endpoints
async def ingest_brand_full_pipeline(brand_id: int) -> Dict:
    """Run the complete pipeline for a brand"""
    return await orchestrator.run_full_pipeline(brand_id)


async def explore_brand_only(brand_id: int) -> ScrapingStrategy:
    """Run only exploration phase"""
    return await orchestrator.run_explorer_only(brand_id)


async def verify_brand_ingestion(brand_id: int):
    """Verify ingestion completeness"""
    explorer = ExplorerWorker()
    try:
        return await explorer.verify_ingestion(brand_id)
    finally:
        pass
