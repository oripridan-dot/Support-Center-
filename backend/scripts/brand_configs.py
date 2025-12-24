"""
Brand Website Scraper Configurations
Defines scraping strategies for different brand websites
"""

BRAND_CONFIGS = {
    "Adam Audio": {
        "base_url": "https://www.adam-audio.com",
        "product_catalog_url": "/en/",
        "product_url_pattern": r"/en/[a-z]-series/[\w-]+/$",
        "pdf_selectors": ["a[href$='.pdf']"],
        "exclude_products": ["s-control", "accessories", "mounting-plate"]
    },
    
    "Allen & Heath": {
        "base_url": "https://www.allen-heath.com",
        "product_catalog_url": "/support/products",
        "support_portal": True,
        "search_url": "/support/products?search=",
        "pdf_selectors": [".download-link", "a[href*='.pdf']"]
    },
    
    "Mackie": {
        "base_url": "https://mackie.com",
        "product_catalog_url": "/en/products",
        "product_categories": [
            "/en/products/mixers",
            "/en/products/studio-monitors",
            "/en/products/powered-loudspeakers"
        ],
        "pdf_selectors": ["a[href*='download']", "a[href$='.pdf']"]
    },
    
    "PreSonus": {
        "base_url": "https://www.presonus.com",
        "product_catalog_url": "/products",
        "support_url": "/support",
        "pdf_selectors": [".download-item a", "a[href$='.pdf']"]
    },
    
    "Roland": {
        "base_url": "https://www.roland.com",
        "product_catalog_url": "/global/products",
        "support_url": "/global/support",
        "pdf_selectors": [".download-link", "a[href*='manual']"]
    },
    
    "Boss": {
        "base_url": "https://www.boss.info",
        "product_catalog_url": "/global/products",
        "support_url": "/global/support",
        "pdf_selectors": [".pdf-download", "a[href$='.pdf']"]
    },
    
    "KRK Systems": {
        "base_url": "https://www.krkmusic.com",
        "product_catalog_url": "/Products",
        "pdf_selectors": ["a[href*='download']", "a[href$='.pdf']"]
    },
    
    "Rode": {
        "base_url": "https://www.rode.com",
        "product_catalog_url": "/microphones",
        "support_url": "/support",
        "pdf_selectors": [".download-link", "a[href$='.pdf']"]
    }
}

def get_brand_config(brand_name):
    """Get configuration for a brand"""
    return BRAND_CONFIGS.get(brand_name)

def list_configured_brands():
    """List all brands with configurations"""
    return list(BRAND_CONFIGS.keys())
