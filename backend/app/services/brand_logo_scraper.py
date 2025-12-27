"""
Brand Logo and Color Scraper
Extracts official logos and brand colors from brand websites
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
from pathlib import Path
import base64
from sqlmodel import Session, select
from app.core.database import engine
from app.models.sql_models import Brand
import logging

logger = logging.getLogger(__name__)


class BrandLogoScraper:
    def __init__(self, frontend_public_path: str = "/workspaces/Support-Center-/frontend/public"):
        self.frontend_public_path = Path(frontend_public_path)
        self.logos_dir = self.frontend_public_path / "brand-logos"
        self.logos_dir.mkdir(parents=True, exist_ok=True)

    async def scrape_brand_assets(self, brand_name: str, website_url: str):
        """
        Scrape logo and brand colors from a brand's website
        Returns: dict with logo_url, primary_color, secondary_color
        """
        logger.info(f"Scraping assets for {brand_name} from {website_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                await page.goto(website_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract logo
                logo_url = await self._find_logo(page, soup, website_url)
                
                # Extract colors
                colors = await self._extract_colors(page, soup)
                
                # Download logo if it's a URL
                local_logo_path = None
                if logo_url and logo_url.startswith('http'):
                    local_logo_path = await self._download_logo(page, logo_url, brand_name)
                    if local_logo_path:
                        logo_url = f"/brand-logos/{local_logo_path.name}"
                
                return {
                    'logo_url': logo_url,
                    'primary_color': colors.get('primary', '#000000'),
                    'secondary_color': colors.get('secondary', '#FFFFFF')
                }
                
            except Exception as e:
                logger.error(f"Error scraping {brand_name}: {e}")
                return None
            finally:
                await browser.close()

    async def _find_logo(self, page, soup, base_url):
        """Find the brand logo on the page"""
        
        # Try common logo selectors
        logo_selectors = [
            'img[alt*="logo" i]',
            'img[class*="logo" i]',
            'img[id*="logo" i]',
            '.logo img',
            'header img:first-of-type',
            '.header img:first-of-type',
            'nav img:first-of-type',
            '[class*="brand"] img'
        ]
        
        for selector in logo_selectors:
            try:
                logo = await page.query_selector(selector)
                if logo:
                    src = await logo.get_attribute('src')
                    if src:
                        # Make absolute URL
                        if src.startswith('//'):
                            src = f"https:{src}"
                        elif src.startswith('/'):
                            from urllib.parse import urlparse
                            parsed = urlparse(base_url)
                            src = f"{parsed.scheme}://{parsed.netloc}{src}"
                        elif not src.startswith('http'):
                            src = f"{base_url.rstrip('/')}/{src.lstrip('/')}"
                        
                        logger.info(f"Found logo: {src}")
                        return src
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Try meta tags
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        
        return None

    async def _extract_colors(self, page, soup):
        """Extract primary and secondary brand colors"""
        colors = {'primary': '#000000', 'secondary': '#FFFFFF'}
        
        # Method 1: CSS variables
        try:
            css_vars = await page.evaluate('''() => {
                const styles = getComputedStyle(document.documentElement);
                return {
                    primary: styles.getPropertyValue('--primary-color') || 
                            styles.getPropertyValue('--brand-color') ||
                            styles.getPropertyValue('--color-primary'),
                    secondary: styles.getPropertyValue('--secondary-color') ||
                              styles.getPropertyValue('--color-secondary')
                };
            }''')
            
            if css_vars.get('primary'):
                colors['primary'] = self._normalize_color(css_vars['primary'])
            if css_vars.get('secondary'):
                colors['secondary'] = self._normalize_color(css_vars['secondary'])
                
        except Exception as e:
            logger.debug(f"CSS variables extraction failed: {e}")
        
        # Method 2: Meta tags
        theme_color = soup.find('meta', attrs={'name': 'theme-color'})
        if theme_color and theme_color.get('content'):
            colors['primary'] = self._normalize_color(theme_color['content'])
        
        # Method 3: Analyze common elements
        try:
            header_bg = await page.evaluate('''() => {
                const header = document.querySelector('header, .header, nav, .navbar');
                if (header) {
                    return getComputedStyle(header).backgroundColor;
                }
                return null;
            }''')
            
            if header_bg and not header_bg.startswith('rgba(0, 0, 0, 0)'):
                colors['primary'] = self._normalize_color(header_bg)
                
        except Exception as e:
            logger.debug(f"Header color extraction failed: {e}")
        
        return colors

    def _normalize_color(self, color_str):
        """Convert color to hex format"""
        color_str = color_str.strip()
        
        # Already hex
        if color_str.startswith('#'):
            return color_str.upper()
        
        # RGB/RGBA format
        rgb_match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color_str)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return f"#{r:02X}{g:02X}{b:02X}"
        
        return color_str

    async def _download_logo(self, page, logo_url, brand_name):
        """Download logo and save locally"""
        try:
            # Create safe filename
            safe_name = re.sub(r'[^a-z0-9-]', '-', brand_name.lower())
            extension = Path(logo_url).suffix or '.png'
            filename = f"{safe_name}{extension}"
            filepath = self.logos_dir / filename
            
            # Navigate to image and get content
            response = await page.goto(logo_url, wait_until="domcontentloaded", timeout=15000)
            if response and response.status == 200:
                content = await response.body()
                
                # Check if it's actually an image
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type or 'svg' in content_type:
                    filepath.write_bytes(content)
                    logger.info(f"Downloaded logo: {filepath}")
                    return filepath
                else:
                    logger.warning(f"URL did not return an image: {content_type}")
            
        except Exception as e:
            logger.error(f"Failed to download logo from {logo_url}: {e}")
        
        return None

    async def update_brand_in_db(self, brand_name: str):
        """Update brand with scraped logo and colors"""
        with Session(engine) as session:
            brand = session.exec(select(Brand).where(Brand.name == brand_name)).first()
            if not brand:
                logger.error(f"Brand {brand_name} not found in database")
                return False
            
            assets = await self.scrape_brand_assets(brand_name, brand.website_url)
            
            if assets:
                brand.logo_url = assets['logo_url']
                brand.primary_color = assets['primary_color']
                brand.secondary_color = assets['secondary_color']
                session.add(brand)
                session.commit()
                logger.info(f"✅ Updated {brand_name}: logo={assets['logo_url']}, colors={assets['primary_color']}/{assets['secondary_color']}")
                return True
            
            return False


async def scrape_all_brands():
    """Scrape logos and colors for all brands in the database"""
    scraper = BrandLogoScraper()
    
    with Session(engine) as session:
        brands = session.exec(select(Brand)).all()
        
        for brand in brands:
            print(f"\n{'='*80}")
            print(f"Processing: {brand.name}")
            print(f"{'='*80}")
            
            try:
                success = await scraper.update_brand_in_db(brand.name)
                if success:
                    print(f"✅ {brand.name} - Complete")
                else:
                    print(f"⚠️  {brand.name} - Failed")
            except Exception as e:
                print(f"❌ {brand.name} - Error: {e}")
            
            await asyncio.sleep(2)  # Be polite


if __name__ == "__main__":
    asyncio.run(scrape_all_brands())
