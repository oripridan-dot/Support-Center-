"""
Worker Architecture for Multi-Stage Ingestion Pipeline

This package implements a 3-worker system:
1. Explorer: Analyzes brand websites and generates scraping strategies
2. Scraper: Executes scraping instructions from Explorer
3. Ingester: Vectorizes and indexes scraped documentation

All workers operate independently but follow the Explorer's instructions.
"""

from .explorer import ExplorerWorker
from .scraper import ScraperWorker
from .ingester import IngesterWorker

__all__ = ['ExplorerWorker', 'ScraperWorker', 'IngesterWorker']
