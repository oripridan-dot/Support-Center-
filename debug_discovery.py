
import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.halilit.com/23606-guitar-effects/33269-Avid"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await asyncio.sleep(5) # Wait a bit longer
        
        links = await page.query_selector_all("a")
        print(f"Found {len(links)} links")
        
        count = 0
        for link in links:
            href = await link.get_attribute("href")
            if href:
                print(f"Link: {href}")
                if any(pattern in href.lower() for pattern in ["/product", "/item", "/p/", "/shop/", "/collections/"]):
                    print(f"  -> MATCH: {href}")
                    count += 1
        
        print(f"Total matches: {count}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
