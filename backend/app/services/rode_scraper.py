import asyncio
from playwright.async_api import async_playwright
import logging
from .rag_service import ingest_document
from ..core.database import Session, engine
from ..models.sql_models import Brand, Product, ProductFamily, Document
from sqlmodel import select
import datetime

logger = logging.getLogger(__name__)

class RodeScraper:
    def __init__(self):
        self.base_url = "https://rode.com/en/user-guides"
        self.brand_name = "Rode"

    async def run(self):
        logger.info(f"Starting Rode scraper")
        
        with Session(engine) as session:
            brand = session.exec(select(Brand).where(Brand.name == self.brand_name)).first()
            if not brand:
                logger.error("Rode brand not found in DB")
                return

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
                page = await context.new_page()
                await page.goto(self.base_url, wait_until='networkidle')
                
                # Find all user guide links
                links = await page.query_selector_all("a")
                guide_links = []
                for link in links:
                    href = await link.get_attribute("href")
                    if href and '/user-guides/' in href:
                        guide_links.append(href)
                
                # Remove duplicates
                guide_links = list(set(guide_links))
                logger.info(f"Found {len(guide_links)} guide links")
                
                for full_url in guide_links[:20]: # Increased limit
                    name = full_url.split('/')[-1].replace('-', ' ').title()
                    
                    # Check if document already exists
                    product = session.exec(select(Product).where(Product.name == name)).first()
                    if product:
                        doc = session.exec(select(Document).where(Document.product_id == product.id)).first()
                        if doc:
                            logger.info(f"Document for {name} already exists, skipping")
                            continue

                    logger.info(f"Processing product: {name} at {full_url}")
                    if not product:
                        family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == brand.id)).first()
                        if not family:
                            family = ProductFamily(name="General", brand_id=brand.id)
                            session.add(family)
                            session.commit()
                            session.refresh(family)
                        
                        product = Product(name=name, family_id=family.id)
                        session.add(product)
                        session.commit()
                        session.refresh(product)

                    # Scrape the product guide page
                    await self.scrape_guide_page(page, full_url, brand.id, product.id)
                
                await browser.close()

    async def scrape_guide_page(self, page, url, brand_id, product_id):
        try:
            await page.goto(url, timeout=60000)
            
            # Extract main product image if available
            product_image = await page.get_attribute("img.product-image, img[alt*='Product'], .hero img", "src")
            if product_image and not product_image.startswith('http'):
                product_image = "https://rode.com" + product_image

            # Extract all images with their alt text
            images = await page.query_selector_all("img")
            image_data = []
            for img in images:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                if src and not src.startswith('data:') and (alt or 'guide' in src.lower()):
                    if not src.startswith('http'):
                        src = "https://rode.com" + src
                    image_data.append({"url": src, "alt": alt or ""})

            # Extract text content from the guide
            # We'll try to keep some structure
            content_elements = await page.query_selector_all("h1, h2, h3, p, li")
            structured_content = []
            for el in content_elements:
                text = await el.inner_text()
                if text.strip():
                    structured_content.append(text.strip())
            
            full_text = "\n\n".join(structured_content)
            
            # Ingest into RAG
            # We'll attach the product image to all chunks for this product
            await ingest_document(full_text, {
                "brand_id": brand_id,
                "product_id": product_id,
                "url": url,
                "source": "official_guide",
                "image_url": product_image or (image_data[0]['url'] if image_data else None)
            })
            
            # Save document record in DB
            with Session(engine) as session:
                doc = Document(
                    title=f"User Guide: {url.split('/')[-1]}",
                    url=url,
                    brand_id=brand_id,
                    product_id=product_id,
                    last_updated=datetime.datetime.now()
                )
                session.add(doc)
                session.commit()
                
            logger.info(f"Successfully ingested guide for product {product_id}")
            
        except Exception as e:
            logger.error(f"Error scraping guide page {url}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = RodeScraper()
    asyncio.run(scraper.run())
