# Comprehensive Ingestion Plan for Support Center
## 100% Coverage Strategy with Optimized Accuracy, Speed, and Media Attachment

**Date:** December 23, 2025
**Status:** Active

---

## 1. CURRENT STATE ANALYSIS

### Ingested Brands
| Brand | Documents | Status | Completeness |
|-------|-----------|--------|--------------|
| Allen & Heath | 117 | Active | ~40% |
| RCF | 1,236 | Active | ~95% |
| Montarbo | 61 | Active | ~60% |
| All others | 0 | Not Started | 0% |

### Removed Brands (Dec 23, 2025)
- dBTechnologies (28 docs removed)
- Marshall (0 docs removed)
- Ampeg (0 docs removed)  
- Spector (0 docs removed)

---

## 2. INGESTION OPTIMIZATION STRATEGY

### 2.1 Accuracy Optimization
**Principle:** Only official documentation from brand sites

- ✅ Official brand websites (.com, .it, .org domains)
- ✅ Official manuals/PDFs from brand knowledge bases
- ✅ Official product specification sheets
- ❌ Third-party retailer content (Thomann, Sweetwater, etc.)
- ❌ Forum posts or user-generated content
- ❌ Outdated/deprecated product pages

**Implementation:**
- Use robots.txt compliant scraping
- Verify domain ownership before ingestion
- Timestamp all documents with last-verified date
- Deduplicate identical content across pages
- Extract structured data (specs, manuals, downloads)

### 2.2 Speed Optimization
**Principle:** Fast ingestion while maintaining quality

- **Parallel scraping:** 5-10 concurrent requests per brand
- **Caching strategy:** Skip unchanged pages (content hash comparison)
- **Chunking:** 1500-char chunks with 200-char overlap for RAG
- **Batch processing:** Ingest in 50-100 URL batches with 5-15s delays
- **Database indexing:** Ensure vector DB has proper metadata indices
- **Metadata efficiency:** Store only essential fields (brand_id, product_id, source, title)

### 2.3 Media Attachment Strategy (100% Relevant Context)
**Principle:** Every response includes official media with 100% relevance

**Media Types to Attach:**
1. **Brand Logo** - Always attach to responses (official PNG/SVG)
2. **Product Images** - Attach if query is product-specific
3. **Technical Diagrams** - Attach if query involves specifications/connections
4. **Official Manuals/PDFs** - Link in response with snippet context
5. **Specification Sheets** - Embed or link with direct reference

**Implementation in RAG:**
- Store media URLs in metadata for each ingested document
- Create a `media_store` table with:
  - `id`, `brand_id`, `product_id`, `media_type`, `url`, `alt_text`, `relevance_score`
- Filter media by relevance to query context
- Ensure all media is sourced from official brand domains only
- Verify media URLs are still live before returning to user

---

## 3. BRAND-BY-BRAND INGESTION PLAN

### Phase 1: Complete Allen & Heath (PRIORITY)
**Current:** 117 documents (~40% coverage)
**Target:** 500+ documents (95%+ coverage)

**Missing Coverage:**
- [ ] Support/Knowledge Base (all articles)
- [ ] Downloadable software & firmware
- [ ] Video tutorials & quick start guides
- [ ] API documentation (if available)
- [ ] Compatibility matrices
- [ ] System requirements documents
- [ ] Troubleshooting guides
- [ ] Official case studies
- [ ] All product pages (ensure 100% product line coverage)

**Sources:**
1. `https://www.allen-heath.com/` - Main product catalog
2. `https://www.allen-heath.com/support/` - Support pages
3. `https://www.allen-heath.com/downloads/` - Firmware/manuals
4. `https://www.allen-heath.com/technical/` - Technical specs

**Execution:**
```bash
# Run comprehensive Allen & Heath ingestion
PYTHONPATH=. python scripts/ingest_ah_complete.py
```

---

### Phase 2: Optimize RCF (1,236 docs - Most complete)
**Status:** ~95% complete - Verify coverage is comprehensive

**Tasks:**
- [ ] Audit existing documents for quality
- [ ] Verify all product lines are covered
- [ ] Ensure all support pages are ingested
- [ ] Check for duplicates and consolidate
- [ ] Verify media attachments are proper

