import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.halilit.com/g/5193-Brand/207910-ADAM-Audio')
        await asyncio.sleep(2)
        links = await page.query_selector_all('a')
        for link in links:
            href = await link.get_attribute('href')
            if href:
                print(href)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
