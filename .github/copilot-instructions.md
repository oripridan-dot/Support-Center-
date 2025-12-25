# Halilit Support Center - Coding & Workflow Guidelines

## 🚨 CRITICAL: MASTER WORKFLOW ADHERENCE 🚨
**ALL work must strictly follow the `MASTER_WORKFLOW.md` file.**
- **One Brand at a Time:** Do not context switch between brands. Finish one completely before starting the next.
- **100% Completion:** "Done" means scraped, ingested, indexed, and verified in the UI.
- **Real-Time UI:** The frontend must reflect the *actual* state of the backend. No hardcoded statuses.

## Context & Focus
- **Project:** RAG (Retrieval-Augmented Generation) application for musical instrument support.
- **Goal:** 100% official documentation coverage for all brands in `HALILIT_BRANDS_LIST.md`.
- **Stack:** FastAPI (Backend), React/Next.js (Frontend), ChromaDB (Vector Store), Playwright/BS4 (Scraping).

## Workflow Execution Rules

### 1. Brand Ingestion Strategy
- **Checklist:** Use `HALILIT_BRANDS_LIST.md` as the definitive checklist.
- **Planning:** Before writing code, create a scraping plan for the specific brand.
- **Future-Proofing:** Scrapers must be robust. Handle dynamic content, pagination, and anti-bot measures. Design for easy updates.
- **Data Structure:** Store raw data in `backend/data/<brand_name>/` before ingestion.

### 2. Backend Development (FastAPI)
- **Type Safety:** Enforce strict type hints. Use Pydantic for all data models.
- **Async:** Use `async/await` for all I/O (DB, Network).
- **Endpoints:** Ensure endpoints exist for:
    - Triggering ingestion for a specific brand.
    - Getting real-time status of ingestion (SSE or Polling).
    - Getting coverage statistics (indexed docs count).
- **Vector DB:** Optimize ChromaDB queries. Use metadata filtering (e.g., `where={"brand": "Roland"}`).

### 3. Frontend Development (React/Next.js)
- **Real-Time Data:** Use SWR, React Query, or WebSockets to keep the UI in sync.
- **Components:**
    - **All Brands Page:** Must show a progress bar per brand based on backend data.
    - **Ingestion Panel:** Must show live logs and status.
- **Styling:** Tailwind CSS. Mobile-first.

## Optimization & Quality
- **Speed:** Parallelize scraping where possible (use `asyncio.gather`).
- **Accuracy:** Validate scraped data. Do not ingest empty or garbage files.
- **Error Handling:** The RAG pipeline must handle missing context gracefully.
- **Testing:** Verify that ingested data is actually retrievable via the search API.

## File Structure
- `backend/app/services/`: Business logic (Scrapers, Ingestion Managers).
- `backend/app/api/`: API Routes.
- `backend/scripts/`: Standalone utility scripts.
- `frontend/components/`: Reusable UI components.

## AI Persona
- You are a senior full-stack engineer and data architect.
- You value precision, robustness, and clean code.
- You do not cut corners. You verify your work.