**Action:**
```bash
PYTHONPATH=. python scripts/audit_rcf_ingestion.py
PYTHONPATH=. python scripts/dedup_vectors.py RCF
```

---

### Phase 3: Complete Montarbo (61 docs - ~60%)
**Current:** 61 documents
**Target:** 300+ documents (90% coverage)

**Missing:**
- [ ] All support documentation
- [ ] System requirements
- [ ] Firmware updates & changelogs
- [ ] Configuration guides
- [ ] Integration guides (if available)
- [ ] Video tutorials

**Action:**
```bash
PYTHONPATH=. python scripts/ingest_montarbo_complete.py
```

---

### Phase 4: Expand to Supporting Brands
**Priority Brands** (Based on music equipment relevance):

1. **Rode** - Professional microphones
   - Target: 200+ documents
   - Focus: Mics, wireless systems, support docs
   
2. **Boss** - Effects/processors
   - Target: 150+ documents
   - Focus: Pedals, multi-effects, drivers/software
   
3. **Roland** - Music synthesizers/keyboards
   - Target: 250+ documents
   - Focus: Keyboards, digital pianos, sound modules, drivers
   
4. **Mackie** - Studio monitoring/mixing
   - Target: 180+ documents
   - Focus: Speakers, mixing consoles, interfaces
   
5. **PreSonus** - Studio hardware/software
   - Target: 200+ documents
   - Focus: Interfaces, mixers, DAW documentation
   
6. **Beyerdynamic** - Professional headphones/mics
   - Target: 150+ documents
   - Focus: Headphones, microphones, wireless systems
   
7. **Adam Audio** - Studio monitors
   - Target: 100+ documents
   - Focus: Speakers, specs, setup guides

**Lower Priority** (Niche/Supporting):
- Nord, Krk Systems, Heritage Audio, Ashdown Engineering, etc.

---

## 4. TECHNICAL IMPLEMENTATION

### 4.1 Enhanced Ingestion Engine

```python
# Updated ingestion_engine.py should support:

class AdvancedIngestionEngine:
    """
    Features:
    - Parallel scraping with rate limiting
    - Media extraction and storage
    - Content deduplication
    - Metadata enrichment
    - Quality scoring
    - Error recovery with retries
    """
    
    async def ingest_with_media(
        self,
        url: str,
        brand_id: int,
        extract_media: bool = True,
        verify_official: bool = True
    ):
        # 1. Verify domain is official
        # 2. Scrape content
        # 3. Extract images/pdfs/media
        # 4. Store in document with media references
        # 5. Generate embeddings
        # 6. Store in ChromaDB
        # 7. Index media in media_store table
```

### 4.2 New Data Models

```python
# Add to sql_models.py

class Media(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    media_type: str  # "logo", "screenshot", "diagram", "manual", "spec_sheet"
    alt_text: Optional[str] = None
    brand_id: int = Field(foreign_key="brand.id")
    product_id: Optional[int] = Field(foreign_key="product.id")
    relevance_score: float = 1.0  # 0-1, where 1 = highly relevant
    last_verified: datetime = Field(default_factory=datetime.utcnow)
    
    brand: Brand = Relationship(back_populates="media")
    product: Optional[Product] = Relationship(back_populates="media")

class IngestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int
    url: str
    status: str  # "success", "failed", "skipped"
    reason: Optional[str] = None
    documents_created: int = 0
    media_attached: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ingestion_time_ms: int = 0
```

### 4.3 RAG Enhancement

```python
# Updated rag_service.py ask_question() should:

async def ask_question_with_media(
    question: str,
    brand_id: int = None,
    return_media: bool = True
):
    """
    Enhanced RAG that:
    1. Queries vector DB for context
    2. Retrieves relevant media (logo, images, manuals)
    3. Filters media by relevance_score > 0.7
    4. Ensures all media is from official sources
    5. Returns response with attached media URIs
    """
    
    # Query vector DB
    context_docs = collection.query(...)
    
    # Get relevant media
    if return_media:
        media = get_relevant_media(context_docs, brand_id, question)
        
        # Always include brand logo
        brand_logo = get_brand_logo(brand_id)
        
        # Sort media by relevance
        media = sorted(media, key=lambda x: x.relevance_score, reverse=True)
    
    # Generate response with media
    response = {
        "answer": answer_text,
        "media": {
            "brand_logo": brand_logo,
            "relevant_documents": [m.url for m in media[:5]],  # Top 5 relevant
            "product_images": [m.url for m in media if m.media_type == "screenshot"],
            "manual_links": [m.url for m in media if m.media_type == "manual"]
        }
    }
    return response
```

