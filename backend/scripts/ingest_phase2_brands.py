"""
Phase 2 Multi-Brand Ingestion Script
Ingests 5 target brands using support center discovery method
Brands: Rode, Boss, Roland, Mackie, PreSonus
"""

import asyncio
import json
import hashlib
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
from sqlmodel import Session, select, SQLModel
from app.core.database import create_db_and_tables, engine
from app.models.sql_models import Brand, Document, IngestLog
from app.services.rag_service import ingest_document
from app.services.ingestion_tracker import tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('ingest_phase2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BRAND_CONFIGS = {
    "Rode": {
        "brand_id": 3,
        "support_urls": [
            "https://en.rode.com/support",
            "https://en.rode.com/support/faqs",
            "https://en.rode.com/support/knowledge-base"
        ],
        "main_discovery_url": "https://en.rode.com/support",
        "category_limit": 50,
        "articles_per_category": 200,
        "target_docs": 1000
    },
    "Boss": {
        "brand_id": 2,
        "support_urls": [
            "https://www.boss.info/support",
            "https://www.boss.info/en/support/faqs",
            "https://www.boss.info/en/support/downloads"
        ],
        "main_discovery_url": "https://www.boss.info/support",
        "category_limit": 50,
        "articles_per_category": 200,
        "target_docs": 1000
    },
    "Roland": {
        "brand_id": 1,
        "support_urls": [
            "https://www.roland.com/support/",
            "https://www.roland.com/support/faqs/",
            "https://www.roland.com/support/knowledge-base/"
        ],
        "main_discovery_url": "https://www.roland.com/support/",
        "category_limit": 50,
        "articles_per_category": 200,
        "target_docs": 1000
    },
    "Mackie": {
        "brand_id": 21,
        "support_urls": [
            "https://mackie.com/support",
            "https://mackie.com/en/support/faq",
            "https://mackie.com/en/support/knowledge-base"
        ],
        "main_discovery_url": "https://mackie.com/support",
        "category_limit": 50,
        "articles_per_category": 200,
        "target_docs": 1000
    },
    "PreSonus": {
        "brand_id": 69,
        "support_urls": [
            "https://support.presonus.com/hc/en-us",
            "https://support.presonus.com/hc/en-us/categories",
            "https://presonus.com/support"
        ],
        "main_discovery_url": "https://support.presonus.com/hc/en-us",
        "category_limit": 50,
        "articles_per_category": 200,
        "target_docs": 1000
    }
}

