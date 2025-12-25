
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Deep-Discovery")

async def discover_more():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Start with a known product page
        start_url = "https://www.allen-heath.com/hardware/sq/sq-5/"
        logger.info(f"Visiting {start_url}")
        
        try:
            await page.goto(start_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            # Look for any links that look like products
            links = await page.query_selector_all("a")
            logger.info(f"Found {len(links)} links on page")
            
            product_links = set()
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    if not href.startswith('http'):
                        href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                    href = href.split('#')[0].split('?')[0].rstrip('/')
                    
                    if "/hardware/" in href and len(href.split('/')) > 5:
                        product_links.add(href)
            
            logger.info(f"Found {len(product_links)} potential product links")
            for url in sorted(list(product_links)):
                print(url)
                
        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path="ah_discovery_fail.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_more())
