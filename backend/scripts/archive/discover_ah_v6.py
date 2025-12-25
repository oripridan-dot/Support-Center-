import asyncio
from playwright.async_api import async_playwright
import playwright_stealth
import json
import random

async def discover_ah():
    async with async_playwright() as p:
        # Try Firefox
        browser = await p.firefox.launch(headless=True)
        
        # Create a context with a realistic viewport and user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        # stealth is for chromium
        # playwright_stealth.stealth(page)
        
        print("Navigating to Allen & Heath homepage...")
        try:
            # Go to homepage first to get cookies/session
            await page.goto("https://www.allen-heath.com/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 5))
            
            print("Navigating to Products page...")
            await page.goto("https://www.allen-heath.com/hardware/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(3, 6))
            
            # Look for category links
            # Allen & Heath products are often under /hardware/ or specific series
            links = await page.query_selector_all("a[href*='/hardware/']")
            
            product_links = set()
            for link in links:
                href = await link.get_attribute("href")
                if href and "allen-heath.com/hardware/" in href:
                    # Filter out generic hardware link
                    if href.strip("/") != "https://www.allen-heath.com/hardware":
                        product_links.add(href)
            
            print(f"Found {len(product_links)} potential product/category links.")
            
            # Also try to find links in the menu
            menu_links = await page.query_selector_all(".menu-item a")
            for link in menu_links:
                href = await link.get_attribute("href")
                if href and "allen-heath.com/hardware/" in href:
                    product_links.add(href)

            print(f"Total unique links found: {len(product_links)}")
            
            with open("ah_links_v6.json", "w") as f:
                json.dump(list(product_links), f, indent=2)
                
            if not product_links:
                # If still blocked, take a screenshot to see what's happening
                await page.screenshot(path="ah_blocked.png")
                print("No links found. Screenshot saved to ah_blocked.png")
                content = await page.content()
                if "Cloudflare" in content or "Just a moment" in content:
                    print("Confirmed: Still blocked by Cloudflare.")
                else:
                    print("Not blocked, but no links found. Check selectors.")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="ah_error.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_ah())
