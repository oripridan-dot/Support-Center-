import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import random

async def get_sitemap():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        print("Navigating to Allen & Heath...")
        try:
            # Go to homepage first
            await page.goto("https://www.allen-heath.com/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 5))
            
            # Try to get the sitemap
            sitemap_url = "https://www.allen-heath.com/sitemap-pt-product-p1.xml"
            print(f"Fetching sitemap: {sitemap_url}")
            await page.goto(sitemap_url, wait_until="networkidle", timeout=60000)
            
            content = await page.content()
            if "<urlset" in content:
                print("Sitemap found!")
                with open("/workspaces/Support-Center-/backend/data/ah_sitemap_full.xml", "w") as f:
                    f.write(content)
            else:
                print("Sitemap not found or blocked.")
                await page.screenshot(path="ah_sitemap_fail_robust.png")
                
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_sitemap())