class Phase2Ingester:
    """Multi-brand ingester for Phase 2 brands"""
    
    def __init__(self):
        self.ingested_urls: Set[str] = set()
        self.new_documents: Dict[str, int] = {}
        
    async def init_browser(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        
    async def close_browser(self):
        """Close Playwright browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def get_content_hash(self, content: str) -> str:
        """Generate MD5 hash of content for deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def discover_urls(self, page: Page, brand_name: str, config: dict) -> Set[str]:
        """Discover URLs from support pages"""
        discovered_urls = set()
        
        for base_url in config["support_urls"]:  # Try all URLs
            try:
                logger.info(f"  Discovering from {base_url}...")
                await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                
                # Extract all links
                links = await page.evaluate("""
                    () => {
                        return Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.href)
                            .filter(href => {
                                const h = href.toLowerCase();
                                return h.includes('/support') || h.includes('/faq') || h.includes('/knowledge') || h.includes('/article');
                            })
                            .slice(0, 200);
                    }
                """)
                
                for link in links:
                    if link and len(discovered_urls) < 100:
                        discovered_urls.add(link)
                        
            except Exception as e:
                logger.warning(f"    Error discovering from {base_url}: {e}")
                continue
        
        return discovered_urls
    
    async def extract_content(self, page: Page) -> tuple:
        """Extract article content and metadata"""
        try:
            # Get page content
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to extract title
            title = ""
            for tag in ['h1', 'title', 'meta[property="og:title"]']:
                elem = soup.select_one(tag)
                if elem:
                    title = elem.get('content') or elem.get_text(strip=True)
                    if title:
                        break
            
            # Extract body text
            body_text = ""
            for tag in soup.find_all(['p', 'li', 'div', 'section']):
                text = tag.get_text(strip=True)
                if len(text) > 50:
                    body_text += text + " "
            
            content = f"{title}\n\n{body_text}"
            
            return title or "Untitled", content[:5000]  # Limit to 5000 chars
            
        except Exception as e:
            logger.warning(f"    Error extracting content: {e}")
            return "", ""
    
    async def ingest_brand(self, brand_name: str, config: dict):
        """Ingest documents for a single brand"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"INGESTING: {brand_name}")
        logger.info(f"{'=' * 60}")
        logger.info(f"Target: {config['target_docs']} documents")
        logger.info(f"Brand ID: {config['brand_id']}")
        
        page = await self.browser.new_page()
        
        try:
            # Discover URLs
            logger.info("🔍 Discovering URLs...")
            discovered_urls = await self.discover_urls(page, brand_name, config)
            logger.info(f"   Found {len(discovered_urls)} potential URLs")
            tracker.update_urls_discovered(brand_name, len(discovered_urls))
            
            # Get existing URLs to avoid duplicates
            with Session(engine) as session:
                existing_docs = session.exec(
                    select(Document).where(Document.brand_id == config['brand_id'])
                ).all()
                self.ingested_urls = {doc.url for doc in existing_docs if doc.url}
            
            logger.info(f"   Already have {len(self.ingested_urls)} documents")
            
            # Ingest new URLs
            logger.info("📝 Ingesting documents...")
            new_count = 0
            
            for idx, url in enumerate(discovered_urls, 1):
                if url in self.ingested_urls:
                    continue
                    
                if new_count >= config["target_docs"]:
                    break
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(2)
                    
                    title, content = await self.extract_content(page)
                    
                    if content and len(content) > 100:
                        # Create document in SQL DB
                        doc = Document(
                            brand_id=config['brand_id'],
                            title=title[:200],
                            url=url,
                            content_hash=self.get_content_hash(content),
                            last_updated=datetime.utcnow()
                        )
                        
                        with Session(engine) as session:
                            session.add(doc)
                            session.commit()
                            session.refresh(doc)
                        
                        # Ingest into Vector DB
                        try:
                            await ingest_document(
                                text=content,
                                metadata={
                                    "source": url,
                                    "title": str(title),
                                    "brand_id": int(config['brand_id']),
                                    "doc_id": int(doc.id)
                                }
                            )
                        except Exception as ve:
                            logger.error(f"    Vector DB error for {url}: {ve}")

                        new_count += 1
                        tracker.update_document_count(brand_name, new_count)
                        if new_count % 5 == 0:
                            logger.info(f"   ✅ Ingested {new_count} documents...")
                    
                except Exception as e:
                    logger.warning(f"   Error processing {url}: {e}")
                    continue
            
            self.new_documents[brand_name] = new_count
            logger.info(f"✅ {brand_name}: {new_count} new documents ingested")
            
        finally:
            await page.close()
    
    async def run(self, target_brand: str = None):
        """Execute multi-brand ingestion"""
        create_db_and_tables()
        
        # Start tracker
        tracker.start()
        
        await self.init_browser()
        
        try:
            start_time = datetime.utcnow()
            logger.info(f"\n{'=' * 60}")
            logger.info("PHASE 2 INGESTION STARTED")
            logger.info(f"Time: {start_time.isoformat()}")
            if target_brand:
                logger.info(f"Target Brand: {target_brand}")
            else:
                logger.info(f"Brands: {', '.join(BRAND_CONFIGS.keys())}")
            logger.info(f"{'=' * 60}\n")
            
            brands_to_process = ["Rode", "Boss", "Roland", "Mackie", "PreSonus"]
            if target_brand:
                if target_brand in BRAND_CONFIGS:
                    brands_to_process = [target_brand]
                else:
                    logger.error(f"Brand {target_brand} not found in configuration")
                    return

            # Ingest each brand sequentially
            for brand_name in brands_to_process:
                if brand_name in BRAND_CONFIGS:
                    config = BRAND_CONFIGS[brand_name]
                    try:
                        # Update tracker for brand start
                        tracker.update_brand_start(brand_name, config['brand_id'])
                        
                        ingested = await self.ingest_brand(brand_name, config)
                        
                        # Update tracker for brand completion
                        tracker.update_brand_complete(brand_name, ingested)
                    except Exception as e:
                        logger.error(f"Failed to ingest {brand_name}: {e}")
                        tracker.add_error(f"{brand_name}: {str(e)}")
                        continue
            
            # Summary
            total_new = sum(self.new_documents.values())
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"\n{'=' * 60}")
            logger.info("PHASE 2 SUMMARY")
            logger.info(f"{'=' * 60}")
            logger.info(f"Total new documents: {total_new}")
            logger.info(f"Duration: {duration/60:.1f} minutes")
            
            for brand, count in self.new_documents.items():
                logger.info(f"  {brand}: {count} documents")
            
            logger.info(f"{'=' * 60}\n")
            
            # Mark tracker as complete ONLY if running full suite
            if not target_brand:
                tracker.complete()
            
        finally:
            await self.close_browser()

async def main():
    import sys
    target_brand = sys.argv[1] if len(sys.argv) > 1 else None
    ingester = Phase2Ingester()
    await ingester.run(target_brand)

if __name__ == "__main__":
    asyncio.run(main())
