# Montarbo Scraping Pipeline (Test Case)

This document outlines the standardized process for scraping and ingesting a new brand, using Montarbo as the test case.

## Strategy: Full Coverage DB
We pre-scrape all product data and ingest it into the Vector Database (ChromaDB) to ensure fast and accurate retrieval during chat.

## Steps

### 1. Discovery
Run the discovery script to find all product URLs.
```bash
cd backend
python scripts/discover_montarbo.py
```
Output: `montarbo_links.txt`

### 2. Ingestion
Run the ingestion script to scrape each URL, extract structured data (specs, images, manuals), and ingest into ChromaDB.
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:.
python scripts/ingest_montarbo.py
```
*Note: This script is idempotent. It checks if a product exists in SQL, but has been configured to re-ingest if needed.*

### 3. Verification
Run the test script to verify RAG retrieval.
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:.
python scripts/test_montarbo_rag.py
```

## Files
- `backend/scripts/discover_montarbo.py`: Crawls the product listing page.
- `backend/scripts/ingest_montarbo.py`: Orchestrates the scraping and ingestion.
- `backend/app/services/pa_brands_scraper.py`: Contains the core scraping logic (`scrape_generic_product_page`).
- `backend/scripts/test_montarbo_rag.py`: Verifies the result.
