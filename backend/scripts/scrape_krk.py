#!/usr/bin/env python3
"""
KRK Systems Official Documentation Scraper
Scrapes official product documentation from krkmusic.com
"""
import asyncio
import logging
import sys
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from sqlmodel import Session, select

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand, Product, Document
from app.services.rag_service import ingest_document
from app.services.ingestion_tracker import tracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class KRKScraper:
    def __init__(self):
        self.base_url = "https://www.krkmusic.com"
        self.brand_name = "Krk Systems"
        self.brand_id = None
        self.product_urls = []
        self.ingested_count = 0
        
    async def run(self):
        """Main scraping workflow"""
        logger.info(f"Starting KRK Systems official documentation scrape")
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
                # Step 1: Discover product pages
                await self.discover_products(page)
                
                # Step 2: Scrape each product page
                for product_url in self.product_urls:
                    await self.scrape_product(page, product_url)
                
                logger.info(f"✅ KRK scrape complete! Ingested {self.ingested_count} documents")
                tracker.complete(self.brand_name)
                
            except Exception as e:
                logger.error(f"Error during KRK scrape: {e}", exc_info=True)
            finally:
                await browser.close()
    
    async def discover_products(self, page):
        """Discover all KRK products"""
        logger.info("Discovering KRK products...")
        tracker.update_step("Discovering products", self.brand_name)
        
        products_page = f"{self.base_url}/products"
        
        try:
            await page.goto(products_page, wait_until='domcontentloaded', timeout=30000)
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
                
                # Skip collections/categories - only individual products
                if any(skip in href.lower() for skip in ['/collections/', 'category', 'accessories', 'cables']):
                    continue
                
                # Must have specific product model pattern
                if '/products/' in href and href != f"{self.base_url}/products" and href != f"{self.base_url}/products/":
                    if href not in self.product_urls:
                        self.product_urls.append(href)
            
            logger.info(f"Found {len(self.product_urls)} product pages")
            tracker.update_urls_discovered(self.brand_name, len(self.product_urls))
            
        except Exception as e:
            logger.error(f"Error discovering products: {e}")
    
    async def scrape_product(self, page, product_url):
        """Scrape a single product page"""
        logger.info(f"Scraping: {product_url}")
        
        try:
            await page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(1500)
            
            # Extract product name
            product_name = await page.title()
            product_name = re.sub(r'\s*[\|–-].*$', '', product_name).strip()
            
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
            
            # Extract page content
            content_areas = [
                "main",
                ".product-description",
                ".product-details",
                ".specifications",
                ".features",
                "article"
            ]
            
            content_parts = []
            for selector in content_areas:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.text_content()
                    if text and len(text.strip()) > 50:
                        content_parts.append(text.strip())
            
            if not content_parts:
                # Fallback: get all visible text
                body = await page.query_selector("body")
                if body:
                    content_parts = [await body.text_content()]
            
            full_content = "\n\n".join(content_parts)
            
            if len(full_content) < 100:
                logger.warning(f"Insufficient content for {product_name}")
                return
            
            # Ingest into RAG
            metadata = {
                "brand": self.brand_name,
                "product": product_name,
                "source_url": product_url,
                "doc_type": "product_page",
                "title": product_name
            }
            
            await ingest_document(
                content=full_content,
                metadata=metadata,
                document_id=f"krk_{product_id}_{product_url.split('/')[-1]}"
            )
            
            self.ingested_count += 1
            logger.info(f"✅ Ingested: {product_name}")
            tracker.update_urls_ingested(self.brand_name, self.ingested_count)
            
            # Look for PDF downloads
            pdf_links = await page.query_selector_all("a[href$='.pdf']")
            for pdf_link in pdf_links:
                pdf_href = await pdf_link.get_attribute("href")
                if pdf_href:
                    await self.download_and_ingest_pdf(pdf_href, product_name, product_id)
            
        except Exception as e:
            logger.error(f"Error scraping {product_url}: {e}")
    
    async def download_and_ingest_pdf(self, pdf_url, product_name, product_id):
        """Download and ingest a PDF document"""
        # TODO: Implement PDF download and extraction
        logger.info(f"Found PDF: {pdf_url} for {product_name}")
        pass

async def main():
    scraper = KRKScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())
