"""
Generic Brand Documentation Scraper
Works with multiple brands using configurations from brand_configs.py

Usage:
    python scripts/scrape_brand.py "Allen & Heath"
    python scripts/scrape_brand.py "Mackie"
"""

import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hashlib
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import aiohttp
import logging
from datetime import datetime
import json
import re

from scripts.brand_configs import get_brand_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class BrandScraper:
    def __init__(self, brand_name):
        self.brand_name = brand_name
        self.config = get_brand_config(brand_name)
        
        if not self.config:
            raise ValueError(f"No configuration found for brand: {brand_name}")
        
        self.base_url = self.config['base_url']
        self.download_dir = Path(f"data/brand_docs/{brand_name.lower().replace(' ', '_')}")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser = None
        self.page = None
        self.session = None
        self.downloaded_files = []
    
    async def start(self):
        """Initialize browser and HTTP session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        self.session = aiohttp.ClientSession()
        logging.info(f"✓ Initialized scraper for {self.brand_name}")
    
    async def stop(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()
    
    async def discover_products(self):
        """Discover product URLs from catalog"""
        catalog_url = self.base_url + self.config['product_catalog_url']
        logging.info(f"Discovering products from: {catalog_url}")
        
        await self.page.goto(catalog_url, wait_until="networkidle", timeout=30000)
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        product_urls = set()
        
        # Strategy 1: Pattern matching
        if 'product_url_pattern' in self.config:
            pattern = re.compile(self.config['product_url_pattern'])
            for link in soup.find_all('a', href=True):
                href = link['href']
                if pattern.search(href):
                    if href.startswith('/'):
                        href = self.base_url + href
                    product_urls.add(href)
        
        # Strategy 2: Category-based
        elif 'product_categories' in self.config:
            for category_path in self.config['product_categories']:
                category_url = self.base_url + category_path
                await self.page.goto(category_url, wait_until="networkidle")
                content = await self.page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/product' in href or '/item' in href:
                        if href.startswith('/'):
                            href = self.base_url + href
                        product_urls.add(href)
                
                await asyncio.sleep(1)
        
        logging.info(f"✓ Found {len(product_urls)} product pages")
        return list(product_urls)
    
    async def scrape_product_page(self, product_url):
        """Scrape PDFs from a product page"""
        logging.info(f"Scraping: {product_url}")
        
        try:
            await self.page.goto(product_url, wait_until="networkidle", timeout=30000)
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract product name
            product_name = "Unknown"
            for selector in ['h1', '.product-title', '.product-name']:
                el = soup.select_one(selector)
                if el:
                    product_name = el.text.strip()
                    break
            
            # Find PDFs using configured selectors
            pdf_links = []
            for selector in self.config['pdf_selectors']:
                for link in soup.select(selector):
                    href = link.get('href', '')
                    if '.pdf' in href.lower():
                        if href.startswith('/'):
                            href = self.base_url + href
                        elif not href.startswith('http'):
                            href = self.base_url + '/' + href
                        
                        link_text = link.text.strip()
                        doc_type = self._classify_document(link_text, href)
                        
                        pdf_links.append({
                            'url': href,
                            'name': link_text or os.path.basename(href),
                            'doc_type': doc_type,
                            'product_name': product_name,
                            'product_url': product_url
                        })
            
            logging.info(f"  ✓ Found {len(pdf_links)} PDFs")
            return pdf_links
            
        except Exception as e:
            logging.error(f"  ✗ Error: {e}")
            return []
    
    def _classify_document(self, text, url):
        """Classify document type"""
        text_lower = (text + ' ' + url).lower()
        
        if 'quick' in text_lower:
            return 'quick_start'
        elif 'manual' in text_lower or 'user' in text_lower or 'guide' in text_lower:
            return 'manual'
        elif 'spec' in text_lower or 'sheet' in text_lower:
            return 'spec_sheet'
        elif 'brochure' in text_lower:
            return 'brochure'
        else:
            return 'other'
    
    async def download_pdf(self, pdf_info):
        """Download a PDF file"""
        url = pdf_info['url']
        product_name = pdf_info['product_name'].replace(' ', '_').replace('/', '_')
        doc_type = pdf_info['doc_type']
        
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"{product_name}_{doc_type}_{url_hash}.pdf"
        filepath = self.download_dir / filename
        
        if filepath.exists():
            logging.info(f"  ⏭️ Already downloaded: {filename}")
            return str(filepath)
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    if content[:4] == b'%PDF':
                        filepath.write_bytes(content)
                        file_size = len(content) / 1024
                        logging.info(f"  ✓ Downloaded: {filename} ({file_size:.1f} KB)")
                        
                        self.downloaded_files.append({
                            'filepath': str(filepath),
                            'url': url,
                            'product_name': pdf_info['product_name'],
                            'doc_type': doc_type,
                            'size_kb': file_size,
                            'downloaded_at': datetime.now().isoformat()
                        })
                        
                        return str(filepath)
                    else:
                        logging.warning(f"  ⚠️ Not a valid PDF: {url}")
                        return None
                else:
                    logging.error(f"  ✗ HTTP {response.status}: {url}")
                    return None
                    
        except Exception as e:
            logging.error(f"  ✗ Download failed: {e}")
            return None
    
    async def run(self, max_products=None):
        """Run the scraper"""
        await self.start()
        
        try:
            # Discover products
            product_urls = await self.discover_products()
            
            if max_products:
                product_urls = product_urls[:max_products]
                logging.info(f"⚠️ Limiting to {max_products} products")
            
            # Scrape products
            all_pdfs = []
            for url in product_urls:
                pdfs = await self.scrape_product_page(url)
                all_pdfs.extend(pdfs)
                await asyncio.sleep(1)
            
            logging.info(f"\nTotal PDFs found: {len(all_pdfs)}")
            
            # Download PDFs
            for pdf_info in all_pdfs:
                await self.download_pdf(pdf_info)
                await asyncio.sleep(0.5)
            
            # Save manifest
            manifest_path = self.download_dir / "download_manifest.json"
            manifest_path.write_text(json.dumps(self.downloaded_files, indent=2))
            
            # Summary
            logging.info(f"\n{'='*80}")
            logging.info(f"SCRAPING COMPLETE: {self.brand_name}")
            logging.info(f"{'='*80}")
            logging.info(f"Products: {len(product_urls)}")
            logging.info(f"PDFs found: {len(all_pdfs)}")
            logging.info(f"PDFs downloaded: {len(self.downloaded_files)}")
            logging.info(f"Directory: {self.download_dir.absolute()}")
            
        finally:
            await self.stop()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_brand.py <brand_name>")
        print("Example: python scrape_brand.py \"Allen & Heath\"")
        return
    
    brand_name = sys.argv[1]
    scraper = BrandScraper(brand_name)
    await scraper.run(max_products=3)  # Test with 3 products first


if __name__ == "__main__":
    asyncio.run(main())
