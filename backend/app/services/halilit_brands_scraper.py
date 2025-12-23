import asyncio
from playwright.async_api import async_playwright
import logging
from app.core.database import Session, engine
from app.models.sql_models import Brand
from sqlmodel import select
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_halilit_brands():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.halilit.com/pages/4367', wait_until='networkidle')
        
        elements = await page.query_selector_all('a')
        brands_data = []
        for el in elements:
            href = await el.get_attribute('href')
            if href and ('/g/' in href or '../g/' in href):
                img = await el.query_selector('img')
                if img:
                    logo = await img.get_attribute('src')
                    # Extract brand name from URL
                    # Example: https://www.halilit.com/g/5193-Brand/207910-ADAM-Audio
                    # Example: ../g/5193-%D7%99%D7%A6%D7%A8%D7%9F/33123-Esp
                    match = re.search(r'/(\d+)-([^/]+)$', href.strip())
                    if match:
                        brand_slug = match.group(2)
                        # Clean up slug
                        brand_name = brand_slug.replace('-', ' ').title()
                        
                        # Handle Hebrew encoded parts if any
                        if '%' in brand_name:
                            # It might be Hebrew, let's try to get it from alt if it's not generic
                            alt = await img.get_attribute('alt')
                            if alt and 'מותגים' not in alt:
                                brand_name = alt
                        
                        brands_data.append({
                            'name': brand_name,
                            'logo_url': logo.strip() if logo else None,
                            'website_url': href.strip() if href.startswith('http') else f"https://www.halilit.com{href.strip().replace('..', '')}"
                        })
        
        await browser.close()
        
        # Deduplicate by name
        unique_brands = {}
        for b in brands_data:
            if b['name'] not in unique_brands:
                unique_brands[b['name']] = b
        
        logger.info(f"Found {len(unique_brands)} unique brands")
        
        with Session(engine) as session:
            for name, data in unique_brands.items():
                # Check if exists
                existing = session.exec(select(Brand).where(Brand.name == name)).first()
                if not existing:
                    brand = Brand(
                        name=name,
                        logo_url=data['logo_url'],
                        website_url=data['website_url'],
                        description=f"Official partner of Halilit.",
                        primary_color="#000000",
                        secondary_color="#ffffff"
                    )
                    session.add(brand)
                    logger.info(f"Added brand: {name}")
                else:
                    existing.logo_url = data['logo_url']
                    existing.website_url = data['website_url']
                    session.add(existing)
                    logger.info(f"Updated brand: {name}")
            
            session.commit()

if __name__ == "__main__":
    asyncio.run(scrape_halilit_brands())
