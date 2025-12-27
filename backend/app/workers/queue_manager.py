"""
Celery task queue manager with priority-based routing.

Provides distributed task processing infrastructure with:
- Priority queues for different job types
- Auto-retry logic with exponential backoff
- Task routing to specialized workers
- Connection pooling and resource management
"""

import os
from typing import Dict, Any
from celery import Celery
from kombu import Queue, Exchange
import structlog

logger = structlog.get_logger(__name__)

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# Initialize Celery application
celery_app = Celery(
    'halilit_workers',
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=[
        'app.workers.scraper_worker',
        'app.workers.embedding_worker',
        'app.workers.rag_worker',
        'app.workers.maintenance_worker',
    ]
)

# Define task exchanges
scraping_exchange = Exchange('scraping', type='direct', durable=True)
embeddings_exchange = Exchange('embeddings', type='direct', durable=True)
rag_exchange = Exchange('rag', type='direct', durable=True)
notifications_exchange = Exchange('notifications', type='direct', durable=True)
maintenance_exchange = Exchange('maintenance', type='direct', durable=True)

# Configure task queues with priorities
# Priority scale: 0 (lowest) to 10 (highest)
celery_app.conf.task_queues = (
    # Scraping queue - Medium priority (5)
    Queue(
        'scraping',
        exchange=scraping_exchange,
        routing_key='scraping',
        queue_arguments={'x-max-priority': 10},
        priority=5
    ),
    
    # Embeddings queue - High priority (8)
    Queue(
        'embeddings',
        exchange=embeddings_exchange,
        routing_key='embeddings',
        queue_arguments={'x-max-priority': 10},
        priority=8
    ),
    
    # RAG queries - Highest priority (10)
    Queue(
        'rag_queries',
        exchange=rag_exchange,
        routing_key='rag',
        queue_arguments={'x-max-priority': 10},
        priority=10
    ),
    
    # Notifications - Low priority (3)
    Queue(
        'notifications',
        exchange=notifications_exchange,
        routing_key='notifications',
        queue_arguments={'x-max-priority': 10},
        priority=3
    ),
    
    # Maintenance - Low priority (2)
    Queue(
        'maintenance',
        exchange=maintenance_exchange,
        routing_key='maintenance',
        queue_arguments={'x-max-priority': 10},
        priority=2
    ),
)

# Task routing configuration
celery_app.conf.task_routes = {
    'app.workers.scraper_worker.*': {
        'queue': 'scraping',
        'routing_key': 'scraping',
        'priority': 5
    },
    'app.workers.embedding_worker.*': {
        'queue': 'embeddings',
        'routing_key': 'embeddings',
        'priority': 8
    },
    'app.workers.rag_worker.*': {
        'queue': 'rag_queries',
        'routing_key': 'rag',
        'priority': 10
    },
    'app.workers.maintenance_worker.*': {
        'queue': 'maintenance',
        'routing_key': 'maintenance',
        'priority': 2
    },
}

# Worker configuration for optimal performance
celery_app.conf.update(
    # Task acknowledgment settings
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Worker prefetch settings
    worker_prefetch_multiplier=1,  # One task at a time for better distribution
    
    # Task time limits
    task_time_limit=600,  # Hard limit: 10 minutes
    task_soft_time_limit=540,  # Soft limit: 9 minutes (allows cleanup)
    
    # Worker lifecycle
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_max_memory_per_child=500000,  # 500MB memory limit
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    
    # Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task tracking
    task_track_started=True,  # Track task start time
    task_send_sent_event=True,  # Send task sent events
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Visibility timeout
    broker_transport_options={
        'visibility_timeout': 43200,  # 12 hours
        'priority_steps': list(range(11)),  # 0-10 priority levels
    },
)

# Task default retry policy
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3


def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics for all task queues.
    
    Returns:
        Dictionary containing queue lengths and worker stats
    """
    try:
        inspector = celery_app.control.inspect()
        
        stats = {
            'active_tasks': inspector.active() or {},
            'scheduled_tasks': inspector.scheduled() or {},
            'registered_tasks': inspector.registered() or {},
            'stats': inspector.stats() or {},
        }
        
        return stats
    except Exception as e:
        logger.error("failed_to_get_queue_stats", error=str(e))
        return {}


def purge_queue(queue_name: str) -> int:
    """
    Purge all tasks from a specific queue.
    
    Args:
        queue_name: Name of the queue to purge
        
    Returns:
        Number of tasks purged
    """
    try:
        with celery_app.connection_or_acquire() as conn:
            return celery_app.amqp.queues[queue_name].purge()
    except Exception as e:
        logger.error("failed_to_purge_queue", queue=queue_name, error=str(e))
        return 0


def get_worker_status() -> Dict[str, Any]:
    """
    Get comprehensive worker status across all queues.
    
    Returns:
        Dictionary with worker health, active tasks, and queue lengths
    """
    try:
        inspector = celery_app.control.inspect()
        
        status = {
            'workers': {
                'active': inspector.active_queues() or {},
                'ping': inspector.ping() or {},
                'stats': inspector.stats() or {},
            },
            'queues': get_queue_stats(),
            'broker_url': BROKER_URL.replace(REDIS_HOST, "***"),  # Mask host for security
        }
        
        return status
    except Exception as e:
        logger.error("failed_to_get_worker_status", error=str(e))
        return {'error': str(e)}


# Initialize app on import
logger.info(
    "celery_configured",
    broker=BROKER_URL,
    queues=['scraping', 'embeddings', 'rag_queries', 'notifications', 'maintenance']
)
