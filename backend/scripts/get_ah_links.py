import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import re

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth_cfg = Stealth()
        await stealth_cfg.apply_stealth_async(page)
        
        url = "https://www.allen-heath.com/hardware/"
        print(f"Fetching AH hardware page: {url}")
        
        try:
            # Visit homepage first to get cookies
            print("Visiting homepage...")
            await page.goto("https://www.allen-heath.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(10)
            
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(15) # Wait for JS challenges
            
            title = await page.title()
            print(f"Page title: {title}")
            
            await page.screenshot(path="ah_debug.png")
            print("Screenshot saved to ah_debug.png")
            
            content = await page.content()
            print(f"Content length: {len(content)}")
            
            # Extract links
            links = await page.query_selector_all("a")
            ah_links = set()
            for link in links:
                href = await link.get_attribute("href")
                if href and ("/hardware/" in href or "/products/" in href):
                    if href.startswith("/"):
                        href = "https://www.allen-heath.com" + href
                    if "allen-heath.com" in href:
                        ah_links.add(href)
            
            print(f"Found {len(ah_links)} AH category links")
            
            all_product_links = set()
            for cat_link in sorted(list(ah_links)):
                if cat_link == "https://www.allen-heath.com/hardware/":
                    continue
                
                print(f"Crawling category: {cat_link}")
                try:
                    await page.goto(cat_link, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(5)
                    
                    # Look for links that look like products
                    # Usually they are under /hardware/ or /products/ but deeper
                    links = await page.query_selector_all("a")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            if href.startswith("/"):
                                href = "https://www.allen-heath.com" + href
                            
                            # Filter for product-like URLs
                            # Products usually have a specific structure, e.g., /hardware/zed-series/zed-10/
                            # or /hardware/qu/qu-16/
                            if "allen-heath.com" in href and ("/hardware/" in href or "/products/" in href):
                                # Exclude category pages themselves and common pages
                                if href != cat_link and not href.endswith("/hardware/") and not href.endswith("/products/"):
                                    # A product link usually has more segments than a category link
                                    cat_segments = len(cat_link.strip("/").split("/"))
                                    href_segments = len(href.strip("/").split("/"))
                                    if href_segments > cat_segments:
                                        all_product_links.add(href)
                except Exception as e:
                    print(f"Error crawling {cat_link}: {e}")

            print(f"Found {len(all_product_links)} AH product links")
            with open("ah_product_links.txt", "w") as f:
                for link in sorted(list(all_product_links)):
                    f.write(link + "\n")
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_ah_links())