---

## 5. EXECUTION ROADMAP

### Week 1 (This Week)
- ✅ Drop deprecated brands
- [ ] Complete Allen & Heath ingestion (run comprehensive scraper)
- [ ] Create enhanced ingestion engine
- [ ] Add Media table to database

### Week 2
- [ ] Audit and optimize RCF
- [ ] Complete Montarbo ingestion
- [ ] Implement media attachment in RAG
- [ ] Test responses with media

### Week 3
- [ ] Ingest Rode documentation
- [ ] Ingest Boss documentation
- [ ] Ingest Roland documentation
- [ ] Performance testing

### Week 4
- [ ] Ingest remaining priority brands
- [ ] Deduplication across all brands
- [ ] Vector DB optimization
- [ ] QA and accuracy verification

---

## 6. QUALITY ASSURANCE CHECKLIST

### For Each Brand/Ingestion:
- [ ] All official product pages included
- [ ] Support documentation complete
- [ ] Manuals/PDFs properly extracted
- [ ] No duplicate content in ChromaDB
- [ ] Media URLs verified and live
- [ ] Content hash tracking enabled
- [ ] Metadata complete (brand_id, product_id, title)
- [ ] Ingestion logs recorded
- [ ] Response time < 2 seconds
- [ ] Answer accuracy verified against official docs

### Content Quality Scoring:
```
✅ Excellent (95-100%): Official docs, complete product line, media attached
✅ Good (80-94%): Most official docs, most products, some media
⚠️  Fair (60-79%): Partial coverage, limited media
❌ Poor (<60%): Incomplete, unreliable sources
```

---

## 7. PERFORMANCE TARGETS

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| Query response time | < 2 sec | TBD | Full RAG pipeline |
| Accuracy on official docs | > 95% | TBD | Against benchmark |
| Media attachment rate | 100% | 0% | Every response |
| Brand coverage | 100% of priority | 40% | Allen/RCF/Montarbo |
| Uptime | 99.9% | TBD | API availability |
| Duplicate content | < 1% | TBD | Deduplication needed |

---

## 8. FILES TO CREATE/MODIFY

### New Scripts
- `scripts/ingest_ah_complete.py` - Complete Allen & Heath
- `scripts/audit_rcf_ingestion.py` - Audit RCF coverage
- `scripts/dedup_vectors.py` - Remove duplicates from ChromaDB
- `scripts/ingest_brand_complete_runner.py` - Master runner for all brands

### Modified Files
- `app/models/sql_models.py` - Add Media, IngestLog models
- `app/engines/ingestion_engine.py` - Enhanced with media extraction
- `app/services/rag_service.py` - Add media attachment logic
- `app/api/chat.py` - Return media in responses

### Configuration
- `app/core/config.py` - Add OFFICIAL_DOMAINS whitelist
- `.env` - Add parallelization settings

---

## 9. RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Duplicate content bloating DB | Implement content-hash deduplication before insertion |
| Outdated media links | Verify all URLs weekly, mark as stale if 404 |
| Incomplete product coverage | Create checklist of all products per brand, verify 100% |
| Slow ingestion | Parallelize to 10 concurrent requests, batch in 50-URL chunks |
| Hallucination in responses | Only use official docs, verify against source for QA |
| Media attachment failures | Gracefully degrade - return text response if media unavailable |
| Domain spoofing | Whitelist only official domains (allen-heath.com, rcf.it, etc.) |

---

## 10. SUCCESS CRITERIA

**Completed when:**
1. ✅ All 4 deprecated brands removed (DONE)
2. Allen & Heath: 500+ documents, 95%+ coverage
3. RCF optimized: Deduplicated, all media verified
4. Montarbo: 300+ documents, 90%+ coverage
5. 5 supporting brands with 100+ docs each
6. Every RAG response includes relevant brand logo + media
7. All queries answered from official sources only
8. Response time < 2 seconds
9. No duplicate content in vector DB
10. All media URLs verified live

---

**Next Step:** Run `ingest_ah_complete.py` to complete Allen & Heath ingestion
