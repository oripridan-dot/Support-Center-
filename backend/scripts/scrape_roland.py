#!/usr/bin/env python3
"""
Roland Official Documentation Scraper
Scrapes official product documentation from roland.com
"""
import asyncio
import logging
import sys
import re
from pathlib import Path
from playwright.async_api import async_playwright
from sqlmodel import Session, select

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand, Product
from app.services.rag_service import ingest_document
from app.services.ingestion_tracker import tracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class RolandScraper:
    def __init__(self):
        self.base_url = "https://www.roland.com"
        self.brand_name = "Roland"
        self.brand_id = None
        self.product_urls = set()
        self.ingested_count = 0
        
    async def run(self):
        """Main scraping workflow"""
        logger.info(f"Starting Roland official documentation scrape")
        tracker.start(self.brand_name)
        
        # Get brand from database
        with Session(engine) as session:
            brand = session.exec(
                select(Brand).where(Brand.name == self.brand_name)
            ).first()
            
            if not brand:
                logger.error(f"Brand {self.brand_name} not found in database")
                return
            
            self.brand_id = brand.id
            logger.info(f"Found brand: {brand.name} (ID: {brand.id})")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Discover products from multiple categories
                await self.discover_from_sitemap(page)
                
                logger.info(f"Total products discovered: {len(self.product_urls)}")
                tracker.update_urls_discovered(self.brand_name, len(self.product_urls))
                
                # Scrape each product (limit to first 100 for now)
                for i, product_url in enumerate(list(self.product_urls)[:100]):
                    logger.info(f"[{i+1}/{min(100, len(self.product_urls))}] {product_url}")
                    await self.scrape_product(page, product_url)
                
                logger.info(f"✅ Roland scrape complete! Ingested {self.ingested_count} documents")
                tracker.complete()
                
            except Exception as e:
                logger.error(f"Error during Roland scrape: {e}", exc_info=True)
            finally:
                await browser.close()
    
    async def discover_from_sitemap(self, page):
        """Discover products from Roland sitemap/categories"""
        logger.info("Discovering Roland products...")
        tracker.update_step("Discovering products", self.brand_name)
        
        # Key product categories
        categories = [
            "/global/products/synthesizers/",
            "/global/products/digital-pianos/",
            "/global/products/drum-machines/",
            "/global/products/electronic-drums/",
            "/global/products/guitar-amplifiers/",
            "/global/products/bass-amplifiers/",
            "/global/products/keyboard-amplifiers/",
            "/global/products/guitar-synthesizers/",
            "/global/products/samplers/",
            "/global/products/digital-recorders/",
            "/global/products/audio-interfaces/",
        ]
        
        for category in categories:
            try:
                url = f"{self.base_url}{category}"
                logger.info(f"Checking category: {category}")
                
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Find product links
                links = await page.query_selector_all("a[href*='/products/']")
                
                for link in links:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Make absolute URL
                    if not href.startswith('http'):
                        href = self.base_url + href
                    
                    # Skip category pages themselves
                    if any(skip in href for skip in ['/products/synthesizers/', '/products/digital-pianos/', '/products/drum-machines/']):
                        if href.count('/') <= 6:  # Category page (not specific product)
                            continue
                    
                    # Must be specific product page
                    if '/products/' in href and href not in self.product_urls:
                        # Product pages typically have model names
                        if re.search(r'/[a-z]{2,10}[-_]?\d+[a-z]*/?$', href, re.IGNORECASE):
                            self.product_urls.add(href)
                
                logger.info(f"Found {len(self.product_urls)} products so far")
                
            except Exception as e:
                logger.error(f"Error discovering category {category}: {e}")
    
    async def scrape_product(self, page, product_url):
        """Scrape a single product page"""
        try:
            await page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1500)
            
            # Extract product name
            title_elem = await page.query_selector("h1, .product-title, .product-name")
            if title_elem:
                product_name = await title_elem.text_content()
                product_name = product_name.strip()
            else:
                product_name = product_url.split('/')[-2] if product_url.endswith('/') else product_url.split('/')[-1]
            
            # Get or create product
            with Session(engine) as session:
                product = session.exec(
                    select(Product).where(
                        Product.brand_id == self.brand_id,
                        Product.name == product_name
                    )
                ).first()
                
                if not product:
                    product = Product(
                        brand_id=self.brand_id,
                        name=product_name,
                        url=product_url
                    )
                    session.add(product)
                    session.commit()
                    session.refresh(product)
                
                product_id = product.id
            
            # Extract content
            content_selectors = [
                ".product-description",
                ".product-features",
                ".specifications",
                ".overview",
                "article",
                "main"
            ]
            
            content_parts = []
            for selector in content_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and len(text.strip()) > 100:
                        content_parts.append(text.strip())
            
            if not content_parts:
                # Fallback: get main content
                main = await page.query_selector("main, body")
                if main:
                    text = await main.text_content()
                    content_parts = [text]
            
            full_content = "\n\n".join(content_parts)
            
            if len(full_content) < 200:
                logger.warning(f"Insufficient content for {product_name}")
                return
            
            # Ingest into RAG
            metadata = {
                "brand": self.brand_name,
                "product": product_name,
                "source_url": product_url,
                "doc_type": "product_page",
                "title": f"{product_name} - Roland"
            }
            
            await ingest_document(
                content=full_content,
                metadata=metadata,
                document_id=f"roland_{product_id}_{product_name.replace(' ', '_').lower()}"
            )
            
            self.ingested_count += 1
            logger.info(f"✅ [{self.ingested_count}] Ingested: {product_name}")
            tracker.update_urls_ingested(self.brand_name, self.ingested_count)
            
        except Exception as e:
            logger.error(f"Error scraping {product_url}: {e}")

async def main():
    scraper = RolandScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
