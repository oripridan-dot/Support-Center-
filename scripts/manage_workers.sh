#!/bin/bash

# Worker Orchestration Management Script
# Manages Celery workers, monitoring, and system health

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"
LOG_DIR="$SCRIPT_DIR/../logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# ============================================================================
# Utility Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Check Dependencies
# ============================================================================

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Redis
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is running"
    else
        log_error "Redis is not running. Please start Redis first."
        exit 1
    fi
    
    # Check Python environment
    if ! python3 -c "import celery" > /dev/null 2>&1; then
        log_error "Celery not found. Please install requirements: pip install -r requirements.txt"
        exit 1
    fi
    
    log_success "All dependencies OK"
}

# ============================================================================
# Start Workers
# ============================================================================

start_scraper_workers() {
    log_info "Starting scraper workers (4 concurrent)..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager worker \
        -Q scraping \
        -c 4 \
        --loglevel=info \
        --logfile="$LOG_DIR/scraper_worker.log" \
        --pidfile="$LOG_DIR/scraper_worker.pid" \
        --detach
    
    log_success "Scraper workers started"
}

start_embedding_workers() {
    log_info "Starting embedding workers (2 concurrent)..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager worker \
        -Q embeddings \
        -c 2 \
        --loglevel=info \
        --logfile="$LOG_DIR/embedding_worker.log" \
        --pidfile="$LOG_DIR/embedding_worker.pid" \
        --detach
    
    log_success "Embedding workers started"
}

start_rag_workers() {
    log_info "Starting RAG query workers (8 concurrent)..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager worker \
        -Q rag_queries \
        -c 8 \
        --loglevel=info \
        --logfile="$LOG_DIR/rag_worker.log" \
        --pidfile="$LOG_DIR/rag_worker.pid" \
        --detach
    
    log_success "RAG workers started"
}

start_maintenance_workers() {
    log_info "Starting maintenance workers (2 concurrent)..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager worker \
        -Q maintenance \
        -c 2 \
        --loglevel=info \
        --logfile="$LOG_DIR/maintenance_worker.log" \
        --pidfile="$LOG_DIR/maintenance_worker.pid" \
        --detach
    
    log_success "Maintenance workers started"
}

start_celery_beat() {
    log_info "Starting Celery Beat scheduler..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager beat \
        --loglevel=info \
        --logfile="$LOG_DIR/celery_beat.log" \
        --pidfile="$LOG_DIR/celery_beat.pid" \
        --detach
    
    log_success "Celery Beat started"
}

start_flower() {
    log_info "Starting Flower monitoring dashboard..."
    
    cd "$BACKEND_DIR"
    celery -A app.workers.queue_manager flower \
        --port=5555 \
        --logfile="$LOG_DIR/flower.log" \
        --pidfile="$LOG_DIR/flower.pid" \
        --detach
    
    log_success "Flower started at http://localhost:5555"
}

start_all_workers() {
    log_info "Starting all workers..."
    
    check_dependencies
    
    start_scraper_workers
    start_embedding_workers
    start_rag_workers
    start_maintenance_workers
    start_celery_beat
    start_flower
    
    log_success "All workers started successfully!"
    log_info "Monitor workers at: http://localhost:5555"
}

# ============================================================================
# Stop Workers
# ============================================================================

stop_workers() {
    log_info "Stopping all workers..."
    
    cd "$BACKEND_DIR"
    
    # Stop all Celery workers gracefully
    celery -A app.workers.queue_manager control shutdown || true
    
    # Kill any remaining processes
    for pidfile in "$LOG_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if ps -p "$pid" > /dev/null 2>&1; then
                log_info "Killing process $pid..."
                kill "$pid" || true
            fi
            rm "$pidfile"
        fi
    done
    
    log_success "All workers stopped"
}

# ============================================================================
# Status & Monitoring
# ============================================================================

show_status() {
    log_info "Worker Status:"
    echo ""
    
    cd "$BACKEND_DIR"
    
    # Show active workers
    celery -A app.workers.queue_manager inspect active || {
        log_warning "No active workers found"
    }
    
    echo ""
    log_info "Queue Status:"
    celery -A app.workers.queue_manager inspect stats || true
}

show_logs() {
    local worker=$1
    
    if [ -z "$worker" ]; then
        log_info "Available logs:"
        ls -1 "$LOG_DIR"/*.log 2>/dev/null || log_warning "No logs found"
    else
        log_info "Tailing $worker logs..."
        tail -f "$LOG_DIR/${worker}_worker.log"
    fi
}

purge_queue() {
    local queue=$1
    
    if [ -z "$queue" ]; then
        log_error "Usage: $0 purge <queue_name>"
        log_info "Available queues: scraping, embeddings, rag_queries, maintenance"
        exit 1
    fi
    
    log_warning "Purging queue: $queue"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$BACKEND_DIR"
        celery -A app.workers.queue_manager purge -Q "$queue"
        log_success "Queue $queue purged"
    else
        log_info "Cancelled"
    fi
}

# ============================================================================
# Test Functions
# ============================================================================

test_scraping() {
    log_info "Testing scraping worker with sample URL..."
    
    cd "$BACKEND_DIR"
    python3 -c "
from app.workers.scraper_worker import scrape_product_page
result = scrape_product_page.delay('https://www.roland.com', 'roland')
print(f'Task submitted: {result.id}')
print('Waiting for result...')
print(result.get(timeout=60))
"
    
    log_success "Scraping test completed"
}

test_embedding() {
    log_info "Testing embedding worker..."
    
    cd "$BACKEND_DIR"
    python3 -c "
from app.workers.embedding_worker import embedding_task
test_content = 'This is a test document for embedding generation.'
result = embedding_task.delay(test_content, 'https://test.com', 'test_brand')
print(f'Task submitted: {result.id}')
print('Waiting for result...')
print(result.get(timeout=60))
"
    
    log_success "Embedding test completed"
}

test_rag() {
    log_info "Testing RAG worker..."
    
    cd "$BACKEND_DIR"
    python3 -c "
from app.workers.rag_worker import rag_query_task
result = rag_query_task.delay('How do I reset my device?', brand='test')
print(f'Task submitted: {result.id}')
print('Waiting for result...')
print(result.get(timeout=60))
"
    
    log_success "RAG test completed"
}

# ============================================================================
# Main CLI
# ============================================================================

show_help() {
    cat << EOF
Worker Orchestration Management Script

Usage: $0 <command> [options]

Commands:
    start               Start all workers
    stop                Stop all workers
    restart             Restart all workers
    status              Show worker status
    logs [worker]       Show logs (optional: specify worker name)
    purge <queue>       Purge a specific queue
    
    test-scraping       Test scraping worker
    test-embedding      Test embedding worker
    test-rag            Test RAG worker
    
    help                Show this help message

Worker names:
    scraper
    embedding
    rag
    maintenance
    celery_beat
    flower

Examples:
    $0 start                    # Start all workers
    $0 logs scraper             # Tail scraper logs
    $0 purge scraping           # Purge scraping queue
    $0 test-rag                 # Test RAG worker

EOF
}

# Main command handler
case "${1:-help}" in
    start)
        start_all_workers
        ;;
    stop)
        stop_workers
        ;;
    restart)
        stop_workers
        sleep 2
        start_all_workers
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    purge)
        purge_queue "$2"
        ;;
    test-scraping)
        test_scraping
        ;;
    test-embedding)
        test_embedding
        ;;
    test-rag)
        test_rag
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
