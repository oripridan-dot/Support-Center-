"""
Prometheus monitoring and metrics collection.

Features:
- Task execution metrics
- System health metrics
- Circuit breakers for external APIs
- Structured logging
"""

import os
import time
from typing import Any, Callable
from functools import wraps
import structlog
from prometheus_client import Counter, Histogram, Gauge, Info
from circuitbreaker import circuit

logger = structlog.get_logger(__name__)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# ============================================================================
# Prometheus Metrics
# ============================================================================

# Scraping metrics
scraping_tasks = Counter(
    'scraping_tasks_total',
    'Total number of scraping tasks',
    ['status']  # success, failed, retried
)

scraping_duration = Histogram(
    'scraping_duration_seconds',
    'Time spent scraping pages',
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

scraping_pages_processed = Counter(
    'scraping_pages_processed_total',
    'Total pages scraped',
    ['brand']
)

# Embedding metrics
embedding_tasks = Counter(
    'embedding_tasks_total',
    'Total embedding generation tasks',
    ['status']
)

embedding_duration = Histogram(
    'embedding_duration_seconds',
    'Time spent generating embeddings',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

embedding_chunks_created = Counter(
    'embedding_chunks_created_total',
    'Total embedding chunks created',
    ['brand']
)

# RAG query metrics
rag_queries = Counter(
    'rag_queries_total',
    'Total RAG queries processed',
    ['status', 'from_cache']  # success/failed, true/false
)

rag_latency = Histogram(
    'rag_query_latency_seconds',
    'RAG query processing latency',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

rag_cache_hit_rate = Gauge(
    'rag_cache_hit_rate',
    'Cache hit rate for RAG queries'
)

# Queue metrics
embedding_queue_size = Gauge(
    'embedding_queue_size',
    'Number of tasks in embedding queue'
)

scraping_queue_size = Gauge(
    'scraping_queue_size',
    'Number of tasks in scraping queue'
)

rag_queue_size = Gauge(
    'rag_queue_size',
    'Number of tasks in RAG query queue'
)

# Worker metrics
active_workers = Gauge(
    'active_workers',
    'Number of active Celery workers',
    ['queue']
)

worker_task_runtime = Histogram(
    'worker_task_runtime_seconds',
    'Worker task execution time',
    ['task_name', 'queue']
)

# System metrics
chromadb_collections = Gauge(
    'chromadb_collections_total',
    'Total number of ChromaDB collections'
)

chromadb_documents = Gauge(
    'chromadb_documents_total',
    'Total number of documents in ChromaDB',
    ['brand']
)

redis_memory_usage = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage in bytes'
)

# Application info
app_info = Info(
    'halilit_support_center',
    'Application information'
)

app_info.info({
    'version': '1.0.0',
    'environment': os.getenv('ENVIRONMENT', 'development')
})

# ============================================================================
# Circuit Breakers
# ============================================================================

@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
def call_openai_api(prompt: str, **kwargs) -> dict:
    """
    Protected OpenAI API call with circuit breaker.
    
    Circuit opens after 5 failures, recovers after 60 seconds.
    """
    import openai
    
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model=kwargs.get('model', 'gpt-4'),
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=kwargs.get('max_tokens', 500),
            temperature=kwargs.get('temperature', 0.7)
        )
        
        return {
            'status': 'success',
            'response': response.choices[0].message.content,
            'usage': response.usage.model_dump()
        }
        
    except Exception as e:
        logger.error("openai_api_error", error=str(e))
        raise


@circuit(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
def call_ollama_api(prompt: str, model: str = 'mistral', **kwargs) -> dict:
    """
    Protected Ollama API call with circuit breaker.
    """
    import ollama
    
    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options=kwargs
        )
        
        return {
            'status': 'success',
            'response': response['response']
        }
        
    except Exception as e:
        logger.error("ollama_api_error", error=str(e))
        raise


# ============================================================================
# Monitoring Decorators
# ============================================================================

def monitor_task_execution(task_name: str, queue: str):
    """
    Decorator to monitor task execution time and status.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record success
                duration = time.time() - start_time
                worker_task_runtime.labels(
                    task_name=task_name,
                    queue=queue
                ).observe(duration)
                
                logger.info(
                    "task_completed",
                    task_name=task_name,
                    queue=queue,
                    duration=duration
                )
                
                return result
                
            except Exception as e:
                # Record failure
                duration = time.time() - start_time
                worker_task_runtime.labels(
                    task_name=task_name,
                    queue=queue
                ).observe(duration)
                
                logger.error(
                    "task_failed",
                    task_name=task_name,
                    queue=queue,
                    duration=duration,
                    error=str(e)
                )
                
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Health Check Functions
# ============================================================================

def check_redis_connection() -> bool:
    """Check Redis connectivity."""
    import redis
    
    try:
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=5)
        client.ping()
        
        # Update metrics
        info = client.info('memory')
        redis_memory_usage.set(info.get('used_memory', 0))
        
        return True
        
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return False


def check_chromadb_connection() -> bool:
    """Check ChromaDB connectivity."""
    try:
        from app.core.vector_store import get_chromadb_client
        
        client = get_chromadb_client()
        collections = client.list_collections()
        
        # Update metrics
        chromadb_collections.set(len(collections))
        
        for collection in collections:
            brand = collection.metadata.get('brand', 'unknown')
            chromadb_documents.labels(brand=brand).set(collection.count())
        
        return True
        
    except Exception as e:
        logger.error("chromadb_health_check_failed", error=str(e))
        return False


def check_queue_health() -> dict:
    """Check Celery queue health and update metrics."""
    try:
        from app.workers.queue_manager import celery_app
        
        inspector = celery_app.control.inspect()
        
        # Get active queues
        active_queues = inspector.active_queues() or {}
        
        # Count workers per queue
        for worker, queues in active_queues.items():
            for queue_info in queues:
                queue_name = queue_info['name']
                active_workers.labels(queue=queue_name).inc()
        
        # Get queue lengths (would need additional implementation)
        # For now, placeholder
        
        return {
            'status': 'healthy',
            'active_workers': len(active_queues)
        }
        
    except Exception as e:
        logger.error("queue_health_check_failed", error=str(e))
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_disk_space() -> dict:
    """Check available disk space."""
    import shutil
    
    try:
        usage = shutil.disk_usage('/')
        free_percent = (usage.free / usage.total) * 100
        
        return {
            'status': 'ok' if free_percent > 10 else 'critical',
            'free_gb': usage.free / (1024**3),
            'free_percent': free_percent
        }
        
    except Exception as e:
        logger.error("disk_space_check_failed", error=str(e))
        return {
            'status': 'error',
            'error': str(e)
        }


def check_api_keys() -> dict:
    """Verify required API keys are configured."""
    keys_to_check = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
    }
    
    missing = [key for key, value in keys_to_check.items() if not value]
    
    return {
        'status': 'ok' if not missing else 'warning',
        'missing_keys': missing
    }


# ============================================================================
# Alert Functions
# ============================================================================

def send_alert(checks: dict) -> None:
    """
    Send alert when health checks fail.
    
    In production, this would integrate with PagerDuty, Slack, etc.
    """
    failed_checks = [name for name, result in checks.items() if result.get('status') != 'healthy']
    
    if failed_checks:
        logger.critical(
            "health_check_alert",
            failed_checks=failed_checks,
            details=checks
        )
        
        # Here you would send notifications via:
        # - Slack webhook
        # - PagerDuty
        # - Email
        # - etc.


# ============================================================================
# Metrics Export Endpoint
# ============================================================================

def get_metrics_summary() -> dict:
    """
    Get summary of all metrics for dashboard display.
    """
    return {
        'scraping': {
            'total_pages': scraping_pages_processed._value.sum(),
            'success_rate': _calculate_success_rate(scraping_tasks)
        },
        'embeddings': {
            'total_chunks': embedding_chunks_created._value.sum(),
            'success_rate': _calculate_success_rate(embedding_tasks)
        },
        'rag': {
            'total_queries': rag_queries._value.sum(),
            'cache_hit_rate': rag_cache_hit_rate._value.get(),
            'average_latency': _calculate_average_latency(rag_latency)
        },
        'system': {
            'redis_healthy': check_redis_connection(),
            'chromadb_healthy': check_chromadb_connection(),
            'disk_space': check_disk_space()
        }
    }


def _calculate_success_rate(counter: Counter) -> float:
    """Calculate success rate from a counter with status labels."""
    try:
        total = sum(counter._metrics.values())
        if total == 0:
            return 0.0
        
        success = counter._metrics.get(('success',), 0)
        return (success / total) * 100
        
    except Exception:
        return 0.0


def _calculate_average_latency(histogram: Histogram) -> float:
    """Calculate average latency from histogram."""
    try:
        return histogram._sum.get() / histogram._count.get() if histogram._count.get() > 0 else 0.0
    except Exception:
        return 0.0
