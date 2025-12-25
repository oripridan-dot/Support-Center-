
from pydantic import BaseModel
from typing import Optional
import json

class IngestionStatus(BaseModel):
    is_running: bool
    current_brand: Optional[str] = None
    current_step: Optional[str] = None
    total_documents: int = 0
    documents_by_brand: dict = {}
    urls_discovered: int = 0
    urls_processed: int = 0
    progress_percent: float = 0.0
    last_updated: str = ""
    errors: list = []
    start_time: Optional[str] = None
    estimated_completion: Optional[str] = None
    brand_progress: dict = {}

data = {
  "is_running": True,
  "current_brand": "Maybach",
  "current_step": "Discovered 25 URLs for Maybach, processing...",
  "total_documents": 78,
  "documents_by_brand": {
    "Maestro Guitar Pedals And Effects": 6,
    "Magma": 22,
    "Marimba One": 3,
    "Maton Guitars": 23,
    "Maybach": 24
  },
  "urls_discovered": 25,
  "urls_processed": 25,
  "progress_percent": 100,
  "last_updated": "2025-12-24T22:52:39.388595",
  "errors": [],
  "start_time": "2025-12-24T22:36:02.232597",
  "estimated_completion": "",
  "brand_progress": {
    "Avid": {
      "brand_id": 32,
      "status": "discovering",
      "urls_discovered": 0,
      "documents_ingested": 0,
      "start_time": "2025-12-24T22:37:07.891573"
    },
    "Keith Mcmillen Instruments Kmi": {
      "brand_id": 33,
      "status": "discovering",
      "urls_discovered": 0,
      "documents_ingested": 0,
      "start_time": "2025-12-24T22:37:42.273957"
    },
    "Maestro Guitar Pedals And Effects": {
      "brand_id": 40,
      "status": "processing",
      "urls_discovered": 10,
      "documents_ingested": 6,
      "start_time": "2025-12-24T22:39:16.050622"
    },
    "Magma": {
      "brand_id": 80,
      "status": "processing",
      "urls_discovered": 25,
      "documents_ingested": 22,
      "start_time": "2025-12-24T22:40:56.071915"
    },
    "Marimba One": {
      "brand_id": 86,
      "status": "processing",
      "urls_discovered": 5,
      "documents_ingested": 3,
      "start_time": "2025-12-24T22:43:55.634890"
    },
    "Maton Guitars": {
      "brand_id": 24,
      "status": "processing",
      "urls_discovered": 25,
      "documents_ingested": 23,
      "start_time": "2025-12-24T22:44:40.992622"
    },
    "Maybach": {
      "brand_id": 36,
      "status": "processing",
      "urls_discovered": 25,
      "documents_ingested": 24,
      "start_time": "2025-12-24T22:48:30.209369"
    }
  }
}

try:
    status = IngestionStatus(**data)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
