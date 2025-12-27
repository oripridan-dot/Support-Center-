"""
Task scheduler with Celery Beat for automated workflows.

Features:
- Scheduled scraping (daily/weekly)
- Automated reindexing
- Maintenance tasks
- Workflow orchestration with dependencies
"""

from celery.schedules import crontab
from celery import chain, group, chord
import structlog

from app.workers.queue_manager import celery_app

logger = structlog.get_logger(__name__)

# Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    # Full catalog scrape - weekly (Sunday at 2 AM)
    'full-scrape-weekly': {
        'task': 'app.workers.scheduler.orchestrate_full_refresh',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
        'options': {'priority': 5}
    },
    
    # Delta scrape - daily (3 AM)
    'delta-scrape-daily': {
        'task': 'app.workers.scheduler.orchestrate_delta_scrape',
        'schedule': crontab(hour=3, minute=0),
        'options': {'priority': 7}
    },
    
    # Embedding maintenance - every 6 hours
    'reindex-embeddings': {
        'task': 'app.workers.embedding_worker.reindex_outdated',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {'priority': 6},
        'kwargs': {'days_old': 30}
    },
    
    # Cache cleanup - hourly
    'cleanup-cache': {
        'task': 'app.workers.maintenance_worker.cleanup_cache',
        'schedule': crontab(minute=15),
        'options': {'priority': 3},
        'kwargs': {'max_age_hours': 24}
    },
    
    # Health check - every 5 minutes
    'health-check': {
        'task': 'app.workers.maintenance_worker.health_check',
        'schedule': crontab(minute='*/5'),
        'options': {'priority': 8}
    },
    
    # Task result cleanup - daily (4 AM)
    'cleanup-old-tasks': {
        'task': 'app.workers.maintenance_worker.cleanup_old_tasks',
        'schedule': crontab(hour=4, minute=0),
        'options': {'priority': 2},
        'kwargs': {'days_old': 7}
    },
    
    # Collection optimization - weekly (Monday at 1 AM)
    'optimize-collections': {
        'task': 'app.workers.maintenance_worker.optimize_collections',
        'schedule': crontab(day_of_week=1, hour=1, minute=0),
        'options': {'priority': 4}
    },
}


