#!/usr/bin/env python3
"""
Ingest all Halilit brand documentation
This script runs comprehensive scraping and ingestion for all Halilit partner brands
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.sql_models import Brand, Product, ProductFamily, Document
from app.services.scraper_service import BrandScraper
from app.services.rag_service import ingest_document
from app.services.ingestion_tracker import tracker
from sqlmodel import select
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Priority brands (already have some data or high importance)
PRIORITY_BRANDS = [
    "Mackie",
    " Eaw Eastern Acoustic Works ",
    "Boss",
    "Adam Audio",
    "Krk Systems", 
    "Roland",
    "Nord",
    "Allen & Heath",
    "Presonus",
    "Universal Audio",
    "Warm Audio",
    "Avid",
    "Steinberg",
    "Eve Audio"
]

async def scrape_brand_products(brand: Brand, max_products: int = 1000):
    """
    Scrape products from a brand's Halilit page
    """
    products_found = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Use a more realistic user agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            logger.info(f"Loading {brand.website_url}")
            tracker.update_step(f"Loading brand page for {brand.name}", brand.name)
            
            # Try multiple wait conditions for better reliability
            try:
                await page.goto(brand.website_url, wait_until='networkidle', timeout=45000)
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for networkidle on {brand.name}, trying domcontentloaded")
                await page.goto(brand.website_url, wait_until='domcontentloaded', timeout=30000)
            
            # Scroll to ensure all products are loaded if it's a lazy-loading page
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            # Find product links - be more permissive with selectors
            product_links = await page.query_selector_all('a[href*="/items/"]')
            
            if not product_links:
                # Try alternative selector if the first one fails
                product_links = await page.query_selector_all('.product-item a, .item-name a')

            logger.info(f"Found {len(product_links)} potential product links for {brand.name}")
            tracker.update_urls_discovered(brand.name, len(product_links))
            
            for i, link in enumerate(product_links[:max_products]):
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue
                    
                    href = href.strip()
                    text = await link.text_content()
                    product_name = text.strip() if text and text.strip() else ""
                    
                    # If name is empty, try to get it from an image alt or title attribute
                    if not product_name:
                        product_name = await link.get_attribute('title') or ""
                    
                    if not product_name:
                        # Try to extract from URL as last resort
                        product_name = href.split('/')[-1].replace('-', ' ').title()

                    # Clean product name
                    product_name = product_name.replace('\n', ' ').replace('\t', ' ').strip()
                    
                    if not product_name or len(product_name) < 2:
                        continue
                    
                    # Build full URL
                    if href.startswith('http'):
                        full_url = href
                    else:
                        href = href.lstrip('/')
                        full_url = f"https://www.halilit.com/{href}"
                    
                    products_found.append({
                        'name': product_name,
                        'url': full_url,
                        'brand_id': brand.id
                    })
                    
                except Exception as e:
                    logger.debug(f"Error processing link {i}: {e}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping products for {brand.name}: {e}")
    
    # Deduplicate by URL
    seen_urls = set()
    unique_products = []
    for product in products_found:
        if product['url'] not in seen_urls:
            seen_urls.add(product['url'])
            unique_products.append(product)
    
    tracker.update_urls_discovered(brand.name, len(unique_products))
    return unique_products

async def ingest_product_page(product_info: dict, brand: Brand, current_idx: int, total_count: int):
    """
    Scrape and ingest a single product page
    """
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # Less strict timeout and wait condition
                try:
                    await page.goto(product_info['url'], wait_until='domcontentloaded', timeout=40000)
                except PlaywrightTimeoutError:
                    if attempt < max_retries:
                        logger.warning(f"  Retrying {product_info['name']} (Attempt {attempt+1})")
                        await browser.close()
                        continue
                    else:
                        raise

                # Wait a bit for dynamic content
                await asyncio.sleep(2)
                
                # Extract content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Be LESS strict about what we remove - keep more context
                # Only remove very obvious non-content
                for element in soup(['script', 'style', 'iframe', 'svg']):
                    element.decompose()
                
                # Try to find the main content area to reduce noise, but fall back to body
                main_content = soup.find('main') or soup.find('article') or soup.find('.product-details') or soup.body
                
                if main_content:
                    text_content = main_content.get_text(separator='\n', strip=True)
                else:
                    text_content = soup.get_text(separator='\n', strip=True)
                
                # --- STRICT VALIDATION BEFORE DB WRITE ---
                if len(text_content) < 200:
                    logger.warning(f"  ⚠️ Content too short for {product_info['name']} ({len(text_content)} chars), skipping")
                    await browser.close()
                    return False
                
                # Clean up the name - sometimes it has "Price" or other junk
                # Remove common Hebrew junk and price symbols
                clean_name = product_info['name']
                for junk in ['₪', 'מחיר', 'הוספה לסל', 'Price', 'Add to cart']:
                    clean_name = clean_name.split(junk)[0]
                
                clean_name = clean_name.strip()
                
                # If name is too short or just numbers, it's probably junk
                if not clean_name or len(clean_name) < 3 or clean_name.isdigit():
                    logger.warning(f"  ⚠️ Invalid product name '{clean_name}', skipping")
                    await browser.close()
                    return False

                # Create content hash for deduplication
                content_hash = hashlib.md5(text_content.encode()).hexdigest()
                
                # Check if already ingested
                session = next(get_session())
                existing = session.exec(
                    select(Document).where(
                        Document.url == product_info['url'],
                        Document.brand_id == brand.id
                    )
                ).first()
                
                if existing and existing.content_hash == content_hash:
                    logger.debug(f"  ⏭️ Already indexed: {clean_name}")
                    tracker.update_urls(total_count, current_idx)
                    await browser.close()
                    return False
                
                # Ingest into vector DB
                metadata = {
                    "source": product_info['url'],
                    "brand": brand.name,
                    "brand_id": brand.id,
                    "product": clean_name,
                    "type": "product_page",
                    "title": clean_name,
                    "ingested_at": datetime.now().isoformat()
                }
                
                chunks_count = await ingest_document(text_content, metadata)
                logger.info(f"  ✓ Ingested: {clean_name} ({chunks_count} chunks)")
                
                # Update or create document record
                if existing:
                    existing.content_hash = content_hash
                    existing.last_updated = datetime.now()
                    existing.title = clean_name
                    session.add(existing)
                else:
                    doc = Document(
                        title=clean_name,
                        url=product_info['url'],
                        content_hash=content_hash,
                        brand_id=brand.id,
                        last_updated=datetime.now()
                    )
                    session.add(doc)
                
                session.commit()
                tracker.update_urls(total_count, current_idx)
                await browser.close()
                return True
                
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"  Error ingesting {product_info['name']}, retrying: {e}")
                await asyncio.sleep(2)
            else:
                logger.error(f"  ✗ Final error ingesting {product_info['name']}: {e}")
                return False
    return False

async def ingest_brand(brand: Brand, priority: bool = False):
    """
    Ingest a single brand's documentation
    """
    logger.info(f"{'[PRIORITY] ' if priority else ''}Starting ingestion for: {brand.name}")
    tracker.update_brand_start(brand.name, brand.id)
    
    try:
        # Increase product limit for brand-by-brand
        max_products = 2000 if priority else 1000
        
        # Scrape product list
        products = await scrape_brand_products(brand, max_products)
        logger.info(f"  Found {len(products)} products for {brand.name}")
        
        if not products:
            logger.warning(f"  No products found for {brand.name}")
            tracker.update_step(f"No products found for {brand.name}", brand.name)
            return False
        
        # Ingest each product
        success_count = 0
        for i, product in enumerate(products, 1):
            logger.info(f"  [{i}/{len(products)}] {product['name']}")
            if await ingest_product_page(product, brand, i, len(products)):
                success_count += 1
            # Small delay between products
            await asyncio.sleep(0.3)
        
        logger.info(f"✓ Completed {brand.name}: {success_count}/{len(products)} products ingested")
        tracker.update_step(f"Completed {brand.name}: {success_count} products ingested", brand.name)
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to ingest {brand.name}: {e}")
        tracker.update_step(f"Failed to ingest {brand.name}: {str(e)}", brand.name)
        return False

async def main():
    """
    Main ingestion process
    """
    parser = argparse.ArgumentParser(description='Ingest Halilit brand documentation')
    parser.add_argument('--brand', type=str, help='Specific brand name to ingest')
    parser.add_argument('--limit', type=int, default=2000, help='Max products per brand')
    args = parser.parse_args()

    logger.info("="*80)
    logger.info("HALILIT BRANDS INGESTION")
    logger.info("="*80)
    
    tracker.start()
    session = next(get_session())
    
    if args.brand:
        statement = select(Brand).where(Brand.name.ilike(f"%{args.brand}%"))
        brands = session.exec(statement).all()
        if not brands:
            logger.error(f"Brand '{args.brand}' not found in database.")
            return
    else:
        statement = select(Brand).where(Brand.website_url.contains("halilit.com"))
        brands = session.exec(statement).all()
    
    logger.info(f"Processing {len(brands)} brands")
    
    # Sort brands: priority first, then by name
    brands.sort(key=lambda b: (b.name not in PRIORITY_BRANDS, b.name))
    
    success_count = 0
    fail_count = 0
    
    for i, brand in enumerate(brands, 1):
        logger.info(f"\n[{i}/{len(brands)}] Processing: {brand.name}")
        is_priority = brand.name in PRIORITY_BRANDS
        if await ingest_brand(brand, priority=is_priority):
            success_count += 1
        else:
            fail_count += 1
        
        await asyncio.sleep(1)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("INGESTION SUMMARY")
    logger.info("="*80)
    logger.info(f"Total brands: {len(brands)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("="*80)

if __name__ == "__main__":
    asyncio.run(main())

