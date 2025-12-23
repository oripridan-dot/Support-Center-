# Halilit Support Center - Coding Guidelines

## Context & Focus
- This is a RAG (Retrieval-Augmented Generation) application for musical instrument support.
- Always prioritize accuracy in instrument specifications and support advice.
- The backend is FastAPI; the frontend is React.

## Python / FastAPI Guidelines
- Use type hints for all function signatures.
- Prefer `async/await` for I/O bound operations (database calls, API requests).
- Follow the modular structure: keep business logic in `app/services/` and API routes in `app/api/`.
- Use Pydantic models for request validation and response serialization.

## AI & Vector DB (ChromaDB)
- When writing queries for [chroma_db/](chroma_db/), ensure efficient metadata filtering.
- Use OpenAI's `text-embedding-3-small` or better for embeddings.
- Ensure the RAG pipeline handles "I don't know" gracefully when context is missing.

## Scraping & Data
- Use Playwright for dynamic content and BeautifulSoup4 for static HTML parsing.
- Reference existing data files in `backend/data/` when suggesting data processing scripts.
- Scripts are located in `backend/scripts/`.

## Frontend Guidelines
- Use Tailwind CSS for styling.
- Ensure the UI is accessible and mobile-friendly for musicians on the go.
