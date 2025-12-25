
import asyncio
from playwright.async_api import async_playwright

async def get_ah_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        print("Visiting AH sitemap...")
        try:
            await page.goto("https://www.allen-heath.com/sitemap-pt-product-p1.xml", wait_until='networkidle', timeout=60000)
        except:
            await page.goto("https://www.allen-heath.com/sitemap-pt-product-p1.xml", wait_until='domcontentloaded', timeout=60000)
        
        await asyncio.sleep(10)
        content = await page.content()
        print(f"Content length: {len(content)}")
        if "<loc>" in content:
            print("Found sitemap content!")
            import re
            locs = re.findall(r'<loc>(.*?)</loc>', content)
            print(f"Found {len(locs)} links in sitemap")
            for l in locs[:10]:
                print(f"  - {l}")
        else:
            print("Sitemap content not found or blocked")
            print(content[:500])
            
        await browser.close()

asyncio.run(get_ah_links())
