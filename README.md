# Halilit Support Center

An AI-powered support platform for Halilit musical instruments, featuring automated web scraping, Retrieval-Augmented Generation (RAG), and a modern web interface.

## 🚀 Project Overview
This system crawls Halilit's product data and documentation to provide accurate, context-aware support responses using LLMs and a vector database.

## 🛠 Tech Stack
- **Backend:** Python 3.12+ with FastAPI.
- **AI/LLM:** OpenAI API for embeddings and response generation.
- **Vector Database:** [backend/chroma_db/](backend/chroma_db/) (ChromaDB) for high-performance similarity search.
- **Scraping:** BeautifulSoup4 and Playwright for data extraction.
- **Frontend:** React/Next.js (located in [frontend/](frontend/)).

## 📂 Project Structure
- [backend/](backend/):
    - `app/`: Core application logic (API, RAG, Scrapers).
    - `scripts/`: Utility scripts for discovery, ingestion, and testing.
    - `data/`: Raw data files (HTML, JSON, TXT) and scraped content.
    - `logs/`: Application and ingestion logs.
    - `chroma_db/`: Vector database storage.
- [frontend/](frontend/): React-based user interface.

## ⚙️ Getting Started

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `backend/.env`.
5. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🔍 Data Pipeline & Scripts
Scripts are now located in `backend/scripts/`. To run them, ensure `backend` is in your PYTHONPATH.

Example:
```bash
cd backend
PYTHONPATH=. python scripts/check_db.py
```
