
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        print("Visiting hardware page...")
        await page.goto("https://www.allen-heath.com/hardware/", wait_until='networkidle', timeout=60000)
        
        # Find all links
        links = await page.query_selector_all("a")
        product_links = set()
        for link in links:
            href = await link.get_attribute("href")
            if href:
                if not href.startswith('http'):
                    href = "https://www.allen-heath.com" + (href if href.startswith('/') else '/' + href)
                
                # Filter for product-like links
                if "/hardware/" in href and len(href.split('/')) > 5:
                    # Exclude generic pages
                    if not any(x in href for x in ['/resources/', '/processing-expansion/', '/all-models/']):
                        product_links.add(href.split('#')[0].split('?')[0].rstrip('/'))
        
        print(f"Found {len(product_links)} potential product links")
        for url in sorted(list(product_links)):
            print(url)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_ah_links())