@celery_app.task(name='app.workers.scheduler.orchestrate_full_refresh')
def orchestrate_full_refresh() -> dict:
    """
    Orchestrate complete data refresh workflow with dependencies.
    
    Workflow:
    1. Discover all URLs for each brand
    2. Scrape discovered URLs in parallel batches
    3. Generate embeddings for scraped content
    4. Verify and report results
    """
    from app.workers.scraper_worker import discover_links, batch_scrape
    from app.workers.embedding_worker import batch_embedding
    
    logger.info("full_refresh_orchestration_started")
    
    # List of brands to process
    brands = [
        'roland', 'yamaha', 'korg', 'moog', 'native_instruments',
        'akai', 'arturia', 'novation', 'elektron', 'teenage_engineering'
    ]
    
    results = []
    
    for brand in brands:
        logger.info("processing_brand", brand=brand)
        
        # Workflow for each brand:
        # 1. Discover links
        # 2. Scrape all discovered pages
        # 3. Generate embeddings
        
        workflow = chain(
            discover_links.si(
                start_url=f"https://www.{brand}.com",
                brand=brand,
                max_depth=3
            ),
            batch_scrape.s(brand=brand, batch_size=20),
            batch_embedding.s(brand=brand)
        )
        
        result = workflow.apply_async()
        results.append({
            'brand': brand,
            'task_id': result.id
        })
    
    return {
        'status': 'orchestrated',
        'brands_queued': len(brands),
        'workflows': results,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.scheduler.orchestrate_delta_scrape')
def orchestrate_delta_scrape() -> dict:
    """
    Orchestrate incremental scraping of recently updated pages.
    
    Only scrapes pages that have been modified since last check.
    """
    from app.workers.scraper_worker import batch_scrape
    from app.workers.embedding_worker import batch_embedding
    
    logger.info("delta_scrape_orchestration_started")
    
    # This would query a database of known URLs and their last-modified dates
    # For now, simplified implementation
    
    brands_to_update = ['roland', 'yamaha', 'korg']
    
    results = []
    
    for brand in brands_to_update:
        # In production, this would fetch URLs that need updating
        # For now, placeholder
        workflow = chain(
            batch_scrape.si(
                urls=[],  # Would be populated from DB
                brand=brand,
                batch_size=10
            ),
            batch_embedding.s(brand=brand)
        )
        
        result = workflow.apply_async()
        results.append({
            'brand': brand,
            'task_id': result.id
        })
    
    return {
        'status': 'orchestrated',
        'brands_queued': len(brands_to_update),
        'workflows': results,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.scheduler.orchestrate_brand_ingestion')
def orchestrate_brand_ingestion(brand: str, start_url: str) -> dict:
    """
    Orchestrate complete ingestion for a single brand.
    
    Args:
        brand: Brand name
        start_url: Starting URL for discovery
        
    Returns:
        Workflow status
    """
    from app.workers.scraper_worker import discover_links, batch_scrape
    from app.workers.embedding_worker import batch_embedding
    
    logger.info("brand_ingestion_started", brand=brand, start_url=start_url)
    
    # Build workflow with error handling
    workflow = chain(
        # Step 1: Discover all product links
        discover_links.si(
            start_url=start_url,
            brand=brand,
            max_depth=3
        ),
        
        # Step 2: Scrape discovered pages in parallel
        batch_scrape.s(brand=brand, batch_size=20),
        
        # Step 3: Generate embeddings
        batch_embedding.s(brand=brand, batch_size=10)
    )
    
    result = workflow.apply_async()
    
    return {
        'status': 'orchestrated',
        'brand': brand,
        'workflow_id': result.id,
        'start_url': start_url,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.scheduler.parallel_brand_ingestion')
def parallel_brand_ingestion(brands: list[dict]) -> dict:
    """
    Ingest multiple brands in parallel.
    
    Args:
        brands: List of dicts with 'name' and 'start_url'
        
    Returns:
        Parallel ingestion summary
    """
    logger.info("parallel_ingestion_started", brand_count=len(brands))
    
    # Create parallel workflow
    parallel_jobs = group(
        orchestrate_brand_ingestion.s(brand['name'], brand['start_url'])
        for brand in brands
    )
    
    result = parallel_jobs.apply_async()
    
    return {
        'status': 'orchestrated',
        'brands_queued': len(brands),
        'group_id': result.id,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.scheduler.orchestrate_cache_warmup')
def orchestrate_cache_warmup() -> dict:
    """
    Warm up cache with common queries for all brands.
    """
    from app.workers.rag_worker import warmup_cache
    
    logger.info("cache_warmup_orchestration_started")
    
    # Common questions per brand
    common_queries = [
        "How do I reset my device?",
        "What are the specifications?",
        "How do I update firmware?",
        "Troubleshooting guide",
        "User manual PDF",
        "Installation instructions",
        "Warranty information",
        "Technical support contact"
    ]
    
    brands = ['roland', 'yamaha', 'korg', 'moog']
    
    # Create parallel warmup tasks
    warmup_jobs = group(
        warmup_cache.s(common_queries, brand)
        for brand in brands
    )
    
    result = warmup_jobs.apply_async()
    
    return {
        'status': 'orchestrated',
        'brands': len(brands),
        'queries_per_brand': len(common_queries),
        'group_id': result.id,
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }


@celery_app.task(name='app.workers.scheduler.get_workflow_status')
def get_workflow_status(workflow_id: str) -> dict:
    """
    Get status of a workflow by ID.
    
    Args:
        workflow_id: Celery task/group ID
        
    Returns:
        Workflow status details
    """
    from celery.result import AsyncResult, GroupResult
    
    try:
        # Try as regular task
        result = AsyncResult(workflow_id, app=celery_app)
        
        if result.state == 'PENDING':
            # Might be a group result
            group_result = GroupResult.restore(workflow_id, app=celery_app)
            if group_result:
                return {
                    'type': 'group',
                    'status': 'in_progress',
                    'completed': group_result.completed_count(),
                    'total': len(group_result),
                    'results': [r.state for r in group_result.results]
                }
        
        return {
            'type': 'task',
            'status': result.state,
            'result': result.result if result.ready() else None,
            'traceback': result.traceback if result.failed() else None
        }
        
    except Exception as e:
        logger.error("workflow_status_error", workflow_id=workflow_id, error=str(e))
        return {
            'status': 'error',
            'error': str(e)
        }
