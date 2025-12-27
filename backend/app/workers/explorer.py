"""
Explorer Worker

Responsibilities:
- Discovers brand documentation structure and organization
- Analyzes website patterns (navigation, content types, URL structures)
- Generates comprehensive scraping instructions for the Scraper
- Validates documentation completeness against discovered content
- Provides verification reports after ingestion

The Explorer acts as the intelligence layer, discovering what needs to be scraped
and how, then verifying that everything was properly collected and indexed.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.database import get_session
from app.models.sql_models import Brand
from app.config.brand_configs import get_brand_config, BrandDiscoveryConfig


class DocumentationSource(BaseModel):
    """Represents a discovered documentation source"""
    url: str
    type: str  # 'manual', 'guide', 'tutorial', 'faq', 'spec_sheet', 'release_notes'
    title: Optional[str] = None
    product_name: Optional[str] = None
    priority: int = 5  # 1-10, higher = more important
    estimated_size: Optional[str] = None


class ScrapingStrategy(BaseModel):
    """Scraping instructions for a brand"""
    brand_id: int
    brand_name: str
    base_url: str
    documentation_urls: List[DocumentationSource]
    navigation_pattern: str  # Description of how to navigate docs
    content_selectors: Dict[str, str]  # CSS selectors for different content types
    pagination_info: Optional[Dict[str, Any]] = None
    download_links: bool = False
    requires_javascript: bool = False
    rate_limit_ms: int = 1000  # Delay between requests
    total_estimated_docs: int = 0
    notes: str = ""


class VerificationReport(BaseModel):
    """Report comparing discovered docs vs ingested docs"""
    brand_id: int
    brand_name: str
    discovered_count: int
    ingested_count: int
    missing_docs: List[str]
    extra_docs: List[str]
    coverage_percentage: float
    timestamp: datetime


class ExplorerWorker:
    """
    Explores brand websites to discover documentation and generate scraping strategies.
    
    MISSION: 100% official documentation coverage for ALL Halilit brands.
    The Explorer moves fast, discovers everything, and leaves crystal-clear instructions.
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.strategies_cache: Dict[int, ScrapingStrategy] = {}
        self.discovery_manifest: Dict[int, List[DocumentationSource]] = {}  # What exists
        self.brand_config: Optional[BrandDiscoveryConfig] = None
    
    async def initialize(self):
        """Initialize browser for exploration"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
    
    async def shutdown(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
    
    async def explore_brand(self, brand_id: int) -> ScrapingStrategy:
        """
        Main exploration method - discovers documentation structure
        """
        session = next(get_session())
        brand = session.exec(select(Brand).where(Brand.id == brand_id)).first()
        
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")
        
        # Load brand-specific configuration
        self.brand_config = get_brand_config(brand.name)
        
        print(f"🔍 [EXPLORER] Starting AGGRESSIVE exploration for {brand.name}")
        print(f"    🎯 MISSION: 100% documentation coverage")
        print(f"    ⚙️  Using strategies: {', '.join(self.brand_config.strategies)}")
        
        # Update status tracker
        from app.workers.status_tracker import worker_status
        worker_status.explorer_start(brand_id, brand.name)
        
        try:
            # Discover ALL documentation sources (leave no stone unturned)
            worker_status.explorer_progress("Discovering documentation", 25)
            
            # Add timeout to prevent hanging
            docs = await asyncio.wait_for(
                self._discover_documentation(brand),
                timeout=60.0  # 60 second max for discovery
            )
            
            # Store in discovery manifest
            self.discovery_manifest[brand_id] = docs
            
            # Analyze website structure
            worker_status.explorer_progress("Analyzing website structure", 50)
            navigation_pattern = await self._analyze_navigation(brand)
            
            # Determine content extraction selectors
            worker_status.explorer_progress("Identifying content selectors", 75)
            content_selectors = await self._identify_selectors(brand)
            
            # Check if JavaScript rendering is needed
            requires_js = await self._check_javascript_requirement(brand)
            
            # Build strategy
            worker_status.explorer_progress("Generating strategy", 90, len(docs))
            
            # Use website_url or fallback to a placeholder
            base_url = brand.website_url or f"https://{brand.name.lower().replace(' ', '-')}.com"
            
            strategy = ScrapingStrategy(
                brand_id=brand.id,
                brand_name=brand.name,
                base_url=base_url,
                documentation_urls=docs,
                navigation_pattern=navigation_pattern,
                content_selectors=content_selectors,
                requires_javascript=requires_js,
                total_estimated_docs=len(docs),
                rate_limit_ms=1000,
                notes=f"Discovered {len(docs)} documentation sources"
            )
            
            # Cache for later verification
            self.strategies_cache[brand_id] = strategy
            
            # Save strategy to disk
            await self._save_strategy(strategy)
            
            print(f"✅ [EXPLORER] Completed exploration: {len(docs)} docs discovered")
            
            # Update status tracker
            worker_status.explorer_complete(len(docs))
            
            return strategy
            
        except Exception as e:
            from app.workers.status_tracker import worker_status
            worker_status.explorer_fail(str(e))
            raise
    
    async def _discover_documentation(self, brand: Brand) -> List[DocumentationSource]:
        """
        COMPREHENSIVE multi-strategy discovery system.
        Tries multiple approaches to find ALL documentation.
        """
        docs: List[DocumentationSource] = []
        config = self.brand_config or get_brand_config(brand.name)
        
        print(f"  🔎 Multi-strategy discovery for {brand.name}...")
        
        # Real-time logging
        from app.workers.status_tracker import worker_status
        
        if not self.browser:
            await self.initialize()
        
        page = await self.browser.new_page()
        
        try:
            # Execute strategies in order specified by brand config
            for idx, strategy in enumerate(config.strategies):
                progress = int((idx / len(config.strategies)) * 80)  # 0-80% for discovery
                
                if strategy == "sitemap":
                    worker_status._log("📋 Strategy: Parsing sitemap.xml")
                    sitemap_docs = await self._discover_from_sitemap(page, brand, config)
                    docs.extend(sitemap_docs)
                    worker_status._log(f"✓ Sitemap: Found {len(sitemap_docs)} URLs")
                
                elif strategy == "robots":
                    worker_status._log("🤖 Strategy: Checking robots.txt")
                    robots_docs = await self._discover_from_robots(page, brand, config)
                    docs.extend(robots_docs)
                    worker_status._log(f"✓ Robots.txt: Found {len(robots_docs)} hints")
                
                elif strategy == "common_paths":
                    worker_status._log("🗂️ Strategy: Trying common paths")
                    common_docs = await self._discover_from_common_paths(page, brand, config)
                    docs.extend(common_docs)
                    worker_status._log(f"✓ Common paths: Found {len(common_docs)} pages")
                
                elif strategy == "crawl":
                    worker_status._log("🕷️ Strategy: Deep crawling website")
                    crawl_docs = await self._discover_from_crawling(page, brand, config)
                    docs.extend(crawl_docs)
                    worker_status._log(f"✓ Deep crawl: Found {len(crawl_docs)} links")
                
                elif strategy == "products":
                    worker_status._log("📦 Strategy: Product-based discovery")
                    product_docs = await self._discover_from_products(page, brand, config)
                    docs.extend(product_docs)
                    worker_status._log(f"✓ Products: Found {len(product_docs)} product docs")
                
                worker_status.explorer_progress(f"Strategy {idx+1}/{len(config.strategies)}", progress)
            
        finally:
            await page.close()
        
        # Deduplicate and prioritize
        worker_status._log(f"🔄 Deduplicating {len(docs)} raw documents...")
        docs = self._deduplicate_and_rank(docs)
        worker_status._log(f"✓ Finalized: {len(docs)} unique documentation sources")
        
        return docs
    
    async def _discover_from_sitemap(self, page: Page, brand: Brand, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Parse sitemap.xml for documentation URLs"""
        docs = []
        import xml.etree.ElementTree as ET
        
        sitemap_urls = [
            f"{brand.website_url}/sitemap.xml",
            f"{brand.website_url}/sitemap_index.xml",
            f"{brand.website_url}/sitemap-products.xml",
            f"{brand.website_url}/sitemap-pages.xml",
        ]
        
        print(f"    🔍 Trying {len(sitemap_urls)} sitemap URLs...")
        
        for sitemap_url in sitemap_urls:
            try:
                print(f"      → {sitemap_url}")
                response = await asyncio.wait_for(
                    page.goto(sitemap_url, wait_until="load"),
                    timeout=8.0
                )
                
                if response and response.ok:
                    content = await page.content()
                    print(f"        ✓ Status {response.status}, Content length: {len(content)}")
                    
                    # Parse XML
                    try:
                        root = ET.fromstring(content)
                    except ET.ParseError as e:
                        print(f"        ✗ XML parse error: {e}")
                        continue
                    
                    # Check if this is a sitemap index (contains other sitemaps)
                    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    nested_sitemaps = root.findall('.//sm:sitemap/sm:loc', ns) + root.findall('.//sitemap/loc')
                    
                    if nested_sitemaps:
                        print(f"        ℹ️  Found {len(nested_sitemaps)} nested sitemaps")
                        # Parse ALL nested sitemaps for comprehensive coverage
                        for nested_loc in nested_sitemaps:
                            nested_url = nested_loc.text
                            if nested_url:
                                # Prioritize product and support sitemaps
                                is_priority = any(keyword in nested_url.lower() for keyword in ['product', 'support', 'download', 'manual'])
                                
                                if is_priority:
                                    print(f"        → 🎯 Priority: {nested_url[:70]}...")
                                else:
                                    print(f"        → {nested_url[:70]}...")
                                
                                try:
                                    nested_response = await asyncio.wait_for(
                                        page.goto(nested_url, wait_until="load"),
                                        timeout=10.0  # Increased timeout for large sitemaps
                                    )
                                    if nested_response and nested_response.ok:
                                        nested_content = await page.content()
                                        nested_root = ET.fromstring(nested_content)
                                        nested_docs = self._parse_sitemap_content_sync(nested_root, config)
                                        docs.extend(nested_docs)
                                        print(f"          ✓ Found {len(nested_docs)} URLs")
                                except (asyncio.TimeoutError, Exception) as e:
                                    print(f"          ✗ Error: {e}")
                                    continue
                    else:
                        # Regular sitemap with URLs
                        found_docs = self._parse_sitemap_content_sync(root, config)
                        docs.extend(found_docs)
                        print(f"        ✓ Found {len(found_docs)} relevant URLs")
                else:
                    print(f"        ✗ Status {response.status if response else 'No response'}")
            except asyncio.TimeoutError:
                print(f"        ⏱️  Timeout")
            except Exception as e:
                print(f"        ✗ Error: {e}")
                continue
        
        return docs
    
    async def _parse_sitemap_url(self, page: Page, sitemap_url: str, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Parse a single sitemap URL"""
        docs = []
        import xml.etree.ElementTree as ET
        
        try:
            response = await asyncio.wait_for(
                page.goto(sitemap_url, wait_until="load"),
                timeout=8.0
            )
            if response and response.ok:
                content = await page.content()
                root = ET.fromstring(content)
                docs = self._parse_sitemap_content_sync(root, config)
        except asyncio.TimeoutError:
            print(f"          ⏱️  Timeout")
        except Exception as e:
            print(f"          ✗ Error: {e}")
        
        return docs
    
    def _parse_sitemap_content_sync(self, root, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Extract documentation URLs from parsed sitemap XML (sync version)"""
        docs = []
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # Comprehensive keywords for COMPLETE documentation coverage
        # Include broader product-related keywords since product pages link to manuals
        comprehensive_keywords = (
            config.doc_keywords +  # manual, guide, spec, datasheet, tutorial, support
            ['product', 'hardware', 'software', 'plugin', 'download', 'resource', 'library', 'archive']
        )
        
        # Extract URLs with namespace
        for loc in root.findall('.//sm:loc', ns):
            url = loc.text
            if url and any(keyword in url.lower() for keyword in comprehensive_keywords):
                docs.append(DocumentationSource(
                    url=url,
                    type='manual',
                    priority=7
                ))
        
        # Also check without namespace (some sites don't use it)
        for loc in root.findall('.//loc'):
            url = loc.text
            if url and any(keyword in url.lower() for keyword in comprehensive_keywords):
                docs.append(DocumentationSource(
                    url=url,
                    type='manual',
                    priority=7
                ))
        
        return docs
    
    async def _discover_from_robots(self, page: Page, brand: Brand, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Check robots.txt for documentation hints"""
        docs = []
        
        try:
            response = await page.goto(f"{brand.website_url}/robots.txt", timeout=5000)
            if response and response.ok:
                content = await page.content()
                
                # Look for sitemap declarations and allowed paths
                for line in content.split('\n'):
                    if 'sitemap:' in line.lower():
                        sitemap_url = line.split(':', 1)[1].strip()
                        # Recursively fetch this sitemap
                        sub_docs = await self._discover_from_sitemap(page, brand, config)
                        docs.extend(sub_docs)
        except:
            pass
        
        return docs
    
    async def _discover_from_common_paths(self, page: Page, brand: Brand, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Try common documentation path patterns"""
        docs = []
        
        # Use brand-specific paths if available, otherwise use defaults
        paths_to_try = config.documentation_paths if config.documentation_paths else [
            "/support", "/downloads", "/documentation", "/docs", "/help",
            "/knowledge-base", "/kb", "/support-center", "/resources",
            "/manuals", "/guides", "/tutorials", "/products", "/catalog",
            "/support/downloads", "/support/documentation", "/support/manuals",
            "/en/support", "/en/downloads", "/us/support", "/us/downloads"
        ]
        
        print(f"    🔍 Trying {len(paths_to_try)} common paths...")
        
        for path in paths_to_try:
            try:
                url = f"{brand.website_url}{path}"
                print(f"      → {url}")
                response = await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                
                if response and response.ok:
                    print(f"        ✓ Status {response.status}")
                    
                    # Extract all links that might be documentation (using brand config selectors)
                    link_selector = config.selectors.get("doc_links", "a[href]")
                    links = await page.query_selector_all(link_selector)
                    
                    # Also try download links selector
                    download_selector = config.selectors.get("download_links", "a[href$='.pdf']")
                    download_links = await page.query_selector_all(download_selector)
                    links.extend(download_links)
                    
                    print(f"        ✓ Found {len(links)} potential links")
                    
                    for link in links[:100]:  # Limit per page
                        try:
                            href = await link.get_attribute('href')
                            text = (await link.text_content() or "").strip()
                            
                            if not href:
                                continue
                            
                            # Build full URL
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = f"{brand.website_url}{href}"
                            else:
                                full_url = f"{brand.website_url}/{href}"
                            
                            # Check if it's documentation-related
                            if any(kw in full_url.lower() or kw in text.lower() for kw in config.doc_keywords):
                                doc_type = 'manual'
                                if '.pdf' in full_url.lower():
                                    doc_type = 'spec_sheet'
                                elif 'guide' in text.lower():
                                    doc_type = 'guide'
                                
                                docs.append(DocumentationSource(
                                    url=full_url,
                                    type=doc_type,
                                    title=text[:100] if text else None,
                                    priority=6
                                ))
                        except:
                            continue
                else:
                    print(f"        ✗ Status {response.status if response else 'No response'}")
            except Exception as e:
                print(f"        ✗ Error: {e}")
                continue
        
        print(f"    ✓ Common paths found {len(docs)} documents")
        return docs
    
    async def _discover_from_crawling(self, page: Page, brand: Brand, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Deep crawl the website for documentation"""
        docs = []
        visited = set()
        to_visit = [(brand.website_url, 0)]
        max_pages = min(config.max_pages, 50)  # Respect config but cap at 50
        
        while to_visit and len(visited) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > config.max_crawl_depth:
                continue
            
            visited.add(url)
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                
                # Extract all links
                links = await page.query_selector_all('a[href]')
                
                for link in links[:50]:
                    try:
                        href = await link.get_attribute('href')
                        if not href:
                            continue
                        
                        # Build full URL
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = f"{brand.website_url}{href}"
                        else:
                            continue
                        
                        # Only follow same-domain links
                        if not full_url.startswith(brand.website_url):
                            continue
                        
                        # If it looks like documentation, add it
                        if any(kw in full_url.lower() for kw in config.doc_keywords):
                            text = (await link.text_content() or "").strip()
                            docs.append(DocumentationSource(
                                url=full_url,
                                type='manual',
                                title=text[:100] if text else None,
                                priority=5
                            ))
                        
                        # Queue for further crawling
                        if depth < config.max_crawl_depth:
                            to_visit.append((full_url, depth + 1))
                    except:
                        continue
            except:
                continue
        
        return docs
    
    async def _discover_from_products(self, page: Page, brand: Brand, config: BrandDiscoveryConfig) -> List[DocumentationSource]:
        """Discover documentation by enumerating products from database"""
        docs = []
        
        # Get products from database
        session = next(get_session())
        from app.models.sql_models import Product, ProductFamily
        
        products = session.exec(
            select(Product)
            .join(ProductFamily)
            .where(ProductFamily.brand_id == brand.id)
        ).all()
        
        print(f"    📦 Found {len(products)} products for {brand.name}")
        
        for product in products:  # No limit - explore ALL products for 100% coverage
            # Use brand-specific URL pattern if available
            if config.product_url_pattern:
                slug = product.name.lower().replace(' ', '-').replace('/', '-')
                potential_urls = [config.product_url_pattern.format(slug=slug).replace('{base_url}', brand.website_url)]
            else:
                # Try common product documentation URL patterns
                slug = product.name.lower().replace(' ', '-').replace('/', '-')
                potential_urls = [
                    f"{brand.website_url}/products/{slug}",
                    f"{brand.website_url}/product/{slug}",
                    f"{brand.website_url}/en/products/{slug}",
                    f"{brand.website_url}/downloads/{slug}",
                    f"{brand.website_url}/support/{slug}",
                ]
            
            for url in potential_urls:
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=5000)
                    if response and response.ok:
                        # Look for download/manual links on product page (use brand selectors)
                        download_selector = config.selectors.get("download_links", "a[href$='.pdf']")
                        pdf_links = await page.query_selector_all(download_selector)
                        
                        for link in pdf_links:
                            href = await link.get_attribute('href')
                            text = (await link.text_content() or "").strip()
                            
                            if href:
                                full_url = href if href.startswith('http') else f"{brand.website_url}{href}"
                                docs.append(DocumentationSource(
                                    url=full_url,
                                    type='manual',
                                    title=f"{product.name} - {text}"[:100],
                                    product_name=product.name,
                                    priority=9  # High priority - product-specific
                                ))
                        
                        break  # Found the product page
                except:
                    continue
        
        return docs
    
    def _deduplicate_and_rank(self, docs: List[DocumentationSource]) -> List[DocumentationSource]:
        """Remove duplicates and sort by priority"""
        seen = {}
        
        for doc in docs:
            if doc.url not in seen or doc.priority > seen[doc.url].priority:
                seen[doc.url] = doc
        
        unique_docs = list(seen.values())
        unique_docs.sort(key=lambda x: x.priority, reverse=True)
        
        return unique_docs
    
    async def _analyze_navigation(self, brand: Brand) -> str:
        """Analyze how documentation is organized"""
        return "hierarchical"  # Placeholder - can be expanded
    
    async def _identify_selectors(self, brand: Brand) -> Dict[str, str]:
        """Identify CSS selectors for content extraction"""
        return {
            "title": "h1, .title, .doc-title",
            "content": "article, .content, .documentation, main",
            "sidebar": ".sidebar, nav",
            "download_link": "a[href$='.pdf']"
        }
    
    async def _check_javascript_requirement(self, brand: Brand) -> bool:
        """Check if site requires JavaScript rendering"""
        return True  # Conservative default
    
    async def _save_strategy(self, strategy: ScrapingStrategy):
        """Save scraping strategy to disk"""
        output_path = f"/workspaces/Support-Center-/backend/data/strategies/{strategy.brand_name.lower().replace(' ', '_')}_strategy.json"
        
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(strategy.model_dump(), f, indent=2, default=str)
        
        print(f"  💾 Strategy saved to {output_path}")
    
    async def verify_ingestion(self, brand_id: int) -> VerificationReport:
        """
        Verify that all discovered documentation was properly ingested
        Called by Ingester after vectorization completes
        """
        strategy = self.strategies_cache.get(brand_id)
        if not strategy:
            # Try loading from disk
            session = next(get_session())
            brand = session.exec(select(Brand).where(Brand.id == brand_id)).first()
            if brand:
                strategy_path = f"/workspaces/Support-Center-/backend/data/strategies/{brand.name.lower().replace(' ', '_')}_strategy.json"
                try:
                    with open(strategy_path, 'r') as f:
                        data = json.load(f)
                        strategy = ScrapingStrategy(**data)
                except Exception as e:
                    print(f"⚠️  Could not load strategy: {e}")
                    return None
        
        if not strategy:
            raise ValueError(f"No strategy found for brand {brand_id}")
        
        # Get actual ingested documents from database
        session = next(get_session())
        from app.models.document import Document
        ingested_docs = session.exec(
            select(Document).where(Document.brand_id == brand_id)
        ).all()
        
        discovered_urls = {doc.url for doc in strategy.documentation_urls}
        ingested_urls = {doc.url for doc in ingested_docs}
        
        missing = list(discovered_urls - ingested_urls)
        extra = list(ingested_urls - discovered_urls)
        
        coverage = (len(ingested_urls) / len(discovered_urls) * 100) if discovered_urls else 0
        
        report = VerificationReport(
            brand_id=brand_id,
            brand_name=strategy.brand_name,
            discovered_count=len(discovered_urls),
            ingested_count=len(ingested_urls),
            missing_docs=missing,
            extra_docs=extra,
            coverage_percentage=round(coverage, 2),
            timestamp=datetime.now()
        )
        
        print(f"\n{'='*70}")
        print(f"📊 COVERAGE VERIFICATION: {strategy.brand_name}")
        print(f"{'='*70}")
        print(f"🎯 TARGET:    100% official documentation coverage")
        print(f"📚 DISCOVERED: {report.discovered_count} documents")
        print(f"✅ INGESTED:   {report.ingested_count} documents")
        print(f"📈 COVERAGE:   {report.coverage_percentage}%")
        
        if coverage >= 100:
            print(f"\n🎉 ✨ 100% COVERAGE ACHIEVED! ✨")
            print(f"   {strategy.brand_name} documentation is COMPLETE!")
        else:
            gap = 100 - coverage
            print(f"\n⚠️  GAP ANALYSIS: {gap:.1f}% coverage remaining")
            print(f"   🔴 MISSING {len(missing)} documents:")
            for url in missing:
                print(f"      • {url}")
            print(f"\n📋 NEXT ACTIONS:")
            print(f"   1. Re-run Scraper for missing URLs")
            print(f"   2. Check if URLs are still valid")
            print(f"   3. Update strategy if site structure changed")
        
        if extra:
            print(f"\n➕ BONUS: Found {len(extra)} additional documents (not in original discovery)")
        
        print(f"{'='*70}\n")
        
        # If coverage < 100%, log the gap
        if coverage < 100:
            self._log_coverage_gap(strategy.brand_name, missing)
        
        return report
    
    def _log_coverage_gap(self, brand_name: str, missing_urls: List[str]):
        """Log coverage gaps for follow-up action"""
        gap_file = f"/workspaces/Support-Center-/backend/data/strategies/{brand_name.lower().replace(' ', '_')}_gaps.txt"
        import os
        os.makedirs(os.path.dirname(gap_file), exist_ok=True)
        
        with open(gap_file, 'w') as f:
            f.write(f"# COVERAGE GAPS FOR {brand_name}\n")
            f.write(f"# Generated: {datetime.now()}\n\n")
            f.write(f"Missing {len(missing_urls)} documents:\n\n")
            for url in missing_urls:
                f.write(f"{url}\n")
        
        print(f"  💾 Coverage gaps logged to: {gap_file}")
