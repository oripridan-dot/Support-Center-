# Phase 2: Multi-Brand Expansion Plan

**Status:** Ready to Execute  
**Date:** December 23, 2025  
**Focus:** Rode, Boss, Roland, Mackie, PreSonus

---

## ✅ Phase 1 Complete

| Brand | Documents | Status |
|-------|-----------|--------|
| Allen & Heath | 250 | ✅ 100% |
| RCF | 1,236 | ✅ 100% |
| **TOTAL PHASE 1** | **1,486** | **✅ COMPLETE** |

---

## 🎯 Phase 2 Targets

### Brand Expansion Queue

1. **Rode** (ID: 3)
   - Website: https://www.rode.com
   - Est. Docs: 200+ (manuals, guides, FAQs)
   - Support: https://rode.com/en/support
   - Method: Browser-based (Zendesk or direct)
   - ETA: 15-20 minutes

2. **Boss** (ID: 2)  
   - Website: https://www.boss.info
   - Est. Docs: 150+ (product manuals, patches)
   - Support: Check for Zendesk or knowledge base
   - Method: Browser-based
   - ETA: 10-15 minutes

3. **Roland** (ID: 1)
   - Website: https://www.roland.com
   - Est. Docs: 250+ (large product line)
   - Support: https://support.roland.com or Zendesk
   - Method: Browser-based
   - ETA: 20-25 minutes

4. **Mackie** (ID: 21)
   - Website: https://mackie.com
   - Est. Docs: 180+ (Pro audio equipment)
   - Support: https://mackie.com/support or Zendesk
   - Method: Browser-based
   - ETA: 15-20 minutes

5. **PreSonus** (ID: 6 or 69)
   - Website: https://www.presonus.com
   - Est. Docs: 200+ (DAW + hardware)
   - Support: https://presonus.com/support
   - Method: Browser-based
   - ETA: 15-20 minutes

**Phase 2 Target:** 800-1,000 additional documents  
**Phase 2 Total:** 2,300-2,500 documents

---

## 🔄 Execution Plan

### For Each Brand:

```bash
# 1. Create brand-specific ingestion script
cp scripts/ingest_brands_support_centers.py scripts/ingest_<brand>_support.py

# 2. Update config in script:
#    - Brand ID
#    - Support URL
#    - Category limit
#    - Article limits

# 3. Run ingestion
cd /workspaces/Support-Center-/backend
PYTHONPATH=. python scripts/ingest_<brand>_support.py

# 4. Monitor progress
tail -f ingest_<brand>_support.log

# 5. Verify coverage
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

session = Session(engine)
brand = session.exec(select(Brand).where(Brand.name == "Brand Name")).first()
if brand:
    count = len(session.exec(select(Document).where(Document.brand_id == brand.id)).all())
    print(f"✓ {brand.name}: {count} documents")
session.close()
EOF
```

---

## 🛠️ Template Ingestion Script

Use as base for each brand:

```python
#!/usr/bin/env python3
"""
[Brand] Support Center Ingestion
Target: 100% coverage of official documentation
"""

import asyncio
import logging
from typing import Set, Optional
from datetime import datetime
import hashlib
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingest_<brand>_support.log")
    ]
)
logger = logging.getLogger("<Brand>-Support")

class SupportCenterIngester:
    def __init__(self):
        self.brand_name = "<Brand Name>"
        self.brand_id = XX  # Update with correct ID
        self.base_url = "https://support.<brand>.com/hc/en-us"  # Update
        self.main_page = "https://support.<brand>.com/hc/en-us"  # Update
        self.browser: Optional[Browser] = None
        self.session = None
        self.ingested_urls: Set[str] = set()
        
    async def start(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.session = Session(engine)
        logger.info(f"✓ Initialized {self.brand_name} ingester")
        
    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.session:
            self.session.close()
            
    async def fetch_page(self, url: str) -> str:
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            content = await page.content()
            return content
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return ""
        finally:
            await page.close()
            
    async def discover_articles(self) -> Set[str]:
        logger.info(f"📖 Discovering {self.brand_name} articles...")
        articles = set()
        
        # Fetch and parse main page
        html = await self.fetch_page(self.main_page)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract article links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/articles/' in href:
                full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                articles.add(full_url)
                
        logger.info(f"  ✓ Found {len(articles)} articles")
        return articles
        
    async def ingest_articles(self, article_urls: Set[str]):
        brand = self.session.exec(select(Brand).where(Brand.name == self.brand_name)).first()
        if not brand:
            logger.error(f"Brand {self.brand_name} not found")
            return
            
        existing = self.session.exec(select(Document).where(Document.brand_id == brand.id)).all()
        self.ingested_urls = {doc.url for doc in existing}
        
        new_urls = [url for url in article_urls if url not in self.ingested_urls]
        logger.info(f"📝 Ingesting {len(new_urls)} new articles...")
        
        for i, url in enumerate(new_urls):
            try:
                html = await self.fetch_page(url)
                if not html:
                    continue
                    
                soup = BeautifulSoup(html, 'html.parser')
                title = soup.find('h1')
                title_text = title.text.strip() if title else "Untitled"
                
                content_div = soup.find('div', {'class': ['article-body', 'article-content']})
                if not content_div:
                    content_div = soup.find('main')
                
                content_text = self._extract_text(str(content_div)) if content_div else ""
                if len(content_text) < 50:
                    continue
                
                doc = Document(
                    brand_id=brand.id,
                    title=title_text,
                    url=url,
                    content=content_text,
                    content_hash=hashlib.md5(content_text.encode()).hexdigest(),
                )
                self.session.add(doc)
                self.session.commit()
                
                if (i + 1) % 10 == 0:
                    logger.info(f"  → {i + 1}/{len(new_urls)} articles ingested")
                    
            except Exception as e:
                logger.error(f"Error with {url}: {e}")
                self.session.rollback()
                
    def _extract_text(self, html: str, max_lines: int = 5000) -> str:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = soup.get_text('\n', strip=True)
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            return '\n'.join(lines[:max_lines])
        except:
            return ""
            
    async def ingest(self):
        logger.info(f"\n{'='*70}\n{self.brand_name.upper()} INGESTION\n{'='*70}")
        try:
            await self.start()
            articles = await self.discover_articles()
            await self.ingest_articles(articles)
            logger.info(f"✅ {self.brand_name} complete!")
        finally:
            await self.stop()

async def main():
    ingester = SupportCenterIngester()
    await ingester.ingest()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📊 Success Metrics - Phase 2

After all Phase 2 ingestings:

| Metric | Target | Status |
|--------|--------|--------|
| Total Documents | 2,300+ | In Progress |
| Active Brands | 7 | In Progress |
| Coverage Ratio | 90%+ | In Progress |
| Avg Response Time | < 2s | To Test |
| Duplicate Rate | < 1% | To Verify |

---

## 🔍 Discovery Process for Each Brand

### Finding Support Centers

1. **Google Search:** `"{brand} support" OR "{brand} help" OR "{brand} documentation"`
2. **robots.txt:** `{domain}/robots.txt` - often lists `/support/`, `/help/`, `/docs/`
3. **Zendesk Check:** Try `{brand}.zendesk.com/hc/en-us`
4. **Direct URL:** `{domain}/support`, `{domain}/help`, `{domain}/docs`, `{domain}/knowledge`

### Quick Support Center Finder

```bash
# Check if Zendesk exists
curl -s -I https://<brand>.zendesk.com/hc/en-us | head -1

