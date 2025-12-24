"""
Adam Audio Official Website Scraper
Downloads product documentation (manuals, quick starts, spec sheets) from adam-audio.com

Usage:
    python scripts/scrape_adam_audio.py
"""

import asyncio
import os
import hashlib
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import aiohttp
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Configuration
BASE_URL = "https://www.adam-audio.com"
DOWNLOAD_DIR = Path("data/brand_docs/adam_audio")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

class AdamAudioScraper:
    def __init__(self):
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
        logging.info("✓ Browser and HTTP session initialized")
        
    async def stop(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()
        logging.info("✓ Cleanup completed")
    
    async def discover_products(self):
        """
        Discover all product URLs from the main catalog
        Returns: List of product URLs
        """
        logging.info("Discovering product catalog...")
        await self.page.goto(f"{BASE_URL}/en/", wait_until="networkidle")
        
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        product_urls = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # Match product pages: /en/t-series/t5v/, /en/a-series/a7v/, etc.
            if '/en/' in href and '-series/' in href and href.count('/') >= 4:
                if href.startswith('/'):
                    href = BASE_URL + href
                # Ensure it ends with / and is not a series overview
                if href.endswith('/') and href.split('/')[-2] not in ['t-series', 'a-series', 's-series', 'subwoofers', 'headphones', 'desktop']:
                    product_urls.add(href)
        
        logging.info(f"✓ Found {len(product_urls)} product pages")
        return list(product_urls)
    
    async def scrape_product_page(self, product_url):
        """
        Scrape a single product page for documentation
        Returns: List of PDF URLs
        """
        logging.info(f"Scraping: {product_url}")
        
        try:
            await self.page.goto(product_url, wait_until="networkidle", timeout=30000)
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract product name
            product_name = "Unknown"
            h1 = soup.find('h1')
            if h1:
                product_name = h1.text.strip()
            
            # Find all PDF links
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                link_text = link.text.strip()
                
                if '.pdf' in href.lower():
                    # Normalize URL
                    if href.startswith('/'):
                        href = BASE_URL + href
                    elif not href.startswith('http'):
                        href = BASE_URL + '/' + href
                    
                    # Determine document type
                    doc_type = self._classify_document(link_text, href)
                    
                    pdf_links.append({
                        'url': href,
                        'name': link_text or os.path.basename(href),
                        'doc_type': doc_type,
                        'product_name': product_name,
                        'product_url': product_url
                    })
            
            logging.info(f"  ✓ Found {len(pdf_links)} PDFs for {product_name}")
            return pdf_links
            
        except Exception as e:
            logging.error(f"  ✗ Error scraping {product_url}: {e}")
            return []
    
    def _classify_document(self, link_text, href):
        """Classify document type based on text and URL"""
        text_lower = link_text.lower() + ' ' + href.lower()
        
        if 'quick' in text_lower or 'quickstart' in text_lower:
            return 'quick_start'
        elif 'manual' in text_lower or 'user' in text_lower:
            return 'manual'
        elif 'spec' in text_lower or 'sheet' in text_lower or 'datasheet' in text_lower:
            return 'spec_sheet'
        elif 'brochure' in text_lower or 'product' in text_lower:
            return 'brochure'
        elif 'review' in text_lower:
            return 'review'
        else:
            return 'other'
    
    async def download_pdf(self, pdf_info):
        """
        Download a PDF file
        Returns: Local file path or None
        """
        url = pdf_info['url']
        product_name = pdf_info['product_name'].replace(' ', '_').replace('/', '_')
        doc_type = pdf_info['doc_type']
        
        # Generate filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"{product_name}_{doc_type}_{url_hash}.pdf"
        filepath = DOWNLOAD_DIR / filename
        
        # Skip if already downloaded
        if filepath.exists():
            logging.info(f"  ⏭️  Already downloaded: {filename}")
            return str(filepath)
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Verify it's a PDF
                    if content[:4] == b'%PDF':
                        filepath.write_bytes(content)
                        file_size = len(content) / 1024  # KB
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
                        logging.warning(f"  ⚠️  Not a valid PDF: {url}")
                        return None
                else:
                    logging.error(f"  ✗ HTTP {response.status}: {url}")
                    return None
                    
        except Exception as e:
            logging.error(f"  ✗ Download failed: {url} - {e}")
            return None
    
    async def run(self, max_products=None):
        """
        Main scraping workflow
        
        Args:
            max_products: Limit number of products to scrape (None = all)
        """
        await self.start()
        
        try:
            # Step 1: Discover products
            product_urls = await self.discover_products()
            
            if max_products:
                product_urls = product_urls[:max_products]
                logging.info(f"⚠️  Limiting to {max_products} products for testing")
            
            # Step 2: Scrape each product
            all_pdfs = []
            for url in product_urls:
                pdfs = await self.scrape_product_page(url)
                all_pdfs.extend(pdfs)
                await asyncio.sleep(1)  # Be polite
            
            logging.info(f"\n{'='*80}")
            logging.info(f"Total PDFs found: {len(all_pdfs)}")
            
            # Step 3: Download PDFs
            logging.info(f"\nDownloading PDFs...")
            for pdf_info in all_pdfs:
                await self.download_pdf(pdf_info)
                await asyncio.sleep(0.5)  # Be polite
            
            # Summary
            logging.info(f"\n{'='*80}")
            logging.info(f"SCRAPING COMPLETE")
            logging.info(f"{'='*80}")
            logging.info(f"Products scraped: {len(product_urls)}")
            logging.info(f"PDFs found: {len(all_pdfs)}")
            logging.info(f"PDFs downloaded: {len(self.downloaded_files)}")
            logging.info(f"Download directory: {DOWNLOAD_DIR.absolute()}")
            
            # Save manifest
            manifest_path = DOWNLOAD_DIR / "download_manifest.json"
            import json
            manifest_path.write_text(json.dumps(self.downloaded_files, indent=2))
            logging.info(f"✓ Manifest saved: {manifest_path}")
            
        finally:
            await self.stop()


async def main():
    scraper = AdamAudioScraper()
    
    # Scrape ALL products
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
