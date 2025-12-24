#!/usr/bin/env python3
"""
Generic Brand Ingester
Crawls a brand's website to find product pages and ingests them into the RAG system.
"""

import asyncio
import logging
import sys
import hashlib
import re
import io
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
from sqlmodel import Session, select
from pypdf import PdfReader

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.models.sql_models import Brand, Product, ProductFamily, Document
from app.services.rag_service import ingest_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GenericIngester:
    def __init__(self, brand_name: str, base_url: str):
        self.brand_name = brand_name
        self.base_url = base_url
        self.visited_urls: Set[str] = set()
        self.product_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()
        self.brand_id = None
        
        with Session(engine) as session:
            brand = session.exec(select(Brand).where(Brand.name == brand_name)).first()
            if not brand:
                brand = Brand(name=brand_name, website_url=base_url)
                session.add(brand)
                session.commit()
                session.refresh(brand)
            self.brand_id = brand.id

    async def run(self):
        if not self.base_url:
            logger.error(f"No base URL for {self.brand_name}. Skipping.")
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            logger.info(f"Starting discovery for {self.brand_name} at {self.base_url}")
            await self.discover_products(page, self.base_url)
            
            logger.info(f"Found {len(self.product_urls)} potential product pages and {len(self.pdf_urls)} PDFs for {self.brand_name}")
            
            # Limit to 50 products for generic ingestion
            to_process = list(self.product_urls)[:50]
            for url in to_process:
                try:
                    await self.ingest_product_page(page, url)
                except Exception as e:
                    logger.error(f"Error ingesting {url}: {e}")
            
            # Process PDFs
            for url in list(self.pdf_urls)[:20]:
                try:
                    await self.ingest_pdf(url)
                except Exception as e:
                    logger.error(f"Error ingesting PDF {url}: {e}")
            
            await browser.close()

    async def discover_products(self, page: Page, url: str):
        """Simple discovery: look for links containing 'product', 'item', or in 'collections'"""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            links = await page.query_selector_all("a")
            for link in links:
                href = await link.get_attribute("href")
                if not href: continue
                href = href.strip()
                
                # Normalize URL
                if href.startswith("/"):
                    href = "/".join(url.split("/")[:3]) + href
                elif not href.startswith("http"):
                    continue
                
                # Stay on same domain
                if url.split("/")[2] not in href:
                    continue
                
                href = href.split("#")[0].split("?")[0]
                if href.endswith("/"): href = href[:-1]
                
                if href.lower().endswith(".pdf"):
                    self.pdf_urls.add(href)
                    continue

                if any(pattern in href.lower() for pattern in ["/product", "/item", "/p/", "/shop/", "/collections/"]):
                    if href not in self.product_urls:
                        self.product_urls.add(href)
                        if len(self.product_urls) >= 100: break # Cap discovery
        except Exception as e:
            logger.error(f"Discovery error at {url}: {e}")

    async def ingest_pdf(self, url: str):
        logger.info(f"Ingesting PDF: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download PDF: {url}")
                    return
                
                data = await response.read()
                pdf_file = io.BytesIO(data)
                reader = PdfReader(pdf_file)
                
                text_content = ""
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if len(text_content) < 200:
                    logger.warning(f"PDF content too short for {url}, skipping.")
                    return
                
                title = url.split("/")[-1]
                await self._save_document(url, title, text_content, "pdf_manual")

    async def ingest_product_page(self, page: Page, url: str):
        logger.info(f"Ingesting: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Clean up
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
            
        title = soup.title.string if soup.title else url.split("/")[-1]
        text_content = soup.get_text(separator="\n", strip=True)
        
        if len(text_content) < 200:
            logger.warning(f"Content too short for {url}, skipping.")
            return

        await self._save_document(url, title, text_content, "product_page")

    async def _save_document(self, url: str, title: str, text_content: str, doc_type: str):
        content_hash = hashlib.md5(text_content.encode()).hexdigest()
        
        with Session(engine) as session:
            # Check if already exists
            existing = session.exec(select(Document).where(Document.url == url)).first()
            if existing and existing.content_hash == content_hash:
                logger.info(f"Already ingested and unchanged: {url}")
                return
            
            # Create or update product
            product_name = title.split("|")[0].split("-")[0].strip()
            # Try to find product by name
            product = session.exec(select(Product).where(Product.name == product_name, Product.family_id.in_(
                select(ProductFamily.id).where(ProductFamily.brand_id == self.brand_id)
            ))).first()
            
            if not product:
                # Get or create family
                family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == self.brand_id)).first()
                if not family:
                    family = ProductFamily(name="General", brand_id=self.brand_id)
                    session.add(family)
                    session.commit()
                    session.refresh(family)
                
                product = Product(name=product_name, family_id=family.id)
                session.add(product)
                session.commit()
                session.refresh(product)

            if existing:
                existing.title = title
                existing.content_hash = content_hash
                existing.last_updated = datetime.now()
                doc = existing
            else:
                doc = Document(
                    title=title,
                    url=url,
                    content_hash=content_hash,
                    brand_id=self.brand_id,
                    product_id=product.id,
                    last_updated=datetime.now()
                )
                session.add(doc)
            
            session.commit()
            session.refresh(doc)
            
            # RAG Ingestion
            try:
                await ingest_document(
                    text=text_content,
                    metadata={
                        "source": url,
                        "title": title,
                        "brand": self.brand_name,
                        "product": product_name,
                        "type": doc_type
                    }
                )
                logger.info(f"✅ RAG Ingested: {title} ({doc_type})")
            except Exception as e:
                logger.error(f"RAG error for {url}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_generic_brand.py <BrandName> [BaseURL]")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    base_url = sys.argv[2] if len(sys.argv) > 2 else ""
    
    ingester = GenericIngester(brand_name, base_url)
    asyncio.run(ingester.run())
