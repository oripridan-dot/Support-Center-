import asyncio
import logging
import re
import json
import os
from typing import List, Set, Dict, Optional
from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Product, Brand, ProductFamily

logger = logging.getLogger(__name__)

class DiscoveryEngine:
    def __init__(self, scraper: BaseScraper, brand_name: str, base_url: str):
        self.scraper = scraper
        self.brand_name = brand_name
        self.base_url = base_url
        self.discovered_urls: Set[str] = set()
        self.patterns: List[str] = []
        self.knowledge_base_path = f"/workspaces/Support-Center-/backend/data/knowledge_{brand_name.lower().replace(' ', '_')}.json"
        self.load_knowledge()

    def load_knowledge(self):
        if os.path.exists(self.knowledge_base_path):
            try:
                with open(self.knowledge_base_path, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get("patterns", [])
                    logger.info(f"Loaded {len(self.patterns)} patterns for {self.brand_name}")
            except Exception as e:
                logger.error(f"Failed to load knowledge: {e}")
                self.patterns = []
        else:
            self.patterns = []

    def save_knowledge(self):
        os.makedirs(os.path.dirname(self.knowledge_base_path), exist_ok=True)
        with open(self.knowledge_base_path, 'w') as f:
            json.dump({"patterns": self.patterns}, f, indent=4)

    async def discover_via_sitemap(self, sitemap_url: str):
        logger.info(f"Attempting sitemap discovery: {sitemap_url}")
        content = await self.scraper.scrape_url(sitemap_url)
        if content:
            urls = re.findall(r'<loc>(.*?)</loc>', content)
            for url in urls:
                self.discovered_urls.add(url.rstrip('/'))
            logger.info(f"Found {len(urls)} URLs in sitemap")

    async def discover_via_local_cache(self, cache_path: str):
        logger.info(f"Attempting discovery via local cache: {cache_path}")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/hardware/' in href:
                        full_url = urljoin(self.base_url, href)
                        self.discovered_urls.add(full_url.rstrip('/'))
            logger.info(f"Found {len(self.discovered_urls)} URLs in local cache")

    async def discover_via_guessing(self):
        logger.info(f"Attempting discovery via guessing for {self.brand_name}")
        with Session(engine) as session:
            brand = session.exec(select(Brand).where(Brand.name == self.brand_name)).first()
            if not brand: return
            
            products = session.exec(
                select(Product)
                .join(ProductFamily)
                .where(ProductFamily.brand_id == brand.id)
            ).all()
            
            for product in products:
                slug = product.name.lower().replace(' ', '-').replace(':', '').replace('/', '-')
                potential_urls = [
                    urljoin(self.base_url, f"hardware/{slug}/"),
                    urljoin(self.base_url, f"hardware/zed-series/{slug}/"),
                    urljoin(self.base_url, f"hardware/xone-series/{slug}/"),
                    urljoin(self.base_url, f"hardware/qu/{slug}/"),
                ]
                
                for url in potential_urls:
                    self.discovered_urls.add(url.rstrip('/'))

    async def run_discovery(self, strategies: List[str]):
        if "local" in strategies:
            # Try common local cache files
            cache_files = [
                "/workspaces/Support-Center-/backend/data/ah_product_sample.html",
                "/workspaces/Support-Center-/backend/data/ah_hardware.html"
            ]
            for cf in cache_files:
                await self.discover_via_local_cache(cf)

        if "sitemap" in strategies:
            sitemaps = [
                urljoin(self.base_url, "sitemap.xml"),
                urljoin(self.base_url, "sitemap_index.xml"),
                urljoin(self.base_url, "sitemap-pt-product-p1.xml")
            ]
            for sm in sitemaps:
                await self.discover_via_sitemap(sm)
        
        if "guessing" in strategies:
            await self.discover_via_guessing()

        logger.info(f"Discovery complete. Total URLs found: {len(self.discovered_urls)}")
        return list(self.discovered_urls)

    def learn_pattern(self, successful_urls: List[str]):
        if not successful_urls: return
        for url in successful_urls:
            path = urlparse(url).path
            segments = [s for s in path.split('/') if s]
            if len(segments) >= 2:
                pattern = f"/{segments[0]}/{segments[1]}/.*"
                if pattern not in self.patterns:
                    self.patterns.append(pattern)
        
        self.save_knowledge()
