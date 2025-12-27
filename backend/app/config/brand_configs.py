"""
Brand-Specific Discovery Configurations

Each brand can have custom:
- URL patterns
- CSS selectors
- Discovery strategies
- Content extractors
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class BrandDiscoveryConfig(BaseModel):
    """Configuration for brand-specific discovery"""
    brand_name: str
    
    # Discovery strategies (ordered by preference)
    strategies: List[str] = ["sitemap", "common_paths", "crawl", "products"]
    
    # Custom URL patterns
    documentation_paths: List[str] = []
    product_url_pattern: Optional[str] = None
    
    # CSS selectors for content extraction
    selectors: Dict[str, str] = {
        "doc_links": "a[href*='manual'], a[href*='guide'], a[href*='pdf']",
        "product_links": "a[href*='product']",
        "download_links": "a[href$='.pdf'], a[href*='download']",
        "title": "h1, .title",
        "content": "article, main, .content"
    }
    
    # Keywords to identify documentation
    doc_keywords: List[str] = ["manual", "guide", "spec", "datasheet", "tutorial", "support"]
    
    # Rate limiting
    rate_limit_ms: int = 1000
    
    # JavaScript rendering required
    requires_js: bool = False
    
    # Maximum crawl depth
    max_crawl_depth: int = 2
    max_pages: int = 100


# Brand-specific configurations
BRAND_CONFIGS: Dict[str, BrandDiscoveryConfig] = {
    "Adam Audio": BrandDiscoveryConfig(
        brand_name="Adam Audio",
        strategies=["sitemap", "common_paths", "products", "crawl"],
        documentation_paths=[
            "/en/support",
            "/en/downloads",
            "/support",
            "/downloads",
            "/products"
        ],
        product_url_pattern="/en/products/{slug}",
        selectors={
            "doc_links": "a[href*='download'], a[href*='manual'], a.download-link",
            "product_links": "a[href*='/products/'], a.product-link",
            "download_links": "a[href$='.pdf'], a[href*='manual'], a[href*='spec']",
            "title": "h1.product-title, h1, .page-title",
            "content": "main, .product-content, .page-content"
        },
        requires_js=True,  # Adam Audio likely uses React/Vue
        max_crawl_depth=3
    ),
    
    "Allen & Heath": BrandDiscoveryConfig(
        brand_name="Allen & Heath",
        strategies=["sitemap", "products", "common_paths"],
        documentation_paths=[
            "/hardware",
            "/software",
            "/support",
            "/downloads"
        ],
        product_url_pattern="/hardware/{slug}",
        selectors={
            "doc_links": "a[href*='manual'], a[href*='downloads']",
            "product_links": "a[href*='/hardware/'], a.product-card",
            "download_links": "a[href$='.pdf'], .download-link"
        },
        requires_js=False,
        max_crawl_depth=2
    ),
    
    "Roland": BrandDiscoveryConfig(
        brand_name="Roland",
        strategies=["sitemap", "products", "common_paths"],
        documentation_paths=[
            "/global/products",
            "/global/support",
            "/us/products",
            "/us/support"
        ],
        product_url_pattern="/global/products/{slug}",
        requires_js=True,
        max_crawl_depth=2
    ),
    
    "Shure": BrandDiscoveryConfig(
        brand_name="Shure",
        strategies=["sitemap", "common_paths", "products"],
        documentation_paths=[
            "/en-US/products",
            "/en-US/support",
            "/products",
            "/support"
        ],
        selectors={
            "doc_links": "a[href*='user-guide'], a[href*='manual'], a.resource-link",
            "product_links": "a[href*='/products/']",
            "download_links": "a[href*='user-guide'], a[href*='spec-sheet']"
        },
        requires_js=True,
        max_crawl_depth=2
    ),
    
    # Default configuration for unknown brands
    "default": BrandDiscoveryConfig(
        brand_name="default",
        strategies=["sitemap", "common_paths", "crawl", "products"],
        max_crawl_depth=2
    )
}


def get_brand_config(brand_name: str) -> BrandDiscoveryConfig:
    """Get configuration for a specific brand"""
    return BRAND_CONFIGS.get(brand_name, BRAND_CONFIGS["default"])


def register_brand_config(config: BrandDiscoveryConfig):
    """Register a new brand configuration"""
    BRAND_CONFIGS[config.brand_name] = config
