# Brand Website Scraping Strategy

## Current Problem
- We're scraping Halilit's distributor website (product listings only)
- We need to scrape **official brand websites** for actual documentation, manuals, specs

## Phase 1: Official Website Discovery & Mapping

### Step 1: Create Official Website Database
For each brand, we need to:
1. Identify their official website domain
2. Map it to our Brand table
3. Analyze their website structure

### Priority Brands (Musical Instruments)
| Brand | Official Website | Documentation Location |
|-------|------------------|------------------------|
| Adam Audio | https://www.adam-audio.com | /support, /downloads |
| Allen & Heath | https://www.allen-heath.com | /support/products |
| Mackie | https://mackie.com | /products (each has downloads) |
| PreSonus | https://www.presonus.com | /support |
| Roland | https://www.roland.com | /support/by_product |
| Boss | https://www.boss.info | /support |
| Rode | https://www.rode.com | /support |
| KRK Systems | https://www.krkmusic.com | /Support |
| Beyerdynamic | https://www.beyerdynamic.com | /support |
| Nord | https://www.nordkeyboards.com | /support |

## Phase 2: Website Structure Analysis

### Common Patterns Across Brand Websites

#### Pattern A: Support Portal with Product Search
- **Examples**: Roland, Boss, PreSonus
- **Strategy**: 
  1. Navigate to /support or /downloads
  2. Search for each product family
  3. Download PDFs (manuals, quick starts, specs)

#### Pattern B: Product Pages with Download Sections
- **Examples**: Mackie, Adam Audio, KRK
- **Strategy**:
  1. Crawl product catalog
  2. Extract download links from each product page
  3. Parse PDF metadata

#### Pattern C: Dedicated Downloads Section
- **Examples**: Allen & Heath, Beyerdynamic
- **Strategy**:
  1. Navigate to /downloads or /support
  2. Filter by product category
  3. Bulk download documentation

#### Pattern D: Knowledge Base / Documentation Portal
- **Examples**: Nord, Warm Audio
- **Strategy**:
  1. Scrape KB articles
  2. Download user guides
  3. Extract FAQ content

## Phase 3: Implementation Plan

### Step 1: Update Brand Table
```sql
ALTER TABLE brand ADD COLUMN official_website VARCHAR(255);
ALTER TABLE brand ADD COLUMN support_url VARCHAR(255);
ALTER TABLE brand ADD COLUMN downloads_url VARCHAR(255);
ALTER TABLE brand ADD COLUMN scraper_pattern VARCHAR(50); -- 'support_portal', 'product_pages', 'downloads_section', 'knowledge_base'
```

### Step 2: Create Brand-Specific Scraper Configs
```python
BRAND_SCRAPER_CONFIGS = {
    "Adam Audio": {
        "official_website": "https://www.adam-audio.com",
        "pattern": "product_pages",
        "product_catalog_url": "https://www.adam-audio.com/en/products",
        "selectors": {
            "product_links": ".product-item a",
            "download_section": ".downloads",
            "manual_links": "a[href$='.pdf']"
        }
    },
    "Allen & Heath": {
        "official_website": "https://www.allen-heath.com",
        "pattern": "support_portal",
        "support_url": "https://www.allen-heath.com/support/products",
        "selectors": {
            "product_search": "#product-search",
            "download_links": ".download-item a"
        }
    },
    # ... more brands
}
```

### Step 3: Scraper Priority Queue
1. **Tier 1** (High-value brands with clear documentation):
   - Adam Audio, Allen & Heath, Mackie, PreSonus, Roland
   
2. **Tier 2** (Popular brands):
   - Boss, Rode, KRK, Beyerdynamic, Nord
   
3. **Tier 3** (Niche/Specialty):
   - All remaining brands

### Step 4: Data Structure for Scraped Content

```python
class BrandDocumentation:
    - product_name: str
    - product_family: str
    - doc_type: str  # "manual", "quick_start", "spec_sheet", "faq"
    - file_url: str
    - file_name: str
    - file_size: int
    - last_updated: datetime
    - language: str
```

## Phase 4: Execution Steps

### Before Scraping (Research Phase)
1. ✅ Stop current Halilit scraping
2. ⏳ Manually visit 5-10 priority brand websites
3. ⏳ Document their exact URL patterns
4. ⏳ Test scraping on 2-3 brands manually
5. ⏳ Verify we can actually download PDFs

### During Scraping
1. Start with 1 brand (e.g., Adam Audio)
2. Verify data quality
3. Expand to 5 brands
4. Monitor success rate
5. Adjust scrapers as needed

### After Scraping
1. Index all PDFs in ChromaDB
2. Extract text from PDFs
3. Create product-documentation mapping
4. Test RAG queries

## Phase 5: Legal & Ethical Considerations

### What We CAN Scrape:
- ✅ Publicly available product manuals
- ✅ Spec sheets from support pages
- ✅ FAQ content
- ✅ Product descriptions

### What We SHOULD NOT Scrape:
- ❌ Content behind login walls
- ❌ Proprietary software
- ❌ Content with explicit "no robots" directives
- ❌ Email addresses or personal data

### Best Practices:
1. Respect robots.txt
2. Rate limit (1-2 seconds between requests)
3. Use proper User-Agent
4. Cache downloaded files (don't re-download)
5. Check for "Terms of Use" restrictions

## Next Steps

**IMMEDIATE (Before Any Scraping):**
1. Pick ONE brand (recommend: Adam Audio - clean site structure)
2. Manually explore their website
3. Document exact URLs and selectors
4. Write a test scraper for just that brand
5. Verify we can extract meaningful documentation

**THEN:**
1. Create brand_scraper_configs.py
2. Build generic scraper framework
3. Implement brand-specific adapters
4. Test on 3-5 brands
5. Scale to all 84 brands
