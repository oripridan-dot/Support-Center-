import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging
from app.services.rag_service import ingest_document
from app.core.database import Session, engine
from app.models.sql_models import Brand, Product, ProductFamily, Document
from app.services.ingestion_tracker import tracker
from sqlmodel import select
import datetime
import re
import json

from app.models.ingestion_status import IngestionStatus

logger = logging.getLogger(__name__)

class PABrandsScraper:
    def __init__(self, force_rescan=False):
        self.force_rescan = force_rescan
        # Priority brands from HALILIT_BRANDS_LIST.md - focusing on those with accessible documentation
        self.brands_to_scrape = [
            # Tier 1: Audio Interfaces & Monitoring (High Priority)
            {"name": "Krk Systems", "url": "https://www.krkmusic.com/products"},
            {"name": "Adam Audio", "url": "https://www.adam-audio.com/en/products/"},
            {"name": "Universal Audio", "url": "https://www.uaudio.com/products.html"},
            {"name": "Avid", "url": "https://www.avid.com/products"},
            {"name": "Presonus", "url": "https://www.presonus.com/products"},
            
            # Tier 2: Mixing & Recording (High Priority)
            {"name": "Allen & Heath", "url": "https://www.allen-heath.com/hardware/"},
            {"name": "Mackie", "url": "https://mackie.com/en/products"},
            {"name": "Warm Audio", "url": "https://warmaudio.com/products/"},
            {"name": "Steinberg", "url": "https://www.steinberg.net/en/products.html"},
            {"name": "Eve Audio", "url": "https://eve-audio.de/index.php?page=products"},
            
            # Tier 3: Speakers & PA (High Priority)
            {"name": "RCF", "url": "https://www.rcf.it/en/products"},
            {"name": " Eaw Eastern Acoustic Works ", "url": "https://eaw.com/products/"},
            {"name": "Montarbo", "url": "https://www.montarbo.com/en/products"},
            
            # Tier 4: Accessories & Stands
            {"name": "Ultimate Support", "url": "https://www.ultimatesupport.com/collections/all"},
            {"name": "On Stage", "url": "https://on-stage.com/products"},
            
            # Tier 5: Keyboards & Controllers
            {"name": "Roland", "url": "https://www.roland.com/global/products/"},
            {"name": "Nord", "url": "https://www.nordkeyboards.com/products"},
            {"name": "Boss", "url": "https://www.boss.info/global/products/"},
            {"name": "Akai Professional", "url": "https://www.akaipro.com/products"},
        ]

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            for brand_info in self.brands_to_scrape:
                logger.info(f"Starting scrape for {brand_info['name']}")
                tracker.start(brand_info['name'])
                
                with Session(engine) as session:
                    brand = session.exec(select(Brand).where(Brand.name == brand_info['name'])).first()
                    
                    if not brand:
                        logger.error(f"Brand {brand_info['name']} not found in DB")
                        tracker.update_progress({"errors": [{"message": f"Brand {brand_info['name']} not found in DB"}]})
                        continue

                    page = await context.new_page()
                    try:
                        tracker.update_progress({"current_step": "Navigating to brand page"})
                        await page.goto(brand_info['url'], wait_until='domcontentloaded', timeout=90000)
                        
                        if "Allen Heath" in brand_info['name']:
                            await self.scrape_allen_heath(page, brand, session)
                        elif brand_info['name'] == "Mackie":
                            await self.scrape_mackie(page, brand, session)
                        elif brand_info['name'] == "RCF":
                            await self.scrape_rcf(page, brand, session)
                        else:
                            # Generic scraper for others
                            await self.scrape_generic_brand(page, brand, session)
                            
                    except Exception as e:
                        logger.error(f"Error scraping {brand_info['name']}: {e}")
                        tracker.update_progress({"errors": [{"message": str(e)}]})
                    finally:
                        await page.close()
            
            tracker.update_progress({"is_running": False, "progress_percent": 100})
            await browser.close()

    async def scrape_generic_brand(self, page, brand, session):
        """
        Scrape individual product pages (NOT category/collection pages).
        Strategy: Look for links that go to specific product pages with documentation.
        """
        links = await page.query_selector_all("a")
        product_links = []
        
        for link in links:
            href = await link.get_attribute("href")
            if not href or len(href) < 10:
                continue
                
            # Skip category/collection pages - they just list products
            skip_patterns = [
                '/collections/',  # Shopify collections (lists)
                '/products/controllers.html',  # Category listings
                '/products/keyboards.html',
                '/products/new-products.html',
                '/products/drum-machines.html',
                '/category/',
                '/categories/',
                '?t=',  # Query parameters for filtering categories
                '-series',  # Series pages like "studiolive-classic", "rokit-series"
                '-accessories',  # Accessory categories
                'plug-ins',  # Plugin collections
                'audio-interfaces',  # Interface categories
                'workstations',  # Workstation categories
                'amplifier-stands',  # Stand categories
                'keyboard-stand',  # Keyboard stand categories
                'mic-stands',  # Mic stand categories
            ]
            
            # Skip if URL matches any skip pattern
            href_lower = href.lower()
            if any(pattern in href_lower for pattern in skip_patterns):
                continue
            
            # Look for individual product pages
            # These typically have specific model names/numbers in URL
            if ('/products/' in href or '/product/' in href) and not href.endswith('/products/') and not href.endswith('/products.html'):
                if not href.startswith('http'):
                    base = "/".join(page.url.split('/')[:3])
                    href = base + (href if href.startswith('/') else '/' + href)
                
                # Additional filter: individual product pages usually have longer paths
                # e.g., /products/mpk-mini-mk3 (good) vs /products/ (bad)
                path_parts = href.split('/')
                if len(path_parts) >= 5:  # Must have at least: https, '', domain, products, model-name
                    # PRIORITY: Products with model numbers (digits) - these are actual products
                    product_name = path_parts[-1].lower()
                    has_digits = any(c.isdigit() for c in product_name)
                    
                    if has_digits:
                        # High priority - likely a real product model (e.g., mpk-mini-mk3, rokit-5-g4)
                        product_links.insert(0, href)  # Add to front
                    else:
                        product_links.append(href)
        
        product_links = list(set(product_links))[:100]  # Increased limit for production
        
        # Update tracker with discovered URLs
        tracker.update_progress({
            "urls_discovered": len(product_links),
            "current_step": f"Found {len(product_links)} products"
        })
        
        # Update DB status with discovered URLs
        try:
            status = session.exec(select(IngestionStatus).where(IngestionStatus.brand_id == brand.id)).first()
            if status:
                status.urls_discovered = len(product_links)
                status.updated_at = datetime.datetime.now()
                session.add(status)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update DB status for {brand.name}: {e}")

        for i, url in enumerate(product_links):
            name = url.split('/')[-1].replace('-', ' ').replace('.html', '').title()
            if not name: continue
            logger.info(f"Processing {brand.name} product: {name}")
            
            tracker.update_progress({
                "current_step": f"Processing {name}",
                "current_document": url,
                "urls_processed": i + 1,
                "progress_percent": ((i + 1) / len(product_links)) * 100
            })
            
            product = session.exec(select(Product).where(Product.name == name)).first()
            if not product:
                family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == brand.id)).first()
                if not family:
                    family = ProductFamily(name="General", brand_id=brand.id)
                    session.add(family)
                    session.commit()
                    session.refresh(family)
                product = Product(name=name, family_id=family.id)
                session.add(product)
                session.commit()
                session.refresh(product)

            await self.scrape_generic_product_page(page, url, brand.id, product.id, brand.name)

    async def scrape_allen_heath(self, page, brand, session):
        # Allen & Heath products are listed in categories
        logger.info("Scraping Allen & Heath products...")
        
        # Try to load links from file if it exists
        product_links = []
        try:
            import os
            links_file = "/workspaces/Support-Center-/backend/ah_product_links.txt"
            if os.path.exists(links_file):
                with open(links_file, "r") as f:
                    product_links = [line.strip() for line in f if line.strip()]
                logger.info(f"Loaded {len(product_links)} AH links from file")
        except Exception as e:
            logger.warning(f"Could not load AH links from file: {e}")

        if not product_links:
            # Fallback to crawling if file doesn't exist
            try:
                await Stealth().apply_stealth_async(page)
                await page.goto("https://www.allen-heath.com/hardware/", wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5)
                
                links = await page.query_selector_all("a")
                for link in links:
                    href = await link.get_attribute("href")
                    if href and ('/products/' in href or '/hardware/' in href) and not href.endswith('/products/') and not href.endswith('/hardware/'):
                        if not href.startswith('http'):
                            href = "https://www.allen-heath.com" + href
                        href = href.split('#')[0].split('?')[0]
                        if href.endswith('/'): href = href[:-1]
                        product_links.append(href)
                product_links = list(set(product_links))
            except Exception as e:
                logger.error(f"Error crawling AH links: {e}")

        logger.info(f"Processing {len(product_links)} Allen & Heath products")
        
        for i, url in enumerate(product_links):
            try:
                # Check if already ingested
                if not self.force_rescan:
                    existing_doc = session.exec(select(Document).where(Document.url == url)).first()
                    if existing_doc:
                        logger.info(f"Skipping already ingested AH product: {url}")
                        continue

                name = url.split('/')[-1].replace('-', ' ').title()
                if not name or name == 'Products': 
                    name = url.split('/')[-2].replace('-', ' ').title()
                
                logger.info(f"Processing Allen & Heath product: {name}")
                
                tracker.update_progress({
                    "current_step": f"Processing {name}",
                    "current_document": url,
                    "urls_processed": i + 1,
                    "progress_percent": ((i + 1) / len(product_links)) * 100
                })
                
                product = session.exec(select(Product).where(Product.name == name)).first()
                if not product:
                    family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == brand.id)).first()
                    if not family:
                        family = ProductFamily(name="General", brand_id=brand.id)
                        session.add(family)
                        session.commit()
                        session.refresh(family)
                    product = Product(name=name, family_id=family.id)
                    session.add(product)
                    session.commit()
                    session.refresh(product)

                # Use a new page for each product to apply stealth properly
                product_page = await page.context.new_page()
                try:
                    await Stealth().apply_stealth_async(product_page)
                    await self.scrape_generic_product_page(product_page, url, brand.id, product.id, brand.name)
                finally:
                    await product_page.close()
                    
            except Exception as e:
                logger.error(f"Error processing AH product {url}: {e}")

    async def scrape_mackie(self, page, brand, session):
        # Mackie products
        logger.info("Scraping Mackie products...")
        tracker.update_progress({"current_step": "Discovering Mackie products"})
        
        await page.goto("https://mackie.com/en/products", wait_until='domcontentloaded')
        await asyncio.sleep(5)
        
        # Scroll multiple times to load all products
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
        
        links = await page.query_selector_all("a")
        product_links = []
        for link in links:
            href = await link.get_attribute("href")
            # Mackie product links usually end in .html and are deep in the products tree
            if href and '/products/' in href and href.endswith('.html') and len(href.split('/')) > 4:
                if not href.startswith('http'):
                    href = "https://mackie.com" + href
                product_links.append(href)
        
        product_links = list(set(product_links))
        logger.info(f"Found {len(product_links)} Mackie product links")
        
        tracker.update_progress({
            "urls_discovered": len(product_links),
            "current_step": f"Found {len(product_links)} Mackie products"
        })
        
        # Process more products for Mackie
        for i, url in enumerate(product_links[:50]): 
            try:
                name = url.split('/')[-1].replace('-', ' ').replace('.html', '').title()
                logger.info(f"Processing Mackie product: {name}")
                
                tracker.update_progress({
                    "current_step": f"Processing {name}",
                    "current_document": url,
                    "urls_processed": i + 1,
                    "progress_percent": ((i + 1) / min(len(product_links), 50)) * 100
                })
                
                product = session.exec(select(Product).where(Product.name == name)).first()
                if not product:
                    family_name = url.split('/')[-2].replace('-', ' ').title()
                    family = session.exec(select(ProductFamily).where(ProductFamily.name == family_name)).first()
                    if not family:
                        family = ProductFamily(name=family_name, brand_id=brand.id)
                        session.add(family)
                        session.commit()
                        session.refresh(family)
                    product = Product(name=name, family_id=family.id)
                    session.add(product)
                    session.commit()
                    session.refresh(product)

                await self.scrape_generic_product_page(page, url, brand.id, product.id, brand.name)
            except Exception as e:
                logger.error(f"Error processing Mackie product {url}: {e}")

    async def scrape_rcf(self, page, brand, session):
        # RCF products - use sitemap-extracted links if available
        logger.info("Scraping RCF products...")
        
        import os
        links_file = "rcf_links.txt"
        all_product_links = []
        
        if os.path.exists(links_file):
            logger.info(f"Loading RCF links from {links_file}")
            with open(links_file, "r") as f:
                all_product_links = [line.strip() for line in f if line.strip()]
        else:
            logger.info("rcf_links.txt not found, falling back to category scraping...")
            categories = [
                "https://www.rcf.it/en/pro-sound",
                "https://www.rcf.it/en/live-sound",
                "https://www.rcf.it/en/installed-sound",
                "https://www.rcf.it/en/recording",
                "https://www.rcf.it/en/transducers"
            ]
            
            cat_links = set()
            for cat_url in categories:
                try:
                    logger.info(f"Visiting RCF category: {cat_url}")
                    await page.goto(cat_url, wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(8) # Wait for JS grid
                    
                    # Try to click "Accept" on cookie banner if it exists
                    try:
                        cookie_btn = await page.query_selector("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                        if cookie_btn:
                            await cookie_btn.click()
                            await asyncio.sleep(2)
                    except:
                        pass

                    # Scroll to load more
                    for _ in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)
                    
                    links = await page.query_selector_all("a")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and '/product-detail/' in href:
                            if not href.startswith('http'):
                                href = "https://www.rcf.it" + href
                            cat_links.add(href)
                except Exception as e:
                    logger.error(f"Error scraping RCF category {cat_url}: {e}")
            all_product_links = list(cat_links)
        
        logger.info(f"Found {len(all_product_links)} RCF product links")
        
        # Process a batch of products
        batch_links = all_product_links[:100]
        for i, url in enumerate(batch_links): # Increased limit for RCF
            try:
                name = url.split('/')[-1].replace('-', ' ').title()
                logger.info(f"Processing RCF product: {name}")
                
                tracker.update_progress({
                    "current_step": f"Processing {name}",
                    "current_document": url,
                    "urls_processed": i + 1,
                    "progress_percent": ((i + 1) / len(batch_links)) * 100
                })
                
                product = session.exec(select(Product).where(Product.name == name)).first()
                if not product:
                    # Try to infer family from URL or just use General
                    family = session.exec(select(ProductFamily).where(ProductFamily.brand_id == brand.id)).first()
                    if not family:
                        family = ProductFamily(name="General", brand_id=brand.id)
                        session.add(family)
                        session.commit()
                        session.refresh(family)
                    product = Product(name=name, family_id=family.id)
                    session.add(product)
                    session.commit()
                    session.refresh(product)

                await self.scrape_generic_product_page(page, url, brand.id, product.id, brand.name)
            except Exception as e:
                logger.error(f"Error processing RCF product {url}: {e}")

    async def scrape_generic_product_page(self, page, url, brand_id, product_id, brand_name=""):
        try:
            logger.info(f"Scraping product page: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3) # Wait for content
            
            # Check for "Page not Sound" or 404
            title = await page.title()
            if "Page not Sound" in title or "404" in title:
                logger.warning(f"Skipping {url} - Page not found or blocked")
                return

            # Language Check (Strict English)
            lang = await page.evaluate("document.documentElement.lang")
            if lang and not lang.lower().startswith('en') and len(lang) > 0:
                logger.warning(f"Skipping {url} - Non-English language detected: {lang}")
                return

            # Special handling for RCF tabs
            if "rcf.it" in url:
                try:
                    # Try to click Specifications tab to ensure it's loaded/visible
                    tabs = await page.query_selector_all("a")
                    for tab in tabs:
                        text = await tab.inner_text()
                        if 'SPECIFICATIONS' in text.upper():
                            await tab.click()
                            await asyncio.sleep(1)
                            break
                except:
                    pass

            # 1. Extract all images and illustrations
            images = await page.query_selector_all("img")
            image_urls = []
            for img in images:
                try:
                    src = await img.get_attribute("src")
                    alt = await img.get_attribute("alt") or ""
                    
                    # Filter out small icons, logos, etc.
                    if src and not src.startswith('data:') and (len(alt) > 3 or 'product' in src.lower() or 'hero' in src.lower() or 'gallery' in src.lower()):
                        # Basic relevance check
                        if any(kw in alt.lower() or kw in src.lower() for kw in ['product', 'hero', 'main', 'gallery', 'large']):
                            if not src.startswith('http'):
                                base = "/".join(page.url.split('/')[:3])
                                src = base + (src if src.startswith('/') else '/' + src)
                            image_urls.append({"url": src, "alt": alt})
                except:
                    continue
            
            # 2. Extract all PDF links (Manuals, Datasheets) - PRIORITIZED
            links = await page.query_selector_all("a")
            pdf_links = []
            documentation_links = []  # For non-PDF documentation pages
            
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    text_lower = text.strip().lower()
                    
                    # Priority 1: PDF manuals and documentation
                    if href and href.lower().endswith('.pdf'):
                        # Filter for English manuals
                        title_upper = text.strip().upper()
                        url_upper = href.upper()
                        
                        is_english = any(kw in title_upper or kw in url_upper for kw in ["ENGLISH", " EN ", "_EN", "MANUAL", "USER GUIDE", "DATASHEET", "QUICK START", "REFERENCE"])
                        is_other_lang = any(kw in title_upper for kw in ["FRENCH", "GERMAN", "ITALIAN", "SPANISH", "CHINESE", "FRANCAIS", "DEUTSCH", "ITALIANO", "ESPANOL"])
                        
                        if is_english or not is_other_lang:
                            if not href.startswith('http'):
                                base = "/".join(page.url.split('/')[:3])
                                href = base + (href if href.startswith('/') else '/' + href)
                            
                            # Prioritize manuals over other PDFs
                            is_manual = any(kw in text_lower for kw in ['manual', 'user guide', 'reference', 'documentation'])
                            if is_manual:
                                pdf_links.insert(0, {"url": href, "title": text.strip() or "PDF Document"})
                            else:
                                pdf_links.append({"url": href, "title": text.strip() or "PDF Document"})
                    
                    # Priority 2: Support/Documentation pages (non-PDF)
                    elif href and any(kw in text_lower for kw in ['support', 'documentation', 'specs', 'specifications', 'downloads', 'resources']):
                        if not href.startswith('http'):
                            base = "/".join(page.url.split('/')[:3])
                            href = base + (href if href.startswith('/') else '/' + href)
                        documentation_links.append({"url": href, "title": text.strip()})
                except:
                    continue

            # 3. Extract structured text (Features, Specs)
            content_parts = []
            
            # Try to find specific sections by common classes/IDs
            selectors = [
                (".product-features, .features, #features, .features-list", "FEATURES"),
                (".product-specs, .specs, #specs, .specifications, .technical-specs, #technical-specifications", "SPECIFICATIONS"),
                (".product-description, .description, #description, .overview, .product-overview", "OVERVIEW")
            ]
            
            for selector, label in selectors:
                el = await page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    if len(text.strip()) > 50:
                        content_parts.append(f"### {label}\n{text.strip()}")

            # Fallback: If no structured sections found, try to find by text content
            if not content_parts:
                # Look for elements containing keywords
                for keyword, label in [("Features", "FEATURES"), ("Specifications", "SPECIFICATIONS"), ("Overview", "OVERVIEW")]:
                    try:
                        el = await page.evaluate_handle(f"""() => {{
                            const headers = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, b, strong'));
                            const header = headers.find(h => h.textContent.includes('{keyword}'));
                            if (header && header.parentElement) return header.parentElement;
                            return null;
                        }}""")
                        if el:
                            text = await el.evaluate('node => node.innerText')
                            if len(text.strip()) > 50:
                                content_parts.append(f"### {label}\n{text.strip()}")
                    except:
                        continue

            # Final Fallback: Full body text
            if not content_parts:
                text = await page.evaluate("() => document.body.innerText")
                lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 20]
                clean_text = "\n".join(lines)
                content_parts.append(clean_text)
            
            final_text = "\n\n".join(content_parts)

            # 4. Ingest into RAG with rich metadata
            import json
            from app.services.rag_service import ingest_document
            
            metadata = {
                "brand_id": int(brand_id) if brand_id is not None else 0,
                "brand": brand_name,
                "product_id": int(product_id) if product_id is not None else 0,
                "url": str(url) if url else "",
                "source_url": str(url) if url else "",
                "source": "official_website",
                "title": title.strip() if title else "Product Page",
                "images": json.dumps(image_urls[:10]) if image_urls else "[]", 
                "pdfs": json.dumps(pdf_links[:10]) if pdf_links else "[]",    
            }
            
            if image_urls and image_urls[0].get('url'):
                metadata["image_url"] = str(image_urls[0]['url'])
            else:
                metadata["image_url"] = ""

            # Ensure no None values in metadata
            for key, value in metadata.items():
                if value is None:
                    metadata[key] = ""

            # Only ingest if we have meaningful content OR PDFs
            if len(final_text) > 300 or pdf_links:
                await ingest_document(final_text, metadata, document_id=url)
                
                # 5. Save document record in DB and update product image
                with Session(engine) as session:
                    doc = Document(
                        title=f"Product Page: {url.split('/')[-1]}",
                        url=url,
                        brand_id=brand_id,
                        product_id=product_id,
                        last_updated=datetime.datetime.now()
                    )
                    session.add(doc)
                    
                    # Update product image if not set
                    if product_id and metadata.get("image_url"):
                        product = session.exec(select(Product).where(Product.id == product_id)).first()
                        if product and not product.image_url:
                            product.image_url = metadata["image_url"]
                            session.add(product)
                    
                    session.commit()
                
                logger.info(f"Successfully ingested rich info for product {product_id}")
            else:
                logger.warning(f"Skipping {url} - Insufficient content ({len(final_text)} chars) and no PDFs")
        except Exception as e:
            logger.error(f"Error scraping product page {url}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = PABrandsScraper()
    asyncio.run(scraper.run())
