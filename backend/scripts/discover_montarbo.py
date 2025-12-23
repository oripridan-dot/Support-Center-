import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def discover_montarbo_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        base_url = "https://www.montarbo.com/en/products"
        logger.info(f"Visiting {base_url}")
        await page.goto(base_url)
        
        # Wait for products to load
        await page.wait_for_timeout(5000)
        
        # Find all product links
        # Based on typical structure, they might be in a grid
        links = await page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors
                    .map(a => a.href)
                    .filter(href => href.includes('/en/products/') && !href.endsWith('/products'));
            }
        """)
        
        unique_links = sorted(list(set(links)))
        logger.info(f"Found {len(unique_links)} potential product links")
        
        with open("montarbo_links.txt", "w") as f:
            for link in unique_links:
                f.write(f"{link}\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_montarbo_links())