# Check main domain support paths
for path in /support /help /docs /knowledge /faq /knowledge-base; do
  curl -s -I https://<brand>.com$path | head -1
done
```

---

## 🚀 Parallel Execution Strategy

### Option 1: Sequential (Safest)
Run each brand one at a time, verify, then move to next.
- **Time:** 2-3 hours total
- **Risk:** Low
- **Resources:** Minimal

### Option 2: Parallel (Faster)
Run 2-3 brands simultaneously in separate terminals/screens.
- **Time:** 1-1.5 hours total
- **Risk:** Medium (higher CPU/memory)
- **Resources:** More intensive

### Recommended: Sequential
Execute in order: Rode → Boss → Roland → Mackie → PreSonus

---

## 📋 Checklist - Phase 2

- [ ] Rode ingestion complete
  - [ ] Verify documents count > 150
  - [ ] Check log for errors
  - [ ] Audit for duplicates

- [ ] Boss ingestion complete
  - [ ] Verify documents count > 100
  - [ ] Check log for errors
  - [ ] Audit for duplicates

- [ ] Roland ingestion complete
  - [ ] Verify documents count > 200
  - [ ] Check log for errors
  - [ ] Audit for duplicates

- [ ] Mackie ingestion complete
  - [ ] Verify documents count > 150
  - [ ] Check log for errors
  - [ ] Audit for duplicates

- [ ] PreSonus ingestion complete
  - [ ] Verify documents count > 150
  - [ ] Check log for errors
  - [ ] Audit for duplicates

- [ ] Final verification
  - [ ] Total documents ≥ 2,300
  - [ ] No orphaned documents
  - [ ] All brand IDs correct
  - [ ] ChromaDB indexed properly
  - [ ] RAG queries working

---

## 🎯 Quick Start Phase 2

```bash
# Start servers (if not already running)
cd /workspaces/Support-Center-/backend
bash start_servers.sh &

# Verify Phase 1 completed
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from app.core.database import Session, engine
from app.models.sql_models import Brand, Document
from sqlmodel import select

session = Session(engine)
brands = [("Allen & Heath", 28), ("RCF", 88)]
for name, id in brands:
    count = len(session.exec(select(Document).where(Document.brand_id == id)).all())
    print(f"{name:20s}: {count:5d} documents")
session.close()
EOF

# Start Phase 2: Rode
cd /workspaces/Support-Center-/backend
# Create ingest_rode_support.py from template above
# Update: brand_name="Rode", brand_id=3, URLs for Rode support center
PYTHONPATH=. python scripts/ingest_rode_support.py 2>&1 | tee ingest_rode_support.log &

# Monitor
tail -f ingest_rode_support.log
```

---

## 🔗 Reference Documentation

- [MULTI_BRAND_INGESTION_REPORT.md](MULTI_BRAND_INGESTION_REPORT.md) - Phase 1 complete report
- [BRAND_SCRAPER_QUICK_REF.md](BRAND_SCRAPER_QUICK_REF.md) - Architecture reference
- [INGESTION_PLAN.md](INGESTION_PLAN.md) - Overall strategy

---

**Ready to Execute:** Yes  
**Estimated Duration:** 2-3 hours  
**Resource Requirements:** Low-Medium  
**Risk Level:** Low

Start Phase 2 when ready. All templates and guides are prepared.
