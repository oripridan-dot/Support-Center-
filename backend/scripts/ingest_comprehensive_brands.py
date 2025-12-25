"""
Comprehensive Brand Documentation Ingestion
Captures: Product Documentation + Help/Support Centers + Official Specs
Brands: Rode, Boss, Roland, Mackie, PreSonus
"""

import asyncio
import json
import hashlib
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Tuple
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
from sqlmodel import Session, select, SQLModel
from app.core.database import create_db_and_tables, engine
from app.models.sql_models import Brand, Document, IngestLog, Product, ProductFamily
from app.services.ingestion_tracker import tracker
from app.services.rag_service import ingest_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('ingest_comprehensive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

COMPREHENSIVE_BRAND_CONFIGS = {
    "Rode": {
        "brand_id": 3,
        "support_centers": [
            "https://rode.com/en/support",
            "https://rode.com/en/support/faqs",
            "https://rode.com/en/support/knowledge-base"
        ],
        "product_docs": [
            "https://rode.com/en/microphones",
            "https://rode.com/en/wireless",
            "https://rode.com/en/interfaces",
            "https://rode.com/en/software",
            "https://rode.com/en/accessories"
        ],
        "spec_sources": [
            "https://rode.com/en/support/downloads",
            "https://rode.com/en/microphones/specifications"
        ],
        "target_docs": 1000
    },
    "Boss": {
        "brand_id": 71,
        "support_centers": [
            "https://www.boss.info/support",
            "https://www.boss.info/en/support/faqs",
            "https://www.boss.info/en/support/knowledge-base"
        ],
        "product_docs": [
            "https://www.boss.info/en/products",
            "https://www.boss.info/en/categories/guitar",
            "https://www.boss.info/en/categories/bass",
            "https://www.boss.info/en/categories/drums",
            "https://www.boss.info/en/categories/accessories"
        ],
        "spec_sources": [
            "https://www.boss.info/en/support/downloads",
            "https://www.boss.info/en/support/manuals"
        ],
        "target_docs": 1000
    },
    "Roland": {
        "brand_id": 70,
        "support_centers": [
            "https://www.roland.com/support/",
            "https://www.roland.com/support/faqs/",
            "https://www.roland.com/support/knowledge-base/",
            "https://www.roland.com/support/tutorials/"
        ],
        "product_docs": [
            "https://www.roland.com/products/",
            "https://www.roland.com/categories/keyboards/",
            "https://www.roland.com/categories/drums/",
            "https://www.roland.com/categories/synthesizers/",
            "https://www.roland.com/categories/audio-interfaces/",
            "https://www.roland.com/categories/music-production/"
        ],
        "spec_sources": [
            "https://www.roland.com/support/downloads/",
            "https://www.roland.com/support/documentation/",
            "https://www.roland.com/support/manuals/"
        ],
        "target_docs": 1000
    },
    "Mackie": {
        "brand_id": 21,
        "support_centers": [
            "https://mackie.com/support",
            "https://mackie.com/en/support/faq",
            "https://mackie.com/en/support/knowledge-base",
            "https://mackie.com/en/support/tutorials"
        ],
        "product_docs": [
            "https://mackie.com/en/products",
            "https://mackie.com/en/products/mixers",
            "https://mackie.com/en/products/speakers",
            "https://mackie.com/en/products/interfaces",
            "https://mackie.com/en/products/monitors"
        ],
        "spec_sources": [
            "https://mackie.com/en/support/downloads",
            "https://mackie.com/en/support/documentation"
        ],
        "target_docs": 250
    },
    "PreSonus": {
        "brand_id": 69,
        "support_centers": [
            "https://www.presonus.com/en/support",
            "https://www.presonus.com/en/learn",
            "https://www.presonus.com/en/products"
        ],
        "product_docs": [
            "https://www.presonus.com/products",
            "https://www.presonus.com/en/products/recording",
            "https://www.presonus.com/en/products/mixing",
            "https://www.presonus.com/en/products/live-sound",
            "https://www.presonus.com/en/products/interfaces"
        ],
        "spec_sources": [
            "https://www.presonus.com/en/support/downloads",
            "https://www.presonus.com/en/support/knowledge-base"
        ],
        "target_docs": 280
    }
}

class ComprehensiveIngester:
    """Comprehensive brand documentation ingester"""
    
    def __init__(self):
        self.ingested_urls: Set[str] = set()
        self.processed_hashes: Set[str] = set()
        self.new_documents: Dict[str, int] = {}
        
    async def init_browser(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu'
            ]
        )
        # Create a context with a real user agent
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        logger.info("✅ Browser initialized with stealth settings")
        
    async def close_browser(self):
        """Close Playwright browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("✅ Browser closed")
    
    def get_content_hash(self, content: str) -> str:
        """Generate MD5 hash of content for deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def discover_urls_from_category(self, page: Page, category_url: str, max_urls: int = 100) -> Set[str]:
        """Discover URLs from a category/listing page"""
        discovered_urls = set()
        
        try:
            logger.info(f"  📍 Discovering from: {category_url}")
            try:
                await page.goto(category_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"    ⚠️  Timeout/Error loading {category_url}, attempting to scrape anyway: {e}")
            
            await asyncio.sleep(2)
            
            # Scroll to bottom to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            # Extract all links
            links = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(href => href && (
                            href.includes('/product') ||
                            href.includes('/support') ||
                            href.includes('/faq') ||
                            href.includes('/download') ||
                            href.includes('/manual') ||
                            href.includes('/documentation') ||
                            href.includes('/specification') ||
                            href.includes('/article')
                        ))
                        .slice(0, 150);
                }
            """)
            
            for link in links:
                if link and len(discovered_urls) < max_urls:
                    # Normalize URL
                    link = link.split('#')[0]  # Remove anchors
                    if link not in discovered_urls:
                        discovered_urls.add(link)
                        
        except asyncio.TimeoutError:
            logger.warning(f"    ⏱️  Timeout discovering from {category_url}")
        except Exception as e:
            logger.warning(f"    ⚠️  Error discovering from {category_url}: {str(e)[:100]}")
        
        return discovered_urls
    
    async def extract_content(self, page: Page, source_url: str) -> Tuple[str, str]:
        """Extract article content and metadata"""
        try:
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = ""
            for tag in ['h1', 'title', 'meta[property="og:title"]']:
                elem = soup.select_one(tag)
                if elem:
                    title = elem.get('content') or elem.get_text(strip=True)
                    if title:
                        break
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract body text
            body_text = ""
            
            # Priority: main content areas
            main_content = soup.find(['article', 'main', 'div.main-content', 'div.content'])
            if main_content:
                text_elements = main_content.find_all(['p', 'li', 'h2', 'h3', 'div'])
            else:
                text_elements = soup.find_all(['p', 'li', 'h2', 'h3', 'div'])
            
            for elem in text_elements:
                text = elem.get_text(strip=True)
                if len(text) > 30:
                    body_text += text + "\n"
            
            content = f"{title}\n\n{body_text}"
            
            # Limit content
            if len(content) > 8000:
                content = content[:8000]
            
            return title or "Untitled", content
            
        except Exception as e:
            logger.warning(f"    Error extracting content: {str(e)[:100]}")
            return "", ""
    
    async def ingest_from_urls(self, brand_name: str, brand_id: int, urls: Set[str], page: Page) -> int:
        """Ingest documents from a set of URLs"""
        ingested_count = 0
        
        # Load existing documents to avoid re-ingesting
        # Also load products for linking
        products_map = {} # name -> id
        with Session(engine) as session:
            existing = session.exec(
                select(Document).where(Document.brand_id == brand_id)
            ).all()
            self.ingested_urls = {doc.url for doc in existing if doc.url}
            self.processed_hashes = {doc.content_hash for doc in existing if doc.content_hash}
            
            # Load products
            products = session.exec(
                select(Product)
                .join(ProductFamily)
                .where(ProductFamily.brand_id == brand_id)
            ).all()
            for p in products:
                products_map[p.name.lower()] = p.id
        
        logger.info(f"  Found {len(self.ingested_urls)} existing documents for {brand_name}")
        logger.info(f"  Loaded {len(products_map)} products for linking")
        
        for idx, url in enumerate(urls):
            if url in self.ingested_urls:
                continue
            
            try:
                logger.info(f"  [{idx+1}/{len(urls)}] {url[:80]}...")
                await page.goto(url, wait_until="load", timeout=20000)
                await asyncio.sleep(0.5)
                
                title, content = await self.extract_content(page, url)
                
                if not title or len(content) < 100:
                    logger.info(f"      ⊘ Skipped (minimal content)")
                    continue
                
                # Check for duplicates
                content_hash = self.get_content_hash(content)
                if content_hash in self.processed_hashes:
                    logger.info(f"      ⊘ Duplicate content")
                    continue
                
                # Try to link to product
                product_id = None
                title_lower = title.lower()
                # Simple matching: if product name is in title
                # Sort products by length desc to match longest name first (e.g. "Boss GT-1000" vs "Boss GT-1")
                sorted_products = sorted(products_map.keys(), key=len, reverse=True)
                for p_name in sorted_products:
                    if p_name in title_lower:
                        product_id = products_map[p_name]
                        break

                # Store document
                with Session(engine) as session:
                    doc = Document(
                        brand_id=brand_id,
                        title=title[:200],
                        url=url,
                        content_hash=content_hash,
                        last_updated=datetime.utcnow(),
                        product_id=product_id
                    )
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
                            "brand_id": int(brand_id),
                            "doc_id": int(doc.id),
                            "product_id": product_id if product_id else 0
                        }
                    )
                except Exception as ve:
                    logger.error(f"      Vector DB error: {ve}")

                self.ingested_urls.add(url)
                self.processed_hashes.add(content_hash)
                ingested_count += 1
                
                # Update tracker with progress
                tracker.update_document_count(brand_name, ingested_count)
                
                logger.info(f"      ✅ Ingested ({ingested_count}) [Product: {product_id or 'None'}]")
                
                if ingested_count % 10 == 0:
                    await asyncio.sleep(2)  # Rate limiting
                
            except asyncio.TimeoutError:
                logger.info(f"      ⏱️  Timeout")
                continue
            except Exception as e:
                logger.info(f"      ⚠️  Error: {str(e)[:80]}")
                continue
        
        return ingested_count
    
    async def ingest_brand(self, brand_name: str, config: Dict):
        """Ingest all documentation types for a brand"""
        logger.info(f"\n{'=' * 70}")
        logger.info(f"📦 INGESTING: {brand_name}")
        logger.info(f"{'=' * 70}")
        logger.info(f"   Target: {config['target_docs']} documents")
        logger.info(f"   Categories: Support Centers + Product Docs + Specifications")
        
        # Update tracker
        tracker.update_brand_start(brand_name, config['brand_id'])
        
        # Use the context created in init_browser
        page = await self.context.new_page()
        page.set_default_timeout(60000)
        
        try:
            all_urls = set()
            
            # Discover from support centers
            logger.info(f"\n🆘 SUPPORT CENTERS ({len(config['support_centers'])} sources)")
            for support_url in config['support_centers'][:3]:
                urls = await self.discover_urls_from_category(page, support_url, max_urls=150)
                all_urls.update(urls)
                logger.info(f"     Found {len(urls)} URLs")
            
            # Discover from product documentation
            logger.info(f"\n📚 PRODUCT DOCUMENTATION ({len(config['product_docs'])} sources)")
            for prod_url in config['product_docs'][:5]:
                urls = await self.discover_urls_from_category(page, prod_url, max_urls=120)
                all_urls.update(urls)
                logger.info(f"     Found {len(urls)} URLs")
            
            # Discover from spec/download sources
            logger.info(f"\n📋 SPECIFICATIONS & DOWNLOADS ({len(config['spec_sources'])} sources)")
            for spec_url in config['spec_sources'][:3]:
                urls = await self.discover_urls_from_category(page, spec_url, max_urls=100)
                all_urls.update(urls)
                logger.info(f"     Found {len(urls)} URLs")
            
            logger.info(f"\n✅ Total unique URLs discovered: {len(all_urls)}")
            tracker.update_urls_discovered(brand_name, len(all_urls))
            
            # Ingest documents
            logger.info(f"\n🔄 INGESTING DOCUMENTS")
            ingested = await self.ingest_from_urls(
                brand_name,
                config['brand_id'],
                all_urls,
                page
            )
            
            self.new_documents[brand_name] = ingested
            logger.info(f"\n✅ {brand_name}: {ingested} new documents ingested")
            
            # Update tracker with completion
            tracker.update_brand_complete(brand_name, ingested)
            tracker.update_document_count(brand_name, ingested)
            
        except Exception as e:
            logger.error(f"❌ Error ingesting {brand_name}: {e}")
            tracker.add_error(f"{brand_name}: {str(e)}")
        finally:
            await page.close()
    
    async def run(self, target_brand: str = None):
        """Run comprehensive ingestion for all brands or a specific brand"""
        logger.info(f"\n{'=' * 70}")
        logger.info("🚀 COMPREHENSIVE BRAND DOCUMENTATION INGESTION")
        logger.info("Ingesting: Support Centers + Products + Specifications")
        if target_brand:
            logger.info(f"Target Brand: {target_brand}")
        logger.info(f"{'=' * 70}\n")
        
        # Start tracker
        tracker.start()
        
        await self.init_browser()
        
        try:
            brands_to_process = COMPREHENSIVE_BRAND_CONFIGS.items()
            if target_brand:
                if target_brand in COMPREHENSIVE_BRAND_CONFIGS:
                    brands_to_process = [(target_brand, COMPREHENSIVE_BRAND_CONFIGS[target_brand])]
                else:
                    logger.error(f"Brand {target_brand} not found in configuration")
                    return

            for brand_name, config in brands_to_process:
                await self.ingest_brand(brand_name, config)
                await asyncio.sleep(2)  # Pause between brands
            
            # Summary
            logger.info(f"\n{'=' * 70}")
            logger.info("📊 INGESTION SUMMARY")
            logger.info(f"{'=' * 70}")
            
            total_new = 0
            for brand, count in self.new_documents.items():
                logger.info(f"  {brand:15s}: {count:3d} new documents")
                total_new += count
            
            logger.info(f"  {'─' * 40}")
            logger.info(f"  Total Ingested:   {total_new} documents")
            
            # Get total database count
            with Session(engine) as session:
                total_docs = len(session.exec(select(Document)).all())
                logger.info(f"  Database Total:   {total_docs} documents")
            
            logger.info(f"{'=' * 70}\n")
            logger.info("✅ COMPREHENSIVE INGESTION COMPLETE")
            
            # Mark tracker as complete ONLY if running full suite
            if not target_brand:
                tracker.complete()
            
        finally:
            await self.close_browser()

async def main():
    """Main entry point"""
    import sys
    target_brand = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        ingester = ComprehensiveIngester()
        await ingester.run(target_brand)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Ingestion interrupted by user")
        tracker.add_error("Ingestion interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        tracker.add_error(f"Fatal error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
