"""
Allen & Heath Dedicated Scraper
Multi-browser anti-detection with intelligent discovery and media extraction
"""

import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any, List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx
from app.engines.brand_scraper import BrandScraper

logger = logging.getLogger(__name__)


class AllenHeathScraper(BrandScraper):
    """
    Dedicated scraper for Allen & Heath
    Features:
    - Multi-browser rotation (Chrome, Firefox, WebKit)
    - Advanced Cloudflare evasion
    - Intelligent URL discovery with priority sections
    - Media extraction (images, PDFs, manuals)
    - Content deduplication via hashing
    """
    
    def __init__(self, headless: bool = True):
        super().__init__(brand_name="Allen & Heath", headless=headless)
        self.discovered_urls: Set[str] = set()
        self.visited_hashes: Set[str] = set()  # For deduplication
        
    def get_official_domains(self) -> Set[str]:
        """Allen & Heath official domains"""
        return {
            "allen-heath.com",
            "www.allen-heath.com",
            "support.allen-heath.com",
            "downloads.allen-heath.com",
        }
    
    def get_discovery_urls(self) -> Dict[str, str]:
        """Priority sections for discovery"""
        return {
            "home": "https://www.allen-heath.com",
            "products": "https://www.allen-heath.com/products/",
            "hardware": "https://www.allen-heath.com/hardware/",
            "support": "https://www.allen-heath.com/support/",
            "downloads": "https://www.allen-heath.com/downloads/",
            "technical": "https://www.allen-heath.com/technical/",
            "documentation": "https://www.allen-heath.com/documentation/",
            "blog": "https://www.allen-heath.com/blog/",
            "live-sound": "https://www.allen-heath.com/category/live-sound/",
            "studio": "https://www.allen-heath.com/category/studio/",
            "dj": "https://www.allen-heath.com/category/dj/",
            "education": "https://www.allen-heath.com/category/education/",
        }
    
    async def discover_urls(self) -> Set[str]:
        """
        Multi-strategy URL discovery:
        1. Robots.txt parsing
        2. Sitemap crawling
        3. Priority section exploration
        4. Cross-link following (3 levels deep)
        """
        logger.info("="*60)
        logger.info("[Allen & Heath] Starting comprehensive URL discovery")
        logger.info("="*60)
        
        # Strategy 1: Parse robots.txt
        await self._discover_from_robots()
        logger.info(f"After robots.txt: {len(self.discovered_urls)} URLs")
        
        # Strategy 2: Crawl sitemap
        await self._discover_from_sitemap()
        logger.info(f"After sitemap: {len(self.discovered_urls)} URLs")
        
        # Strategy 3: Explore priority sections
        await self._discover_from_sections()
        logger.info(f"After sections: {len(self.discovered_urls)} URLs")
        
        # Strategy 4: Deep crawl from discovered URLs
        await self._deep_crawl_discovered()
        logger.info(f"After deep crawl: {len(self.discovered_urls)} URLs")
        
        logger.info(f"✓ Discovery complete: {len(self.discovered_urls)} unique URLs")
        return self.discovered_urls
    
    async def _discover_from_robots(self):
        """Extract URLs from robots.txt"""
        try:
            logger.info("[AH-Discovery] Checking robots.txt...")
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get("https://www.allen-heath.com/robots.txt", headers={
                    "User-Agent": self._get_user_agent()
                })
                
                if response.status_code == 200:
                    lines = response.text.split('\n')
                    for line in lines:
                        if line.startswith('Allow: ') or line.startswith('Disallow: '):
                            path = line.split(': ')[1].strip()
                            if path and not path.startswith('*'):
                                url = urljoin("https://www.allen-heath.com", path)
                                if self.is_valid_url(url):
                                    self.discovered_urls.add(url)
                    
                    logger.info(f"  → Found {len(self.discovered_urls)} URLs from robots.txt")
        except Exception as e:
            logger.warning(f"Failed to parse robots.txt: {e}")
    
    async def _discover_from_sitemap(self):
        """Crawl all URLs from sitemap"""
        try:
            logger.info("[AH-Discovery] Crawling sitemaps...")
            
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                # Main sitemap index
                response = await client.get("https://www.allen-heath.com/sitemap_index.xml", 
                                           headers={"User-Agent": self._get_user_agent()})
                
                if response.status_code != 200:
                    # Try alternative sitemap location
                    response = await client.get("https://www.allen-heath.com/sitemap.xml",
                                               headers={"User-Agent": self._get_user_agent()})
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')
                    
                    # Extract sitemap URLs
                    for sitemap in soup.find_all('sitemap'):
                        loc = sitemap.find('loc')
                        if loc:
                            await self._parse_sitemap(loc.text.strip(), client)
                    
                    # Extract direct URLs from sitemap
                    for url_tag in soup.find_all('url'):
                        loc = url_tag.find('loc')
                        if loc:
                            url = loc.text.strip()
                            if self.is_valid_url(url):
                                self.discovered_urls.add(url)
                    
                    logger.info(f"  → Found {len(self.discovered_urls)} URLs from sitemaps")
        except Exception as e:
            logger.warning(f"Failed to crawl sitemap: {e}")
    
    async def _parse_sitemap(self, sitemap_url: str, client: httpx.AsyncClient):
        """Parse individual sitemap file"""
        try:
            response = await client.get(sitemap_url, headers={"User-Agent": self._get_user_agent()})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                for url_tag in soup.find_all('url'):
                    loc = url_tag.find('loc')
                    if loc:
                        url = loc.text.strip()
                        if self.is_valid_url(url):
                            self.discovered_urls.add(url)
        except Exception as e:
            logger.debug(f"Failed to parse sitemap {sitemap_url}: {e}")
    
    async def _discover_from_sections(self):
        """Scrape priority sections to discover URLs using HTTP first"""
        logger.info("[AH-Discovery] Exploring priority sections...")
        
        sections = self.get_discovery_urls()
        for section_name, section_url in sections.items():
            logger.info(f"  → Section {section_name}")
            
            # Try HTTP first (faster, less blocking)
            html = await self._get_content_http(section_url)
            
            # If HTTP fails, fall back to browser
            if not html:
                logger.debug(f"    HTTP failed, trying browser for {section_name}")
                html = await self.scrape_url(section_url)
            
            if not html:
                logger.debug(f"    Skipped {section_name} (no content)")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all links on the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                url = urljoin("https://www.allen-heath.com", href)
                
                # Clean URL (remove fragments)
                url = url.split('#')[0]
                
                if self.is_valid_url(url):
                    self.discovered_urls.add(url)
    
    async def _deep_crawl_discovered(self, max_depth: int = 2):
        """Deep crawl from discovered URLs to find more links"""
        logger.info(f"[AH-Discovery] Deep crawling {len(self.discovered_urls)} discovered URLs (depth={max_depth})...")
        
        # Prioritize product/documentation URLs
        priority_patterns = [
            '/products/', '/hardware/', '/support/', '/downloads/',
            '/technical/', '/documentation/', '/manuals/', '/specs/'
        ]
        
        urls_to_crawl = sorted(
            [u for u in self.discovered_urls],
            key=lambda u: sum(1 for p in priority_patterns if p in u),
            reverse=True
        )[:100]  # Limit to top 100 to avoid explosion
        
        for i, url in enumerate(urls_to_crawl):
            logger.info(f"[AH-Discovery] Deep crawl {i+1}/{len(urls_to_crawl)}: {url.split('/')[-1]}")
            
            # Try HTTP first, then browser
            html = await self._get_content_http(url)
            if not html:
                html = await self.scrape_url(url)
            
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product links, documentation links, etc.
            for link in soup.find_all('a', href=True):
                href = link['href']
                url_new = urljoin("https://www.allen-heath.com", href)
                url_new = url_new.split('#')[0]  # Remove fragments
                
                if self.is_valid_url(url_new) and url_new not in self.discovered_urls:
                    # Only add if it matches priority patterns or is on products
                    if any(p in url_new for p in priority_patterns) or '/products' in url_new:
                        self.discovered_urls.add(url_new)
            
            await asyncio.sleep(2)  # Polite crawling
    
    def _get_content_hash(self, content: str) -> str:
        """Get hash of content for deduplication"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def scrape_with_dedup(self, url: str) -> Optional[str]:
        """Scrape URL and check for duplicate content"""
        html = await self.scrape_url(url)
        if not html:
            return None
        
        content_hash = self._get_content_hash(html)
        if content_hash in self.visited_hashes:
            logger.debug(f"[AH] Duplicate content detected: {url}")
            return None
        
        self.visited_hashes.add(content_hash)
        return html
    
    async def _get_content_http(self, url: str) -> Optional[str]:
        """Try to get content via HTTP (avoids Cloudflare for static content)"""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": self._get_user_agent(),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Referer": "https://www.google.com/",
                })
                
                if response.status_code == 200:
                    # Quick check if it's actually HTML and not a CF challenge
                    content = response.text
                    if "Just a moment" in content or "Verify you are human" in content:
                        logger.debug(f"[AH-HTTP] Cloudflare block detected on {url}")
                        return None
                    
                    return content
                else:
                    logger.debug(f"[AH-HTTP] Status {response.status_code} for {url}")
                    return None
        except Exception as e:
            logger.debug(f"[AH-HTTP] Error: {str(e)[:60]}")
            return None
    
    def extract_media(self, html: str, base_url: str) -> Dict[str, List[str]]:
        """Extract media (images, PDFs, etc.) from HTML"""
        media = {
            "images": [],
            "pdfs": [],
            "documents": [],
            "manuals": []
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Images
            for img in soup.find_all('img', src=True):
                src = img['src']
                url = urljoin(base_url, src)
                if url not in media["images"]:
                    media["images"].append(url)
            
            # PDFs and documents
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.zip']):
                    url = urljoin(base_url, href)
                    if url.endswith('.pdf'):
                        media["pdfs"].append(url)
                    else:
                        media["documents"].append(url)
                    
                    # Check if it's a manual
                    if 'manual' in href.lower() or 'guide' in href.lower():
                        media["manuals"].append(url)
            
        except Exception as e:
            logger.debug(f"Error extracting media: {e}")
        
        return media
