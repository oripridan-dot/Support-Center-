import asyncio
from playwright.async_api import async_playwright
import os

async def discover_db_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        base_url = "https://www.dbtechnologies.com/en/products/"
        print(f"Discovering links from {base_url}")
        
        await page.goto(base_url, wait_until="networkidle")
        
        # Find all product links
        # On dBTechnologies, products are often under /en/products/[category]/[product-name]
        links = await page.query_selector_all("a")
        product_links = set()
        
        for link in links:
            href = await link.get_attribute("href")
            if href and "/en/products/" in href and len(href.split("/")) > 4:
                if not href.startswith("http"):
                    href = "https://www.dbtechnologies.com" + href
                product_links.add(href)
        
        print(f"Found {len(product_links)} potential product links")
        
        output_file = "/workspaces/Support-Center-/backend/data/db_technologies_links.txt"
        with open(output_file, "w") as f:
            for link in sorted(list(product_links)):
                f.write(link + "\n")
        
        print(f"Links saved to {output_file}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(discover_db_links())
