import json
from pathlib import Path

INGESTION_STATUS_FILE = Path("/tmp/ingestion_status.json")

status = {
    "is_running": False,
    "current_brand": None,
    "current_step": None,
    "current_document": None,
    "total_documents": 0,
    "documents_by_brand": {},
    "urls_discovered": 0,
    "urls_processed": 0,
    "progress_percent": 0.0,
    "last_updated": "",
    "errors": [],
    "start_time": "",
    "estimated_completion": "",
    "brand_progress": {}
}

with open(INGESTION_STATUS_FILE, 'w') as f:
    json.dump(status, f, indent=2)

print("Tracker reset.")
