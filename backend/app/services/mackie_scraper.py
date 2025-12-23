
import asyncio
import json
import os
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from ..core.database import Session, engine
from ..models.sql_models import Brand, Product, ProductFamily, Document
from .rag_service import ingest_document
from sqlmodel import select

class MackieScraper:
    def __init__(self):
        self.base_url = "https://mackie.com"

    async def get_product_links(self, page) -> List[str]:
        print("Fetching product links from Mackie...")
        await page.goto(f"{self.base_url}/en/products", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) # Wait for JS to render links
        
        # Extract all links
        links = await page.eval_on_selector_all('a', 'elements => elements.map(e => e.href)')
        
        # Filter for product links
        # Mackie product links usually look like /en/products/category/product-name
        # or /intl/products/...
        product_links = []
        for link in links:
            if '/products/' in link and not link.endswith('/products') and not link.endswith('/products/'):
                # Avoid category-only links if possible, but Mackie often has products at the end
                if any(x in link for x in ['mixers', 'loudspeakers', 'studio-monitoring', 'microphones', 'headphones']):
                    product_links.append(link)
        
        return list(set(product_links))

    async def scrape_product(self, page, url: str, brand: Brand, session: Session):
        print(f"Scraping Mackie product: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Extract product name
            name_elem = await page.query_selector('h1')
            name = await name_elem.inner_text() if name_elem else url.split('/')[-1].replace('-', ' ').title()
            
            # Extract description
            desc_elem = await page.query_selector('.product-description, .overview-content, .description')
            description = await desc_elem.inner_text() if desc_elem else ""
            
            # Extract image
            img_elem = await page.query_selector('.product-image img, .main-image img')
            image_url = await img_elem.get_attribute('src') if img_elem else None
            if image_url and not image_url.startswith('http'):
                image_url = self.base_url + image_url

            # Extract specs/features
            specs_content = ""
            specs_elem = await page.query_selector('.specs-content, .features-content, #specifications')
            if specs_elem:
                specs_content = await specs_elem.inner_text()
            else:
                # Fallback: get all text from the main content area
                main_content = await page.query_selector('main')
                if main_content:
                    specs_content = await main_content.inner_text()

            # Create or get product family (use category from URL)
            family_name = "Mackie Products"
            parts = url.split('/')
            if 'products' in parts:
                idx = parts.index('products')
                if len(parts) > idx + 1:
                    family_name = parts[idx+1].replace('-', ' ').title()

            family = session.exec(select(ProductFamily).where(ProductFamily.name == family_name, ProductFamily.brand_id == brand.id)).first()
            if not family:
                family = ProductFamily(name=family_name, brand_id=brand.id)
                session.add(family)
                session.commit()
                session.refresh(family)

            # Create or update product
            product = session.exec(select(Product).where(Product.name == name, Product.family_id == family.id)).first()
            if not product:
                product = Product(name=name, description=description, image_url=image_url, family_id=family.id)
                session.add(product)
                session.commit()
                session.refresh(product)

            # Ingest into RAG
            content = f"Product: {name}\nBrand: Mackie\nCategory: {family_name}\n\nDescription:\n{description}\n\nSpecifications/Features:\n{specs_content}"
            
            # Check if document already exists
            doc = session.exec(select(Document).where(Document.url == url)).first()
            if not doc:
                doc = Document(title=f"Mackie Product: {name}", url=url, brand_id=brand.id, product_id=product.id)
                session.add(doc)
                session.commit()
            
            await ingest_document(content, {"source": url, "brand": "Mackie", "product": name, "type": "product_page"})
            print(f"Successfully ingested {name}")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            with Session(engine) as session:
                brand = session.exec(select(Brand).where(Brand.name.ilike('%mackie%'))).first()
                if not brand:
                    brand = Brand(name="Mackie", website_url="https://mackie.com", primary_color="#000000", secondary_color="#ffffff")
                    session.add(brand)
                    session.commit()
                    session.refresh(brand)

                links = await self.get_product_links(page)
                print(f"Found {len(links)} potential product links")
                
                # Limit to first 50 for testing
                for link in links[:50]:
                    await self.scrape_product(page, link, brand, session)
            
            await browser.close()

if __name__ == "__main__":
    scraper = MackieScraper()
    asyncio.run(scraper.run())
