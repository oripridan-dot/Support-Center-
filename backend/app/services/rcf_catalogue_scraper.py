import asyncio
from playwright.async_api import async_playwright
import logging
from .rag_service import ingest_document
from ..core.database import Session, engine
from ..models.sql_models import Brand, Product, ProductFamily, Document
from sqlmodel import select
import datetime
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RCFCatalogueScraper:
    def __init__(self):
        self.base_url = "https://www.halilit.com"
        self.start_url = "https://www.halilit.com/g/5193-%D7%99%D7%A6%D7%A8%D7%9F/33208-Rcf"

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            with Session(engine) as session:
                brand = session.exec(select(Brand).where(Brand.name.ilike('%rcf%'))).first()
                if not brand:
                    logger.error("RCF brand not found in DB.")
                    return

                page = await context.new_page()
                logger.info(f"Starting RCF catalogue scrape from {self.start_url}")
                
                try:
                    await page.goto(self.start_url, wait_until='networkidle', timeout=90000)
                    
                    # Scroll down multiple times to load all products
                    last_height = await page.evaluate("document.body.scrollHeight")
                    for i in range(20):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                        logger.info(f"Scrolled {i+1} times...")
                    
                    # Find all product links
                    product_links = set()
                    links = await page.query_selector_all("a")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and '/items/' in href:
                            href = href.strip()
                            if not href.startswith('http'):
                                href = self.base_url + href
                            product_links.add(href)
                    
                    logger.info(f"Found {len(product_links)} unique RCF products")

                    # Scrape each product
                    for i, url in enumerate(list(product_links)):
                        # Check if already ingested
                        existing_doc = session.exec(select(Document).where(Document.url == url)).first()
                        if existing_doc:
                            logger.info(f"[{i+1}/{len(product_links)}] Skipping already ingested: {url}")
                            continue

                        logger.info(f"[{i+1}/{len(product_links)}] Processing RCF product: {url}")
                        try:
                            await self.scrape_product(page, url, brand, session)
                        except Exception as e:
                            logger.error(f"Error processing product {url}: {e}")
                            
                finally:
                    await page.close()
            
            await browser.close()

    async def scrape_product(self, page, url, brand, session):
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Extract name
        name_el = await page.query_selector("h1")
        if name_el:
            name = await name_el.inner_text()
        else:
            name = url.split('/')[-1].replace('-', ' ').title()
        
        name = name.strip()
        if not name: return

        # Check if product exists
        product = session.exec(select(Product).where(Product.name == name)).first()
        if not product:
            family_name = "RCF Products"
            family = session.exec(select(ProductFamily).where(ProductFamily.name == family_name, ProductFamily.brand_id == brand.id)).first()
            if not family:
                family = ProductFamily(name=family_name, brand_id=brand.id)
                session.add(family)
                session.commit()
                session.refresh(family)
            
            product = Product(name=name, family_id=family.id)
            session.add(product)
            session.commit()
            session.refresh(product)

        # Extract images
        images = await page.query_selector_all("img")
        image_urls = []
        for img in images:
            src = await img.get_attribute("src")
            alt = await img.get_attribute("alt") or ""
            if src and not src.startswith('data:') and (len(alt) > 3 or 'product' in src.lower()):
                src = src.strip()
                if not src.startswith('http'):
                    src = self.base_url + (src if src.startswith('/') else '/' + src)
                image_urls.append({"url": src, "alt": alt})
        
        # Extract PDFs
        links = await page.query_selector_all("a")
        pdf_links = []
        for link in links:
            href = await link.get_attribute("href")
            text = await link.inner_text()
            if href and href.lower().endswith('.pdf'):
                href = href.strip()
                if not href.startswith('http'):
                    href = self.base_url + (href if href.startswith('/') else '/' + href)
                pdf_links.append({"url": href, "title": text.strip() or "PDF Document"})

        # Extract text
        text = await page.evaluate("() => document.body.innerText")
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 20]
        clean_text = "\n".join(lines)

        # Ingest into RAG
        await ingest_document(clean_text, {
            "brand_id": brand.id,
            "product_id": product.id,
            "url": url,
            "source": "halilit_website",
            "images": json.dumps(image_urls[:10]),
            "pdfs": json.dumps(pdf_links[:10]),
            "image_url": image_urls[0]['url'] if image_urls else None
        })
        
        # Save document record
        doc = Document(
            title=f"Halilit Product: {name}",
            url=url,
            brand_id=brand.id,
            product_id=product.id,
            last_updated=datetime.datetime.now()
        )
        session.add(doc)
        session.commit()
        logger.info(f"Successfully ingested {name}")

if __name__ == "__main__":
    scraper = RCFCatalogueScraper()
    asyncio.run(scraper.run())
