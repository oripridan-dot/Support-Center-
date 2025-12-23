
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Discovery")

async def discover_ah():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        logger.info("Visiting hardware page...")
        await page.goto("https://www.allen-heath.com/hardware/", wait_until='domcontentloaded', timeout=60000)
        
        # Scroll down multiple times to trigger lazy loading
        for _ in range(5):
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)
        
        await page.screenshot(path="ah_hardware_debug_scrolled.png")
        
        # Find all links
        links = await page.query_selector_all("a")
        logger.info(f"Found {len(links)} total links on page after scrolling")
        for link in links:
            href = await link.get_attribute("href")
            if href and "/hardware/" in href:
                if not href.startswith('http'):
                    href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                href = href.split('#')[0].split('?')[0].rstrip('/')
                # Categories usually have fewer segments than products
                if len(href.split('/')) <= 5:
                    category_links.add(href)
        
        logger.info(f"Found {len(category_links)} potential category links")
        
        product_links = set()
        for cat_url in sorted(list(category_links)):
            logger.info(f"Checking category: {cat_url}")
            try:
                await page.goto(cat_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                cat_links = await page.query_selector_all("a")
                for link in cat_links:
                    href = await link.get_attribute("href")
                    if href:
                        if not href.startswith('http'):
                            href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                        href = href.split('#')[0].split('?')[0].rstrip('/')
                        
                        # Product links are usually deeper
                        if "/hardware/" in href and len(href.split('/')) > 5:
                            if not any(x in href for x in ['/resources/', '/processing-expansion/', '/all-models/', '/where-to-buy/']):
                                product_links.add(href)
            except Exception as e:
                logger.error(f"Error checking {cat_url}: {e}")
        
        logger.info(f"Total unique product links found: {len(product_links)}")
        with open("ah_discovered_links_v2.txt", "w") as f:
            for url in sorted(list(product_links)):
                f.write(url + "\n")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_ah())
