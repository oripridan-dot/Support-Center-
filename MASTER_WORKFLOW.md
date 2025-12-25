# Halilit Support Center - Local AI Workflow

## 🚨 CRITICAL: MASTER WORKFLOW ADHERENCE 🚨
**ALL work must strictly follow this file.**

## Context & Focus
- **Project:** Local AI Product Knowledge System for Halilit Staff.
- **Goal:** Instant, private, and accurate answers using local LLMs.
- **Stack:** FastAPI (Backend), Electron/React (Frontend), Qdrant (Vector Store), Ollama (LLM Runtime).

## Workflow Execution Rules

### 1. Local AI Stack
- **Runtime:** Ollama must be running (`ollama serve`).
- **Model:** `llama3.2:3b` (or `phi3:mini` for lower RAM).
- **Embeddings:** `nomic-embed-text`.
- **Vector DB:** Qdrant running in Docker (`docker run -p 6333:6333 qdrant/qdrant`).

### 2. Data Ingestion
- **Source:** Official PDF manuals and product pages.
- **Process:**
    1.  **Scrape/Download:** Use Playwright for authenticated portals.
    2.  **Extract:** PyMuPDF for PDFs.
    3.  **Chunk:** Semantic chunking (preserve context).
    4.  **Enrich:** Add metadata (Brand, Model, Category).
    5.  **Embed & Store:** Generate embeddings and upsert to Qdrant.

### 3. Backend Development (FastAPI)
- **Location:** `backend/app/`
- **Standards:**
    - Async/Await for all I/O.
    - Pydantic models for all requests/responses.
    - Type hints everywhere.
- **Endpoints:**
    - `/api/v1/search`: RAG search with filters.
    - `/api/v1/ingest`: Trigger ingestion (admin only).

### 4. Frontend Development (Electron/React)
- **Location:** `frontend/`
- **Standards:**
    - Tailwind CSS for styling.
    - React Query for data fetching.
    - Electron IPC for native features (if needed).

## File Structure
- `backend/app/services/`: Business logic (LLM, VectorDB, Ingestion).
- `backend/app/api/`: API Routes.
- `frontend/electron/`: Electron main process.
- `frontend/src/`: React UI.
