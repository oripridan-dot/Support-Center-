# Official Brand Website Scraping - Action Plan

## ✅ VERIFIED: We Can Scrape Brand Websites

### Test Results (Adam Audio)
- ✅ Product pages are accessible
- ✅ PDFs are directly downloadable (Quick Start Guides, Manuals, Spec Sheets)
- ✅ No login walls or paywalls
- ✅ robots.txt allows scraping

### Example URLs Found
```
https://www.adam-audio.com/content/uploads/2020/04/adam-audio-t-series-quick-start-guide-english-german-french-spanish-simplified-chinese-japanese.pdf
https://www.adam-audio.com/content/uploads/2018/01/ADAM_Audio_T5V_Product_Sheet.pdf
```

## Implementation Strategy

### Phase 1: Single Brand Scraper (Adam Audio)
**File:** `scripts/scrape_adam_audio.py`

```python
async def scrape_adam_audio():
    1. Visit product catalog: https://www.adam-audio.com/en/
    2. Extract all product URLs
    3. For each product:
       - Visit product page
       - Find PDF links (Quick Start, Manual, Spec Sheet)
       - Download PDFs to /backend/data/brand_docs/adam_audio/
       - Extract text from PDFs
       - Store in ChromaDB with metadata
```

### Phase 2: Multi-Brand Framework
**File:** `scripts/brand_doc_scraper.py`

```python
BRAND_CONFIGS = {
    "Adam Audio": {
        "base_url": "https://www.adam-audio.com/en/",
        "product_catalog": "/",
        "product_url_pattern": r"/en/[a-z]-series/[\w-]+/$",
        "pdf_selectors": ["a[href$='.pdf']", ".downloads a"],
    },
    "Allen & Heath": {
        "base_url": "https://www.allen-heath.com",
        ...
    }
}
```

### Phase 3: PDF Processing Pipeline
1. Download PDF
2. Extract text using `PyPDF2` or `pdfplumber`
3. Store metadata:
   - brand
   - product_name
   - doc_type (manual, quick_start, spec_sheet)
   - language
   - file_size
   - url
4. Index in ChromaDB

## Next Steps

### IMMEDIATE (Do Now)
1. ✅ Stop scraping Halilit (already done)
2. ⏳ Create `scrape_adam_audio.py` - full implementation
3. ⏳ Test with 3-5 Adam Audio products
4. ⏳ Verify PDFs are downloaded and indexed

### SHORT TERM (Next 2-3 hours)
1. Add 4-5 more brands (Allen & Heath, Mackie, PreSonus, Roland)
2. Create generic `BrandDocScraper` class
3. Run full scrape for priority brands

### MEDIUM TERM (Next day)
1. Update Brand table with official websites
2. Create monitoring dashboard
3. Schedule periodic re-scraping

## File Structure
```
backend/
  data/
    brand_docs/          # Downloaded PDFs
      adam_audio/
        T5V_manual.pdf
        T5V_quick_start.pdf
      allen_heath/
        SQ5_user_guide.pdf
  scripts/
    scrape_adam_audio.py      # Single brand test
    brand_doc_scraper.py       # Generic framework
    test_adam_audio_official.py # Already created
```

## Success Criteria
- [ ] Download 20+ PDFs from Adam Audio
- [ ] Extract text and index in ChromaDB
- [ ] Query RAG system: "What's the frequency response of T5V?"
- [ ] Get answer from the official manual

## Legal & Ethical ✅
- robots.txt allows scraping
- PDFs are publicly available
- We're an authorized distributor
- No login/paywall bypass
- Proper attribution in responses
