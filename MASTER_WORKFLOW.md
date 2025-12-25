# Master Workflow: Halilit Brands Documentation Coverage

This document defines the **ONLY** authorized workflow for this project. All other workflows are deprecated.

## Goal
Achieve 100% official documentation coverage for all brands in the Halilit Brands List, ensuring the UI reflects this status in real-time.

## The Workflow

### 1. Brand Selection
- **Source of Truth:** `HALILIT_BRANDS_LIST.md`
- **Process:** Select brands **one by one** from the list.
- **Constraint:** Do NOT move to the next brand until the current brand is 100% complete.

### 2. Planning (Per Brand)
- Create a specific scraping plan for the brand.
- **Objective:** 100% official documentation coverage (Manuals, Specs, FAQs, Drivers/Firmware).
- **Future-proofing:** The plan must include a strategy for fast, accurate future updates (e.g., monitoring specific URL patterns, RSS feeds, or sitemaps).

### 3. Execution & Resolution
- Execute the scraping plan.
- Resolve ALL issues immediately. Do not defer fixes.
- **Validation:** Verify that the data is correctly ingested into the Vector DB (ChromaDB) and is retrievable.

### 4. Real-Time UI Synchronization
- The UI must reflect the backend's status in real-time.
- **All Brands Page:** Must show a coverage bar for each brand based on *actual* ingested data vs. expected data.
- **Ingestion Panel:** Must show accurate, live progress of the current scraping/ingestion task.

### 5. Completion Criteria
- A brand is "Complete" ONLY when:
    - All targeted documentation is scraped.
    - All data is ingested and indexed.
    - The UI shows 100% coverage.
    - Search queries for the brand return accurate results.

### 6. Iteration
- Once a brand is Complete, mark it as such in `HALILIT_BRANDS_LIST.md`.
- Proceed to the next brand in the list.

## UI Requirements

### All Brands Page
- **List View:** Display all brands from the master list.
- **Coverage Bar:** Visual indicator (0-100%) for each brand.
- **Data Source:** Real-time query to the backend to count indexed documents vs. estimated total.

### Ingestion Panel
- **Status:** Live updates (Running, Completed, Failed).
- **Logs:** Real-time stream of ingestion logs.
- **Accuracy:** No "fake" progress bars. Display actual processed items count.

## Optimization Guidelines
- **Speed:** Use parallel processing where safe (respecting rate limits).
- **Structure:** Maintain a consistent folder structure for scraped data (`backend/data/<brand_name>/`).
- **Caching:** Cache successful requests to avoid redundant network calls during development.
