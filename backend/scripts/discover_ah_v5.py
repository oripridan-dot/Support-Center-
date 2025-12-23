
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AH-Discovery-V5")

categories = [
    "https://www.allen-heath.com/hardware/avantis/",
    "https://www.allen-heath.com/hardware/ahm/",
    "https://www.allen-heath.com/hardware/audio-networking/",
    "https://www.allen-heath.com/hardware/cc-7-cc-10/",
    "https://www.allen-heath.com/hardware/controllers/",
    "https://www.allen-heath.com/hardware/cq/",
    "https://www.allen-heath.com/hardware/dlive-series/",
    "https://www.allen-heath.com/hardware/everything-i-o/",
    "https://www.allen-heath.com/hardware/gr-series/",
    "https://www.allen-heath.com/hardware/ip-series/",
    "https://www.allen-heath.com/hardware/me-series/",
    "https://www.allen-heath.com/hardware/mixwizard4-series/",
    "https://www.allen-heath.com/hardware/qu/",
    "https://www.allen-heath.com/hardware/sq/",
    "https://www.allen-heath.com/hardware/xb-series/",
    "https://www.allen-heath.com/hardware/xone-series/",
    "https://www.allen-heath.com/hardware/zed-series/",
    "https://www.allen-heath.com/hardware/legacy/"
]

async def discover():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        all_links = set()
        
        for cat in categories:
            logger.info(f"Visiting category: {cat}")
            try:
                # Try to visit the category page
                response = await page.goto(cat, wait_until='domcontentloaded', timeout=60000)
                if response.status == 404:
                    logger.warning(f"Category not found: {cat}")
                    continue
                
                await asyncio.sleep(5)
                
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                links = await page.query_selector_all("a")
                cat_links_count = 0
                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        # Clean the URL
                        if href.startswith("/"):
                            href = "https://www.allen-heath.com" + href
                        
                        # Filter for product-like URLs
                        # Products are usually in /hardware/category/product-name/
                        # But some are just /hardware/product-name/
                        if "allen-heath.com/hardware/" in href and href != cat and not href.endswith("/hardware/"):
                            # Avoid some common non-product links
                            if any(x in href for x in ["/resources/", "/accessories/", "/mixpad/", "/4you/", "/control/"]):
                                continue
                            
                            all_links.add(href)
                            cat_links_count += 1
                
                logger.info(f"Found {cat_links_count} links in {cat}")
                
            except Exception as e:
                logger.error(f"Error visiting {cat}: {e}")
        
        logger.info(f"Total unique links found: {len(all_links)}")
        
        with open("ah_product_links_v5.txt", "w") as f:
            for link in sorted(list(all_links)):
                f.write(link + "\n")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover())
