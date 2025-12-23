# Backend Scripts

This directory contains various utility scripts for scraping, data ingestion, and testing.

## How to Run

Since these scripts are now located in a subdirectory, you need to ensure the `backend` directory is in your Python path so they can import the `app` module.

**Run from the `backend` directory:**

```bash
cd backend
PYTHONPATH=. python scripts/script_name.py
```

**Example:**

```bash
# To run the database check script
PYTHONPATH=. python scripts/check_db.py
```

## Script Categories

- **Discovery (`discover_*.py`)**: Scripts to find URLs and product links.
- **Ingestion (`ingest_*.py`)**: Scripts to scrape content and populate the vector database.
- **Testing (`test_*.py`)**: Unit and integration tests.
- **Utilities**: `check_db.py`, `list_db_urls.py`, etc.
